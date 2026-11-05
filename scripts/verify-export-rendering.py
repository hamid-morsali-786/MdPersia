"""Exercise actual offline PDF/DOCX export; writes artifacts without installing anything.

Run from the repository: py -3.11 scripts/verify-export-rendering.py
Inspect the PDFs separately (including a Word-exported PDF for DOCX visual QA).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

from lxml import etree
from playwright.sync_api import sync_playwright

from fa_md_pdf.converter import ConvertJob, ConvertOptions, _render_job, _render_job_docx
from fa_md_pdf.html_builder import build_markdown_renderer, read_text_safely, strip_front_matter


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("tests/fixtures/export-bilingual.md"))
    parser.add_argument("--output", type=Path, default=Path("output/export-verification"))
    args = parser.parse_args()
    source = args.source.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    original = hashlib.sha256(source.read_bytes()).hexdigest()
    tokens = build_markdown_renderer().parse(strip_front_matter(read_text_safely(source)))
    expected = sum(t.type == "math_block" for t in tokens) + sum(
        c.type == "math_inline" for t in tokens for c in t.children or [])
    options = ConvertOptions(mermaid_source=str(Path("vendor/mermaid.min.js").resolve()),
                             font_dir=Path("fonts").resolve())
    _render_job_docx(ConvertJob(source, output / "document.docx"), options)
    counts = {"oMath": 0, "f": 0, "borderBox": 0}
    ns = {"m": "http://schemas.openxmlformats.org/officeDocument/2006/math"}
    with ZipFile(output / "document.docx") as archive:
        for name in ("word/document.xml", "word/footnotes.xml"):
            if name in archive.namelist():
                root = etree.fromstring(archive.read(name))
                for tag in counts:
                    counts[tag] += len(root.findall(".//m:" + tag, ns))
    assert counts["oMath"] == expected, (counts, expected)
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception:
            browser = pw.chromium.launch(channel="msedge")
        context = browser.new_context(viewport={"width": 680, "height": 1000}, offline=True)
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        _render_job(page, ConvertJob(source, output / "document.pdf"), options, output)
        metrics = page.evaluate("""() => ({
            equations: document.querySelectorAll('math').length,
            errors: document.querySelectorAll('code.math-error').length,
            fractions: document.querySelectorAll('mfrac').length,
            boxes: document.querySelectorAll('menclose[notation="box"]').length,
            wrapped: document.querySelectorAll('math > mtable').length,
            overflowing: Array.from(document.querySelectorAll('.math.block math')).filter(m =>
                m.getBoundingClientRect().width > m.parentElement.clientWidth + 1).length,
            tablesOverflowing: Array.from(document.querySelectorAll('.md-table-scroll table'))
                .filter(t => t.scrollWidth > document.body.clientWidth + 1).length
        })""")
        assert metrics["equations"] == expected, metrics
        assert not metrics["errors"] and not metrics["overflowing"], metrics
        assert not metrics["tablesOverflowing"] and not errors, (metrics, errors)
        assert counts["f"] == metrics["fractions"]
        assert counts["borderBox"] == metrics["boxes"]
        browser.close()
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original
    receipt = {"source": str(source), "sourceSha256": original, "sourceUnchanged": True,
               "docx": counts, "pdfDOM": metrics, "pageErrors": errors,
               "scope": "Source runtime and print DOM; inspect exported pages separately."}
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
