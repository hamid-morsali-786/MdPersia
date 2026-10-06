"""Render Mermaid diagrams to PNG images using Playwright/Chromium."""

from __future__ import annotations

import html
import json
import tempfile
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from .html_builder import to_mermaid_source

MERMAID_PAGE_TEMPLATE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ margin: 0; padding: 40px; background: white; }}
  .mermaid {{
    display: block;
    font-size: 18px;
    min-width: 600px;
  }}
  .mermaid svg {{
    width: 100%;
    height: auto;
    min-width: 600px;
  }}
</style>
</head>
<body>
<pre class="mermaid">{mermaid_code}</pre>
<script src="{mermaid_src}"></script>
<script>
window.__READY = false;
window.__ERROR = null;
(async function () {{
  try {{
    if (!window.mermaid) throw new Error("Mermaid library not loaded");
    window.mermaid.initialize({config_json});
    await window.mermaid.run({{ querySelector: ".mermaid" }});
  }} catch (error) {{
    window.__ERROR = String((error && error.stack) || error);
  }} finally {{
    window.__READY = true;
  }}
}})();
</script>
</body>
</html>
"""


def render_mermaid_to_png(
    mermaid_codes: list[str],
    *,
    mermaid_source: str,
    mermaid_theme: str = "default",
    font_family: str = '"Vazirmatn", Tahoma, sans-serif',
    timeout_ms: int = 30_000,
    ignore_errors: bool = False,
    device_scale_factor: int = 3,
) -> dict[str, Path]:
    """
    Render a list of mermaid code blocks to PNG files.

    Returns a mapping of mermaid_code -> PNG path. Files are written to a
    temporary directory; caller is responsible for keeping the directory alive
    until the images are consumed.
    """
    if not mermaid_codes:
        return {}

    config = {
        "startOnLoad": False,
        "theme": mermaid_theme,
        "securityLevel": "strict",
        "htmlLabels": True,
        "fontFamily": font_family,
    }
    config_json = json.dumps(config, ensure_ascii=False)
    src = html.escape(to_mermaid_source(mermaid_source), quote=True)

    temp_dir = Path(tempfile.mkdtemp(prefix="fa-md-pdf-mermaid-"))
    result: dict[str, Path] = {}

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            for idx, code in enumerate(mermaid_codes):
                if code in result:
                    continue

                page = browser.new_page(
                    viewport={"width": 2400, "height": 1600},
                    device_scale_factor=device_scale_factor,
                )
                try:
                    escaped_code = html.escape(code, quote=False)
                    html_doc = MERMAID_PAGE_TEMPLATE.format(
                        mermaid_code=escaped_code,
                        mermaid_src=src,
                        config_json=config_json,
                    )

                    html_file = temp_dir / f"mermaid_{idx}.html"
                    html_file.write_text(html_doc, encoding="utf-8")

                    page.goto(html_file.resolve().as_uri(), wait_until="domcontentloaded")
                    try:
                        page.wait_for_function(
                            "() => window.__READY === true", timeout=timeout_ms
                        )
                    except PlaywrightTimeoutError:
                        if not ignore_errors:
                            raise RuntimeError(
                                f"Timeout rendering Mermaid block #{idx}. "
                                "Increase --mermaid-timeout or check the diagram."
                            )
                        continue

                    error = page.evaluate("() => window.__ERROR || null")
                    if error:
                        if not ignore_errors:
                            raise RuntimeError(f"Mermaid render error: {error}")
                        continue

                    # Locate the rendered diagram container
                    mermaid_el = page.query_selector(".mermaid")
                    if mermaid_el is None:
                        if ignore_errors:
                            continue
                        raise RuntimeError(
                            f"Mermaid block #{idx} did not produce an SVG output."
                        )

                    # Wait a moment for SVG to fully render
                    page.wait_for_timeout(200)

                    png_path = temp_dir / f"mermaid_{idx}.png"
                    mermaid_el.screenshot(path=str(png_path), omit_background=False)
                    result[code] = png_path
                finally:
                    page.close()
        finally:
            browser.close()

    return result
