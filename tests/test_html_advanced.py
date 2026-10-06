"""
Advanced tests for HTML builder: Windows encodings (BOM, CP1256), title extraction,
frontmatter stripping, syntax highlighting across languages, callouts, pagebreaks,
Mermaid scripts, and security sanitization.
"""

from __future__ import annotations

from pathlib import Path
import pytest

from fa_md_pdf.html_builder import (
    HtmlBuildOptions,
    _highlight_code,
    _transform_callouts,
    _transform_pagebreaks,
    build_css,
    build_html,
    build_mermaid_script,
    extract_title,
    read_text_safely,
    strip_front_matter,
    to_mermaid_source,
)


def test_read_text_safely_utf8_bom(tmp_path: Path):
    bom_file = tmp_path / "bom.md"
    # UTF-8 BOM is \xef\xbb\xbf
    bom_file.write_bytes(b"\xef\xbb\xbf# \xd8\xb9\xd9\x86\xd9\x88\xd8\xa7\xd9\x86 \xd9\x81\xd8\xa7\xd8\xb1\xd8\xb3\xdb\x8c")

    text = read_text_safely(bom_file)
    assert text.startswith("# عنوان فارسی")
    assert not text.startswith("\ufeff")


def test_read_text_safely_cp1256_fallback(tmp_path: Path):
    cp_file = tmp_path / "legacy.md"
    # Text in CP1256 encoding: "سلام"
    persian_cp1256 = "سلام".encode("cp1256")
    cp_file.write_bytes(persian_cp1256)

    text = read_text_safely(cp_file)
    assert text == "سلام"


def test_strip_front_matter_variations():
    crlf_doc = "---\r\ntitle: تست\r\nauthor: تیم\r\n---\r\n# بدنه سند"
    assert strip_front_matter(crlf_doc) == "# بدنه سند"

    lf_doc = "---\ntitle: تست\n---\nمتن اصلی"
    assert strip_front_matter(lf_doc) == "متن اصلی"

    no_fm = "# بدنه بدون فرانت‌متر\n---\nخط افقی در متن"
    assert strip_front_matter(no_fm) == no_fm


def test_extract_title_complex_markdown():
    fallback = "fallback_title"

    assert extract_title("# **گزارش** *فنی*", fallback) == "گزارش فنی"
    assert extract_title("# مستند شماره ۱۲: بررسی سیستم", fallback) == "مستند شماره ۱۲: بررسی سیستم"
    assert extract_title("بدون تیتر اصلی\n## سطح ۲", fallback) == fallback
    assert extract_title("#    ", fallback) == fallback


def test_highlight_code_languages():
    py_code = "def calc(x):\n    return x * 2"
    hl_py = _highlight_code(py_code, "python", "")
    assert '<span class="k">def</span>' in hl_py or '<span class="nf">calc</span>' in hl_py

    sql_code = "SELECT id, name FROM users WHERE active = 1;"
    hl_sql = _highlight_code(sql_code, "sql", "")
    assert '<span class="k">SELECT</span>' in hl_sql or '<span class="k">FROM</span>' in hl_sql

    json_code = '{"status": "ok", "code": 200}'
    hl_json = _highlight_code(json_code, "json", "")
    assert '<span class="s2">&quot;status&quot;</span>' in hl_json or '200' in hl_json

    # Unknown language gracefully falls back to empty string (unhighlighted)
    hl_unknown = _highlight_code("some code", "invalid_lang_xyz", "")
    assert hl_unknown == ""


def test_transform_callouts_case_insensitivity_and_variants():
    html_input = """
<blockquote>
<p>[!note]<br>
یادداشت با حروف کوچک
</p>
</blockquote>

<blockquote>
<p>[!WARNING]
هشدار با حروف بزرگ
</p>
</blockquote>

<blockquote>
<p>[!caution]<br />
احتیاط فوری
</p>
</blockquote>
"""
    transformed = _transform_callouts(html_input, strip_emojis_flag=False)
    assert 'class="callout callout-note"' in transformed
    assert "💡 نکته" in transformed
    assert 'class="callout callout-warning"' in transformed
    assert "⚠️ هشدار" in transformed
    assert 'class="callout callout-caution"' in transformed
    assert "🛑 احتیاط" in transformed

    # Strip emojis flag test
    transformed_plain = _transform_callouts(html_input, strip_emojis_flag=True)
    assert "💡" not in transformed_plain
    assert "⚠️" not in transformed_plain
    assert "🛑" not in transformed_plain
    assert '<div class="callout-title">نکته</div>' in transformed_plain


def test_transform_pagebreaks():
    sample = "بخش اول\n<!-- pagebreak -->\nبخش دوم\n<!--page-break-->\nبخش سوم\n\\pagebreak\nپایان"
    res = _transform_pagebreaks(sample)
    assert res.count('<div class="page-break"></div>') == 3
    assert "<!-- pagebreak -->" not in res
    assert "\\pagebreak" not in res


def test_to_mermaid_source(tmp_path: Path):
    assert to_mermaid_source("https://example.com/mermaid.js") == "https://example.com/mermaid.js"
    assert to_mermaid_source("file:///opt/mermaid.js") == "file:///opt/mermaid.js"

    local_file = tmp_path / "mermaid.min.js"
    local_file.write_text("window.mermaid={}", encoding="utf-8")
    assert to_mermaid_source(str(local_file)) == local_file.resolve().as_uri()

    assert to_mermaid_source("missing_file.js") == "missing_file.js"


def test_build_css_orientation_and_custom_options(tmp_path: Path):
    custom_css_file = tmp_path / "custom.css"
    custom_css_file.write_text(".custom-class { color: red; }", encoding="utf-8")

    opts = HtmlBuildOptions(
        source_path=tmp_path / "doc.md",
        page_format="Letter",
        margin="20mm",
        landscape=True,
        custom_css=custom_css_file,
    )
    css = build_css(opts)

    assert "size: Letter landscape;" in css
    assert "margin: 20mm;" in css
    assert ".custom-class { color: red; }" in css


def test_build_mermaid_script_ready_flag(tmp_path: Path):
    opts = HtmlBuildOptions(source_path=tmp_path / "test.md")

    script_no_mermaid = build_mermaid_script(opts, has_mermaid=False)
    assert "window.__FA_MD_PDF_READY = true;" in script_no_mermaid
    assert "<script src=" not in script_no_mermaid

    script_with_mermaid = build_mermaid_script(opts, has_mermaid=True)
    assert "window.__FA_MD_PDF_READY = false;" in script_with_mermaid
    assert "window.mermaid.initialize" in script_with_mermaid


def test_build_html_sanitizes_title_xss(tmp_path: Path):
    malicious_md = "# <script>alert('xss')</script>\n\nمتن صفحه"
    doc = build_html(malicious_md, HtmlBuildOptions(source_path=tmp_path / "test.md"))

    # Title tag in head must be properly escaped preventing tag injection
    assert "<title><script>" not in doc.html
    assert "&lt;script" in doc.html
