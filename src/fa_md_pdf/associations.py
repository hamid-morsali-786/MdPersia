"""Per-user Windows file association for the Markdown viewer.

HKCU only (no elevation), and unregister removes exactly the keys this module
creates, leaving the user's own default-program choice for `.md` untouched.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

PROG_ID = "MdPersia.Markdown"
PROGID_KEY = rf"Software\Classes\{PROG_ID}"
APP_NAME = "MdPersia Markdown Viewer"
VERB_LABEL = "باز کردن با MdPersia"
EXTENSIONS = (".md", ".markdown")
REGISTERED_APPS_KEY = r"Software\RegisteredApplications"
VIEWER_FLAG = "--gui"


@dataclass(frozen=True)
class RegEntry:
    """A single registry value: key path, value name, value data."""

    key: str
    name: str
    value: str

    @property
    def location(self) -> str:
        return f"HKCU\\{self.key}\\{self.name}" if self.name else f"HKCU\\{self.key}"


def open_command(exe: str, extra_args: str | None = None) -> str:
    """Command line Explorer runs for a double-clicked file.

    Double-clicking must open the viewer, never start a conversion: `mdpersia file.md`
    without --gui is the CLI converter. The native Tauri exe also takes --gui because
    `startup_arguments` keeps only arguments that name an existing file, so the flag is
    inert there and cannot be mistaken for a document.
    """
    if extra_args is None:
        name = Path(exe).name.lower()
        launcher = "-m mdpersia " if name.startswith("python") else ""
        extra_args = f"{launcher}{VIEWER_FLAG}"
    quoted = f'"{exe}"'
    tail = f" {extra_args}" if extra_args else ""
    return f'{quoted}{tail} "%1"'


def build_entries(exe_path: str | Path, icon_path: str | Path | None = None) -> list[RegEntry]:
    exe = str(Path(exe_path))
    # Use the application's Markdown mark even when Python launches the GUI.
    bundled_icon = Path(__file__).parent / "assets" / "mdpersia.ico"
    icon = str(Path(icon_path)) if icon_path else str(bundled_icon)
    icon_value = f'"{icon}",0'
    command = open_command(exe)

    entries = [
        RegEntry(PROGID_KEY, "", APP_NAME),
        RegEntry(PROGID_KEY, "FriendlyTypeName", APP_NAME),
        RegEntry(rf"{PROGID_KEY}\DefaultIcon", "", icon_value),
        RegEntry(rf"{PROGID_KEY}\shell\open\command", "", command),
        RegEntry(rf"{PROGID_KEY}\Application", "AppUserModelID", "MdPersia.Viewer"),
    ]

    # Listed in "Open with" and in Settings > Default apps, without claiming .md.
    for ext in EXTENSIONS:
        entries.append(RegEntry(rf"{PROGID_KEY}\SupportedTypes", ext, ""))

    entries.append(RegEntry(rf"{PROGID_KEY}\OpenWithList", "a", Path(exe).name))
    entries.append(RegEntry(REGISTERED_APPS_KEY, "MdPersia", rf"{PROGID_KEY}\Capabilities"))
    entries.append(RegEntry(rf"{PROGID_KEY}\Capabilities", "ApplicationName", APP_NAME))
    for ext in EXTENSIONS:
        entries.append(RegEntry(rf"{PROGID_KEY}\Capabilities\FileAssociations", ext, PROG_ID))

    # Right-click verb on every .md file; does not change any default handler.
    for ext in EXTENSIONS:
        verb = rf"Software\Classes\SystemFileAssociations\{ext}\shell\MdPersia.view"
        entries.append(RegEntry(verb, "", VERB_LABEL))
        entries.append(RegEntry(verb, "Icon", icon_value))
        entries.append(RegEntry(rf"{verb}\command", "", command))

    return entries


def build_uninstall_keys() -> list[str]:
    """Key trees to delete on unregister, deepest first."""
    trees = [PROGID_KEY]
    trees += [rf"Software\Classes\SystemFileAssociations\{ext}\shell\MdPersia.view" for ext in EXTENSIONS]
    return trees


def _reg():
    import winreg

    return winreg


def register(exe_path: str | Path, icon_path: str | Path | None = None) -> list[str]:
    """Write the per-user association. Returns the locations that were written."""
    if sys.platform != "win32":
        raise OSError("File associations are only available on Windows.")
    winreg = _reg()
    written: list[str] = []
    for entry in build_entries(exe_path, icon_path):
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, entry.key) as key:
            winreg.SetValueEx(key, entry.name, 0, winreg.REG_SZ, entry.value)
        written.append(entry.location)
    notify_shell()
    return written


def unregister() -> list[str]:
    """Remove only the keys this module creates. Missing keys are skipped."""
    if sys.platform != "win32":
        raise OSError("File associations are only available on Windows.")
    winreg = _reg()
    removed: list[str] = []
    for tree in build_uninstall_keys():
        try:
            parent, _, leaf = tree.rpartition("\\")
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, parent, 0, winreg.KEY_ALL_ACCESS) as pk:
                winreg.DeleteKey(pk, leaf)
            removed.append(f"HKCU\\{tree}")
        except FileNotFoundError:
            continue
    # RegisteredApplications marker sits under a different parent.
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTERED_APPS_KEY, 0, winreg.KEY_ALL_ACCESS) as pk:
            winreg.DeleteValue(pk, "MdPersia")
        removed.append(f"HKCU\\{REGISTERED_APPS_KEY}\\MdPersia")
    except FileNotFoundError:
        pass
    notify_shell()
    return removed


def read_open_command() -> str | None:
    """The command Explorer currently runs, or None when nothing is registered."""
    if sys.platform != "win32":
        return None
    winreg = _reg()
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, rf"{PROGID_KEY}\shell\open\command") as key:
            return winreg.QueryValue(key, None) or None
    except OSError:
        return None


def split_command(command: str) -> tuple[str, list[str]]:
    """Split a registry command line into (executable, args), dropping the quotes."""
    import shlex

    try:
        parts = [p.strip('"') for p in shlex.split(command, posix=False)]
    except ValueError:
        return "", []
    return (parts[0], parts[1:]) if parts else ("", [])


def _module_resolvable(exe: str, module: str) -> bool | None:
    """Ask the registered interpreter whether the module still exists. None = could not ask."""
    import subprocess

    probe = "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec(sys.argv[1]) else 1)"
    try:
        done = subprocess.run(
            [exe, "-c", probe, module], timeout=20, capture_output=True, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return done.returncode == 0


def validate_open_command(
    command: str | None,
    *,
    module_resolver=_module_resolvable,
    exe_exists: Callable[[str], bool] = lambda p: Path(p).is_file(),
) -> tuple[bool, str]:
    """A stale entry outlives its target, so key presence alone is not 'working'."""
    if not command:
        return False, "not registered"
    exe, args = split_command(command)
    if not exe:
        return False, "command is unreadable"
    if not exe_exists(exe):
        return False, f"executable is missing: {exe}"
    if len(args) >= 2 and args[0] == "-m":
        if module_resolver(exe, args[1]) is False:
            return False, f"module '{args[1]}' is not importable by {exe}"
        if VIEWER_FLAG not in args:
            return False, f"command lacks {VIEWER_FLAG}, so a double-click runs the converter"
    return True, exe


def association_state() -> tuple[bool, str, str]:
    """(working, command, explanation) for the current per-user registration."""
    command = read_open_command()
    ok, reason = validate_open_command(command)
    return ok, command or "", reason


def is_registered() -> bool:
    if sys.platform != "win32":
        return False
    winreg = _reg()
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, rf"{PROGID_KEY}\shell\open\command"):
            return True
    except OSError:
        return False


def notify_shell() -> None:
    """Tell Explorer the association database changed (best effort)."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        SHCNE_ASSOCCHANGED = 0x08000000
        SHCNF_IDLIST = 0x0000
        ctypes.windll.shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, None, None)
    except Exception:
        pass


def resolve_viewer_exe(project_root: Path, override: str | Path | None = None) -> Path:
    """Prefer an explicit path, then the built Tauri exe, then the module launcher."""
    if override:
        return Path(override)
    release = (
        project_root / "desktop-tauri" / "src-tauri" / "target" / "release" / "MdPersia.exe"
    )
    if release.is_file():
        return release
    return _windowless_launcher(Path(sys.executable))


def _windowless_launcher(exe: Path) -> Path:
    """A double-click must not leave a console window open behind the viewer."""
    if sys.platform != "win32" or exe.stem.lower() != "python":
        return exe
    windowless = exe.with_name("pythonw.exe")
    return windowless if windowless.is_file() else exe
