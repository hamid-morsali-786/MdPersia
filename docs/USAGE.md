# راهنمای استفاده

## دستور کلی

```powershell
fa-md-pdf INPUT [OPTIONS]
```

`INPUT` می‌تواند یک فایل Markdown یا یک فولدر باشد.

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

## گزینه‌های مهم

| گزینه | توضیح |
|---|---|
| `-o, --output` | فایل خروجی برای ورودی تکی یا فولدر خروجی برای ورودی فولدر |
| `--recursive` | تبدیل فایل‌های زیرپوشه‌ها؛ پیش‌فرض فعال است |
| `--no-recursive` | فقط فایل‌های مستقیم فولدر |
| `--extensions` | پسوندهای مجاز، پیش‌فرض `.md .markdown` |
| `--font-family` | تنظیم خانواده فونت |
| `--font-file` | معرفی فایل فونت محلی |
| `--css` | افزودن CSS سفارشی |
| `--page-format` | اندازه صفحه مانند A4 یا Letter |
| `--margin` | حاشیه، مثل `12mm` |
| `--landscape` | خروجی افقی |
| `--mermaid-js` | مسیر محلی یا URL فایل Mermaid |
| `--mermaid-theme` | تم Mermaid مانند `default`, `neutral`, `dark`, `forest` |
| `--mermaid-timeout` | timeout رندر نمودارها به میلی‌ثانیه |
| `--keep-html` | نگه‌داشتن فایل HTML میانی |
| `--fail-fast` | توقف با اولین خطا |
| `--ignore-mermaid-errors` | ادامه تبدیل حتی در صورت خطای Mermaid |
| `--verbose` | چاپ اطلاعات بیشتر |

## نمونه کامل

```powershell
fa-md-pdf .\docs `
  -o .\pdf `
  --font-family "Vazirmatn, Tahoma, Segoe UI, Arial, sans-serif" `
  --page-format A4 `
  --margin 15mm `
  --mermaid-theme neutral `
  --keep-html
```
