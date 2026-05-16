# نمونه مستند فارسی

این یک فایل Markdown نمونه برای تست تبدیل به PDF است. متن فارسی باید راست‌به‌چپ نمایش داده شود و کدها چپ‌به‌راست بمانند.

## نمودار Mermaid

```mermaid
flowchart TD
    A[شروع] --> B{فایل Markdown است؟}
    B -->|بله| C[تبدیل Markdown به HTML]
    C --> D[رندر نمودار Mermaid]
    D --> E[چاپ با Chromium]
    E --> F[فایل PDF]
    B -->|خیر| G[رد کردن فایل]
```

## جدول

| بخش | وضعیت | توضیح |
|---|---:|---|
| فارسی و RTL | خوب | متن راست‌به‌چپ است |
| Mermaid | خوب | داخل مرورگر رندر می‌شود |
| PDF | خوب | با Playwright ساخته می‌شود |

## کد

```python
def hello(name: str) -> str:
    return f"Hello, {name}"
```

## فهرست

1. خواندن فایل Markdown
2. تبدیل به HTML
3. رندر Mermaid
4. تولید PDF
