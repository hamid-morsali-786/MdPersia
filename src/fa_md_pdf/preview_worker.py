"""Keep the existing HTML renderer warm for desktop previews over UTF-8 stdio.

The worker has no window, HTTP server or alternate renderer. Each line is one
request to html_builder, so normal documents reuse imports between opens.
"""
from __future__ import annotations

import json
import secrets
import sys
from pathlib import Path
from typing import TextIO

from .html_builder import HtmlBuildOptions, build_html, read_text_safely
from .document_io import document_operation, MAX_DOCUMENT_BYTES


def serve(root: Path, requests: TextIO, responses: TextIO) -> None:
    fonts = root / "fonts"
    mermaid = root / "vendor" / "mermaid.min.js"
    for line in requests:
        request = None
        try:
            request = json.loads(line)
            if request.get("operation") in {"read", "save"}:
                result = {"id": request["id"], "document": document_operation(request)}
                responses.write(json.dumps(result, ensure_ascii=False) + "\n")
                responses.flush()
                continue
            source = Path(request["path"]).resolve(strict=True)
            if source.suffix.lower() not in {".md", ".markdown"} or not source.is_file():
                raise ValueError("یک فایل Markdown انتخاب کنید.")
            if source.stat().st_size > 16 * 1024 * 1024:
                raise ValueError("حجم فایل برای پیش‌نمایش از ۱۶ مگابایت بیشتر است.")
            text = request.get("text", None)
            if text is not None and (not isinstance(text, str) or len(text.encode("utf-8")) > MAX_DOCUMENT_BYTES):
                raise ValueError("متن پیش‌نمایش معتبر نیست یا بیش از ۱۶ مگابایت است.")
            document = build_html(text if text is not None else read_text_safely(source), HtmlBuildOptions(
                source_path=source, font_dir=fonts if fonts.is_dir() else None,
                mermaid_source=mermaid.as_uri() if mermaid.is_file() else "",
                preview_nonce=secrets.token_urlsafe(24),
            ))
            result = {"id": request["id"], "html": document.html}
        except Exception as error:
            result = {"id": request.get("id") if isinstance(request, dict) else None,
                      "error": str(error), "code": getattr(error, "code", "IO")}
        responses.write(json.dumps(result, ensure_ascii=False) + "\n")
        responses.flush()


if __name__ == "__main__":
    serve(Path(sys.argv[1]).resolve(), sys.stdin, sys.stdout)
