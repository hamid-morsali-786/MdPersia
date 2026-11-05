from __future__ import annotations
from .rtl_wrapper import has_persian, classify_block_direction
from .word_math import append_equation
from .word_numbering import new_list, apply_list
from .conversion_report import warn
# Compatibility exports preserve the previous import paths.
from .word_styles import (
    _clean_xml_text as _clean_xml_text,
    _set_paragraph_rtl as _set_paragraph_rtl,
    _set_paragraph_ltr as _set_paragraph_ltr,
    _set_run_rtl as _set_run_rtl,
    _set_run_ltr as _set_run_ltr,
    _set_run_size_cs as _set_run_size_cs,
    _set_run_bold_cs as _set_run_bold_cs,
    _set_run_italic_cs as _set_run_italic_cs,
    _set_run_font as _set_run_font,
    _set_document_default_rtl as _set_document_default_rtl,
    RunStyle as RunStyle,
    _split_emojis as _split_emojis,
    _apply_run_formatting as _apply_run_formatting,
    _add_single_run as _add_single_run,
    _add_emoji_split_runs as _add_emoji_split_runs,
    _add_styled_run as _add_styled_run,
    _create_hyperlink_piece as _create_hyperlink_piece,
    DEFAULT_DOCX_FONT as DEFAULT_DOCX_FONT,
    DEFAULT_DOCX_FONT_FALLBACK as DEFAULT_DOCX_FONT_FALLBACK,
    DEFAULT_DOCX_CODE_FONT as DEFAULT_DOCX_CODE_FONT,
    DEFAULT_DOCX_EMOJI_FONT as DEFAULT_DOCX_EMOJI_FONT,
    XML_ILLEGAL_CHARS_RE as XML_ILLEGAL_CHARS_RE,
)
from .word_document import (
    create_document,
    page_geometry,
    PAGE_FORMAT_DIMENSIONS as PAGE_FORMAT_DIMENSIONS,
    UNIT_CONVERTERS as UNIT_CONVERTERS,
    parse_docx_length as parse_docx_length,
)
from .local_images import resolve_image_file as _resolve_image_file

import re
import hashlib
from urllib.parse import unquote
from dataclasses import dataclass, replace
from html.parser import HTMLParser
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
    build_markdown_renderer,
    strip_emojis,
    strip_front_matter,
)

if TYPE_CHECKING:
    from docx.document import Document as DocxDocument
    from docx.text.paragraph import Paragraph


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
    include_page_numbers: bool = True
    highlight_code: bool = True
    page_format: str = "A4"
    margin: str = "15mm"
    landscape: bool = False
    strip_emojis: bool = False


@dataclass(frozen=True)
class DocxBuildResult:
    title: str
    has_mermaid: bool
    mermaid_blocks: list[str]  # raw mermaid code blocks (for image rendering)


def _add_hyperlink_run(
    paragraph: "Paragraph",
    text: str,
    href: str,
    *,
    font_name: str = DEFAULT_DOCX_FONT,
    font_size_pt: int | None = None,
    bold: bool = False,
    italic: bool = False,
    rtl: bool = True,
) -> None:
    """Add a native Word hyperlink to a paragraph with emoji support."""
    try:
        from docx.opc.constants import RELATIONSHIP_TYPE

        part = paragraph.part
        from docx.oxml import OxmlElement
        hyperlink = OxmlElement("w:hyperlink")
        if href.startswith("#"):
            hyperlink.set(qn("w:anchor"), _bookmark_name(href[1:]))
        else:
            r_id = part.relate_to(href, RELATIONSHIP_TYPE.HYPERLINK, is_external=True)
            hyperlink.set(qn("r:id"), r_id)
        paragraph._p.append(hyperlink)

        base_style = RunStyle(
            font_name=font_name,
            font_size_pt=font_size_pt,
            bold=bold,
            italic=italic,
            color=RGBColor(0x07, 0x58, 0x85),
            rtl=rtl,
        )
        for piece, is_emoji in _split_emojis(text):
            style = replace(
                base_style,
                font_name=DEFAULT_DOCX_EMOJI_FONT if is_emoji else font_name,
                rtl=False if is_emoji else rtl,
            )
            _create_hyperlink_piece(hyperlink, paragraph, piece, style)
    except Exception:
        _add_styled_run(
            paragraph,
            text,
            font_name=font_name,
            font_size_pt=font_size_pt,
            bold=bold,
            italic=italic,
            color=RGBColor(0x07, 0x58, 0x85),
            rtl=rtl,
        )


