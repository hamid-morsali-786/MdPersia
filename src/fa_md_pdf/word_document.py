"""Word document defaults, page geometry and footer setup."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Mm, Pt, RGBColor

from .word_styles import _set_document_default_rtl, _set_paragraph_rtl, _set_run_font

if TYPE_CHECKING:
    from docx.document import Document as DocxDocument
    from docx.shared import Length

    from .docx_builder import DocxBuildOptions

PAGE_FORMAT_DIMENSIONS: dict[str, tuple[float, float]] = {
    "A3": (297.0, 420.0),
    "A4": (210.0, 297.0),
    "A5": (148.0, 210.0),
    "LETTER": (215.9, 279.4),
    "LEGAL": (215.9, 355.6),
}


UNIT_CONVERTERS: dict[str, Any] = {
    "mm": Mm,
    "cm": Cm,
    "in": Inches,
    "inch": Inches,
    "pt": Pt,
    "px": lambda v: Inches(v / 96.0),
}


def parse_docx_length(margin_str: str) -> Length:
    """Parse length string (e.g. '5mm', '15mm', '0.5in', '1.5cm', '20px') into docx Length."""
    m = re.match(r"^([\d.]+)\s*(mm|cm|in|inch|pt|px)?$", (margin_str or "").strip().lower())
    if not m:
        return Mm(15.0)
    try:
        val = float(m.group(1))
    except ValueError:
        return Mm(15.0)
    converter = UNIT_CONVERTERS.get(m.group(2) or "mm", Mm)
    return converter(val)


@dataclass(frozen=True)
class WordPageGeometry:
    width_mm: float
    height_mm: float
    margin: Length

    @property
    def available_image_height(self) -> float:
        return self.height_mm / 25.4 - 2 * self.margin.inches - .3

    @property
    def available_image_width(self) -> float:
        return max(1.0, self.width_mm / 25.4 - 2 * self.margin.inches)

    def image_width_limit(self, requested: float) -> float:
        # 6.5 is the existing option default: use all available page width.
        if requested == 6.5:
            return self.available_image_width
        return min(requested, self.available_image_width)


def page_geometry(format_key: str, margin: str, landscape: bool) -> WordPageGeometry:
    """Use the caller's existing format normalization and A4 fallback."""
    width, height = PAGE_FORMAT_DIMENSIONS.get(format_key, (210.0, 297.0))
    if landscape:
        width, height = height, width
    return WordPageGeometry(width, height, parse_docx_length(margin))


def create_document(options: DocxBuildOptions) -> DocxDocument:
    document = Document()
    _set_document_default_rtl(document, options.font_family, options.font_size_pt)

    # Set page dimensions, orientation, margins, and footer page numbers
    fmt_key = (options.page_format or "A4").strip().upper()
    geometry = page_geometry(fmt_key, options.margin, options.landscape)
    margin_len = geometry.margin

    for section in document.sections:
        section.page_width = Mm(geometry.width_mm)
        section.page_height = Mm(geometry.height_mm)
        section.orientation = WD_ORIENT.LANDSCAPE if options.landscape else WD_ORIENT.PORTRAIT

        section.left_margin = margin_len
        section.right_margin = margin_len
        section.top_margin = margin_len
        section.bottom_margin = margin_len
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

        # Dynamic Persian footer page numbering: "صفحه X از Y"
        if options.include_page_numbers:
            footer = section.footer
            if footer.paragraphs:
                f_p = footer.paragraphs[0]
                f_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                if options.rtl:
                    _set_paragraph_rtl(f_p)
                r_page = f_p.add_run("صفحه ")
                _set_run_font(r_page, options.font_family)
                r_page.font.size = Pt(9)
                r_page.font.color.rgb = RGBColor(0x6B, 0x72, 0x80)

                from docx.oxml import parse_xml

                f_p.add_run()._r.append(
                    parse_xml(r'<w:fldSimple xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" w:instr="PAGE"/>')
                )
                r_of = f_p.add_run(" از ")
                _set_run_font(r_of, options.font_family)
                r_of.font.size = Pt(9)
                r_of.font.color.rgb = RGBColor(0x6B, 0x72, 0x80)

                f_p.add_run()._r.append(
                    parse_xml(r'<w:fldSimple xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" w:instr="NUMPAGES"/>')
                )

    return document
