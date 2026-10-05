import tkinter as tk
from pathlib import Path
import pytest
from fa_md_pdf.gui_inspector import ParametersInspectorPanel
from fa_md_pdf.gui_theme import DARK_PALETTE



def test_inspector_build_options_pdf_parity(tk_root, tmp_path):
    panel = ParametersInspectorPanel(tk_root, tmp_path, lambda: None, lambda: None)
    panel.format_var.set("pdf")
    panel.page_format_var.set("A4")
    panel.margin_var.set("15mm")
    panel.landscape_var.set(True)
    panel.strip_emojis_var.set(True)
    panel.pdf_page_numbers_var.set(False)

    opts = panel.build_convert_options()
    assert opts.output_format == "pdf"
    assert opts.page_format == "A4"
    assert opts.margin == "15mm"
    assert opts.landscape is True
    assert opts.strip_emojis is True
    assert opts.include_page_numbers is False


def test_inspector_build_options_docx_parity(tk_root, tmp_path):
    panel = ParametersInspectorPanel(tk_root, tmp_path, lambda: None, lambda: None)
    panel.format_var.set("docx")
    panel.docx_image_scale_var.set(3)
    panel.docx_font_size_var.set(12)
    panel.docx_highlight_code_var.set(True)
    panel.docx_page_numbers_var.set(True)
    panel.docx_image_min_width_var.set("2.5")
    panel.docx_image_max_width_var.set("6.0")

    opts = panel.build_convert_options()
    assert opts.output_format == "docx"
    assert opts.docx_image_scale == 3
    assert opts.docx_font_size_pt == 12
    assert opts.docx_image_min_width == 2.5
    assert opts.docx_image_max_width == 6.0
    assert opts.highlight_code is True
    assert opts.include_page_numbers is True


def test_inspector_build_options_mermaid_and_fonts(tk_root, tmp_path):
    panel = ParametersInspectorPanel(tk_root, tmp_path, lambda: None, lambda: None)
    panel.mermaid_theme_var.set("forest")
    panel.mermaid_timeout_var.set("45")
    panel.ignore_mermaid_errors_var.set(True)
    panel.font_family_var.set("Vazirmatn")

    opts = panel.build_convert_options()
    assert opts.mermaid_theme == "forest"
    assert opts.mermaid_timeout_ms == 45000
    assert opts.ignore_mermaid_errors is True
    assert opts.font_family == "Vazirmatn"


def test_inspector_format_reaction_and_running_state(tk_root, tmp_path):
    panel = ParametersInspectorPanel(tk_root, tmp_path, lambda: None, lambda: None)
    panel.set_format("docx")
    assert panel.format_var.get() == "docx"

    panel.set_running_state(is_running=True)
    assert str(panel.convert_btn.cget("state")) == "disabled"
    assert str(panel.cancel_btn.cget("state")) == "normal"

    panel.set_running_state(is_running=False)
    assert str(panel.convert_btn.cget("state")) == "normal"
    assert str(panel.cancel_btn.cget("state")) == "disabled"


def test_inspector_apply_colors(tk_root, tmp_path):
    panel = ParametersInspectorPanel(tk_root, tmp_path, lambda: None, lambda: None)
    panel.apply_colors(DARK_PALETTE)
    assert panel.convert_btn is not None