HTML_IMG_RE = re.compile(r"""<img\b(?P<attrs>[^>]*)>""", re.IGNORECASE)
ATTR_SRC_RE = re.compile(r"""src\s*=\s*['"]([^'"]+)['"]""", re.IGNORECASE)
ATTR_ALT_RE = re.compile(r"""alt\s*=\s*['"]([^'"]*)['"]""", re.IGNORECASE)


def _calculate_image_width(img_px_width: int, options: DocxBuildOptions) -> float:
    """Calculate target width in inches constrained by page format and margins."""
    css_width = img_px_width / 96.0
    fmt_key = (options.page_format or "A4").strip().upper()
    geometry = page_geometry(fmt_key, options.margin, options.landscape)
    available_w = geometry.available_image_width
    max_w = geometry.image_width_limit(options.image_max_width_inches)
    target_w = min(css_width, max_w)
    return min(css_width, available_w) if target_w < 1.0 else target_w


def _embed_image_picture(paragraph: "Paragraph", image_path: Path, options: DocxBuildOptions) -> bool:
    """Embed local picture file into paragraph run."""
    try:
        from docx.image.image import Image as DocxImage

        img = DocxImage.from_file(str(image_path))
        target_w = _calculate_image_width(img.px_width, options)
        geometry = page_geometry(options.page_format.upper(), options.margin, options.landscape)
        usable_height = geometry.available_image_height
        target_w = min(target_w, max(.1, usable_height) * img.px_width / img.px_height)
        run = paragraph.add_run()
        run.add_picture(str(image_path), width=Inches(target_w))
        return True
    except Exception:
        return False


def _add_image_to_paragraph(
    paragraph: "Paragraph",
    src: str,
    alt: str,
    options: DocxBuildOptions,
) -> bool:
    """Resolve and embed image into paragraph or add fallback text."""
    resolved = _resolve_image_file(src, options.source_path)
    if resolved and _embed_image_picture(paragraph, resolved, options):
        return True
    warn("image.embed", f"درج تصویر در Word ممکن نشد: {src}")
    _add_styled_run(
        paragraph,
        f"[تصویر: {alt or src}]",
        font_name=options.font_family,
        font_size_pt=options.font_size_pt,
        italic=True,
        color=RGBColor(0x6B, 0x72, 0x80),
        rtl=options.rtl,
    )
    return False


def _add_standalone_image(
    document: "DocxDocument",
    src: str,
    alt: str,
    options: DocxBuildOptions,
) -> "Paragraph":
    """Add a standalone centered paragraph containing the image."""
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _add_image_to_paragraph(paragraph, src, alt, options)
    return paragraph


def _handle_html_inline_image(
    paragraph: "Paragraph",
    raw_html: str,
    options: DocxBuildOptions,
) -> None:
    match = HTML_IMG_RE.search(raw_html)
    if not match:
        return
    attrs = match.group("attrs")
    src_m = ATTR_SRC_RE.search(attrs)
    alt_m = ATTR_ALT_RE.search(attrs)
    src = src_m.group(1) if src_m else ""
    alt = alt_m.group(1) if alt_m else ""
    if src:
        _add_image_to_paragraph(paragraph, src, alt, options)


class HtmlBlockImageParser(HTMLParser):
    """Parse HTML blocks extracting image tags and caption containers."""

    def __init__(self) -> None:
        super().__init__()
        self.images: list[tuple[str, str]] = []
        self.caption_runs: list[tuple[str, str, str | None]] = []
        self._in_caption = False
        self._current_href: str | None = None
        self._ignore = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = {k.lower(): v or "" for k, v in attrs}
        t = tag.lower()
        if t in ("style", "script"):
            self._ignore = True
        elif t == "img":
            self.images.append((attr_dict.get("src", ""), attr_dict.get("alt", "")))
        elif t in ("figcaption",) or "caption" in attr_dict.get("class", "").lower():
            self._in_caption = True
        elif t == "a":
            self._current_href = attr_dict.get("href")
        elif t == "br" and self._in_caption:
            self.caption_runs.append(("break", "", None))

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in ("style", "script"):
            self._ignore = False
        elif t in ("figcaption", "div"):
            self._in_caption = False
        elif t == "a":
            self._current_href = None

    def handle_data(self, data: str) -> None:
        if self._ignore or not self._in_caption or not data:
            return
        if self._current_href:
            self.caption_runs.append(("link", data, self._current_href))
        else:
            self.caption_runs.append(("text", data, None))


