import http.server
import socketserver
import threading
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

PORT = 9878
DIST_DIR = Path(__file__).resolve().parent.parent / "desktop-tauri" / "dist"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "screenshots"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIST_DIR), **kwargs)

async def capture():
    server = socketserver.TCPServer(("127.0.0.1", PORT), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        
        # 1. Dark Mode
        page_dark = await browser.new_page(viewport={"width": 1366, "height": 820})
        await page_dark.goto(f"http://127.0.0.1:{PORT}")
        await page_dark.wait_for_timeout(1500)
        await page_dark.screenshot(path=str(OUTPUT_DIR / "desktop-ui-dark.png"))
        await page_dark.close()

        # 2. Light Mode
        context_light = await browser.new_context(viewport={"width": 1366, "height": 820})
        page_light = await context_light.new_page()
        await page_light.add_init_script("localStorage.setItem('theme', 'light');")
        await page_light.goto(f"http://127.0.0.1:{PORT}")
        await page_light.wait_for_timeout(1500)
        await page_light.screenshot(path=str(OUTPUT_DIR / "desktop-ui-light.png"))
        await page_light.close()

        await browser.close()

    server.shutdown()
    print("Screenshots captured successfully!")

if __name__ == "__main__":
    asyncio.run(capture())
