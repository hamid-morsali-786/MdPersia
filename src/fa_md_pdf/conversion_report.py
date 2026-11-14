"""Per-conversion diagnostics, shared by CLI and the desktop log stream."""
from __future__ import annotations

import json
import sys
from inspect import signature
from itertools import islice
from contextvars import ContextVar
from dataclasses import asdict, dataclass
from functools import wraps


@dataclass(frozen=True)
class ConversionIssue:
    code: str
    message: str
    line: int | None = None
    suggestion: str | None = None


_current: ContextVar[list[ConversionIssue] | None] = ContextVar('conversion_issues', default=None)


def warn(code, message, line=None, suggestion=None):
    issues = _current.get()
    issue = ConversionIssue(code, message, line, suggestion)
    if issues is not None and issue not in issues:
        issues.append(issue)


def preflight(job, options):
    from .html_builder import build_markdown_renderer, read_text_safely, strip_front_matter
    from .math_renderer import render_math
    from .local_images import resolve_image_file
    from .word_document import parse_docx_length, PAGE_FORMAT_DIMENSIONS
    from html.parser import HTMLParser

    class Images(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag == 'img':
                check_image(dict(attrs).get('src', ''))

    line = None

    def check_image(src):
        if src.startswith(('http:', 'https:')):
            warn('image.remote', 'تصویر اینترنتی برای خروجی آفلاین قابل اتکا نیست.', line,
                 'تصویر را کنار سند ذخیره و از مسیر محلی استفاده کنید.')
        elif resolve_image_file(src, job.source) is None:
            warn('image.missing', f'تصویر محلی پیدا نشد: {src}', line, 'مسیر تصویر را اصلاح کنید.')
        elif options.output_format == 'docx' and src.lower().endswith('.svg'):
            warn('image.svg', 'درج مستقیم SVG در Word پشتیبانی نمی‌شود.', line,
                 'نسخه PNG تصویر را استفاده کنید.')

    text = read_text_safely(job.source)
    stripped = strip_front_matter(text)
    offset = len(text.splitlines()) - len(stripped.splitlines())
    tokens = build_markdown_renderer(source_path=job.source).parse(stripped)
    if job.source.suffix.lower() == ".mdx":
        from .mdx import MDX_NOTICE
        warn("mdx.static", MDX_NOTICE)
    for token in tokens:
        line = token.map[0] + 1 + offset if token.map else None
        for node in [token, *(token.children or [])]:
            if node.type in {'math_block', 'math_inline'}:
                if render_math(node.content, {'display_mode': node.type == 'math_block'}).startswith('<code'):
                    warn('math.invalid', 'فرمول نامعتبر است؛ متن آن حفظ می‌شود.', line,
                         'دستورها و آکولادهای LaTeX را بررسی کنید.')
            elif node.type == 'image':
                check_image(node.attrGet('src') or '')
            elif node.type in {'html_inline', 'html_block'}:
                Images().feed(node.content)
    dims = PAGE_FORMAT_DIMENSIONS.get(options.page_format.upper(), (210, 297))
    width = dims[1 if options.landscape else 0] - 2 * parse_docx_length(options.margin).mm
    if width < 80:
        warn('layout.narrow', 'عرض قابل استفاده کاغذ بسیار کم است.', suggestion='حاشیه را کمتر کنید یا کاغذ بزرگ‌تر انتخاب کنید.')
    for index, token in enumerate(tokens):
        if token.type == 'tr_open':
            cells = 0
            for cell in islice(tokens, index + 1, None):
                if cell.type == 'tr_close':
                    break
                cells += cell.type in {'td_open', 'th_open'}
            if cells and width / cells < 18:
                warn('layout.table', 'ستون‌های جدول در کاغذ انتخاب‌شده باریک خواهند بود.',
                     suggestion='جهت افقی یا کاغذ بزرگ‌تر انتخاب کنید.')
                break


def report_conversion(function):
    parameters = signature(function)

    @wraps(function)
    def wrapper(*args, **kwargs):
        arguments = parameters.bind(*args, **kwargs)
        arguments.apply_defaults()
        job = arguments.arguments['job']
        options = arguments.arguments['options']
        issues = []
        token = _current.set(issues)
        error = None
        try:
            preflight(job, options)
            function(*args, **kwargs)
            return tuple(issues)
        except Exception as exc:
            error = str(exc)
            raise
        finally:
            _current.reset(token)
            report = job.output.with_name(job.output.name + '.report.json')
            saved = False
            if issues or error or report.exists():
                payload = {'version': 1, 'source': str(job.source), 'output': str(job.output),
                           'ok': error is None, 'error': error,
                           'issues': [asdict(issue) for issue in issues]}
                try:
                    report.parent.mkdir(parents=True, exist_ok=True)
                    temp = report.with_suffix(report.suffix + '.tmp')
                    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf8')
                    temp.replace(report)
                    saved = True
                except OSError as exc:
                    print(f'WARN گزارش تبدیل ذخیره نشد: {exc}', file=sys.stderr)
            for issue in issues[:10]:
                detail = ' '.join(issue.message.split())
                hint = ' ' + issue.suggestion if issue.suggestion else ''
                location = f':{issue.line}' if issue.line else ''
                print(f'WARN [{issue.code}] {job.source}{location}: {detail}{hint}', file=sys.stderr)
            if issues:
                location = f'گزارش کامل: {report}' if saved else 'گزارش فقط در کنسول ثبت شد'
                print(f'WARN [report] {len(issues)} مورد؛ {location}', file=sys.stderr)
    return wrapper
