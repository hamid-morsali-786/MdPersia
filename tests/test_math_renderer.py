from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from fa_md_pdf.html_builder import build_markdown_renderer, build_html, HtmlBuildOptions
from fa_md_pdf.math_renderer import normalize_tex, render_math

FIXTURE = Path(__file__).parent / 'fixtures/math-bilingual.md'


def test_user_equations_survive_markdown_and_form_real_mathml():
    document = build_html(FIXTURE.read_text(encoding='utf-8'), HtmlBuildOptions(source_path=FIXTURE))
    import re
    equations = re.findall(r'<math\b.*?</math>', document.html, re.S)
    assert len(equations) == 10
    ns = {'m': 'http://www.w3.org/1998/Math/MathML'}
    roots = [ET.fromstring(equation) for equation in equations]
    assert sum(len(root.findall('.//m:mfrac', ns)) for root in roots) == 8
    assert sum(len(root.findall('.//m:menclose', ns)) for root in roots) == 3
    assert roots[1].find('.//m:msub', ns) is not None
    assert any(node.text == '×' for node in roots[1].findall('.//m:mo', ns))
    assert any(node.text == 's' and node.get('mathvariant') == 'normal'
               for node in roots[1].findall('.//m:mi', ns))
    assert '<script src=' not in document.html  # No math CDN or startup script.
    assert 'math-error' not in document.html.split('<body>')[1]


def test_code_escaped_dollars_and_currency_remain_literal():
    renderer = build_markdown_renderer()
    result = renderer.render('`$x$`\n\n```tex\n$$x$$\n```\n\n\\$x$ costs $5 and $10.')
    assert '<math' not in result
    assert '<span class="sb">$$</span>' in result


def test_normalization_is_limited_to_export_artifacts_inside_equations():
    assert normalize_tex('\\\n'+r't\_{\rm tx}=x’'+'\\\n') == r"t_{\rm tx}=x'"
    assert normalize_tex(r'\text{file\_name}\\x') == r'\text{file\_name}\\x'


def test_math_text_cannot_inject_html():
    result = build_markdown_renderer().render(r'$\text{<script>alert(1)</script>}$')
    assert '<script>' not in result
    assert '<math' in result


def test_invalid_formula_does_not_hide_following_paragraph():
    result = build_markdown_renderer().render('$$\n\\frac{\n$$\n\nپایان سند')
    assert 'math-error' in result
    assert 'پایان سند' in result


def test_aligned_equations_keep_rows_alignment_and_boxed_result():
    source = r"""متن فارسی

$$
\begin{aligned}
\gamma &= 10^{20/10}=100\\
C &= 500\,000\log_2(101)
\approx 3\,329\,106\ \mathrm{bit/s}
\approx \boxed{3.329\ \mathrm{Mbit/s}}
\end{aligned}
$$
"""
    import re
    result = build_markdown_renderer().render(source)
    assert 'math-error' not in result
    math = ET.fromstring(re.search(r'<math\b.*?</math>', result, re.S).group())
    ns = {'m': 'http://www.w3.org/1998/Math/MathML'}
    rows = math.findall('.//m:mtable/m:mtr', ns)
    assert len(rows) == 2
    for row, symbol in zip(rows, ('γ', 'C'), strict=True):
        left, right = row.findall('m:mtd', ns)
        assert ''.join(left.itertext()) == symbol
        assert (left.get('columnalign'), right.get('columnalign')) == ('right', 'left')
        assert ''.join(right.itertext()).startswith('=')
    assert rows[1].find('.//m:menclose', ns) is not None


@pytest.mark.parametrize('source, columns', [
    (r'\begin{aligned}[t]a&=b\\c&=d\end{aligned}', 2),
    (r'\begin{align}a&=b\\c&=d\end{align}', 2),
    (r'\begin{gathered}a=b\\c=d\end{gathered}', 1),
    (r'\begin{gather*}a=b\\c=d\end{gather*}', 1),
])
def test_multiline_environments_preserve_table_shape(source, columns):
    root = ET.fromstring(render_math(source, {'display_mode': True}))
    ns = {'m': 'http://www.w3.org/1998/Math/MathML'}
    rows = root.findall('.//m:mtable/m:mtr', ns)
    assert len(rows) == 2
    assert all(len(row.findall('m:mtd', ns)) == columns for row in rows)
    assert [''.join(row.itertext()) for row in rows] == ['a=b', 'c=d']


def test_literal_xml_characters_in_formula_text_stay_visible_and_safe():
    result = render_math(r'\text{A & B < C > D}', {'display_mode': False})
    root = ET.fromstring(result)
    assert root.tag == '{http://www.w3.org/1998/Math/MathML}math'
    assert ''.join(root.itertext()).replace('\u00a0', ' ') == 'A & B < C > D'
