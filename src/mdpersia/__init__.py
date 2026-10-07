"""
MdPersia: The modern, offline-first Persian and RTL Markdown to Word (DOCX) & PDF converter.
"""
from fa_md_pdf import __version__
from fa_md_pdf.converter import (
    ConversionError,
    ConvertOptions,
    build_jobs,
    convert_jobs,
)
from fa_md_pdf.rtl_wrapper import (
    WrapOptions,
    wrap_rtl_in_file,
    wrap_rtl_in_markdown,
)
from fa_md_pdf.cli import main

__all__ = [
    "__version__",
    "convert_jobs",
    "build_jobs",
    "ConvertOptions",
    "ConversionError",
    "WrapOptions",
    "wrap_rtl_in_markdown",
    "wrap_rtl_in_file",
    "main",
]

