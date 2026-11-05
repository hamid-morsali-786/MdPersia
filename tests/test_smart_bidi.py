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

* `Installed`: نام ابزار
* `Verified`: Yes / No
* Repository با موفقیت دریافت شد.
"""
    doc = build_html(md, HtmlBuildOptions(source_path=tmp_path / "test.md"))
    # The key + colon should be isolated in <bdi> to prevent colon inversion
    assert "<bdi><code>Installed</code>:</bdi>" in doc.html
    # Pure Latin line should be wrapped in <bdi>
    assert "<bdi><code>Verified</code>: Yes / No</bdi>" in doc.html
    # Persian list containing Latin keyword at start remains intact
    assert "Repository با موفقیت دریافت شد." in doc.html
