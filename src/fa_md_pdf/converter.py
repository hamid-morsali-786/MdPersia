from __future__ import annotations

import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from collections.abc import Callable

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from .html_builder import (
    DEFAULT_MERMAID_CDN,
    HtmlBuildOptions,
    build_html,
    read_text_safely,
)


class ConversionError(RuntimeError):
    """Raised when a Markdown file cannot be converted."""


@dataclass(frozen=True)
class ConvertJob:
    source: Path
    output: Path
    html_output: Path | None = None


@dataclass(frozen=True)
class ConvertOptions:
    font_family: str = '"Vazirmatn", "Noto Naskh Arabic", "Segoe UI", Tahoma, Arial, sans-serif'
    font_file: Path | None = None
    font_dir: Path | None = None
    custom_css: Path | None = None
    mermaid_source: str = DEFAULT_MERMAID_CDN
    mermaid_theme: str = "default"
    mermaid_timeout_ms: int = 30_000
    page_format: str = "A4"
    margin: str = "15mm"
    landscape: bool = False
    keep_html: bool = False
    ignore_mermaid_errors: bool = False
    verbose: bool = False
    output_format: str = "pdf"  # "pdf" or "docx"
    docx_font_size_pt: int = 12
    docx_image_scale: int = 3       # device scale factor for Mermaid PNGs
    docx_image_min_width: float = 4.0    # minimum image width in inches
    docx_image_max_width: float = 6.5    # maximum image width in inches
    include_page_numbers: bool = True
    highlight_code: bool = True
    strip_emojis: bool = False


@dataclass(frozen=True)
class ConvertResult:
    job: ConvertJob
    ok: bool
    error: str | None = None


def normalize_extensions(values: Iterable[str]) -> tuple[str, ...]:
    exts = tuple(dict.fromkeys(f".{v.strip().lstrip('.').lower()}" for v in values if v.strip()))
    return exts or (".md", ".markdown")


def is_markdown_file(path: Path, extensions: Iterable[str]) -> bool:
    return path.is_file() and path.suffix.lower() in set(normalize_extensions(extensions))


def discover_markdown_files(input_dir: Path, recursive: bool, extensions: Iterable[str]) -> list[Path]:
    normalized = normalize_extensions(extensions)
    pattern = "**/*" if recursive else "*"
    return sorted(path for path in input_dir.glob(pattern) if is_markdown_file(path, normalized))


def output_for_file(
    source: Path,
    input_root: Path | None,
    output: Path | None,
    output_format: str = "pdf",
    target_name: str | None = None,
) -> Path:
    target_name = target_name or source.with_suffix(f".{output_format}").name
    target_suffixes = {".pdf", ".docx", ".md", ".markdown"}

    if output is None:
        return source.parent / target_name

    if input_root is None:
        if output.suffix.lower() in target_suffixes:
            return output
        return output / target_name

    relative = source.relative_to(input_root)
    return output / relative.parent / target_name


def build_jobs(
    input_path: Path,
    output: Path | None,
    recursive: bool = True,
    extensions: Iterable[str] = (".md", ".markdown"),
    keep_html: bool = False,
    output_format: str = "pdf",
) -> list[ConvertJob]:
    if output_format not in ("pdf", "docx"):
        raise ConversionError(f"Unsupported output format: {output_format}")

    input_path = input_path.resolve()
    output = output.resolve() if output else None
    target_suffix = f".{output_format}"
    target_suffixes = {".pdf", ".docx"}

    if input_path.is_file():
        if not is_markdown_file(input_path, extensions):
            raise ConversionError(f"Input file is not a supported Markdown file: {input_path}")
        out = output_for_file(input_path, None, output, output_format)
        html_output = out.with_suffix(".html") if keep_html else None
        return [ConvertJob(source=input_path, output=out, html_output=html_output)]

    if input_path.is_dir():
        if output is not None and output.suffix.lower() in target_suffixes:
            raise ConversionError(
                "When input is a directory, --output must be a directory, not a file."
            )

        files = discover_markdown_files(input_path, recursive=recursive, extensions=extensions)
        jobs: list[ConvertJob] = []
        for source in files:
            out = output_for_file(source, input_path if output else None, output, output_format)
            html_output = out.with_suffix(".html") if keep_html else None
            jobs.append(ConvertJob(source=source, output=out, html_output=html_output))
        return jobs

    raise ConversionError(f"Input path does not exist: {input_path}")


def _render_job(page, job: ConvertJob, options: ConvertOptions, temp_dir: Path) -> None:
    markdown_text = read_text_safely(job.source)
    html_document = build_html(
        markdown_text,
        HtmlBuildOptions(
            source_path=job.source,
            font_family=options.font_family,
            font_file=options.font_file,
            font_dir=options.font_dir,
            custom_css=options.custom_css,
            mermaid_source=options.mermaid_source,
            mermaid_theme=options.mermaid_theme,
            page_format=options.page_format,
            margin=options.margin,
            landscape=options.landscape,
            strip_emojis=options.strip_emojis,
        ),
    )

    if job.html_output:
        job.html_output.parent.mkdir(parents=True, exist_ok=True)
        job.html_output.write_text(html_document.html, encoding="utf-8")

    temp_html = temp_dir / f"{job.source.stem}.html"
    temp_html.write_text(html_document.html, encoding="utf-8")

    page.goto(temp_html.resolve().as_uri(), wait_until="domcontentloaded")

    try:
        page.wait_for_function(
            "() => window.__FA_MD_PDF_READY === true",
            timeout=options.mermaid_timeout_ms,
        )
    except PlaywrightTimeoutError as exc:
        raise ConversionError(
            f"Timed out while rendering Mermaid diagrams in {job.source}. "
            f"Increase --mermaid-timeout or check the Mermaid script source."
        ) from exc

    mermaid_error = page.evaluate("() => window.__FA_MD_PDF_MERMAID_ERROR || null")
    if mermaid_error and not options.ignore_mermaid_errors:
        raise ConversionError(f"Mermaid render error in {job.source}:\n{mermaid_error}")

    page.emulate_media(media="print")

    job.output.parent.mkdir(parents=True, exist_ok=True)
    page.pdf(
        path=str(job.output),
        format=options.page_format,
        landscape=options.landscape,
        print_background=True,
        prefer_css_page_size=False,
        display_header_footer=options.include_page_numbers,
        header_template="<div></div>",
        footer_template='<div style="font-size: 8pt; width: 100%; text-align: center; color: #6b7280; font-family: Vazirmatn, Tahoma, sans-serif; direction: rtl;">'
                        'صفحه <span class="pageNumber"></span> از <span class="totalPages"></span>'
                        '</div>',
        margin={
            "top": options.margin,
            "right": options.margin,
            "bottom": options.margin,
            "left": options.margin,
        },
    )


