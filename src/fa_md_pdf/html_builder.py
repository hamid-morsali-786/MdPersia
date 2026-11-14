from __future__ import annotations
from .rtl_wrapper import classify_block_direction, detect_direction, has_persian, inline_prose, split_latin_field

import html
import json
import re
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Final

from mdit_py_plugins.footnote import footnote_plugin
from mdit_py_plugins.tasklists import tasklists_plugin
from markdown_it import MarkdownIt
from markdown_it.token import Token
from .math_renderer import math_plugin

DEFAULT_MERMAID_CDN: Final[str] = "https://cdn.jsdelivr.net/npm/mermaid@11.15.0/dist/mermaid.min.js"

MERMAID_FENCE_RE: Final[re.Pattern[str]] = re.compile(
    r"(?ms)(^|\n)(?P<fence>`{3,}|~{3,})[ \t]*mermaid[^\n]*\n(?P<code>.*?)(?:\n(?P=fence)[ \t]*(?=\n|$))"
)

FRONT_MATTER_RE: Final[re.Pattern[str]] = re.compile(
    r"\A---[ \t]*\r?\n.*?\r?\n---[ \t]*(?:\r?\n|$)",
    re.DOTALL,
)

H1_RE: Final[re.Pattern[str]] = re.compile(r"(?m)^\s*#\s+(.+?)\s*$")

VAZIRMATN_WEIGHTS: Final[dict[str, int]] = {
    "Thin": 100,
    "ExtraLight": 200,
    "Light": 300,
    "Regular": 400,
    "Medium": 500,
    "SemiBold": 600,
    "Bold": 700,
    "ExtraBold": 800,
    "Black": 900,
}


@dataclass(frozen=True)
class HtmlBuildOptions:
    source_path: Path
    font_family: str = "Vazirmatn"
    font_file: Path | None = None
    font_dir: Path | None = None
    custom_css: Path | None = None
    mermaid_source: str = DEFAULT_MERMAID_CDN
    mermaid_theme: str = "default"
    include_default_css: bool = True
    page_format: str = "A4"
    margin: str = "15mm"
    landscape: bool = False
    strip_emojis: bool = False
    preview_nonce: str | None = None


EMOJI_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"("
    r"[\U0001F000-\U0001FAFF]"
    r"|[\u2600-\u27BF]"
    r"|[\u2300-\u23FF]"
    r"|[\u2B00-\u2BFF]"
    r"|[\U0001F1E6-\U0001F1FF]"
    r"|[\u203C\u2049\u2122\u2139\u2194-\u2199\u21A9-\u21AA\u25AA-\u25AB\u25B6\u25C0\u25FB-\u25FE\u2934-\u2935]"
    r"|[\uFE0E\uFE0F]"
    r")+"
)


def strip_emojis(text: str) -> str:
    """Remove emojis and normalize spaces without removing newlines or Persian typography characters."""
    res = re.sub(r"[ \t]{2,}", " ", EMOJI_PATTERN.sub("", text))
    res = re.sub(r"\([ \t]+", "(", res)
    return re.sub(r"[ \t]+\)", ")", res)


@dataclass(frozen=True)
class HtmlDocument:
    html: str
    title: str
    has_mermaid: bool


def read_text_safely(path: Path) -> str:
    """Read Markdown files commonly produced on Windows editors."""
    from .document_io import decode_markdown, normalized_text
    return normalized_text(decode_markdown(path.read_bytes())[0])


def strip_front_matter(text: str) -> str:
    match = FRONT_MATTER_RE.match(text)
    if match and re.search(r"(?m)^[^\s:#][^:\n]*:(?:[ \t]|$)", match.group()):
        return text[match.end():]
    return text


def convert_mermaid_fences_to_html(text: str) -> tuple[str, bool]:
    """Replace ```mermaid fenced blocks with raw HTML blocks for Mermaid.js."""

    has_mermaid = False

    def repl(match: re.Match[str]) -> str:
        nonlocal has_mermaid
        has_mermaid = True
        code = match.group("code").strip()
        escaped = html.escape(code, quote=False)
        return f'\n\n<pre class="mermaid">\n{escaped}\n</pre>\n\n'

    return MERMAID_FENCE_RE.sub(repl, text), has_mermaid


def extract_title(markdown_text: str, fallback: str) -> str:
    match = H1_RE.search(markdown_text)
    if not match:
        return fallback
    cleaned = re.sub(r"[#*_`>\[\]()]","", match.group(1)).strip()
    return cleaned or fallback


