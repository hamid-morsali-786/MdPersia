import tkinter as tk
from pathlib import Path
import pytest
from fa_md_pdf.gui_theme import DARK_PALETTE
from fa_md_pdf.gui_workspace import LivePreviewConsolePanel, StatusBarPanel


def test_console_append_and_clear(tk_root):
    panel = LivePreviewConsolePanel(tk_root)
    panel.append_log("Starting conversion...", level="info")
    panel.append_log("File doc1.md converted successfully", level="success")
    panel.append_log("Failed to convert doc2.md", level="error")

    content = panel.get_log_text()
    assert "Starting conversion..." in content
    assert "File doc1.md converted successfully" in content
    assert "Failed to convert doc2.md" in content

    panel.clear_logs()
    assert panel.get_log_text().strip() == ""


def test_preview_panel_content(tk_root, tmp_path):
    f = tmp_path / "test.md"
    f.write_text("# Persian Document\nاین یک متن تستی است.", encoding="utf-8")

    panel = LivePreviewConsolePanel(tk_root)
    panel.set_preview_file(f)
    assert "Persian Document" in panel.get_preview_text()
    assert "این یک متن تستی است" in panel.get_preview_text()

    panel.set_preview_file(None)
    assert "فایلی انتخاب نشده است" in panel.get_preview_text()


def test_status_bar_progress(tk_root):
    bar = StatusBarPanel(tk_root)
    bar.set_progress(3, 10)
    assert bar.progress_var.get() == 30.0

    bar.set_status("تبدیل ۳ از ۱۰ فایل انجام شد", badge_type="running")
    assert "۳ از ۱۰" in bar.status_var.get()

    bar.reset()
    assert bar.progress_var.get() == 0.0
    assert "آماده" in bar.status_var.get()


def test_workspace_apply_colors(tk_root):
    panel = LivePreviewConsolePanel(tk_root)
    panel.apply_colors(DARK_PALETTE)
    bar = StatusBarPanel(tk_root)
    bar.apply_colors(DARK_PALETTE)
    assert panel.console_text.cget("background") == DARK_PALETTE.terminal_bg