def _render_job_docx(job: ConvertJob, options: ConvertOptions) -> None:
    """Render a Markdown file to DOCX, with Mermaid diagrams as embedded PNGs."""
    from .docx_builder import DocxBuildOptions, build_docx, extract_mermaid_blocks
    from .mermaid_renderer import render_mermaid_to_png

    markdown_text = read_text_safely(job.source)

    # Extract mermaid codes first to render them as PNGs (only if any exist)
    _, mermaid_codes = extract_mermaid_blocks(markdown_text)

    mermaid_images: dict[str, Path] = {}
    if mermaid_codes:
        try:
            mermaid_images = render_mermaid_to_png(
                mermaid_codes,
                mermaid_source=options.mermaid_source,
                mermaid_theme=options.mermaid_theme,
                font_family=options.font_family,
                timeout_ms=options.mermaid_timeout_ms,
                ignore_errors=options.ignore_mermaid_errors,
                device_scale_factor=options.docx_image_scale,
            )
        except Exception as exc:  # noqa: BLE001
            if not options.ignore_mermaid_errors:
                raise ConversionError(
                    f"Failed to render Mermaid diagrams for {job.source}: {exc}"
                ) from exc

    # Pick a clean DOCX font name (single family, no CSS list)
    docx_font = _pick_docx_font_family(options.font_family)

    try:
        build_docx(
            markdown_text,
            DocxBuildOptions(
                source_path=job.source,
                font_family=docx_font,
                font_size_pt=options.docx_font_size_pt,
                rtl=True,
                mermaid_images=mermaid_images or None,
                image_scale=options.docx_image_scale,
                image_min_width_inches=options.docx_image_min_width,
                image_max_width_inches=options.docx_image_max_width,
                include_page_numbers=options.include_page_numbers,
                highlight_code=options.highlight_code,
                page_format=options.page_format,
                margin=options.margin,
                landscape=options.landscape,
                strip_emojis=options.strip_emojis,
            ),
            job.output,
        )
    finally:
        if mermaid_images:
            import shutil

            first_path = next(iter(mermaid_images.values()), None)
            if first_path and first_path.parent.is_dir():
                shutil.rmtree(first_path.parent, ignore_errors=True)


def _pick_docx_font_family(css_font_family: str) -> str:
    """Pick a single font family name from a CSS-style font-family list."""
    parts = css_font_family.split(",")
    for part in parts:
        cleaned = part.strip().strip("'").strip('"')
        if cleaned:
            return cleaned
    return "Vazirmatn"


def convert_jobs(
    jobs: Iterable[ConvertJob],
    options: ConvertOptions,
    fail_fast: bool = False,
    on_progress: "Callable[[ConvertJob, bool, str | None], None] | None" = None,
    cancel_event: "threading.Event | None" = None,
) -> list[ConvertResult]:
    jobs = list(jobs)
    if not jobs:
        return []

    results: list[ConvertResult] = []

    if options.output_format == "docx":
        # DOCX conversion doesn't need a persistent browser session
        for job in jobs:
            if cancel_event and cancel_event.is_set():
                break

            if options.verbose:
                print(f"[fa-md-pdf] {job.source} -> {job.output}")

            try:
                _render_job_docx(job, options)
                result = ConvertResult(job=job, ok=True)
                results.append(result)
                if on_progress:
                    on_progress(job, True, None)
            except Exception as exc:  # noqa: BLE001
                result = ConvertResult(job=job, ok=False, error=str(exc))
                results.append(result)
                if on_progress:
                    on_progress(job, False, str(exc))
                if fail_fast:
                    break

        return results

    # PDF conversion uses Playwright browser session
    with tempfile.TemporaryDirectory(prefix="fa-md-pdf-") as tmp:
        temp_dir = Path(tmp)

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()

            try:
                for job in jobs:
                    if cancel_event and cancel_event.is_set():
                        break

                    if options.verbose:
                        print(f"[fa-md-pdf] {job.source} -> {job.output}")

                    try:
                        _render_job(page, job, options, temp_dir)
                        result = ConvertResult(job=job, ok=True)
                        results.append(result)
                        if on_progress:
                            on_progress(job, True, None)
                    except Exception as exc:  # noqa: BLE001 - CLI needs to summarize all job failures.
                        result = ConvertResult(job=job, ok=False, error=str(exc))
                        results.append(result)
                        if on_progress:
                            on_progress(job, False, str(exc))
                        if fail_fast:
                            break
                    finally:
                        page.close()
                        page = browser.new_page()
            finally:
                browser.close()

    return results