def _append_caption_runs(
    paragraph: "Paragraph",
    caption_runs: list[tuple[str, str, str | None]],
    options: DocxBuildOptions,
) -> None:
    c_size = max(8, options.font_size_pt - 2)
    c_color = RGBColor(0x4B, 0x55, 0x63)
    at_line_start = True
    for kind, text, href in caption_runs:
        clean = re.sub(r"[ \t\r\n]+", " ", text)
        if kind == "break":
            paragraph.add_run().add_break()
            at_line_start = True
        elif kind == "link" and href and clean.strip():
            _add_hyperlink_run(paragraph, clean.strip(), href, font_name=options.font_family, font_size_pt=c_size, rtl=options.rtl)
            at_line_start = False
        elif kind == "text" and clean.strip():
            val = clean.lstrip() if at_line_start else clean
            _add_styled_run(paragraph, val, font_name=options.font_family, font_size_pt=c_size, color=c_color, rtl=options.rtl)
            at_line_start = False


def _render_caption_paragraph(
    document: "DocxDocument",
    caption_runs: list[tuple[str, str, str | None]],
    options: DocxBuildOptions,
) -> None:
    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if options.rtl:
        _set_paragraph_rtl(p)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(12)
    _append_caption_runs(p, caption_runs, options)


def _render_html_images_block(
    document: "DocxDocument",
    raw_html: str,
    options: DocxBuildOptions,
) -> None:
    parser = HtmlBlockImageParser()
    parser.feed(raw_html)
    for src, alt in parser.images:
        _add_standalone_image(document, src, alt, options)
    if parser.caption_runs:
        _render_caption_paragraph(document, parser.caption_runs, options)


def _handle_html_block(
    document: "DocxDocument",
    raw_html: str,
    options: DocxBuildOptions,
) -> None:
    raw_lower = raw_html.lower()
    if "pagebreak" in raw_lower or "page-break" in raw_lower:
        document.add_page_break()
    if "<img" in raw_lower:
        _render_html_images_block(document, raw_html, options)


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
    ltr_stack = [False]
    strike = False

    for token in tokens:
        kind = token.type
        previous_children = len(paragraph._p)

        if kind == "html_inline":
            content_lower = token.content.lower()
            if 'task-list-item-checkbox' in content_lower:
                _add_styled_run(paragraph, "☒ " if 'checked="checked"' in content_lower else "☐ ",
                                font_name="Segoe UI Symbol", rtl=False)
                continue
            if 'dir="ltr"' in content_lower or "dir='ltr'" in content_lower or "<bdi" in content_lower:
                ltr_stack.append(True)
            elif 'dir="rtl"' in content_lower or "dir='rtl'" in content_lower:
                ltr_stack.append(False)
            elif ("</span" in content_lower or "</bdi" in content_lower) and len(ltr_stack) > 1:
                ltr_stack.pop()
            elif "<img" in content_lower:
                _handle_html_inline_image(paragraph, token.content, options)
            continue

        if kind in {"math_inline", "math_block"}:
            append_equation(paragraph, _clean_xml_text(token.content), display=kind == "math_block")
        elif kind == "footnote_ref":
            from docx.oxml import OxmlElement
            ref = OxmlElement("w:footnoteReference")
            ref.set(qn("w:id"), str(token.meta["id"] + 1))
            run = paragraph.add_run()
            run.font.superscript = True
            run._r.append(ref)
        elif kind == "text":
            text = token.content
            if not text:
                continue
            is_rtl = options.rtl and (not ltr_stack[-1]) and has_persian(text)
            link_href = getattr(paragraph, "_link_href", None)
            if link_href:
                _add_hyperlink_run(
                    paragraph,
                    text,
                    link_href,
                    font_name=options.font_family,
                    font_size_pt=base_size,
                    bold=bold_stack[-1],
                    italic=italic_stack[-1],
                    rtl=is_rtl,
                )
            else:
                _add_styled_run(
                    paragraph,
                    text,
                    font_name=options.font_family,
                    font_size_pt=base_size,
                    bold=bold_stack[-1],
                    italic=italic_stack[-1],
                    rtl=is_rtl,
                )
            paragraph._link_has_text = True  # type: ignore[attr-defined]

        elif kind == "softbreak":
            is_rtl = options.rtl and (not ltr_stack[-1])
            _add_styled_run(paragraph, " ", font_name=options.font_family, rtl=is_rtl)

        elif kind == "hardbreak":
            run = paragraph.add_run()
            run.add_break()

        elif kind == "code_inline":
            href = getattr(paragraph, "_link_href", None)
            if href:
                _add_hyperlink_run(paragraph, token.content, href,
                                   font_name=DEFAULT_DOCX_CODE_FONT,
                                   font_size_pt=base_size, rtl=False)
            else:
                _add_styled_run(paragraph, token.content, font_name=options.font_family,
                                font_size_pt=base_size, code=True, rtl=False)
            paragraph._link_has_text = True

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
            # Store href in a marker
            paragraph._link_href = href  # type: ignore[attr-defined]
            paragraph._link_has_text = False  # type: ignore[attr-defined]

        elif kind == "link_close":
            paragraph._link_href = None  # type: ignore[attr-defined]
            paragraph._link_has_text = False  # type: ignore[attr-defined]

        elif kind == "image":
            alt = token.content or token.attrGet("alt") or ""
            src = token.attrGet("src") or ""
            _add_image_to_paragraph(paragraph, src, alt, options)

        elif kind == "s_open":
            strike = True
        elif kind == "s_close":
            strike = False

        if strike:
            from docx.text.run import Run
            for element in list(paragraph._p)[previous_children:]:
                for run_element in element.iter(qn("w:r")):
                    Run(run_element, paragraph).font.strike = True


