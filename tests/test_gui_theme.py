import tkinter as tk
import pytest
from fa_md_pdf.gui_theme import ModernThemeManager, ThemeColors, ThemeFonts


@pytest.fixture(scope="module")
def tk_root():
    root = tk.Tk()
    root.withdraw()
    yield root
    try:
        root.destroy()
    except Exception:
        pass


def test_theme_manager_initialization(tk_root):
    manager = ModernThemeManager(tk_root)
    assert manager.is_dark is True
    colors = manager.get_colors()
    assert isinstance(colors, ThemeColors)
    assert colors.bg.startswith("#")
    assert colors.accent_primary.startswith("#")
    fonts = manager.get_fonts()
    assert isinstance(fonts, ThemeFonts)


def test_theme_manager_toggle(tk_root):
    manager = ModernThemeManager(tk_root)
    initial_dark = manager.is_dark
    manager.toggle_theme()
    assert manager.is_dark != initial_dark
    manager.toggle_theme()
    assert manager.is_dark == initial_dark


def test_theme_apply_styles(tk_root):
    manager = ModernThemeManager(tk_root)
    colors = manager.apply_theme()
    assert colors is not None
    assert colors.card_bg.startswith("#")
