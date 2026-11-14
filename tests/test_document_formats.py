"""Exercise supported input formats through reader, editor and export entry points."""
import io
import json
from pathlib import Path

import pytest
from docx import Document

from fa_md_pdf.associations import EXTENSIONS, PROGID_KEY, build_entries
from fa_md_pdf.cli import main
from fa_md_pdf.converter import ConversionError, build_jobs
from fa_md_pdf.document_io import read_document, save_document
from fa_md_pdf.formats import DOCUMENT_EXTENSIONS
from fa_md_pdf.html_builder import HtmlBuildOptions, build_html, build_markdown_renderer
from fa_md_pdf.preview_worker import serve


@pytest.mark.parametrize("suffix", DOCUMENT_EXTENSIONS)
def test_supported_formats_open_edit_save_and_convert(tmp_path, suffix):
    source = tmp_path / ("سند" + suffix.upper())
    original = "# راهنمای فارسی\r\n\r\n**متن** و $x^2$\r\n"
    source.write_bytes(original.encode("utf-8-sig"))
    before = source.read_bytes()
    reply = io.StringIO()
    serve(Path("missing-assets"), io.StringIO(json.dumps({"id": 1, "path": str(source)}) + "\n"), reply)
    preview = json.loads(reply.getvalue())
    assert "<h1" in preview["html"] and "<strong>متن</strong>" in preview["html"]
    assert "<math" in preview["html"]
    assert source.read_bytes() == before
    snapshot = read_document(str(source))
    save_document(str(source), snapshot["text"] + "پایان\n", snapshot["revision"])
    assert source.read_bytes() == (original + "پایان\r\n").encode("utf-8-sig")
    job = build_jobs(source, None, output_format="docx")[0]
    assert job.output == source.with_suffix(".docx")
    assert main([str(source), "--format", "docx"]) == 0
    paragraphs = "\n".join(p.text for p in Document(job.output).paragraphs)
    assert "راهنمای فارسی" in paragraphs and "پایان" in paragraphs


def test_folder_discovery_finds_aliases_and_respects_custom_filter(tmp_path):
    nested = tmp_path / "nested"
    nested.mkdir()
    for index, suffix in enumerate(DOCUMENT_EXTENSIONS):
        (nested / (str(index) + suffix.upper())).write_text("# سند", encoding="utf8")
    (nested / "foreign.txt").write_text("plain", encoding="utf8")
    assert len(build_jobs(tmp_path, None)) == len(DOCUMENT_EXTENSIONS)
    assert len(build_jobs(tmp_path, None, extensions=[".md"])) == 1
    assert len(build_jobs(tmp_path, None, recursive=False)) == 0


def test_batch_rejects_competing_outputs_before_overwriting(tmp_path):
    (tmp_path / "guide.md").write_text("# اول", encoding="utf8")
    (tmp_path / "guide.mdx").write_text("# دوم", encoding="utf8")
    output = tmp_path / "guide.pdf"
    output.write_bytes(b"existing output")
    with pytest.raises(ConversionError, match="Multiple input files"):
        build_jobs(tmp_path, None)
    assert output.read_bytes() == b"existing output"


def test_registration_and_installer_cover_the_supported_family():
    assert EXTENSIONS == DOCUMENT_EXTENSIONS
    entries = {(entry.key, entry.name): entry.value for entry in build_entries("MdPersia.exe")}
    hook = Path("desktop-tauri/src-tauri/installer/hooks.nsh").read_text("utf8")
    for suffix in DOCUMENT_EXTENSIONS:
        assert entries[(PROGID_KEY + r"\Capabilities\FileAssociations", suffix)]
        assert f'Classes\\{suffix}\\OpenWithProgids" "MdPersia.Markdown"' in hook
        assert f'FileAssociations" "{suffix}" "MdPersia.Markdown"' in hook
        assert f'DeleteRegValue HKCU "Software\\Classes\\{suffix}\\OpenWithProgids"' in hook


