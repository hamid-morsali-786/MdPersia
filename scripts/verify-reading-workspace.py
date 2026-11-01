"""Exercise reading layout, actual wheel input, interrupted drags and preview colors.

Run against the production bridge, not mocked document responses.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import atexit
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright


def contrast(foreground, background):
    def luminance(color):
        values = [int(n.strip()) / 255 for n in color[color.index('(') + 1:color.index(')')].split(',')[:3]]
        values = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in values]
        return sum(v * w for v, w in zip(values, (.2126, .7152, .0722)))
    a, b = sorted((luminance(foreground), luminance(background)))
    return round((b + .05) / (a + .05), 2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:1423')
    parser.add_argument('--start', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = root / 'output/reading-ui'
    if args.start:
        server = subprocess.Popen(['node', 'dist/desktop-server.mjs', '--port', '1423'],
            cwd=root / 'desktop-tauri', env={**os.environ, 'PYTHON_EXECUTABLE': sys.executable},
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        atexit.register(lambda: server.terminate() if server.poll() is None else None)
        for _ in range(100):
            try:
                urlopen(args.url + '/api/health', timeout=.1).close()
                break
            except OSError:
                time.sleep(.1)
        else:
            raise RuntimeError('Production bridge did not start')
    document = output / 'reading-fixture.md'
    output.mkdir(parents=True, exist_ok=True)
    if not document.exists():
        document.write_text('# مطالعه و کدنویسی\n\nمتن فارسی با English: و نشانه‌گذاری.\n\n'
            '```mermaid\ngraph TD\nA[شروع] --> B{انتخاب مسیر}\nB -->|بله| C[پایان]\nB -->|خیر| A\n```\n\n'
            '```python\n# توضیح فارسی\ndef solve(value: str):\n    return {"result": value, "count": 42}\n```\n\n'
            + '\n\nمتن بلند برای آزمون پیمایش.' * 70, encoding='utf-8')
    report = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 900})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(args.url + '/?file=' + quote(str(document)))
        frame = page.frame_locator('iframe')
        frame.locator('.mermaid svg').wait_for(timeout=30000)
        inner = page.locator('iframe').element_handle().content_frame()
        sidebar = page.get_by_role('region', name='تنظیمات خروجی', exact=True)
        workspace = page.get_by_role('region', name='محیط مطالعه', exact=True)
        assert sidebar.bounding_box()['x'] < workspace.bounding_box()['x']
        assert workspace.bounding_box()['x'] < page.locator('tbody').bounding_box()['x']
        page.screenshot(path=str(output / 'layout-open.png'), animations='disabled')
        report['workspaceCenteredAndOutputOnLeft'] = True
        page.get_by_role('button', name='پنهان‌کردن تنظیمات خروجی', exact=True).click()
        expect(page.get_by_role('button', name='نمایش تنظیمات خروجی', exact=True)).to_be_visible()
        assert page.locator('#output-inspector').bounding_box()['width'] == 0
        assert page.locator('#output-inspector').evaluate('el=>el.inert')
        # Startup arguments are consumed from the address bar; reopening the
        # explicit file tests persistence without inventing a restored queue.
        page.goto(args.url + '/?file=' + quote(str(document)))
        expect(page.get_by_role('button', name='نمایش تنظیمات خروجی', exact=True)).to_be_visible()
        page.get_by_role('button', name='نمایش تنظیمات خروجی', exact=True).click()
        frame.locator('.mermaid svg').wait_for(timeout=30000)
        inner = page.locator('iframe').element_handle().content_frame()
        report['closeReopenAndCollapsedPreferencePersist'] = True
        separator = page.get_by_role('separator', name='تغییر عرض پنل تنظیمات', exact=False)
        box = separator.bounding_box()
        page.mouse.move(box['x'] + box['width'] / 2, box['y'] + 200)
        page.mouse.down()
        page.mouse.move(250, box['y'] + 200, steps=10)
        assert page.locator('#output-inspector').bounding_box()['width'] >= 300
        page.mouse.move(120, box['y'] + 200, steps=10)
        assert page.locator('#output-inspector').bounding_box()['width'] == 0
        page.mouse.move(5, box['y'] + 200, steps=4)
        page.mouse.up()
        expect(page.get_by_role('button', name='نمایش تنظیمات خروجی', exact=True)).to_be_visible()
        report['dragToLeftEdgeFullyCloses'] = True
        report['sidebarNeverRendersSquashedControlsDuringDrag'] = True
        assert page.get_by_role('button', name='نمایش تنظیمات خروجی', exact=True).count() == 1
        # The separator stays mounted at the edge, so dragging right can reopen it.
        box = separator.bounding_box()
        page.mouse.move(box['x'] + box['width'] / 2, box['y'] + 200)
        page.mouse.down()
        page.mouse.move(330, box['y'] + 200, steps=20)
        page.mouse.up()
        expect(page.get_by_role('button', name='پنهان‌کردن تنظیمات خروجی', exact=True)).to_be_visible()
        report['dragRightFromEdgeReopens'] = True
        # Test capture loss while the pointer is still held, not just normal mouseup.
        box = separator.bounding_box()
        page.mouse.move(box['x'] + box['width'] / 2, box['y'] + 200)
        page.mouse.down()
        expect(page.locator('iframe')).to_have_css('pointer-events', 'none')
        separator.evaluate('el=>el.releasePointerCapture(1)')
        page.mouse.move(box['x'] + 30, box['y'] + 200)
        page.mouse.up()
        expect(page.locator('iframe')).to_have_css('pointer-events', 'auto')
        report['lostCaptureRestoresPreviewInput'] = True
        box = separator.bounding_box()
        page.mouse.move(box['x'] + box['width'] / 2, box['y'] + 200)
        page.mouse.down()
        page.evaluate('window.dispatchEvent(new Event("blur"))')
        page.mouse.up()
        expect(page.locator('iframe')).to_have_css('pointer-events', 'auto')
        report['windowBlurRestoresPreviewInput'] = True
        separator.focus()
        page.keyboard.press('Home')
        before_width = page.locator('#output-inspector').bounding_box()['width']
        page.keyboard.press('ArrowLeft')
        assert page.locator('#output-inspector').bounding_box()['width'] < before_width
        page.keyboard.press('ArrowRight')
        assert page.locator('#output-inspector').bounding_box()['width'] == before_width
        report['keyboardResizeAndReset'] = True
        for width in (1024, 1280, 1920, 1440):
            page.set_viewport_size({'width': width, 'height': 900})
            page.wait_for_function("()=>[...document.querySelectorAll('section')].find(el=>el.getAttribute('aria-label')==='محیط مطالعه').getBoundingClientRect().width>=320")
            assert page.evaluate('document.body.scrollWidth<=window.innerWidth')
        report['desktopWidthsFitWithoutHorizontalOverflow'] = True
        box = page.locator('iframe').bounding_box()
        inner.evaluate('window.scrollTo(0,0)')
        page.mouse.move(box['x'] + box['width'] / 2, box['y'] + 150)
        page.mouse.wheel(0, 850)
        inner.wait_for_function('()=>window.scrollY>200')
        report['realWheelScrollsAfterInterruptedDrag'] = True
        page.get_by_role('button', name='پنهان‌کردن تنظیمات خروجی', exact=True).click()
        for theme in ('dark', 'light'):
            if page.locator('html').evaluate('el=>el.classList.contains("dark")') != (theme == 'dark'):
                page.get_by_role('button', name='تغییر تم', exact=True).click()
            inner.evaluate('window.scrollTo(0,0)')
            inner.wait_for_function('()=>getComputedStyle(document.documentElement).colorScheme === ' + json.dumps(theme))
            expect(page.locator('header').first).to_have_css('background-color', 'rgb(17, 24, 39)' if theme == 'dark' else 'rgb(255, 255, 255)')
            colors = inner.evaluate('''() => {
              const pre=document.querySelector('pre:not(.mermaid)'), code=pre.querySelector('code');
              const keyword=pre.querySelector('.k'), string=pre.querySelector('.s2');
              const diagram=document.querySelector('.mermaid'), edge=diagram.querySelector('.flowchart-link');
              return {code:getComputedStyle(code).color, background:getComputedStyle(pre).backgroundColor,
                keyword:getComputedStyle(keyword).color, string:getComputedStyle(string).color,
                tokenBackground:getComputedStyle(keyword).backgroundColor,
                edge:getComputedStyle(edge).stroke, diagram:getComputedStyle(diagram).backgroundColor,
                filter:getComputedStyle(diagram).filter, codeFont:getComputedStyle(keyword).fontFamily};
            }''')
            assert colors['filter'] == 'none'
            assert colors['tokenBackground'] == 'rgba(0, 0, 0, 0)'
            assert colors['keyword'] != colors['string']
            for token in ('code', 'keyword', 'string'):
                colors[token + 'Contrast'] = contrast(colors[token], colors['background'])
                assert colors[token + 'Contrast'] >= 4.5, colors
            colors['edgeContrast'] = contrast(colors['edge'], colors['diagram'])
            assert colors['edgeContrast'] >= 3, colors
            report[theme] = colors
            page.screenshot(path=str(output / f'after-{theme}.png'))
            frame.locator('pre:not(.mermaid)').scroll_into_view_if_needed()
            page.screenshot(path=str(output / f'code-{theme}.png'), animations='disabled')
        page.get_by_role('tab', name='کنسول و گزارش‌ها', exact=True).click()
        assert page.locator('.console-report').bounding_box()['x'] == workspace.bounding_box()['x']
        report['consoleUsesCenterWorkspace'] = True
        assert not errors, errors
        report['pageErrors'] = errors
        browser.close()
    (output / 'reading-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
