import os
import sys
import tkinter as tk
import pytest

# Ensure TCL and TK library paths are accurately registered for Windows
base_prefix = getattr(sys, "base_prefix", sys.prefix)
tcl_dir = os.path.join(base_prefix, "tcl", "tcl8.6")
tk_dir = os.path.join(base_prefix, "tcl", "tk8.6")
if os.path.isdir(tcl_dir):
    os.environ.setdefault("TCL_LIBRARY", tcl_dir)
if os.path.isdir(tk_dir):
    os.environ.setdefault("TK_LIBRARY", tk_dir)


@pytest.fixture(scope="session")
def session_tk_root():
    root = tk.Tk()
    root.withdraw()
    yield root
    try:
        root.destroy()
    except Exception:
        pass


@pytest.fixture
def tk_root(session_tk_root):
    # Clean up children from previous test so each test gets clean state
    for child in list(session_tk_root.children.values()):
        try:
            child.destroy()
        except Exception:
            pass
    return session_tk_root
