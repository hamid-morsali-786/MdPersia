"""Word run/paragraph typography and BiDi formatting, independent of block rendering."""
from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

from .html_builder import EMOJI_PATTERN

if TYPE_CHECKING:
    from docx.document import Document as DocxDocument
    from docx.text.paragraph import Paragraph

DEFAULT_DOCX_FONT = "Vazirmatn"
DEFAULT_DOCX_FONT_FALLBACK = "Tahoma"
DEFAULT_DOCX_CODE_FONT = "Consolas"
DEFAULT_DOCX_EMOJI_FONT = "Segoe UI Emoji"

XML_ILLEGAL_CHARS_RE = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\ud800-\udfff\ufffe\uffff]"
)


def _clean_xml_text(text: str) -> str:
    """Remove control characters, surrogates, and noncharacters invalid in XML 1.0."""
    return XML_ILLEGAL_CHARS_RE.sub("", text) if text else ""


def _set_paragraph_rtl(paragraph: "Paragraph") -> None:
    """Apply right-to-left direction to a paragraph."""
    pPr = paragraph._p.get_or_add_pPr()
    bidi = pPr.find(qn("w:bidi"))
    if bidi is not None:
        pPr.remove(bidi)
    bidi = pPr.makeelement(qn("w:bidi"), {})
    pPr.append(bidi)


def _set_paragraph_ltr(paragraph: "Paragraph") -> None:
    """Explicitly apply left-to-right direction to a paragraph."""
    pPr = paragraph._p.get_or_add_pPr()
    bidi = pPr.find(qn("w:bidi"))
    if bidi is not None:
        pPr.remove(bidi)
    bidi = pPr.makeelement(qn("w:bidi"), {qn("w:val"): "0"})
    pPr.append(bidi)


def _set_run_rtl(run) -> None:
    """Apply right-to-left text formatting to a run."""
    rPr = run._r.get_or_add_rPr()
    rtl = rPr.find(qn("w:rtl"))
    if rtl is not None:
        rPr.remove(rtl)
    rtl = rPr.makeelement(qn("w:rtl"), {})
    rPr.append(rtl)


def _set_run_ltr(run) -> None:
    """Explicitly apply left-to-right text formatting to a run."""
    rPr = run._r.get_or_add_rPr()
    rtl = rPr.find(qn("w:rtl"))
    if rtl is not None:
        rPr.remove(rtl)
    rtl = rPr.makeelement(qn("w:rtl"), {qn("w:val"): "0"})
    rPr.append(rtl)


def _set_run_size_cs(run, font_size_pt: int) -> None:
    """Set complex-script font size (szCs) used for Arabic/Persian text in Word."""
    rPr = run._r.get_or_add_rPr()
    # Word stores size in half-points
    half_pts = str(int(font_size_pt * 2))
    szCs = rPr.find(qn("w:szCs"))
    if szCs is None:
        szCs = rPr.makeelement(qn("w:szCs"), {})
        rPr.append(szCs)
    szCs.set(qn("w:val"), half_pts)


def _set_run_bold_cs(run) -> None:
    """Set complex-script bold (bCs) used for Arabic/Persian text in Word."""
    rPr = run._r.get_or_add_rPr()
    bCs = rPr.find(qn("w:bCs"))
    if bCs is None:
        bCs = rPr.makeelement(qn("w:bCs"), {})
        rPr.append(bCs)


def _set_run_italic_cs(run) -> None:
    """Set complex-script italic (iCs) used for Arabic/Persian text in Word."""
    rPr = run._r.get_or_add_rPr()
    iCs = rPr.find(qn("w:iCs"))
    if iCs is None:
        iCs = rPr.makeelement(qn("w:iCs"), {})
        rPr.append(iCs)


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


@dataclass(frozen=True)
class RunStyle:
    font_name: str = DEFAULT_DOCX_FONT
    font_size_pt: int | None = None
    bold: bool = False
    italic: bool = False
    color: RGBColor | None = None
    code: bool = False
    rtl: bool = True


def _split_emojis(text: str) -> list[tuple[str, bool]]:
    """Split text into (substring, is_emoji) pairs."""
    result: list[tuple[str, bool]] = []
    last_end = 0
    for match in EMOJI_PATTERN.finditer(text):
        start, end = match.span()
        if start > last_end:
            result.append((text[last_end:start], False))
        result.append((match.group(0), True))
        last_end = end
    if last_end < len(text):
        result.append((text[last_end:], False))
    return result or [(text, False)]


def _apply_run_formatting(run, style: RunStyle) -> None:
    """Apply size, weight, slant, color, and bidi formatting to a run."""
    if style.font_size_pt is not None:
        run.font.size = Pt(style.font_size_pt)
        _set_run_size_cs(run, style.font_size_pt)
    if style.bold:
        run.bold = True
        _set_run_bold_cs(run)
    if style.italic:
        run.italic = True
        _set_run_italic_cs(run)
    if style.color is not None:
        run.font.color.rgb = style.color
    if style.rtl:
        _set_run_rtl(run)
    else:
        _set_run_ltr(run)


def _add_single_run(paragraph: "Paragraph", text: str, style: RunStyle):
    """Add a single formatted run to a paragraph."""
    run = paragraph.add_run(_clean_xml_text(text))
    f_name = style.font_name
    cs_font = DEFAULT_DOCX_FONT if style.code else f_name
    _set_run_font(run, f_name, complex_script_font=cs_font)
    _apply_run_formatting(run, style)
    return run


def _add_emoji_split_runs(
    paragraph: "Paragraph",
    text: str,
    base_style: RunStyle,
    base_font: str,
):
    """Split text by emojis and add individual runs with matching fonts."""
    last_run = None
    for piece, is_emoji in _split_emojis(text):
        style = replace(
            base_style,
            font_name=DEFAULT_DOCX_EMOJI_FONT if is_emoji else base_font,
            rtl=False if is_emoji else base_style.rtl,
        )
        last_run = _add_single_run(paragraph, piece, style)
    return last_run


def _add_styled_run(
    paragraph: "Paragraph",
    text: str,
    *,
    font_name: str = DEFAULT_DOCX_FONT,
    font_size_pt: int | None = None,
    bold: bool = False,
    italic: bool = False,
    code: bool = False,
    rtl: bool = True,
    color: RGBColor | None = None,
):
    """Add a run to the paragraph with styling and emoji font fallback."""
    if not text:
        return None
    style = RunStyle(
        font_name=DEFAULT_DOCX_CODE_FONT if code else font_name,
        font_size_pt=font_size_pt,
        bold=bold,
        italic=italic,
        color=color,
        code=code,
        rtl=rtl,
    )
    if not code and EMOJI_PATTERN.search(text):
        return _add_emoji_split_runs(paragraph, text, style, font_name)
    return _add_single_run(paragraph, text, style)


def _create_hyperlink_piece(hyperlink, paragraph: "Paragraph", text: str, style: RunStyle) -> None:
    """Create a styled run inside a Word hyperlink element."""
    from docx.oxml import parse_xml
    from docx.text.run import Run

    run_xml = parse_xml(r'<w:r xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>')
    hyperlink.append(run_xml)
    run = Run(run_xml, paragraph)
    run.text = _clean_xml_text(text)
    cs_font = style.font_name if not style.rtl else None
    _set_run_font(run, style.font_name, complex_script_font=cs_font)
    _apply_run_formatting(run, style)
    run.underline = True