# ─── Mermaid extraction (without HTML conversion) ──────────────────

def extract_mermaid_blocks(text: str) -> tuple[str, list[str]]:
    """Discover actual fences, never Mermaid examples inside another code fence."""
    tokens = _build_renderer().parse(strip_front_matter(text))
    return text, [t.content.strip() for t in tokens
                  if t.type == "fence" and t.info.strip().lower() == "mermaid"]


def _build_renderer() -> MarkdownIt:
    return build_markdown_renderer()


def _bookmark_name(slug: str) -> str:
    # Word bookmark names cannot contain arbitrary Unicode/punctuation.
    return "md_" + hashlib.sha256(unquote(slug).encode("utf8")).hexdigest()[:32]


def _add_bookmark(paragraph, slug: str, identifier: int) -> None:
    from docx.oxml import OxmlElement
    start = OxmlElement("w:bookmarkStart")
    start.set(qn("w:id"), str(identifier))
    start.set(qn("w:name"), _bookmark_name(slug))
    end = OxmlElement("w:bookmarkEnd")
    end.set(qn("w:id"), str(identifier))
    paragraph._p.append(start)
    paragraph._p.append(end)


# ─── Block rendering ───────────────────────────────────────────────


def _add_heading(
    document: "DocxDocument",
    level: int,
    inline_token: Token,
    options: DocxBuildOptions,
) -> None:
    paragraph = document.add_paragraph(style=f"Heading {level}")
    has_fa = options.rtl and classify_block_direction(inline_token.content) == "rtl"
    if has_fa:
        _set_paragraph_rtl(paragraph)
    else:
        _set_paragraph_ltr(paragraph)
        paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT

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
    children = inline_token.children or []
    visible_children = [
        t for t in children
        if (t.type != "html_inline" or "<img" in t.content.lower())
        and not (t.type == "text" and not t.content.strip())
    ]
    if not visible_children:
        return

    paragraph = document.add_paragraph()
    has_image = any(
        t.type == "image" or (t.type == "html_inline" and "<img" in t.content.lower())
        for t in children
    )
    has_fa = options.rtl and classify_block_direction(inline_token.content) == "rtl"
    if has_image:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif has_fa:
        _set_paragraph_rtl(paragraph)
    else:
        _set_paragraph_ltr(paragraph)
        paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT

    _render_inline_tokens(
        paragraph,
        children,
        options,
        base_size=options.font_size_pt,
    )


CALLOUT_CONFIGS = {
    "NOTE": {"color": RGBColor(0x25, 0x63, 0xEB), "hex": "2563EB", "bg": "EFF6FF", "title": "💡 نکته:", "title_plain": "نکته:"},
    "TIP": {"color": RGBColor(0x16, 0xA3, 0x4A), "hex": "16A34A", "bg": "F0FDF4", "title": "💡 راهنما:", "title_plain": "راهنما:"},
    "IMPORTANT": {"color": RGBColor(0x7C, 0x3A, 0xED), "hex": "7C3AED", "bg": "F5F3FF", "title": "📌 مهم:", "title_plain": "مهم:"},
    "WARNING": {"color": RGBColor(0xD9, 0x77, 0x06), "hex": "D97706", "bg": "FFFBEB", "title": "⚠️ هشدار:", "title_plain": "هشدار:"},
    "CAUTION": {"color": RGBColor(0xDC, 0x26, 0x26), "hex": "DC2626", "bg": "FEF2F2", "title": "🛑 احتیاط:", "title_plain": "احتیاط:"},
}


