import json
from zipfile import ZipFile

from docx import Document
from docx.oxml.ns import qn

from fa_md_pdf.converter import ConvertJob, ConvertOptions, convert_jobs
from fa_md_pdf.docx_builder import DocxBuildOptions, build_docx


def test_reports_are_per_file_and_clear_after_repair(tmp_path, capsys):
    source = tmp_path / 'bad.md'
    source.write_text('![missing](missing.png)\n\n$$\n\\frac{\n$$', encoding='utf8')
    good = tmp_path / 'good.md'
    good.write_text('# Good', encoding='utf8')
    jobs = [ConvertJob(source, tmp_path / 'bad.docx'), ConvertJob(good, tmp_path / 'good.docx')]
    results = convert_jobs(jobs, ConvertOptions(output_format='docx'))
    assert all(r.ok for r in results)
    assert {'image.missing', 'math.invalid', 'math.fallback'} <= {i.code for i in results[0].issues}
    assert results[1].issues == ()
    assert 'WARN [image.missing]' in capsys.readouterr().err
    report = tmp_path / 'bad.docx.report.json'
    assert json.loads(report.read_text(encoding='utf8'))['ok']
    assert not (tmp_path / 'good.docx.report.json').exists()
    source.write_text('# Repaired', encoding='utf8')
    convert_jobs(jobs[:1], ConvertOptions(output_format='docx'))
    assert json.loads(report.read_text(encoding='utf8'))['issues'] == []


def test_layout_preflight_and_failure_receipt(tmp_path):
    source = tmp_path / 'wide.md'
    source.write_text('|a|b|c|d|e|f|g|h|i|j|\n|' + '---|' * 10, encoding='utf8')
    result = convert_jobs([ConvertJob(source, tmp_path / 'wide.docx')],
                          ConvertOptions(output_format='docx', margin='75mm'))[0]
    assert {'layout.narrow', 'layout.table'} <= {i.code for i in result.issues}
    missing = ConvertJob(tmp_path / 'absent.md', tmp_path / 'absent.docx')
    assert not convert_jobs([missing], ConvertOptions(output_format='docx'))[0].ok
    assert not json.loads((tmp_path / 'absent.docx.report.json').read_text())['ok']


def test_native_numbering_restarts_continuations_and_nesting(tmp_path):
    path = tmp_path / 'lists.docx'
    build_docx('0. Zero\n1. One\n   - Child\n\n   Continued\n\n2. Two\n\n'
               '## Restart\n\n5. Five\n6. Six', DocxBuildOptions(source_path=tmp_path/'a.md'), path)
    doc = Document(path)
    pars = {p.text: p for p in doc.paragraphs}
    def number(label):
        return pars[label]._p.find(qn('w:pPr')).find(qn('w:numPr'))
    assert number('Zero') is not None
    assert number('Continued') is None
    assert number('Child').find(qn('w:ilvl')).get(qn('w:val')) == '1'
    assert number('Zero').find(qn('w:numId')).get(qn('w:val')) != number('Five').find(qn('w:numId')).get(qn('w:val'))
    with ZipFile(path) as z:
        assert b'w:startOverride w:val="0"' in z.read('word/numbering.xml')
        assert b'w:startOverride w:val="5"' in z.read('word/numbering.xml')


def test_footnote_lists_use_package_numbering_definitions(tmp_path):
    from lxml import etree
    path = tmp_path / 'notes.docx'
    build_docx('1. Main\n\nText[^n]\n\n[^n]: Note\n\n    3. Third\n    4. Fourth',
               DocxBuildOptions(source_path=tmp_path/'a.md'), path)
    with ZipFile(path) as z:
        root = etree.fromstring(z.read('word/numbering.xml'))
        ids = {n.get(qn('w:numId')) for n in root.findall(qn('w:num'))}
        note = etree.fromstring(z.read('word/footnotes.xml'))
        references = list(note.iter(qn('w:numId')))
        assert references
        assert all(n.get(qn('w:val')) in ids for n in references)
