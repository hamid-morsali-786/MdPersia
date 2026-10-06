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
    assert "<h1>عنوان</h1>" in doc.html
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
