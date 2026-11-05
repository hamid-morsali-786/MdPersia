"""Exercise real settings behavior in the existing desktop build with a fresh Edge profile."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    root = Path(__file__).resolve().parent.parent
    output = root / "output" / "settings"
    output.mkdir(parents=True, exist_ok=True)
    source = output / "reading.md"
    source.write_text("# سند مطالعه\n\n```js\n" + "const longLine = '" + "example" * 70 + "';\n```\n\n" + "\n\n".join("متن فارسی و English برای بررسی محل مطالعه و تنظیمات خواندن." for _ in range(60)), encoding="utf-8")
    other = output / "another.md"
    other.write_text("# سند دوم\n\nیک سند مستقل برای بررسی صف.", encoding="utf-8")
    base = "http://127.0.0.1:1422"
    server = subprocess.Popen(["node", "dist/desktop-server.mjs", "--port", "1422"], cwd=root / "desktop-tauri",
                              env={**os.environ, "PYTHON_EXECUTABLE": sys.executable}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    report = {}
    try:
        for _ in range(100):
            try:
                urlopen(base + "/api/health", timeout=.1).close()
                break
            except OSError:
                time.sleep(.1)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()
            errors, requests = [], []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("request", lambda request: requests.append(request.url))
            page.goto(base + "/?file=" + quote(str(source)))
            frame = page.frame_locator("iframe")
            expect(frame.get_by_role("heading", name="سند مطالعه", exact=True)).to_be_visible()
            rows = page.locator("tbody tr")
            gear = page.get_by_role("button", name="تنظیمات برنامه", exact=True)
            theme = page.get_by_role("button", name="تغییر تم", exact=True)
            assert abs(gear.bounding_box()["x"] - theme.bounding_box()["x"]) < 50
            assert not any("SettingsDialog-" in url for url in requests)
            gear.click()
            dialog = page.get_by_role("dialog", name="تنظیمات برنامه", exact=True)
            expect(dialog).to_be_visible()
            assert any("SettingsDialog-" in url for url in requests)
            report["settingsLoadedOnlyWhenOpened"] = True
            for step in range(35):
                page.keyboard.press("Tab")
                assert dialog.evaluate("el => el.contains(document.activeElement)"), {"step": step, "active": page.evaluate("document.activeElement.outerHTML.slice(0, 500)")}
            page.keyboard.press("Delete")
            expect(rows).to_have_count(1)
            page.keyboard.press("Escape")
            expect(dialog).to_have_count(0)
            expect(gear).to_be_focused()
            frame.get_by_role("heading", name="سند مطالعه").click()
            page.keyboard.press("Control+,")
            expect(dialog).to_be_visible()
            report["modalKeyboardContainmentEscapeAndFocusReturn"] = True
            before_previews = sum("/api/preview-html?" in url for url in requests)

            dialog.get_by_role("radio", name="روشن", exact=True).check()
            expect(page.locator("html")).not_to_have_class("dark")
            page.emulate_media(color_scheme="dark")
            dialog.get_by_role("radio", name="همگام با سیستم", exact=True).check()
            expect(page.locator("html")).to_have_class("dark")
            page.emulate_media(color_scheme="light")
            expect(page.locator("html")).not_to_have_class("dark")
            report["themeFollowsSystemChanges"] = True
            for label, presses in [("بزرگ‌نمایی مطالعه", 7), ("فاصلهٔ خطوط", 8)]:
                slider = dialog.get_by_role("slider", name=label, exact=True)
                slider.focus()
                page.keyboard.press("Home")
                for _ in range(presses):
                    page.keyboard.press("ArrowRight")
            expect(dialog.get_by_role("slider", name="بزرگ‌نمایی مطالعه")).to_have_value("130")
            expect(dialog.get_by_role("slider", name="فاصلهٔ خطوط")).to_have_value("2.2")
            dialog.get_by_role("radio", name="تمام عرض", exact=True).check()
            dialog.get_by_role("switch", name="شکستن خطوط طولانی کد", exact=True).check()
            appearance = frame.locator(".markdown-body").evaluate("el => ({ width: getComputedStyle(el).maxWidth, leading: parseFloat(getComputedStyle(el).lineHeight) / parseFloat(getComputedStyle(el).fontSize), zoom: getComputedStyle(document.documentElement).zoom, code: getComputedStyle(document.querySelector('pre')).whiteSpace })")
            assert appearance["width"] == "none" and abs(appearance["leading"] - 2.2) < .01, appearance
            assert appearance["zoom"] == "1.3" and appearance["code"] == "pre-wrap", appearance
            assert before_previews == sum("/api/preview-html?" in url for url in requests)
            report["readingControlsApplyWithoutRerenderingDocument"] = True
            dialog.get_by_role("switch", name="نمایش خودکار فایل تازه", exact=True).uncheck()
            dialog.get_by_role("switch", name="نمایش کنسول هنگام تبدیل", exact=True).uncheck()
            dialog.get_by_role("switch", name="تأیید پیش از پاک‌کردن صف", exact=True).check()
            dialog.get_by_role("radio", name="Word", exact=True).check()
            dialog.get_by_role("button", name="تمام", exact=True).click()
            page.request.post(base + "/api/open-file", data={"path": str(other)})
            expect(rows).to_have_count(2)
            expect(frame.get_by_role("heading", name="سند مطالعه", exact=True)).to_be_visible()
            report["backgroundOpenPreservesCurrentReading"] = True
            inner = page.locator("iframe").element_handle().content_frame()
            inner.evaluate("window.scrollTo(0, 800)")
            page.wait_for_timeout(100)
            rows.filter(has_text=other.name).click()
            expect(frame.get_by_role("heading", name="سند دوم", exact=True)).to_be_visible()
            rows.filter(has_text=source.name).click()
            expect(frame.get_by_role("heading", name="سند مطالعه", exact=True)).to_be_visible()
            page.wait_for_timeout(200)
            assert page.locator("iframe").element_handle().content_frame().evaluate("window.scrollY") > 700
            gear.click()
            dialog.get_by_role("switch", name="حفظ محل مطالعهٔ هر سند", exact=True).uncheck()
            dialog.get_by_role("button", name="تمام", exact=True).click()
            rows.filter(has_text=other.name).click()
            expect(frame.get_by_role("heading", name="سند دوم", exact=True)).to_be_visible()
            rows.filter(has_text=source.name).click()
            expect(frame.get_by_role("heading", name="سند مطالعه", exact=True)).to_be_visible()
            page.wait_for_timeout(200)
            assert page.locator("iframe").element_handle().content_frame().evaluate("window.scrollY") == 0
            report["rememberReadingPositionCanBeDisabled"] = True

            page.get_by_role("button", name="شروع تبدیل اسناد", exact=True).click()
            expect(page.get_by_role("tab", name="پیش‌نمایش سند", exact=True)).to_have_attribute("aria-selected", "true")
            expect(page.get_by_role("button", name="شروع تبدیل اسناد", exact=True)).to_be_enabled(timeout=20000)
            assert source.with_suffix(".docx").is_file() and other.with_suffix(".docx").is_file()
            report["conversionCanKeepPreviewOpen"] = True
            page.get_by_label("حالت پایش زنده (Watch Mode)", exact=True).check()
            page.get_by_role("button", name="شروع تبدیل اسناد", exact=True).click()
            gear.click()
            expect(dialog.get_by_role("switch", name="به خاطر سپردن تنظیمات تبدیل", exact=True)).to_be_disabled()
            expect(dialog.get_by_role("radio", name="Word", exact=True)).to_be_disabled()
            expect(dialog.get_by_role("button", name="بازگردانی تنظیمات پیش‌فرض", exact=True)).to_be_disabled()
            dialog.get_by_role("switch", name="شکستن خطوط طولانی کد", exact=True).uncheck()
            assert frame.locator("pre").evaluate("el => getComputedStyle(el).whiteSpace") == "pre"
            dialog.get_by_role("button", name="تمام", exact=True).click()
            page.get_by_role("button", name="توقف تبدیل", exact=True).click()
            expect(page.get_by_role("button", name="شروع تبدیل اسناد", exact=True)).to_be_enabled(timeout=10000)
            report["conversionPreferencesDisabledWhileReadingRemainsAdjustable"] = True

            page.get_by_role("button", name="پاک کردن صف", exact=True).click()
            confirm = page.get_by_role("dialog", name="پاک‌کردن صف", exact=True)
            expect(confirm).to_be_visible()
            page.keyboard.press("Escape")
            expect(rows).to_have_count(2)
            page.get_by_role("button", name="پاک کردن صف", exact=True).click()
            confirm.get_by_role("button", name="پاک‌کردن همهٔ صف", exact=True).click()
            expect(rows).to_have_count(0)
            page.request.post(base + "/api/open-file", data={"path": str(source)})
            expect(frame.get_by_role("heading", name="سند مطالعه", exact=True)).to_be_visible()
            report["clearConfirmationAndFirstOpenWithoutAutofocus"] = True
            page.get_by_label("حالت پایش زنده (Watch Mode)", exact=True).check()
            page.reload()
            expect(rows).to_have_count(0)
            expect(page.get_by_label("حالت پایش زنده (Watch Mode)", exact=True)).not_to_be_checked()
            gear.click()
            expect(dialog.get_by_role("radio", name="Word", exact=True)).to_be_checked()
            expect(dialog.get_by_role("slider", name="بزرگ‌نمایی مطالعه")).to_have_value("130")
            expect(dialog.get_by_role("switch", name="نمایش خودکار فایل تازه", exact=True)).not_to_be_checked()
            report["preferencesPersistWithoutGhostFilesOrWatch"] = True
            dialog.get_by_role("switch", name="به خاطر سپردن تنظیمات تبدیل", exact=True).uncheck()
            page.reload()
            gear.click()
            expect(dialog.get_by_role("radio", name="PDF", exact=True)).to_be_checked()
            expect(dialog.get_by_role("slider", name="بزرگ‌نمایی مطالعه")).to_have_value("130")
            report["conversionPersistenceOptOutRespected"] = True
            dialog.get_by_role("button", name="بازنشانی عرض پنل‌ها", exact=True).click()
            expect(dialog.locator("footer [role=status]")).to_contain_text("عرض پنل‌ها")
            assert page.locator("main > section").first.evaluate("el => el.style.width") == "380px"
            dialog.get_by_role("button", name="تمام", exact=True).click()
            page.request.post(base + "/api/open-file", data={"path": str(source)})
            expect(rows).to_have_count(1)
            gear.click()
            dialog.get_by_role("button", name="بازگردانی تنظیمات پیش‌فرض", exact=True).click()
            expect(dialog.get_by_role("slider", name="بزرگ‌نمایی مطالعه")).to_have_value("100")
            expect(rows).to_have_count(1)
            expect(dialog.locator("footer [role=status]")).to_contain_text("اسناد صف حفظ شدند")
            report["resetPreferencesAndLayoutKeepDocuments"] = True

            for mode in ("dark", "light"):
                dialog.get_by_role("radio", name="تاریک" if mode == "dark" else "روشن", exact=True).check()
                dialog.locator(".app-dialog-body").evaluate("el => el.scrollTop = 0")
                page.screenshot(path=str(output / f"settings-{mode}.png"))
            for width, height in ((720, 520), (414, 740), (320, 640), (280, 640)):
                page.set_viewport_size({"width": width, "height": height})
                bounds = dialog.bounding_box()
                assert bounds["x"] >= 0 and bounds["x"] + bounds["width"] <= width + 1
                assert bounds["y"] >= 0 and bounds["y"] + bounds["height"] <= height + 1
                assert dialog.evaluate("el => el.scrollWidth <= el.clientWidth")
                expect(dialog.get_by_role("button", name="تمام", exact=True)).to_be_in_viewport()
            page.screenshot(path=str(output / "settings-narrow.png"))
            report["responsiveDialogWidths"] = [720, 414, 320, 280]
            report["pageErrors"] = errors
            assert not errors, errors
            failed_context = browser.new_context()
            failed_context.add_init_script("localStorage.setItem('mdpersia.preferences.v1', '{broken'); Storage.prototype.setItem = function() { throw new Error('storage unavailable'); };")
            failed = failed_context.new_page()
            failed.goto(base + "/?file=" + quote(str(source)))
            expect(failed.frame_locator("iframe").get_by_role("heading", name="سند مطالعه", exact=True)).to_be_visible()
            failed.get_by_role("button", name="تنظیمات برنامه", exact=True).click()
            expect(failed.get_by_role("dialog").locator("footer [role=status]")).to_contain_text("ذخیره ممکن نشد")
            report["unavailableStorageDoesNotBlockReading"] = True
            failed_context.close()
            browser.close()
        server.wait(timeout=10)
        assert server.returncode == 0
        report["serverExitsAfterWindowsClose"] = True
        (output / "settings-verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        if server.poll() is None:
            server.terminate()
            server.wait(timeout=5)


if __name__ == "__main__":
    main()
