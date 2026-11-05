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


@pytest.mark.parametrize('changed_ok', [True, False])
def test_watch_reconversion_reports_actual_result_and_returns_to_waiting(tmp_path, monkeypatch, capsys, changed_ok):
    import os
    import time
    from fa_md_pdf import converter

    source = tmp_path / 'watched.md'
    source.write_text('# Watch test', encoding='utf-8')
    calls = []

    def convert(jobs, **_kwargs):
        calls.append(jobs)
        ok = len(calls) == 1 or changed_ok
        return [converter.ConvertResult(job, ok, None if ok else 'reconversion failed') for job in jobs]

    ticks = 0

    def tick(_seconds):
        nonlocal ticks
        ticks += 1
        if ticks > 1:
            raise KeyboardInterrupt
        later = source.stat().st_mtime + 2
        os.utime(source, (later, later))

    monkeypatch.setattr(converter, 'convert_jobs', convert)
    monkeypatch.setattr(time, 'sleep', tick)
    assert main([str(source), '--format', 'docx', '--watch']) == 0
    captured = capsys.readouterr()
    assert len(calls) == 2
    assert '[fa-md-pdf] Waiting for changes.' in captured.out
    assert captured.out.count('OK  ') == (2 if changed_ok else 1)
    assert ('reconversion failed' in captured.err) is (not changed_ok)


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


# --- GUI launcher: a second launch must reuse the running dev server --------------
# Double-clicking .md files repeatedly should not pile up heavy `npm run dev` processes.

class _Response:
    def __init__(self, status: int, payload: bytes = b'{"app":"MdPersia"}'):
        self.status = status
        self.payload = payload

    def read(self):
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_dev_server_running_only_answers_true_for_a_live_server(monkeypatch):
    import urllib.request

    from fa_md_pdf import cli

    monkeypatch.setattr(urllib.request, "urlopen", lambda url, timeout=None: _Response(200))
    assert cli._dev_server_running() is True

    monkeypatch.setattr(urllib.request, "urlopen", lambda url, timeout=None: _Response(200, b'{}'))
    assert cli._dev_server_running() is False

    def refused(url, timeout=None):
        raise OSError("connection refused")

    monkeypatch.setattr(urllib.request, "urlopen", refused)
    assert cli._dev_server_running() is False


def test_gui_reuses_a_running_server_and_never_spawns_npm(tmp_path, monkeypatch):
    from fa_md_pdf import cli

    (tmp_path / "desktop-tauri").mkdir()
    doc = tmp_path / "note.md"
    doc.write_text("# note\n", encoding="utf-8")

    monkeypatch.setattr(cli, "find_project_root", lambda *a, **k: tmp_path)
    monkeypatch.setattr(cli, "_dev_server_running", lambda *a, **k: True)
    monkeypatch.setattr(cli, "_handoff_gui_file", lambda *a, **k: False)
    monkeypatch.setattr(cli, "_wait_gui_window", lambda *a: True)

    opened: list[str] = []
    spawned: list = []
    monkeypatch.setattr(cli, "_open_gui_window", lambda url: opened.append(url))
    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: spawned.append(a))

    assert main(["--gui", str(doc)]) == 0
    assert spawned == []
    assert len(opened) == 1 and "?file=" in opened[0] and "note.md" in opened[0]


class _Proc:
    def poll(self):
        return None


def test_gui_launch_passes_a_python_interpreter_to_the_dev_server(tmp_path, monkeypatch):
    from fa_md_pdf import cli

    vite_cli = tmp_path / "desktop-tauri" / "node_modules" / "vite" / "bin" / "vite.js"
    vite_cli.parent.mkdir(parents=True)
    vite_cli.write_text("", encoding="utf-8")
    monkeypatch.setattr(cli, "find_project_root", lambda *a, **k: tmp_path)
    ready = iter([False, True, False, True])
    monkeypatch.setattr(cli, "_dev_server_running", lambda *a, **k: next(ready))
    monkeypatch.setattr(cli, "_open_gui_window", lambda url: None)
    monkeypatch.setattr(cli, "_wait_gui_window", lambda *a: True)
    monkeypatch.setattr("shutil.which", lambda name: "node.exe")

    spawned: list = []
    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: (spawned.append((a, k)), _Proc())[1])

    # An explicitly chosen interpreter wins: the launching one may lack the conversion deps.
    monkeypatch.setenv("PYTHON_EXECUTABLE", r"C:\py\good\python.exe")
    assert main(["--gui"]) == 0
    assert spawned[0][1]["env"]["PYTHON_EXECUTABLE"] == r"C:\py\good\python.exe"

    monkeypatch.delenv("PYTHON_EXECUTABLE")
    assert main(["--gui"]) == 0
    assert spawned[1][1]["env"]["PYTHON_EXECUTABLE"] == cli.sys.executable