def _add_code_block(
    document: "DocxDocument",
    code: str,
    options: DocxBuildOptions,
    lang: str = "",
) -> None:
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    _set_paragraph_ltr(paragraph)
    paragraph.paragraph_format.left_indent = Inches(0.2)
    paragraph.paragraph_format.right_indent = Inches(0.2)

    # Add shading via XML
    pPr = paragraph._p.get_or_add_pPr()
    shd = pPr.makeelement(
        qn("w:shd"),
        {qn("w:val"): "clear", qn("w:color"): "auto", qn("w:fill"): "F8FAFC"},
    )
    pPr.append(shd)

    # Attempt Pygments syntax highlighting
    tokens = None
    clean_lang = (lang or "").strip().lower().split()[0] if (lang or "").strip() else ""
    if options.highlight_code and clean_lang:
        try:
            from pygments.lexers import get_lexer_by_name

            lexer = get_lexer_by_name(clean_lang, stripall=False)
            tokens = list(lexer.get_tokens(code.rstrip("\n")))
        except Exception:
            tokens = None

    if tokens:
        from pygments.token import Comment, Keyword, Name, Number, Operator, String

        for ttype, val in tokens:
            if not val:
                continue
            color = None
            bold = False
            italic = False
            if ttype in Keyword or Keyword in ttype.split():
                color = RGBColor(0x00, 0x70, 0x20)
                bold = True
            elif ttype in String or String in ttype.split():
                color = RGBColor(0xBA, 0x21, 0x21)
            elif ttype in Comment or Comment in ttype.split():
                color = RGBColor(0x60, 0xA0, 0xB0)
                italic = True
            elif ttype in Number or Number in ttype.split():
                color = RGBColor(0x20, 0x80, 0x50)
            elif ttype in Name.Function or ttype in Name.Class:
                color = RGBColor(0x06, 0x28, 0x7E)
                bold = True
            elif ttype in Name.Builtin:
                color = RGBColor(0x00, 0x70, 0x20)
            elif ttype in Operator:
                color = RGBColor(0x55, 0x55, 0x55)

            _add_styled_run(
                paragraph,
                val,
                font_name=options.font_family,
                font_size_pt=options.font_size_pt - 1,
                bold=bold,
                italic=italic,
                color=color,
                code=True,
                rtl=False,
            )
    else:
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
    callout_type = None
    if inline_tokens and inline_tokens[0]:
        first_token = inline_tokens[0][0]
        if first_token.type == "text":
            match = re.match(
                r"^\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*",
                first_token.content,
                re.IGNORECASE,
            )
            if match:
                callout_type = match.group(1).upper()
                first_token.content = first_token.content[match.end():]

    cfg = CALLOUT_CONFIGS.get(callout_type) if callout_type else None

    title_rendered = False
    for inline in inline_tokens:
        has_text = any(t.content.strip() for t in inline if t.type == "text")
        if cfg and not title_rendered and not has_text:
            # If the first line was only the [!NOTE] tag and is now empty, skip creating an empty line
            continue

        paragraph = document.add_paragraph()
        if options.rtl:
            _set_paragraph_rtl(paragraph)
        paragraph.paragraph_format.left_indent = Inches(0.3)
        paragraph.paragraph_format.right_indent = Inches(0.3)

        pPr = paragraph._p.get_or_add_pPr()
        if cfg:
            shd = pPr.makeelement(
                qn("w:shd"),
                {qn("w:val"): "clear", qn("w:color"): "auto", qn("w:fill"): cfg["bg"]},
            )
            pPr.append(shd)
            pBdr = pPr.makeelement(qn("w:pBdr"), {})
            border = pPr.makeelement(
                qn("w:right" if options.rtl else "w:left"),
                {qn("w:val"): "single", qn("w:sz"): "24", qn("w:space"): "8", qn("w:color"): cfg["hex"]},
            )
            pBdr.append(border)
            pPr.append(pBdr)

            if not title_rendered:
                raw_title = cfg["title_plain"] if options.strip_emojis else cfg["title"]
                suffix = " " if has_text else ""
                _add_styled_run(
                    paragraph,
                    raw_title + suffix,
                    font_name=options.font_family,
                    font_size_pt=options.font_size_pt,
                    bold=True,
                    color=cfg["color"],
                    rtl=options.rtl,
                )
                title_rendered = True

        _render_inline_tokens(
            paragraph,
            inline,
            options,
            base_size=options.font_size_pt,
        )

        if not cfg:
            for run in paragraph.runs:
                run.italic = True
                run.font.color.rgb = RGBColor(0x4B, 0x55, 0x63)

    if cfg and not title_rendered:
        # Standalone callout tag with no following text
        paragraph = document.add_paragraph()
        if options.rtl:
            _set_paragraph_rtl(paragraph)
        paragraph.paragraph_format.left_indent = Inches(0.3)
        paragraph.paragraph_format.right_indent = Inches(0.3)
        pPr = paragraph._p.get_or_add_pPr()
        shd = pPr.makeelement(
            qn("w:shd"),
            {qn("w:val"): "clear", qn("w:color"): "auto", qn("w:fill"): cfg["bg"]},
        )
        pPr.append(shd)
        pBdr = pPr.makeelement(qn("w:pBdr"), {})
        border = pPr.makeelement(
            qn("w:right" if options.rtl else "w:left"),
            {qn("w:val"): "single", qn("w:sz"): "24", qn("w:space"): "8", qn("w:color"): cfg["hex"]},
        )
        pBdr.append(border)
        pPr.append(pBdr)
        raw_title = cfg["title_plain"] if options.strip_emojis else cfg["title"]
        _add_styled_run(
            paragraph,
            raw_title,
            font_name=options.font_family,
            font_size_pt=options.font_size_pt,
            bold=True,
            color=cfg["color"],
            rtl=options.rtl,
        )


