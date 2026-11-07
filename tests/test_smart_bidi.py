from pathlib import Path
from fa_md_pdf.rtl_wrapper import detect_direction, is_rtl_document
from fa_md_pdf.html_builder import build_html, HtmlBuildOptions
from fa_md_pdf.docx_builder import build_docx, DocxBuildOptions
from docx import Document


def test_direction_detection():
    # Pure English
    en_text = "# Master System Prompt\nYou are an AI compiler.\n- Item 1\n- Item 2"
    assert detect_direction(en_text) == "ltr"
    assert is_rtl_document(en_text) is False

    # Pure Persian
    fa_text = "# راهنمای فارسی\nاین یک سند آزمایشی است.\n- مورد اول\n- مورد دوم"
    assert detect_direction(fa_text) == "rtl"
    assert is_rtl_document(fa_text) is True

    # Persian with tech English words
    mixed_text = "پروژه با React و TypeScript و Vite به خوبی بیلد شد."
    assert detect_direction(mixed_text) == "rtl"
    assert is_rtl_document(mixed_text) is True

    # Code block immunity
    code_text = "```python\n# کامنت فارسی داخل کد\ndef calculate(x):\n    return x * 2\n```"
    assert detect_direction(code_text) == "ltr"


def test_html_builder_smart_direction(tmp_path: Path):
    # English doc should get lang="en" dir="ltr"
    en_file = tmp_path / "en.md"
    en_file.write_text("# English Title\n\nParagraph in English.", encoding="utf-8")
    doc_en = build_html(en_file.read_text(encoding="utf-8"), HtmlBuildOptions(source_path=en_file))
    assert 'lang="en" dir="ltr"' in doc_en.html

    # Persian doc should get lang="fa" dir="rtl"
    fa_file = tmp_path / "fa.md"
    fa_file.write_text("# عنوان فارسی\n\nمتن فارسی با فونت وزیر.", encoding="utf-8")
    doc_fa = build_html(fa_file.read_text(encoding="utf-8"), HtmlBuildOptions(source_path=fa_file))
    assert 'lang="fa" dir="rtl"' in doc_fa.html


def test_docx_builder_smart_direction(tmp_path: Path):
    md_content = """# English Heading

English paragraph.

# عنوان فارسی

متن فارسی در همان سند.
"""
    out_docx = tmp_path / "bidi.docx"
    build_docx(
        md_content,
        DocxBuildOptions(
            source_path=tmp_path / "test.md",
            rtl=True,
        ),
        output_path=out_docx,
    )

    doc = Document(str(out_docx))
    headings = [p for p in doc.paragraphs if p.text in ("English Heading", "عنوان فارسی")]
    assert len(headings) == 2

    # English heading should have bidi="0" (LTR)
    h_en_bidi = headings[0]._p.xpath(".//w:bidi")
    assert len(h_en_bidi) > 0
    assert h_en_bidi[0].get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val") == "0"

    # Persian heading should have bidi without val="0" (RTL)
    h_fa_bidi = headings[1]._p.xpath(".//w:bidi")
    assert len(h_fa_bidi) > 0
    assert h_fa_bidi[0].get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val") is None


def test_bilingual_colon_keys(tmp_path: Path):
    md = """# راهنمای فارسی

* `Installed:` نام Skillها
* `Verified:` Yes / No
* `Location`: مسیر نصب
* **Method:** روش نصب
* Warnings: فقط در صورت وجود مشکل
* Repository با موفقیت دریافت شد.
"""
    source = tmp_path / "test.md"
    doc = build_html(md, HtmlBuildOptions(source_path=source))
    for label, value in [
        ("<code>Installed:</code>", "نام Skillها"),
        ("<code>Verified:</code>", "Yes / No"),
        ("<code>Location</code>:", "مسیر نصب"),
        ("<strong>Method:</strong>", "روش نصب"),
        ("Warnings:", "فقط در صورت وجود مشکل"),
    ]:
        assert f'<bdi dir="ltr">{label}</bdi> <bdi dir="auto">{value}</bdi>' in doc.html
    assert "Repository با موفقیت دریافت شد." in doc.html

    output = tmp_path / "fields.docx"
    build_docx(md, DocxBuildOptions(source_path=source, rtl=True), output_path=output)
    items = Document(output).paragraphs[1:]
    assert all(item._p.xpath("w:pPr/w:numPr") for item in items)
    assert all(item._p.xpath("w:pPr/w:bidi[not(@w:val)]") for item in items)
    assert items[0].text.replace("\u200f", "") == "Installed: نام Skillها"
    assert items[1].text.replace("\u200f", "") == "Verified: Yes / No"
    assert any(run.text == "Method:" and run.bold for run in items[3].runs)

    english = build_html("- `Verified:` Yes / No", HtmlBuildOptions(source_path=source))
    assert '<ul dir="ltr">\n<li><bdi><code>Verified:</code> Yes / No</bdi></li>' in english.html
