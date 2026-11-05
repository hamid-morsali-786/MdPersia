"""Acceptance against the actual installed Tauri/WebView2 application on Windows.

Uses an isolated WebView2 profile and a temporary CDP port. No dev server or
mock bridge is involved. The executable and engine run with a restricted PATH.
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from contextlib import ExitStack
import json
import os
from pathlib import Path
import platform
import socket
import struct
import subprocess
import time
from urllib.request import urlopen
import zipfile
import zlib

from playwright.sync_api import expect, sync_playwright


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def owned_processes(directory: Path) -> list[dict]:
    literal = str(directory).replace("'", "''")
    query = f"Get-CimInstance Win32_Process | Where-Object {{ $_.ExecutablePath -and $_.ExecutablePath.StartsWith('{literal}', [StringComparison]::OrdinalIgnoreCase) }} | Select-Object ProcessId,Name,WorkingSetSize | ConvertTo-Json -Compress"
    result = subprocess.check_output(['powershell.exe', '-NoProfile', '-Command', query], text=True)
    value = json.loads(result) if result.strip() else []
    return value if isinstance(value, list) else [value]


def open_registered_markdown(path: Path) -> None:
    class ShellInfo(ctypes.Structure):
        _fields_ = [('cbSize', wintypes.DWORD), ('fMask', wintypes.ULONG),
                    ('hwnd', wintypes.HWND), ('lpVerb', wintypes.LPCWSTR),
                    ('lpFile', wintypes.LPCWSTR), ('lpParameters', wintypes.LPCWSTR),
                    ('lpDirectory', wintypes.LPCWSTR), ('nShow', ctypes.c_int),
                    ('hInstApp', wintypes.HINSTANCE), ('lpIDList', ctypes.c_void_p),
                    ('lpClass', wintypes.LPCWSTR), ('hkeyClass', wintypes.HKEY),
                    ('dwHotKey', wintypes.DWORD), ('hIcon', wintypes.HANDLE),
                    ('hProcess', wintypes.HANDLE)]
    shell = ctypes.WinDLL('shell32', use_last_error=True)
    shell.ShellExecuteExW.argtypes = [ctypes.POINTER(ShellInfo)]
    shell.ShellExecuteExW.restype = wintypes.BOOL
    info = ShellInfo(cbSize=ctypes.sizeof(ShellInfo), fMask=0x1 | 0x40,
                     lpVerb='open', lpFile=str(path), lpClass='MdPersia.Markdown', nShow=1)
    if not shell.ShellExecuteExW(ctypes.byref(info)):
        raise ctypes.WinError(ctypes.get_last_error())
    if info.hProcess:
        kernel = ctypes.WinDLL('kernel32')
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        try:
            assert kernel.WaitForSingleObject(info.hProcess, 15000) == 0
        finally:
            kernel.CloseHandle(info.hProcess)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('executable', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--registered-handler', action='store_true')
    parser.add_argument('--reuse-runtime', action='store_true', help='Skip first-install scenarios when resuming a failed acceptance run')
    args = parser.parse_args()
    exe, output = args.executable.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    port = free_port()
    profile = output / ('profile-' + str(time.time_ns()))
    env = {**os.environ, 'PATH': os.path.join(os.environ['SYSTEMROOT'], 'System32'),
        'WEBVIEW2_USER_DATA_FOLDER': str(profile),
        'WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS': f'--remote-debugging-port={port} --remote-debugging-address=127.0.0.1 --no-first-run'}
    for key in ('PYTHONHOME', 'PYTHONPATH', 'PLAYWRIGHT_BROWSERS_PATH'):
        env.pop(key, None)
    original = '# سند نخست\r\n\r\n- Host: localhost برای اتصال\r\n\r\nEnglish Solver: example.\r\n\r\n![local](local-image.png)\r\n\r\n```mermaid\r\ngraph LR\r\nA[شروع]-->B[پایان]\r\n```\r\n'
    original += '\r\n```python\r\ndef solve(value):\r\n    return {"result": value, "count": 42}\r\n```\r\n'
    original += '\r\n\r\nمتن برای آزمون پیمایش پیش‌نمایش.' * 30
    first, second, third = [output / name for name in ('فایل نخست.md', 'second.markdown', 'third.md')]
    first.write_bytes(original.encode('utf-8-sig'))
    second.write_text('# سند دوم\n\nمتن دوم.', encoding='utf-8')
    third.write_text('# سند سوم\n\nمتن سوم.', encoding='utf-8')
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind+data))
    image = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 80, 30, 8, 2, 0, 0, 0))
    image += chunk(b'IDAT', zlib.compress((b'\0'+b'\x46\x82\xb4'*80)*30)) + chunk(b'IEND', b'')
    (output / 'local-image.png').write_bytes(image)
    started = time.perf_counter()
    proc = subprocess.Popen([str(exe), str(first)], cwd=output, env=env)
    report = {'os': platform.platform(), 'executable': str(exe), 'restrictedPath': env['PATH']}
    errors = []
    try:
        with sync_playwright() as p, ExitStack() as diagnostics:
            def capture_diagnostics():
                if proc.poll() is not None:
                    return
                try:
                    (output / 'console-diagnostic.txt').write_text(page.locator('.console-report').text_content() or '', encoding='utf-8')
                    (output / 'interaction-diagnostic.json').write_text(json.dumps(page.evaluate('window.__qaEvents || []'), ensure_ascii=False, indent=2), encoding='utf-8')
                    page.screenshot(path=str(output / 'failure.png'))
                except Exception:
                    pass
            diagnostics.callback(capture_diagnostics)
            deadline = time.monotonic() + 40
            while True:
                try:
                    urlopen(f'http://127.0.0.1:{port}/json/version', timeout=.2).close()
                    break
                except OSError:
                    if proc.poll() is not None:
                        raise RuntimeError(f'Native app exited: {proc.returncode}')
                    if time.monotonic() > deadline:
                        raise TimeoutError('WebView2 CDP endpoint did not become ready')
                    time.sleep(.1)
            browser = p.chromium.connect_over_cdp(f'http://127.0.0.1:{port}')
            page = browser.contexts[0].pages[0]
            report['webViewVersion'] = browser.version
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.wait_for_function('Boolean(window.__TAURI_INTERNALS__)')
            frame = page.frame_locator('iframe')
            frame.get_by_role('heading', name='سند نخست', exact=True).wait_for(timeout=30000)
            report['launchToRenderedHeadingSeconds'] = round(time.perf_counter()-started, 3)
            frame.locator('.mermaid svg').wait_for(timeout=30000)
            frame.locator('img').wait_for()
            assert frame.locator('img').evaluate('(el)=>el.complete && el.naturalWidth>0')
            assert frame.locator('body').evaluate('async()=>{await document.fonts.ready;return document.fonts.check("16px Vazirmatn")}')
            report['nativePreviewWithLocalImageFontAndMermaid'] = True
            from window_icon_probe import probe
            report['actualNativeWindowIcons'] = probe(output / 'window-icons', title_prefix='MdPersia |')
            assert report['actualNativeWindowIcons']
            assert all(max(row.get(slot, [0])[0] for slot in ('large', 'small', 'small2')) >= 32
                       for row in report['actualNativeWindowIcons'])
            # Tauri can supply ICON_SMALL without setting ICON_BIG. Verify the
            # actual pixels, rather than treating an unset slot as a blurry icon.
            from PIL import Image
            icon = Image.open(Path(__file__).resolve().parents[1] / 'src/fa_md_pdf/assets/mdpersia.ico')
            actual_icon = Image.open(output / 'window-icons/window-small.png').convert('RGBA')
            expected_icon = icon.ico.getimage(actual_icon.size).convert('RGBA')
            assert actual_icon.tobytes() == expected_icon.tobytes()
            report['nativeWindowIconMatchesSizeSpecificOriginalArtwork'] = True
            sidebar = page.locator('#output-inspector')
            workspace = page.get_by_role('region', name='محیط مطالعه', exact=True)
            assert sidebar.bounding_box()['x'] < workspace.bounding_box()['x'] < page.locator('tbody').bounding_box()['x']
            page.get_by_role('button', name='پنهان‌کردن تنظیمات خروجی', exact=True).click()
            assert sidebar.bounding_box()['width'] == 0
            page.get_by_role('button', name='نمایش تنظیمات خروجی', exact=True).click()
            separator = page.get_by_role('separator', name='تغییر عرض پنل تنظیمات', exact=False)
            box = separator.bounding_box()
            page.mouse.move(box['x'] + box['width'] / 2, box['y'] + 200)
            page.mouse.down()
            page.evaluate('window.dispatchEvent(new Event("blur"))')
            page.mouse.up()
            expect(page.locator('iframe')).to_have_css('pointer-events', 'auto')
            inner = page.locator('iframe').element_handle().content_frame()
            frame_box = page.locator('iframe').bounding_box()
            page.mouse.move(frame_box['x'] + 100, frame_box['y'] + 200)
            page.mouse.wheel(0, 600)
            inner.wait_for_function('()=>window.scrollY>100')
            assert frame.locator('.mermaid').evaluate('el=>getComputedStyle(el).filter') == 'none'
            assert frame.locator('pre:not(.mermaid) code').evaluate('el=>getComputedStyle(el).backgroundColor') == 'rgba(0, 0, 0, 0)'
            inner.evaluate('window.scrollTo(0,0)')
            page.screenshot(path=str(output / 'native-reading-layout.png'))
            report['nativeCenteredLayoutSidebarAndScrollAfterInterruptedDrag'] = True
            runtime = page.evaluate('window.__TAURI_INTERNALS__.invoke("conversion_runtime_status")')
            runtime_directory = Path(runtime['directory'].removeprefix('\\\\?\\'))
            def application_processes():
                return owned_processes(exe.parent) + owned_processes(runtime_directory)
            report['initialConversionRuntime'] = runtime
            if not args.reuse_runtime:
                assert not runtime['installed'], 'Use --reuse-runtime only for an explicitly resumed run'
                assert not (exe.parent / 'engine').exists()
                assert not (exe.parent / 'browsers').exists()
                report['readerWorksBeforeOptionalDownload'] = True
            for file in (second, third):
                subprocess.run([str(exe), str(file)], cwd=output, env=env, timeout=15, check=True)
            expect(page.locator('tbody tr')).to_have_count(3)
            frame.get_by_role('heading', name='سند سوم', exact=True).wait_for()
            if args.registered_handler:
                open_registered_markdown(second)
                frame.get_by_role('heading', name='سند دوم', exact=True).wait_for()
                expect(page.locator('tbody tr')).to_have_count(3)
                report['windowsShellRegisteredHandlerOpensInExistingWindow'] = True
            subprocess.run([str(exe), str(first)], cwd=output, env=env, timeout=15, check=True)
            expect(page.locator('tbody tr')).to_have_count(3)
            frame.get_by_role('heading', name='سند نخست', exact=True).wait_for()
            report['successiveOpensAppendAndReopenDeduplicates'] = True
            page.get_by_role('button', name='ویرایش سند', exact=True).click()
            content = page.locator('.cm-content[contenteditable=true]')
            expect(content).to_be_visible()
            content.click()
            page.keyboard.press('Control+a')
            changed = original.replace('\r\n', '\n').replace('سند نخست', 'سند ویرایش‌شده') + '\nذخیرهٔ واقعی در نصب\n'
            page.keyboard.insert_text(changed)
            frame.get_by_role('heading', name='سند ویرایش‌شده', exact=True).wait_for(timeout=15000)
            page.keyboard.press('Control+s')
            expect(page.get_by_role('button', name='ذخیره سند', exact=True)).to_be_disabled()
            expect(page.get_by_role('img', name='تغییرات ذخیره‌نشده', exact=True)).to_have_count(0)
            assert first.read_bytes() == changed.replace('\n', '\r\n').encode('utf-8-sig')
            report['nativeLiveEditAndActualCtrlSSave'] = True
            content.click()
            page.keyboard.press('Control+End')
            page.keyboard.insert_text('\nپیش‌نویس برای آزمون خروج\n')
            expect(page.get_by_role('img', name='تغییرات ذخیره‌نشده', exact=True)).to_have_count(1)
            page.evaluate('void window.__TAURI_INTERNALS__.invoke("plugin:window|close",{label:"main"})')
            guard = page.get_by_role('dialog', name='تغییرات ذخیره‌نشده', exact=True)
            expect(guard).to_be_visible()
            guard.get_by_role('button', name='انصراف', exact=True).click()
            page.keyboard.press('Control+s')
            expect(page.get_by_role('button', name='ذخیره سند', exact=True)).to_be_disabled()
            expect(page.get_by_role('img', name='تغییرات ذخیره‌نشده', exact=True)).to_have_count(0)
            report['nativeCloseGuardPreservesUnsavedEdits'] = True
            # Exercise the native directory command against actual files.
            scanned = page.evaluate('(folderPath)=>window.__TAURI_INTERNALS__.invoke("scan_folder",{folderPath,recursive:true})', str(output))
            assert {first.name, second.name, third.name} <= {f['name'] for f in scanned}
            report['nativeFolderScan'] = True
            page.get_by_role('button', name='پایان ویرایش', exact=True).click()
            page.get_by_role('button', name='DOCX (Word)', exact=True).click()
            page.get_by_role('button', name='شروع تبدیل اسناد', exact=True).click()
            if not runtime['installed']:
                dialog = page.get_by_role('dialog', name='آماده‌سازی خروجی PDF و Word', exact=True)
                expect(dialog).to_be_visible()
                assert page.evaluate('window.__TAURI_INTERNALS__.invoke("conversion_runtime_status")')['phase'] == 'idle'
                for _ in range(dialog.locator('button').count() + 2):
                    page.keyboard.press('Tab')
                    assert dialog.evaluate('el=>el.contains(document.activeElement)')
                assert dialog.evaluate('el=>el.scrollWidth<=el.clientWidth')
                page.keyboard.press('Escape')
                expect(dialog).not_to_be_visible()
                expect(page.get_by_role('button', name='شروع تبدیل اسناد', exact=True)).to_be_focused()
                page.get_by_role('button', name='شروع تبدیل اسناد', exact=True).click()
                expect(dialog).to_be_visible()
                report['optionalDialogKeyboardContainmentEscapeAndFocusRestore'] = True
                page.screenshot(path=str(output / 'optional-engine-dark.png'))
                report['conversionRequiresExplicitDownload'] = True
                # Exact-length corrupt input must fail SHA-256, before extraction.
                corrupt = output / 'corrupt-conversion.zip'
                with corrupt.open('wb') as handle:
                    handle.truncate(runtime['totalBytes'])
                rejected = page.evaluate('''async sourcePath => {
                  try { await window.__TAURI_INTERNALS__.invoke("conversion_runtime_install", {sourcePath}); return null; }
                  catch (error) { return String(error); }
                }''', str(corrupt))
                corrupt.unlink()
                assert rejected and 'سالم' in rejected, rejected
                assert not runtime_directory.exists()
                assert not list(runtime_directory.parent.glob('.download-*'))
                report['corruptSameLengthPackageRejectedBeforeExtraction'] = True
                expect(dialog.get_by_role('alert')).to_be_visible()
                page.screenshot(path=str(output / 'optional-engine-error.png'))
                dialog.get_by_role('button', name='تلاش دوباره برای دریافت', exact=True).click()
                dialog.get_by_role('button', name='توقف دریافت', exact=True).click()
                expect(dialog.get_by_text('دریافت متوقف شد.', exact=False)).to_be_visible(timeout=15000)
                cancelled = page.evaluate('window.__TAURI_INTERNALS__.invoke("conversion_runtime_status")')
                assert not cancelled['installed'] and cancelled['phase'] == 'cancelled'
                assert not runtime_directory.exists()
                assert not list(runtime_directory.parent.glob('.download-*'))
                report['downloadCancelLeavesNoPartialInstallation'] = True
                dialog.get_by_role('button', name='دریافت موتور تبدیل', exact=True).click()
                page.screenshot(path=str(output / 'optional-engine-downloading.png'))
                dialog.get_by_role('button', name='ادامهٔ مطالعه', exact=True).click()
                frame.get_by_role('heading', name='سند ویرایش‌شده', exact=True).wait_for()
                report['readingContinuesDuringExplicitDownload'] = True
                deadline = time.monotonic() + 900
                previous = None
                while time.monotonic() < deadline:
                    status = page.evaluate('window.__TAURI_INTERNALS__.invoke("conversion_runtime_status")')
                    progress = (status['phase'], status['downloadedBytes'] // (32 * 1048576))
                    if progress != previous:
                        print(json.dumps({'optionalRuntime': status['phase'], 'bytes': status['downloadedBytes']}, ensure_ascii=True), flush=True)
                        previous = progress
                    if status['installed']:
                        break
                    assert status['phase'] != 'error', status['error']
                    page.wait_for_timeout(500)
                else:
                    raise TimeoutError('Optional conversion package did not become ready')
                report['realPublicDownloadVerifiedAndInstalled'] = status
                report['optionalInstalledFileBytes'] = sum(path.stat().st_size for path in runtime_directory.rglob('*') if path.is_file())
                page.get_by_role('button', name='مدیریت موتور تبدیل', exact=True).click()
                expect(dialog.get_by_text('موتور تبدیل آماده است', exact=True)).to_be_visible()
                dialog.get_by_role('button', name='شروع تبدیل', exact=True).click()
            page.get_by_text('فرآیند تبدیل پایان یافت:', exact=False).wait_for(timeout=90000)
            assert page.get_by_text('فرآیند تبدیل پایان یافت: 3 موفق، 0 ناموفق.', exact=True).is_visible()
            for file in (first, second, third):
                with zipfile.ZipFile(file.with_suffix('.docx')) as archive:
                    assert 'word/document.xml' in archive.namelist()
            report['realNativeBatchDocxConversion'] = True
            page.get_by_role('tab', name='پیشرفته', exact=True).click()
            watch = page.get_by_label('حالت پایش زنده (Watch Mode)', exact=True)
            watch.check()
            page.get_by_role('button', name='شروع تبدیل اسناد', exact=True).click()
            console = page.locator('.console-report')
            console.get_by_text('پایش زنده فعال است', exact=True).wait_for(timeout=30000)
            first.write_text('# ویرایش بیرونی\n\nآزمون پایش نصب واقعی.', encoding='utf-8')
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                try:
                    with zipfile.ZipFile(first.with_suffix('.docx')) as archive:
                        if 'ویرایش بیرونی' in archive.read('word/document.xml').decode('utf-8'):
                            break
                except (OSError, zipfile.BadZipFile):
                    pass
                page.wait_for_timeout(200)
            else:
                raise AssertionError('Native watch did not rebuild Word output')
            console.get_by_role('button', name='توقف پایش', exact=True).click()
            expect(page.get_by_role('button', name='شروع تبدیل اسناد', exact=True)).to_be_enabled(timeout=10000)
            watch.uncheck()
            report['nativeWatchRebuildAndCancellation'] = True
            page.get_by_role('tab', name='پیش‌نمایش سند', exact=True).click()
            page.get_by_role('button', name='تنظیمات برنامه', exact=True).click()
            settings = page.get_by_role('dialog', name='تنظیمات برنامه', exact=True)
            settings.get_by_label('روشن', exact=True).check()
            settings.get_by_role('button', name='تمام', exact=True).click()
            assert not page.locator('html').evaluate('el=>el.classList.contains("dark")')
            page.screenshot(path=str(output / 'native-workspace.png'))
            report['ownedProcessesWhileReading'] = application_processes()
            assert sum(row['Name'].lower() == 'mdpersia.exe' for row in report['ownedProcessesWhileReading']) == 1
            assert not any(row['Name'].lower() == 'chrome-headless-shell.exe' for row in report['ownedProcessesWhileReading'])
            report['noConversionBrowserRemainsWhileReading'] = True
            assert not errors, errors
            report['pageErrors'] = errors
            page.evaluate('void window.__TAURI_INTERNALS__.invoke("plugin:window|close",{label:"main"})')
            proc.wait(timeout=15)
            for _ in range(30):
                if not application_processes():
                    break
                time.sleep(.1)
            assert not application_processes(), 'Application children remained after exit'
            report['engineAndConversionTreesStopOnExit'] = True
            # A normal launch reuses the installed profile, unlike the fresh-profile
            # first-launch timing above. Both measurements include CDP attachment.
            started = time.perf_counter()
            proc = subprocess.Popen([str(exe), str(third)], cwd=output, env=env)
            deadline = time.monotonic() + 30
            while True:
                if time.monotonic() > deadline:
                    raise TimeoutError('Subsequent native launch did not expose its WebView2 page')
                try:
                    again = p.chromium.connect_over_cdp(f'http://127.0.0.1:{port}', timeout=1000)
                    if again.contexts and again.contexts[0].pages:
                        page = again.contexts[0].pages[0]
                        page.on('pageerror', lambda error: errors.append(str(error)))
                        break
                except Exception:
                    if time.monotonic() > deadline:
                        raise
                time.sleep(.1)
            page.frame_locator('iframe').get_by_role('heading', name='سند سوم', exact=True).wait_for(timeout=20000)
            report['subsequentLaunchToRenderedHeadingSeconds'] = round(time.perf_counter()-started, 3)
            assert not page.locator('html').evaluate('el=>el.classList.contains("dark")')
            expect(page.locator('tbody tr')).to_have_count(1)
            report['preferencesPersistAndPreviousQueueDoesNotBecomeGhostFiles'] = True
            assert page.evaluate('window.__TAURI_INTERNALS__.invoke("conversion_runtime_status")')['installed']
            report['conversionResourcesReusedAcrossLaunches'] = True
            page.get_by_role('button', name='PDF', exact=True).click()
            page.get_by_role('button', name='شروع تبدیل اسناد', exact=True).click()
            page.get_by_text('فرآیند تبدیل پایان یافت: 1 موفق، 0 ناموفق.', exact=True).wait_for(timeout=60000)
            assert third.with_suffix('.pdf').read_bytes().startswith(b'%PDF-')
            report['realNativePdfConversion'] = True
            page.evaluate('''() => {
              window.__qaEvents=[];
              for (const type of ['pointerdown','pointerup','click']) for (const capture of [true,false])
                document.addEventListener(type, event => window.__qaEvents.push({type,capture,
                  target: event.target.tagName+':'+event.target.textContent.slice(0,80),
                  x:event.clientX,y:event.clientY,
                  bounds:document.querySelector('dialog')?.getBoundingClientRect().toJSON()}), capture);
            }''')
            page.get_by_role('button', name='مدیریت موتور تبدیل', exact=True).click()
            dialog = page.get_by_role('dialog', name='آماده‌سازی خروجی PDF و Word', exact=True)
            page.screenshot(path=str(output / 'optional-engine-light.png'))
            dialog.get_by_role('button', name='حذف موتور و آزادکردن فضا', exact=True).click()
            expect(dialog.get_by_role('button', name='دریافت موتور تبدیل', exact=True)).to_be_visible(timeout=30000)
            assert not runtime_directory.exists()
            dialog.get_by_role('button', name='ادامهٔ مطالعه', exact=True).click()
            page.get_by_role('tab', name='پیش‌نمایش سند', exact=True).click()
            page.frame_locator('iframe').get_by_role('heading', name='سند سوم', exact=True).wait_for()
            assert third.with_suffix('.pdf').read_bytes().startswith(b'%PDF-')
            report['optionalRemovalPreservesReadingAndOutputDocuments'] = True
            assert not errors, errors
            report['pageErrors'] = errors
            page.evaluate('void window.__TAURI_INTERNALS__.invoke("plugin:window|close",{label:"main"})')
            proc.wait(timeout=15)
            assert not application_processes()
    except Exception:
        report['pageErrors'] = errors
        raise
    finally:
        if proc.poll() is None:
            # Only the specific acceptance application and its descendants.
            subprocess.run(['taskkill.exe', '/PID', str(proc.pid), '/T', '/F'], capture_output=True)
        (output / 'native-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
