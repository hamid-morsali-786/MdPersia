"""
Tests for fa-md-pdf converter orchestration, job planning, and conversion pipeline.
"""

from __future__ import annotations

import threading
from pathlib import Path
import pytest

from fa_md_pdf.converter import (
    ConversionError,
    ConvertJob,
    ConvertOptions,
    _pick_docx_font_family,
    build_jobs,
    convert_jobs,
    discover_markdown_files,
    is_markdown_file,
    normalize_extensions,
    output_for_file,
)


def test_normalize_extensions_edge_cases():
    assert normalize_extensions([]) == (".md", ".markdown")
    assert normalize_extensions(["   ", ""]) == (".md", ".markdown")
    assert normalize_extensions([".MD", "md", ".Markdown", "mD"]) == (".md", ".markdown")
    assert normalize_extensions(["txt", ".md"]) == (".txt", ".md")


def test_is_markdown_file(tmp_path: Path):
    f_md = tmp_path / "doc.md"
    f_md.write_text("content", encoding="utf-8")
    d_md = tmp_path / "folder.md"
    d_md.mkdir()
    f_txt = tmp_path / "doc.txt"
    f_txt.write_text("content", encoding="utf-8")

    assert is_markdown_file(f_md, [".md"]) is True
    assert is_markdown_file(d_md, [".md"]) is False
    assert is_markdown_file(f_txt, [".md"]) is False
    assert is_markdown_file(f_txt, [".md", ".txt"]) is True


def test_discover_markdown_files_flat_vs_recursive(tmp_path: Path):
    (tmp_path / "root.md").write_text("# Root", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "nested.md").write_text("# Nested", encoding="utf-8")

    flat = discover_markdown_files(tmp_path, recursive=False, extensions=[".md"])
    assert [p.name for p in flat] == ["root.md"]

    rec = discover_markdown_files(tmp_path, recursive=True, extensions=[".md"])
    assert sorted(p.name for p in rec) == ["nested.md", "root.md"]


def test_output_for_file():
    source = Path("docs/intro.md")

    # 1. output is None -> alongside source
    assert output_for_file(source, None, None, "pdf") == Path("docs/intro.pdf")
    assert output_for_file(source, None, None, "docx") == Path("docs/intro.docx")

    # 2. single file with output dir
    out_dir = Path("dist")
    assert output_for_file(source, None, out_dir, "pdf") == out_dir / "intro.pdf"

    # 3. single file with exact output filename
    exact_out = Path("dist/custom_name.pdf")
    assert output_for_file(source, None, exact_out, "pdf") == exact_out

    # 4. directory hierarchy preserved
    input_root = Path("docs")
    nested_source = Path("docs/advanced/guide.md")
    assert output_for_file(nested_source, input_root, out_dir, "pdf") == out_dir / "advanced/guide.pdf"

    # 5. target_name override
    assert output_for_file(source, None, None, target_name="custom.txt") == Path("docs/custom.txt")


def test_build_jobs_unsupported_format(tmp_path: Path):
    doc = tmp_path / "test.md"
    doc.write_text("hello", encoding="utf-8")
    with pytest.raises(ConversionError, match="Unsupported output format"):
        build_jobs(doc, None, output_format="html")


def test_build_jobs_missing_input_raises_error(tmp_path: Path):
    missing = tmp_path / "non_existent.md"
    with pytest.raises(ConversionError, match="Input path does not exist"):
        build_jobs(missing, None)


def test_build_jobs_dir_input_with_file_output_raises_error(tmp_path: Path):
    d = tmp_path / "my_docs"
    d.mkdir()
    with pytest.raises(ConversionError, match="must be a directory, not a file"):
        build_jobs(d, tmp_path / "output.pdf")


def test_build_jobs_keep_html(tmp_path: Path):
    doc = tmp_path / "page.md"
    doc.write_text("# Page", encoding="utf-8")
    jobs = build_jobs(doc, None, keep_html=True)
    assert len(jobs) == 1
    assert jobs[0].html_output == doc.with_suffix(".html")


