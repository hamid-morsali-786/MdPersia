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
from fa_md_pdf.cli import main

__all__ = [
    "__version__",
    "convert_jobs",
    "build_jobs",
    "ConvertOptions",
    "ConversionError",
    "main",
]