def _highlight_code(code: str, lang: str, attrs: str) -> str:
    clean_lang = (lang or "").strip().lower().split()[0] if (lang or "").strip() else ""
    if not clean_lang:
        return ""
    try:
        from pygments import highlight
        from pygments.formatters import HtmlFormatter
        from pygments.lexers import get_lexer_by_name

        lexer = get_lexer_by_name(clean_lang, stripall=False)
        formatter = HtmlFormatter(nowrap=True)
        return highlight(code, lexer, formatter)
    except Exception:
        return ""


def _bidi_plugin(md: MarkdownIt) -> None:
    """
    Intelligently tags Markdown blocks with dir="rtl" or dir="ltr" attributes.
    Preserves RTL layout for bilingual sentences starting with Latin terms,
    while cleanly tagging pure English sections/headings/lists as LTR.
    """
    def rule(state):
        tokens = state.tokens
        prose = " ".join(inline_prose(token.children or []) for token in tokens if token.type == "inline")
        if prose.strip():
            state.env["document_direction"] = detect_direction(prose)
        lists: list[Token] = []
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token.type in ("bullet_list_close", "ordered_list_close"):
                lists.pop()

            # 1. Headings
            if token.type == "heading_open":
                if i + 1 < len(tokens) and tokens[i + 1].type == "inline":
                    token.attrSet("dir", classify_block_direction(inline_prose(tokens[i + 1].children or [])))

            # 2. Paragraphs (not nested inside lists to keep list items uniform)
            elif token.type == "paragraph_open":
                if i + 1 < len(tokens) and tokens[i + 1].type == "inline":
                    inline = tokens[i + 1]
                    if not lists:
                        token.attrSet("dir", classify_block_direction(inline_prose(inline.children or [])))
                    elif lists[-1].attrGet("dir") == "rtl" and token.level == lists[-1].level + 2:
                        field = split_latin_field(inline.children or [])
                        if field:
                            label, value = field
                            inline.meta["rtl_field"] = True
                            inline.children = [Token("field_label_open", "bdi", 1), *label,
                                               Token("field_separator", "", 0), *value,
                                               Token("field_value_close", "bdi", -1)]

            # 3. Lists (ul / ol)
            elif token.type in ("bullet_list_open", "ordered_list_open"):
                list_tokens = []
                j = i + 1
                depth = 1
                while j < len(tokens):
                    if tokens[j].type == token.type:
                        depth += 1
                    elif tokens[j].type == token.type.replace("_open", "_close"):
                        depth -= 1
                        if depth == 0:
                            break
                    list_tokens.append(tokens[j])
                    j += 1
                all_text = " ".join(inline_prose(t.children or []) for t in list_tokens if t.type == "inline")
                token.attrSet("dir", classify_block_direction(all_text))
                lists.append(token)

            # 4. Tables
            elif token.type == "table_open":
                table_tokens = []
                j = i + 1
                depth = 1
                while j < len(tokens):
                    if tokens[j].type == "table_open":
                        depth += 1
                    elif tokens[j].type == "table_close":
                        depth -= 1
                        if depth == 0:
                            break
                    table_tokens.append(tokens[j])
                    j += 1
                all_text = " ".join(inline_prose(t.children or []) for t in table_tokens if t.type == "inline")
                token.attrSet("dir", classify_block_direction(all_text))

            # 5. Blockquotes
            elif token.type == "blockquote_open":
                bq_tokens = []
                j = i + 1
                depth = 1
                while j < len(tokens):
                    if tokens[j].type == "blockquote_open":
                        depth += 1
                    elif tokens[j].type == "blockquote_close":
                        depth -= 1
                        if depth == 0:
                            break
                    bq_tokens.append(tokens[j])
                    j += 1
                all_text = " ".join(inline_prose(t.children or []) for t in bq_tokens if t.type == "inline")
                token.attrSet("dir", classify_block_direction(all_text))

            # 6. Code blocks / fences (always LTR)
            elif token.type in ("fence", "code_block"):
                token.attrSet("dir", "ltr")

            i += 1

    md.core.ruler.push("bidi_plugin", rule)


