"""Convert the reader's sanitized MathML into editable Office equations offline."""
from __future__ import annotations

from .conversion_report import warn
import logging
from xml.etree import ElementTree as ET

from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls
from mathml2omml import convert

from .math_renderer import render_math

logger = logging.getLogger(__name__)


def append_equation(paragraph, source: str, *, display: bool = False) -> None:
    """Keep malformed/unsupported TeX visible instead of dropping document content."""
    try:
        mathml = ET.fromstring(render_math(source, {"display_mode": display}))
        if mathml.tag.rsplit("}", 1)[-1] != "math":
            raise ValueError("invalid TeX")
        # mathml2omml otherwise drops TeX spacing commands (mspace).
        for node in mathml.iter():
            if node.tag.endswith("}mspace"):
                width = node.get("width", "0")
                node.tag = "{http://www.w3.org/1998/Math/MathML}mtext"
                node.attrib.clear()
                node.text = "\u2009" if not width.startswith("-") else ""
        xml = convert(ET.tostring(mathml, encoding="unicode"))
        equation = parse_xml(xml.replace("<m:oMath>", f"<m:oMath {nsdecls('m', 'w')}>"))
        # The converter wraps every mrow in an unbreakable box. Plain grouping
        # needs no Office box and must allow Word to wrap at binary operators.
        for box in reversed(list(equation.iter(qn("m:box")))):
            content = box.find(qn("m:e"))
            if content is not None and len(box) == 1:
                parent = box.getparent()
                index = parent.index(box)
                parent.remove(box)
                for offset, child in enumerate(list(content)):
                    parent.insert(index + offset, child)
        # The converter omits the required degree element for square roots.
        for rad in equation.iter(qn("m:rad")):
            if rad.find(qn("m:deg")) is None:
                props = OxmlElement("m:radPr")
                hidden = OxmlElement("m:degHide")
                hidden.set(qn("m:val"), "1")
                props.append(hidden)
                rad.insert(0, props)
                rad.insert(1, OxmlElement("m:deg"))
        for run in equation.iter(qn("m:r")):
            props = OxmlElement("w:rPr")
            fonts = OxmlElement("w:rFonts")
            for name in ("ascii", "hAnsi", "cs"):
                fonts.set(qn("w:" + name), "Cambria Math")
            props.append(fonts)
            rtl = OxmlElement("w:rtl")
            rtl.set(qn("w:val"), "0")
            props.append(rtl)
            run.insert(1 if run.find(qn("m:rPr")) is not None else 0, props)
        for text in equation.iter(qn("m:t")):
            text.set(qn("xml:space"), "preserve")
        if display:
            wrapper = OxmlElement("m:oMathPara")
            wrapper.append(equation)
            paragraph._p.append(wrapper)
        else:
            paragraph._p.append(equation)
    except Exception as exc:
        warn('math.fallback', 'فرمول در Word قابل حروف‌چینی نبود؛ متن منبع حفظ شد.')
        logger.warning("Could not typeset a Word equation; preserving TeX: %s", exc)
        paragraph.add_run(source)
