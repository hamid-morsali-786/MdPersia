from __future__ import annotations

import argparse
from contextlib import contextmanager
import os
import sys
from pathlib import Path

from . import __version__
from .defaults import (
    default_browsers_path,
    default_fonts_path,
    default_mermaid_path,
    find_project_root,
    resolve_user_path,
    set_playwright_browsers_path,
)


DEFAULT_FONT_FAMILY = '"Vazirmatn", "Noto Naskh Arabic", "Segoe UI", Tahoma, Arial, sans-serif'


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mdpersia",
        description=(
            "MdPersia: Modern, offline-first Persian and RTL Markdown to PDF and Word (DOCX) converter "
            "with Mermaid support. Offline defaults loaded from ./browsers, ./fonts and ./vendor/mermaid.min.js."
        ),
    )

    parser.add_argument(
        "input",
        type=Path,
        nargs="?",
        default=None,
        help="Markdown file or directory containing Markdown files.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output path for a single file, or output directory for directory input.",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["pdf", "docx"],
        default="pdf",
        help="Output format: pdf or docx. Default: pdf.",
    )
    parser.add_argument(
        "--docx-image-scale",
        type=int,
        default=3,
        choices=[1, 2, 3, 4],
        help=(
            "Image quality multiplier for Mermaid diagrams in DOCX. "
            "Higher = sharper but larger files. Default: 3."
        ),
    )
    parser.add_argument(
        "--docx-image-min-width",
        type=float,
        default=4.0,
        help="Minimum width (in inches) of Mermaid images in DOCX. Default: 4.0.",
    )
    parser.add_argument(
        "--docx-image-max-width",
        type=float,
        default=6.5,
        help="Maximum width (in inches) of Mermaid images in DOCX. Default: 6.5.",
    )
    parser.add_argument(
        "--docx-font-size",
        type=int,
        default=12,
        help="Body font size (in points) for DOCX output. Default: 12.",
    )
    parser.add_argument(
        "--recursive",
        dest="recursive",
        action="store_true",
        default=True,
        help="Search Markdown files recursively when input is a directory. Default: enabled.",
    )
    parser.add_argument(
        "--no-recursive",
        dest="recursive",
        action="store_false",
        help="Only convert Markdown files directly inside the input directory.",
    )
    parser.add_argument(
        "--extensions",
        nargs="+",
        default=[".md", ".markdown"],
        help="Markdown extensions to include. Default: .md .markdown",
    )

    parser.add_argument(
        "--font-family",
        default=DEFAULT_FONT_FAMILY,
        help="CSS font-family used for Persian/RTL text. Default: Vazirmatn fallback stack.",
    )
    parser.add_argument(
        "--font-file",
        type=Path,
        help="Optional local font file to embed through CSS @font-face. Overrides --font-dir.",
    )
    parser.add_argument(
        "--font-dir",
        type=Path,
        help="Directory containing Vazirmatn-*.ttf files. Default: ./fonts when it exists.",
    )
    parser.add_argument(
        "--css",
        type=Path,
        help="Optional custom CSS file appended after the built-in RTL CSS.",
    )

    parser.add_argument(
        "--page-format",
        default="A4",
        help="PDF page format supported by Chromium, for example A4, Letter, Legal. Default: A4.",
    )
    parser.add_argument(
        "--margin",
        default="15mm",
        help="PDF margin, for example 10mm, 0.5in, 24px. Default: 15mm.",
    )
    parser.add_argument(
        "--landscape",
        action="store_true",
        help="Generate landscape PDFs.",
    )
    parser.add_argument(
        "--strip-emojis",
        action="store_true",
        help="Remove all emojis from converted PDF and DOCX documents.",
    )

    parser.add_argument(
        "--mermaid-js",
        type=Path,
        help="Local mermaid.min.js path. Default: ./vendor/mermaid.min.js.",
    )
    parser.add_argument(
        "--mermaid-url",
        help=(
            "Optional Mermaid JS URL. This is not used by default because the tool is offline-first."
        ),
    )
    parser.add_argument(
        "--mermaid-theme",
        default="default",
        choices=["default", "base", "dark", "forest", "neutral", "null"],
        help="Mermaid theme. Default: default.",
    )
    parser.add_argument(
        "--mermaid-timeout",
        type=int,
        default=30_000,
        help="Timeout for Mermaid rendering in milliseconds. Default: 30000.",
    )
    parser.add_argument(
        "--ignore-mermaid-errors",
        action="store_true",
        help="Continue PDF generation if Mermaid fails. The broken diagram text may remain visible.",
    )

    parser.add_argument(
        "--browsers-path",
        type=Path,
        help=(
            "Playwright browser directory. Default: ./browsers when it exists. "
            "The value is assigned to PLAYWRIGHT_BROWSERS_PATH for this process."
        ),
    )
    parser.add_argument(
        "--keep-html",
        action="store_true",
        help="Keep intermediate HTML files next to generated PDFs.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop batch conversion after the first failed file.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print each conversion job and resolved offline asset paths.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Launch the graphical user interface instead of converting.",
    )
    parser.add_argument(
        "--wrap-rtl",
        action="store_true",
        help=(
            "Transform Markdown files to wrap Persian/Arabic text blocks with "
            "<div dir='rtl'>...</div> for correct browser rendering. "
            "Code blocks and existing RTL wrappers are left untouched. "
            "When used alone, the transform is applied in-place (or to --output) "
            "without converting to PDF/DOCX."
        ),
    )
    parser.add_argument(
        "--wrap-rtl-suffix",
        default=".rtl",
        help=(
            "Suffix added before the file extension when writing the wrapped file in-place. "
            "Default: '.rtl' (so file.md -> file.rtl.md). Use empty string to overwrite."
        ),
    )
    parser.add_argument(
        "-w",
        "--watch",
        action="store_true",
        help="Watch input files or directory for changes and re-convert automatically.",
    )
    parser.add_argument(
        "--register-associations",
        action="store_true",
        help=(
            "Register MdPersia as a per-user handler for .md/.markdown files on Windows "
            "(double-click, 'Open with' and a right-click verb). HKCU only, no elevation. "
            "Reversible with --unregister-associations."
        ),
    )
    parser.add_argument(
        "--unregister-associations",
        action="store_true",
        help="Remove only the MdPersia association keys created by --register-associations.",
    )
    parser.add_argument(
        "--association-status",
        action="store_true",
        help="Report whether MdPersia is registered for Markdown files for the current user.",
    )
    parser.add_argument(
        "--viewer-exe",
        default=None,
        help=(
            "Executable that Windows should launch for an associated file. "
            "Defaults to the built desktop exe, then to the current Python interpreter."
        ),
    )

    return parser