def build_markdown_renderer(*, source_path: Path | None = None) -> MarkdownIt:
    renderer = MarkdownIt(
        "default",
        {"html": True, "breaks": True, "typographer": True, "highlight": _highlight_code},
    )
    # These rules are commonly used in documentation Markdown.
    renderer.enable("table")
    renderer.enable("strikethrough")
    renderer.use(footnote_plugin)
    renderer.use(tasklists_plugin)
    renderer.renderer.rules.update({
        "field_label_open": lambda *_: '<bdi dir="ltr">',
        "field_separator": lambda *_: '</bdi> <bdi dir="auto">',
        "field_value_close": lambda *_: '</bdi>',
    })
    original_fence = renderer.renderer.rules["fence"]

    def fence(tokens, index, options, env):
        token = tokens[index]
        if token.info.strip().lower() == "mermaid":
            env["has_mermaid"] = True
            return '<pre class="mermaid">\n' + html.escape(token.content.strip()) + '\n</pre>\n'
        return original_fence(tokens, index, options, env)

    renderer.renderer.rules["fence"] = fence
    renderer.add_render_rule("table_open", lambda self, tokens, i, options, env:
                             '<div class="md-table-scroll">' + self.renderToken(tokens, i, options, env))
    renderer.add_render_rule("table_close", lambda self, tokens, i, options, env:
                             self.renderToken(tokens, i, options, env) + '</div>\n')

    def heading_ids(state):
        used = set()
        for index, token in enumerate(state.tokens[:-1]):
            if token.type != "heading_open":
                continue
            children = state.tokens[index + 1].children or []
            label = "".join(t.content for t in children if t.type in {"text", "code_inline", "image"})
            if token.tag == "h1" and label:
                state.env.setdefault("document_title", "".join(t.content for t in children
                        if t.type in {"text", "code_inline", "image", "html_inline"}))
            stem = re.sub(r"[^\w\- \u200c]", "", label.lower()).strip().replace(" ", "-") or "section"
            slug, suffix = stem, 0
            while slug in used:
                suffix += 1
                slug = f"{stem}-{suffix}"
            used.add(slug)
            token.attrSet("id", slug)

    renderer.core.ruler.push("heading_ids", heading_ids)
    math_plugin(renderer)
    if source_path and source_path.suffix.lower() == ".mdx":
        from .mdx import static_mdx_plugin
        renderer.use(static_mdx_plugin)
    _bidi_plugin(renderer)
    return renderer


def directory_uri(path: Path) -> str:
    uri = path.resolve().as_uri()
    if not uri.endswith("/"):
        uri += "/"
    return uri


def to_mermaid_source(value: str) -> str:
    if value.startswith(("https://", "http://", "file://")):
        return value

    candidate = Path(value)
    if candidate.exists():
        return candidate.resolve().as_uri()

    # Keep the value as-is so the browser can report a useful loading error.
    return value


def load_default_css() -> str:
    return resources.files("fa_md_pdf.assets").joinpath("default.css").read_text(encoding="utf-8")


def _build_single_font_file_css(font_family: str, font_file: Path) -> str:
    font_uri = font_file.resolve().as_uri()
    return f"""
@font-face {{
  font-family: "FaMdPdfCustomFont";
  src: url("{font_uri}") format("truetype");
  font-weight: 400;
  font-style: normal;
}}

body {{
  font-family: "FaMdPdfCustomFont", {font_family};
}}
"""


def _build_vazirmatn_font_dir_css(font_family: str, font_dir: Path) -> str:
    rules: list[str] = []

    for label, weight in VAZIRMATN_WEIGHTS.items():
        font_file = font_dir / f"Vazirmatn-{label}.ttf"
        if not font_file.is_file():
            continue

        rules.append(
            f"""
@font-face {{
  font-family: "Vazirmatn";
  src: url("{font_file.resolve().as_uri()}") format("truetype");
  font-weight: {weight};
  font-style: normal;
}}
"""
        )

    rules.append(
        f"""
body {{
  font-family: {font_family};
}}
"""
    )
    return "\n".join(rules)


def build_font_css(font_family: str, font_file: Path | None, font_dir: Path | None) -> str:
    if font_file:
        return _build_single_font_file_css(font_family, font_file)

    if font_dir and font_dir.is_dir():
        return _build_vazirmatn_font_dir_css(font_family, font_dir)

    return f"""
body {{
  font-family: {font_family};
}}
"""


def build_css(options: HtmlBuildOptions) -> str:
    css_parts: list[str] = []
    # Dynamic @page rule matching user margin and page format
    orient = " landscape" if options.landscape else " portrait"
    page_css = f"@page {{\n  size: {options.page_format}{orient};\n  margin: {options.margin};\n}}"
    css_parts.append(page_css)

    if options.include_default_css:
        css_parts.append(load_default_css())

    css_parts.append(build_font_css(options.font_family, options.font_file, options.font_dir))

    if options.custom_css:
        css_parts.append(options.custom_css.read_text(encoding="utf-8-sig"))

    return "\n\n".join(css_parts)


