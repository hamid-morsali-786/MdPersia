"""Graphical user interface for fa-md-pdf using modern modular architecture."""

from __future__ import annotations

import datetime
import queue
import threading
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox, ttk

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
    default_mermaid_path,
    find_project_root,
    set_playwright_browsers_path,
)
from .gui_inspector import ParametersInspectorPanel
from .gui_queue import DocumentQueuePanel, QueueItem
from .gui_theme import ModernThemeManager
from .gui_workspace import LivePreviewConsolePanel, StatusBarPanel


@dataclass
class ProgressEvent:
    """Event posted from ConversionThread to the GUI queue."""

    event_type: str  # "start" | "success" | "error" | "done" | "cancelled"
    job: ConvertJob | None = None
    total: int = 0
    completed: int = 0
    error: str | None = None


def _resolve_job_output_path(
    source: Path,
    output_dir: Path | None,
    ext: str,
    used_paths: set[Path],
    relative_path: Path | None = None,
    is_custom_file: bool = False,
) -> Path:
    """Resolve non-colliding destination path for batch conversion."""
    if not output_dir:
        return source.with_suffix(ext)
    if is_custom_file:
        output_dir.parent.mkdir(parents=True, exist_ok=True)
        used_paths.add(output_dir)
        return output_dir
    if relative_path:
        dest = output_dir / relative_path.with_suffix(ext)
        dest.parent.mkdir(parents=True, exist_ok=True)
        used_paths.add(dest)
        return dest
    return _find_unique_name(source, output_dir, ext, used_paths)


def _find_unique_name(source: Path, out_dir: Path, ext: str, used: set[Path]) -> Path:
    """Find unique output path by adding numeric suffix if needed."""
    candidate = out_dir / source.with_suffix(ext).name
    counter = 2
    while candidate in used:
        candidate = out_dir / f"{source.stem}_{counter}{ext}"
        counter += 1
    used.add(candidate)
    return candidate


class ConversionThread(threading.Thread):
    """Background thread that runs conversions and posts progress events."""

    def __init__(
        self,
        jobs: list[ConvertJob],
        options: ConvertOptions,
        progress_queue: queue.Queue[ProgressEvent],
        cancel_event: threading.Event,
        fail_fast: bool = False,
    ) -> None:
        super().__init__(daemon=True)
        self.jobs = jobs
        self.options = options
        self.progress_queue = progress_queue
        self.cancel_event = cancel_event
        self.fail_fast = fail_fast
        self._completed = 0

    def _on_progress(self, job: ConvertJob, ok: bool, error: str | None) -> None:
        self._completed += 1
        ev_type = "success" if ok else "error"
        self.progress_queue.put(
            ProgressEvent(
                event_type=ev_type,
                job=job,
                total=len(self.jobs),
                completed=self._completed,
                error=error,
            )
        )

    def run(self) -> None:
        try:
            self.progress_queue.put(ProgressEvent(event_type="start", total=len(self.jobs)))
            convert_jobs(
                self.jobs,
                options=self.options,
                fail_fast=self.fail_fast,
                on_progress=self._on_progress,
                cancel_event=self.cancel_event,
            )
        except Exception as exc:  # noqa: BLE001
            self.progress_queue.put(ProgressEvent(event_type="error", error=str(exc)))

        ev_type = "cancelled" if self.cancel_event.is_set() else "done"
        self.progress_queue.put(
            ProgressEvent(event_type=ev_type, total=len(self.jobs), completed=self._completed)
        )


