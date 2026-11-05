from pathlib import Path

from fa_md_pdf.html_builder import HtmlBuildOptions, build_html


def render(text):
    return build_html(text, HtmlBuildOptions(source_path=Path("document.md").resolve()))


def test_mermaid_examples_remain_code_but_nested_diagrams_render():
    example = render("~~~~text\n```mermaid\ngraph LR\n```\n~~~~")
    assert not example.has_mermaid
    diagram = render("> ~~~mermaid\n> graph LR\n> A-->B\n> ~~~~")
    assert diagram.has_mermaid and '<pre class="mermaid">' in diagram.html


def test_hr_does_not_discard_intro():
    assert 'پاراگراف اول' in render('---\nپاراگراف اول\n\n---\nپایان').html


def test_reader_dialects_in_one_document():
    result = render("# بخش اول\n\n# بخش اول\n\n- [x] تمام\n- [ ] باقی\n\nارجاع[^1]\n\n[^1]: تعریف\n\n| A | B |\n|---|---|\n|1|2|").html
    assert 'id="بخش-اول"' in result and 'id="بخش-اول-1"' in result
    assert result.count('type="checkbox"') == 2
    assert 'checked="checked"' in result
    assert 'href="#fn1"' in result and 'id="fn1"' in result
    assert '<div class="md-table-scroll">' in result

def test_literal_title_and_page_break_in_examples():
    doc = render("~~~\n# Fake title\n\\pagebreak\n~~~\n\nActual title\n============")
    assert doc.title == "Actual title"
    assert '<div class="page-break"></div>' not in doc.html

def test_unicode_windows_sources_round_trip_without_losing_byte_order(tmp_path):
    from fa_md_pdf.document_io import read_document, save_document
    from fa_md_pdf.html_builder import read_text_safely
    source = tmp_path / 'سند.md'
    for encoding in ('utf-16-le', 'utf-16-be', 'utf-32-le', 'utf-32-be'):
        source.write_bytes('\ufeff# سلام\r\n'.encode(encoding))
        assert read_text_safely(source) == '# سلام\n'
        snapshot = read_document(str(source))
        save_document(str(source), '# دنیا\n', snapshot['revision'])
        assert source.read_bytes() == '\ufeff# دنیا\r\n'.encode(encoding)
