"""Contracts that must survive export-module refactoring."""
from pathlib import Path
import subprocess
import sys

import pytest

from docx import Document
from docx.shared import Inches

from fa_md_pdf import docx_builder, word_document, word_styles
from fa_md_pdf.conversion_report import report_conversion, warn
from fa_md_pdf.converter import ConvertJob, ConvertOptions


def test_existing_word_imports_remain_compatible():
    assert docx_builder.parse_docx_length is word_document.parse_docx_length
    assert docx_builder.RunStyle is word_styles.RunStyle
    assert docx_builder._add_styled_run is word_styles._add_styled_run
    document = Document()
    paragraph = document.add_paragraph()
    docx_builder._add_styled_run(paragraph, 'Host: میزبان', rtl=True, bold=True)
    assert paragraph.runs[0].bold
    assert paragraph._p.xpath('.//w:rtl')


def test_report_binding_supports_page_argument_and_keyword_calls(tmp_path):
    source = tmp_path / 'source.md'
    source.write_text('# Valid', encoding='utf8')
    job = ConvertJob(source, tmp_path / 'result.pdf')
    options = ConvertOptions()
    calls = []

    @report_conversion
    def renamed_pdf_export(page, job, options):
        calls.append((page, job, options))
        warn('test.contract', 'contract warning')

    issues = renamed_pdf_export(object(), job=job, options=options)
    assert [i.code for i in issues] == ['test.contract']
    assert calls[0][1:] == (job, options)
    with pytest.raises(TypeError):
        renamed_pdf_export(None, job, options, unexpected=True)
    assert len(calls) == 1


def test_document_layout_and_image_bounds_survive_orientation_changes():
    for landscape, expected in [(False, (215.9, 279.4)), (True, (279.4, 215.9))]:
        options = docx_builder.DocxBuildOptions(
            source_path=Path('source.md'), page_format='Letter', margin='0.5in',
            landscape=landscape, include_page_numbers=False)
        document = word_document.create_document(options)
        section = document.sections[0]
        assert (section.page_width.mm, section.page_height.mm) == pytest.approx(expected)
        assert section.left_margin == Inches(.5)
        assert not section.footer.paragraphs[0]._p.xpath('.//w:fldSimple')
        # A tiny image stays at natural size; a wide image fits the content area.
        assert docx_builder._calculate_image_width(48, options) == .5
        assert docx_builder._calculate_image_width(9600, options) == pytest.approx(expected[0]/25.4 - 1)


def test_preflight_no_longer_loads_the_word_block_renderer():
    code = '''
import sys
from pathlib import Path
from types import SimpleNamespace
from fa_md_pdf.conversion_report import preflight
preflight(SimpleNamespace(source=Path('tests/fixtures/lists-bilingual.md')),
          SimpleNamespace(output_format='pdf', page_format='A4', margin='15mm', landscape=False))
assert 'fa_md_pdf.docx_builder' not in sys.modules
'''
    subprocess.run([sys.executable, '-c', code], check=True)


def test_reader_does_not_import_optional_conversion_modules():
    # The lightweight reader must remain independent of python-docx/Playwright.
    code = '''
import sys
sys.modules['docx'] = None
sys.modules['playwright'] = None
from fa_md_pdf.html_builder import build_html, HtmlBuildOptions
from pathlib import Path
result = build_html('# Reader\\n\\n$x^2$', HtmlBuildOptions(source_path=Path('a.md')))
assert '<math' in result.html
'''
    subprocess.run([sys.executable, '-c', code], check=True)
