from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .converter import (
    ConversionError,
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
    resolve_user_path,
    set_playwright_browsers_path,
)


DEFAULT_FONT_FAMILY = '"Vazirmatn", "Noto Naskh Arabic", "Segoe UI", Tahoma, Arial, sans-serif'


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fa-md-pdf",
        description=(
            "Convert Persian/RTL Markdown files with Mermaid diagrams to PDF. "
            "Offline defaults are loaded from ./browsers, ./fonts and ./vendor/mermaid.min.js."
        ),
    )

    parser.add_argument(
        "input",
        type=Path,
        help="Markdown file or directory containing Markdown files.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output PDF path for a single file, or output directory for directory input.",
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

    return parser


def validate_file_option(path: Path | None, label: str) -> Path | None:
    if path is None:
        return None

    resolved = path.resolve()
    if not resolved.exists():
        raise ConversionError(f"{label} does not exist: {resolved}")
    if not resolved.is_file():
        raise ConversionError(f"{label} must be a file: {resolved}")
    return resolved


def validate_dir_option(path: Path | None, label: str) -> Path | None:
    if path is None:
        return None

    resolved = path.resolve()
    if not resolved.exists():
        raise ConversionError(f"{label} does not exist: {resolved}")
    if not resolved.is_dir():
        raise ConversionError(f"{label} must be a directory: {resolved}")
    return resolved


def resolve_mermaid_source(args: argparse.Namespace, project_root: Path) -> str:
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


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

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

        return 1 if failures else 0

    except ConversionError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
