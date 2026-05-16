from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

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


@dataclass(frozen=True)
class ConvertResult:
    job: ConvertJob
    ok: bool
    error: str | None = None


def normalize_extensions(values: Iterable[str]) -> tuple[str, ...]:
    extensions: list[str] = []
    for value in values:
        value = value.strip().lower()
        if not value:
            continue
        if not value.startswith("."):
            value = "." + value
        extensions.append(value)
    return tuple(dict.fromkeys(extensions)) or (".md", ".markdown")


def is_markdown_file(path: Path, extensions: Iterable[str]) -> bool:
    return path.is_file() and path.suffix.lower() in set(normalize_extensions(extensions))


def discover_markdown_files(input_dir: Path, recursive: bool, extensions: Iterable[str]) -> list[Path]:
    normalized = normalize_extensions(extensions)
    pattern = "**/*" if recursive else "*"
    return sorted(path for path in input_dir.glob(pattern) if is_markdown_file(path, normalized))


def output_for_file(source: Path, input_root: Path | None, output: Path | None) -> Path:
    if output is None:
        return source.with_suffix(".pdf")

    if input_root is None:
        if output.suffix.lower() == ".pdf":
            return output
        return output / source.with_suffix(".pdf").name

    relative = source.relative_to(input_root)
    return (output / relative).with_suffix(".pdf")


def build_jobs(
    input_path: Path,
    output: Path | None,
    recursive: bool = True,
    extensions: Iterable[str] = (".md", ".markdown"),
    keep_html: bool = False,
) -> list[ConvertJob]:
    input_path = input_path.resolve()
    output = output.resolve() if output else None

    if input_path.is_file():
        if not is_markdown_file(input_path, extensions):
            raise ConversionError(f"Input file is not a supported Markdown file: {input_path}")
        pdf_output = output_for_file(input_path, None, output)
        html_output = pdf_output.with_suffix(".html") if keep_html else None
        return [ConvertJob(source=input_path, output=pdf_output, html_output=html_output)]

    if input_path.is_dir():
        if output is not None and output.suffix.lower() == ".pdf":
            raise ConversionError("When input is a directory, --output must be a directory, not a PDF file.")

        files = discover_markdown_files(input_path, recursive=recursive, extensions=extensions)
        jobs: list[ConvertJob] = []
        for source in files:
            pdf_output = output_for_file(source, input_path if output else None, output)
            html_output = pdf_output.with_suffix(".html") if keep_html else None
            jobs.append(ConvertJob(source=source, output=pdf_output, html_output=html_output))
        return jobs

    raise ConversionError(f"Input path does not exist: {input_path}")


def _write_html_for_debug(job: ConvertJob, html: str) -> None:
    if not job.html_output:
        return
    job.html_output.parent.mkdir(parents=True, exist_ok=True)
    job.html_output.write_text(html, encoding="utf-8")


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
        ),
    )

    _write_html_for_debug(job, html_document.html)

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
        prefer_css_page_size=True,
        margin={
            "top": options.margin,
            "right": options.margin,
            "bottom": options.margin,
            "left": options.margin,
        },
    )


def convert_jobs(
    jobs: Iterable[ConvertJob],
    options: ConvertOptions,
    fail_fast: bool = False,
) -> list[ConvertResult]:
    jobs = list(jobs)
    if not jobs:
        return []

    results: list[ConvertResult] = []

    with tempfile.TemporaryDirectory(prefix="fa-md-pdf-") as tmp:
        temp_dir = Path(tmp)

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()

            try:
                for job in jobs:
                    if options.verbose:
                        print(f"[fa-md-pdf] {job.source} -> {job.output}")

                    try:
                        _render_job(page, job, options, temp_dir)
                        results.append(ConvertResult(job=job, ok=True))
                    except Exception as exc:  # noqa: BLE001 - CLI needs to summarize all job failures.
                        results.append(ConvertResult(job=job, ok=False, error=str(exc)))
                        if fail_fast:
                            break
                    finally:
                        page.close()
                        page = browser.new_page()
            finally:
                browser.close()

    return results
