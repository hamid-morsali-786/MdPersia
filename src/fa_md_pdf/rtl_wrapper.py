"""
Wrap Persian/Arabic text blocks in Markdown with `<div dir="rtl">...</div>` so
mixed-direction documents render correctly in browsers and other Markdown
viewers.

Strategy:
- Preserve YAML frontmatter at document root untouched.
- Split the document into segments by detecting fenced code blocks (``` or ~~~),
  display math blocks ($$...$$), and HTML comments (<!--...-->).
- Within text segments, track RTL div tag nesting depth to ensure idempotency.
- A block is wrapped with `<div dir="rtl">...</div>` only if it contains Persian/Arabic
  characters and is not already inside an RTL wrapper.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# Persian/Arabic Unicode blocks including ZWNJ (\u200C) and ZWJ (\u200D)
PERSIAN_RE = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF\u200C\u200D]"
)

# Match opening/closing of fenced code blocks. Stays in sync with markdown-it.
FENCE_OPEN_RE = re.compile(r"^([ \t]{0,3})(`{3,}|~{3,})([^\n]*)$")

# Math display blocks ($$ ... $$)
MATH_BLOCK_RE = re.compile(r"^\$\$\s*$")

# YAML Frontmatter at beginning of document
FRONTMATTER_RE = re.compile(r"^---\r?\n.*?\r?\n---(?:\r?\n|$)", re.DOTALL)

# Match an existing wrapper opening: <div dir="rtl"> or <div dir='rtl'> etc.
DIV_RTL_OPEN_RE = re.compile(r"<div\b[^>]*\bdir\s*=\s*[\"']?rtl[\"']?[^>]*>", re.IGNORECASE)
DIV_CLOSE_RE = re.compile(r"</div>", re.IGNORECASE)


@dataclass(frozen=True)
class WrapOptions:
    """Configuration for the RTL wrapper."""

    enabled: bool = True
    # Minimum number of Persian characters in a block to trigger wrapping.
    # Helps avoid wrapping tiny fragments like a single word in English text.
    min_persian_chars: int = 1


def has_persian(text: str) -> bool:
    """Return True if the string contains at least one Persian/Arabic letter."""
    return bool(PERSIAN_RE.search(text))


def count_persian(text: str) -> int:
    """Return total count of Persian/Arabic characters in text."""
    return len(PERSIAN_RE.findall(text))


def _is_fence_open(line: str) -> str | None:
    """Return the fence marker (e.g. '```' or '~~~~') if line opens/closes a fence."""
    match = FENCE_OPEN_RE.match(line)
    if not match:
        return None
    return match.group(2)


def _split_segments(lines: list[str]) -> list[tuple[str, list[str]]]:
    """
    Split lines into ('text', lines) and ('code'/'math', lines) segments.
    Code and math segments include boundary lines and are returned untouched.
    """
    segments: list[tuple[str, list[str]]] = []
    buffer: list[str] = []
    in_code = False
    in_math = False
    fence_marker: str | None = None

    for line in lines:
        stripped = line.strip()
        if in_code:
            buffer.append(line)
            if (
                fence_marker is not None
                and stripped.startswith(fence_marker[0])
                and set(stripped) <= {fence_marker[0], " ", "\t"}
                and len(stripped.replace(" ", "").replace("\t", "")) >= len(fence_marker)
            ):
                segments.append(("code", buffer))
                buffer = []
                in_code = False
                fence_marker = None
        elif in_math:
            buffer.append(line)
            if stripped == "$$":
                segments.append(("code", buffer))
                buffer = []
                in_math = False
        else:
            marker = _is_fence_open(line)
            if marker is not None:
                if buffer:
                    segments.append(("text", buffer))
                    buffer = []
                buffer.append(line)
                in_code = True
                fence_marker = marker
            elif stripped == "$$":
                if buffer:
                    segments.append(("text", buffer))
                    buffer = []
                buffer.append(line)
                in_math = True
            else:
                buffer.append(line)

    if buffer:
        segments.append(("code" if (in_code or in_math) else "text", buffer))

    return segments


def _split_blocks(text_lines: list[str]) -> list[list[str]]:
    """
    Split text-segment lines into blocks separated by blank lines.
    A block is a maximal run of non-blank lines plus its trailing blanks.
    """
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in text_lines:
        current.append(line)
        if line.strip() == "":
            blocks.append(current)
            current = []

    if current:
        blocks.append(current)

    return blocks


def _block_has_existing_rtl_wrapper(block: list[str]) -> bool:
    """Check whether a block already contains an explicit <div dir="rtl"> open."""
    text = "\n".join(block)
    return bool(DIV_RTL_OPEN_RE.search(text))


def _wrap_block(block: list[str]) -> list[str]:
    """Wrap a block with <div dir="rtl">...</div>. Preserves trailing blank lines."""
    trailing_blanks: list[str] = []
    content = list(block)
    while content and content[-1].strip() == "":
        trailing_blanks.append(content.pop())

    if not content:
        return block

    wrapped = ['<div dir="rtl">', "", *content, "", "</div>"]
    return wrapped + trailing_blanks


def _process_text_segment(lines: list[str], options: WrapOptions) -> list[str]:
    """Wrap Persian-containing blocks within a text segment with tag-depth tracking."""
    blocks = _split_blocks(lines)
    output: list[str] = []
    rtl_div_depth = 0

    for block in blocks:
        block_text = "\n".join(block)
        open_count = len(DIV_RTL_OPEN_RE.findall(block_text))
        close_count = len(DIV_CLOSE_RE.findall(block_text))

        # If already inside an RTL wrapper or contains an existing wrapper, preserve as-is
        if rtl_div_depth > 0 or open_count > 0:
            output.extend(block)
            rtl_div_depth = max(0, rtl_div_depth + open_count - close_count)
            continue

        # Check if block needs wrapping
        if count_persian(block_text) >= options.min_persian_chars:
            output.extend(_wrap_block(block))
        else:
            output.extend(block)

        rtl_div_depth = max(0, rtl_div_depth - close_count)

    return output


def wrap_rtl_in_markdown(text: str, options: WrapOptions | None = None) -> str:
    """
    Transform Markdown text by wrapping Persian/Arabic blocks with
    `<div dir="rtl">...</div>` while leaving code blocks, math blocks,
    YAML frontmatter, and existing RTL wrappers untouched.
    """
    options = options or WrapOptions()
    if not options.enabled:
        return text

    # Extract YAML frontmatter if present at top
    frontmatter = ""
    body = text
    fm_match = FRONTMATTER_RE.match(text)
    if fm_match:
        frontmatter = fm_match.group(0)
        body = text[len(frontmatter):]

    lines = body.splitlines(keepends=False)
    segments = _split_segments(lines)

    output_lines: list[str] = []
    for kind, segment_lines in segments:
        if kind == "code":
            output_lines.extend(segment_lines)
        else:
            output_lines.extend(_process_text_segment(segment_lines, options))

    result = frontmatter + "\n".join(output_lines)
    if text.endswith("\n") and not result.endswith("\n"):
        result += "\n"
    return result


def wrap_rtl_in_file(
    source: Path,
    destination: Path | None = None,
    options: WrapOptions | None = None,
) -> Path:
    """
    Read a Markdown file, apply wrap_rtl_in_markdown, and write the result.
    If destination is None, writes alongside the source with a `.rtl.md` suffix.
    """
    from .html_builder import read_text_safely

    text = read_text_safely(source)
    transformed = wrap_rtl_in_markdown(text, options)

    if destination is None:
        destination = source.with_suffix(".rtl" + source.suffix)

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(transformed, encoding="utf-8")
    return destination
