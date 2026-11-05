"""Verify the real Windows/pythonw launcher and concurrent opens of this same desktop UI.

Uses an isolated Edge profile and test port; does not close or modify personal browser windows.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    root = Path(__file__).resolve().parent.parent
    output = root / "output" / "windows-launch"
    output.mkdir(parents=True, exist_ok=True)
    port, debug_port = free_port(), free_port()
    base = f"http://localhost:{port}"
    docs = []
    for name in ("نخست", "دوم", "سوم"):
        file = output / f"فایل {name}.md"
        file.write_text(f"# سند {name}\n\nمتن فارسی و English برای آزمون مسیر واقعی باز کردن فایل.", encoding="utf-8")
        docs.append(file)
    env = {**os.environ, "PYTHONPATH": str(root / "src"),
           "MDPERSIA_GUI_PORT": str(port),
           "MDPERSIA_BROWSER_PROFILE": str(output / "profiles" / str(time.time_ns())),
           "MDPERSIA_BROWSER_DEBUG_PORT": str(debug_port)}
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    started = time.perf_counter()
    first = subprocess.Popen([str(pythonw), "-m", "mdpersia", "--gui", str(docs[0])], cwd=output, env=env)
    second = subprocess.Popen([str(pythonw), "-m", "mdpersia", "--gui", str(docs[1])], cwd=output, env=env)
    with sync_playwright() as playwright:
        deadline = time.monotonic() + 25
        while True:
            try:
                with urlopen(f"http://127.0.0.1:{debug_port}/json/version", timeout=.2):
                    break
            except OSError:
                if time.monotonic() > deadline:
                    raise AssertionError("The real launcher did not open its desktop window")
                time.sleep(.05)
        browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{debug_port}")
        pages = [page for context in browser.contexts for page in context.pages if f":{port}" in page.url]
        assert len(pages) == 1, [page.url for context in browser.contexts for page in context.pages]
        page = pages[0]
        page.wait_for_timeout(1000)
        from window_icon_probe import probe
        print(json.dumps({'actualWindowIcons': probe(output / 'window-icons')}), flush=True)
        frame = page.frame_locator("iframe")
        expect(frame.locator('.markdown-body')).to_be_visible()
        expect(page.get_by_text('در حال رندر پیش‌نمایش…', exact=True)).to_be_hidden()
        report = {"coldLaunchToReadableMs": round((time.perf_counter() - started) * 1000)}
        expect(page.locator('tbody tr')).to_have_count(2)
        assert first.wait(timeout=10) == second.wait(timeout=10) == 0
        report["concurrentColdOpensKeepBothFiles"] = True
        start = time.perf_counter()
        third = subprocess.Popen([str(pythonw), "-m", "mdpersia", "--gui", str(docs[2])], cwd=output, env=env)
        expect(frame.get_by_role('heading', name='سند سوم', exact=True)).to_be_visible()
        expect(page.locator('tbody tr')).to_have_count(3)
        report["warmLauncherToReadableMs"] = round((time.perf_counter() - start) * 1000)
        assert third.wait(timeout=10) == 0
        assert len([p for c in browser.contexts for p in c.pages if f":{port}" in p.url]) == 1
        report["warmOpenUsesOneWindow"] = True
        with urlopen(base + '/api/health') as response:
            health = json.load(response)
        report["mode"] = health["mode"]
        bounds = page.locator('iframe').bounding_box()
        assert bounds and bounds['x'] >= -1 and bounds['width'] >= 319, bounds
        report['previewIsFullyInsideWindow'] = True
        page.screenshot(path=str(output / "actual-launch-queue.png"))
        session = browser.new_browser_cdp_session()
        try:
            session.send('Browser.close')
        except Exception:
            pass
    for _ in range(100):
        try:
            with urlopen(base + '/api/health', timeout=.1):
                pass
        except OSError:
            report["backendExitsAfterClosingWindow"] = True
            break
        time.sleep(.1)
    assert report.get("backendExitsAfterClosingWindow")
    # Repeat after the complete app/backend exit using the now-existing browser profile.
    restarted = time.perf_counter()
    reopen = subprocess.Popen([str(pythonw), "-m", "mdpersia", "--gui", str(docs[0])], cwd=output, env=env)
    with sync_playwright() as playwright:
        deadline = time.monotonic() + 25
        while True:
            try:
                with urlopen(f"http://127.0.0.1:{debug_port}/json/version", timeout=.2):
                    break
            except OSError:
                if time.monotonic() > deadline:
                    raise AssertionError("The existing profile could not reopen")
                time.sleep(.05)
        browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{debug_port}")
        page = next(p for c in browser.contexts for p in c.pages if f":{port}" in p.url)
        expect(page.frame_locator('iframe').get_by_role('heading', name='سند نخست', exact=True)).to_be_visible()
        expect(page.get_by_text('در حال رندر پیش‌نمایش…', exact=True)).to_be_hidden()
        expect(page.locator('tbody tr')).to_have_count(1)
        report['reopenAfterFullExitWithExistingProfileMs'] = round((time.perf_counter() - restarted) * 1000)
        assert reopen.wait(timeout=10) == 0
        try:
            browser.new_browser_cdp_session().send('Browser.close')
        except Exception:
            pass
    (output / "launch-verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
