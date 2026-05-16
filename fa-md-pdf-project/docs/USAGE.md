# راهنمای استفاده

## دستور کلی

```powershell
fa-md-pdf INPUT [OPTIONS]
```

`INPUT` می‌تواند یک فایل Markdown یا یک فولدر باشد.

نسخه فعلی ابزار به‌صورت پیش‌فرض از فایل‌ها و فولدرهای آفلاین داخل ریشه پروژه استفاده می‌کند:

```text
browsers\
fonts\
vendor\mermaid.min.js
```

بنابراین وقتی از ریشه پروژه اجرا کنید، این دستور کافی است:

```powershell
fa-md-pdf .\docs
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

## مسیرهای پیش‌فرض آفلاین

برنامه این مسیرها را به‌صورت خودکار از ریشه پروژه پیدا می‌کند:

| مسیر | کاربرد |
|---|---|
| `vendor\mermaid.min.js` | رندر نمودارهای Mermaid بدون اینترنت |
| `fonts\Vazirmatn-*.ttf` | فونت فارسی داخل PDF |
| `browsers\` | Chromium مخصوص Playwright |

برای دیدن مسیرهای نهایی:

```powershell
fa-md-pdf .\docs --verbose
```

## گزینه‌های مهم

| گزینه | توضیح |
|---|---|
| `-o, --output` | فایل خروجی برای ورودی تکی یا فولدر خروجی برای ورودی فولدر |
| `--recursive` | تبدیل فایل‌های زیرپوشه‌ها؛ پیش‌فرض فعال است |
| `--no-recursive` | فقط فایل‌های مستقیم فولدر |
| `--extensions` | پسوندهای مجاز، پیش‌فرض `.md .markdown` |
| `--font-family` | تنظیم خانواده فونت |
| `--font-file` | معرفی یک فایل فونت محلی؛ جایگزین `--font-dir` می‌شود |
| `--font-dir` | معرفی فولدر فونت؛ پیش‌فرض `.\fonts` |
| `--css` | افزودن CSS سفارشی |
| `--page-format` | اندازه صفحه مانند A4 یا Letter |
| `--margin` | حاشیه، مثل `12mm` |
| `--landscape` | خروجی افقی |
| `--mermaid-js` | مسیر محلی فایل Mermaid؛ پیش‌فرض `.\vendor\mermaid.min.js` |
| `--mermaid-url` | URL فایل Mermaid؛ فقط برای حالت آنلاین |
| `--mermaid-theme` | تم Mermaid مانند `default`, `neutral`, `dark`, `forest` |
| `--mermaid-timeout` | timeout رندر نمودارها به میلی‌ثانیه |
| `--browsers-path` | مسیر Chromium/Browserهای Playwright؛ پیش‌فرض `.\browsers` |
| `--keep-html` | نگه‌داشتن فایل HTML میانی |
| `--fail-fast` | توقف با اولین خطا |
| `--ignore-mermaid-errors` | ادامه تبدیل حتی در صورت خطای Mermaid |
| `--verbose` | چاپ اطلاعات بیشتر و مسیرهای تشخیص‌داده‌شده |

## نمونه کامل آفلاین

```powershell
fa-md-pdf .\docs `
  -o .\pdf `
  --page-format A4 `
  --margin 15mm `
  --mermaid-theme neutral `
  --keep-html `
  --verbose
```

## Override دستی مسیرها

```powershell
fa-md-pdf .\docs `
  --browsers-path .\browsers `
  --font-dir .\fonts `
  --mermaid-js .\vendor\mermaid.min.js
```
