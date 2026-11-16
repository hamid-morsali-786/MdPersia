"""Render Mermaid diagrams to PNG images using Playwright/Chromium."""

from __future__ import annotations

import html
import json
import os
import tempfile
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from .defaults import ensure_playwright_node_path
from .html_builder import to_mermaid_source

MERMAID_PAGE_TEMPLATE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ margin: 0; padding: 24px; background: white; }}
  .mermaid {{
    display: block;
    font-size: 18px;
    background: white;
  }}
  .mermaid svg {{
    display: block;
    max-width: 100%;
    height: auto;
    background: white;
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

MAX_SCREENSHOT_PHYS_PX = 12_000
FALLBACK_SCREENSHOT_PHYS_PX = 4_096


def _clamp_svg_for_screenshot(page, scale_factor: int, max_phys_px: int) -> None:
    """Clamp rendered SVG size so physical dimensions stay within Chromium texture limits."""
    max_css = max(256, int(max_phys_px // max(1, scale_factor)))
    page.evaluate(
        """(maxCss) => {
            const pre = document.querySelector('.mermaid');
            const svg = document.querySelector('.mermaid svg');
            if (!pre || !svg) return;
            const rect = svg.getBoundingClientRect();
            const vb = svg.viewBox && svg.viewBox.baseVal;
            const rawW = rect.width >= 1 ? rect.width : (vb && vb.width > 0 ? vb.width : 800);
            const rawH = rect.height >= 1 ? rect.height : (vb && vb.height > 0 ? vb.height : 600);
            if (!svg.getAttribute('viewBox')) svg.setAttribute('viewBox', `0 0 ${rawW} ${rawH}`);
            const ratio = Math.min(1, maxCss / Math.max(rawW, rawH, 1));
            const w = Math.max(1, Math.floor(rawW * ratio));
            const h = Math.max(1, Math.floor(rawH * ratio));
            svg.style.width = `${w}px`;
            svg.style.maxWidth = `${w}px`;
            svg.style.minWidth = '0px';
            svg.style.height = `${h}px`;
            pre.style.display = 'inline-block';
            pre.style.width = `${w}px`;
        }""",
        max_css,
    )


def _capture_mermaid_png(page, target_el, png_path: Path, scale_factor: int) -> None:
    """Capture Mermaid element screenshot with fallback clamping if texture limits are hit."""
    _clamp_svg_for_screenshot(page, scale_factor, MAX_SCREENSHOT_PHYS_PX)
    try:
        target_el.screenshot(path=str(png_path), omit_background=False)
    except Exception:
        _clamp_svg_for_screenshot(page, scale_factor, FALLBACK_SCREENSHOT_PHYS_PX)
        target_el.screenshot(path=str(png_path), omit_background=False)



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

    ensure_playwright_node_path()
    with sync_playwright() as playwright:
        def _launch_browser(pw):
            if os.environ.get('MDPERSIA_BUNDLED_ENGINE') == '1':
                return pw.chromium.launch(headless=True)
            for kw in (
                {"headless": True},
                {"headless": True, "channel": "msedge"},
                {"headless": True, "channel": "chrome"},
            ):
                try:
                    return pw.chromium.launch(**kw)
                except Exception:
                    continue
            raise RuntimeError(
                "Could not launch browser (Chromium/Edge/Chrome). Please make sure a browser is installed."
            )

        browser = _launch_browser(playwright)
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

                    # Locate the rendered diagram SVG (or container fallback)
                    mermaid_el = page.query_selector(".mermaid svg") or page.query_selector(".mermaid")
                    if mermaid_el is None:
                        if ignore_errors:
                            continue
                        raise RuntimeError(
                            f"Mermaid block #{idx} did not produce an SVG output."
                        )

                    # Wait a moment for SVG to fully render
                    page.wait_for_timeout(200)

                    png_path = temp_dir / f"mermaid_{idx}.png"
                    _capture_mermaid_png(page, mermaid_el, png_path, device_scale_factor)
                    result[code] = png_path
                finally:
                    page.close()
        finally:
            browser.close()

    return result
