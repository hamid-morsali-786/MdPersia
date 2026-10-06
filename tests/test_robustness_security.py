"""
Robustness, security, boundary condition, and stress testing for fa-md-pdf.
Verifies safety against path traversal, XSS payloads, corrupt inputs, and high-volume documents.
"""

from __future__ import annotations

import os
from pathlib import Path
import docx
import pytest

from fa_md_pdf.converter import ConversionError, ConvertJob, ConvertOptions, convert_jobs
from fa_md_pdf.docx_builder import DocxBuildOptions, build_docx
from fa_md_pdf.html_builder import HtmlBuildOptions, build_html, read_text_safely


def test_path_traversal_image_reference(tmp_path: Path):
    # Attempt to reference a file outside the document directory
    secret_dir = tmp_path / "secret"
    secret_dir.mkdir()
    secret_file = secret_dir / "confidential.txt"
    secret_file.write_text("TOP_SECRET_DATA", encoding="utf-8")

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    md_content = f"# تست امنیت\n![نفوذ](../secret/{secret_file.name})\nمتن سند."
    md_file = docs_dir / "attack.md"
    md_file.write_text(md_content, encoding="utf-8")
    out_docx = docs_dir / "out.docx"

    # docx_builder must not fail or corrupt the document when referencing non-image file
    build_docx(md_content, DocxBuildOptions(source_path=md_file), out_docx)
    assert out_docx.is_file()
    doc = docx.Document(out_docx)
    # The non-image file should not be embedded as a drawing
    drawings = [d for p in doc.paragraphs for d in p._p.xpath(".//w:drawing")]
    assert len(drawings) == 0


def test_script_tag_injection_in_mermaid_and_html(tmp_path: Path):
    malicious_md = """# <script>alert('title-xss')</script>

```mermaid
graph TD
    A["<script>alert('mermaid-xss')</script>"] --> B
```

<script>document.body.innerHTML = 'HACKED';</script>

متن باقی‌مانده.
"""
    doc_path = tmp_path / "xss.md"
    doc_path.write_text(malicious_md, encoding="utf-8")
    out_html_doc = build_html(malicious_md, HtmlBuildOptions(source_path=doc_path))

    # In Mermaid pre tag, <script> must be escaped
    assert '<pre class="mermaid">' in out_html_doc.html
    assert "&lt;script&gt;alert(&#x27;mermaid-xss&#x27;)&lt;/script&gt;" in out_html_doc.html or \
           "&lt;script&gt;alert('mermaid-xss')&lt;/script&gt;" in out_html_doc.html

    # In title tag, it must be escaped
    assert "<title><script>" not in out_html_doc.html


def test_corrupted_and_unclosed_markdown_constructs(tmp_path: Path):
    corrupt_md = """# سرتیتر بدون پایان

```python
# کد بدون فنس پایانی
x = 123

$$
y = 456

> [!NOTE]

| ستون ۱ | ستون ۲ |
| ---

[لینک ناقص](
**متن بولد ناقص
"""
    doc_path = tmp_path / "corrupt.md"
    doc_path.write_text(corrupt_md, encoding="utf-8")

    # 1. HTML builder must not raise an unhandled exception
    html_doc = build_html(corrupt_md, HtmlBuildOptions(source_path=doc_path))
    assert html_doc.html is not None

    # 2. DOCX builder must not raise an unhandled exception
    out_docx = tmp_path / "corrupt.docx"
    build_docx(corrupt_md, DocxBuildOptions(source_path=doc_path), out_docx)
    assert out_docx.is_file()
    doc = docx.Document(out_docx)
    assert len(doc.paragraphs) > 0


def test_binary_garbage_file_handling(tmp_path: Path):
    garbage_file = tmp_path / "garbage.md"
    # Write random binary bytes
    garbage_file.write_bytes(os.urandom(1024))

    # read_text_safely should handle it without crashing (falls back to cp1256)
    text = read_text_safely(garbage_file)
    assert isinstance(text, str)

    # DOCX build from decoded text should succeed without crash
    out_docx = tmp_path / "garbage.docx"
    build_docx(text, DocxBuildOptions(source_path=garbage_file), out_docx)
    assert out_docx.is_file()


def test_boundary_options_docx_margins_and_sizes(tmp_path: Path):
    md = "# سند با مقادیر مرزی"
    doc_path = tmp_path / "boundary.md"
    doc_path.write_text(md, encoding="utf-8")

    # 0 margin
    out_0 = tmp_path / "zero_margin.docx"
    build_docx(md, DocxBuildOptions(source_path=doc_path, margin="0mm", font_size_pt=1), out_0)
    assert out_0.is_file()

    # Extreme font size
    out_big = tmp_path / "big_font.docx"
    build_docx(md, DocxBuildOptions(source_path=doc_path, margin="50mm", font_size_pt=72), out_big)
    assert out_big.is_file()


def test_stress_volume_large_document(tmp_path: Path):
    # Generate large document with 100 headings, 100 paragraphs, 20 tables, 20 callouts
    sections = ["# مستند بسیار بزرگ و جامع\n"]
    for i in range(1, 101):
        sections.append(f"## بخش شماره {i}\nاین متن پاراگراف آزمایشی برای بخش {i} است.")
        if i % 5 == 0:
            sections.append(f"> [!NOTE]\n> نکته مربوط به بخش {i}")
        if i % 10 == 0:
            sections.append(f"| شناسه | مقدار |\n| --- | --- |\n| {i} | مقدار {i} |")

    large_md = "\n\n".join(sections)
    doc_path = tmp_path / "large.md"
    doc_path.write_text(large_md, encoding="utf-8")

    # HTML build
    html_doc = build_html(large_md, HtmlBuildOptions(source_path=doc_path))
    assert len(html_doc.html) > 10_000

    # DOCX build
    out_docx = tmp_path / "large.docx"
    build_docx(large_md, DocxBuildOptions(source_path=doc_path), out_docx)
    assert out_docx.is_file()
    assert out_docx.stat().st_size > 5_000


def test_unicode_surrogate_and_noncharacter_resilience(tmp_path: Path):
    corrupt_str = "عنوان با کاراکتر \ufffe و \uffff و کنترل \x01\x02\x08\x0b"
    doc_path = tmp_path / "unicode_edge.md"
    doc_path.write_text(corrupt_str, encoding="utf-8")

    # 1. HTML builder handles safely
    html_res = build_html(corrupt_str, HtmlBuildOptions(source_path=doc_path))
    assert html_res.html is not None

    # 2. DOCX builder strips illegal characters and does not crash
    out_docx = tmp_path / "unicode_edge.docx"
    build_docx(corrupt_str, DocxBuildOptions(source_path=doc_path), out_docx)
    assert out_docx.is_file()
    doc = docx.Document(out_docx)
    assert len(doc.paragraphs) > 0