def build_mermaid_script(options: HtmlBuildOptions, has_mermaid: bool) -> str:
    if not has_mermaid:
        return """
<script>
window.__FA_MD_PDF_READY = true;
window.__FA_MD_PDF_MERMAID_ERROR = null;
</script>
"""

    mermaid_src = html.escape(to_mermaid_source(options.mermaid_source), quote=True)
    mermaid_config = {
        "startOnLoad": False,
        "theme": options.mermaid_theme,
        "securityLevel": "strict",
        "htmlLabels": True,
        "fontFamily": options.font_family,
    }
    config_json = json.dumps(mermaid_config, ensure_ascii=False)

    return f"""
<script src="{mermaid_src}"></script>
<script>
window.__FA_MD_PDF_READY = false;
window.__FA_MD_PDF_MERMAID_ERROR = null;

(async function () {{
  try {{
    if (!window.mermaid) {{
      throw new Error("Mermaid library was not loaded. In offline mode, make sure vendor/mermaid.min.js exists or pass --mermaid-js PATH.");
    }}
    window.mermaid.initialize({config_json});
    await window.mermaid.run({{ querySelector: ".mermaid" }});
  }} catch (error) {{
    window.__FA_MD_PDF_MERMAID_ERROR = String((error && error.stack) || error);
  }} finally {{
    window.__FA_MD_PDF_READY = true;
  }}
}})();
</script>
"""


CALLOUT_TITLES: Final[dict[str, tuple[str, str]]] = {
    "NOTE": ("callout-note", "💡 نکته"),
    "TIP": ("callout-tip", "💡 راهنما"),
    "IMPORTANT": ("callout-important", "📌 مهم"),
    "WARNING": ("callout-warning", "⚠️ هشدار"),
    "CAUTION": ("callout-caution", "🛑 احتیاط"),
}

CALLOUT_TITLES_PLAIN: Final[dict[str, tuple[str, str]]] = {
    "NOTE": ("callout-note", "نکته"),
    "TIP": ("callout-tip", "راهنما"),
    "IMPORTANT": ("callout-important", "مهم"),
    "WARNING": ("callout-warning", "هشدار"),
    "CAUTION": ("callout-caution", "احتیاط"),
}

CALLOUT_RE: Final[re.Pattern[str]] = re.compile(
    r"<blockquote\b[^>]*>\s*<p\b[^>]*>\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\](?:\s*<br\s*/?>|\s*\n)?\s*(.*?)(?=</blockquote>)",
    re.IGNORECASE | re.DOTALL,
)

PAGEBREAK_RE: Final[re.Pattern[str]] = re.compile(
    r"<!--\s*page-?break\s*-->|\\pagebreak",
    re.IGNORECASE,
)


def _transform_callouts(html_str: str, strip_emojis_flag: bool = False) -> str:
    titles = CALLOUT_TITLES_PLAIN if strip_emojis_flag else CALLOUT_TITLES

    def repl(m: re.Match[str]) -> str:
        callout_type = m.group(1).upper()
        content = m.group(2)
        cls_name, title_fa = titles.get(
            callout_type, (f"callout-{callout_type.lower()}", callout_type)
        )
        return (
            f'<blockquote class="callout {cls_name}">\n'
            f'<div class="callout-title">{title_fa}</div>\n'
            f'<p>{content}'
        )

    return CALLOUT_RE.sub(repl, html_str)


def _transform_pagebreaks(html_str: str) -> str:
    # Preserve the literal contents of code examples and highlighted fences.
    parts = re.split(r"(<pre\b[^>]*>.*?</pre>|<code\b[^>]*>.*?</code>)", html_str,
                     flags=re.IGNORECASE | re.DOTALL)
    return "".join(part if index % 2 else PAGEBREAK_RE.sub('<div class="page-break"></div>', part)
                   for index, part in enumerate(parts))


