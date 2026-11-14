"""The supported Markdown family, shared with the desktop and native shell."""
import json
from importlib import resources

DOCUMENT_EXTENSIONS = tuple(
    "." + extension for extension in
    json.loads(resources.files("fa_md_pdf.assets").joinpath("document-formats.json").read_text("utf-8"))
)
