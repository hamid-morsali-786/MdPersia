import threading
import tkinter as tk
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from fa_md_pdf.gui import MainWindow
from fa_md_pdf.gui_inspector import ParametersInspectorPanel
from fa_md_pdf.gui_queue import DocumentQueuePanel


def test_auto_detect_assets(tk_root, tmp_path):
    browsers_dir = tmp_path / "browsers"
    browsers_dir.mkdir()
    vendor_dir = tmp_path / "vendor"
    vendor_dir.mkdir()
    mermaid_file = vendor_dir / "mermaid.min.js"
    mermaid_file.write_text("// mermaid", encoding="utf-8")
    fonts_dir = tmp_path / "fonts"
    fonts_dir.mkdir()

    panel = ParametersInspectorPanel(tk_root, tmp_path, lambda: None, lambda: None)
    panel.auto_detect_assets(tmp_path)

    assert panel.browsers_path_var.get() == str(browsers_dir.resolve())
    assert panel.mermaid_js_var.get() == str(mermaid_file.resolve())
    assert panel.font_dir_var.get() == str(fonts_dir.resolve())


def test_page_geometry_controls_active_for_pdf_and_docx(tk_root, tmp_path):
    panel = ParametersInspectorPanel(tk_root, tmp_path, lambda: None, lambda: None)

    panel.set_format("pdf")
    for ctrl in panel._page_geometry_controls:
        assert str(ctrl.cget("state")) == "normal"

    panel.set_format("docx")
    for ctrl in panel._page_geometry_controls:
        assert str(ctrl.cget("state")) == "normal"

    panel.set_format("wrap-rtl")
    for ctrl in panel._page_geometry_controls:
        assert str(ctrl.cget("state")) == "disabled"


def test_queue_relative_path_preserves_structure(tk_root, tmp_path):
    sub = tmp_path / "sub" / "nested"
    sub.mkdir(parents=True)
    f = sub / "doc.md"
    f.write_text("# Test", encoding="utf-8")

    panel = DocumentQueuePanel(tk_root)
    panel.add_directory(tmp_path, recursive=True)

    items = panel.get_queue_items()
    assert len(items) == 1
    assert items[0].relative_path == Path("sub") / "nested" / "doc.md"

    app = MainWindow(tk_root, tmp_path)
    out_dir = tmp_path / "out"
    jobs = app._create_jobs_from_queue(items, out_dir, "pdf", False)
    assert jobs[0].output == out_dir / "sub" / "nested" / "doc.pdf"


def test_queue_reset_statuses(tk_root, tmp_path):
    f = tmp_path / "err.md"
    f.write_text("# Err", encoding="utf-8")

    panel = DocumentQueuePanel(tk_root)
    panel.add_files([f])
    panel.update_status(f, "خطا", error="Syntax error")

    items = panel.get_queue_items()
    assert items[0].status == "خطا"
    assert items[0].error == "Syntax error"

    panel.reset_statuses()
    assert items[0].status == "در انتظار"
    assert items[0].error is None


def test_watch_thread_guard_prevents_collision(tk_root, tmp_path):
    app = MainWindow(tk_root, tmp_path)
    app.is_watching = True
    app._watched_options = app._build_convert_options()

    dummy_thread = MagicMock()
    dummy_thread.is_alive.return_value = True
    app.conversion_thread = dummy_thread

    # Should exit early without spawning new thread or failing
    app._check_watched_files()
    assert dummy_thread.is_alive.called


def test_single_file_custom_output_name(tk_root, tmp_path):
    app = MainWindow(tk_root, tmp_path)
    f = tmp_path / "report.md"
    f.write_text("# Test", encoding="utf-8")
    custom_out = tmp_path / "custom_report_name.pdf"

    jobs = app._create_jobs_from_queue([f], custom_out, "pdf", False)
    assert len(jobs) == 1
    assert jobs[0].output == custom_out


def test_queue_context_menu_actions(tk_root, tmp_path):
    panel = DocumentQueuePanel(tk_root)
    f = tmp_path / "item.md"
    f.write_text("# Test", encoding="utf-8")
    panel.add_files([f])

    # Select the item
    key = str(f.resolve())
    panel.tree.selection_set(key)

    # Context menu exists and has items
    assert panel.context_menu.index("end") >= 3
    # Remove via context action
    panel.remove_selected()
    assert len(panel.get_files()) == 0

