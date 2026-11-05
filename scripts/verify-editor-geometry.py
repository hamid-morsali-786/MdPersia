"""Real pointer hit testing and tooltip placement in the shipped desktop UI."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright


PROBE = """(content, {word, fraction}) => {
  const view = content.cmTile.root.view;
  const line = [...content.querySelectorAll('.cm-line')].find(el => el.textContent.includes(word));
  const offset = line.textContent.indexOf(word) + word.length - 1;
  const walker = document.createTreeWalker(line, NodeFilter.SHOW_TEXT);
  let node, skipped = 0;
  while ((node = walker.nextNode())) {
    if (skipped + node.length > offset) break;
    skipped += node.length;
  }
  const range = document.createRange();
  range.setStart(node, offset - skipped); range.setEnd(node, offset - skipped + 1);
  const box = range.getBoundingClientRect();
  const x = box.left + box.width * fraction, y = (box.top + box.bottom) / 2;
  const source = view.state.doc.toString();
  const start = range.cloneRange(), end = range.cloneRange();
  start.collapse(true); end.collapse(false);
  const after = Math.abs(x - end.getBoundingClientRect().x) < Math.abs(x - start.getBoundingClientRect().x);
  const pos = source.indexOf(word) + word.length - 1 + (after ? 1 : 0);
  range.collapse(!after);
  const expected = range.getBoundingClientRect();
  return {x, y, pos, expectedX: expected.x, modelX: view.coordsAtPos(pos)?.left,
    hit: view.posAtCoords({x, y}), source, character: node.textContent[offset - skipped],
    direction: getComputedStyle(line).direction, bidi: getComputedStyle(line).unicodeBidi,
    editorDirection: getComputedStyle(content).direction, font: getComputedStyle(node.parentElement).font};
}"""


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", action="store_true")
    parser.add_argument(
        "--source",
        type=Path,
        help="Read a reproduction document; all typing stays in an isolated copy",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    output = root / "output" / "playwright" / "editor-hit-testing"
    output.mkdir(parents=True, exist_ok=True)
    document = output / "pointer-fixture.md"
    text = (
        "# MASTER SYSTEM PROMPT — LOSSLESS COMPETITION PROBLEM COMPILER & SOLVER-PROMPT ENGINEER\n\n"
        "You are a **Competition Problem Compiler and AI-Solver Prompt Engineer**.\n\n"
        "Your job is to edit the document yourself.\n\n"
        "متن فارسی با **Compiler** و نشانه‌گذاری English: متن بعدی.\n\n"
        "English paragraph with **wrapped characters** and a long description. " * 1
    )
    if args.source:
        source_bytes = args.source.read_bytes()
        document.write_bytes(source_bytes)
    else:
        document.write_text(text, encoding="utf-8")
    base = "http://127.0.0.1:1424"
    server = subprocess.Popen(
        ["node", "dist/desktop-server.mjs", "--port", "1424"],
        cwd=root / "desktop-tauri",
        env={**os.environ, "PYTHON_EXECUTABLE": sys.executable},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    report = {"baseline": args.baseline, "clicks": [], "tooltips": []}
    try:
        for _ in range(100):
            try:
                urlopen(base + "/api/health", timeout=0.1).close()
                break
            except OSError:
                time.sleep(0.1)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page(viewport={"width": 1600, "height": 1000})
            page_errors = []
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.on("dialog", lambda dialog: dialog.accept())
            page.goto(base + "/?file=" + quote(str(document)))
            page.get_by_role("button", name="ویرایش سند", exact=True).click()
            content = page.locator(".cm-content[contenteditable=true]")
            expect(content).to_be_visible()
            page.evaluate("document.fonts.ready")
            for width, font_scale in [(1600, 1), (1280, 1.25), (1920, 1.5), (1440, 0.8)]:
                # Exercise wrapping and fractional font metrics without scaling the
                # workbench's viewport units or clicking outside the visible editor.
                page.set_viewport_size({"width": width, "height": 1000})
                page.locator(".cm-editor").evaluate(
                    "(el, scale) => el.style.fontSize = `${14 * scale}px`", font_scale
                )
                page.wait_for_timeout(100)
                page.locator(".cm-scroller").evaluate("(el) => el.scrollTop = 53.2")
                words = ["Solver", "Compiler", "yourself"] + ([] if args.source else ["بعدی"])
                for word in words:
                    for fraction in [0.2, 0.8]:
                        measured = content.evaluate(PROBE, {"word": word, "fraction": fraction})
                        viewport = page.viewport_size
                        assert (
                            0 < measured["x"] < viewport["width"]
                            and 0 < measured["y"] < viewport["height"]
                        ), {key: value for key, value in measured.items() if key != "source"}
                        page.mouse.click(measured["x"], measured["y"])
                        expect(content).to_be_focused()
                        page.wait_for_timeout(50)
                        actual = content.evaluate(
                            "el => { const view=el.cmTile.root.view; const p=view.state.selection.main.head; const selection=window.getSelection(); const range=selection.getRangeAt(0); return {pos:p, cursor:view.coordsAtPos(p)?.left, nativeX:range.getBoundingClientRect().left, drawn:document.querySelector('.cm-cursor')?.getBoundingClientRect().left}; }"
                        )
                        source = measured.pop("source")
                        page.keyboard.insert_text("|")
                        inserted = content.evaluate(
                            "el => el.cmTile.root.view.state.doc.toString()"
                        )
                        actual["insertedCorrectly"] = (
                            inserted == source[: measured["pos"]] + "|" + source[measured["pos"] :]
                        )
                        page.keyboard.press("Control+z")
                        assert (
                            content.evaluate("el => el.cmTile.root.view.state.doc.toString()")
                            == source
                        )
                        report["clicks"].append(
                            {
                                "width": width,
                                "fontScale": font_scale,
                                "word": word,
                                "fraction": fraction,
                                **measured,
                                "actual": actual,
                            }
                        )
            page.locator(".cm-editor").evaluate("el => el.style.removeProperty('font-size')")
            page.set_viewport_size({"width": 1600, "height": 1000})
            if not args.baseline:
                assert content.evaluate("el => getComputedStyle(el).caretColor") not in [
                    "transparent",
                    "rgba(0, 0, 0, 0)",
                ]
                expect(page.locator(".cm-cursorLayer")).to_have_count(0)
                for fraction, key in [(0.2, "Delete"), (0.8, "Backspace")]:
                    point = content.evaluate(PROBE, {"word": "Solver", "fraction": fraction})
                    page.mouse.click(point["x"], point["y"])
                    page.keyboard.press(key)
                    deleted = point["pos"] - (1 if key == "Backspace" else 0)
                    assert (
                        content.evaluate("el => el.cmTile.root.view.state.doc.toString()")
                        == point["source"][:deleted] + point["source"][deleted + 1 :]
                    )
                    page.keyboard.press("Control+z")
                    assert (
                        content.evaluate("el => el.cmTile.root.view.state.doc.toString()")
                        == point["source"]
                    )
                point = content.evaluate(PROBE, {"word": "Solver", "fraction": 0.8})
                page.mouse.click(point["x"], point["y"])
                for _ in "Solver":
                    page.keyboard.press("Shift+ArrowLeft")
                page.get_by_role("button", name="پررنگ (Ctrl+B)", exact=True).click()
                start, end = point["pos"] - len("Solver"), point["pos"]
                assert (
                    content.evaluate("el => el.cmTile.root.view.state.doc.toString()")
                    == point["source"][:start] + "**Solver**" + point["source"][end:]
                )
                page.keyboard.press("Control+z")
                assert (
                    content.evaluate("el => el.cmTile.root.view.state.doc.toString()")
                    == point["source"]
                )
                report["nativeSelectionSurvivesToolbarClick"] = True
                report["backspaceAndDeleteAtClickedCharacter"] = True
            page.mouse.move(800, 20)
            for label in ["پررنگ (Ctrl+B)", "مورب (Ctrl+I)", "جستجو در متن (Ctrl+F)"]:
                page.get_by_role("button", name=label, exact=True).hover()
                tip = page.get_by_role("tooltip")
                expect(tip).to_be_visible()
                samples = []
                for _ in range(9):
                    samples.append(tip.bounding_box())
                    page.wait_for_timeout(20)
                report["tooltips"].append({"label": label, "samples": samples})
                if not args.baseline:
                    expect(tip).to_have_count(1)
                    assert (
                        max(box["x"] for box in samples) - min(box["x"] for box in samples) < 1
                    ), samples
                    assert (
                        max(box["y"] for box in samples) - min(box["y"] for box in samples) < 1
                    ), samples
                    button = page.get_by_role("button", name=label, exact=True)
                    assert (
                        tip.get_attribute("id") in button.get_attribute("aria-describedby").split()
                    )
                    assert not button.get_attribute("title")
                page.mouse.move(800, 20)
                expect(tip).to_have_count(0)
            if not args.baseline:
                bold = page.get_by_role("button", name="پررنگ (Ctrl+B)", exact=True)
                bold.focus()
                page.keyboard.press("Escape")
                page.wait_for_timeout(180)
                expect(page.get_by_role("tooltip")).to_have_count(0)
                bold.evaluate("el => el.blur()")
                bold.focus()
                expect(page.get_by_role("tooltip")).to_be_visible()
                page.keyboard.press("Escape")
                expect(page.get_by_role("tooltip")).to_have_count(0)
                bold.hover()
                expect(page.get_by_role("tooltip")).to_be_visible()
                page.evaluate('window.dispatchEvent(new Event("scroll"))')
                expect(page.get_by_role("tooltip")).to_have_count(0)
                # An icon at the top-left must fall below and remain inside the window.
                theme = page.get_by_role("button", name="تغییر تم", exact=True)
                theme.hover()
                expect(page.get_by_role("tooltip")).to_be_visible()
                box = page.get_by_role("tooltip").bounding_box()
                assert box["x"] >= 8 and box["y"] >= 8 and box["x"] + box["width"] <= 1592
                report["viewportEdgeTooltip"] = box
                page.mouse.move(800, 20)
                for mode in ["dark", "light"]:
                    if page.locator("html").evaluate('el => el.classList.contains("dark")') != (
                        mode == "dark"
                    ):
                        theme.click()
                    bold.hover()
                    expect(page.get_by_role("tooltip")).to_be_visible()
                    page.wait_for_timeout(180)
                    page.screenshot(path=str(output / f"after-{mode}.png"))
                    page.mouse.move(800, 20)
                    expect(page.get_by_role("tooltip")).to_have_count(0)
                    point = content.evaluate(PROBE, {"word": "Solver", "fraction": 0.8})
                    page.mouse.click(point["x"], point["y"])
                    expect(content).to_be_focused()
                    page.screenshot(path=str(output / f"caret-{mode}.png"), caret="initial")
                # Pending hover timers must not resurrect a tooltip after pointer leave.
                bold.hover()
                page.mouse.move(800, 20)
                page.wait_for_timeout(200)
                expect(page.get_by_role("tooltip")).to_have_count(0)
            page.screenshot(path=str(output / ("before.png" if args.baseline else "after.png")))
            browser.close()
        server.wait(timeout=10)
        if args.source:
            assert args.source.read_bytes() == source_bytes, (
                "The original reproduction document changed"
            )
        report["failures"] = [
            click
            for click in report["clicks"]
            if click["pos"] != click["actual"]["pos"]
            or not click["actual"]["insertedCorrectly"]
            or abs(click["expectedX"] - click["actual"]["cursor"]) > 2
            or abs(click["expectedX"] - click["actual"]["nativeX"]) > 2
        ]
        report["pageErrors"] = page_errors
        (output / ("baseline.json" if args.baseline else "verification.json")).write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    "clicks": len(report["clicks"]),
                    "failedClicks": report["failures"],
                    "tooltips": len(report["tooltips"]),
                    "pageErrors": page_errors,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        if not args.baseline:
            assert not report["failures"], report["failures"]
            assert not page_errors, page_errors
    finally:
        if server.poll() is None:
            server.terminate()
            server.wait(timeout=5)


if __name__ == "__main__":
    main()
