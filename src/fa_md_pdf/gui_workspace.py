"""Zone C: Dual preview and streaming terminal workspace panel with status bar."""

from __future__ import annotations

import datetime
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from .gui_theme import ThemeColors


class LivePreviewConsolePanel(ttk.Frame):
    """Dual tab workspace hosting Markdown live preview and streaming terminal."""

    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self._build_preview_tab()
        self._build_console_tab()

    def _build_preview_tab(self) -> None:
        """Create document preview tab."""
        tab = ttk.Frame(self.notebook, padding=4)
        self.notebook.add(tab, text="پیش‌نمایش سند (Preview)")

        meta_bar = ttk.Frame(tab)
        meta_bar.pack(fill=tk.X, pady=(0, 4))
        self.preview_path_lbl = ttk.Label(meta_bar, text="سندی انتخاب نشده است", style="Title.TLabel")
        self.preview_path_lbl.pack(side=tk.LEFT)
        self.preview_info_lbl = ttk.Label(meta_bar, text="", style="Muted.TLabel")
        self.preview_info_lbl.pack(side=tk.RIGHT)

        txt_frame = ttk.Frame(tab)
        txt_frame.pack(fill=tk.BOTH, expand=True)
        self.preview_text = tk.Text(txt_frame, wrap=tk.WORD, state="disabled", padx=8, pady=8)
        scroll = ttk.Scrollbar(txt_frame, orient=tk.VERTICAL, command=self.preview_text.yview)
        self.preview_text.configure(yscrollcommand=scroll.set)
        self.preview_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _build_console_tab(self) -> None:
        """Create streaming console terminal tab."""
        tab = ttk.Frame(self.notebook, padding=4)
        self.notebook.add(tab, text="ترمینال و لاگ‌ها (Console)")

        tool_bar = ttk.Frame(tab)
        tool_bar.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(tool_bar, text="وقایع زنده تبدیل", style="Title.TLabel").pack(side=tk.LEFT)
        ttk.Button(tool_bar, text="پاکسازی", command=self.clear_logs).pack(side=tk.RIGHT, padx=2)

        txt_frame = ttk.Frame(tab)
        txt_frame.pack(fill=tk.BOTH, expand=True)
        self.console_text = tk.Text(
            txt_frame,
            wrap=tk.WORD,
            state="disabled",
            padx=8,
            pady=8,
            bg="#060913",
            fg="#cbd5e1",
            insertbackground="#ffffff",
        )
        self._setup_console_tags()
        scroll = ttk.Scrollbar(txt_frame, orient=tk.VERTICAL, command=self.console_text.yview)
        self.console_text.configure(yscrollcommand=scroll.set)
        self.console_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _setup_console_tags(self) -> None:
        """Configure semantic colors for terminal log levels."""
        self.console_text.tag_configure("time", foreground="#64748b")
        self.console_text.tag_configure("info", foreground="#94a3b8")
        self.console_text.tag_configure("success", foreground="#10b981")
        self.console_text.tag_configure("error", foreground="#ef4444")
        self.console_text.tag_configure("warn", foreground="#f59e0b")
        self.console_text.tag_configure("summary", foreground="#38bdf8")

    def set_preview_file(self, file_path: Path | None) -> None:
        """Display content and metadata of a file in previewer."""
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", tk.END)
        if not file_path or not file_path.is_file():
            self.preview_path_lbl.configure(text="فایلی انتخاب نشده است")
            self.preview_info_lbl.configure(text="")
            self.preview_text.insert(tk.END, "فایلی انتخاب نشده است.")
            self.preview_text.configure(state="disabled")
            return

        try:
            content = file_path.read_text(encoding="utf-8-sig")
            lines_count = len(content.splitlines())
            self.preview_path_lbl.configure(text=file_path.name)
            self.preview_info_lbl.configure(text=f"{lines_count} سطر | {file_path.stat().st_size} بایت")
            self.preview_text.insert(tk.END, content)
        except Exception as exc:
            self.preview_text.insert(tk.END, f"خطا در خواندن فایل: {exc}")
        self.preview_text.configure(state="disabled")

    def get_preview_text(self) -> str:
        """Return raw content currently rendered in preview."""
        return self.preview_text.get("1.0", tk.END)

    def append_log(self, message: str, level: str = "info") -> None:
        """Append timestamped colored log entry to terminal."""
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        self.console_text.configure(state="normal")
        self.console_text.insert(tk.END, f"[{now_str}] ", "time")
        self.console_text.insert(tk.END, f"{message}\n", level)
        self.console_text.see(tk.END)
        self.console_text.configure(state="disabled")

    def get_log_text(self) -> str:
        """Return all log entries from console."""
        return self.console_text.get("1.0", tk.END)

    def clear_logs(self) -> None:
        """Clear all content from console."""
        self.console_text.configure(state="normal")
        self.console_text.delete("1.0", tk.END)
        self.console_text.configure(state="disabled")

    def apply_colors(self, colors: ThemeColors) -> None:
        """Update terminal and preview backgrounds with active theme."""
        self.console_text.configure(
            bg=colors.terminal_bg,
            fg=colors.terminal_fg,
            insertbackground=colors.text_main,
        )
        self.preview_text.configure(
            bg=colors.input_bg,
            fg=colors.text_main,
            insertbackground=colors.text_main,
        )


class StatusBarPanel(ttk.Frame):
    """Bottom status bar with progress indicator and system badges."""

    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        self.progress_var = tk.DoubleVar(value=0.0)
        self.status_var = tk.StringVar(value="آماده")
        self._build_bar()

    def _build_bar(self) -> None:
        """Construct status bar layout."""
        self.status_lbl = ttk.Label(self, textvariable=self.status_var, style="Muted.TLabel")
        self.status_lbl.pack(side=tk.LEFT, padx=6)

        self.badge_lbl = ttk.Label(self, text="Playwright Ready", style="Muted.TLabel")
        self.badge_lbl.pack(side=tk.RIGHT, padx=6)

        self.progress = ttk.Progressbar(
            self,
            variable=self.progress_var,
            maximum=100.0,
            style="Horizontal.TProgressbar",
            length=160,
        )
        self.progress.pack(side=tk.RIGHT, padx=6)

    def set_status(self, text: str, badge_type: str = "idle") -> None:
        """Update status message and badge appearance."""
        self.status_var.set(text)
        badge_text = "در حال کار..." if badge_type == "running" else "Playwright Ready"
        self.badge_lbl.configure(text=badge_text)

    def set_progress(self, completed: int, total: int) -> None:
        """Update progress bar percentage."""
        if total <= 0:
            self.progress_var.set(0.0)
        else:
            pct = min(100.0, (completed / total) * 100.0)
            self.progress_var.set(pct)

    def reset(self) -> None:
        """Reset progress and return to idle state."""
        self.progress_var.set(0.0)
        self.status_var.set("آماده")
        self.badge_lbl.configure(text="Playwright Ready")

    def apply_colors(self, colors: ThemeColors) -> None:
        """Update label colors based on theme."""
        self.status_lbl.configure(foreground=colors.text_muted)
        self.badge_lbl.configure(foreground=colors.text_muted)
