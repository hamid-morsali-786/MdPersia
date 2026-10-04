"""Graphical user interface for fa-md-pdf using tkinter."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, font, messagebox, ttk
from typing import TYPE_CHECKING

from .converter import (
    ConversionError,
    ConvertJob,
    ConvertOptions,
    build_jobs,
    convert_jobs,
    normalize_extensions,
)
from .defaults import (
    default_browsers_path,
    default_fonts_path,
    default_mermaid_path,
    find_project_root,
    set_playwright_browsers_path,
)

if TYPE_CHECKING:
    pass


DEFAULT_FONT_FAMILY = '"Vazirmatn", "Noto Naskh Arabic", "Segoe UI", Tahoma, Arial, sans-serif'

PAGE_FORMATS = ["A4", "Letter", "Legal"]
MERMAID_THEMES = ["default", "base", "dark", "forest", "neutral", "null"]


@dataclass
class ProgressEvent:
    """Event posted from ConversionThread to the GUI queue."""

    event_type: str  # "start" | "success" | "error" | "done" | "cancelled"
    job: ConvertJob | None = None
    total: int = 0
    completed: int = 0
    error: str | None = None


class ConversionThread(threading.Thread):
    """Background thread that runs PDF conversion and posts progress events."""

    def __init__(
        self,
        jobs: list[ConvertJob],
        options: ConvertOptions,
        progress_queue: queue.Queue[ProgressEvent],
        cancel_event: threading.Event,
    ):
        super().__init__(daemon=True)
        self.jobs = jobs
        self.options = options
        self.progress_queue = progress_queue
        self.cancel_event = cancel_event
        self._completed = 0

    def _on_progress(self, job: ConvertJob, ok: bool, error: str | None) -> None:
        self._completed += 1
        event_type = "success" if ok else "error"
        self.progress_queue.put(
            ProgressEvent(
                event_type=event_type,
                job=job,
                total=len(self.jobs),
                completed=self._completed,
                error=error,
            )
        )

    def run(self) -> None:
        try:
            self.progress_queue.put(
                ProgressEvent(event_type="start", total=len(self.jobs))
            )
            convert_jobs(
                self.jobs,
                options=self.options,
                fail_fast=self.options.ignore_mermaid_errors is False
                and getattr(self.options, "_fail_fast", False),
                on_progress=self._on_progress,
                cancel_event=self.cancel_event,
            )
        except Exception as exc:  # noqa: BLE001
            self.progress_queue.put(
                ProgressEvent(event_type="error", error=str(exc))
            )

        if self.cancel_event.is_set():
            self.progress_queue.put(
                ProgressEvent(
                    event_type="cancelled",
                    total=len(self.jobs),
                    completed=self._completed,
                )
            )
        else:
            self.progress_queue.put(
                ProgressEvent(
                    event_type="done",
                    total=len(self.jobs),
                    completed=self._completed,
                )
            )


class MainWindow:
    """Main GUI application window with RTL Persian interface."""

    def __init__(self, root: tk.Tk, project_root: Path):
        self.root = root
        self.project_root = project_root
        self.progress_queue: queue.Queue[ProgressEvent] = queue.Queue()
        self.cancel_event = threading.Event()
        self.conversion_thread: ConversionThread | None = None

        self._setup_window()
        self._setup_fonts()
        self._build_ui()
        self._auto_detect_assets()

    def _setup_window(self) -> None:
        self.root.title("fa-md-pdf - تبدیل مارک‌داون به PDF و DOCX")
        self.root.geometry("900x780")
        self.root.minsize(800, 650)

    def _setup_fonts(self) -> None:
        available = font.families()
        if "Vazirmatn" in available:
            self.ui_font = font.Font(family="Vazirmatn", size=10)
        elif "Tahoma" in available:
            self.ui_font = font.Font(family="Tahoma", size=10)
        else:
            self.ui_font = font.Font(family="Segoe UI", size=10)

        self.ui_font_bold = self.ui_font.copy()
        self.ui_font_bold.configure(weight="bold")

    def _build_ui(self) -> None:
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        self._build_input_panel(main_frame)
        self._build_output_panel(main_frame)
        self._build_options_panel(main_frame)
        self._build_buttons(main_frame)
        self._build_progress_panel(main_frame)

    # ─── Input Panel ───────────────────────────────────────────────

    def _build_input_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="  ورودی  ", padding=8)
        frame.pack(fill=tk.X, pady=(0, 6))

        row = ttk.Frame(frame)
        row.pack(fill=tk.X)

        self.input_var = tk.StringVar()
        entry = ttk.Entry(row, textvariable=self.input_var, font=self.ui_font, justify="right")
        entry.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(4, 0))

        btn_file = ttk.Button(row, text="انتخاب فایل", command=self._pick_input_file)
        btn_file.pack(side=tk.RIGHT, padx=2)

        btn_dir = ttk.Button(row, text="انتخاب فولدر", command=self._pick_input_dir)
        btn_dir.pack(side=tk.RIGHT, padx=2)

        row2 = ttk.Frame(frame)
        row2.pack(fill=tk.X, pady=(4, 0))

        self.recursive_var = tk.BooleanVar(value=True)
        chk = ttk.Checkbutton(
            row2, text="جستجوی بازگشتی در زیرپوشه‌ها", variable=self.recursive_var
        )
        chk.pack(side=tk.RIGHT)

        self.input_error_var = tk.StringVar()
        self.input_error_label = ttk.Label(
            row2, textvariable=self.input_error_var, foreground="red", font=self.ui_font
        )
        self.input_error_label.pack(side=tk.RIGHT, padx=8)

    def _pick_input_file(self) -> None:
        path = filedialog.askopenfilename(
            title="انتخاب فایل Markdown",
            filetypes=[("Markdown", "*.md *.markdown"), ("همه فایل‌ها", "*.*")],
        )
        if path:
            self.input_var.set(str(Path(path).resolve()))
            self.input_error_var.set("")

    def _pick_input_dir(self) -> None:
        path = filedialog.askdirectory(title="انتخاب فولدر حاوی فایل‌های Markdown")
        if path:
            self.input_var.set(str(Path(path).resolve()))
            self.input_error_var.set("")

    # ─── Output Panel ──────────────────────────────────────────────

    def _build_output_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="  خروجی  ", padding=8)
        frame.pack(fill=tk.X, pady=(0, 6))

        # Format selector row
        row_format = ttk.Frame(frame)
        row_format.pack(fill=tk.X, pady=(0, 4))

        ttk.Label(row_format, text="فرمت خروجی:", font=self.ui_font_bold).pack(side=tk.RIGHT)

        self.format_var = tk.StringVar(value="pdf")
        ttk.Radiobutton(
            row_format, text="PDF", variable=self.format_var, value="pdf",
            command=self._on_format_changed,
        ).pack(side=tk.RIGHT, padx=8)
        ttk.Radiobutton(
            row_format, text="DOCX (Word)", variable=self.format_var, value="docx",
            command=self._on_format_changed,
        ).pack(side=tk.RIGHT, padx=8)
        ttk.Radiobutton(
            row_format, text="Markdown با RTL",
            variable=self.format_var, value="wrap-rtl",
            command=self._on_format_changed,
        ).pack(side=tk.RIGHT, padx=8)

        # Output path row
        row = ttk.Frame(frame)
        row.pack(fill=tk.X)

        self.output_var = tk.StringVar()
        entry = ttk.Entry(row, textvariable=self.output_var, font=self.ui_font, justify="right")
        entry.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(4, 0))

        btn = ttk.Button(row, text="انتخاب...", command=self._pick_output_dir)
        btn.pack(side=tk.RIGHT, padx=2)

    def _on_format_changed(self) -> None:
        # Enable/disable DOCX-only settings visually if needed
        is_docx = self.format_var.get() == "docx"
        # The DOCX tab is always visible, but we could enable/disable controls.
        # For now, just update state of any related widgets.
        if hasattr(self, "_docx_tab_widgets"):
            state = "normal" if is_docx else "disabled"
            for widget in self._docx_tab_widgets:
                try:
                    widget.configure(state=state)
                except tk.TclError:
                    pass

    def _pick_output_dir(self) -> None:
        path = filedialog.askdirectory(title="انتخاب فولدر خروجی")
        if path:
            self.output_var.set(str(Path(path).resolve()))


    # ─── Options Panel (Notebook with tabs) ────────────────────────

    def _build_options_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="  تنظیمات  ", padding=8)
        frame.pack(fill=tk.X, pady=(0, 6))

        notebook = ttk.Notebook(frame)
        notebook.pack(fill=tk.X)

        self._build_page_tab(notebook)
        self._build_font_tab(notebook)
        self._build_mermaid_tab(notebook)
        self._build_docx_tab(notebook)
        self._build_advanced_tab(notebook)

    def _build_page_tab(self, notebook: ttk.Notebook) -> None:
        tab = ttk.Frame(notebook, padding=8)
        notebook.add(tab, text="  صفحه  ")

        # Page format
        row1 = ttk.Frame(tab)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text="فرمت صفحه:", font=self.ui_font).pack(side=tk.RIGHT)
        self.page_format_var = tk.StringVar(value="A4")
        combo = ttk.Combobox(
            row1, textvariable=self.page_format_var, values=PAGE_FORMATS,
            state="readonly", width=10
        )
        combo.pack(side=tk.RIGHT, padx=8)

        # Margin
        row2 = ttk.Frame(tab)
        row2.pack(fill=tk.X, pady=2)
        ttk.Label(row2, text="حاشیه:", font=self.ui_font).pack(side=tk.RIGHT)
        self.margin_var = tk.StringVar(value="15mm")
        ttk.Entry(row2, textvariable=self.margin_var, width=10, justify="right").pack(
            side=tk.RIGHT, padx=8
        )

        # Landscape
        row3 = ttk.Frame(tab)
        row3.pack(fill=tk.X, pady=2)
        self.landscape_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row3, text="خروجی افقی (Landscape)", variable=self.landscape_var).pack(
            side=tk.RIGHT
        )

    def _build_font_tab(self, notebook: ttk.Notebook) -> None:
        tab = ttk.Frame(notebook, padding=8)
        notebook.add(tab, text="  فونت  ")

        # Font family (read-only display)
        row1 = ttk.Frame(tab)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text="خانواده فونت:", font=self.ui_font).pack(side=tk.RIGHT)
        self.font_family_var = tk.StringVar(value=DEFAULT_FONT_FAMILY)
        ttk.Entry(
            row1, textvariable=self.font_family_var, state="readonly", width=50, justify="right"
        ).pack(side=tk.RIGHT, padx=8)

        # Font file
        row2 = ttk.Frame(tab)
        row2.pack(fill=tk.X, pady=2)
        ttk.Label(row2, text="فایل فونت:", font=self.ui_font).pack(side=tk.RIGHT)
        self.font_file_var = tk.StringVar()
        self.font_file_entry = ttk.Entry(
            row2, textvariable=self.font_file_var, width=40, justify="right"
        )
        self.font_file_entry.pack(side=tk.RIGHT, padx=4)
        ttk.Button(row2, text="انتخاب...", command=self._pick_font_file).pack(
            side=tk.RIGHT, padx=2
        )

        # Font directory
        row3 = ttk.Frame(tab)
        row3.pack(fill=tk.X, pady=2)
        ttk.Label(row3, text="فولدر فونت‌ها:", font=self.ui_font).pack(side=tk.RIGHT)
        self.font_dir_var = tk.StringVar()
        self.font_dir_entry = ttk.Entry(
            row3, textvariable=self.font_dir_var, width=40, justify="right"
        )
        self.font_dir_entry.pack(side=tk.RIGHT, padx=4)
        ttk.Button(row3, text="انتخاب...", command=self._pick_font_dir).pack(
            side=tk.RIGHT, padx=2
        )

        # Mutual exclusivity
        self.font_file_var.trace_add("write", self._on_font_file_changed)

    def _pick_font_file(self) -> None:
        path = filedialog.askopenfilename(
            title="انتخاب فایل فونت",
            filetypes=[("TrueType Font", "*.ttf"), ("همه فایل‌ها", "*.*")],
        )
        if path:
            self.font_file_var.set(str(Path(path).resolve()))

    def _pick_font_dir(self) -> None:
        path = filedialog.askdirectory(title="انتخاب فولدر فونت‌ها")
        if path:
            self.font_dir_var.set(str(Path(path).resolve()))

    def _on_font_file_changed(self, *_args) -> None:
        if self.font_file_var.get().strip():
            self.font_dir_entry.configure(state="disabled")
        else:
            self.font_dir_entry.configure(state="normal")

    def _build_mermaid_tab(self, notebook: ttk.Notebook) -> None:
        tab = ttk.Frame(notebook, padding=8)
        notebook.add(tab, text="  Mermaid  ")

        # Mermaid JS file
        row1 = ttk.Frame(tab)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text="فایل Mermaid JS:", font=self.ui_font).pack(side=tk.RIGHT)
        self.mermaid_js_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.mermaid_js_var, width=40, justify="right").pack(
            side=tk.RIGHT, padx=4
        )
        ttk.Button(row1, text="انتخاب...", command=self._pick_mermaid_js).pack(
            side=tk.RIGHT, padx=2
        )

        # Theme
        row2 = ttk.Frame(tab)
        row2.pack(fill=tk.X, pady=2)
        ttk.Label(row2, text="تم:", font=self.ui_font).pack(side=tk.RIGHT)
        self.mermaid_theme_var = tk.StringVar(value="default")
        ttk.Combobox(
            row2, textvariable=self.mermaid_theme_var, values=MERMAID_THEMES,
            state="readonly", width=12
        ).pack(side=tk.RIGHT, padx=8)

        # Timeout
        row3 = ttk.Frame(tab)
        row3.pack(fill=tk.X, pady=2)
        ttk.Label(row3, text="Timeout (ms):", font=self.ui_font).pack(side=tk.RIGHT)
        self.mermaid_timeout_var = tk.StringVar(value="30000")
        ttk.Entry(row3, textvariable=self.mermaid_timeout_var, width=10, justify="right").pack(
            side=tk.RIGHT, padx=8
        )

        # Ignore errors
        row4 = ttk.Frame(tab)
        row4.pack(fill=tk.X, pady=2)
        self.ignore_mermaid_errors_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            row4, text="نادیده گرفتن خطاهای Mermaid", variable=self.ignore_mermaid_errors_var
        ).pack(side=tk.RIGHT)

        # Optional URL
        row5 = ttk.Frame(tab)
        row5.pack(fill=tk.X, pady=2)
        ttk.Label(row5, text="URL (اختیاری):", font=self.ui_font).pack(side=tk.RIGHT)
        self.mermaid_url_var = tk.StringVar()
        ttk.Entry(row5, textvariable=self.mermaid_url_var, width=50, justify="left").pack(
            side=tk.RIGHT, padx=4
        )

    def _pick_mermaid_js(self) -> None:
        path = filedialog.askopenfilename(
            title="انتخاب فایل mermaid.min.js",
            filetypes=[("JavaScript", "*.js"), ("همه فایل‌ها", "*.*")],
        )
        if path:
            self.mermaid_js_var.set(str(Path(path).resolve()))

    def _build_docx_tab(self, notebook: ttk.Notebook) -> None:
        tab = ttk.Frame(notebook, padding=8)
        notebook.add(tab, text="  DOCX  ")

        # Info label
        info = ttk.Label(
            tab,
            text="این تنظیمات فقط هنگام انتخاب فرمت DOCX اعمال می‌شوند.",
            font=self.ui_font, foreground="#6b7280",
        )
        info.pack(anchor=tk.E, pady=(0, 6))

        # Image scale (quality)
        row1 = ttk.Frame(tab)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text="کیفیت تصویر نمودار:", font=self.ui_font).pack(side=tk.RIGHT)
        self.docx_image_scale_var = tk.StringVar(value="3")
        scale_combo = ttk.Combobox(
            row1, textvariable=self.docx_image_scale_var,
            values=["1", "2", "3", "4"],
            state="readonly", width=6,
        )
        scale_combo.pack(side=tk.RIGHT, padx=8)
        ttk.Label(
            row1, text="(۱=کم، ۳=پیش‌فرض، ۴=بالا)",
            font=self.ui_font, foreground="#6b7280",
        ).pack(side=tk.RIGHT, padx=4)

        # Min image width
        row2 = ttk.Frame(tab)
        row2.pack(fill=tk.X, pady=2)
        ttk.Label(row2, text="حداقل عرض تصویر (اینچ):", font=self.ui_font).pack(side=tk.RIGHT)
        self.docx_image_min_width_var = tk.StringVar(value="4.0")
        ttk.Entry(
            row2, textvariable=self.docx_image_min_width_var, width=10, justify="right"
        ).pack(side=tk.RIGHT, padx=8)

        # Max image width
        row3 = ttk.Frame(tab)
        row3.pack(fill=tk.X, pady=2)
        ttk.Label(row3, text="حداکثر عرض تصویر (اینچ):", font=self.ui_font).pack(side=tk.RIGHT)
        self.docx_image_max_width_var = tk.StringVar(value="6.5")
        ttk.Entry(
            row3, textvariable=self.docx_image_max_width_var, width=10, justify="right"
        ).pack(side=tk.RIGHT, padx=8)

        # Body font size
        row4 = ttk.Frame(tab)
        row4.pack(fill=tk.X, pady=2)
        ttk.Label(row4, text="اندازه فونت متن (پوینت):", font=self.ui_font).pack(side=tk.RIGHT)
        self.docx_font_size_var = tk.StringVar(value="12")
        ttk.Entry(
            row4, textvariable=self.docx_font_size_var, width=10, justify="right"
        ).pack(side=tk.RIGHT, padx=8)

    def _build_advanced_tab(self, notebook: ttk.Notebook) -> None:
        tab = ttk.Frame(notebook, padding=8)
        notebook.add(tab, text="  پیشرفته  ")

        # Extensions
        row1 = ttk.Frame(tab)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text="پسوندهای مجاز:", font=self.ui_font).pack(side=tk.RIGHT)
        self.extensions_var = tk.StringVar(value=".md .markdown")
        ttk.Entry(row1, textvariable=self.extensions_var, width=20, justify="right").pack(
            side=tk.RIGHT, padx=8
        )

        # Keep HTML
        row2 = ttk.Frame(tab)
        row2.pack(fill=tk.X, pady=2)
        self.keep_html_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row2, text="نگه‌داشتن HTML میانی", variable=self.keep_html_var).pack(
            side=tk.RIGHT
        )

        # Fail fast
        row3 = ttk.Frame(tab)
        row3.pack(fill=tk.X, pady=2)
        self.fail_fast_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row3, text="توقف با اولین خطا", variable=self.fail_fast_var).pack(
            side=tk.RIGHT
        )

        # Browsers path
        row4 = ttk.Frame(tab)
        row4.pack(fill=tk.X, pady=2)
        ttk.Label(row4, text="مسیر مرورگرها:", font=self.ui_font).pack(side=tk.RIGHT)
        self.browsers_path_var = tk.StringVar()
        ttk.Entry(row4, textvariable=self.browsers_path_var, width=40, justify="right").pack(
            side=tk.RIGHT, padx=4
        )
        ttk.Button(row4, text="انتخاب...", command=self._pick_browsers_path).pack(
            side=tk.RIGHT, padx=2
        )

        # Custom CSS
        row5 = ttk.Frame(tab)
        row5.pack(fill=tk.X, pady=2)
        ttk.Label(row5, text="CSS سفارشی:", font=self.ui_font).pack(side=tk.RIGHT)
        self.css_var = tk.StringVar()
        ttk.Entry(row5, textvariable=self.css_var, width=40, justify="right").pack(
            side=tk.RIGHT, padx=4
        )
        ttk.Button(row5, text="انتخاب...", command=self._pick_css_file).pack(
            side=tk.RIGHT, padx=2
        )

    def _pick_browsers_path(self) -> None:
        path = filedialog.askdirectory(title="انتخاب فولدر مرورگرها (Playwright)")
        if path:
            self.browsers_path_var.set(str(Path(path).resolve()))

    def _pick_css_file(self) -> None:
        path = filedialog.askopenfilename(
            title="انتخاب فایل CSS",
            filetypes=[("CSS", "*.css"), ("همه فایل‌ها", "*.*")],
        )
        if path:
            self.css_var.set(str(Path(path).resolve()))


    # ─── Buttons ───────────────────────────────────────────────────

    def _build_buttons(self, parent: ttk.Frame) -> None:
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=6)

        self.convert_btn = ttk.Button(
            frame, text="🔄 تبدیل", command=self._start_conversion
        )
        self.convert_btn.pack(side=tk.RIGHT, padx=4)

        self.cancel_btn = ttk.Button(
            frame, text="⏹ انصراف", command=self._cancel_conversion, state="disabled"
        )
        self.cancel_btn.pack(side=tk.RIGHT, padx=4)

    # ─── Progress Panel ────────────────────────────────────────────

    def _build_progress_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="  نتایج  ", padding=8)
        frame.pack(fill=tk.BOTH, expand=True, pady=(0, 0))

        self.progress_text = tk.Text(
            frame, height=10, font=self.ui_font, state="disabled",
            wrap="word", spacing1=2, spacing3=2
        )
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.progress_text.yview)
        self.progress_text.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        self.progress_text.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Configure tags for colored output
        self.progress_text.tag_configure("success", foreground="#16a34a")
        self.progress_text.tag_configure("error", foreground="#dc2626")
        self.progress_text.tag_configure("info", foreground="#2563eb")
        self.progress_text.tag_configure("summary", foreground="#1f2937", font=self.ui_font_bold)

    def _log(self, message: str, tag: str = "") -> None:
        self.progress_text.configure(state="normal")
        if tag:
            self.progress_text.insert(tk.END, message + "\n", tag)
        else:
            self.progress_text.insert(tk.END, message + "\n")
        self.progress_text.see(tk.END)
        self.progress_text.configure(state="disabled")

    def _clear_log(self) -> None:
        self.progress_text.configure(state="normal")
        self.progress_text.delete("1.0", tk.END)
        self.progress_text.configure(state="disabled")

    # ─── Auto-detect Assets ────────────────────────────────────────

    def _auto_detect_assets(self) -> None:
        browsers = default_browsers_path(self.project_root)
        if browsers.is_dir():
            self.browsers_path_var.set(str(browsers))

        mermaid = default_mermaid_path(self.project_root)
        if mermaid.is_file():
            self.mermaid_js_var.set(str(mermaid))

        fonts = default_fonts_path(self.project_root)
        if fonts.is_dir():
            self.font_dir_var.set(str(fonts))

    # ─── Conversion Logic ──────────────────────────────────────────

    def _validate_input(self) -> Path | None:
        input_str = self.input_var.get().strip()
        if not input_str:
            self.input_error_var.set("مسیر ورودی را مشخص کنید")
            return None

        input_path = Path(input_str)
        if not input_path.exists():
            self.input_error_var.set("مسیر وارد شده وجود ندارد")
            return None

        self.input_error_var.set("")
        return input_path

    def _build_convert_options(self) -> ConvertOptions:
        # Resolve mermaid source
        mermaid_url = self.mermaid_url_var.get().strip()
        if mermaid_url:
            mermaid_source = mermaid_url
        else:
            mermaid_js = self.mermaid_js_var.get().strip()
            if mermaid_js and Path(mermaid_js).is_file():
                mermaid_source = mermaid_js
            else:
                mermaid_source = str(default_mermaid_path(self.project_root))

        # Font settings
        font_file = None
        font_dir = None
        font_file_str = self.font_file_var.get().strip()
        font_dir_str = self.font_dir_var.get().strip()

        if font_file_str and Path(font_file_str).is_file():
            font_file = Path(font_file_str)
        elif font_dir_str and Path(font_dir_str).is_dir():
            font_dir = Path(font_dir_str)

        # Custom CSS
        custom_css = None
        css_str = self.css_var.get().strip()
        if css_str and Path(css_str).is_file():
            custom_css = Path(css_str)

        # Timeout
        try:
            timeout = int(self.mermaid_timeout_var.get().strip())
        except ValueError:
            timeout = 30_000

        # DOCX-specific options
        try:
            docx_image_scale = int(self.docx_image_scale_var.get().strip())
        except ValueError:
            docx_image_scale = 3
        try:
            docx_image_min_width = float(self.docx_image_min_width_var.get().strip())
        except ValueError:
            docx_image_min_width = 4.0
        try:
            docx_image_max_width = float(self.docx_image_max_width_var.get().strip())
        except ValueError:
            docx_image_max_width = 6.5
        try:
            docx_font_size = int(self.docx_font_size_var.get().strip())
        except ValueError:
            docx_font_size = 12

        return ConvertOptions(
            font_family=self.font_family_var.get(),
            font_file=font_file,
            font_dir=font_dir,
            custom_css=custom_css,
            mermaid_source=mermaid_source,
            mermaid_theme=self.mermaid_theme_var.get(),
            mermaid_timeout_ms=timeout,
            page_format=self.page_format_var.get(),
            margin=self.margin_var.get().strip() or "15mm",
            landscape=self.landscape_var.get(),
            keep_html=self.keep_html_var.get(),
            ignore_mermaid_errors=self.ignore_mermaid_errors_var.get(),
            verbose=False,
            output_format=self.format_var.get(),
            docx_font_size_pt=docx_font_size,
            docx_image_scale=docx_image_scale,
            docx_image_min_width=docx_image_min_width,
            docx_image_max_width=docx_image_max_width,
        )

    def _start_conversion(self) -> None:
        input_path = self._validate_input()
        if input_path is None:
            return

        # Wrap-RTL mode: transform Markdown without conversion
        if self.format_var.get() == "wrap-rtl":
            self._run_wrap_rtl(input_path)
            return

        # Validate mermaid
        mermaid_url = self.mermaid_url_var.get().strip()
        if not mermaid_url:
            mermaid_js = self.mermaid_js_var.get().strip()
            if not mermaid_js or not Path(mermaid_js).is_file():
                mermaid_default = default_mermaid_path(self.project_root)
                if not mermaid_default.is_file():
                    messagebox.showerror(
                        "خطا - Mermaid",
                        "فایل mermaid.min.js پیدا نشد.\n\n"
                        f"مسیر مورد انتظار:\n{mermaid_default}\n\n"
                        "فایل mermaid.min.js را در فولدر vendor/ قرار دهید.",
                    )
                    return

        # Validate browsers
        browsers_str = self.browsers_path_var.get().strip()
        if browsers_str and Path(browsers_str).is_dir():
            set_playwright_browsers_path(Path(browsers_str), force=True)
        else:
            browsers_default = default_browsers_path(self.project_root)
            if browsers_default.is_dir():
                set_playwright_browsers_path(browsers_default, force=False)
            else:
                messagebox.showerror(
                    "خطا - مرورگر",
                    "فولدر مرورگرها (browsers) پیدا نشد.\n\n"
                    f"مسیر مورد انتظار:\n{browsers_default}\n\n"
                    "Chromium مخصوص Playwright را در فولدر browsers/ قرار دهید.\n"
                    "راهنما: README.md بخش نصب سریع",
                )
                return

        # Build jobs
        extensions = normalize_extensions(self.extensions_var.get().split())
        output_str = self.output_var.get().strip()
        output_path = Path(output_str) if output_str else None

        try:
            jobs = build_jobs(
                input_path=input_path,
                output=output_path,
                recursive=self.recursive_var.get(),
                extensions=extensions,
                keep_html=self.keep_html_var.get(),
                output_format=self.format_var.get(),
            )
        except ConversionError as exc:
            messagebox.showerror("خطا", str(exc))
            return

        if not jobs:
            messagebox.showinfo("اطلاع", "هیچ فایل Markdown‌ای پیدا نشد.")
            return

        # Start conversion
        self._clear_log()
        self._log(f"شروع تبدیل {len(jobs)} فایل...", "info")

        self.convert_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.cancel_event.clear()

        options = self._build_convert_options()
        self.conversion_thread = ConversionThread(
            jobs=jobs,
            options=options,
            progress_queue=self.progress_queue,
            cancel_event=self.cancel_event,
        )
        self.conversion_thread.start()
        self._poll_progress()

    def _run_wrap_rtl(self, input_path: Path) -> None:
        """Run the wrap-rtl Markdown transformation (no PDF/DOCX conversion)."""
        from .converter import discover_markdown_files
        from .rtl_wrapper import WrapOptions, wrap_rtl_in_markdown

        extensions = normalize_extensions(self.extensions_var.get().split())

        if input_path.is_file():
            if input_path.suffix.lower() not in extensions:
                messagebox.showerror("خطا", f"این فایل یک Markdown نیست: {input_path}")
                return
            sources = [input_path]
            input_root = None
        elif input_path.is_dir():
            sources = discover_markdown_files(
                input_path, recursive=self.recursive_var.get(), extensions=extensions
            )
            input_root = input_path
        else:
            messagebox.showerror("خطا", f"مسیر نامعتبر: {input_path}")
            return

        if not sources:
            messagebox.showinfo("اطلاع", "هیچ فایل Markdown‌ای پیدا نشد.")
            return

        output_str = self.output_var.get().strip()
        output = Path(output_str).resolve() if output_str else None

        self._clear_log()
        self._log(f"شروع تبدیل Markdown به نسخه RTL ({len(sources)} فایل)...", "info")

        options = WrapOptions(enabled=True)
        successes = 0
        failures = 0

        for source in sources:
            try:
                text = source.read_text(encoding="utf-8-sig")
                transformed = wrap_rtl_in_markdown(text, options)
                destination = self._resolve_wrap_rtl_output(source, output, input_root)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(transformed, encoding="utf-8")
                self._log(f"✓ {source.name} → {destination.name}", "success")
                successes += 1
            except Exception as exc:  # noqa: BLE001
                self._log(f"✗ {source.name} - خطا: {exc}", "error")
                failures += 1
                if self.fail_fast_var.get():
                    break

        self._log("─" * 40)
        self._log(f"نتیجه: {successes} موفق، {failures} ناموفق", "summary")

    @staticmethod
    def _resolve_wrap_rtl_output(
        source: Path, output: Path | None, input_root: Path | None
    ) -> Path:
        """Compute output path for wrap-rtl transform in GUI mode."""
        if output is None:
            # Default: write next to source with .rtl suffix
            return source.with_suffix(f".rtl{source.suffix}")

        if input_root is None:
            if output.suffix.lower() in {".md", ".markdown"}:
                return output
            return output / source.name

        relative = source.relative_to(input_root)
        return output / relative

    def _cancel_conversion(self) -> None:
        self.cancel_event.set()
        self._log("در حال لغو...", "info")

    def _poll_progress(self) -> None:
        try:
            while True:
                event = self.progress_queue.get_nowait()
                self._handle_progress_event(event)
        except queue.Empty:
            pass

        if self.conversion_thread and self.conversion_thread.is_alive():
            self.root.after(100, self._poll_progress)
        else:
            # Final poll to catch remaining events
            try:
                while True:
                    event = self.progress_queue.get_nowait()
                    self._handle_progress_event(event)
            except queue.Empty:
                pass
            self.convert_btn.configure(state="normal")
            self.cancel_btn.configure(state="disabled")

    def _handle_progress_event(self, event: ProgressEvent) -> None:
        if event.event_type == "start":
            self._log(f"تعداد فایل‌ها: {event.total}", "info")

        elif event.event_type == "success":
            assert event.job is not None
            self._log(
                f"✓ {event.job.source.name} → {event.job.output.name}"
                f"  ({event.completed}/{event.total})",
                "success",
            )

        elif event.event_type == "error":
            if event.job:
                self._log(
                    f"✗ {event.job.source.name} - خطا: {event.error}"
                    f"  ({event.completed}/{event.total})",
                    "error",
                )
            else:
                self._log(f"✗ خطای غیرمنتظره: {event.error}", "error")

        elif event.event_type == "done":
            successes = event.completed
            # Count actual errors from log (approximate)
            self._log("─" * 40)
            self._log(f"نتیجه: {successes} موفق، {event.total - successes} ناموفق", "summary")

        elif event.event_type == "cancelled":
            self._log("─" * 40)
            self._log(
                f"لغو شد. {event.completed} از {event.total} فایل تبدیل شد.", "info"
            )


def launch_gui(project_root: Path | None = None) -> None:
    """Create and run the GUI application."""
    root = tk.Tk()

    if project_root is None:
        project_root = find_project_root()

    MainWindow(root, project_root)
    root.mainloop()


def main() -> int:
    """Entry point for fa-md-pdf-gui command."""
    launch_gui()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