def _fix_li_inner(content: str) -> str:
    lead_ws = content[:len(content) - len(content.lstrip())]
    trail_ws = content[len(content.rstrip()):]
    inner = content.strip()
    if not inner:
        return content
    if inner.startswith('<bdi dir="ltr">'):
        return content  # The token renderer already isolated both parts of this field.

    # Loose list items contain blocks; bdi may only wrap phrasing content.
    if re.search(r"<(?:p|pre|div|blockquote|table|h[1-6]|hr|section|figure)\b", inner, re.I):
        return re.sub(r"(<p\b[^>]*>)(.*?)(</p>)",
                      lambda m: m[1] + _fix_li_inner(m[2]) + m[3],
                      content, flags=re.I | re.S)

    if not has_persian(inner):
        return f"{lead_ws}<bdi>{inner}</bdi>{trail_ws}"

    # Has Persian: check if it opens with a Latin key + colon
    m1 = re.match(r"^(\s*<code>[A-Za-z0-9_.-]+</code>\s*:\s*)(.*)$", inner, re.DOTALL)
    if m1:
        return f"{lead_ws}<bdi>{m1.group(1).rstrip()}</bdi> {m1.group(2).lstrip()}{trail_ws}"

    m2 = re.match(r"^(\s*<code>[A-Za-z0-9_.-]+:\s*</code>)(.*)$", inner, re.DOTALL)
    if m2:
        return f"{lead_ws}<bdi>{m2.group(1).rstrip()}</bdi> {m2.group(2).lstrip()}{trail_ws}"

    m3 = re.match(r"^(\s*<strong>[A-Za-z0-9_.-]+(?::</strong>|</strong>\s*:)\s*)(.*)$", inner, re.DOTALL)
    if m3:
        return f"{lead_ws}<bdi>{m3.group(1).rstrip()}</bdi> {m3.group(2).lstrip()}{trail_ws}"

    m4 = re.match(r"^(\s*[A-Za-z0-9_.-]+\s*:\s*)(.*)$", inner, re.DOTALL)
    if m4:
        return f"{lead_ws}<bdi>{m4.group(1).rstrip()}</bdi> {m4.group(2).lstrip()}{trail_ws}"

    return content


def fix_bidi_list_items(html_content: str) -> str:
    """
    Ensure list items in RTL contexts properly isolate leading Latin keys/codes with colons,
    and ensure pure Latin list items inside RTL lists render cleanly without colon inversion.
    Handles nested lists without breaking HTML hierarchy.
    """
    tokens = re.split(r"(</li>|<li\b[^>]*>|<ul\b[^>]*>|</ul>|<ol\b[^>]*>|</ol>)", html_content, flags=re.IGNORECASE)
    result = []
    in_li_direct = False

    for token in tokens:
        lower = token.lower()
        if lower.startswith("<li"):
            result.append(token)
            in_li_direct = True
        elif lower == "</li>":
            in_li_direct = False
            result.append(token)
        elif lower.startswith("<ul") or lower.startswith("<ol"):
            in_li_direct = False
            result.append(token)
        elif in_li_direct and token.strip():
            result.append(_fix_li_inner(token))
            in_li_direct = False
        else:
            result.append(token)

    return "".join(result)


def build_html(markdown_text: str, options: HtmlBuildOptions) -> HtmlDocument:
    if options.strip_emojis:
        markdown_text = strip_emojis(markdown_text)
    markdown_text = strip_front_matter(markdown_text)


    renderer = build_markdown_renderer(source_path=options.source_path)
    env = {}
    body_html = renderer.render(markdown_text, env)
    has_mermaid = bool(env.get("has_mermaid"))
    title = env.get("document_title", options.source_path.stem)
    body_html = _transform_callouts(body_html, strip_emojis_flag=options.strip_emojis)
    body_html = _transform_pagebreaks(body_html)
    body_html = fix_bidi_list_items(body_html)
    if options.source_path.suffix.lower() == ".mdx":
        from .mdx import MDX_NOTICE
        body_html = '<blockquote dir="rtl" role="note">' + html.escape(MDX_NOTICE) + '</blockquote>\n' + body_html

    css = build_css(options)
    base_uri = directory_uri(options.source_path.parent)
    mermaid_script = build_mermaid_script(options, has_mermaid)
    preview_policy = ""
    if options.preview_nonce:
        nonce = html.escape(options.preview_nonce, quote=True)
        mermaid_script = mermaid_script.replace("<script", f'<script nonce="{nonce}"')
        preview_policy = f'''<meta http-equiv="Content-Security-Policy" content="script-src 'nonce-{nonce}'; object-src 'none'; frame-src 'none'; form-action 'none'">'''

    doc_dir = env.get("document_direction") or detect_direction(markdown_text)
    doc_lang = "fa" if doc_dir == "rtl" else "en"

    document = f"""<!doctype html>
<html lang="{doc_lang}" dir="{doc_dir}">
<head>
  <meta charset="utf-8">
  {preview_policy}
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <base href="{html.escape(base_uri, quote=True)}">
  <title>{html.escape(title)}</title>
  <style>
{css}
  </style>
</head>
<body>
  <main class="markdown-body">
{body_html}
  </main>
{mermaid_script}
</body>
</html>
"""
    return HtmlDocument(html=document, title=title, has_mermaid=has_mermaid)
