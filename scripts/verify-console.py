"""Exercise the actual console, exports, and watch phases in the production desktop UI."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    root = Path(__file__).resolve().parent.parent
    output = root / "output/playwright/console"
    output.mkdir(parents=True, exist_ok=True)
    good, missing = output / "گزارش روزانه.md", output / "missing-source.md"
    good.write_text(
        "# گزارش روزانه\n\nمتن فارسی و English برای آزمون گزارش تبدیل.", encoding="utf-8"
    )
    missing.write_text("# Source removed after opening", encoding="utf-8")
    base = "http://127.0.0.1:1425"
    server = subprocess.Popen(
        ["node", "dist/desktop-server.mjs", "--port", "1425"],
        cwd=root / "desktop-tauri",
        env={**os.environ, "PYTHON_EXECUTABLE": sys.executable},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    report = {}
    try:
        for _ in range(100):
            try:
                urlopen(base + "/api/health", timeout=0.1).close()
                break
            except OSError:
                time.sleep(0.1)
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge", headless=True)
            context = browser.new_context(
                viewport={"width": 1600, "height": 1000},
                permissions=["clipboard-read", "clipboard-write"],
                accept_downloads=True,
            )
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(base + "/?file=" + quote(str(good)))
            page.frame_locator("iframe").get_by_role("heading", name="گزارش روزانه").wait_for()
            page.request.post(base + "/api/open-file", data={"path": str(missing)})
            expect(page.locator("tbody tr")).to_have_count(2)
            page.frame_locator("iframe").get_by_role(
                "heading", name="Source removed after opening"
            ).wait_for()
            missing.unlink()
            page.get_by_role("button", name="DOCX (Word)", exact=True).click()
            page.get_by_role("button", name="شروع تبدیل اسناد", exact=True).click()
            expect(
                page.get_by_text("فرآیند تبدیل پایان یافت: 1 موفق، 1 ناموفق.", exact=True)
            ).to_be_visible(timeout=30000)
            console = page.locator(".console-report")
            rows = console.locator(".report-row")
            expect(console.get_by_role("heading", name="گزارش فعالیت", exact=True)).to_be_visible()
            error_events = console.locator(".report-error").count()
            assert error_events >= 1
            expect(console.locator(".report-success")).to_have_count(1)
            expect(console.locator("details[open]")).to_have_count(0)
            console.locator("summary").first.click()
            expect(console.locator("pre").first).to_contain_text("fa-md-pdf")
            console.locator("summary").first.click()
            report["realSuccessFailureAndCollapsibleCommands"] = True
            with zipfile.ZipFile(good.with_suffix(".docx")) as archive:
                assert "گزارش روزانه" in archive.read("word/document.xml").decode("utf-8")
            report["reportReflectsActualDocxOnDisk"] = True

            for theme in ["dark", "light"]:
                if page.locator("html").evaluate('el=>el.classList.contains("dark")') != (
                    theme == "dark"
                ):
                    page.get_by_role("button", name="تغییر تم", exact=True).click()
                page.mouse.move(1000, 20)
                page.wait_for_timeout(250)
                page.screenshot(path=str(output / f"after-{theme}.png"))
                console.screenshot(path=str(output / f"console-{theme}.png"))
            console.get_by_role("button", name=re.compile("^خطاها")).click()
            expect(rows).to_have_count(error_events)
            search = console.get_by_role("searchbox", name="جستجو در گزارش‌ها")
            search.fill("MISSING-SOURCE")
            expect(rows).to_have_count(error_events)
            page.get_by_role("tab", name="پیش‌نمایش سند", exact=True).click()
            page.get_by_role("tab", name="کنسول و گزارش‌ها", exact=True).click()
            expect(search).to_have_value("MISSING-SOURCE")
            expect(rows).to_have_count(error_events)
            report["filtersSearchAndTabStatePreserved"] = True
            console.get_by_role("button", name="کپی گزارش‌های نمایش‌داده‌شده", exact=True).click()
            expect(console.get_by_role("status").filter(has_text="کپی شدند")).to_be_visible()
            copied = page.evaluate("navigator.clipboard.readText()")
            assert "[ERROR]" in copied and missing.name in copied and good.name not in copied, (
                copied
            )
            with page.expect_download() as download_info:
                console.get_by_role("button", name="ذخیره گزارش", exact=True).click()
            downloaded = download_info.value
            assert downloaded.suggested_filename.endswith(".log")
            # The Windows clipboard normalizes line endings to CRLF.
            assert Path(downloaded.path()).read_text(encoding="utf-8-sig") == copied.replace(
                "\r\n", "\n"
            )
            report["clipboardAndDownloadRespectVisibleFilter"] = True
            search.fill("no event should match this literal text")
            expect(
                console.get_by_role("heading", name="رویدادی با این فیلتر پیدا نشد", exact=True)
            ).to_be_visible()
            expect(console.get_by_role("button", name="ذخیره گزارش", exact=True)).to_be_disabled()
            console.get_by_role("button", name="نمایش همهٔ رویدادها", exact=True).click()
            report["noMatchesAreRecoverable"] = True

            for width in [816, 480, 360, 320]:
                console.evaluate("(el,width) => el.style.width = `${width}px`", width)
                page.wait_for_timeout(100)
                assert console.evaluate("el => el.scrollWidth <= el.clientWidth"), width
                assert console.locator(".report-scroll").evaluate(
                    "el => el.scrollWidth <= el.clientWidth"
                ), width
                expect(
                    console.get_by_role("button", name="ذخیره گزارش", exact=True)
                ).to_be_in_viewport()
            console.screenshot(path=str(output / "console-narrow.png"))
            console.evaluate('el => el.style.removeProperty("width")')
            report["consoleWidthsWithoutOverflow"] = [816, 480, 360, 320]

            page.get_by_role("button", name="پاک کردن صف", exact=True).click()
            console.get_by_role("button", name="پاکسازی کنسول", exact=True).click()
            expect(
                console.get_by_role("heading", name="هنوز گزارشی ثبت نشده است", exact=True)
            ).to_be_visible()
            expect(console.get_by_role("button", name="پاکسازی کنسول", exact=True)).to_be_disabled()
            assert good.exists() and good.with_suffix(".docx").exists()
            report["clearingLogsKeepsFiles"] = True
            page.request.post(base + "/api/open-file", data={"path": str(good)})
            page.frame_locator("iframe").get_by_role(
                "heading", name="گزارش روزانه", exact=True
            ).wait_for()
            page.get_by_role("tab", name="پیشرفته", exact=True).click()
            # The real engine emits enough verbose output to exercise scrolling.
            page.get_by_label(re.compile("Verbose|لاگ|جزئیات")).check()
            page.get_by_label("حالت پایش زنده (Watch Mode)", exact=True).check()
            page.get_by_role("button", name="شروع تبدیل اسناد", exact=True).click()
            expect(console.get_by_text("پایش زنده فعال است", exact=True)).to_be_visible(
                timeout=30000
            )
            expect(page.locator("tbody tr").get_by_text("پایش زنده", exact=True)).to_be_visible()
            expect(
                console.get_by_role("status").filter(has_text="در انتظار تغییر فایل")
            ).to_be_visible()
            expect(page.locator("footer").last).not_to_contain_text("0%")
            report["watchIsExplicitWaitingRatherThanStuckProgress"] = True
            expect(page.locator("header").first).not_to_contain_text("در حال پردازش")
            scroller = console.locator(".report-scroll")
            assert scroller.evaluate("el => el.scrollHeight > el.clientHeight + 50")
            scroller.evaluate("el => el.scrollTop = 0")
            expect(
                console.get_by_role("button", name="رفتن به تازه‌ترین‌ها", exact=True)
            ).to_have_attribute("aria-pressed", "false")
            before = rows.count()
            good.write_text("# گزارش روزانه\n\nویرایش دوم برای پایش زنده.", encoding="utf-8")
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                page.wait_for_timeout(200)
                try:
                    with zipfile.ZipFile(good.with_suffix(".docx")) as archive:
                        if "ویرایش دوم" in archive.read("word/document.xml").decode("utf-8"):
                            break
                except (OSError, zipfile.BadZipFile):
                    # The writer may be between ZIP records while rebuilding.
                    continue
            else:
                raise AssertionError("Watch did not rebuild the actual output")
            expect(console.get_by_text("پایش زنده فعال است", exact=True)).to_be_visible()
            assert rows.count() > before
            assert scroller.evaluate("el => el.scrollTop < 32")
            console.get_by_role("button", name="رفتن به تازه‌ترین‌ها", exact=True).click()
            expect(
                console.get_by_role("button", name="دنبال‌کردن تازه‌ترین‌ها", exact=True)
            ).to_have_attribute("aria-pressed", "true")
            assert scroller.evaluate("el => el.scrollHeight - el.clientHeight - el.scrollTop < 32")
            report["manualScrollPreservedDuringRealWatchRebuild"] = True
            page.mouse.move(1000, 20)
            page.screenshot(path=str(output / "watch-waiting.png"))
            console.get_by_role("button", name="توقف پایش", exact=True).click()
            expect(page.get_by_role("button", name="شروع تبدیل اسناد", exact=True)).to_be_enabled(
                timeout=10000
            )
            expect(console.get_by_text("پایش زنده فعال است", exact=True)).to_have_count(0)
            report["stopWatchClosesTheActualProcess"] = True
            page.evaluate(
                "Object.defineProperty(navigator, 'clipboard', {configurable:true,value:{writeText:async()=>{throw new Error('clipboard unavailable')}}})"
            )
            console.get_by_role("button", name="کپی گزارش‌های نمایش‌داده‌شده", exact=True).click()
            expect(
                console.get_by_text(
                    "کپی انجام نشد؛ می‌توانید گزارش را در فایل ذخیره کنید.", exact=True
                )
            ).to_be_visible()
            report["clipboardFailureIsTruthfulAndRecoverable"] = True
            report["pageErrors"] = errors
            assert not errors, errors
            browser.close()
        server.wait(timeout=10)
        report["serverExitsAfterWindowCloses"] = True
        (output / "verification.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        if server.poll() is None:
            server.terminate()
            server.wait(timeout=5)


if __name__ == "__main__":
    main()
