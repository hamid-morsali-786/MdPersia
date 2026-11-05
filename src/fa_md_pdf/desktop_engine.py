"""Private, frozen desktop entrypoint. Uses the existing renderer and CLI over stdio.

Release builds never discover code or assets through the document's directory,
PATH, a system Python installation, or a developer checkout.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def asset_root(value: str | None = None) -> Path:
    if value:
        root = Path(value).resolve()
    elif getattr(sys, 'frozen', False):
        root = Path(sys.executable).resolve().parent.parent / 'assets'
    else:
        root = Path(__file__).resolve().parents[2]
    # Tauri resource_dir can use Windows verbatim paths. pathlib.as_uri turns
    # those into file://%3F/... URLs, which browsers cannot load. Keep the
    # installed filesystem path in its ordinary drive/UNC form for renderers.
    raw = str(root)
    if raw.startswith('\\\\?\\UNC\\'):
        root = Path('\\\\' + raw[8:])
    elif raw.startswith('\\\\?\\'):
        root = Path(raw[4:])
    root = root.resolve()
    if not (root / 'fonts' / 'Vazirmatn-Regular.ttf').is_file():
        raise RuntimeError('فونت‌های داخلی برنامه پیدا نشدند؛ نصب برنامه را تعمیر کنید.')
    if not (root / 'vendor' / 'mermaid.min.js').is_file():
        raise RuntimeError('موتور داخلی نمودار پیدا نشد؛ نصب برنامه را تعمیر کنید.')
    return root


def configure_runtime(root: Path) -> None:
    # All default conversion assets resolve from the installed resource directory.
    os.chdir(root)
    if getattr(sys, 'frozen', False):
        browsers = root.parent / 'browsers'
        if not browsers.is_dir():
            raise RuntimeError('مرورگر داخلی تبدیل پیدا نشد؛ نصب برنامه را تعمیر کنید.')
        os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(browsers)
        os.environ['MDPERSIA_BUNDLED_ENGINE'] = '1'


def doctor(root: Path) -> dict:
    from importlib.metadata import version
    from . import __version__

    browser_root = root.parent / 'browsers'
    return {
        'version': __version__, 'frozen': bool(getattr(sys, 'frozen', False)),
        'python': sys.version.split()[0], 'playwright': version('playwright'),
        'assets': str(root), 'browserRoot': str(browser_root),
        'browserPresent': any(browser_root.glob('chromium_headless_shell-*')),
        'fontPresent': (root / 'fonts' / 'Vazirmatn-Regular.ttf').is_file(),
        'mermaidPresent': (root / 'vendor' / 'mermaid.min.js').is_file(),
    }


def main(argv: list[str] | None = None) -> int:
    # Frozen CPython does not inherit all interpreter environment settings.
    # Explicitly decode Rust's UTF-8 input, including Persian paths and draft text.
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if stream is not None:
            stream.reconfigure(encoding='utf-8', line_buffering=True)
    parser = argparse.ArgumentParser(prog='mdpersia-engine')
    parser.add_argument('--assets-dir')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--worker', action='store_true')
    mode.add_argument('--doctor', action='store_true')
    mode.add_argument('--convert', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    try:
        root = asset_root(args.assets_dir)
        configure_runtime(root)
        if args.doctor:
            print(json.dumps(doctor(root), ensure_ascii=False))
            return 0
        if args.worker:
            from .preview_worker import serve
            serve(root, sys.stdin, sys.stdout)
            return 0
        from .cli import main as convert
        return convert(args.convert)
    except Exception as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