def validate_file_option(path: Path | None, label: str) -> Path | None:
    from .converter import ConversionError

    if path is None:
        return None

    resolved = path.resolve()
    if not resolved.exists():
        raise ConversionError(f"{label} does not exist: {resolved}")
    if not resolved.is_file():
        raise ConversionError(f"{label} must be a file: {resolved}")
    return resolved


def validate_dir_option(path: Path | None, label: str) -> Path | None:
    from .converter import ConversionError

    if path is None:
        return None

    resolved = path.resolve()
    if not resolved.exists():
        raise ConversionError(f"{label} does not exist: {resolved}")
    if not resolved.is_dir():
        raise ConversionError(f"{label} must be a directory: {resolved}")
    return resolved


def resolve_mermaid_source(args: argparse.Namespace, project_root: Path) -> str:
    from .converter import ConversionError

    if args.mermaid_url:
        return args.mermaid_url

    if args.mermaid_js:
        mermaid_path = resolve_user_path(args.mermaid_js, project_root)
    else:
        mermaid_path = default_mermaid_path(project_root)

    if not mermaid_path.is_file():
        raise ConversionError(
            "Mermaid JS file was not found.\n"
            f"Expected offline default: {mermaid_path}\n"
            "Put mermaid.min.js in vendor/mermaid.min.js, or pass --mermaid-js PATH."
        )

    return str(mermaid_path)


def resolve_font_settings(args: argparse.Namespace, project_root: Path) -> tuple[Path | None, Path | None]:
    if args.font_file:
        return validate_file_option(resolve_user_path(args.font_file, project_root), "--font-file"), None

    if args.font_dir:
        return None, validate_dir_option(resolve_user_path(args.font_dir, project_root), "--font-dir")

    fonts_dir = default_fonts_path(project_root)
    if fonts_dir.is_dir():
        return None, fonts_dir

    return None, None


