<div dir="rtl">

# راهنمای استفاده

## دستور کلی

```powershell
fa-md-pdf INPUT [OPTIONS]
```

`INPUT` می‌تواند یک فایل Markdown یا یک فولدر باشد.

برای اجرای رابط گرافیکی:

```powershell
fa-md-pdf-gui
```

یا:

```powershell
fa-md-pdf --gui
```

## حالت فایل تکی

```powershell
fa-md-pdf .\docs\intro.md
```

خروجی:

```text
.\docs\intro.pdf
```

با مسیر خروجی مشخص:

```powershell
fa-md-pdf .\docs\intro.md -o .\out\intro.pdf
```

یا:

```powershell
fa-md-pdf .\docs\intro.md -o .\out
```

در حالت دوم خروجی می‌شود:

```text
.\out\intro.pdf
```

## حالت فولدر

```powershell
fa-md-pdf .\docs
```

در حالت پیش‌فرض، خروجی هر فایل کنار همان فایل ساخته می‌شود.

با فولدر خروجی:

```powershell
fa-md-pdf .\docs -o .\pdf
```

ساختار زیرپوشه‌ها حفظ می‌شود.

## حالت DOCX (Word)

```powershell
fa-md-pdf .\docs -f docx -o .\docx-output
```

نمودارهای Mermaid به‌صورت تصویر PNG با کیفیت بالا داخل سند جای می‌گیرند.

## حالت بسته‌بندی RTL در Markdown

برای افزودن خودکار `<div dir="rtl">...</div>` به بلوک‌های فارسی فایل‌های Markdown:

```powershell
fa-md-pdf .\docs --wrap-rtl
```

پیش‌فرض: کنار هر فایل، نسخه‌ای با پسوند `.rtl` ذخیره می‌شود (`file.md → file.rtl.md`). برای تغییر یا حذف پسوند از `--wrap-rtl-suffix` استفاده کنید.

## گزینه‌های مهم

### عمومی

| گزینه | توضیح |
|---|---|
| `-o, --output` | فایل خروجی برای ورودی تکی یا فولدر خروجی برای ورودی فولدر |
| `-f, --format` | `pdf` یا `docx`. پیش‌فرض: `pdf` |
| `--gui` | باز کردن رابط گرافیکی به‌جای تبدیل |
| `--recursive` | تبدیل فایل‌های زیرپوشه‌ها؛ پیش‌فرض فعال است |
| `--no-recursive` | فقط فایل‌های مستقیم فولدر |
| `--extensions` | پسوندهای مجاز، پیش‌فرض `.md .markdown` |
| `--keep-html` | نگه‌داشتن فایل HTML میانی |
| `--fail-fast` | توقف با اولین خطا |
| `--verbose` | چاپ اطلاعات بیشتر |

### فونت و CSS

| گزینه | توضیح |
|---|---|
| `--font-family` | تنظیم خانواده فونت (CSS برای PDF، نام فونت برای DOCX) |
| `--font-file` | معرفی فایل فونت محلی (`.ttf`)؛ override روی `--font-dir` |
| `--font-dir` | فولدر حاوی `Vazirmatn-*.ttf` |
| `--css` | افزودن CSS سفارشی پس از CSS پیش‌فرض |

### صفحه (PDF)

| گزینه | توضیح |
|---|---|
| `--page-format` | اندازه صفحه مانند `A4`، `Letter`، `Legal` |
| `--margin` | حاشیه، مثل `12mm` یا `0.5in` |
| `--landscape` | خروجی افقی |

### Mermaid

| گزینه | توضیح |
|---|---|
| `--mermaid-js` | مسیر محلی فایل `mermaid.min.js` |
| `--mermaid-url` | URL آنلاین (override) |
| `--mermaid-theme` | `default`, `base`, `dark`, `forest`, `neutral`, `null` |
| `--mermaid-timeout` | timeout رندر هر دیاگرام به میلی‌ثانیه (پیش‌فرض `30000`) |
| `--ignore-mermaid-errors` | ادامه تبدیل حتی در صورت خطای Mermaid |

### DOCX

| گزینه | توضیح | پیش‌فرض |
|---|---|---|
| `--docx-image-scale` | ضریب کیفیت تصویر Mermaid (۱..۴) | `3` |
| `--docx-image-min-width` | حداقل عرض تصویر در سند (اینچ) | `4.0` |
| `--docx-image-max-width` | حداکثر عرض تصویر در سند (اینچ) | `6.5` |
| `--docx-font-size` | اندازه فونت متن (پوینت) | `12` |

### آفلاین

| گزینه | توضیح |
|---|---|
| `--browsers-path` | فولدر مرورگرهای Playwright |

### بسته‌بندی RTL

| گزینه | توضیح |
|---|---|
| `--wrap-rtl` | فعال‌سازی حالت بسته‌بندی Markdown با `<div dir="rtl">` |
| `--wrap-rtl-suffix` | پسوند فایل خروجی، پیش‌فرض `.rtl`. مقدار خالی برای overwrite |

## نمونه کامل PDF

```powershell
fa-md-pdf .\docs `
  -o .\pdf `
  --font-family "Vazirmatn, Tahoma, Segoe UI, Arial, sans-serif" `
  --page-format A4 `
  --margin 15mm `
  --mermaid-theme neutral `
  --keep-html
```

## نمونه کامل DOCX

```powershell
fa-md-pdf .\docs `
  -f docx `
  -o .\docx-output `
  --font-family "Vazirmatn" `
  --docx-font-size 12 `
  --docx-image-scale 3 `
  --docx-image-max-width 6.5
```

</div>
