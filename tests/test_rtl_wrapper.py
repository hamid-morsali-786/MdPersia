"""
Tests for RTL Markdown wrapping and output path resolution.
Verifies edge cases, idempotency, YAML frontmatter, and CLI suffix handling.
"""

from pathlib import Path
import pytest
from fa_md_pdf.rtl_wrapper import wrap_rtl_in_markdown, WrapOptions
from fa_md_pdf.cli import _resolve_wrap_rtl_output


def test_cli_output_resolution_suffix_no_double_extension():
    """Verify that .rtl.md suffix does not create .rtl.md.md."""
    source = Path("document.md")
    
    # Passing .rtl.md
    out1 = _resolve_wrap_rtl_output(source, None, None, ".rtl.md")
    assert out1.name == "document.rtl.md"
    
    # Passing .rtl
    out2 = _resolve_wrap_rtl_output(source, None, None, ".rtl")
    assert out2.name == "document.rtl.md"
    
    # Passing rtl (without dot)
    out3 = _resolve_wrap_rtl_output(source, None, None, "rtl")
    assert out3.name == "document.rtl.md"
    
    # Passing empty string (overwrite)
    out4 = _resolve_wrap_rtl_output(source, None, None, "")
    assert out4.name == "document.md"


def test_cli_output_resolution_with_output_dir_applies_suffix():
    """Verify that when an output directory is specified, the suffix is not dropped."""
    source = Path("docs/guide.md")
    out_dir = Path("dist")
    
    # Single file with output dir and .rtl suffix
    res = _resolve_wrap_rtl_output(source, out_dir, None, ".rtl")
    assert res == out_dir / "guide.rtl.md"
    
    # Single file with output dir and .rtl.md suffix
    res_md = _resolve_wrap_rtl_output(source, out_dir, None, ".rtl.md")
    assert res_md == out_dir / "guide.rtl.md"
    
    # Directory mode with relative structure and suffix
    input_root = Path("docs")
    res_dir = _resolve_wrap_rtl_output(source, out_dir, input_root, ".rtl")
    assert res_dir == out_dir / "guide.rtl.md"


def test_wrap_rtl_preserves_yaml_frontmatter():
    """YAML frontmatter with Persian text must NOT be wrapped inside <div dir='rtl'>."""
    doc = """---
title: راهنمای سیستم
author: علی رضایی
---

# عنوان اصلی

متن پاراگراف فارسی.
"""
    result = wrap_rtl_in_markdown(doc)
    assert result.startswith("---\ntitle: راهنمای سیستم\nauthor: علی رضایی\n---")
    assert '<div dir="rtl">\n\n---' not in result


def test_wrap_rtl_multiline_existing_div_idempotent():
    """An existing multiline <div dir='rtl'> must not be doubly wrapped or corrupted."""
    doc = """<div dir="rtl">
پاراگراف یک

پاراگراف دو
</div>"""
    result = wrap_rtl_in_markdown(doc)
    assert result.count('<div dir="rtl">') == 1
    assert result.count('</div>') == 1


def test_wrap_rtl_preserves_fenced_code_blocks():
    """Code blocks containing Persian comments must remain untouched."""
    doc = """# راهنما

```python
# تابع چاپ پیام فارسی
def greet():
    print("سلام دنیا")
```

متن پس از کد.
"""
    result = wrap_rtl_in_markdown(doc)
    assert "```python\n# تابع چاپ پیام فارسی\ndef greet():\n    print(\"سلام دنیا\")\n```" in result
    assert '<div dir="rtl">\n\n```python' not in result


def test_wrap_rtl_preserves_math_blocks():
    """Math blocks ($$ ... $$) must not be wrapped inside RTL divs."""
    doc = """# فرمول ریاضی

$$
E = mc^2
$$

متن پایانی.
"""
    result = wrap_rtl_in_markdown(doc)
    assert "$$\nE = mc^2\n$$" in result
    assert '<div dir="rtl">\n\n$$' not in result
