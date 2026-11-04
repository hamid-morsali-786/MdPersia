"""Offline TeX parsing and native MathML; no browser scripts or CDN required."""
from __future__ import annotations

import html
import re
from xml.etree import ElementTree as ET

from latex2mathml.converter import convert
from markdown_it import MarkdownIt
from mdit_py_plugins.dollarmath import dollarmath_plugin


def normalize_tex(source: str) -> str:
    # Accept Markdown-export escapes only inside an already parsed equation.
    source = re.sub(r"(?<!\\)\\[ \t]*(?=\n|$)", "", source)
    source = re.sub(r"\\_(?=\{)", "_", source)
    # This converter version loses the roman variant on single-letter \mathrm.
    source = re.sub(r"\\mathrm\{([A-Za-z])\}", r"{\\rm \1}", source)
    return source.strip().replace("’", "'")


def render_math(source: str, options: dict) -> str:
    try:
        result = convert(normalize_tex(source),
                         display="block" if options["display_mode"] else "inline")
        root = ET.fromstring(result)
        allowed = set(('math mrow mi mn mo mtext mspace ms mfrac msqrt mroot '
                       'mstyle merror mpadded mphantom mfenced menclose msub msup '
                       'msubsup munder mover munderover mmultiscripts mprescripts '
                       'none mtable mtr mtd mlabeledtr').split())
        for node in root.iter():
            if node.tag.endswith('}mi') and node.text in {'×', '÷', '±', '∓', '·', '⋅'}:
                node.tag = '{http://www.w3.org/1998/Math/MathML}mo'
            if node.tag.rsplit('}', 1)[-1] not in allowed:
                text = ''.join(node.itertext())
                node.clear()
                node.tag = '{http://www.w3.org/1998/Math/MathML}mtext'
                node.text = text
            for attribute in list(node.attrib):
                if attribute.lower().startswith('on') or attribute.rsplit('}', 1)[-1] in {
                    'href', 'src', 'style', 'mathcolor', 'mathbackground',
                }:
                    del node.attrib[attribute]
        ET.register_namespace('', 'http://www.w3.org/1998/Math/MathML')
        return ET.tostring(root, encoding='unicode')
    except Exception:
        # A malformed equation must not prevent reading the rest of a document.
        return '<code class="math-error" title="فرمول LaTeX معتبر نیست">' + html.escape(source) + '</code>'


def math_plugin(renderer: MarkdownIt) -> None:
    renderer.use(dollarmath_plugin, renderer=render_math, allow_labels=False,
                 allow_space=False, allow_digits=False)