def resolve_browsers_setting(args: argparse.Namespace, project_root: Path) -> Path | None:
    if args.browsers_path:
        browsers_path = validate_dir_option(resolve_user_path(args.browsers_path, project_root), "--browsers-path")
        return set_playwright_browsers_path(browsers_path, force=True)

    browsers_path = default_browsers_path(project_root)
    if browsers_path.is_dir():
        return set_playwright_browsers_path(browsers_path, force=False)

    return None


def _run_wrap_rtl(args: argparse.Namespace) -> int:
    """Transform Markdown files by wrapping Persian text in <div dir='rtl'>."""
    from .html_builder import read_text_safely
    from .input_files import normalize_extensions
    from .rtl_wrapper import WrapOptions, wrap_rtl_in_markdown

    input_path = args.input.resolve()
    if not input_path.exists():
        print(f"Error: input does not exist: {input_path}", file=sys.stderr)
        return 1

    extensions = normalize_extensions(args.extensions)

    if input_path.is_file():
        if input_path.suffix.lower() not in extensions:
            print(
                f"Error: input is not a Markdown file: {input_path}", file=sys.stderr
            )
            return 1
        sources = [input_path]
        input_root = None
    elif input_path.is_dir():
        from .input_files import discover_markdown_files
        sources = discover_markdown_files(input_path, recursive=args.recursive, extensions=extensions)
        input_root = input_path
    else:
        print(f"Error: invalid input: {input_path}", file=sys.stderr)
        return 1

    if not sources:
        print("No Markdown files found.", file=sys.stderr)
        return 2

    output = args.output.resolve() if args.output else None
    suffix = args.wrap_rtl_suffix

    options = WrapOptions(enabled=True)
    successes = 0
    failures = 0

    for source in sources:
        try:
            text = read_text_safely(source)
            transformed = wrap_rtl_in_markdown(text, options)
            destination = _resolve_wrap_rtl_output(source, output, input_root, suffix)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(transformed, encoding="utf-8")
            print(f"OK  {source} -> {destination}")
            successes += 1
        except Exception as exc:  # noqa: BLE001
            print(f"ERR {source}", file=sys.stderr)
            print(f"    {exc}", file=sys.stderr)
            failures += 1
            if args.fail_fast:
                break

    print(f"Done: {successes} succeeded, {failures} failed.")

    if args.watch:
        print(f"\n[fa-md-pdf] Watching for changes in {input_path} (Press Ctrl+C to stop)...")
        import time

        def get_wrap_mtimes() -> dict[Path, float]:
            mtimes: dict[Path, float] = {}
            for src in sources:
                if src.is_file():
                    try:
                        mtimes[src] = src.stat().st_mtime
                    except OSError:
                        pass
            return mtimes

        last_mtimes = get_wrap_mtimes()
        try:
            while True:
                time.sleep(1.0)
                current_mtimes = get_wrap_mtimes()
                changed = [
                    s for s, mt in current_mtimes.items()
                    if s not in last_mtimes or mt > last_mtimes[s]
                ]
                if changed:
                    print(f"\n[fa-md-pdf] Detected changes in {len(changed)} file(s). Re-transforming...")
                    for s in changed:
                        try:
                            txt = read_text_safely(s)
                            tf = wrap_rtl_in_markdown(txt, options)
                            dest = _resolve_wrap_rtl_output(s, output, input_root, suffix)
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            dest.write_text(tf, encoding="utf-8")
                            print(f"OK  {s} -> {dest}")
                        except Exception as ex:  # noqa: BLE001
                            print(f"ERR {s}: {ex}", file=sys.stderr)
                    last_mtimes = get_wrap_mtimes()
                    print('[fa-md-pdf] Waiting for changes.')
        except KeyboardInterrupt:
            print("\n[fa-md-pdf] Watch stopped.")

    return 1 if failures else 0


def _normalize_rtl_suffix(suffix: str, default_ext: str) -> str:
    """Normalize suffix so that .rtl or .rtl.md results in a single clean extension."""
    if not suffix:
        return ""
    clean = suffix.strip()
    if clean.endswith(".markdown"):
        clean = clean[:-9]
    elif clean.endswith(".md"):
        clean = clean[:-3]
    clean = clean.strip(".")
    return f".{clean}" if clean else ""


def _resolve_wrap_rtl_output(
    source: Path, output: Path | None, input_root: Path | None, suffix: str
) -> Path:
    """Compute output path for wrap-rtl transform with clean suffix handling."""
    from .input_files import output_for_file

    clean_suffix = _normalize_rtl_suffix(suffix, source.suffix)
    target_name = (
        f"{source.stem}{clean_suffix}{source.suffix}" if clean_suffix else source.name
    )
    return output_for_file(source, input_root, output, target_name=target_name)


