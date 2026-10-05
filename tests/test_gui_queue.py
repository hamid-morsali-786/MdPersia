import tkinter as tk
from pathlib import Path
import pytest
from fa_md_pdf.gui_queue import DocumentQueuePanel, QueueItem
from fa_md_pdf.gui_theme import DARK_PALETTE


@pytest.fixture(scope="module")
def tk_root():
    root = tk.Tk()
    root.withdraw()
    yield root
    try:
        root.destroy()
    except Exception:
        pass


def test_queue_add_files_and_clear(tk_root, tmp_path):
    f1 = tmp_path / "doc1.md"
    f2 = tmp_path / "doc2.markdown"
    f1.write_text("# Doc 1", encoding="utf-8")
    f2.write_text("# Doc 2", encoding="utf-8")

    selected = []
    panel = DocumentQueuePanel(tk_root, on_file_selected=lambda p: selected.append(p))
    added = panel.add_files([f1, f2])
    assert added == 2
    assert len(panel.get_files()) == 2
    assert panel.get_files()[0] == f1.resolve()

    panel.clear_all()
    assert len(panel.get_files()) == 0


def test_queue_add_directory_recursive(tk_root, tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    (tmp_path / "root.md").write_text("root", encoding="utf-8")
    (sub / "nested.md").write_text("nested", encoding="utf-8")
    (sub / "ignore.txt").write_text("ignore", encoding="utf-8")

    panel = DocumentQueuePanel(tk_root)
    added = panel.add_directory(tmp_path, recursive=True)
    assert added == 2
    files = panel.get_files()
    assert len(files) == 2
    names = {f.name for f in files}
    assert "root.md" in names
    assert "nested.md" in names


def test_queue_status_update_and_removal(tk_root, tmp_path):
    f = tmp_path / "doc.md"
    f.write_text("sample", encoding="utf-8")

    panel = DocumentQueuePanel(tk_root)
    panel.add_files([f])
    panel.update_status(f, "موفق")

    # Select and remove
    items = panel.tree.get_children()
    assert len(items) == 1
    panel.tree.selection_set(items[0])
    panel.remove_selected()
    assert len(panel.get_files()) == 0


def test_queue_apply_colors(tk_root):
    panel = DocumentQueuePanel(tk_root)
    panel.apply_colors(DARK_PALETTE)
    assert panel.counter_label.cget("foreground") != ""
