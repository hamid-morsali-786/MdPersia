"""Convert Markdown to DOCX with Persian/RTL support and Mermaid diagram embedding."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from markdown_it import MarkdownIt
from markdown_it.token import Token

from .html_builder import (
    DEFAULT_MERMAID_CDN,
    convert_mermaid_fences_to_html,
    extract_title,
    read_text_safely,
    strip_front_matter,
)

if TYPE_CHECKING:
    from docx.document import Document as DocxDocument
    from docx.text.paragraph import Paragraph


DEFAULT_DOCX_FONT = "Vazirmatn"
DEFAULT_DOCX_FONT_FALLBACK = "Tahoma"
DEFAULT_DOCX_CODE_FONT = "Consolas"

HEADING_SIZES = {1: 22, 2: 18, 3: 15, 4: 13, 5: 12, 6: 11}


@dataclass(frozen=True)
class DocxBuildOptions:
    source_path: Path
    font_family: str = DEFAULT_DOCX_FONT
    font_size_pt: int = 12
    rtl: bool = True
    mermaid_images: dict[str, Path] | None = None  # mermaid_code -> png path
    image_scale: int = 3                  # device scale factor used for the PNGs
    image_min_width_inches: float = 4.0   # minimum image width in document
    image_max_width_inches: float = 6.5   # maximum image width in document


@dataclass(frozen=True)
class DocxBuildResult:
    title: str
    has_mermaid: bool
    mermaid_blocks: list[str]  # raw mermaid code blocks (for image rendering)


def _set_paragraph_rtl(paragraph: "Paragraph") -> None:
    """Apply right-to-left direction to a paragraph."""
    pPr = paragraph._p.get_or_add_pPr()
    bidi = pPr.find(qn("w:bidi"))
    if bidi is None:
        bidi = pPr.makeelement(qn("w:bidi"), {})
        pPr.append(bidi)


def _set_run_rtl(run) -> None:
    """Apply right-to-left text formatting to a run."""
    rPr = run._r.get_or_add_rPr()
    rtl = rPr.find(qn("w:rtl"))
    if rtl is None:
        rtl = rPr.makeelement(qn("w:rtl"), {})
        rPr.append(rtl)


def _set_run_font(run, font_name: str, complex_script_font: str | None = None) -> None:
    """Set the font for both ASCII and complex script (Arabic/Persian)."""
    run.font.name = font_name
    rPr = run._r.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = rPr.makeelement(qn("w:rFonts"), {})
        rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), font_name)
    rFonts.set(qn("w:hAnsi"), font_name)
    rFonts.set(qn("w:cs"), complex_script_font or font_name)


def _set_document_default_rtl(document: "DocxDocument", font_name: str, font_size_pt: int) -> None:
    """Configure document-wide defaults for RTL Persian."""
    style = document.styles["Normal"]
    style.font.name = font_name
    style.font.size = Pt(font_size_pt)

    # Set RTL on the Normal style paragraph properties
    style_element = style.element
    pPr = style_element.find(qn("w:pPr"))
    if pPr is None:
        pPr = style_element.makeelement(qn("w:pPr"), {})
        style_element.append(pPr)
    bidi = pPr.find(qn("w:bidi"))
    if bidi is None:
        bidi = pPr.makeelement(qn("w:bidi"), {})
        pPr.append(bidi)
    # Remove any jc - let bidi handle alignment naturally
    jc = pPr.find(qn("w:jc"))
    if jc is not None:
        pPr.remove(jc)

    # Set RTL on the Normal style run properties
    rPr = style_element.find(qn("w:rPr"))
    if rPr is None:
        rPr = style_element.makeelement(qn("w:rPr"), {})
        style_element.append(rPr)
    rtl = rPr.find(qn("w:rtl"))
    if rtl is None:
        rtl = rPr.makeelement(qn("w:rtl"), {})
        rPr.append(rtl)
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = rPr.makeelement(qn("w:rFonts"), {})
        rPr.append(rFonts)
    rFonts.set(qn("w:cs"), font_name)
    rFonts.set(qn("w:ascii"), font_name)
    rFonts.set(qn("w:hAnsi"), font_name)

    # Also set heading styles to RTL
    for heading_num in range(1, 7):
        style_name = f"Heading {heading_num}"
        try:
            h_style = document.styles[style_name]
            h_element = h_style.element
            h_pPr = h_element.find(qn("w:pPr"))
            if h_pPr is None:
                h_pPr = h_element.makeelement(qn("w:pPr"), {})
                h_element.append(h_pPr)
            h_bidi = h_pPr.find(qn("w:bidi"))
            if h_bidi is None:
                h_bidi = h_pPr.makeelement(qn("w:bidi"), {})
                h_pPr.append(h_bidi)
            # Remove jc from headings too
            h_jc = h_pPr.find(qn("w:jc"))
            if h_jc is not None:
                h_pPr.remove(h_jc)
        except KeyError:
            pass


def _add_styled_run(
    paragraph: "Paragraph",
    text: str,
    *,
    font_name: str,
    font_size_pt: int | None = None,
    bold: bool = False,
    italic: bool = False,
    code: bool = False,
    rtl: bool = True,
    color: RGBColor | None = None,
):
    """Add a run to the paragraph with styling."""
    run = paragraph.add_run(text)
    if code:
        _set_run_font(run, DEFAULT_DOCX_CODE_FONT, complex_script_font=font_name)
    else:
        _set_run_font(run, font_name)
    if font_size_pt is not None:
        run.font.size = Pt(font_size_pt)
    if bold:
        run.bold = True
    if italic:
        run.italic = True
    if color is not None:
        run.font.color.rgb = color
    if rtl and not code:
        _set_run_rtl(run)
    return run


def _render_inline_tokens(
    paragraph: "Paragraph",
    tokens: list[Token],
    options: DocxBuildOptions,
    *,
    base_size: int | None = None,
    base_bold: bool = False,
) -> None:
    """Render inline markdown tokens into runs of the paragraph."""
    bold_stack = [base_bold]
    italic_stack = [False]
    code = False

    for token in tokens:
        kind = token.type

        if kind == "text":
            text = token.content
            if not text:
                continue
            _add_styled_run(
                paragraph,
                text,
                font_name=options.font_family,
                font_size_pt=base_size,
                bold=bold_stack[-1],
                italic=italic_stack[-1],
                rtl=options.rtl,
            )

        elif kind == "softbreak":
            _add_styled_run(paragraph, " ", font_name=options.font_family, rtl=options.rtl)

        elif kind == "hardbreak":
            run = paragraph.add_run()
            run.add_break()

        elif kind == "code_inline":
            _add_styled_run(
                paragraph,
                token.content,
                font_name=options.font_family,
                font_size_pt=base_size,
                code=True,
                rtl=False,
            )

        elif kind == "strong_open":
            bold_stack.append(True)
        elif kind == "strong_close":
            if len(bold_stack) > 1:
                bold_stack.pop()

        elif kind == "em_open":
            italic_stack.append(True)
        elif kind == "em_close":
            if len(italic_stack) > 1:
                italic_stack.pop()

        elif kind == "link_open":
            href = token.attrGet("href") or ""
            run = paragraph.add_run()
            # Store href in a "link" attribute marker; we'll emit the link target as plain text after.
            # For simplicity, we just continue rendering link text; full hyperlink support is omitted.
            paragraph._link_href = href  # type: ignore[attr-defined]

        elif kind == "link_close":
            href = getattr(paragraph, "_link_href", None)
            if href:
                _add_styled_run(
                    paragraph,
                    f" ({href})",
                    font_name=options.font_family,
                    font_size_pt=base_size,
                    color=RGBColor(0x07, 0x58, 0x85),
                    rtl=False,
                )
                paragraph._link_href = None  # type: ignore[attr-defined]

        elif kind == "image":
            alt = token.content or token.attrGet("alt") or ""
            src = token.attrGet("src") or ""
            _add_styled_run(
                paragraph,
                f"[تصویر: {alt or src}]",
                font_name=options.font_family,
                font_size_pt=base_size,
                italic=True,
                color=RGBColor(0x6B, 0x72, 0x80),
                rtl=options.rtl,
            )

        elif kind == "s_open":
            # strikethrough not commonly used; ignore for now
            pass


# ─── Mermaid extraction (without HTML conversion) ──────────────────

MERMAID_FENCE_RE = re.compile(
    r"(?ms)(^|\n)(?P<fence>`{3,}|~{3,})[ \t]*mermaid[^\n]*\n(?P<code>.*?)(?:\n(?P=fence)[ \t]*(?=\n|$))"
)


def extract_mermaid_blocks(text: str) -> tuple[str, list[str]]:
    """
    Extract mermaid code blocks and replace them with placeholder fences.
    Returns (modified_text, list_of_mermaid_codes).
    """
    blocks: list[str] = []

    def repl(match: re.Match[str]) -> str:
        code = match.group("code").strip()
        idx = len(blocks)
        blocks.append(code)
        # Use a marker fence that markdown-it parses as a special code block
        return f"\n\n```__mermaid_placeholder__\n__MERMAID_PLACEHOLDER__{idx}__\n```\n\n"

    modified = MERMAID_FENCE_RE.sub(repl, text)
    return modified, blocks


def _build_renderer() -> MarkdownIt:
    renderer = MarkdownIt("default", {"html": False, "breaks": True, "typographer": True})
    renderer.enable("table")
    renderer.enable("strikethrough")
    return renderer


# ─── Block rendering ───────────────────────────────────────────────


def _add_heading(
    document: "DocxDocument",
    level: int,
    inline_token: Token,
    options: DocxBuildOptions,
) -> None:
    paragraph = document.add_paragraph()
    if options.rtl:
        _set_paragraph_rtl(paragraph)
        # Don't set jc=right; bidi handles RTL alignment in Word

    size = HEADING_SIZES.get(level, 12)
    paragraph.paragraph_format.space_before = Pt(12)
    paragraph.paragraph_format.space_after = Pt(6)

    _render_inline_tokens(
        paragraph,
        inline_token.children or [],
        options,
        base_size=size,
        base_bold=True,
    )


def _add_paragraph_block(
    document: "DocxDocument",
    inline_token: Token,
    options: DocxBuildOptions,
) -> None:
    paragraph = document.add_paragraph()
    if options.rtl:
        _set_paragraph_rtl(paragraph)
        # Don't set jc=right; bidi handles RTL alignment in Word

    _render_inline_tokens(
        paragraph,
        inline_token.children or [],
        options,
        base_size=options.font_size_pt,
    )


def _add_code_block(
    document: "DocxDocument",
    code: str,
    options: DocxBuildOptions,
) -> None:
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    paragraph.paragraph_format.left_indent = Inches(0.2)
    paragraph.paragraph_format.right_indent = Inches(0.2)

    # Add shading via XML
    pPr = paragraph._p.get_or_add_pPr()
    shd = pPr.makeelement(
        qn("w:shd"),
        {qn("w:val"): "clear", qn("w:color"): "auto", qn("w:fill"): "F3F4F6"},
    )
    pPr.append(shd)

    _add_styled_run(
        paragraph,
        code.rstrip("\n"),
        font_name=options.font_family,
        font_size_pt=options.font_size_pt - 1,
        code=True,
        rtl=False,
    )


def _add_blockquote(
    document: "DocxDocument",
    inline_tokens: list[list[Token]],
    options: DocxBuildOptions,
) -> None:
    for inline in inline_tokens:
        paragraph = document.add_paragraph()
        if options.rtl:
            _set_paragraph_rtl(paragraph)
        paragraph.paragraph_format.left_indent = Inches(0.3)
        paragraph.paragraph_format.right_indent = Inches(0.3)

        _render_inline_tokens(
            paragraph,
            inline,
            options,
            base_size=options.font_size_pt,
        )
        # Color italic gray for blockquote feel
        for run in paragraph.runs:
            run.italic = True
            run.font.color.rgb = RGBColor(0x4B, 0x55, 0x63)


def _add_list_item(
    document: "DocxDocument",
    inline_token: Token,
    options: DocxBuildOptions,
    *,
    ordered: bool,
    index: int,
    level: int,
) -> None:
    paragraph = document.add_paragraph()
    if options.rtl:
        _set_paragraph_rtl(paragraph)

    indent = Inches(0.25 * (level + 1))
    if options.rtl:
        paragraph.paragraph_format.right_indent = indent
    else:
        paragraph.paragraph_format.left_indent = indent

    bullet = f"{index}. " if ordered else "• "
    _add_styled_run(
        paragraph,
        bullet,
        font_name=options.font_family,
        font_size_pt=options.font_size_pt,
        bold=True,
        rtl=options.rtl,
    )

    _render_inline_tokens(
        paragraph,
        inline_token.children or [],
        options,
        base_size=options.font_size_pt,
    )


def _add_horizontal_rule(document: "DocxDocument") -> None:
    paragraph = document.add_paragraph()
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = pPr.makeelement(qn("w:pBdr"), {})
    bottom = pPr.makeelement(
        qn("w:bottom"),
        {
            qn("w:val"): "single",
            qn("w:sz"): "6",
            qn("w:space"): "1",
            qn("w:color"): "E5E7EB",
        },
    )
    pBdr.append(bottom)
    pPr.append(pBdr)


def _add_mermaid_image(
    document: "DocxDocument",
    image_path: Path,
    options: DocxBuildOptions,
) -> None:
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    try:
        # Read PNG dimensions to calculate proportional width
        import struct

        with open(image_path, "rb") as f:
            header = f.read(24)
        img_width = struct.unpack(">I", header[16:20])[0]
        img_height = struct.unpack(">I", header[20:24])[0]

        # PNGs are rendered at options.image_scale * 96 DPI.
        # Compute natural CSS width and clamp between min and max.
        css_width_inches = img_width / (float(options.image_scale) * 96.0)
        target_width = min(
            max(css_width_inches, options.image_min_width_inches),
            options.image_max_width_inches,
        )

        run.add_picture(str(image_path), width=Inches(target_width))
    except Exception as exc:  # noqa: BLE001
        _add_styled_run(
            paragraph,
            f"[خطا در درج نمودار Mermaid: {exc}]",
            font_name=options.font_family,
            font_size_pt=options.font_size_pt - 1,
            italic=True,
            color=RGBColor(0xDC, 0x26, 0x26),
            rtl=options.rtl,
        )


def _add_mermaid_placeholder_text(
    document: "DocxDocument",
    code: str,
    options: DocxBuildOptions,
) -> None:
    """Fallback when Mermaid image is not available: include the source code."""
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    _add_styled_run(
        paragraph,
        "[نمودار Mermaid - متن منبع:]",
        font_name=options.font_family,
        font_size_pt=options.font_size_pt - 1,
        italic=True,
        color=RGBColor(0x6B, 0x72, 0x80),
        rtl=options.rtl,
    )
    _add_code_block(document, code, options)


# ─── Table rendering ───────────────────────────────────────────────


def _add_table_from_tokens(
    document: "DocxDocument",
    tokens: list[Token],
    start_index: int,
    options: DocxBuildOptions,
) -> int:
    """
    Build a docx table from markdown-it table tokens.
    Returns index of token after table_close.
    """
    rows: list[list[list[Token]]] = []  # rows -> cells -> inline children
    is_header_row = False
    current_row: list[list[Token]] = []

    i = start_index + 1  # skip table_open
    while i < len(tokens):
        token = tokens[i]
        if token.type == "table_close":
            i += 1
            break
        elif token.type == "thead_open":
            is_header_row = True
        elif token.type == "thead_close":
            is_header_row = False
        elif token.type == "tr_open":
            current_row = []
        elif token.type == "tr_close":
            rows.append(current_row)
        elif token.type in ("th_open", "td_open"):
            # next token should be inline
            if i + 1 < len(tokens) and tokens[i + 1].type == "inline":
                current_row.append(tokens[i + 1].children or [])
                i += 1  # skip inline
        i += 1

    if not rows:
        return i

    cols = max(len(row) for row in rows)
    table = document.add_table(rows=len(rows), cols=cols)
    table.style = "Light Grid Accent 1"

    # Right-to-left table layout
    if options.rtl:
        tbl = table._tbl
        tblPr = tbl.find(qn("w:tblPr"))
        if tblPr is not None:
            bidiVisual = tblPr.find(qn("w:bidiVisual"))
            if bidiVisual is None:
                bidiVisual = tblPr.makeelement(qn("w:bidiVisual"), {})
                tblPr.append(bidiVisual)

    for row_idx, row_cells in enumerate(rows):
        for col_idx, inline_tokens in enumerate(row_cells):
            cell = table.rows[row_idx].cells[col_idx]
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            # Clear default empty paragraph
            paragraph = cell.paragraphs[0]
            paragraph.text = ""
            if options.rtl:
                _set_paragraph_rtl(paragraph)
                # Don't set jc; bidi handles alignment

            is_header = row_idx == 0
            _render_inline_tokens(
                paragraph,
                inline_tokens,
                options,
                base_size=options.font_size_pt - 1,
                base_bold=is_header,
            )

    return i


# ─── Main build function ───────────────────────────────────────────


def _is_mermaid_placeholder_block(token: Token) -> tuple[bool, int | None]:
    """Check if a fence token is a mermaid placeholder. Returns (is_placeholder, index)."""
    if token.type != "fence":
        return False, None
    if (token.info or "").strip() != "__mermaid_placeholder__":
        return False, None
    match = re.search(r"__MERMAID_PLACEHOLDER__(\d+)__", token.content)
    if not match:
        return False, None
    return True, int(match.group(1))


def build_docx(
    markdown_text: str,
    options: DocxBuildOptions,
    output_path: Path,
) -> DocxBuildResult:
    """
    Build a DOCX file from Markdown text.

    If options.mermaid_images is provided, mermaid blocks are replaced with
    embedded PNG images. Otherwise the source code is included as a code block.
    """
    text = strip_front_matter(markdown_text)
    title = extract_title(text, options.source_path.stem)

    # Extract mermaid blocks before parsing
    text_with_placeholders, mermaid_blocks = extract_mermaid_blocks(text)

    renderer = _build_renderer()
    tokens = renderer.parse(text_with_placeholders)

    document = Document()
    _set_document_default_rtl(document, options.font_family, options.font_size_pt)

    # Set page margins
    for section in document.sections:
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        # RTL section - set bidi on section properties
        if options.rtl:
            sectPr = section._sectPr
            bidi = sectPr.find(qn("w:bidi"))
            if bidi is None:
                bidi = sectPr.makeelement(qn("w:bidi"), {})
                sectPr.append(bidi)
            # Also set document grid for RTL
            docGrid = sectPr.find(qn("w:docGrid"))
            if docGrid is None:
                docGrid = sectPr.makeelement(qn("w:docGrid"), {})
                sectPr.append(docGrid)
            docGrid.set(qn("w:charSpace"), "0")

    # Walk tokens
    i = 0
    list_levels: list[bool] = []  # stack of ordered flags
    list_indices: list[int] = []  # stack of current index per list

    while i < len(tokens):
        token = tokens[i]
        kind = token.type

        if kind.startswith("heading_open"):
            level = int(kind[-1]) if kind[-1].isdigit() else int(token.tag[1:])
            if i + 1 < len(tokens) and tokens[i + 1].type == "inline":
                _add_heading(document, level, tokens[i + 1], options)
            i += 3  # heading_open, inline, heading_close
            continue

        if kind == "paragraph_open":
            if i + 1 < len(tokens) and tokens[i + 1].type == "inline":
                inline = tokens[i + 1]
                # Check if inside a list item
                if list_levels:
                    ordered = list_levels[-1]
                    list_indices[-1] += 1
                    _add_list_item(
                        document,
                        inline,
                        options,
                        ordered=ordered,
                        index=list_indices[-1],
                        level=len(list_levels) - 1,
                    )
                else:
                    _add_paragraph_block(document, inline, options)
            i += 3  # paragraph_open, inline, paragraph_close
            continue

        if kind == "fence" or kind == "code_block":
            is_mermaid, mermaid_idx = _is_mermaid_placeholder_block(token)
            if is_mermaid and mermaid_idx is not None and mermaid_idx < len(mermaid_blocks):
                mermaid_code = mermaid_blocks[mermaid_idx]
                if options.mermaid_images and mermaid_code in options.mermaid_images:
                    _add_mermaid_image(
                        document, options.mermaid_images[mermaid_code], options
                    )
                else:
                    _add_mermaid_placeholder_text(document, mermaid_code, options)
            else:
                _add_code_block(document, token.content, options)
            i += 1
            continue

        if kind == "bullet_list_open":
            list_levels.append(False)
            list_indices.append(0)
            i += 1
            continue
        if kind == "ordered_list_open":
            list_levels.append(True)
            list_indices.append(0)
            i += 1
            continue
        if kind in ("bullet_list_close", "ordered_list_close"):
            if list_levels:
                list_levels.pop()
                list_indices.pop()
            i += 1
            continue

        if kind in ("list_item_open", "list_item_close"):
            i += 1
            continue

        if kind == "blockquote_open":
            inlines: list[list[Token]] = []
            j = i + 1
            depth = 1
            while j < len(tokens) and depth > 0:
                if tokens[j].type == "blockquote_open":
                    depth += 1
                elif tokens[j].type == "blockquote_close":
                    depth -= 1
                    if depth == 0:
                        break
                elif tokens[j].type == "inline":
                    inlines.append(tokens[j].children or [])
                j += 1
            _add_blockquote(document, inlines, options)
            i = j + 1
            continue

        if kind == "hr":
            _add_horizontal_rule(document)
            i += 1
            continue

        if kind == "table_open":
            i = _add_table_from_tokens(document, tokens, i, options)
            continue

        # Skip unknown tokens
        i += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(output_path))

    return DocxBuildResult(
        title=title,
        has_mermaid=bool(mermaid_blocks),
        mermaid_blocks=mermaid_blocks,
    )