def _run_associations(args) -> int:
    """Apply the per-user Markdown file association requests."""
    from . import associations

    if args.unregister_associations:
        try:
            removed = associations.unregister()
        except OSError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        if removed:
            print(f"Removed {len(removed)} MdPersia registry keys:")
            for loc in removed:
                print(f"  - {loc}")
        else:
            print("No MdPersia association keys were present.")
        return 0

    if args.association_status:
        ok, command, reason = associations.association_state()
        if not command:
            print("MdPersia Markdown association for the current user: not registered")
            return 0
        print(f"MdPersia Markdown association command:\n  {command}")
        if ok:
            print("Status: working")
            return 0
        print(f"Status: broken - {reason}")
        print("Repair with: mdpersia --register-associations")
        return 1

    try:
        exe = associations.resolve_viewer_exe(find_project_root(args.input), args.viewer_exe)
        written = associations.register(exe)
    except OSError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Registered MdPersia for {' and '.join(associations.EXTENSIONS)} -> {exe}")
    print(f"Wrote {len(written)} per-user values (HKCU, no elevation).")
    print("Undo with: mdpersia --unregister-associations")
    return 0


_gui_port = os.environ.get("MDPERSIA_GUI_PORT", "1420")
GUI_PORT = int(_gui_port) if _gui_port.isdigit() and 0 < int(_gui_port) < 65536 else 1420
GUI_DEV_URL = f"http://localhost:{GUI_PORT}"


def _dev_server_running(url: str = GUI_DEV_URL) -> bool:
    """Whether a `--gui` dev server already answers on the fixed port."""
    import json
    import urllib.request

    try:
        with urllib.request.urlopen(url + "/api/health", timeout=0.6) as resp:
            return json.load(resp).get("app") == "MdPersia"
    except Exception:
        return False


def _handoff_gui_file(path: str, url: str = GUI_DEV_URL) -> bool:
    """Deliver another file to the existing app without opening another window."""
    import json
    import urllib.request

    request = urllib.request.Request(
        url + "/api/open-file", data=json.dumps({"path": path}).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=1) as response:
            return bool(json.load(response).get("delivered"))
    except Exception:
        return False


def _focus_gui_window() -> None:
    if sys.platform != "win32":
        return
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.ShowWindowAsync.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]

    @callback_type
    def visit(hwnd, _):
        title = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, title, len(title))
        if user32.IsWindowVisible(hwnd) and title.value.startswith("MdPersia - تبدیل اسناد"):
            user32.ShowWindowAsync(hwnd, 9)  # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
            return False
        return True

    user32.EnumWindows(visit, 0)


def _frontend_build_current(tauri_dir: Path) -> bool:
    """Use the built version of this same UI when it matches the current sources."""
    stamp = tauri_dir / "dist" / ".mdpersia-build"
    if not (tauri_dir / "dist" / "index.html").is_file() or not stamp.is_file() or not (tauri_dir / "dist" / "desktop-server.mjs").is_file():
        return False
    built_at = stamp.stat().st_mtime_ns
    sources = [tauri_dir / name for name in ("index.html", "package.json", "package-lock.json", "vite.config.ts", "desktopBridge.ts", "desktop-server.ts")]
    sources.extend(p for p in (tauri_dir / "src").rglob("*")
                   if p.is_file() and ".test." not in p.name and "__tests__" not in p.parts)
    return all(not p.exists() or p.stat().st_mtime_ns <= built_at for p in sources)


def _open_gui_window(url: str) -> None:
    """Edge's app mode has no address bar, so the viewer reads as a desktop window."""
    import subprocess
    import webbrowser

    if sys.platform == "win32":
        for root in (os.environ.get("PROGRAMFILES(X86)"), os.environ.get("PROGRAMFILES")):
            edge = Path(root or "") / "Microsoft" / "Edge" / "Application" / "msedge.exe"
            if edge.is_file():
                try:
                    command = [str(edge), f"--app={url}", "--window-size=1280,800"]
                    # Opt-in isolated profile for reproducible launch diagnostics.
                    profile = os.environ.get("MDPERSIA_BROWSER_PROFILE")
                    if profile:
                        command += [f"--user-data-dir={profile}", "--no-first-run", "--no-default-browser-check", "--disable-background-networking"]
                        debug = os.environ.get("MDPERSIA_BROWSER_DEBUG_PORT", "")
                        if debug.isdigit() and 1024 <= int(debug) <= 65535:
                            command.append(f"--remote-debugging-port={debug}")
                    subprocess.Popen(command)
                    return
                except OSError:
                    continue
    webbrowser.open(url)


