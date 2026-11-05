import os
import sys
import time
import subprocess
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PORT = 9878
URL = f"http://127.0.0.1:{PORT}"
OUTPUT_DIR = ROOT / "docs" / "screenshots"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

NODE_EXE = ROOT / ".venv" / "Lib" / "site-packages" / "playwright" / "driver" / "node.exe"
SERVER_SCRIPT = ROOT / "desktop-tauri" / "dist" / "desktop-server.mjs"
SAMPLE_FILE = ROOT / "examples" / "sample-fa.md"

def capture():
    print(f"Starting desktop server on {URL}...")
    env = os.environ.copy()
    env["PYTHON_EXECUTABLE"] = sys.executable
    env["MDPERSIA_INITIAL_FILE"] = str(SAMPLE_FILE)

    server = subprocess.Popen(
        [str(NODE_EXE), str(SERVER_SCRIPT), "--port", str(PORT), "--host", "127.0.0.1"],
        cwd=str(ROOT / "desktop-tauri"),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        # Wait for server health
        for _ in range(60):
            try:
                with urlopen(f"{URL}/api/health", timeout=0.2) as resp:
                    if resp.status == 200:
                        print("Desktop server ready!")
                        break
            except Exception:
                time.sleep(0.1)
        else:
            raise RuntimeError("Desktop server failed to start")

        with sync_playwright() as p:
            browser = p.chromium.launch()

            # 1. Dark Mode
            context_dark = browser.new_context(
                viewport={"width": 1366, "height": 820},
                device_scale_factor=1.25,
            )
            page_dark = context_dark.new_page()
            page_dark.add_init_script("localStorage.setItem('theme', 'dark');")
            page_dark.goto(f"{URL}/?file={quote(str(SAMPLE_FILE))}")
            frame_dark = page_dark.frame_locator("iframe")
            frame_dark.locator(".markdown-body").wait_for(timeout=15000)
            try:
                frame_dark.locator(".mermaid svg").wait_for(timeout=10000)
            except Exception:
                pass
            page_dark.wait_for_timeout(2000)
            dark_path = OUTPUT_DIR / "desktop-ui-dark.png"
            page_dark.screenshot(path=str(dark_path))
            print(f"Captured {dark_path} ({dark_path.stat().st_size} bytes)")
            page_dark.close()
            context_dark.close()

            # 2. Light Mode
            context_light = browser.new_context(
                viewport={"width": 1366, "height": 820},
                device_scale_factor=1.25,
            )
            page_light = context_light.new_page()
            page_light.add_init_script("""
                localStorage.setItem('theme', 'light');
                localStorage.setItem('mdpersia_preferences', JSON.stringify({
                    version: 1,
                    settings: { theme: 'light' }
                }));
            """)
            page_light.goto(f"{URL}/?file={quote(str(SAMPLE_FILE))}")
            frame_light = page_light.frame_locator("iframe")
            frame_light.locator(".markdown-body").wait_for(timeout=15000)
            try:
                frame_light.locator(".mermaid svg").wait_for(timeout=10000)
            except Exception:
                pass
            page_light.wait_for_timeout(2000)
            light_path = OUTPUT_DIR / "desktop-ui-light.png"
            page_light.screenshot(path=str(light_path))
            print(f"Captured {light_path} ({light_path.stat().st_size} bytes)")
            page_light.close()
            context_light.close()

            browser.close()
            print("Both screenshots updated successfully!")

    finally:
        server.terminate()
        server.wait()
        print("Desktop server stopped.")

if __name__ == "__main__":
    capture()
