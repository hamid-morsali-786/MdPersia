"""Small packaged entrypoint for the existing Markdown preview/editor worker.

PDF/Word run through the optional full engine. Reading never imports Playwright
or starts a conversion browser.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from .desktop_engine import asset_root


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if stream is not None:
            stream.reconfigure(encoding='utf-8', line_buffering=True)
    parser = argparse.ArgumentParser(prog='mdpersia-reader')
    parser.add_argument('--assets-dir')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--worker', action='store_true')
    mode.add_argument('--doctor', action='store_true')
    mode.add_argument('--convert', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    try:
        root = asset_root(args.assets_dir)
        os.chdir(root)
        if args.doctor:
            from . import __version__
            print(json.dumps({'version': __version__, 'kind': 'reader',
                'frozen': bool(getattr(sys, 'frozen', False)), 'assets': str(root),
                'fontPresent': True, 'mermaidPresent': True}, ensure_ascii=False))
            return 0
        if args.worker:
            from .preview_worker import serve
            serve(root, sys.stdin, sys.stdout)
            return 0
        if not args.convert or '--wrap-rtl' not in args.convert:
            raise RuntimeError('برای خروجی PDF یا Word، موتور تبدیل را از تنظیمات دریافت کنید.')
        from .cli import main as convert
        return convert(args.convert)
    except Exception as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
