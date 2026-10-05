"""Zone A: Batch document queue management panel for fa-md-pdf GUI."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, ttk
from typing import Callable

from .converter import discover_markdown_files, normalize_extensions
from .gui_theme import ThemeColors


@dataclass
class QueueItem:
    """Represents a document in the conversion batch queue."""

    path: Path
    name: str
    size_str: str
    status: str
    error: str | None = None


def format_file_size(size_bytes: int) -> str:
    """Format byte size into human readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


class DocumentQueuePanel(ttk.Frame):
    """Batch document list and queue management component."""

    COLUMNS = ("name", "size", "status", "path")

    def __init__(
        self,
        parent: tk.Widget,
        on_file_selected: Callable[[Path], None] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(parent, **kwargs)
        self.on_file_selected = on_file_selected
        self._items: dict[str, QueueItem] = {}
        self._build_header()
        self._build_treeview()
        self._build_toolbar()

    def _build_header(self) -> None:
        """Build top queue header bar with count badge."""
        hdr = ttk.Frame(self)
        hdr.pack(fill=tk.X, padx=4, pady=(2, 4))
        title = ttk.Label(hdr, text="صف اسناد (Batch Queue)", style="Title.TLabel")
        title.pack(side=tk.LEFT)
        self.counter_label = ttk.Label(hdr, text="۰ فایل", style="Muted.TLabel")
        self.counter_label.pack(side=tk.RIGHT)

    def _build_treeview(self) -> None:
        """Build treeview table for batch files."""
        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True, padx=4)

        self.tree = ttk.Treeview(
            container,
            columns=self.COLUMNS,
            show="headings",
            selectmode="extended",
        )
        self._setup_columns()
        scroll = ttk.Scrollbar(container, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

    def _setup_columns(self) -> None:
        """Configure column headings and alignments."""
        self.tree.heading("name", text="نام فایل")
        self.tree.heading("size", text="حجم")
        self.tree.heading("status", text="وضعیت")
        self.tree.heading("path", text="مسیر کامل")

        self.tree.column("name", width=140, anchor=tk.W)
        self.tree.column("size", width=70, anchor=tk.CENTER)
        self.tree.column("status", width=90, anchor=tk.CENTER)
        self.tree.column("path", width=200, anchor=tk.W)

    def _build_toolbar(self) -> None:
        """Build bottom action buttons for queue manipulation."""
        bar = ttk.Frame(self)
        bar.pack(fill=tk.X, padx=4, pady=4)
        ttk.Button(bar, text="+ فایل", command=self._pick_files).pack(side=tk.LEFT, padx=2)
        ttk.Button(bar, text="+ فولدر", command=self._pick_dir).pack(side=tk.LEFT, padx=2)
        ttk.Button(bar, text="حذف", command=self.remove_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(bar, text="پاکسازی", command=self.clear_all).pack(side=tk.RIGHT, padx=2)

    def _pick_files(self) -> None:
        """Open file dialog to pick markdown files."""
        paths = filedialog.askopenfilenames(
            title="انتخاب فایل‌های Markdown",
            filetypes=[("Markdown", "*.md *.markdown"), ("همه فایل‌ها", "*.*")],
        )
        if paths:
            self.add_files(paths)

    def _pick_dir(self) -> None:
        """Open directory dialog to pick folder containing markdown files."""
        path = filedialog.askdirectory(title="انتخاب فولدر فایل‌های Markdown")
        if path:
            self.add_directory(path, recursive=True)

    def _on_tree_select(self, _event: tk.Event) -> None:
        """Handle tree selection change and trigger callback."""
        selected = self.tree.selection()
        if not selected or not self.on_file_selected:
            return
        item_id = selected[0]
        if item_id in self._items:
            self.on_file_selected(self._items[item_id].path)

    def add_files(self, paths: list[str | Path]) -> int:
        """Add individual files to queue and return count added."""
        added = 0
        for p in paths:
            path_obj = Path(p).resolve()
            if not path_obj.is_file() or str(path_obj) in self._items:
                continue
            self._insert_item(path_obj)
            added += 1
        self._update_counter()
        return added

    def add_directory(
        self, dir_path: str | Path, recursive: bool = True, extensions: list[str] | None = None
    ) -> int:
        """Discover and add markdown files in directory."""
        dir_obj = Path(dir_path).resolve()
        if not dir_obj.is_dir():
            return 0
        exts = normalize_extensions(extensions or [".md", ".markdown"])
        files = discover_markdown_files(dir_obj, recursive=recursive, extensions=exts)
        return self.add_files(files)

    def _insert_item(self, path: Path) -> None:
        """Insert single item row into Treeview."""
        try:
            size_val = format_file_size(path.stat().st_size)
        except OSError:
            size_val = "-"
        key = str(path)
        item = QueueItem(path=path, name=path.name, size_str=size_val, status="در انتظار")
        self._items[key] = item
        self.tree.insert(
            "",
            tk.END,
            iid=key,
            values=(item.name, item.size_str, item.status, str(item.path)),
        )

    def remove_selected(self) -> None:
        """Remove highlighted rows from queue."""
        selected = list(self.tree.selection())
        for item_id in selected:
            self.tree.delete(item_id)
            self._items.pop(item_id, None)
        self._update_counter()

    def clear_all(self) -> None:
        """Remove all rows from queue."""
        for item_id in list(self._items.keys()):
            self.tree.delete(item_id)
        self._items.clear()
        self._update_counter()

    def get_files(self) -> list[Path]:
        """Return list of all file paths in queue."""
        return [item.path for item in self._items.values()]

    def update_status(self, file_path: Path, status: str, error: str | None = None) -> None:
        """Update display status of a file in the queue."""
        key = str(file_path.resolve())
        if key in self._items:
            item = self._items[key]
            item.status = status
            item.error = error
            self.tree.item(key, values=(item.name, item.size_str, item.status, str(item.path)))

    def _update_counter(self) -> None:
        """Refresh queue counter badge text."""
        count = len(self._items)
        self.counter_label.configure(text=f"{count} فایل")

    def apply_colors(self, colors: ThemeColors) -> None:
        """Update colors based on theme changes."""
        self.counter_label.configure(foreground=colors.text_muted)
