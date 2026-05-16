from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable


DEFAULT_MERMAID_RELATIVE_PATH = Path("vendor") / "mermaid.min.js"
DEFAULT_BROWSERS_RELATIVE_PATH = Path("browsers")
DEFAULT_FONTS_RELATIVE_PATH = Path("fonts")

PREFERRED_FONT_FILES = (
    "Vazirmatn-Regular.ttf",
    "Vazirmatn-Medium.ttf",
    "Vazirmatn-Light.ttf",
    "Vazirmatn-Bold.ttf",
)


def _path_parents(start: Path) -> Iterable[Path]:
    """Yield start directory and all parents, without requiring the path to exist."""
    try:
        resolved = start.resolve()
    except OSError:
        resolved = start.absolute()

    if resolved.suffix and not resolved.is_dir():
        resolved = resolved.parent

    yield resolved
    yield from resolved.parents


def find_project_root(input_path: Path | None = None, cwd: Path | None = None) -> Path:
    """
    Find the project root for offline assets.

    Priority:
    1. Current working directory and its parents.
    2. Input path directory and its parents.
    3. Current working directory.

    A directory is treated as project root when it contains one of these common
    offline asset locations: vendor/mermaid.min.js, browsers/, fonts/.
    """
    cwd = cwd or Path.cwd()
    starts: list[Path] = [cwd]
    if input_path is not None:
        starts.append(input_path)

    seen: set[Path] = set()
    for start in starts:
        for candidate in _path_parents(start):
            if candidate in seen:
                continue
            seen.add(candidate)

            if (
                (candidate / DEFAULT_MERMAID_RELATIVE_PATH).is_file()
                or (candidate / DEFAULT_BROWSERS_RELATIVE_PATH).is_dir()
                or (candidate / DEFAULT_FONTS_RELATIVE_PATH).is_dir()
                or ((candidate / "pyproject.toml").is_file() and (candidate / "src" / "fa_md_pdf").is_dir())
            ):
                return candidate

    return cwd.resolve()


def resolve_user_path(value: str | Path, project_root: Path) -> Path:
    """
    Resolve a user path.

    Relative paths are first resolved from the current working directory. If the
    file does not exist there, the same relative path is checked from project_root.
    """
    path = Path(value).expanduser()
    if path.is_absolute():
        return path.resolve()

    cwd_candidate = (Path.cwd() / path).resolve()
    if cwd_candidate.exists():
        return cwd_candidate

    root_candidate = (project_root / path).resolve()
    if root_candidate.exists():
        return root_candidate

    return cwd_candidate


def default_mermaid_path(project_root: Path) -> Path:
    return (project_root / DEFAULT_MERMAID_RELATIVE_PATH).resolve()


def default_browsers_path(project_root: Path) -> Path:
    return (project_root / DEFAULT_BROWSERS_RELATIVE_PATH).resolve()


def default_fonts_path(project_root: Path) -> Path:
    return (project_root / DEFAULT_FONTS_RELATIVE_PATH).resolve()


def set_playwright_browsers_path(path: Path | None, *, force: bool = False) -> Path | None:
    """
    Set PLAYWRIGHT_BROWSERS_PATH for the current process.

    If force is False, an already existing environment variable is respected.
    """
    if path is None:
        return None

    if "PLAYWRIGHT_BROWSERS_PATH" in os.environ and not force:
        return Path(os.environ["PLAYWRIGHT_BROWSERS_PATH"])

    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(path)
    return path


def find_preferred_font_file(fonts_dir: Path) -> Path | None:
    for name in PREFERRED_FONT_FILES:
        candidate = fonts_dir / name
        if candidate.is_file():
            return candidate.resolve()
    return None
