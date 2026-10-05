"""Modern design system and theme manager for fa-md-pdf GUI."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import font, ttk


@dataclass(frozen=True)
class ThemeColors:
    """Color tokens for application styling."""

    bg: str
    card_bg: str
    input_bg: str
    border: str
    border_focus: str
    text_main: str
    text_muted: str
    accent_primary: str
    accent_hover: str
    accent_text: str
    success: str
    error: str
    warning: str
    tree_selected: str
    terminal_bg: str
    terminal_fg: str


@dataclass(frozen=True)
class ThemeFonts:
    """Typography fonts for the interface."""

    ui: font.Font
    ui_bold: font.Font
    title: font.Font
    mono: font.Font


DARK_PALETTE = ThemeColors(
    bg="#0b1120",
    card_bg="#131d31",
    input_bg="#0b1120",
    border="#26354f",
    border_focus="#3b82f6",
    text_main="#f1f5f9",
    text_muted="#94a3b8",
    accent_primary="#2563eb",
    accent_hover="#1d4ed8",
    accent_text="#ffffff",
    success="#10b981",
    error="#ef4444",
    warning="#f59e0b",
    tree_selected="#1e3a5f",
    terminal_bg="#060913",
    terminal_fg="#cbd5e1",
)

LIGHT_PALETTE = ThemeColors(
    bg="#f1f5f9",
    card_bg="#ffffff",
    input_bg="#ffffff",
    border="#cbd5e1",
    border_focus="#2563eb",
    text_main="#0f172a",
    text_muted="#64748b",
    accent_primary="#2563eb",
    accent_hover="#1d4ed8",
    accent_text="#ffffff",
    success="#059669",
    error="#dc2626",
    warning="#d97706",
    tree_selected="#dbeafe",
    terminal_bg="#0f172a",
    terminal_fg="#e2e8f0",
)


class ModernThemeManager:
    """Manages Dark/Light themes and TTK styling for the application."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.is_dark: bool = True
        self.style = ttk.Style(root)
        self.fonts = self._resolve_fonts()
        self.apply_theme()

    def get_colors(self) -> ThemeColors:
        """Return the current active color palette."""
        return DARK_PALETTE if self.is_dark else LIGHT_PALETTE

    def get_fonts(self) -> ThemeFonts:
        """Return typography definitions."""
        return self.fonts

    def toggle_theme(self) -> bool:
        """Toggle between Dark and Light mode."""
        self.is_dark = not self.is_dark
        self.apply_theme()
        return self.is_dark

    def apply_theme(self, style: ttk.Style | None = None) -> ThemeColors:
        """Apply active theme styles to the Tkinter/TTK environment."""
        if style:
            self.style = style
        colors = self.get_colors()
        self.root.configure(bg=colors.bg)
        self._configure_base_styles(colors)
        self._configure_control_styles(colors)
        self._configure_view_styles(colors)
        return colors

    def _resolve_fonts(self) -> ThemeFonts:
        """Detect and load modern typography with fallbacks."""
        families = font.families(self.root)
        ui_family = "Vazirmatn" if "Vazirmatn" in families else "Segoe UI"
        if ui_family not in families and "Tahoma" in families:
            ui_family = "Tahoma"

        mono_family = "Consolas"
        for candidate in ("JetBrains Mono", "Cascadia Code", "Consolas"):
            if candidate in families:
                mono_family = candidate
                break

        return ThemeFonts(
            ui=font.Font(family=ui_family, size=9),
            ui_bold=font.Font(family=ui_family, size=9, weight="bold"),
            title=font.Font(family=ui_family, size=11, weight="bold"),
            mono=font.Font(family=mono_family, size=9),
        )

    def _configure_base_styles(self, c: ThemeColors) -> None:
        """Configure foundational styles for containers and text."""
        self.style.theme_use("clam")
        self.style.configure(".", background=c.bg, foreground=c.text_main, font=self.fonts.ui)
        self.style.configure("TFrame", background=c.bg)
        self.style.configure("Card.TFrame", background=c.card_bg)
        self.style.configure("TLabel", background=c.bg, foreground=c.text_main)
        self.style.configure("Card.TLabel", background=c.card_bg, foreground=c.text_main)
        self.style.configure("Muted.TLabel", foreground=c.text_muted)
        self.style.configure("Title.TLabel", font=self.fonts.title, foreground=c.text_main)
        self.style.configure(
            "TLabelframe", background=c.card_bg, foreground=c.text_main, bordercolor=c.border
        )
        self.style.configure(
            "TLabelframe.Label", background=c.card_bg, foreground=c.text_main, font=self.fonts.ui_bold
        )

    def _configure_control_styles(self, c: ThemeColors) -> None:
        """Configure interactive inputs and buttons."""
        self.style.configure(
            "TButton",
            background=c.card_bg,
            foreground=c.text_main,
            bordercolor=c.border,
            focuscolor=c.accent_primary,
            padding=(8, 4),
        )
        self.style.map(
            "TButton",
            background=[("active", c.border), ("disabled", c.bg)],
            foreground=[("disabled", c.text_muted)],
        )
        self.style.configure(
            "Primary.TButton",
            background=c.accent_primary,
            foreground=c.accent_text,
            font=self.fonts.ui_bold,
            padding=(10, 6),
        )
        self.style.map("Primary.TButton", background=[("active", c.accent_hover)])
        self.style.configure(
            "TEntry",
            fieldbackground=c.input_bg,
            foreground=c.text_main,
            insertcolor=c.text_main,
            bordercolor=c.border,
            padding=4,
        )
        self.style.configure("TCheckbutton", background=c.card_bg, foreground=c.text_main)
        self.style.configure("TRadiobutton", background=c.card_bg, foreground=c.text_main)

    def _configure_view_styles(self, c: ThemeColors) -> None:
        """Configure complex components such as Notebook, Treeview, and Progressbar."""
        self.style.configure(
            "TNotebook", background=c.bg, tabmargins=[2, 4, 2, 0], bordercolor=c.border
        )
        self.style.configure(
            "TNotebook.Tab",
            background=c.card_bg,
            foreground=c.text_muted,
            padding=(12, 6),
            font=self.fonts.ui,
        )
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", c.bg)],
            foreground=[("selected", c.accent_primary if self.is_dark else c.text_main)],
        )
        self.style.configure(
            "Treeview",
            background=c.card_bg,
            foreground=c.text_main,
            fieldbackground=c.card_bg,
            bordercolor=c.border,
            rowheight=24,
        )
        self.style.map(
            "Treeview",
            background=[("selected", c.tree_selected)],
            foreground=[("selected", c.text_main)],
        )
        self.style.configure(
            "Treeview.Heading",
            background=c.bg,
            foreground=c.text_muted,
            font=self.fonts.ui_bold,
            padding=(4, 4),
        )
        self.style.configure(
            "Horizontal.TProgressbar",
            background=c.accent_primary,
            troughcolor=c.card_bg,
            bordercolor=c.border,
        )