def _add_list_item(
    document: "DocxDocument",
    inline_token: Token,
    options: DocxBuildOptions,
    *,
    ordered: bool,
    index: int,
    level: int,
    continuation: bool = False,
    number_id: int | None = None,
) -> None:
    paragraph = document.add_paragraph()
    is_item_rtl = options.rtl and classify_block_direction(inline_token.content) == "rtl"
    if is_item_rtl:
        _set_paragraph_rtl(paragraph)
        paragraph.paragraph_format.right_indent = Inches(0.25 * (level + 1))
    else:
        _set_paragraph_ltr(paragraph)
        paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
        paragraph.paragraph_format.left_indent = Inches(0.25 * (level + 1))

    task = any(t.type == "html_inline" and "task-list-item-checkbox" in t.content
               for t in inline_token.children or [])
    if not task and not continuation and number_id is not None:
        apply_list(paragraph, number_id, level, is_item_rtl)

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
        img_width, img_height = struct.unpack(">II", header[16:24])

        # PNGs are rendered at options.image_scale * 96 DPI.
        # Compute natural CSS width and clamp between min and max.
        css_width_inches = img_width / (float(options.image_scale) * 96.0)
        fmt_key = (options.page_format or "A4").strip().upper()
        geometry = page_geometry(fmt_key, options.margin, options.landscape)
        max_limit = geometry.image_width_limit(options.image_max_width_inches)
        target_width = min(
            max(css_width_inches, options.image_min_width_inches),
            max_limit,
        )

        usable_height = geometry.available_image_height
        target_width = min(target_width, max(.1, usable_height) * img_width / img_height)
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
    current_row: list[list[Token]] = []
    alignments: list[str | None] = []

    i = start_index + 1  # skip table_open
    while i < len(tokens):
        token = tokens[i]
        if token.type == "table_close":
            i += 1
            break
        elif token.type in ("thead_open", "thead_close"):
            pass
        elif token.type == "tr_open":
            current_row = []
        elif token.type == "tr_close":
            rows.append(current_row)
        elif token.type in ("th_open", "td_open"):
            if token.type == "th_open":
                alignments.append(token.attrGet("style"))
            # next token should be inline
            if i + 1 < len(tokens) and tokens[i + 1].type == "inline":
                current_row.append(tokens[i + 1].children or [])
                i += 1  # skip inline
        i += 1

    if not rows:
        return i

    cols = max(len(row) for row in rows)
    if cols == 0:
        return i

    table = document.add_table(rows=len(rows), cols=cols)
    table.style = "Light Grid Accent 1"
    table.autofit = False
    section = document.sections[0]
    width = (section.page_width - section.left_margin - section.right_margin) // cols
    for column in table.columns:
        column.width = width
    for row in table.rows:
        for cell in row.cells:
            cell.width = width

    # Preserve column order for English tables even in a Persian document.
    if options.rtl and tokens[start_index].attrGet("dir") == "rtl":
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
            text = " ".join(t.content for t in inline_tokens)
            if options.rtl and classify_block_direction(text) == "rtl":
                _set_paragraph_rtl(paragraph)
            else:
                _set_paragraph_ltr(paragraph)
            align = alignments[col_idx] if col_idx < len(alignments) else None
            if align:
                paragraph.alignment = {"text-align:left": WD_ALIGN_PARAGRAPH.LEFT,
                    "text-align:center": WD_ALIGN_PARAGRAPH.CENTER,
                    "text-align:right": WD_ALIGN_PARAGRAPH.RIGHT}.get(align)

            is_header = row_idx == 0
            if is_header and col_idx == 0:
                trPr = table.rows[row_idx]._tr.get_or_add_trPr()
                if trPr.find(qn("w:tblHeader")) is None:
                    trPr.append(trPr.makeelement(qn("w:tblHeader"), {}))

            _render_inline_tokens(
                paragraph,
                inline_tokens,
                options,
                base_size=options.font_size_pt - 1,
                base_bold=is_header,
            )

    return i


