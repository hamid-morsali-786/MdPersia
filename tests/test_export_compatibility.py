from pathlib import Path
from zipfile import ZipFile

from docx import Document
from lxml import etree

from fa_md_pdf.docx_builder import DocxBuildOptions, build_docx, extract_mermaid_blocks
from fa_md_pdf.html_builder import build_markdown_renderer

NS = {"m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
      "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def export(tmp_path, source):
    path = tmp_path / "export.docx"
    result = build_docx(source, DocxBuildOptions(source_path=tmp_path / "source.md"), path)
    with ZipFile(path) as archive:
        xml = etree.fromstring(archive.read("word/document.xml"))
    return path, xml, result


def test_equations_are_editable_office_math(tmp_path):
    source = Path("tests/fixtures/math-bilingual.md").read_text(encoding="utf8")
    path, xml, _ = export(tmp_path, source)
    assert len(xml.findall(".//m:oMath", NS)) == 10
    assert len(xml.findall(".//m:f", NS)) == 8
    assert len(xml.findall(".//m:borderBox", NS)) == 3
    assert len(xml.findall(".//m:oMathPara", NS)) == 9
    assert "$$ literal code" in "\n".join(p.text for p in Document(path).paragraphs)
    assert all(r.find("w:rPr/w:rtl", NS).get("{" + NS["w"] + "}val") == "0"
               for r in xml.findall(".//m:r", NS))


def test_roots_matrices_and_limits(tmp_path):
    _, xml, _ = export(tmp_path, r"$$\sqrt{x}+\sqrt[3]{x}+\sum_{i=1}^n i"
                       r"+\int_0^1 x dx+\begin{pmatrix}a&b\\c&d\end{pmatrix}$$")
    assert len(xml.findall(".//m:rad", NS)) == 2
    assert all(r.find("m:deg", NS) is not None for r in xml.findall(".//m:rad", NS))
    assert len(xml.findall(".//m:m/m:mr", NS)) == 2
    operators = [node.get("{" + NS["m"] + "}val")
                 for node in xml.findall(".//m:naryPr/m:chr", NS)]
    assert "∑" in operators and "∫" in operators


def test_word_preserves_alignment_of_multiline_equations(tmp_path):
    _, xml, _ = export(tmp_path, r"$$\begin{aligned}x&=1\\xyz&=123\end{aligned}$$")
    matrix = xml.find(".//m:m", NS)
    assert len(matrix.findall("m:mr", NS)) == 2
    assert [item.get("{" + NS["m"] + "}val")
            for item in matrix.findall("m:mPr/m:mcs/m:mc/m:mcPr/m:mcJc", NS)] == ["right", "left"]


def test_invalid_math_preserves_source_and_following_text(tmp_path, caplog):
    path, _, _ = export(tmp_path, "$$\n\\frac{\n$$\n\nپایان")
    text = "\n".join(p.text for p in Document(path).paragraphs)
    assert r"\frac{" in text and "پایان" in text
    assert "preserving TeX" in caplog.text


def test_native_footnotes_keep_math_and_link_relationships(tmp_path):
    path, xml, _ = export(tmp_path, "متن[^n] و دوباره[^n].\n\n"
                         "[^n]: پانوشت $x^2$ و [پیوند](https://example.com).")
    assert len(xml.findall(".//w:footnoteReference", NS)) == 2
    with ZipFile(path) as archive:
        notes = etree.fromstring(archive.read("word/footnotes.xml"))
        assert len(notes.findall(".//m:oMath", NS)) == 1
        assert len(notes.findall(".//w:footnoteRef", NS)) == 1
        assert b"https://example.com" in archive.read("word/_rels/footnotes.xml.rels")


def test_headings_bookmarks_tasks_and_numbered_continuations(tmp_path):
    path, xml, result = export(tmp_path,
        "```md\n# Fake\n```\n\nعنوان\n====\n\n[برو](#مقصد)\n\n"
        "- [x] انجام\n- [ ] باقی\n\n3. First\n\n   Continued\n\n4. Next\n\n"
        "## مقصد\n\n~~حذف~~\n\n## مقصد")
    assert result.title == "عنوان"
    paragraphs = [p.text for p in Document(path).paragraphs]
    assert "First" in paragraphs and "Continued" in paragraphs and "Next" in paragraphs
    assert any("☒" in p for p in paragraphs) and any("☐" in p for p in paragraphs)
    names = [b.get("{" + NS["w"] + "}name") for b in xml.findall(".//w:bookmarkStart", NS)]
    assert len(names) == len(set(names)) == 3
    assert xml.find(".//w:hyperlink", NS).get("{" + NS["w"] + "}anchor") in names
    assert xml.find(".//w:strike", NS) is not None


def test_nested_math_and_code_do_not_disappear_or_gain_quote_markers(tmp_path):
    source = "> $$\n> \\frac{1}{2}\n> $$\n>\n> ```text\n> keep me\n> ```"
    path, xml, _ = export(tmp_path, source)
    assert len(xml.findall(".//m:f", NS)) == 1
    assert ">" not in "".join(xml.find(".//m:oMath", NS).itertext())
    assert any("keep me" in p.text for p in Document(path).paragraphs)
    tokens = build_markdown_renderer().parse(source)
    assert ">" not in next(t.content for t in tokens if t.type == "math_block")


def test_only_actual_mermaid_fences_are_extracted(tmp_path):
    source = "````md\n```mermaid\nexample\n```\n````\n\n> ```mermaid\n> graph TD; A-->B\n> ````"
    _, blocks = extract_mermaid_blocks(source)
    assert blocks == ["graph TD; A-->B"]
    path, _, result = export(tmp_path, source)
    assert result.has_mermaid
    assert any("example" in p.text for p in Document(path).paragraphs)


def test_zero_start_nested_lists_and_pagebreak_code(tmp_path):
    path, xml, _ = export(tmp_path,
        "0. Zero\n1. One\n\n> 4. Nested\n> 5. Next\n\n"
        "```text\n\\pagebreak\n```\n\n\\pagebreak\n\nAfter")
    text = [p.text for p in Document(path).paragraphs]
    assert "Zero" in text and "One" in text
    assert "Nested" in text and "Next" in text
    assert any(p.rstrip("\n") == r"\pagebreak" for p in text)
    assert len(xml.findall('.//w:br[@w:type="page"]', NS)) == 1


def test_english_table_keeps_order_alignment_and_math(tmp_path):
    path, xml, _ = export(tmp_path, "| Left | Center | Right |\n| :-- | :-: | --: |\n"
                         "| A | $x$ | B |")
    assert xml.find(".//w:tblPr/w:bidiVisual", NS) is None
    assert len(xml.findall(".//m:oMath", NS)) == 1
    table = Document(path).tables[0]
    assert [c.paragraphs[0].alignment for c in table.rows[1].cells] == [0, 1, 2]
    assert not table.autofit


def test_encoded_image_paths_and_long_titles(tmp_path):
    import base64
    from urllib.parse import quote
    image = tmp_path / "تصویر نمونه.png"
    image.write_bytes(base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9Zl1sAAAAASUVORK5CYII="))
    path, _, _ = export(tmp_path, "# " + "عنوان " * 100 + "\n\n"
                         + f'![a]({quote(image.name)})\n\n<img src="{image.as_uri()}" alt="b">')
    assert len(Document(path).inline_shapes) == 2
    assert len(Document(path).core_properties.title) <= 255


def test_callout_with_code_and_code_label_hyperlink(tmp_path):
    path, xml, _ = export(tmp_path,
        "> [!NOTE]\n>\n> ```python\n> print(1)\n> ```\n\n[`code`](https://example.com)")
    text = "\n".join(p.text for p in Document(path).paragraphs)
    assert "[!NOTE]" not in text and "نکته" in text and "print(1)" in text
    link = xml.find(".//w:hyperlink", NS)
    assert link is not None and "code" in "".join(link.itertext())
