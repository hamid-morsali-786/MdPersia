from pathlib import Path

from fa_md_pdf.html_builder import HtmlBuildOptions, build_html, convert_mermaid_fences_to_html


def test_convert_mermaid_fence():
    text = """# Test

```mermaid
flowchart TD
  A --> B
```
"""
    converted, has_mermaid = convert_mermaid_fences_to_html(text)

    assert has_mermaid is True
    assert '<pre class="mermaid">' in converted
    assert "flowchart TD" in converted


def test_build_html_rtl(tmp_path: Path):
    source = tmp_path / "sample.md"
    source.write_text("# عنوان\n\nمتن فارسی", encoding="utf-8")

    doc = build_html(
        source.read_text(encoding="utf-8"),
        HtmlBuildOptions(
            source_path=source,
            font_family="Tahoma, sans-serif",
            font_file=None,
            font_dir=None,
            custom_css=None,
            mermaid_source="https://example.test/mermaid.js",
            mermaid_theme="default",
        ),
    )

    assert 'lang="fa" dir="rtl"' in doc.html
    assert "عنوان</h1>" in doc.html
    assert doc.has_mermaid is False


def test_build_html_loads_vazirmatn_font_dir(tmp_path: Path):
    source = tmp_path / "sample.md"
    source.write_text("# عنوان\n\nمتن فارسی", encoding="utf-8")
    fonts = tmp_path / "fonts"
    fonts.mkdir()
    (fonts / "Vazirmatn-Regular.ttf").write_bytes(b"fake-font-for-css-test")

    doc = build_html(
        source.read_text(encoding="utf-8"),
        HtmlBuildOptions(
            source_path=source,
            font_family='"Vazirmatn", Tahoma, sans-serif',
            font_file=None,
            font_dir=fonts,
            custom_css=None,
            mermaid_source="https://example.test/mermaid.js",
            mermaid_theme="default",
        ),
    )

    assert 'font-family: "Vazirmatn";' in doc.html
    assert "Vazirmatn-Regular.ttf" in doc.html


def test_html_strip_emojis_option(tmp_path: Path):
    source = tmp_path / "emoji.md"
    content = "# 📊 عنوان تستی\n\nمتن با 💡 و ⚠️\n\n> [!NOTE]\n> نکته تستی\n"
    source.write_text(content, encoding="utf-8")

    doc = build_html(
        content,
        HtmlBuildOptions(
            source_path=source,
            strip_emojis=True,
        ),
    )

    assert "📊" not in doc.html
    assert "💡" not in doc.html
    assert "⚠️" not in doc.html
    assert "عنوان تستی" in doc.html
    assert '<div class="callout-title">نکته</div>' in doc.html


def test_strip_emojis_preserves_persian_zwj_and_zwnj():
    from fa_md_pdf.html_builder import strip_emojis

    # \u200C is ZWNJ (نیم‌فاصله), \u200D is ZWJ (اتصال‌دهنده صفر-عرض)
    sample = "کتاب\u200Cها و اتصال\u200Dنما همراه با 😊 و 🚀 در متن."
    cleaned = strip_emojis(sample)

    assert "\u200C" in cleaned, "ZWNJ must be preserved"
    assert "\u200D" in cleaned, "ZWJ must be preserved for Persian typography"
    assert "😊" not in cleaned
    assert "🚀" not in cleaned
    assert cleaned == "کتاب\u200Cها و اتصال\u200Dنما همراه با و در متن."


def test_build_font_css_empty_dir(tmp_path: Path):
    from fa_md_pdf.html_builder import build_font_css

    empty_dir = tmp_path / "empty_fonts"
    empty_dir.mkdir()

    css = build_font_css("Vazirmatn", font_file=None, font_dir=empty_dir)
    assert 'font-family: Vazirmatn;' in css
    assert "@font-face" not in css


def test_fix_bidi_nested_list_items_preserves_structure():
    from fa_md_pdf.html_builder import fix_bidi_list_items
    html_input = """<ul>
<li>Parent
<ul>
<li>Child 1</li>
<li>Child 2</li>
</ul>
</li>
</ul>"""
    output = fix_bidi_list_items(html_input)
    assert "<li>Child 1</bdi>" not in output
    assert "<li><bdi>Child 1</bdi></li>" in output


def test_code_blocks_and_ascii_diagrams_render_pre_dir_ltr():
    from fa_md_pdf.html_builder import build_markdown_renderer, load_default_css

    renderer = build_markdown_renderer()

    # 1. Fenced code block with syntax highlighting
    fence_html = renderer.render("```python\nx = 1\n```")
    assert '<pre dir="ltr"><code dir="ltr" class="language-python">' in fence_html

    # 2. Plain fenced code block / ASCII diagram
    ascii_diagram = "```\n+---+\n| A |\n+---+\n```"
    ascii_html = renderer.render(ascii_diagram)
    assert '<pre dir="ltr"><code dir="ltr">' in ascii_html

    # 3. Indented code block
    indented_code = "    +---+\n    | B |\n    +---+\n"
    indented_html = renderer.render(indented_code)
    assert '<pre dir="ltr"><code>' in indented_html

    # 4. CSS verifies code blocks and inner spans stay LTR without isolated BiDi inversion
    css = load_default_css()
    assert 'pre :is(code, span, a, strong, em, b, i, u, s, mark)' in css
    assert 'unicode-bidi: normal !important;' in css
    assert 'font-family: Consolas, "Cascadia Mono", "Courier New", "Vazirmatn", monospace;' in css


def test_fix_bidi_heading_parentheses_isolates_latin_parentheses():
    from fa_md_pdf.html_builder import build_html, HtmlBuildOptions

    md_content = """# گزارش پیشرفت پروژه (Hamneshin Progress Report)

## معماری سیستم (System Architecture) و دیتابیس (Oracle RAC)

### گزارش عملکرد (دوره بهار ۱۴۰۵)

# Pure English Heading (Architecture Overview)
"""
    html_doc = build_html(md_content, HtmlBuildOptions(source_path=Path("test_headings.md")))
    html = html_doc.html

    # 1. H1 with Latin parenthetical isolates the parenthetical
    assert '<h1 id="گزارش-پیشرفت-پروژه-hamneshin-progress-report" dir="rtl">گزارش پیشرفت پروژه <bdi dir="ltr">(Hamneshin Progress Report)</bdi></h1>' in html

    # 2. H2 with multiple Latin parentheticals isolates each
    assert '<h2 id="معماری-سیستم-system-architecture-و-دیتابیس-oracle-rac" dir="rtl">معماری سیستم <bdi dir="ltr">(System Architecture)</bdi> و دیتابیس <bdi dir="ltr">(Oracle RAC)</bdi></h2>' in html

    # 3. Persian parenthetical is left intact without bdi
    assert '<h3 id="گزارش-عملکرد-دوره-بهار-۱۴۰۵" dir="rtl">گزارش عملکرد (دوره بهار ۱۴۰۵)</h3>' in html

    # 4. Pure English heading is left intact
    assert '<h1 id="pure-english-heading-architecture-overview" dir="ltr">Pure English Heading (Architecture Overview)</h1>' in html

    # 5. Document title extracted cleanly without raw HTML tags
    assert "Hamneshin Progress Report" in html_doc.title