@contextmanager
def _gui_launch_lock():
    """Serialize cold Explorer launches so rapid double-clicks share one server/window."""
    if sys.platform != "win32":
        yield
        return
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.windll.kernel32
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.CreateMutexW.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.ReleaseMutex.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateMutexW(None, False, f"Local\\MdPersia.Desktop.Startup.{GUI_PORT}")
    if not handle:
        raise OSError("Could not acquire the MdPersia startup lock")
    acquired = kernel.WaitForSingleObject(handle, 15000) in (0, 0x80)
    try:
        if not acquired:
            raise OSError("MdPersia is still starting. Try opening the file again.")
        yield
    finally:
        if acquired:
            kernel.ReleaseMutex(handle)
        kernel.CloseHandle(handle)


def _wait_gui_window(timeout: float = 8.0) -> bool:
    import json
    import time
    import urllib.request

    deadline = time.monotonic() + timeout
    while True:
        try:
            with urllib.request.urlopen(GUI_DEV_URL + "/api/health", timeout=0.2) as response:
                if json.load(response).get("windows", 0):
                    return True
        except Exception:
            pass
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.05)


def _run_gui(args: argparse.Namespace) -> int:
    import subprocess
    import time

    project_root = find_project_root(args.input if args.input else None)
    tauri_dir = project_root / "desktop-tauri"
    if not tauri_dir.is_dir():
        pkg_root = Path(__file__).resolve().parent.parent.parent
        if (pkg_root / "desktop-tauri").is_dir():
            project_root = pkg_root
            tauri_dir = pkg_root / "desktop-tauri"
    release_exe = (
        tauri_dir
        / "src-tauri"
        / "target"
        / "release"
        / "MdPersia.exe"
    )
    if release_exe.is_file():
        cmd = [str(release_exe)]
        if args.input:
            cmd.append(str(Path(args.input).resolve()))
        subprocess.Popen(cmd)
        return 0

    if tauri_dir.is_dir():
        from urllib.parse import quote

        initial = str(Path(args.input).resolve()) if args.input else None
        gui_url = f"{GUI_DEV_URL}/?file={quote(initial)}" if initial else GUI_DEV_URL

        if _dev_server_running():
            # A second launch must not stack another heavy dev server; the running
            # window takes the file from the URL and hands it to its open tab.
            if initial and _handoff_gui_file(initial):
                _focus_gui_window()
                return 0
            print("[fa-md-pdf] Desktop already running; opening the document there.")
            _open_gui_window(gui_url)
            _wait_gui_window()
            return 0

        print("[fa-md-pdf] Launching MdPersia desktop...")
        import shutil

        node = shutil.which("node")
        vite_cli = tauri_dir / "node_modules" / "vite" / "bin" / "vite.js"
        if not node or not vite_cli.is_file():
            print("Error: Node.js or the desktop dependencies are missing. Run npm install in desktop-tauri.", file=sys.stderr)
            return 1

        env = os.environ.copy()
        # The interpreter that launched the CLI may be one without the conversion
        # dependencies, so an explicitly chosen interpreter has to win.
        env.setdefault("PYTHON_EXECUTABLE", sys.executable)
        env.pop("MDPERSIA_INITIAL_FILE", None)

        built = _frontend_build_current(tauri_dir)
        cmd = [node, str(tauri_dir / "dist" / "desktop-server.mjs")] if built else [node, str(vite_cli)]
        cmd += ["--port", str(GUI_PORT), "--host", "127.0.0.1", "--strictPort"]
        proc = subprocess.Popen(
            cmd, cwd=str(tauri_dir), env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        for _ in range(120):
            if proc.poll() is not None:
                print("Error: MdPersia desktop server stopped during startup.", file=sys.stderr)
                return 1
            if _dev_server_running():
                _open_gui_window(gui_url)
                _wait_gui_window()
                return 0
            time.sleep(0.1)
        proc.terminate()
        print("Error: MdPersia desktop server did not become ready.", file=sys.stderr)
        return 1

    print("Error: Graphical interface is provided by desktop-tauri.", file=sys.stderr)
    return 1



def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.register_associations or args.unregister_associations or args.association_status:
        return _run_associations(args)

    if args.gui:
        with _gui_launch_lock():
            return _run_gui(args)

    if args.input is None:
        parser.error("the following arguments are required: input (or use --gui)")

    if args.wrap_rtl:
        return _run_wrap_rtl(args)

    from .converter import (
        ConversionError, ConvertOptions, build_jobs, convert_jobs, normalize_extensions,
    )

    try:
        project_root = find_project_root(args.input)

        custom_css = validate_file_option(
            resolve_user_path(args.css, project_root) if args.css else None,
            "--css",
        )
        font_file, font_dir = resolve_font_settings(args, project_root)
        mermaid_source = resolve_mermaid_source(args, project_root)
        browsers_path = resolve_browsers_setting(args, project_root)
        extensions = normalize_extensions(args.extensions)

        if args.verbose:
            print(f"[fa-md-pdf] project root: {project_root}")
            print(f"[fa-md-pdf] format:       {args.format}")
            print(f"[fa-md-pdf] mermaid js:   {mermaid_source}")
            print(f"[fa-md-pdf] font file:    {font_file or '-'}")
            print(f"[fa-md-pdf] font dir:     {font_dir or '-'}")
            print(f"[fa-md-pdf] browsers:     {browsers_path or 'Playwright default'}")

        jobs = build_jobs(
            input_path=args.input,
            output=args.output,
            recursive=args.recursive,
            extensions=extensions,
            keep_html=args.keep_html,
            output_format=args.format,
        )

        if not jobs:
            print("No Markdown files found.", file=sys.stderr)
            return 2

        options = ConvertOptions(
            font_family=args.font_family,
            font_file=font_file,
            font_dir=font_dir,
            custom_css=custom_css,
            mermaid_source=mermaid_source,
            mermaid_theme=args.mermaid_theme,
            mermaid_timeout_ms=args.mermaid_timeout,
            page_format=args.page_format,
            margin=args.margin,
            landscape=args.landscape,
            keep_html=args.keep_html,
            ignore_mermaid_errors=args.ignore_mermaid_errors,
            verbose=args.verbose,
            output_format=args.format,
            docx_font_size_pt=args.docx_font_size,
            docx_image_scale=args.docx_image_scale,
            docx_image_min_width=args.docx_image_min_width,
            docx_image_max_width=args.docx_image_max_width,
            strip_emojis=args.strip_emojis,
        )

        results = convert_jobs(jobs, options=options, fail_fast=args.fail_fast)
        successes = [result for result in results if result.ok]
        failures = [result for result in results if not result.ok]

        for result in successes:
            print(f"OK  {result.job.source} -> {result.job.output}")

        for result in failures:
            print(f"ERR {result.job.source}", file=sys.stderr)
            print(f"    {result.error}", file=sys.stderr)

        print(f"Done: {len(successes)} succeeded, {len(failures)} failed.")

        if args.watch:
            print(f"\n[fa-md-pdf] Watching for changes in {args.input} (Press Ctrl+C to stop)...")
            import time

            def get_mtimes() -> dict[Path, float]:
                mtimes = {}
                for job in jobs:
                    if job.source.is_file():
                        try:
                            mtimes[job.source] = job.source.stat().st_mtime
                        except OSError:
                            pass
                return mtimes

            last_mtimes = get_mtimes()
            try:
                while True:
                    time.sleep(1.0)
                    current_mtimes = get_mtimes()
                    changed = [
                        src for src, mtime in current_mtimes.items()
                        if src not in last_mtimes or mtime > last_mtimes[src]
                    ]
                    if changed:
                        print(f"\n[fa-md-pdf] Detected changes in {len(changed)} file(s). Re-converting...")
                        changed_jobs = [j for j in jobs if j.source in set(changed)]
                        changed_results = convert_jobs(changed_jobs, options=options, fail_fast=False)
                        for result in changed_results:
                            if result.ok:
                                print(f"OK  {result.job.source} -> {result.job.output}")
                            else:
                                print(f"ERR {result.job.source}", file=sys.stderr)
                                print(f"    {result.error}", file=sys.stderr)
                        last_mtimes = current_mtimes
                        print('[fa-md-pdf] Waiting for changes.')
            except KeyboardInterrupt:
                print("\n[fa-md-pdf] Stopped watching.")
                return 0

        return 1 if failures else 0

    except ConversionError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