class WrapRtlThread(threading.Thread):
    """Background worker thread for wrap-rtl markdown transformations."""

    def __init__(
        self,
        jobs: list[ConvertJob],
        progress_queue: queue.Queue[ProgressEvent],
        cancel_event: threading.Event,
        fail_fast: bool = False,
    ) -> None:
        super().__init__(daemon=True)
        self.jobs = jobs
        self.progress_queue = progress_queue
        self.cancel_event = cancel_event
        self.fail_fast = fail_fast
        self._completed = 0

    def run(self) -> None:
        from .rtl_wrapper import WrapOptions, wrap_rtl_in_markdown

        opts = WrapOptions(enabled=True)
        total = len(self.jobs)
        self.progress_queue.put(ProgressEvent(event_type="start", total=total))

        for job in self.jobs:
            if self.cancel_event.is_set():
                break
            self._process_single_rtl_job(job, opts, total)
            if self.fail_fast and not self.cancel_event.is_set():
                # If last event was error and fail_fast, stop
                pass

        ev_type = "cancelled" if self.cancel_event.is_set() else "done"
        self.progress_queue.put(ProgressEvent(event_type=ev_type, total=total, completed=self._completed))

    def _process_single_rtl_job(self, job: ConvertJob, opts: WrapOptions, total: int) -> None:
        from .rtl_wrapper import wrap_rtl_in_markdown

        try:
            job.output.parent.mkdir(parents=True, exist_ok=True)
            content = job.source.read_text(encoding="utf-8-sig")
            job.output.write_text(wrap_rtl_in_markdown(content, opts), encoding="utf-8")
            self._completed += 1
            self.progress_queue.put(
                ProgressEvent(event_type="success", job=job, total=total, completed=self._completed)
            )
        except Exception as exc:  # noqa: BLE001
            self._completed += 1
            self.progress_queue.put(
                ProgressEvent(event_type="error", job=job, total=total, completed=self._completed, error=str(exc))
            )


