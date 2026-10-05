import tkinter as tk
from pathlib import Path
import pytest
from fa_md_pdf.gui import MainWindow



def test_main_window_init(tk_root, tmp_path):
    app = MainWindow(tk_root, tmp_path)
    assert app.pdf_page_numbers_var.get() is True
    assert app.docx_page_numbers_var.get() is True
    assert app.docx_highlight_code_var.get() is True
    assert app.watch_var.get() is False


def test_main_window_build_options_pdf(tk_root, tmp_path):
    app = MainWindow(tk_root, tmp_path)
    app.format_var.set("pdf")
    app.pdf_page_numbers_var.set(False)
    opts = app._build_convert_options()
    assert opts.output_format == "pdf"
    assert opts.include_page_numbers is False


def test_main_window_build_options_docx(tk_root, tmp_path):
    app = MainWindow(tk_root, tmp_path)
    app.format_var.set("docx")
    app.docx_page_numbers_var.set(True)
    app.docx_highlight_code_var.set(False)
    opts = app._build_convert_options()
    assert opts.output_format == "docx"
    assert opts.include_page_numbers is True
    assert opts.highlight_code is False


def test_main_window_watch_mode_cancel(tk_root, tmp_path):
    app = MainWindow(tk_root, tmp_path)
    app.watch_var.set(True)
    app.is_watching = True
    app._cancel_conversion()
    assert app.is_watching is False
    assert app.watch_var.get() is False


def test_main_window_modern_panels(tk_root, tmp_path):
    app = MainWindow(tk_root, tmp_path)
    assert hasattr(app, "queue_panel")
    assert hasattr(app, "inspector_panel")
    assert hasattr(app, "workspace_panel")
    assert hasattr(app, "status_bar")
    assert hasattr(app, "theme_manager")

    # Add a file to queue
    f = tmp_path / "sample.md"
    f.write_text("# Hello World", encoding="utf-8")
    app.queue_panel.add_files([f])
    assert len(app.queue_panel.get_files()) == 1

    # Check preview selection
    app.queue_panel.on_file_selected(f)
    assert "Hello World" in app.workspace_panel.get_preview_text()


def test_main_window_theme_toggle(tk_root, tmp_path):
    app = MainWindow(tk_root, tmp_path)
    dark_before = app.theme_manager.is_dark
    app._toggle_theme()
    assert app.theme_manager.is_dark != dark_before