def test_pick_docx_font_family():
    assert _pick_docx_font_family("Vazirmatn") == "Vazirmatn"
    assert _pick_docx_font_family('"Vazirmatn", Tahoma, sans-serif') == "Vazirmatn"
    assert _pick_docx_font_family("'B Nazanin', Arial") == "B Nazanin"
    assert _pick_docx_font_family("  ,  ") == "Vazirmatn"
    assert _pick_docx_font_family("") == "Vazirmatn"


def test_convert_jobs_empty_list():
    assert convert_jobs([], ConvertOptions()) == []


def test_convert_jobs_docx_multi_and_progress(tmp_path: Path):
    doc1 = tmp_path / "doc1.md"
    doc1.write_text("# سند یک", encoding="utf-8")
    doc2 = tmp_path / "doc2.md"
    doc2.write_text("# سند دو", encoding="utf-8")

    jobs = [
        ConvertJob(source=doc1, output=tmp_path / "doc1.docx"),
        ConvertJob(source=doc2, output=tmp_path / "doc2.docx"),
    ]

    progress_calls = []

    def on_progress(job, ok, err):
        progress_calls.append((job.source.name, ok, err))

    options = ConvertOptions(output_format="docx")
    results = convert_jobs(jobs, options=options, on_progress=on_progress)

    assert len(results) == 2
    assert all(r.ok for r in results)
    assert (tmp_path / "doc1.docx").is_file()
    assert (tmp_path / "doc2.docx").is_file()
    assert len(progress_calls) == 2
    assert progress_calls[0] == ("doc1.md", True, None)
    assert progress_calls[1] == ("doc2.md", True, None)


def test_convert_jobs_docx_cancellation(tmp_path: Path):
    doc1 = tmp_path / "c1.md"
    doc1.write_text("# ۱", encoding="utf-8")
    doc2 = tmp_path / "c2.md"
    doc2.write_text("# ۲", encoding="utf-8")

    jobs = [
        ConvertJob(source=doc1, output=tmp_path / "c1.docx"),
        ConvertJob(source=doc2, output=tmp_path / "c2.docx"),
    ]

    cancel_event = threading.Event()
    cancel_event.set()  # Cancel immediately

    results = convert_jobs(
        jobs,
        options=ConvertOptions(output_format="docx"),
        cancel_event=cancel_event,
    )
    assert len(results) == 0


def test_convert_jobs_docx_fail_fast(tmp_path: Path):
    missing_doc = tmp_path / "missing.md"
    valid_doc = tmp_path / "valid.md"
    valid_doc.write_text("# معتبر", encoding="utf-8")

    jobs = [
        ConvertJob(source=missing_doc, output=tmp_path / "missing.docx"),
        ConvertJob(source=valid_doc, output=tmp_path / "valid.docx"),
    ]

    results = convert_jobs(
        jobs,
        options=ConvertOptions(output_format="docx"),
        fail_fast=True,
    )
    # With fail_fast=True, execution terminates after first failure
    assert len(results) == 1
    assert results[0].ok is False
    assert results[0].error is not None


def test_convert_jobs_docx_cleans_mermaid_temp_dir(tmp_path: Path, monkeypatch, sample_png_bytes: bytes):
    import tempfile
    import fa_md_pdf.converter as conv_mod

    temp_mermaid_dir = Path(tempfile.mkdtemp(prefix="test-mermaid-leak-"))
    dummy_png = temp_mermaid_dir / "diagram.png"
    dummy_png.write_bytes(sample_png_bytes)

    def mock_render(*args, **kwargs):
        return {"graph TD\n    A --> B": dummy_png}

    monkeypatch.setattr("fa_md_pdf.mermaid_renderer.render_mermaid_to_png", mock_render)

    doc = tmp_path / "mermaid_doc.md"
    doc.write_text("# تست دیاگرام\n\n```mermaid\ngraph TD\n    A --> B\n```\n", encoding="utf-8")
    out = tmp_path / "out.docx"

    jobs = [ConvertJob(source=doc, output=out)]
    results = convert_jobs(jobs, options=ConvertOptions(output_format="docx"))

    assert len(results) == 1
    assert results[0].ok is True
    assert out.is_file()
    # The temporary mermaid directory must have been cleaned up
    assert not temp_mermaid_dir.exists()
