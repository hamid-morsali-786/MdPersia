import queue
import threading
import time
import tkinter as tk
from pathlib import Path
import pytest
from fa_md_pdf.gui import MainWindow
from fa_md_pdf.gui_inspector import ParametersInspectorPanel
from fa_md_pdf.gui_queue import DocumentQueuePanel


def test_format_reactivity_enables_disables_widgets(tk_root, tmp_path):
    panel = ParametersInspectorPanel(tk_root, tmp_path, lambda: None, lambda: None)

    # Initially PDF
    panel.set_format("pdf")
    assert panel.is_docx_active() is False

    # Switch to DOCX
    panel.set_format("docx")
    assert panel.is_docx_active() is True

    # Switch to wrap-rtl
    panel.set_format("wrap-rtl")
    assert panel.is_docx_active() is False


def test_queue_uses_custom_extensions(tk_root, tmp_path):
    f1 = tmp_path / "custom.special"
    f2 = tmp_path / "normal.md"
    f1.write_text("special", encoding="utf-8")
    f2.write_text("normal", encoding="utf-8")

    panel = DocumentQueuePanel(
        tk_root,
        get_extensions=lambda: [".special"],
    )
    added = panel.add_directory(tmp_path, recursive=False)
    assert added == 1
    assert panel.get_files()[0].name == "custom.special"


def test_output_file_collision_prevention(tk_root, tmp_path):
    app = MainWindow(tk_root, tmp_path)
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    app.output_var.set(str(out_dir))

    d1 = tmp_path / "dir1"
    d2 = tmp_path / "dir2"
    d1.mkdir()
    d2.mkdir()
    f1 = d1 / "same_name.md"
    f2 = d2 / "same_name.md"
    f1.write_text("# Doc 1", encoding="utf-8")
    f2.write_text("# Doc 2", encoding="utf-8")

    jobs = app._create_jobs_from_queue([f1, f2], out_dir, "pdf", False)
    assert len(jobs) == 2
    # The output paths must NOT collide!
    assert jobs[0].output != jobs[1].output


def test_wrap_rtl_threaded_execution(tk_root, tmp_path):
    app = MainWindow(tk_root, tmp_path)
    f = tmp_path / "doc.md"
    f.write_text("# سلام دنیا", encoding="utf-8")
    app.queue_panel.add_files([f])
    app.format_var.set("wrap-rtl")

    # Start conversion in wrap-rtl mode
    app._start_conversion()
    # conversion_thread must exist and run asynchronously
    assert app.conversion_thread is not None
