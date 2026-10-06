"""Pytest fixtures and environment configuration for fa-md-pdf tests."""

from __future__ import annotations

import base64
import os
from pathlib import Path
import pytest

from fa_md_pdf.defaults import find_project_root, set_playwright_browsers_path


@pytest.fixture(autouse=True)
def configure_playwright_browsers():
    """Ensure PLAYWRIGHT_BROWSERS_PATH is set to the project browsers directory if present."""
    root = find_project_root()
    browsers_dir = root / "browsers"
    original = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if browsers_dir.is_dir():
        set_playwright_browsers_path(browsers_dir, force=True)
    yield
    if original is not None:
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = original
    elif browsers_dir.is_dir():
        set_playwright_browsers_path(browsers_dir, force=True)


@pytest.fixture
def repo_root() -> Path:
    return find_project_root()


@pytest.fixture
def vendor_mermaid(repo_root: Path) -> Path:
    return repo_root / "vendor" / "mermaid.min.js"


@pytest.fixture
def sample_png_bytes() -> bytes:
    # 1x1 transparent PNG
    b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    return base64.b64decode(b64)


@pytest.fixture
def complex_persian_markdown() -> str:
    return """---
title: سند جامع آزمایشی
author: تیم فنی
version: 1.0.0
---

# سامانه جامع آزمایشی

این یک سند آزمایشی کامل برای اعتبارسنجی کیفیت و پایداری تبدیل متون فارسی به PDF و DOCX است.

## ۱. نکات و راهنماها

> [!NOTE]
> این یک یادداشت مهم درباره معماری سیستم است.
> جزئیات بیشتر در مستندات پیوست آمده است.

> [!WARNING]
> توجه: تغییر در تنظیمات شبکه ممکن است اتصال را قطع کند!

> [!TIP]
> برای سرعت بیشتر، از حالت کش محلی استفاده کنید.

## ۲. دیاگرام جریان کاری

```mermaid
graph TD
    A[شروع فرآیند] --> B{آیا داده معتبر است؟}
    B -- بله --> C[ذخیره در پایگاه داده]
    B -- خیر --> D[ثبت خطا در لاگ]
    C --> E[پایان موفق]
    D --> E
```

## ۳. قطعه کد نمونه

```python
def process_persian_text(text: str) -> str:
    # پردازش متن فارسی با نیم‌فاصله
    cleaned = text.strip()
    return f"خروجی: {cleaned}"
```

## ۴. جدول مقایسه ویژگی‌ها

| شناسه | ویژگی | وضعیت | اولویت |
| :--- | :--- | :---: | ---: |
| ۱ | پشتیبانی RTL کامل | ✅ فعال | بالا |
| ۲ | تبدیل به ورد (DOCX) | ✅ فعال | متوسط |
| ۳ | دیاگرام‌های تعاملی | ✅ فعال | بالا |

<!-- pagebreak -->

## ۵. بخش دوم پس از شکست صفحه

این بخش در صفحه دوم قرار می‌گیرد و شامل استایل‌های متنوع است.
"""
