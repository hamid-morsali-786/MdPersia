# Changelog

## Unreleased

- رابط گرافیکی (GUI) فارسی/RTL با `tkinter` اضافه شد:
  - دستور جدید `fa-md-pdf-gui` و فلگ `fa-md-pdf --gui`
  - تب‌های تنظیمات: صفحه، فونت، Mermaid، DOCX و پیشرفته
  - لاگ پیشرفت رنگی، دکمه انصراف، و تشخیص خودکار دارایی‌های آفلاین
- خروجی **DOCX (Word)** اضافه شد:
  - گزینه `-f docx` / `--format docx`
  - رندر نمودارهای Mermaid به‌صورت PNG با کیفیت بالا و embed داخل سند
  - پشتیبانی RTL کامل برای پاراگراف‌ها و عنوان‌ها (`w:bidi`، `w:rtl`، `w:bCs`، `w:szCs`)
  - گزینه‌های `--docx-image-scale`، `--docx-image-min-width`، `--docx-image-max-width`، `--docx-font-size`
- ابزار **`--wrap-rtl`** برای بسته‌بندی خودکار بلوک‌های فارسی با `<div dir="rtl">...</div>` در فایل‌های Markdown، با حفظ بلوک‌های کد و wrapperهای موجود (ایدمپوتنت)
- گزینه‌های `--mermaid-theme` و `--mermaid-timeout` به CLI اضافه شد
- اسکریپت `scripts/build-exe.ps1` برای تولید `fa-md-pdf.exe` (CLI) و `fa-md-pdf-gui.exe` (GUI) با PyInstaller
- spec فایل‌های `fa-md-pdf.spec` و `fa-md-pdf-gui.spec` همراه `entry_point.py` و `entry_point_gui.py`
- تشخیص project root وقتی برنامه به‌صورت exe اجرا می‌شود (با `sys.frozen`)

## 0.2.0

- پیش‌فرض‌های آفلاین اضافه شد:
  - `vendor/mermaid.min.js`
  - `fonts/Vazirmatn-*.ttf`
  - `browsers/`
- گزینه `--browsers-path` اضافه شد.
- گزینه `--font-dir` اضافه شد.
- گزینه `--mermaid-url` برای حالت آنلاین اختیاری اضافه شد.
- `fa-md-pdf .\docs` اکنون از دارایی‌های محلی پروژه استفاده می‌کند.
- مستندات اجرای آفلاین اضافه شد.

## 0.1.0

- اولین نسخه پروژه
- تبدیل فایل تکی و فولدر
- پشتیبانی از فارسی/RTL
- پشتیبانی از Mermaid
- خروجی PDF با Playwright/Chromium
