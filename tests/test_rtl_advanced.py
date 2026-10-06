"""
Advanced tests for RTL wrapper: Persian Unicode boundaries, ZWNJ/ZWJ,
min_persian_chars threshold, nested fences, idempotency, and file writing.
"""

from __future__ import annotations

from pathlib import Path
import pytest

from fa_md_pdf.rtl_wrapper import (
    WrapOptions,
    count_persian,
    has_persian,
    wrap_rtl_in_file,
    wrap_rtl_in_markdown,
)


def test_has_persian_and_count_persian_unicode_ranges():
    # Standard Persian letters
    assert has_persian("گچپژکی") is True
    assert count_persian("گچپژکی") == 6

    # ZWNJ (\u200C) and ZWJ (\u200D)
    assert has_persian("کتاب\u200cها") is True
    assert count_persian("کتاب\u200cها") == 7

    # Arabic Presentation Forms
    assert has_persian("\uFB8A\uFE8E") is True

    # English, digits, punctuation, and emojis
    assert has_persian("Hello World! 12345 🚀 :)") is False
    assert count_persian("Hello World! 12345 🚀 :)") == 0


def test_min_persian_chars_threshold():
    text = "English sentence with یک Persian word."
    persian_chars_count = count_persian(text)
    assert persian_chars_count == 2

    # Threshold set to 3: should not wrap
    opts_strict = WrapOptions(enabled=True, min_persian_chars=3)
    res_strict = wrap_rtl_in_markdown(text, opts_strict)
    assert '<div dir="rtl">' not in res_strict

    # Threshold set to 2: should wrap
    opts_lenient = WrapOptions(enabled=True, min_persian_chars=2)
    res_lenient = wrap_rtl_in_markdown(text, opts_lenient)
    assert '<div dir="rtl">' in res_lenient


def test_wrap_rtl_idempotency_multi_pass():
    doc = """# عنوان مستند

این یک پاراگراف فارسی است.

```python
# کد پایتون
print("سلام")
```

پاراگراف دوم فارسی.
"""
    pass1 = wrap_rtl_in_markdown(doc)
    pass2 = wrap_rtl_in_markdown(pass1)
    pass3 = wrap_rtl_in_markdown(pass2)

    assert pass1 == pass2
    assert pass2 == pass3
    assert pass1.count('<div dir="rtl">') == 3


def test_wrap_rtl_nested_and_long_fences():
    doc = """````markdown
```python
# داخل کد بلاک تو در تو
x = 1
```
````

متن فارسی پس از کد.
"""
    wrapped = wrap_rtl_in_markdown(doc)
    assert '<div dir="rtl">\n\n````markdown' not in wrapped
    assert '<div dir="rtl">\n\nمتن فارسی پس از کد.' in wrapped


def test_wrap_rtl_empty_and_whitespace():
    assert wrap_rtl_in_markdown("") == ""
    assert wrap_rtl_in_markdown("   \n\n\t  \n") == "   \n\n\t  \n"


def test_wrap_rtl_preserves_trailing_newline():
    doc_with_nl = "متن فارسی\n"
    res_with_nl = wrap_rtl_in_markdown(doc_with_nl)
    assert res_with_nl.endswith("\n")

    doc_no_nl = "متن فارسی"
    res_no_nl = wrap_rtl_in_markdown(doc_no_nl)
    assert '<div dir="rtl">' in res_no_nl


def test_wrap_rtl_in_file(tmp_path: Path):
    source = tmp_path / "input.md"
    source.write_text("# عنوان\n\nمتن فارسی", encoding="utf-8")

    # 1. Default destination (creates input.rtl.md)
    dest_default = wrap_rtl_in_file(source)
    assert dest_default == tmp_path / "input.rtl.md"
    assert dest_default.is_file()
    assert '<div dir="rtl">' in dest_default.read_text(encoding="utf-8")

    # 2. Explicit destination in nested non-existent directory
    dest_custom = tmp_path / "sub" / "output.md"
    wrap_rtl_in_file(source, destination=dest_custom)
    assert dest_custom.is_file()
    assert '<div dir="rtl">' in dest_custom.read_text(encoding="utf-8")