def test_gui_handoff_keeps_the_existing_window(tmp_path, monkeypatch):
    from fa_md_pdf import cli

    (tmp_path / "desktop-tauri").mkdir()
    doc = tmp_path / "سند من.MD"
    doc.write_text("# سلام", encoding="utf-8")
    monkeypatch.setattr(cli, "find_project_root", lambda *a: tmp_path)
    monkeypatch.setattr(cli, "_dev_server_running", lambda: True)
    delivered = []
    monkeypatch.setattr(cli, "_handoff_gui_file", lambda path: delivered.append(path) or True)
    focused = []
    monkeypatch.setattr(cli, "_focus_gui_window", lambda: focused.append(True))
    monkeypatch.setattr(cli, "_open_gui_window", lambda url: pytest.fail("Opened a second window"))
    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: pytest.fail("Spawned another server"))
    assert cli.main(["--gui", str(doc)]) == 0
    assert delivered == [str(doc.resolve())]
    assert focused == [True]


def test_gui_uses_current_build_and_falls_back_when_sources_change(tmp_path):
    import os

    from fa_md_pdf.cli import _frontend_build_current

    assert not _frontend_build_current(tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "dist").mkdir()
    source = tmp_path / "src" / "App.tsx"
    source.write_text("source", encoding="utf-8")
    (tmp_path / "dist" / "index.html").write_text("built UI", encoding="utf-8")
    (tmp_path / "dist" / "desktop-server.mjs").write_text("built bridge", encoding="utf-8")
    stamp = tmp_path / "dist" / ".mdpersia-build"
    stamp.write_text("built", encoding="utf-8")
    os.utime(stamp, ns=(source.stat().st_mtime_ns + 1000000,) * 2)
    assert _frontend_build_current(tmp_path)
    test_source = tmp_path / "src" / "queue.test.ts"
    test_source.write_text("test-only edit", encoding="utf-8")
    os.utime(test_source, ns=(stamp.stat().st_mtime_ns + 1000000,) * 2)
    assert _frontend_build_current(tmp_path)
    os.utime(source, ns=(stamp.stat().st_mtime_ns + 1000000,) * 2)
    assert not _frontend_build_current(tmp_path)


def test_gui_entrypoint_does_not_import_conversion_runtime():
    import os
    import subprocess
    import sys

    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
    check = subprocess.run([
        sys.executable, "-c",
        "import mdpersia; from fa_md_pdf.cli import build_parser; import sys; "
        "assert 'fa_md_pdf.converter' not in sys.modules; "
        "assert not any(m.startswith('playwright') for m in sys.modules); "
        "assert build_parser().parse_args(['--gui']).gui",
    ], capture_output=True, text=True, env=env)
    assert check.returncode == 0, check.stderr


def test_open_gui_window_falls_back_to_the_default_browser(monkeypatch, tmp_path):
    import webbrowser

    from fa_md_pdf import cli

    opened: list[str] = []
    monkeypatch.setattr(webbrowser, "open", lambda url: opened.append(url))
    monkeypatch.setattr(cli.sys, "platform", "win32")
    monkeypatch.setenv("PROGRAMFILES", str(tmp_path))
    monkeypatch.setenv("PROGRAMFILES(X86)", str(tmp_path))

    cli._open_gui_window("http://localhost:1420")
    assert opened == ["http://localhost:1420"]
