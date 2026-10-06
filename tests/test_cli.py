"""
Tests for fa-md-pdf CLI argument parsing, option resolution, and execution workflows.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import pytest

from fa_md_pdf.cli import (
    build_parser,
    main,
    resolve_browsers_setting,
    resolve_font_settings,
    resolve_mermaid_source,
    validate_dir_option,
    validate_file_option,
)
from fa_md_pdf.converter import ConversionError


def test_parser_defaults():
    parser = build_parser()
    args = parser.parse_args(["input.md"])

    assert args.input == Path("input.md")
    assert args.output is None
    assert args.format == "pdf"
    assert args.docx_image_scale == 3
    assert args.docx_font_size == 12
    assert args.recursive is True
    assert args.extensions == [".md", ".markdown"]
    assert args.page_format == "A4"
    assert args.margin == "15mm"
    assert args.landscape is False
    assert args.strip_emojis is False
    assert args.keep_html is False
    assert args.fail_fast is False
    assert args.verbose is False
    assert args.wrap_rtl is False
    assert args.wrap_rtl_suffix == ".rtl"


def test_parser_custom_options():
    parser = build_parser()
    args = parser.parse_args([
        "my_dir",
        "-o", "output_dir",
        "-f", "docx",
        "--docx-image-scale", "4",
        "--docx-font-size", "14",
        "--no-recursive",
        "--page-format", "Letter",
        "--margin", "10mm",
        "--landscape",
        "--strip-emojis",
        "--keep-html",
        "--verbose",
        "--wrap-rtl",
        "--wrap-rtl-suffix", ".ar",
    ])

    assert args.input == Path("my_dir")
    assert args.output == Path("output_dir")
    assert args.format == "docx"
    assert args.docx_image_scale == 4
    assert args.docx_font_size == 14
    assert args.recursive is False
    assert args.page_format == "Letter"
    assert args.margin == "10mm"
    assert args.landscape is True
    assert args.strip_emojis is True
    assert args.keep_html is True
    assert args.verbose is True
    assert args.wrap_rtl is True
    assert args.wrap_rtl_suffix == ".ar"


def test_parser_rejects_invalid_format():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["input.md", "-f", "txt"])


def test_validate_file_option(tmp_path: Path):
    assert validate_file_option(None, "File") is None

    valid_file = tmp_path / "valid.txt"
    valid_file.write_text("ok", encoding="utf-8")
    assert validate_file_option(valid_file, "File") == valid_file.resolve()

    non_existent = tmp_path / "missing.txt"
    with pytest.raises(ConversionError, match="does not exist"):
        validate_file_option(non_existent, "File")

    directory = tmp_path / "dir"
    directory.mkdir()
    with pytest.raises(ConversionError, match="must be a file"):
        validate_file_option(directory, "File")


def test_validate_dir_option(tmp_path: Path):
    assert validate_dir_option(None, "Directory") is None

    valid_dir = tmp_path / "folder"
    valid_dir.mkdir()
    assert validate_dir_option(valid_dir, "Directory") == valid_dir.resolve()

    non_existent = tmp_path / "missing_dir"
    with pytest.raises(ConversionError, match="does not exist"):
        validate_dir_option(non_existent, "Directory")

    file_path = tmp_path / "some_file.txt"
    file_path.write_text("ok", encoding="utf-8")
    with pytest.raises(ConversionError, match="must be a directory"):
        validate_dir_option(file_path, "Directory")


def test_resolve_mermaid_source_url():
    args = argparse.Namespace(mermaid_url="https://cdn.test/mermaid.js", mermaid_js=None)
    assert resolve_mermaid_source(args, Path.cwd()) == "https://cdn.test/mermaid.js"


def test_resolve_mermaid_source_custom_file(tmp_path: Path):
    custom_js = tmp_path / "custom_mermaid.js"
    custom_js.write_text("// mermaid", encoding="utf-8")
    args = argparse.Namespace(mermaid_url=None, mermaid_js=custom_js)
    assert resolve_mermaid_source(args, tmp_path) == str(custom_js.resolve())


def test_resolve_mermaid_source_missing_raises_error(tmp_path: Path):
    args = argparse.Namespace(mermaid_url=None, mermaid_js=None)
    empty_root = tmp_path / "empty_project"
    empty_root.mkdir()
    with pytest.raises(ConversionError, match="Mermaid JS file was not found"):
        resolve_mermaid_source(args, empty_root)


def test_resolve_font_settings(tmp_path: Path):
    font_file = tmp_path / "Font.ttf"
    font_file.write_text("f", encoding="utf-8")
    args = argparse.Namespace(font_file=font_file, font_dir=None)
    f_file, f_dir = resolve_font_settings(args, tmp_path)
    assert f_file == font_file.resolve()
    assert f_dir is None

    font_dir = tmp_path / "fonts_folder"
    font_dir.mkdir()
    args2 = argparse.Namespace(font_file=None, font_dir=font_dir)
    f_file2, f_dir2 = resolve_font_settings(args2, tmp_path)
    assert f_file2 is None
    assert f_dir2 == font_dir.resolve()


def test_resolve_browsers_setting(tmp_path: Path, monkeypatch):
    browsers_dir = tmp_path / "browsers"
    browsers_dir.mkdir()
    args = argparse.Namespace(browsers_path=browsers_dir)
    monkeypatch.delenv("PLAYWRIGHT_BROWSERS_PATH", raising=False)
    res = resolve_browsers_setting(args, tmp_path)
    assert res == browsers_dir.resolve()


def test_cli_main_missing_input_exits_with_error():
    with pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.value.code != 0


def test_cli_main_non_existent_input_returns_1(tmp_path: Path, capsys):
    ret = main([str(tmp_path / "non_existent.md")])
    assert ret == 1
    captured = capsys.readouterr()
    assert "does not exist" in captured.err


def test_cli_main_non_markdown_file_returns_1(tmp_path: Path, capsys):
    text_file = tmp_path / "doc.txt"
    text_file.write_text("sample", encoding="utf-8")
    ret = main([str(text_file)])
    assert ret == 1
    captured = capsys.readouterr()
    assert "not a supported Markdown file" in captured.err


def test_cli_main_empty_directory_returns_2(tmp_path: Path, capsys):
    empty_dir = tmp_path / "empty_dir"
    empty_dir.mkdir()
    ret = main([str(empty_dir)])
    assert ret == 2
    captured = capsys.readouterr()
    assert "No Markdown files found" in captured.err


def test_cli_main_dir_input_with_file_output_returns_1(tmp_path: Path, capsys):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "a.md").write_text("# A", encoding="utf-8")
    ret = main([str(docs_dir), "-o", str(tmp_path / "out.pdf")])
    assert ret == 1
    captured = capsys.readouterr()
    assert "When input is a directory, --output must be a directory" in captured.err


def test_cli_main_docx_conversion_success(tmp_path: Path, capsys):
    doc_path = tmp_path / "test_doc.md"
    doc_path.write_text("# سلام دنیا\n\nاین یک تست است.", encoding="utf-8")
    out_docx = tmp_path / "test_doc.docx"

    ret = main([str(doc_path), "-o", str(out_docx), "-f", "docx", "--verbose"])
    assert ret == 0
    assert out_docx.is_file()
    captured = capsys.readouterr()
    assert "1 succeeded, 0 failed" in captured.out


def test_cli_main_wrap_rtl_single_file(tmp_path: Path, capsys):
    doc_path = tmp_path / "persian.md"
    doc_path.write_text("متن آزمایشی فارسی بدون تگ رپ.", encoding="utf-8")

    ret = main([str(doc_path), "--wrap-rtl"])
    assert ret == 0
    expected_output = tmp_path / "persian.rtl.md"
    assert expected_output.is_file()
    content = expected_output.read_text(encoding="utf-8")
    assert '<div dir="rtl">' in content


def test_cli_main_wrap_rtl_in_place_overwrite(tmp_path: Path):
    doc_path = tmp_path / "inplace.md"
    doc_path.write_text("متن فارسی جهت بازنویسی درجا.", encoding="utf-8")

    ret = main([str(doc_path), "--wrap-rtl", "--wrap-rtl-suffix", ""])
    assert ret == 0
    content = doc_path.read_text(encoding="utf-8")
    assert '<div dir="rtl">' in content


def test_cli_main_wrap_rtl_directory(tmp_path: Path):
    docs = tmp_path / "wrap_docs"
    docs.mkdir()
    (docs / "doc1.md").write_text("متن سند اول", encoding="utf-8")
    (docs / "doc2.md").write_text("متن سند دوم", encoding="utf-8")

    ret = main([str(docs), "--wrap-rtl"])
    assert ret == 0
    assert (docs / "doc1.rtl.md").is_file()
    assert (docs / "doc2.rtl.md").is_file()


def test_cli_main_wrap_rtl_empty_dir_returns_2(tmp_path: Path, capsys):
    empty = tmp_path / "no_md"
    empty.mkdir()
    ret = main([str(empty), "--wrap-rtl"])
    assert ret == 2
    captured = capsys.readouterr()
    assert "No Markdown files found" in captured.err


def test_cli_main_wrap_rtl_missing_input_returns_1(tmp_path: Path, capsys):
    ret = main([str(tmp_path / "missing.md"), "--wrap-rtl"])
    assert ret == 1
    captured = capsys.readouterr()
    assert "input does not exist" in captured.err


def test_cli_main_wrap_rtl_cp1256_legacy_encoding(tmp_path: Path, capsys):
    # CP1256 encoded Persian text ("سلام دنیا")
    cp_file = tmp_path / "legacy_persian.md"
    # "سلام" encoded in cp1256: \xd3\xe1\xc7\xe3
    cp_file.write_bytes(b"\xd3\xe1\xc7\xe3 \xe3\xca\xe4")

    ret = main([str(cp_file), "--wrap-rtl"])
    assert ret == 0
    expected_out = tmp_path / "legacy_persian.rtl.md"
    assert expected_out.is_file()
    content = expected_out.read_text(encoding="utf-8")
    assert '<div dir="rtl">' in content
    assert "سلام" in content


def test_mdpersia_package_exports():
    import mdpersia
    from fa_md_pdf import __version__

    assert mdpersia.__version__ == __version__
    assert callable(mdpersia.main)
    assert callable(mdpersia.convert_jobs)
    assert callable(mdpersia.build_jobs)
    assert mdpersia.ConvertOptions is not None
    assert mdpersia.ConversionError is not None