# ─── Main build function ───────────────────────────────────────────


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
    if options.strip_emojis:
        markdown_text = strip_emojis(markdown_text)
    text = strip_front_matter(markdown_text)
    renderer = _build_renderer()
    env = {}
    tokens = renderer.parse(text, env)
    title = env.get("document_title", options.source_path.stem)
    mermaid_blocks = [t.content.strip() for t in tokens
                      if t.type == "fence" and t.info.strip().lower() == "mermaid"]

    document = create_document(options)

    document.core_properties.title = _clean_xml_text(title)[:255]
    _render_blocks(document, tokens, options)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(output_path))

    return DocxBuildResult(
        title=title,
        has_mermaid=bool(mermaid_blocks),
        mermaid_blocks=mermaid_blocks,
    )


def _render_blocks(document, tokens: list[Token], options: DocxBuildOptions) -> None:
    # Walk tokens
    i = 0
    list_levels: list[bool] = []  # stack of ordered flags
    list_indices: list[int] = []  # stack of current index per list
    item_first: list[bool] = []
    list_numbers: list[int] = []

    while i < len(tokens):
        token = tokens[i]
        kind = token.type

        if kind.startswith("heading_open"):
            level = int(kind[-1]) if kind[-1].isdigit() else int(token.tag[1:])
            if i + 1 < len(tokens) and tokens[i + 1].type == "inline":
                _add_heading(document, level, tokens[i + 1], options)
                _add_bookmark(document.paragraphs[-1], token.attrGet("id") or "section",
                              len(document.paragraphs))
            i += 3  # heading_open, inline, heading_close
            continue

        if kind == "paragraph_open":
            if i + 1 < len(tokens) and tokens[i + 1].type == "inline":
                inline = tokens[i + 1]
                if inline.content.strip() == r"\pagebreak":
                    document.add_page_break()
                    i += 3
                    continue
                # Check if inside a list item
                if list_levels:
                    ordered = list_levels[-1]
                    first = item_first[-1]
                    item_first[-1] = False
                    _add_list_item(
                        document,
                        inline,
                        options,
                        ordered=ordered,
                        index=list_indices[-1],
                        level=len(list_levels) - 1,
                        continuation=not first,
                        number_id=list_numbers[-1],
                    )
                else:
                    _add_paragraph_block(document, inline, options)
            i += 3  # paragraph_open, inline, paragraph_close
            continue

        if kind == "math_block":
            paragraph = document.add_paragraph()
            _set_paragraph_ltr(paragraph)
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.keep_together = True
            append_equation(paragraph, _clean_xml_text(token.content), display=True)
            i += 1
            continue

        if kind == "fence" or kind == "code_block":
            if kind == "fence" and token.info.strip().lower() == "mermaid":
                mermaid_code = token.content.strip()
                if options.mermaid_images and mermaid_code in options.mermaid_images:
                    _add_mermaid_image(
                        document, options.mermaid_images[mermaid_code], options
                    )
                else:
                    _add_mermaid_placeholder_text(document, mermaid_code, options)
            else:
                lang = (token.info or "").strip().split()[0] if (token.info or "").strip() else ""
                _add_code_block(document, token.content, options, lang=lang)
            i += 1
            continue

        if kind == "bullet_list_open":
            list_numbers.append(new_list(document, False))
            list_levels.append(False)
            list_indices.append(0)
            i += 1
            continue
        if kind == "ordered_list_open":
            list_numbers.append(new_list(document, True, int(token.attrGet("start") if token.attrGet("start") is not None else 1)))
            list_levels.append(True)
            list_indices.append(int(token.attrGet("start") if token.attrGet("start") is not None else 1) - 1)
            i += 1
            continue
        if kind in ("bullet_list_close", "ordered_list_close"):
            if list_levels:
                list_numbers.pop()
                list_levels.pop()
                list_indices.pop()
            i += 1
            continue

        if kind in ("list_item_open", "list_item_close"):
            if kind == "list_item_open":
                item_first.append(True)
                if list_indices:
                    list_indices[-1] += 1
            elif item_first:
                item_first.pop()
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
            nested = tokens[i + 1:j]
            if any(t.type in {"math_block", "fence", "code_block", "table_open",
                              "heading_open", "bullet_list_open", "ordered_list_open", "hr"}
                   for t in nested):
                before = len(document.paragraphs)
                if (len(nested) >= 3 and nested[0].type == "paragraph_open"
                        and re.match(r"^\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]",
                                     nested[1].content, re.IGNORECASE)):
                    _add_blockquote(document, [nested[1].children or []], options)
                    nested = nested[3:]
                _render_blocks(document, nested, options)
                for paragraph in document.paragraphs[before:]:
                    paragraph.paragraph_format.left_indent = Inches(.3)
                    paragraph.paragraph_format.right_indent = Inches(.3)
            else:
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

        if kind == "html_block":
            _handle_html_block(document, token.content, options)
            i += 1
            continue

        if kind == "footnote_block_open":
            _add_footnotes(document, tokens[i + 1:], options)
            break

        # Skip unknown tokens
        i += 1


