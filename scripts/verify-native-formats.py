"""Verify new document formats in the installed Windows app with its real engines.

Use an isolated WebView2 profile and an explicit local conversion pack. The
browser and native programs run without Python or Node on their PATH.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import time
from urllib.request import urlopen
from zipfile import ZipFile

from playwright.sync_api import expect, sync_playwright

from fa_md_pdf.formats import DOCUMENT_EXTENSIONS


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", type=Path)
    parser.add_argument("--conversion-pack", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    executable = args.executable.resolve(strict=True)
    package = args.conversion_pack.resolve(strict=True)
    output = args.output.resolve()
    project_output = Path(__file__).resolve().parents[1] / "output"
    if project_output not in output.parents or output.exists():
        raise ValueError("Use a fresh directory under the project's output directory.")
    output.mkdir(parents=True)
    documents = []
    originals = {}
    for extension in DOCUMENT_EXTENSIONS:
        name = extension[1:]
        source = output / ("سند-" + name + extension.upper())
        content = f"# سند {name}\n\n**متن فارسی** و English و $x^2$\n"
        if extension == ".mdx":
            content = ("import Card from './unavailable.jsx'\n\n"
                       "export const value = globalThis.__mdxExecuted = 1\n\n"
                       + content + "\n<Card value={value} />\n\n"
                       "[سند بعدی](سند-mkdn.MKDN)\n\n"
                       "```mermaid\ngraph LR\nA[شروع]-->B[پایان]\n```\n")
        raw = content.replace("\n", "\r\n").encode("utf-8-sig")
        source.write_bytes(raw)
        originals[str(source)] = raw
        documents.append(source)
    (output / "unsupported.txt").write_text("not a Markdown input", encoding="utf8")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = {**os.environ, "PATH": os.path.join(os.environ["SYSTEMROOT"], "System32"),
           "WEBVIEW2_USER_DATA_FOLDER": str(output / "profile"),
           "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS": f"--remote-debugging-port={port}"}
    for key in ("PYTHONHOME", "PYTHONPATH", "PLAYWRIGHT_BROWSERS_PATH"):
        env.pop(key, None)
    started = time.monotonic()
    proc = subprocess.Popen([str(executable), str(documents[0])], cwd=output, env=env)
    report = {"os": platform.platform(), "executable": str(executable),
              "executableSha256": hashlib.file_digest(executable.open("rb"), "sha256").hexdigest(),
              "restrictedPath": env["PATH"]}
    page_errors = []
    try:
        with sync_playwright() as playwright:
            deadline = time.monotonic() + 40
            while True:
                try:
                    urlopen(f"http://127.0.0.1:{port}/json/version", timeout=.3).close()
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError("The installed native window did not start.")
                    time.sleep(.1)
            browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
            context = browser.contexts[0]
            context.set_offline(True)
            page = context.pages[0]
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            frame = page.frame_locator("iframe")
            expect(frame.get_by_role("heading", name="سند md", exact=True)).to_be_visible()
            report["firstDocumentSeconds"] = round(time.monotonic() - started, 3)
            initial = page.evaluate("window.__TAURI_INTERNALS__.invoke('conversion_runtime_status')")
            report["initialRuntime"] = initial
            for count, source in enumerate(documents[1:], start=2):
                subprocess.run([str(executable), str(source)], cwd=output, env=env,
                               check=True, timeout=15)
                expect(frame.get_by_role("heading", name="سند " + source.suffix[1:].lower(),
                                         exact=True)).to_be_visible()
                expect(page.locator("tbody tr")).to_have_count(count)
            subprocess.run([str(executable), str(documents[-1])], env=env, check=True, timeout=15)
            expect(page.locator("tbody tr")).to_have_count(len(documents))
            report["allFormatsOpenAndAccumulateWithoutDuplicates"] = True
            expect(frame.get_by_role("note")).to_contain_text("پیش‌نمایش ایستای MDX")
            frame.locator(".mermaid svg").wait_for()
            assert frame.locator("math").count() == 1
            assert frame.locator("card").count() == 0
            assert frame.locator(".markdown-body").evaluate("el => window.__mdxExecuted") is None
            report["staticMdxMathAndMermaidWithoutExecutingComponents"] = True
            frame.get_by_role("link", name="سند بعدی").click()
            expect(frame.get_by_role("heading", name="سند mkdn", exact=True)).to_be_visible()
            expect(page.locator("tbody tr")).to_have_count(len(documents))
            page.locator("tbody tr").filter(has_text=documents[-1].name).click()
            expect(frame.get_by_role("heading", name="سند mdx", exact=True)).to_be_visible()
            page.get_by_role("button", name="ویرایش سند", exact=True).click()
            content = page.locator(".cm-content[contenteditable=true]")
            content.click()
            page.keyboard.press("Control+a")
            changed = originals[str(documents[-1])].decode("utf-8-sig").replace("\r\n", "\n")
            changed += "\nذخیرهٔ بومی فرمت تازه\n"
            page.keyboard.insert_text(changed)
            expect(frame.locator(".markdown-body")).to_contain_text("ذخیرهٔ بومی فرمت تازه")
            assert documents[-1].read_bytes() == originals[str(documents[-1])]
            page.keyboard.press("Control+s")
            expect(page.get_by_role("img", name="تغییرات ذخیره‌نشده", exact=True)).to_have_count(0)
            assert documents[-1].read_bytes() == changed.replace("\n", "\r\n").encode("utf-8-sig")
            originals[str(documents[-1])] = documents[-1].read_bytes()
            page.get_by_role("button", name="پایان ویرایش", exact=True).click()
            report["nativeLiveDraftAndSavePreserveBomCrLfAndMdxSource"] = True
            found = page.evaluate("""folderPath => window.__TAURI_INTERNALS__.invoke(
                'scan_folder', {folderPath, recursive: false})""", str(output))
            assert {item["name"] for item in found} == {source.name for source in documents}
            report["nativeFolderScanRecognizesTheWholeFamily"] = True
            if not initial["installed"]:
                installed = page.evaluate("""sourcePath => window.__TAURI_INTERNALS__.invoke(
                    'conversion_runtime_install', {sourcePath})""", str(package))
                assert installed["installed"] and installed["phase"] == "ready", installed
                report["localPackImportedThroughNativeVerifier"] = installed
            report["conversions"] = []
            for source in documents:
                formats = ("docx", "pdf") if source.suffix.lower() == ".mdx" else ("docx",)
                for output_format in formats:
                    target = source.with_suffix("." + output_format)
                    result = page.evaluate("""async ({source, target, format, id}) => {
                        const events = [];
                        const callback = window.__TAURI_INTERNALS__.transformCallback(raw => {
                            if (raw.message) events.push(raw.message);
                        });
                        const code = await window.__TAURI_INTERNALS__.invoke('run_conversion', {
                            id, args: [source, '--format', format, '--output', target],
                            events: '__CHANNEL__:' + callback
                        });
                        return {code, events};
                    }""", {"source": str(source), "target": str(target), "format": output_format,
                           "id": source.stem + "-" + output_format})
                    assert result["code"] == 0 and target.is_file(), result
                    if output_format == "docx":
                        with ZipFile(target) as archive:
                            assert "متن فارسی" in archive.read("word/document.xml").decode()
                    else:
                        assert target.read_bytes().startswith(b"%PDF-")
                    report["conversions"].append({"source": source.name, "format": output_format,
                                                   "bytes": target.stat().st_size, **result})
            assert all(Path(path).read_bytes() == raw for path, raw in originals.items())
            assert not page_errors, page_errors
            page.screenshot(path=str(output / "native-formats.png"))
            page.evaluate("void window.__TAURI_INTERNALS__.invoke('plugin:window|close', {label: 'main'})")
            proc.wait(timeout=15)
            report["nativeWindowClosedNormally"] = True
    finally:
        report["pageErrors"] = page_errors
        (output / "native-formats-report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8")
        if proc.poll() is None:
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
    print(json.dumps({"passed": True, "formats": len(documents),
                      "conversions": len(report["conversions"]), "report": str(output)}, indent=2))


if __name__ == "__main__":
    main()
