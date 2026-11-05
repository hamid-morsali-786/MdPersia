"""Exercise the existing desktop UI/bridge in a clean browser, including offline Mermaid.

Start `npm run preview -- --port 1421` in desktop-tauri first, then run:
  py -3.11 scripts/verify-desktop.py --url http://127.0.0.1:1421
Requires the project's Playwright dependency and the installed Edge browser.
"""

from __future__ import annotations

import argparse
import atexit
import base64
import ctypes
import zipfile
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote, urlparse
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:1421")
    parser.add_argument("--start", action="store_true", help="Start the existing production desktop server")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    output = root / "output" / "playwright"
    output.mkdir(parents=True, exist_ok=True)
    server = None
    server_start_ms = None
    if args.start:
        server_started = time.perf_counter()
        server = subprocess.Popen([
            shutil.which("node"), "dist/desktop-server.mjs",
            "--port", str(urlparse(args.url).port), "--host", "127.0.0.1", "--strictPort",
        ], cwd=root / "desktop-tauri", env={**os.environ, "PYTHON_EXECUTABLE": sys.executable, "MDPERSIA_INITIAL_FILE": str(root / "examples" / "sample-fa.md")},
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        atexit.register(lambda: server.terminate() if server.poll() is None else None)
        for _ in range(150):
            try:
                with urlopen(args.url + "/api/health", timeout=.1) as response:
                    assert json.load(response)["mode"] == "production"
                    server_start_ms = round((time.perf_counter() - server_started) * 1000)
                    break
            except OSError:
                time.sleep(.1)
        else:
            raise RuntimeError("Production desktop server did not start")
    document = output / "سند روزمره با فاصله.MD"
    original = (
        "# سند روزمره\n\nنسخه اول برای خواندن متن فارسی و English.\n\n"
        "- Host: localhost برای اتصال محلی\n- `Port`: مقدار درگاه\n\n"
        "## English heading\n\nThis paragraph stays left to right.\n\n"
        "```mermaid\ngraph LR\nA[شروع] --> B[پایان]\n```\n"
    )
    linked = output / "سند پیوندی.md"
    linked.write_text("# سند پیوندی\n\nیک سند مستقل.", encoding="utf-8")
    image_dir = output / "preview assets"
    image_dir.mkdir(exist_ok=True)
    (image_dir / "sample.png").write_bytes(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jPioAAAAASUVORK5CYII="))
    original += "\n\n![تصویر محلی](preview%20assets/sample.png)\n\n[سند بعدی](سند%20پیوندی.md)\n\n"
    original += "\n\n".join("این بند برای بررسی حفظ محل مطالعه در سند است." for _ in range(24))
    document.write_text(original, encoding="utf-8-sig")
    report = {}
    if server_start_ms is not None:
        report["serverStartupMs"] = server_start_ms
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        errors = []
        previews = []
        remote = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("request", lambda req: previews.append(req.url)
                if "/api/preview-html?" in req.url else None)

        def offline(route):
            if urlparse(route.request.url).netloc == urlparse(args.url).netloc:
                route.continue_()
            else:
                remote.append(route.request.url)
                route.abort()

        page.route("**/*", offline)
        renderer_pid = page.request.get(args.url + '/api/health').json()['rendererPid']
        assert page.request.get(args.url + '/api/initial-items').json()['items'] == []
        initial_b = page.request.get(args.url + '/api/initial-items?file=' + quote(str(document))).json()
        assert [item['name'] for item in initial_b['items']] == [document.name], initial_b
        report['launchEnvironmentNeverReplaysFirstFile'] = True
        started = time.perf_counter()
        page.goto(args.url + "/?file=" + quote(str(root / "examples" / "sample-fa.md")))
        frame = page.frame_locator("iframe")
        frame.locator(".markdown-body").wait_for(timeout=30000)
        expect(page.get_by_text('در حال رندر پیش‌نمایش…', exact=True)).to_be_hidden()
        report["navigationToTextMs"] = round((time.perf_counter() - started) * 1000)
        frame.locator(".mermaid svg").wait_for(timeout=30000)
        report["navigationToDiagramMs"] = round((time.perf_counter() - started) * 1000)
        inner = page.locator("iframe").element_handle().content_frame()
        inner.evaluate("document.fonts.ready")
        assert inner.evaluate("window.__FA_MD_PDF_MERMAID_ERROR") is None
        assert page.locator('header img').evaluate("img => img.complete && img.naturalWidth > 0")
        before = len(previews)
        inner.evaluate("window.__appearanceTest = true")
        page.get_by_role("button", name="بزرگ‌نمایی", exact=True).click()
        inner.wait_for_function("getComputedStyle(document.documentElement).zoom === '1.1'")
        page.get_by_role("button", name="تغییر تم", exact=True).click()
        inner.wait_for_function("getComputedStyle(document.body).backgroundColor === 'rgb(255, 255, 255)'")
        assert inner.evaluate("window.__appearanceTest === true")
        assert len(previews) == before, "Theme/zoom re-requested the document"
        report["appearanceAdditionalRenders"] = len(previews) - before
        page.get_by_role("button", name="کوچک‌نمایی", exact=True).click()
        page.screenshot(path=str(output / "mdpersia-after-light.png"))
        page.get_by_role("button", name="تغییر تم", exact=True).click()
        page.screenshot(path=str(output / "mdpersia-after-dark.png"))

        started = time.perf_counter()
        result = page.request.post(args.url + "/api/open-file", data={"path": str(document)})
        assert result.ok and result.json()["delivered"]
        frame.get_by_role("heading", name="سند روزمره", exact=True).wait_for()
        report["handoffToTextMs"] = round((time.perf_counter() - started) * 1000)
        assert len(page.context.pages) == 1
        assert frame.get_by_role("heading", name="English heading").get_attribute("dir") == "ltr"
        assert "Host:" in frame.locator("li bdi").first.inner_text()
        assert frame.locator(".markdown-body").inner_text().startswith("سند روزمره")
        frame.locator(".mermaid svg").wait_for()
        report["sameWindowHandoff"] = True
        rows = page.locator('tbody tr')
        expect(rows).to_have_count(2)
        report['queueAccumulatesDocuments'] = True
        image = frame.get_by_alt_text('تصویر محلی')
        expect(image).to_be_visible()
        assert image.evaluate('img => img.complete && img.naturalWidth > 0'), image.get_attribute('src')
        report['relativeLocalImages'] = True

        document.write_text(original.replace("نسخه اول", "نسخه دوم"), encoding="utf-8-sig")
        result = page.request.post(args.url + "/api/open-file", data={"path": str(document)})
        assert result.ok and result.json()["delivered"]
        frame.get_by_text("نسخه دوم", exact=False).wait_for()
        report["reopeningEditedFileInvalidatedCache"] = True

        document.write_text(original.replace("نسخه اول", "نسخه سوم"), encoding="utf-8-sig")
        page.get_by_role("button", name="بازسازی پیش‌نمایش", exact=True).click()
        frame.get_by_text("نسخه سوم", exact=False).wait_for()
        report["refreshInvalidatedCache"] = True

        source_button = page.get_by_role("button", name="کد منبع", exact=True)
        source_button.click()
        assert page.get_by_text("نسخه سوم", exact=False).count() > 0
        assert page.get_by_text("## English heading", exact=False).count() > 0
        page.get_by_role("button", name="پیش‌نمایش", exact=True).click()
        frame.locator(".markdown-body").wait_for()
        report["sourceAndRenderedViews"] = True
        # Viewing source and logs must preserve the same document/diagram instance.
        inner_b = page.locator('iframe').element_handle().content_frame()
        inner_b.evaluate('window.__keptDocument = true; window.scrollTo(0, 300)')
        page.get_by_role('tab', name='کنسول و گزارش‌ها').click()
        page.get_by_role('tab', name='پیش‌نمایش سند').click()
        assert inner_b.evaluate('window.__keptDocument === true')
        report['switchingWorkspaceKeepsPreview'] = True

        frame.get_by_role('link', name='سند بعدی', exact=True).click()
        frame.get_by_role('heading', name='سند پیوندی', exact=True).wait_for()
        expect(rows).to_have_count(3)
        report['linkedMarkdownOpensInSameQueue'] = True
        rows.filter(has_text=document.name).click()
        frame.get_by_role('heading', name='سند روزمره', exact=True).wait_for()
        inner_b = page.locator('iframe').element_handle().content_frame()
        inner_b.wait_for_function('window.scrollY >= 280')
        report['documentReadingPositionRestored'] = True

        twins = []
        for name in ('same-name-one', 'same-name-two'):
            folder = output / name
            folder.mkdir(exist_ok=True)
            twin = folder / 'README.md'
            twin.write_text('# ' + name, encoding='utf-8')
            twins.append(str(twin))
        page.evaluate("paths => Promise.all(paths.map(path => fetch('/api/open-file', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path})})))", twins)
        expect(rows).to_have_count(5)
        frame.get_by_role('heading', name='same-name-two', exact=True).wait_for()
        report['rapidOpensAndIdenticalBasenames'] = True

        rows.filter(has_text='sample-fa.md').click()
        rows.filter(has_text=document.name).click(modifiers=['Control'])
        frame.get_by_role('heading', name='سند روزمره', exact=True).wait_for()
        expect(page.locator('tbody tr[aria-selected="true"]')).to_have_count(2)
        report['multiselectDisplaysLastClickedDocument'] = True
        page.screenshot(path=str(output / 'mdpersia-multiple-documents.png'))
        page.keyboard.press('ArrowDown')
        frame.get_by_role('heading', name='سند پیوندی', exact=True).wait_for()
        rows.filter(has_text='README.md').last.click(modifiers=['Shift'])
        expect(page.locator('tbody tr[aria-selected="true"]')).to_have_count(3)
        report['keyboardNavigationAndRangeSelection'] = True

        search = page.locator('input[placeholder^="جستجوی نام فایل"]')
        search.fill('no document has this name')
        expect(rows).to_have_count(0)
        page.request.post(args.url + '/api/open-file', data={'path':str(document)})
        expect(rows).to_have_count(5)
        expect(search).to_have_value('')
        report['newlyOpenedFileCannotHideBehindOldFilter'] = True

        # A folder import merges, and changing future scan depth never deletes prior opens.
        folder = output / 'folder-import'
        (folder / 'nested').mkdir(parents=True, exist_ok=True)
        (folder / 'one.md').write_text('# Imported one', encoding='utf-8')
        (folder / 'nested' / 'two.md').write_text('# Imported two', encoding='utf-8')
        page.route('**/api/pick-folder?**', lambda route: route.fulfill(json={'path':str(folder),'cancelled':False}))
        page.get_by_role('button', name='افزودن پوشه', exact=True).click()
        expect(rows).to_have_count(7)
        page.get_by_label('افزودن زیرپوشه‌ها', exact=True).uncheck()
        expect(rows).to_have_count(7)
        page.get_by_role('button', name='افزودن پوشه', exact=True).click()
        expect(page.get_by_role('button', name='افزودن پوشه', exact=True)).to_be_enabled()
        expect(rows).to_have_count(7)
        report['folderImportsMergeAndDepthTogglePreservesQueue'] = True

        # Deleting the active row leaves a neighbor visible; clearing never restores the seed.
        rows.filter(has_text=document.name).click()
        page.keyboard.press('Delete')
        expect(rows).to_have_count(6)
        expect(frame.locator('.markdown-body')).to_be_visible()
        report['deleteSelectsNeighbor'] = True
        pending_file = output / 'pending-open.md'
        pending_file.write_text('# A pending open must not resurrect after clear', encoding='utf-8')
        held = []
        page.route('**/api/initial-items?file=*pending-open.md*', lambda route: held.append(route))
        with page.expect_request(lambda request: '/api/initial-items?file=' in request.url and 'pending-open.md' in request.url):
            page.request.post(args.url + '/api/open-file', data={'path':str(pending_file)})
        page.get_by_role('button', name='پاک کردن صف', exact=True).click()
        assert held
        with page.expect_response(lambda response: '/api/initial-items?file=' in response.url and 'pending-open.md' in response.url) as delayed:
            held[0].continue_()
        delayed.value.finished()
        page.wait_for_timeout(100)
        expect(rows).to_have_count(0)
        report['pendingOpenCannotResurrectClearedQueue'] = True
        assert page.request.get(args.url + '/api/initial-items').json()['items'] == []
        page.request.post(args.url + '/api/open-file', data={'path':str(linked)})
        expect(rows).to_have_count(1)
        frame.get_by_role('heading', name='سند پیوندی', exact=True).wait_for()
        page.keyboard.press('F5')
        frame.get_by_role('heading', name='سند پیوندی', exact=True).wait_for()
        expect(rows).to_have_count(1)
        report['clearAndRefreshNeverResurrectOldFiles'] = True

        page.get_by_role('tab', name='کنسول و گزارش‌ها').click()
        page.route('**/api/pick-files?**', lambda route: route.fulfill(json={
            'files':[{'name':document.name,'path':str(document),'sizeBytes':document.stat().st_size,'sizeStr':'1 KB'}], 'cancelled':False}))
        page.keyboard.press('Control+o')
        expect(rows).to_have_count(2)
        frame.get_by_role('heading', name='سند روزمره', exact=True).wait_for()
        expect(page.get_by_role('tab', name='پیش‌نمایش سند')).to_have_attribute('aria-selected', 'true')
        report['openShortcutFromConsoleShowsDocument'] = True
        rows.filter(has_text=document.name).click()
        page.keyboard.press('Delete')
        expect(rows).to_have_count(1)
        frame.get_by_role('heading', name='سند پیوندی', exact=True).wait_for()

        # Watch mode must stream output and actually stop, rather than leaving a hidden process.
        page.get_by_role('button', name='DOCX (Word)', exact=True).click()
        page.get_by_label('حالت پایش زنده (Watch Mode)', exact=True).check()
        page.get_by_role('button', name='شروع تبدیل اسناد', exact=True).click()
        page.get_by_text('Watching for changes', exact=False).first.wait_for(timeout=20000)
        page.get_by_role('button', name='توقف تبدیل', exact=True).click()
        expect(page.get_by_role('button', name='شروع تبدیل اسناد', exact=True)).to_be_enabled(timeout=10000)
        expect(page.get_by_text('عملیات تبدیل توسط کاربر لغو گردید.', exact=True)).to_be_visible()
        report['watchModeStreamsAndStops'] = True
        with zipfile.ZipFile(linked.with_suffix('.docx')) as archive:
            assert 'سند پیوندی' in archive.read('word/document.xml').decode('utf-8')
        report['realDocxConversionThroughDesktopBridge'] = True
        assert page.request.get(args.url + '/api/health').json()['rendererPid'] == renderer_pid
        report['oneRendererReusedAcrossDocuments'] = True

        # Every existing workbench panel is still present.
        for label in ("صف فایل‌ها", "شروع تبدیل اسناد", "کنسول و گزارش‌ها"):
            assert page.get_by_text(label, exact=False).count() > 0
        report["existingWorkbenchPreserved"] = True
        assert not errors, errors
        assert not remote, remote
        report["remoteRequests"] = len(remote)
        report["pageErrors"] = errors
        # Closing the last window must also stop a continuous watch.
        watching = page.get_by_text('Watching for changes', exact=False)
        before_watch = watching.count()
        page.get_by_role('button', name='شروع تبدیل اسناد', exact=True).click()
        expect(watching).to_have_count(before_watch + 1, timeout=20000)
        report['windowCloseWithActiveWatchTested'] = True

        renderer_handle = None
        if sys.platform == 'win32':
            kernel = ctypes.windll.kernel32
            kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
            kernel.OpenProcess.restype = ctypes.c_void_p
            kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
            kernel.CloseHandle.argtypes = [ctypes.c_void_p]
            renderer_handle = kernel.OpenProcess(0x00100000, False, renderer_pid)
            assert renderer_handle
        browser.close()
    if server is not None:
        for _ in range(120):
            if server.poll() is not None:
                break
            time.sleep(.1)
        assert server.poll() == 0, "Production server stayed alive after the last window closed"
        report["productionIdleExit"] = True
        if renderer_handle:
            assert kernel.WaitForSingleObject(renderer_handle, 5000) == 0, 'Preview worker outlived its server'
            kernel.CloseHandle(renderer_handle)
            report['previewWorkerExitsWithServer'] = True
    (output / "desktop-verification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
