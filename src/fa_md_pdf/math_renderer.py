"""Offline TeX parsing and native MathML; no browser scripts or CDN required."""
from __future__ import annotations

import html
import re
from xml.etree import ElementTree as ET

from latex2mathml.converter import convert_to_element
from markdown_it import MarkdownIt
from mdit_py_plugins.dollarmath import dollarmath_plugin
from mdit_py_plugins.dollarmath.index import math_block_dollar


_SYMBOL_REFERENCE = re.compile(r"&#(?:x[0-9A-Fa-f]+|[0-9]+);")


def _decode_symbols(text: str) -> str:
    # The converter stores generated symbols as numeric references. Decode
    # those, then let XML serialization escape literal text and attributes.
    return _SYMBOL_REFERENCE.sub(lambda match: html.unescape(match[0]), text)


def normalize_tex(source: str) -> str:
    # Accept Markdown-export escapes only inside an already parsed equation.
    source = re.sub(r"(?<!\\)\\[ \t]*(?=\n|$)", "", source)
    source = re.sub(r"\\_(?=\{)", "_", source)
    # This converter version loses the roman variant on single-letter \mathrm.
    source = re.sub(r"\\mathrm\{([A-Za-z])\}", r"{\\rm \1}", source)
    # Translate environments to the converter's supported table forms.
    # Its bracket argument means column alignment, not the TeX baseline.
    source = re.sub(r"(\\begin\{(?:aligned|gathered)\})\s*\[[tcb]\]", r"\1", source)
    for original, supported in (
        ("aligned", "align*"), ("align", "align*"),
        ("gathered", "matrix"), ("gather", "matrix"), ("gather*", "matrix"),
    ):
        for boundary in ("begin", "end"):
            source = source.replace(rf"\{boundary}{{{original}}}", rf"\{boundary}{{{supported}}}")
    return source.strip().replace("’", "'")


def render_math(source: str, options: dict) -> str:
    try:
        root = convert_to_element(normalize_tex(source),
                                  display="block" if options["display_mode"] else "inline")
        allowed = set(('math mrow mi mn mo mtext mspace ms mfrac msqrt mroot '
                       'mstyle merror mpadded mphantom mfenced menclose msub msup '
                       'msubsup munder mover munderover mmultiscripts mprescripts '
                       'none mtable mtr mtd mlabeledtr').split())
        for node in root.iter():
            if node.text:
                node.text = _decode_symbols(node.text)
            if node.tag == 'mi' and node.text in {'×', '÷', '±', '∓', '·', '⋅'}:
                node.tag = 'mo'
            if node.tag not in allowed:
                text = ''.join(node.itertext())
                node.clear()
                node.tag = 'mtext'
                node.text = text
            for attribute in list(node.attrib):
                if attribute.lower().startswith('on') or attribute.rsplit('}', 1)[-1] in {
                    'href', 'src', 'style', 'mathcolor', 'mathbackground',
                }:
                    del node.attrib[attribute]
                else:
                    node.attrib[attribute] = _decode_symbols(node.attrib[attribute])
        result = ET.tostring(root, encoding='unicode')
        ET.fromstring(result)  # Reject invalid XML characters before returning it.
        return result
    except Exception:
        # A malformed equation must not prevent reading the rest of a document.
        return '<code class="math-error" title="فرمول LaTeX معتبر نیست">' + html.escape(source) + '</code>'


def math_plugin(renderer: MarkdownIt) -> None:
    renderer.use(dollarmath_plugin, renderer=render_math, allow_labels=False,
                 allow_space=False, allow_digits=False)
    original = math_block_dollar(allow_labels=False)

    def block(state, start, end, silent):
        matched = original(state, start, end, silent)
        if matched and not silent:
            token = state.tokens[-1]
            # The upstream rule slices raw source across lines, retaining quote
            # markers. Read the parser's adjusted line offsets inside containers.
            lines = [state.src[state.bMarks[i] + state.tShift[i]:state.eMarks[i]]
                     for i in range(start, state.line)]
            content = "\n".join(lines)[2:]
            token.content = content.rsplit("$$", 1)[0]
        return matched

    renderer.block.ruler.at("math_block", block)
