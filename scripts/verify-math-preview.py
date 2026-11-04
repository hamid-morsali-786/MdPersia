"""Exercise actual frozen reader and native MathML preview, with offline networking."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import time
from urllib.request import urlopen

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('app', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    fixture = root / 'tests/fixtures/math-bilingual.md'
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    env = {**os.environ, 'PATH': os.path.join(os.environ['SYSTEMROOT'], 'System32'),
           'WEBVIEW2_USER_DATA_FOLDER': str(out / 'profile'),
           'WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS': f'--remote-debugging-port={port} --no-first-run'}
    proc = subprocess.Popen([str(args.app.resolve() / 'MdPersia.exe'), str(fixture)], env=env)
    errors = []
    try:
        with sync_playwright() as p:
            deadline = time.monotonic() + 30
            while True:
                try:
                    urlopen(f'http://127.0.0.1:{port}/json/version', timeout=.3).close()
                    break
                except OSError:
                    assert time.monotonic() < deadline
                    time.sleep(.1)
            browser = p.chromium.connect_over_cdp(f'http://127.0.0.1:{port}')
            page = browser.contexts[0].pages[0]
            page.on('pageerror', lambda e: errors.append(str(e)))
            frame = page.frame_locator('iframe')
            frame.locator('math').nth(9).wait_for()
            browser.contexts[0].set_offline(True)
            assert frame.locator('math').count() == 10
            assert frame.locator('mfrac').count() == 8
            assert frame.locator('menclose').count() == 3
            assert frame.locator('.math-error').count() == 0
            assert frame.locator('math').first.evaluate('e=>getComputedStyle(e).direction') == 'ltr'
            # Hide optional output controls to give equations the normal reading width.
            close = page.get_by_role('button', name='پنهان‌کردن تنظیمات خروجی', exact=True)
            if close.is_visible():
                close.click()
            for mode in ('تاریک', 'روشن'):
                page.get_by_role('button', name='تنظیمات برنامه', exact=True).click()
                dialog = page.get_by_role('dialog', name='تنظیمات برنامه', exact=True)
                dialog.get_by_label(mode, exact=True).check()
                dialog.get_by_role('button', name='تمام', exact=True).click()
                frame.locator('math').nth(9).wait_for()
                frame.locator('h1').scroll_into_view_if_needed()
                page.screenshot(path=str(out / ('dark.png' if mode == 'تاریک' else 'light.png')))
                assert frame.locator('mfrac').first.bounding_box()['height'] > 25
            frame.locator('menclose').last.scroll_into_view_if_needed()
            page.screenshot(path=str(out / 'boxed-results.png'))
            assert not errors, errors
            page.evaluate('void window.__TAURI_INTERNALS__.invoke("plugin:window|close",{label:"main"})')
            proc.wait(timeout=15)
    finally:
        if proc.poll() is None:
            subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'], capture_output=True)
    report = {'actualNativeApp': True, 'offline': True, 'restrictedPath': env['PATH'],
              'equations': 10, 'fractions': 8, 'boxedResults': 3, 'pageErrors': errors}
    (out / 'report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