def _add_footnotes(document, tokens, options):
    """Emit real Word footnotes, including math, images and external link relations."""
    from copy import deepcopy
    from docx.oxml import OxmlElement
    from docx.opc.part import Part
    from docx.opc.packuri import PackURI
    from docx.opc.constants import RELATIONSHIP_TYPE as RT, CONTENT_TYPE as CT
    from lxml import etree

    root = OxmlElement("w:footnotes")
    part = Part(PackURI("/word/footnotes.xml"), CT.WML_FOOTNOTES, b"", document.part.package)
    for identifier, kind in [(-1, "separator"), (0, "continuationSeparator")]:
        footnote = OxmlElement("w:footnote")
        footnote.set(qn("w:id"), str(identifier))
        footnote.set(qn("w:type"), kind)
        p = OxmlElement("w:p")
        r = OxmlElement("w:r")
        r.append(OxmlElement("w:" + kind))
        p.append(r)
        footnote.append(p)
        root.append(footnote)
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.type != "footnote_open":
            i += 1
            continue
        j = i + 1
        while j < len(tokens) and tokens[j].type != "footnote_close":
            j += 1
        note = Document()
        # Footnote list IDs must belong to the package-wide numbering part.
        numbering_rel = next(rel for rel in note.part.rels.values() if rel.reltype == RT.NUMBERING)
        note.part.drop_rel(numbering_rel.rId)
        note.part.relate_to(document.part.numbering_part, RT.NUMBERING)
        _render_blocks(note, tokens[i + 1:j], options)
        if not note.paragraphs:
            note.add_paragraph()
        marker = OxmlElement("w:r")
        marker.append(OxmlElement("w:footnoteRef"))
        note.paragraphs[0]._p.insert(1 if note.paragraphs[0]._p.pPr is not None else 0, marker)
        footnote = OxmlElement("w:footnote")
        footnote.set(qn("w:id"), str(token.meta["id"] + 1))
        for child in note._element.body:
            if child.tag == qn("w:sectPr"):
                continue
            element = deepcopy(child)
            for node in element.iter():
                for attr in (qn("r:id"), qn("r:embed"), qn("r:link")):
                    old = node.get(attr)
                    if old:
                        rel = note.part.rels[old]
                        target = rel.target_ref if rel.is_external else rel.target_part
                        node.set(attr, part.relate_to(target, rel.reltype, rel.is_external))
            footnote.append(element)
        root.append(footnote)
        i = j + 1
    part._blob = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    document.part.relate_to(part, RT.FOOTNOTES)
