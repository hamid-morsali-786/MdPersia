"""Verify editing and actual disk writes through the same production desktop UI."""
from __future__ import annotations

import json
import os
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
    output = root / "output" / "editor"
    output.mkdir(parents=True, exist_ok=True)
    source, other, copy = (output / name for name in ("سند اصلی.md", "another.md", "saved-copy.md"))
    original = "# سند اصلی\r\n\r\n- Host: localhost برای اتصال\r\n\r\nEnglish paragraph.\r\n\r\n<!-- keep this comment -->\r\n\r\n```mermaid\r\ngraph LR\r\nA[شروع]-->B[پایان]\r\n```\r\n"
    source.write_bytes(original.encode("utf-8-sig"))
    other.write_text("# سند دوم\n\nمتن سند دوم.", encoding="utf-8")
    copy.unlink(missing_ok=True)
    base = "http://127.0.0.1:1423"
    server = subprocess.Popen(["node", "dist/desktop-server.mjs", "--port", "1423"], cwd=root / "desktop-tauri", env={**os.environ, "PYTHON_EXECUTABLE": sys.executable}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    report = {}
    try:
        for _ in range(100):
            try:
                urlopen(base + "/api/health", timeout=.1).close()
                break
            except OSError:
                time.sleep(.1)
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            errors, requests = [], []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("request", lambda request: requests.append(request.url))
            page.on("dialog", lambda dialog: dialog.accept())
            page.goto(base + "/?file=" + quote(str(source)))
            frame = page.frame_locator("iframe")
            frame.locator(".mermaid svg").wait_for(timeout=30000)
            assert not any("MarkdownEditor-" in url for url in requests)
            page.get_by_role("button", name="ویرایش سند", exact=True).click()
            content = page.locator(".cm-content[contenteditable=true]")
            expect(content).to_be_visible()
            assert any("MarkdownEditor-" in url for url in requests)
            report["editorLoadsOnDemandInsidePreview"] = True
            content.click()
            page.keyboard.press('Control+f')
            expect(page.locator('.cm-search')).to_be_visible()
            page.keyboard.press('Escape')
            expect(page.locator('.cm-search')).to_have_count(0)
            report['editorSearchOpensAndClosesWithKeyboard'] = True

            def replace(text):
                content.click()
                page.keyboard.press("Control+a")
                page.keyboard.insert_text(text)

            changed = original.replace("\r\n", "\n").replace("سند اصلی", "سند ویرایش‌شده") + "\nیک بند تازه با English و فارسی.\n"
            live = page.get_by_label('پیش‌نمایش زنده', exact=True)
            live.uncheck()
            preview_requests = sum('/api/preview-draft' in url for url in requests)
            replace(changed)
            page.wait_for_timeout(650)
            assert preview_requests == sum('/api/preview-draft' in url for url in requests)
            live.check()
            report['disablingLivePreviewStopsRenderingWhileTyping'] = True
            expect(frame.get_by_role("heading", name="سند ویرایش‌شده", exact=True)).to_be_visible(timeout=15000)
            assert source.read_bytes() == original.encode("utf-8-sig")
            frame.locator(".mermaid svg").wait_for(timeout=30000)
            expect(page.get_by_role("img", name="تغییرات ذخیره‌نشده", exact=True)).to_have_count(1)
            report["livePreviewUsesDraftWithoutWritingSource"] = True
            directions = content.locator(".cm-line").evaluate_all("els => els.filter(el => el.textContent.trim()).map(el => ({text: el.textContent, direction: getComputedStyle(el).direction}))")
            assert any(line["direction"] == "rtl" for line in directions if "سند" in line["text"]), directions
            assert any(line["direction"] == "ltr" for line in directions if "English paragraph" in line["text"]), directions
            report["persianAndEnglishLinesHaveIndependentDirections"] = True
            content.click()
            page.keyboard.press("Control+z")
            expect(content).to_contain_text("سند اصلی")
            page.keyboard.press("Control+Shift+z")
            expect(content).to_contain_text("سند ویرایش‌شده")
            page.get_by_role("button", name="پایان ویرایش", exact=True).click()
            page.get_by_role("button", name="ویرایش سند", exact=True).click()
            content.click()
            page.keyboard.press("Control+z")
            expect(content).to_contain_text("سند اصلی")
            page.keyboard.press("Control+Shift+z")
            expect(content).to_contain_text("سند ویرایش‌شده")
            report["undoRedoSurviveReadingMode"] = True
            page.keyboard.press("Control+s")
            expect(page.get_by_role("button", name="ذخیره سند", exact=True)).to_be_disabled()
            expect(page.get_by_role("img", name="تغییرات ذخیره‌نشده", exact=True)).to_have_count(0)
            assert source.read_bytes() == changed.replace("\n", "\r\n").encode("utf-8-sig")
            report["ctrlSSavesActualFilePreservingBomCrLfAndMarkdown"] = True
            replace(changed + '\nمیان‌بر با صفحه‌کلید فارسی\n')
            with page.expect_response(lambda response: response.url.endswith('/api/document') and response.request.post_data_json.get('operation') == 'save') as persisted:
                page.evaluate("window.dispatchEvent(new KeyboardEvent('keydown', {key:'س', code:'KeyS', ctrlKey:true, cancelable:true}))")
            persisted.value.finished()
            expect(page.get_by_role('button', name='ذخیره سند', exact=True)).to_be_disabled()
            expect(page.get_by_role('img', name='تغییرات ذخیره‌نشده', exact=True)).to_have_count(0)
            assert 'میان‌بر با صفحه‌کلید فارسی' in source.read_text(encoding='utf-8-sig')
            report['saveShortcutHandlesPersianKeyboardLayout'] = True

            source.write_bytes((changed + '\nتازهٔ بیرونی\n').replace('\n', '\r\n').encode('utf-8-sig'))
            page.request.post(base + '/api/open-file', data={'path': str(source)})
            expect(content).to_contain_text('تازهٔ بیرونی')
            report['reopeningCleanEditedDocumentReadsExternalChanges'] = True

            replace(changed + "\nپیش‌نویس الف\n")
            page.request.post(base + "/api/open-file", data={"path": str(other)})
            expect(content).to_contain_text("سند دوم")
            replace("# سند دوم\n\nپیش‌نویس ب")
            page.locator("tbody tr").filter(has_text=source.name).click()
            expect(content).to_contain_text("پیش‌نویس الف")
            page.locator("tbody tr").filter(has_text=other.name).click()
            expect(content).to_contain_text("پیش‌نویس ب")
            report["switchingDocumentsKeepsIndependentDrafts"] = True

            page.get_by_role("button", name="حذف انتخاب", exact=True).click()
            guard = page.get_by_role("dialog", name="تغییرات ذخیره‌نشده", exact=True)
            expect(guard).to_be_visible()
            guard.get_by_role("button", name="انصراف", exact=True).click()
            expect(page.locator("tbody tr")).to_have_count(2)
            page.get_by_role("button", name="حذف انتخاب", exact=True).click()
            guard.get_by_role("button", name="کنارگذاشتن تغییرات", exact=True).click()
            expect(page.locator("tbody tr")).to_have_count(1)
            assert other.read_text(encoding="utf-8") == "# سند دوم\n\nمتن سند دوم."
            report["removalAsksBeforeDiscardingAndNeverDeletesFile"] = True
            expect(content).to_contain_text("پیش‌نویس الف")
            source.write_bytes("# تغییر بیرونی\r\n".encode("utf-8-sig"))
            page.get_by_role("button", name="ذخیره سند", exact=True).click()
            expect(page.get_by_role("alert")).to_contain_text("فایل روی دیسک تغییر کرده")
            assert source.read_text(encoding="utf-8-sig").strip() == "# تغییر بیرونی"
            expect(content).to_contain_text("پیش‌نویس الف")
            report["externalConflictPreservesBothDiskAndDraft"] = True
            save_target = {"path": str(copy)}
            page.route("**/api/pick-save-file?**", lambda route: route.fulfill(json={"path": save_target['path'], "cancelled": False}))
            page.get_by_role("button", name="ذخیره با نام دیگر", exact=True).click()
            expect(page.locator("tbody tr").filter(has_text=copy.name)).to_have_count(1)
            expect(content).to_contain_text("پیش‌نویس الف")
            assert copy.read_text(encoding="utf-8") == changed + "\nپیش‌نویس الف\n"
            assert source.read_text(encoding="utf-8-sig").strip() == "# تغییر بیرونی"
            report["saveAsCreatesUtf8CopyAndSelectsItInQueue"] = True

            replacement = '# جایگزینی تأییدشده\n\nمتن جایگزین با رضایت کاربر.'
            replace(replacement)
            save_target['path'] = str(other)
            page.get_by_role('button', name='ذخیره با نام دیگر', exact=True).click()
            overwrite = page.get_by_role('dialog', name='جایگزینی فایل موجود', exact=True)
            expect(overwrite).to_be_visible()
            assert other.read_text(encoding='utf-8') == '# سند دوم\n\nمتن سند دوم.'
            other.write_text('# تغییر همزمان مقصد', encoding='utf-8')
            overwrite.get_by_role('button', name='ذخیره و جایگزینی', exact=True).click()
            expect(overwrite.get_by_role('alert')).to_contain_text('فایل روی دیسک تغییر کرده')
            assert other.read_text(encoding='utf-8') == '# تغییر همزمان مقصد'
            overwrite.get_by_role('button', name='انصراف', exact=True).click()
            page.get_by_role('button', name='ذخیره با نام دیگر', exact=True).click()
            overwrite.get_by_role('button', name='ذخیره و جایگزینی', exact=True).click()
            expect(page.locator('tbody tr').filter(has_text=other.name)).to_have_count(1)
            assert other.read_text(encoding='utf-8') == replacement
            copy = other
            report['overwriteRequiresConfirmationAndRechecksTargetRevision'] = True

            replace("# بازیابی\n\nپیش‌نویس بازیابی بعد از بازشدن دوباره")
            dump_recovery = """async () => { const db = await new Promise(resolve => {const r = indexedDB.open('mdpersia-edit-recovery', 1); r.onsuccess = () => resolve(r.result);}); return new Promise(resolve => {const r = db.transaction('drafts').objectStore('drafts').getAll(); r.onsuccess = () => resolve(r.result);}); }"""
            for _ in range(100):
                records = page.evaluate(dump_recovery)
                if any("بازیابی بعد" in record["text"] for record in records):
                    break
                page.wait_for_timeout(100)
            else:
                raise AssertionError("No committed recovery record for the current draft")
            page.reload()
            expect(page.locator("tbody tr")).to_have_count(0)
            page.request.post(base + "/api/open-file", data={"path": str(copy)})
            expect(page.locator("tbody tr").filter(has_text=copy.name)).to_have_count(1)
            page.get_by_role("button", name="ویرایش سند", exact=True).click()
            try:
                expect(content).to_contain_text("پیش‌نویس بازیابی بعد")
            except Exception:
                page.screenshot(path=str(output / "recovery-failure.png"))
                print(json.dumps({"errors": errors, "body": page.locator('body').inner_text()[-2200:]}, ensure_ascii=False))
                raise
            expect(page.get_by_text("پیش‌نویس محلی بازیابی شد؛ برای ثبت در فایل، ذخیره را بزنید.", exact=True)).to_be_visible()
            assert "بازیابی بعد" not in copy.read_text(encoding="utf-8")
            report["localRecoveryRequiresExplicitFileOpenAndNeverWritesAutomatically"] = True

            page.get_by_role("button", name="شروع تبدیل اسناد", exact=True).click()
            expect(guard).to_be_visible()
            expect(guard.get_by_role("button", name="کنارگذاشتن تغییرات", exact=True)).to_have_count(0)
            guard.get_by_role("button", name="انصراف", exact=True).click()
            report["conversionCannotSilentlyUseStaleDiskContent"] = True
            page.get_by_role('button', name='DOCX (Word)', exact=True).click()
            page.get_by_role('button', name='شروع تبدیل اسناد', exact=True).click()
            guard.get_by_role('button', name='ذخیره و ادامه', exact=True).click()
            expect(guard).to_have_count(0)
            expect(page.get_by_role('button', name='شروع تبدیل اسناد', exact=True)).to_be_enabled(timeout=30000)
            with zipfile.ZipFile(copy.with_suffix('.docx')) as archive:
                assert 'پیش‌نویس بازیابی بعد' in archive.read('word/document.xml').decode('utf-8')
            page.get_by_role('tab', name='پیش‌نمایش سند', exact=True).click()
            expect(content).to_be_visible()
            replace('# نسخهٔ موقتی برای بازخوانی')
            report['saveAndContinueConvertsTheEditedContentToRealDocx'] = True
            page.get_by_role("button", name="بازسازی پیش‌نمایش", exact=True).click()
            reload_dialog = page.get_by_role("dialog", name="بازخوانی نسخهٔ دیسک", exact=True)
            expect(reload_dialog).to_be_visible()
            reload_dialog.get_by_role("button", name="کنارگذاشتن تغییرات و بازخوانی", exact=True).click()
            expect(content).not_to_contain_text("نسخهٔ موقتی")
            expect(page.get_by_role("button", name="ذخیره سند", exact=True)).to_be_disabled()
            report["explicitReloadDiscardsOnlyAfterConfirmation"] = True

            malicious = '# سند امن\n\n<script>parent.window.__MDPERSIA_INJECTED=true</script>\n<img src="missing" onerror="parent.window.__MDPERSIA_INJECTED=true">\n\n```mermaid\ngraph LR\nA-->B\n```'
            replace(malicious)
            expect(frame.get_by_role("heading", name="سند امن", exact=True)).to_be_visible()
            frame.locator(".mermaid svg").wait_for(timeout=30000)
            assert page.evaluate("window.__MDPERSIA_INJECTED") is None
            report["markdownScriptsBlockedWhileOfflineMermaidStillWorks"] = True
            bad = page.request.post(base + "/api/document", headers={"Origin": "https://other.example"}, data={"operation": "save", "path": str(copy), "text": "BAD", "revision": None})
            assert bad.status == 403
            report["crossOriginWriteRequestsRejected"] = True
            replace('# برنامهٔ روزانه\n\nاین متن فارسی و English را در همین پنل ویرایش کنید.\n\n## کارهای امروز\n\n- [x] خواندن سند\n- [ ] ذخیرهٔ تغییرات\n\n**خروجی مرتب** با حفظ ساختار Markdown.\n\n```mermaid\ngraph LR\nA[نوشتن]-->B[پیش‌نمایش]\nB-->C[ذخیره]\n```\n')
            expect(frame.get_by_role('heading', name='برنامهٔ روزانه', exact=True)).to_be_visible()
            frame.locator('.mermaid svg').wait_for(timeout=30000)
            for dark in (True, False):
                if not dark:
                    page.get_by_role("button", name="تغییر تم", exact=True).click()
                expect(page.locator('header').first).to_have_css('background-color', 'rgb(17, 24, 39)' if dark else 'rgb(255, 255, 255)')
                page.locator('.cm-scroller').evaluate('el => el.scrollTop = 0')
                page.screenshot(path=str(output / ("editor-dark.png" if dark else "editor-light.png")))
            assert not errors, errors
            report["pageErrors"] = errors
            page.get_by_role("button", name="پاک کردن صف", exact=True).click()
            guard.get_by_role("button", name="کنارگذاشتن تغییرات", exact=True).click()
            expect(page.locator("tbody tr")).to_have_count(0)
            browser.close()
        server.wait(timeout=10)
        assert server.returncode == 0
        report["backendExitsAfterEditorCloses"] = True
        (output / "editor-verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        if server.poll() is None:
            server.terminate()
            server.wait(timeout=5)


if __name__ == "__main__":
    main()
