<div dir="rtl">

# MdPersia (مدپرشیا)

**ابزار مدرن، آفلاین و تخصصی تبدیل اسناد Markdown فارسی و راست‌به‌چپ (RTL) به Word (DOCX) و PDF با پشتیبانی کامل از دیاگرام‌های Mermaid.**

[![CI](https://github.com/hamid-morsali-786/MdPersia/actions/workflows/ci.yml/badge.svg)](https://github.com/hamid-morsali-786/MdPersia/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![RTL Supported](https://img.shields.io/badge/RTL-Native%20Support-orange.svg)](#)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

> [English Documentation](README.md) | **مستندات فارسی**

---

## چرا MdPersia؟

بسیاری از توسعه‌دهندگان، پژوهشگران و نویسندگان فارسی‌زبان هنگام تبدیل یادداشت‌ها و مستندات Markdown خود به Word یا PDF با مشکلات اساسی مواجه می‌شوند:
* **به‌هم‌ریختگی جهت متون ترکیبی:** کلمات انگلیسی، پرانتزها، اعداد و کدهای درون‌خطی در ابزارهای معمولی (مانند Pandoc یا اکستنشن‌های VS Code) معکوس می‌شوند.
* **فقدان خروجی استاندارد Word (DOCX):** تبدیل‌های متداول به Word، تنظیمات RTL پاراگراف‌ها و جدول‌ها را اعمال نمی‌کنند.
* **عدم نمایش یا خراب شدن دیاگرام‌های Mermaid:** نمودارهای سیستمی و فلوچارت‌ها در خروجی‌های آفلاین رندر نمی‌شوند.

**MdPersia** با معماری دوگانه و اختصاصی، فایل‌های شما را با بالاترین کیفیت بصری و کاملاً استاندارد به **PDF و DOCX** تبدیل می‌کند.

---

## ویژگی‌های کلیدی

- 🚀 **تبدیل صحیح و دقیق:** پشتیبانی بی‌نقص از جهت متن (BiDi)، اعداد، پرانتزها و فونت‌های استاندارد فارسی.
- 📄 **پشتیبانی دوگانه از Word (DOCX) و PDF:** ایجاد اسناد تمیز سازمانی و اداری با جدول‌ها و استایل‌های راست‌چین.
- 📊 **رندر مستقیم دیاگرام‌های Mermaid:** فلوچارت‌ها، توالی‌ها (Sequence)، کلاس‌ها و گانت‌ها به صورت خودکار با کیفیت رتینا درون سند قرار می‌گیرند.
- ⚡ **کاملاً آفلاین (Offline-First):** بدون وابستگی به CDN خارجی؛ مرورگر headless، فونت وزیرمتن و کتابخانه‌های گرافیکی همگی به صورت آفلاین مدیریت می‌شوند.
- 🖥️ **رابط کاربری گرافیکی (GUI) و ترمینال (CLI):** امکان استفاده از خط فرمان سریع یا محیط گرافیکی روان (Tkinter و نسخه Tauri).
- 🔄 **حالت پایش زنده (`--watch`):** تبدیل آنی فایل‌ها با هر ذخیره‌سازی (`Ctrl+S`).
- 📁 **تبدیل دسته‌ای (Batch Processing):** تبدیل پوشه‌ها و زیرپوشه‌ها به همراه حفظ کامل ساختار درختی در خروجی.
- 🛠️ **اصلاح‌کننده خودکار Markdown (`--wrap-rtl`):** قابلیت تزریق هوشمند تگ‌های `<div dir="rtl">` به فایل‌های موجود بدون دستکاری بلوک‌های کد.

---

## ساختار پوشه پیشنهادی (حالت آفلاین)

```text
MdPersia/
  ├── browsers/           # مرورگر Chromium محلی برای رندر PDF و نمودارها
  ├── fonts/              # فونت‌های Vazirmatn-*.ttf
  ├── vendor/             # فایل آفلاین mermaid.min.js
  ├── docs/               # فایل‌های Markdown شما
  └── output/             # خروجی‌های تولید شده
```

---

## نصب و راه‌اندازی

### ۱. نصب سریع با pip (توسعه‌دهندگان)

```powershell
pip install mdpersia
```

یا از سورس مخزن:

```powershell
git clone https://github.com/hamid-morsali-786/MdPersia.git
cd MdPersia
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

### ۲. آماده‌سازی مرورگر Chromium (یک‌بار برای همیشه)

اگر به اینترنت متصل هستید:
```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = "$PWD\browsers"
python -m playwright install chromium
```

اگر پوشه مرورگر را از قبل دانلود کرده‌اید، کافیست محتویات `%LOCALAPPDATA%\ms-playwright` را درون پوشه `browsers/` در ریشه پروژه کپی کنید.

---

## راهنمای استفاده از CLI

### تبدیل یک فایل به PDF (پیش‌فرض)
```powershell
mdpersia .\docs\report.md
```
*خروجی `docs/report.pdf` تولید خواهد شد.*

### تبدیل به فایل Word (DOCX)
```powershell
mdpersia .\docs\report.md -f docx
```
*خروجی `docs/report.docx` با استایل و پاراگراف‌های کاملاً راست‌چین و جدول‌های منظم ایجاد می‌شود.*

### تبدیل دسته‌ای یک پوشه با تعیین مقصد خروجی
```powershell
mdpersia .\docs -o .\dist -f pdf
```

### پایش خودکار فایل‌ها هنگام ویرایش (Watch Mode)
```powershell
mdpersia .\docs\paper.md -w -f pdf
```

### اصلاح خودکار فایل‌های مارک‌داون موجود
```powershell
mdpersia .\my-notes --wrap-rtl
```

---

## اجرای رابط گرافیکی (GUI)

برای اجرای محیط گرافیکی کافی است دستور زیر را وارد کنید:

```powershell
mdpersia --gui
```

یا در صورت ایجاد میانبر:
```powershell
mdpersia-gui
```

---

## استفاده به عنوان کتابخانه در پایتون (Python API)

```python
from pathlib import Path
from mdpersia import build_jobs, convert_jobs, ConvertOptions

options = ConvertOptions(
    format="docx",       # یا "pdf"
    font_family='"Vazirmatn", sans-serif',
    page_format="A4",
    margin="15mm"
)

jobs = build_jobs(
    input_path=Path("./docs/guide.md"),
    options=options
)

success_count, fail_count = convert_jobs(jobs)
print(f"تبدیل انجام شد: {success_count} موفق، {fail_count} ناموفق")
```

---

## گزینه‌ها و سوئیچ‌های پرکاربرد CLI

| سوئیچ | عملکرد | مقدار پیش‌فرض |
| :--- | :--- | :--- |
| `-o, --output` | مسیر فایل یا پوشه خروجی | کنار فایل ورودی |
| `-f, --format` | فرمت خروجی (`pdf` یا `docx`) | `pdf` |
| `-w, --watch` | پایش تغییرات فایل و تبدیل بلادرنگ | غیرفعال |
| `--gui` | باز کردن رابط گرافیکی | غیرفعال |
| `--font-family` | خانواده فونت CSS | `Vazirmatn` |
| `--docx-image-scale` | ضریب کیفیت تصاویر Mermaid در ورد (۱ تا ۴) | `3` |
| `--page-format` | قطع صفحه PDF (`A4`, `Letter`, ...) | `A4` |
| `--margin` | حاشیه صفحات PDF | `15mm` |
| `--landscape` | ایجاد صفحات افقی | عمودی |
| `--strip-emojis` | حذف اموجی‌ها از خروجی نهایی | غیرفعال |
| `--wrap-rtl` | افزودن تگ‌های RTL به متن مارک‌داون | غیرفعال |

---

## مشارکت در توسعه (Contributing)

مشارکت شما باعث پیشرفت این ابزار می‌شود! لطفاً راهنمای [CONTRIBUTING.md](CONTRIBUTING.md) را مطالعه کرده و ایده‌ها یا گزارش باگ‌های خود را در بخش Issues مطرح فرمایید.

---

## سازنده و حق امتیاز

توسعه‌داده شده توسط **[حمید مرسلی (Hamid Morsali)](https://github.com/hamid-morsali-786)** تحت مجوز متن‌باز [MIT](LICENSE).

</div>
