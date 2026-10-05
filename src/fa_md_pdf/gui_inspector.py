"""Zone B: 5-tab parameters inspector panel for fa-md-pdf GUI."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk
from typing import Callable

from .converter import ConvertOptions
from .defaults import default_browsers_path, default_fonts_path, default_mermaid_path
from .gui_theme import ThemeColors

DEFAULT_FONT_FAMILY = '"Vazirmatn", "Noto Naskh Arabic", "Segoe UI", Tahoma, Arial, sans-serif'
PAGE_FORMATS = ["A4", "Letter", "Legal", "A3"]
MERMAID_THEMES = ["default", "base", "dark", "forest", "neutral", "null"]


def _safe_float(val: str, default: float) -> float:
    try:
        return float(val.strip())
    except (ValueError, AttributeError):
        return default


def _safe_int(val: str | int, default: int) -> int:
    try:
        return int(str(val).strip())
    except (ValueError, AttributeError):
        return default


def _safe_path(val: str) -> Path | None:
    text = val.strip()
    return Path(text).resolve() if text else None


class ParametersInspectorPanel(ttk.Frame):
    """5-Tab configuration inspector and conversion controller."""

    def __init__(
        self,
        parent: tk.Widget,
        project_root: Path,
        on_convert: Callable[[], None],
        on_cancel: Callable[[], None],
        **kwargs,
    ) -> None:
        super().__init__(parent, **kwargs)
        self.project_root = project_root
        self.on_convert = on_convert
        self.on_cancel = on_cancel
        self._init_variables()
        self._build_top_controls()
        self._build_tabs()
        self._build_bottom_actions()

    def _init_variables(self) -> None:
        """Initialize all 30 configuration reactive variables."""
        self.format_var = tk.StringVar(value="pdf")
        self.output_var = tk.StringVar()
        self.page_format_var = tk.StringVar(value="A4")
        self.margin_var = tk.StringVar(value="20mm")
        self.landscape_var = tk.BooleanVar(value=False)
        self.pdf_page_numbers_var = tk.BooleanVar(value=True)
        self.strip_emojis_var = tk.BooleanVar(value=False)
        self._init_docx_variables()
        self._init_mermaid_variables()
        self._init_font_variables()
        self._init_advanced_variables()

    def _init_docx_variables(self) -> None:
        self.docx_image_scale_var = tk.IntVar(value=2)
        self.docx_image_min_width_var = tk.StringVar(value="2.0")
        self.docx_image_max_width_var = tk.StringVar(value="6.5")
        self.docx_font_size_var = tk.IntVar(value=11)
        self.docx_highlight_code_var = tk.BooleanVar(value=True)
        self.docx_page_numbers_var = tk.BooleanVar(value=True)

    def _init_mermaid_variables(self) -> None:
        self.mermaid_theme_var = tk.StringVar(value="default")
        self.mermaid_timeout_var = tk.StringVar(value="30")
        self.mermaid_js_var = tk.StringVar()
        self.mermaid_url_var = tk.StringVar()
        self.ignore_mermaid_errors_var = tk.BooleanVar(value=True)

    def _init_font_variables(self) -> None:
        self.font_family_var = tk.StringVar(value=DEFAULT_FONT_FAMILY)
        self.font_file_var = tk.StringVar()
        self.font_dir_var = tk.StringVar()
        self.custom_css_var = tk.StringVar()

    def _init_advanced_variables(self) -> None:
        self.keep_html_var = tk.BooleanVar(value=False)
        self.fail_fast_var = tk.BooleanVar(value=False)
        self.browsers_path_var = tk.StringVar()
        self.wrap_rtl_suffix_var = tk.StringVar(value=".rtl.md")
        self.watch_var = tk.BooleanVar(value=False)
        self.recursive_var = tk.BooleanVar(value=True)
        self.extensions_var = tk.StringVar(value=".md, .markdown")

    def _build_top_controls(self) -> None:
        """Build format selector and output path picker."""
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=4, pady=4)
        fmt_frame = ttk.Frame(top)
        fmt_frame.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(fmt_frame, text="فرمت خروجی:", style="Title.TLabel").pack(side=tk.LEFT, padx=(0, 6))
        for val, lbl in [("pdf", "PDF"), ("docx", "DOCX (Word)"), ("wrap-rtl", "RTL Markdown")]:
            ttk.Radiobutton(
                fmt_frame, text=lbl, value=val, variable=self.format_var, command=self._on_format_changed
            ).pack(side=tk.LEFT, padx=4)

        out_frame = ttk.Frame(top)
        out_frame.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(out_frame, text="پوشه خروجی:").pack(side=tk.LEFT, padx=(0, 4))
        ttk.Entry(out_frame, textvariable=self.output_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Button(out_frame, text="انتخاب...", command=self._pick_output_dir).pack(side=tk.LEFT, padx=2)

    def _pick_output_dir(self) -> None:
        path = filedialog.askdirectory(title="انتخاب پوشه ذخیره خروجی")
        if path:
            self.output_var.set(str(Path(path).resolve()))

    def _build_tabs(self) -> None:
        """Create 5-tab inspector notebook."""
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self._build_tab_page()
        self._build_tab_docx()
        self._build_tab_mermaid()
        self._build_tab_fonts()
        self._build_tab_advanced()

    def _build_tab_page(self) -> None:
        tab = ttk.Frame(self.notebook, padding=6)
        self.notebook.add(tab, text="سند و صفحه")
        r1 = ttk.Frame(tab)
        r1.pack(fill=tk.X, pady=2)
        ttk.Label(r1, text="اندازه صفحه:").pack(side=tk.LEFT)
        ttk.Combobox(r1, values=PAGE_FORMATS, textvariable=self.page_format_var, width=10).pack(side=tk.LEFT, padx=4)
        ttk.Label(r1, text="حاشیه:").pack(side=tk.LEFT, padx=(8, 2))
        ttk.Entry(r1, textvariable=self.margin_var, width=8).pack(side=tk.LEFT)
        ttk.Checkbutton(tab, text="افقی (Landscape)", variable=self.landscape_var).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(tab, text="شماره صفحه PDF", variable=self.pdf_page_numbers_var).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(tab, text="حذف ایموجی‌ها از خروجی", variable=self.strip_emojis_var).pack(anchor=tk.W, pady=2)

    def _build_tab_docx(self) -> None:
        tab = ttk.Frame(self.notebook, padding=6)
        self.notebook.add(tab, text="ورد (DOCX)")
        r1 = ttk.Frame(tab)
        r1.pack(fill=tk.X, pady=2)
        ttk.Label(r1, text="مقیاس تصاویر:").pack(side=tk.LEFT)
        ttk.Combobox(r1, values=[1, 2, 3, 4], textvariable=self.docx_image_scale_var, width=5).pack(side=tk.LEFT, padx=4)
        ttk.Label(r1, text="سایز فونت:").pack(side=tk.LEFT, padx=(8, 2))
        ttk.Spinbox(r1, from_=8, to=24, textvariable=self.docx_font_size_var, width=5).pack(side=tk.LEFT)
        r2 = ttk.Frame(tab)
        r2.pack(fill=tk.X, pady=2)
        ttk.Label(r2, text="حداقل عرض تصویر (اینچ):").pack(side=tk.LEFT)
        ttk.Entry(r2, textvariable=self.docx_image_min_width_var, width=6).pack(side=tk.LEFT, padx=4)
        ttk.Label(r2, text="حداکثر عرض:").pack(side=tk.LEFT, padx=(8, 2))
        ttk.Entry(r2, textvariable=self.docx_image_max_width_var, width=6).pack(side=tk.LEFT)
        ttk.Checkbutton(tab, text="رنگ‌آمیزی کدها (Syntax Highlight)", variable=self.docx_highlight_code_var).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(tab, text="شماره صفحه داینامیک Word", variable=self.docx_page_numbers_var).pack(anchor=tk.W, pady=2)

    def _build_tab_mermaid(self) -> None:
        tab = ttk.Frame(self.notebook, padding=6)
        self.notebook.add(tab, text="Mermaid")
        r1 = ttk.Frame(tab)
        r1.pack(fill=tk.X, pady=2)
        ttk.Label(r1, text="تم نمودار:").pack(side=tk.LEFT)
        ttk.Combobox(r1, values=MERMAID_THEMES, textvariable=self.mermaid_theme_var, width=10).pack(side=tk.LEFT, padx=4)
        ttk.Label(r1, text="تایم‌اوت (ثانیه):").pack(side=tk.LEFT, padx=(8, 2))
        ttk.Entry(r1, textvariable=self.mermaid_timeout_var, width=6).pack(side=tk.LEFT)
        self._build_path_row(tab, "اسکریپت Mermaid.js:", self.mermaid_js_var, is_dir=False)
        r3 = ttk.Frame(tab)
        r3.pack(fill=tk.X, pady=2)
        ttk.Label(r3, text="CDN URL:").pack(side=tk.LEFT)
        ttk.Entry(r3, textvariable=self.mermaid_url_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        ttk.Checkbutton(tab, text="نادیده گرفتن خطاهای رندر Mermaid", variable=self.ignore_mermaid_errors_var).pack(anchor=tk.W, pady=2)

    def _build_tab_fonts(self) -> None:
        tab = ttk.Frame(self.notebook, padding=6)
        self.notebook.add(tab, text="فونت و CSS")
        r1 = ttk.Frame(tab)
        r1.pack(fill=tk.X, pady=2)
        ttk.Label(r1, text="خانواده فونت:").pack(side=tk.LEFT)
        ttk.Entry(r1, textvariable=self.font_family_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self._build_path_row(tab, "فایل فونت اختصاصی:", self.font_file_var, is_dir=False)
        self._build_path_row(tab, "پوشه فونت‌ها:", self.font_dir_var, is_dir=True)
        self._build_path_row(tab, "فایل CSS سفارشی:", self.custom_css_var, is_dir=False)

    def _build_tab_advanced(self) -> None:
        tab = ttk.Frame(self.notebook, padding=6)
        self.notebook.add(tab, text="پیشرفته")
        ttk.Checkbutton(tab, text="ذخیره فایل HTML موقت (keep_html)", variable=self.keep_html_var).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(tab, text="توقف با اولین خطا (fail_fast)", variable=self.fail_fast_var).pack(anchor=tk.W, pady=2)
        self._build_path_row(tab, "مسیر مرورگرها (browsers):", self.browsers_path_var, is_dir=True)
        r = ttk.Frame(tab)
        r.pack(fill=tk.X, pady=2)
        ttk.Label(r, text="پسوند wrap-rtl:").pack(side=tk.LEFT)
        ttk.Entry(r, textvariable=self.wrap_rtl_suffix_var, width=10).pack(side=tk.LEFT, padx=4)
        ttk.Label(r, text="پسوندهای مجاز:").pack(side=tk.LEFT, padx=(8, 2))
        ttk.Entry(r, textvariable=self.extensions_var, width=16).pack(side=tk.LEFT)

    def _build_path_row(self, parent: ttk.Frame, label_text: str, var: tk.StringVar, is_dir: bool) -> None:
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=label_text).pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        cmd = (lambda: self._pick_path_dir(var)) if is_dir else (lambda: self._pick_path_file(var))
        ttk.Button(row, text="...", width=3, command=cmd).pack(side=tk.LEFT)

    def _pick_path_dir(self, var: tk.StringVar) -> None:
        path = filedialog.askdirectory()
        if path:
            var.set(str(Path(path).resolve()))

    def _pick_path_file(self, var: tk.StringVar) -> None:
        path = filedialog.askopenfilename()
        if path:
            var.set(str(Path(path).resolve()))

    def _build_bottom_actions(self) -> None:
        """Build execution action buttons."""
        bar = ttk.Frame(self)
        bar.pack(fill=tk.X, padx=4, pady=6)
        self.convert_btn = ttk.Button(bar, text="▶ تبدیل اسناد", style="Primary.TButton", command=self.on_convert)
        self.convert_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.cancel_btn = ttk.Button(bar, text="⏹ انصراف", command=self.on_cancel, state="disabled")
        self.cancel_btn.pack(side=tk.LEFT, padx=2)
        self.watch_btn = ttk.Checkbutton(bar, text="👁️ پایش (Watch)", variable=self.watch_var)
        self.watch_btn.pack(side=tk.LEFT, padx=4)

    def _on_format_changed(self) -> None:
        """Handle format switch and update state."""
        # Selection triggers reactivity
        pass

    def set_format(self, format_name: str) -> None:
        self.format_var.set(format_name)
        self._on_format_changed()

    def set_running_state(self, is_running: bool, is_watching: bool = False) -> None:
        """Update button states during conversion."""
        self.convert_btn.configure(state="disabled" if is_running else "normal")
        self.cancel_btn.configure(state="normal" if is_running else "disabled")
        if is_watching:
            self.cancel_btn.configure(text="⏹ توقف پایش", state="normal")

    def _resolve_mermaid_source(self) -> str:
        """Resolve mermaid script file, CDN URL or fallback."""
        url = self.mermaid_url_var.get().strip()
        if url:
            return url
        js_path = self.mermaid_js_var.get().strip()
        if js_path and Path(js_path).is_file():
            return js_path
        default_js = default_mermaid_path(self.project_root)
        if default_js.is_file():
            return str(default_js)
        return "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"

    def build_convert_options(self) -> ConvertOptions:
        """Build ConvertOptions dataclass instance with all 30 parameters."""
        fmt = self.format_var.get()
        timeout_ms = _safe_int(self.mermaid_timeout_var.get(), 30) * 1000
        min_w = _safe_float(self.docx_image_min_width_var.get(), 2.0)
        max_w = _safe_float(self.docx_image_max_width_var.get(), 6.5)

        return ConvertOptions(
            font_family=self.font_family_var.get() or DEFAULT_FONT_FAMILY,
            font_file=_safe_path(self.font_file_var.get()),
            font_dir=_safe_path(self.font_dir_var.get()),
            custom_css=_safe_path(self.custom_css_var.get()),
            mermaid_source=self._resolve_mermaid_source(),
            mermaid_theme=self.mermaid_theme_var.get(),
            mermaid_timeout_ms=timeout_ms,
            page_format=self.page_format_var.get(),
            margin=self.margin_var.get().strip() or "15mm",
            landscape=self.landscape_var.get(),
            keep_html=self.keep_html_var.get(),
            ignore_mermaid_errors=self.ignore_mermaid_errors_var.get(),
            verbose=False,
            output_format=fmt,
            docx_font_size_pt=self.docx_font_size_var.get(),
            docx_image_scale=self.docx_image_scale_var.get(),
            docx_image_min_width=min_w,
            docx_image_max_width=max_w,
            include_page_numbers=self.docx_page_numbers_var.get() if fmt == "docx" else self.pdf_page_numbers_var.get(),
            highlight_code=self.docx_highlight_code_var.get(),
            strip_emojis=self.strip_emojis_var.get(),
        )

    def apply_colors(self, colors: ThemeColors) -> None:
        """Apply active theme palette to inspector."""
        # TTK styles apply globally, but specific custom elements can update here
        pass
