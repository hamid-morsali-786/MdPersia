"""Resolve local document image paths without importing an export renderer."""
from pathlib import Path
from urllib.parse import unquote, urlsplit
from urllib.request import url2pathname


def resolve_image_file(src: str, source_path: Path) -> Path | None:
    """Resolve relative or absolute local image file path."""
    if not src or src.lower().startswith(("http://", "https://", "data:")):
        return None
    if src.lower().startswith("file:"):
        url = urlsplit(src)
        src = url2pathname(("//" + url.netloc if url.netloc else "") + url.path)
    else:
        src = unquote(src)
    candidate = (source_path.parent / src).resolve()
    if candidate.is_file():
        return candidate
    alt_cand = Path(src).resolve()
    if alt_cand.is_file():
        return alt_cand
    if candidate.suffix.lower() == ".svg" and candidate.with_suffix(".png").is_file():
        return candidate.with_suffix(".png")
    return None