class MainWindow:
    """Main modern 3-zone desktop application window."""

    def __init__(self, root: tk.Tk, project_root: Path) -> None:
        self.root = root
        self.project_root = project_root
        self.progress_queue: queue.Queue[ProgressEvent] = queue.Queue()
        self.cancel_event = threading.Event()
        self.conversion_thread: threading.Thread | None = None
        self.is_watching = False
        self._watch_timer_id: str | None = None
        self._watched_jobs: list[ConvertJob] = []
        self._watched_options: ConvertOptions | None = None
        self._watched_mtimes: dict[Path, float] = {}

        self._setup_window()
        self.theme_manager = ModernThemeManager(root)
        self._build_ui()
        self._bind_legacy_properties()
        self.inspector_panel.auto_detect_assets(self.project_root)
        has_offline = default_browsers_path(self.project_root).is_dir()
        self.status_bar.update_system_status(offline_browsers=has_offline)

    def _setup_window(self) -> None:
        """Set initial window properties."""
        self.root.title("fa-md-pdf - تبدیل اسناد فارسی و RTL به PDF و Word")
        self.root.geometry("1120x760")
        self.root.minsize(920, 620)

    def _build_ui(self) -> None:
        """Build top-level 3-zone layout with paned view."""
        self._build_header_bar()
        self.paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        self.inspector_panel = ParametersInspectorPanel(
            self.paned,
            project_root=self.project_root,
            on_convert=self._start_conversion,
            on_cancel=self._cancel_conversion,
        )
        self.queue_panel = DocumentQueuePanel(
            self.paned,
            on_file_selected=self._on_queue_file_selected,
            get_extensions=self.inspector_panel.get_extensions,
            get_recursive=self.inspector_panel.get_recursive,
        )
        self.workspace_panel = LivePreviewConsolePanel(
            self.paned, on_open_output_dir=self._on_open_output_dir
        )
        self.paned.add(self.queue_panel, weight=2)
        self.paned.add(self.inspector_panel, weight=3)
        self.paned.add(self.workspace_panel, weight=3)

        self.status_bar = StatusBarPanel(self.root)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=6, pady=2)

    def _build_header_bar(self) -> None:
        """Build top navigation and theme switch bar."""
        bar = ttk.Frame(self.root)
        bar.pack(fill=tk.X, padx=8, pady=(6, 2))
        ttk.Label(bar, text="⚡ fa-md-pdf", style="Title.TLabel").pack(side=tk.LEFT)
        ttk.Label(bar, text="میز کار حرفه‌ای تبدیل اسناد Markdown", style="Muted.TLabel").pack(
            side=tk.LEFT, padx=8
        )
        self.theme_btn = ttk.Button(bar, text="🌓 تغییر تم", command=self._toggle_theme)
        self.theme_btn.pack(side=tk.RIGHT)

    def _toggle_theme(self) -> None:
        """Toggle dark/light theme and update subpanels."""
        self.theme_manager.toggle_theme()
        colors = self.theme_manager.get_colors()
        self.queue_panel.apply_colors(colors)
        self.inspector_panel.apply_colors(colors)
        self.workspace_panel.apply_colors(colors)
        self.status_bar.apply_colors(colors)

    def _on_queue_file_selected(self, path: Path) -> None:
        """Update preview panel when a file is selected in the queue."""
        self.workspace_panel.set_preview_file(path)

    def _bind_legacy_properties(self) -> None:
        """Maintain backward compatibility for existing tests."""
        self.format_var = self.inspector_panel.format_var
        self.output_var = self.inspector_panel.output_var
        self.pdf_page_numbers_var = self.inspector_panel.pdf_page_numbers_var
        self.docx_page_numbers_var = self.inspector_panel.docx_page_numbers_var
        self.docx_highlight_code_var = self.inspector_panel.docx_highlight_code_var
        self.watch_var = self.inspector_panel.watch_var
        self.convert_btn = self.inspector_panel.convert_btn
        self.cancel_btn = self.inspector_panel.cancel_btn
        self.input_var = tk.StringVar()
        self.inspector_panel.on_watch_toggle = self._on_watch_toggle

    def _build_convert_options(self) -> ConvertOptions:
        return self.inspector_panel.build_convert_options()

    def _start_conversion(self) -> None:
        """Validate files and start background conversion."""
        queue_items = self.queue_panel.get_queue_items()
        if not queue_items:
            messagebox.showinfo("اطلاع", "لطفاً ابتدا فایلی به صف اسناد اضافه کنید.")
            return

        self.queue_panel.reset_statuses()
        fmt = self.format_var.get()
        options = self._build_convert_options()
        output_dir = Path(self.output_var.get().strip()) if self.output_var.get().strip() else None
        jobs = self._create_jobs_from_queue(queue_items, output_dir, fmt, options.keep_html)

        if fmt == "wrap-rtl":
            self._launch_wrap_rtl_thread(jobs, options)
            return

        if not self._validate_environment():
            return

        self._launch_conversion_thread(jobs, options)

    def _validate_environment(self) -> bool:
        """Verify Mermaid and Playwright browser availability."""
        mermaid_url = self.inspector_panel.mermaid_url_var.get().strip()
        if not mermaid_url:
            js = self.inspector_panel.mermaid_js_var.get().strip()
            if not js or not Path(js).is_file():
                default_js = default_mermaid_path(self.project_root)
                if not default_js.is_file():
                    messagebox.showerror(
                        "خطا - Mermaid",
                        f"فایل mermaid.min.js پیدا نشد:\n{default_js}\nآن را در vendor/ قرار دهید.",
                    )
                    return False

        browsers_str = self.inspector_panel.browsers_path_var.get().strip()
        if browsers_str and Path(browsers_str).is_dir():
            set_playwright_browsers_path(Path(browsers_str), force=True)
        else:
            default_b = default_browsers_path(self.project_root)
            if default_b.is_dir():
                set_playwright_browsers_path(default_b, force=False)
        return True

    def _create_jobs_from_queue(
        self, items: list[QueueItem | Path], output_dir: Path | None, fmt: str, keep_html: bool
    ) -> list[ConvertJob]:
        """Convert list of queue items into ConvertJob records with path collision protection."""
        jobs: list[ConvertJob] = []
        suffix = self.inspector_panel.wrap_rtl_suffix_var.get() or ".rtl.md"
        ext = suffix if fmt == "wrap-rtl" else (".docx" if fmt == "docx" else ".pdf")
        used_paths: set[Path] = set()
        is_single = (
            len(items) == 1
            and output_dir is not None
            and output_dir.suffix.lower() in (".pdf", ".docx", ".md")
        )
        for it in items:
            source = it.path if isinstance(it, QueueItem) else it
            rel = it.relative_path if isinstance(it, QueueItem) else None
            out_file = _resolve_job_output_path(source, output_dir, ext, used_paths, rel, is_single)
            html_out = source.with_suffix(".html") if keep_html else None
            jobs.append(ConvertJob(source=source, output=out_file, html_output=html_out))
        return jobs

    def _launch_conversion_thread(self, jobs: list[ConvertJob], options: ConvertOptions) -> None:
        """Spawn worker thread and begin progress event polling."""
        self.workspace_panel.append_log(f"شروع تبدیل {len(jobs)} فایل...", "info")
        self.inspector_panel.set_running_state(is_running=True)
        self.cancel_event.clear()
        self._watched_jobs = jobs
        self._watched_options = options
        self._record_watched_mtimes()

        self.conversion_thread = ConversionThread(
            jobs=jobs,
            options=options,
            progress_queue=self.progress_queue,
            cancel_event=self.cancel_event,
            fail_fast=self.inspector_panel.fail_fast_var.get(),
        )
        self.conversion_thread.start()
        self._poll_progress()

    def _launch_wrap_rtl_thread(self, jobs: list[ConvertJob], options: ConvertOptions) -> None:
        """Launch background thread for wrap-rtl transformation."""
        self.workspace_panel.append_log(f"شروع تبدیل RTL ({len(jobs)} فایل)...", "info")
        self.inspector_panel.set_running_state(is_running=True)
        self.cancel_event.clear()
        self._watched_jobs = jobs
        self._watched_options = options
        self._record_watched_mtimes()

        self.conversion_thread = WrapRtlThread(
            jobs=jobs,
            progress_queue=self.progress_queue,
            cancel_event=self.cancel_event,
            fail_fast=self.inspector_panel.fail_fast_var.get(),
        )
        self.conversion_thread.start()
        self._poll_progress()

    def _poll_progress(self) -> None:
        """Process background progress events and reschedule."""
        try:
            while True:
                ev = self.progress_queue.get_nowait()
                self._handle_progress_event(ev)
        except queue.Empty:
            pass

        if self.conversion_thread and self.conversion_thread.is_alive():
            self.root.after(80, self._poll_progress)
        else:
            # Final drain of remaining queue events
            try:
                while True:
                    ev = self.progress_queue.get_nowait()
                    self._handle_progress_event(ev)
            except queue.Empty:
                pass
            self._on_conversion_finished()

    def _handle_progress_event(self, ev: ProgressEvent) -> None:
        """Dispatch single progress event to workspace and queue."""
        if ev.event_type == "start":
            self.status_bar.set_status(f"در حال پردازش {ev.total} فایل...", badge_type="running")
        elif ev.event_type == "success" and ev.job:
            self.workspace_panel.append_log(f"✓ {ev.job.source.name} → {ev.job.output.name}", "success")
            self.queue_panel.update_status(ev.job.source, "موفق")
            self.status_bar.set_progress(ev.completed, ev.total)
        elif ev.event_type == "error":
            msg = f"✗ {ev.job.source.name}: {ev.error}" if ev.job else f"✗ خطا: {ev.error}"
            self.workspace_panel.append_log(msg, "error")
            if ev.job:
                self.queue_panel.update_status(ev.job.source, "خطا", ev.error)
        elif ev.event_type == "done":
            self.workspace_panel.append_log(f"پایان تبدیل: {ev.completed} از {ev.total} موفق", "summary")
        elif ev.event_type == "cancelled":
            self.workspace_panel.append_log("عملیات توسط کاربر لغو شد.", "warn")

    def _on_conversion_finished(self) -> None:
        """Handle completion of worker thread and manage watch mode."""
        if self.watch_var.get() and not self.cancel_event.is_set():
            self.is_watching = True
            self.inspector_panel.set_running_state(is_running=False, is_watching=True)
            self.status_bar.set_status("پایش زنده فعال (Watch Mode)", badge_type="running")
            self._schedule_watch_poll()
        else:
            self.is_watching = False
            self.inspector_panel.set_running_state(is_running=False, is_watching=False)
            self.status_bar.reset()

    def _record_watched_mtimes(self) -> None:
        mtimes: dict[Path, float] = {}
        for j in self._watched_jobs:
            if j.source.is_file():
                try:
                    mtimes[j.source] = j.source.stat().st_mtime
                except OSError:
                    pass
        self._watched_mtimes = mtimes

    def _schedule_watch_poll(self) -> None:
        if self.is_watching:
            self._watch_timer_id = self.root.after(1500, self._check_watched_files)

    def _check_watched_files(self) -> None:
        if not self.is_watching or not self._watched_options:
            return
        if self.conversion_thread and self.conversion_thread.is_alive():
            self._schedule_watch_poll()
            return
        changed = [
            j.source
            for j in self._watched_jobs
            if j.source.is_file() and self._is_file_modified(j.source)
        ]
        if changed:
            self.workspace_panel.append_log(
                f"تغییر در {len(changed)} فایل شناسایی شد. تبدیل مجدد...", "info"
            )
            if self._watched_options.output_format == "wrap-rtl":
                self._launch_wrap_rtl_thread(self._watched_jobs, self._watched_options)
            else:
                self._launch_conversion_thread(self._watched_jobs, self._watched_options)
        else:
            self._schedule_watch_poll()

    def _is_file_modified(self, path: Path) -> bool:
        try:
            return path.stat().st_mtime > self._watched_mtimes.get(path, 0)
        except OSError:
            return False

    def _on_watch_toggle(self) -> None:
        """Handle user checking or unchecking watch mode checkbox."""
        if not self.watch_var.get() and self.is_watching:
            self._cancel_conversion()

    def _on_open_output_dir(self) -> None:
        """Open output directory or parent of last job in system file explorer."""
        import os
        import subprocess

        target: Path | None = None
        raw_out = self.output_var.get().strip()
        if raw_out and Path(raw_out).resolve().is_dir():
            target = Path(raw_out).resolve()
        elif self._watched_jobs and self._watched_jobs[0].output.parent.is_dir():
            target = self._watched_jobs[0].output.parent

        if target:
            try:
                os.startfile(str(target))
            except AttributeError:
                subprocess.Popen(["explorer", str(target)])
        else:
            messagebox.showinfo("اطلاع", "پوشه خروجی معتبری برای باز کردن یافت نشد.")

    def _cancel_conversion(self) -> None:
        """Terminate active conversion or watch mode safely."""
        self.cancel_event.set()
        if self.is_watching:
            self.is_watching = False
            self.watch_var.set(False)
            if self._watch_timer_id:
                try:
                    self.root.after_cancel(self._watch_timer_id)
                except Exception:
                    pass
                self._watch_timer_id = None

        if self.conversion_thread and self.conversion_thread.is_alive():
            self.cancel_btn.configure(text="در حال توقف...", state="disabled")
        else:
            self.inspector_panel.set_running_state(is_running=False, is_watching=False)
            self.status_bar.reset()


def launch_gui(project_root: Path | None = None) -> None:
    """Entry point for standalone graphical interface."""
    root = tk.Tk()
    if project_root is None:
        project_root = find_project_root()
    MainWindow(root, project_root)
    root.mainloop()


def main() -> int:
    """Console script entry point."""
    launch_gui()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