MDX_SOURCE = """import Card from './Card.jsx'

export const title = "Test"

# راهنمای MDX

<Card title={title}>

**متن فارسی** و $x^2$

</Card>

<img src="https://example.invalid/tracker.png" onError={alert(1)} />

{title}

```javascript
import unchanged from './example.js'
```
"""


def test_mdx_preserves_dynamic_source_and_markdown_without_active_jsx(tmp_path):
    result = build_html(MDX_SOURCE, HtmlBuildOptions(source_path=tmp_path / "a.mdx"))
    from html import unescape
    from html.parser import HTMLParser

    class Visible(HTMLParser):
        def __init__(self):
            super().__init__()
            self.tags = []
            self.text = []

        def handle_starttag(self, tag, attrs):
            self.tags.append(tag)

        def handle_data(self, data):
            self.text.append(data)

    body = result.html.split('<main class="markdown-body">')[1].split("</main>")[0]
    visible = Visible()
    visible.feed(body)
    text = "".join(visible.text)
    assert "پیش‌نمایش ایستای MDX" in text
    for literal in ("import Card from './Card.jsx'", 'export const title = "Test"',
                    "<Card title={title}>", "</Card>", "{title}",
                    "import unchanged from './example.js'"):
        assert literal in unescape(text)
    assert not {"card", "img", "script"} & set(visible.tags)
    assert "<strong>متن فارسی</strong>" in body and "<math" in body
    assert "example.invalid" in text


def test_mdx_word_export_keeps_source_and_records_its_static_mode(tmp_path):
    source = tmp_path / "a.mdx"
    source.write_text(MDX_SOURCE, encoding="utf8")
    original = source.read_bytes()
    assert main([str(source), "--format", "docx"]) == 0
    text = "\n".join(p.text for p in Document(source.with_suffix(".docx")).paragraphs)
    assert "<Card title={title}>" in text and "import Card" in text
    assert "راهنمای MDX" in text and "پیش‌نمایش ایستای MDX" in text
    report = json.loads(source.with_suffix(".docx.report.json").read_text("utf8"))
    assert [issue["code"] for issue in report["issues"]] == ["mdx.static"]
    assert source.read_bytes() == original


def test_mdx_mode_does_not_change_html_in_standard_markdown():
    assert "<div" in build_markdown_renderer().render('<div dir="rtl">سلام</div>')
    source = Path("example.mdx")
    assert "&lt;div" in build_markdown_renderer(source_path=source).render('<div dir="rtl">سلام</div>')


def test_mdx_module_source_preserves_punctuation_and_code_fences():
    source = """import {
  One,
  Two
} from './module.js'

export const label = "**literal** $not_math$"

# عنوان

```text
import literal from './sample'
```
"""
    tokens = build_markdown_renderer(source_path=Path("a.mdx")).parse(source)
    code = [token for token in tokens if token.type == "fence"]
    assert [token.info for token in code] == ["javascript", "javascript", "text"]
    assert code[0].content == "import {\n  One,\n  Two\n} from './module.js'"
    assert code[1].content == 'export const label = "**literal** $not_math$"'
    assert code[2].content == "import literal from './sample'\n"
    assert any(token.type == "heading_open" for token in tokens)


def test_mdx_rtl_rewrite_refuses_before_changing_source(tmp_path):
    source = tmp_path / "a.mdx"
    source.write_text(MDX_SOURCE, encoding="utf8")
    original = source.read_bytes()
    assert main([str(source), "--wrap-rtl"]) == 1
    assert source.read_bytes() == original
    assert not source.with_name("a.rtl.mdx").exists()


@pytest.mark.parametrize("suffix", [ext for ext in DOCUMENT_EXTENSIONS if ext != ".mdx"])
def test_rtl_copy_keeps_the_original_format_without_duplicate_suffix(tmp_path, suffix):
    source = tmp_path / ("source" + suffix)
    source.write_text("# فارسی", encoding="utf8")
    assert main([str(source), "--wrap-rtl", "--wrap-rtl-suffix", ".rtl" + suffix]) == 0
    target = source.with_name("source.rtl" + suffix)
    assert target.is_file()
    assert not target.with_name(target.name + suffix).exists()
