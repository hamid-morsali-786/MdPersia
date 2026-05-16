# اجرای کاملاً آفلاین در ویندوز

برای اجرای کاملاً آفلاین، پروژه باید این دارایی‌ها را داخل خودش داشته باشد:

```text
fa-md-pdf-project/
  .venv/
  browsers/
  fonts/
  vendor/
    mermaid.min.js
```

## 1. مرورگرهای Playwright

اگر قبلاً دستور زیر را اجرا کرده‌اید:

```powershell
python -m playwright install chromium
```

فایل‌ها معمولاً در این مسیر هستند:

```text
%LOCALAPPDATA%\ms-playwright
```

کل محتویات آن را داخل `browsers` پروژه کپی کنید:

```powershell
cd E:\project\fa-md-pdf-project

New-Item -ItemType Directory -Force .\browsers
Copy-Item "$env:LOCALAPPDATA\ms-playwright\*" ".\browsers\" -Recurse -Force
```

بعد از کپی باید ساختار چیزی شبیه این باشد:

```text
browsers/
  _links/
  chromium_headless_shell-1217/
  chromium-1217/
  ffmpeg-1011/
  winldd-1007/
```

برنامه به‌صورت خودکار همین فولدر را به متغیر `PLAYWRIGHT_BROWSERS_PATH` وصل می‌کند.

## 2. Mermaid آفلاین

فایل Mermaid را اینجا قرار دهید:

```text
vendor\mermaid.min.js
```

بعد از آن، دیگر نیازی به `--mermaid-js` نیست.

## 3. فونت فارسی

فونت‌های Vazirmatn را اینجا قرار دهید:

```text
fonts\Vazirmatn-Regular.ttf
fonts\Vazirmatn-Bold.ttf
fonts\Vazirmatn-Medium.ttf
...
```

برنامه فایل‌های `Vazirmatn-*.ttf` را خودکار در HTML embed می‌کند.

## 4. اجرای آفلاین

```powershell
cd E:\project\fa-md-pdf-project
.\.venv\Scripts\Activate.ps1

fa-md-pdf .\docs --verbose
```

باید در خروجی مسیرهای محلی را ببینید:

```text
[fa-md-pdf] mermaid js:   E:\project\fa-md-pdf-project\vendor\mermaid.min.js
[fa-md-pdf] font dir:     E:\project\fa-md-pdf-project\fonts
[fa-md-pdf] browsers:     E:\project\fa-md-pdf-project\browsers
```

## نکته مهم

کپی کردن فولدر `browsers` فقط مرورگر را آفلاین می‌کند. خود وابستگی‌های Python مثل `playwright` و `markdown-it-py` هم باید داخل `.venv` نصب شده باشند یا از طریق wheelhouse آفلاین نصب شوند.
