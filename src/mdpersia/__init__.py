"""
MdPersia: The modern, offline-first Persian and RTL Markdown to Word (DOCX) & PDF converter.
"""
from fa_md_pdf import __version__


def __getattr__(name: str):
    """Keep public exports compatible without loading conversion tools to open the GUI."""
    if name in {"ConversionError", "ConvertOptions", "build_jobs", "convert_jobs"}:
        from fa_md_pdf import converter

        value = getattr(converter, name)
    elif name in {"WrapOptions", "wrap_rtl_in_file", "wrap_rtl_in_markdown"}:
        from fa_md_pdf import rtl_wrapper

        value = getattr(rtl_wrapper, name)
    elif name == "main":
        from fa_md_pdf.cli import main

        value = main
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    globals()[name] = value
    return value

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

