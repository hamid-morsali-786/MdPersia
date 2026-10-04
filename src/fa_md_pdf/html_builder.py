from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Final

from markdown_it import MarkdownIt

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


EMOJI_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"("
    r"[\U0001F000-\U0001FAFF]"
    r"|[\u2600-\u27BF]"
    r"|[\u2300-\u23FF]"
    r"|[\u2B00-\u2BFF]"
    r"|[\U0001F1E6-\U0001F1FF]"
    r"|[\u203C\u2049\u2122\u2139\u2194-\u2199\u21A9-\u21AA\u25AA-\u25AB\u25B6\u25C0\u25FB-\u25FE\u2934-\u2935]"
    r"|[\uFE0E\uFE0F]"
    r"|[\u200D]"
    r")+"
)


def strip_emojis(text: str) -> str:
    """Remove emojis and normalize surrounding spaces from text without removing newlines."""
    res = EMOJI_PATTERN.sub("", text)
    res = re.sub(r"[ \t]{2,}", " ", res)
    res = re.sub(r"\([ \t]+", "(", res)
    res = re.sub(r"[ \t]+\)", ")", res)
    res = re.sub(r"\|[ \t]{2,}", "| ", res)
    res = re.sub(r"[ \t]{2,}\|", " |", res)
    return res


@dataclass(frozen=True)
class HtmlDocument:
    html: str
    title: str
    has_mermaid: bool


def read_text_safely(path: Path) -> str:
    """Read Markdown files commonly produced on Windows editors."""
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text(encoding="cp1256")


def strip_front_matter(text: str) -> str:
    return FRONT_MATTER_RE.sub("", text, count=1)


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


def build_markdown_renderer() -> MarkdownIt:
    renderer = MarkdownIt(
        "default",
        {"html": True, "breaks": True, "typographer": True, "highlight": _highlight_code},
    )
    # These rules are commonly used in documentation Markdown.
    renderer.enable("table")
    renderer.enable("strikethrough")
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

    if not rules:
        return f"""
body {{
  font-family: {font_family};
}}
"""

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
    r"<blockquote>\s*<p>\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\](?:\s*<br\s*/?>|\s*\n)?\s*(.*?)(?=</blockquote>)",
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
    return PAGEBREAK_RE.sub(r'<div class="page-break"></div>', html_str)


def build_html(markdown_text: str, options: HtmlBuildOptions) -> HtmlDocument:
    if options.strip_emojis:
        markdown_text = strip_emojis(markdown_text)
    markdown_text = strip_front_matter(markdown_text)
    title = extract_title(markdown_text, options.source_path.stem)

    markdown_with_mermaid, has_mermaid = convert_mermaid_fences_to_html(markdown_text)
    renderer = build_markdown_renderer()
    body_html = renderer.render(markdown_with_mermaid)
    body_html = _transform_callouts(body_html, strip_emojis_flag=options.strip_emojis)
    body_html = _transform_pagebreaks(body_html)

    css = build_css(options)
    base_uri = directory_uri(options.source_path.parent)
    mermaid_script = build_mermaid_script(options, has_mermaid)

    document = f"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8">
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
