"""Prepare the browser's print layout and report adjustments before PDF output."""
from __future__ import annotations

from typing import TYPE_CHECKING

from .conversion_report import warn

if TYPE_CHECKING:
    from .converter import ConvertOptions


def prepare_print_layout(page, options: ConvertOptions) -> None:
    # Printing has no horizontal scrollbar. Measure against the actual paper's
    # content width rather than Playwright's unrelated default viewport width.
    layout = page.evaluate("""async ({format, landscape, margin}) => {
        await document.fonts.ready;
        await Promise.all(Array.from(document.images, image =>
            image.decode().catch(() => {})));
        const papers = {A3: [297, 420], A4: [210, 297], A5: [148, 210],
            LETTER: [215.9, 279.4], LEGAL: [215.9, 355.6], TABLOID: [279.4, 431.8]};
        const paper = papers[format.toUpperCase()] || papers.A4;
        const probe = document.createElement('div');
        probe.style.width = `calc(${paper[landscape ? 1 : 0]}mm - 2 * ${margin})`;
        document.body.append(probe);
        const width = probe.getBoundingClientRect().width;
        probe.remove();
        let wrapped = 0, scaled = 0;
        for (const math of document.querySelectorAll('.math.block math')) {
            const available = Math.min(width - 24, math.parentElement.clientWidth - 24);
            let current = math.getBoundingClientRect().width;
            const row = math.firstElementChild;
            if (available > 0 && current > available && row?.localName === 'mrow') {
                const groups = [];
                let group = [];
                for (const node of Array.from(row.children)) {
                    if (node.localName === 'mo' && /^[+=−<>≤≥]$/.test(node.textContent)
                        && group.length) {
                        groups.push(group);
                        group = [];
                    }
                    group.push(node);
                }
                if (group.length) groups.push(group);
                if (groups.length > 1) {
                    const widths = groups.map(nodes => {
                        const first = nodes[0].getBoundingClientRect();
                        const last = nodes[nodes.length - 1].getBoundingClientRect();
                        return last.right - first.left + 16;
                    });
                    const ns = 'http://www.w3.org/1998/Math/MathML';
                    const table = document.createElementNS(ns, 'mtable');
                    let cell, lineWidth = 0;
                    groups.forEach((nodes, index) => {
                        if (!cell || lineWidth + widths[index] > available) {
                            const tr = document.createElementNS(ns, 'mtr');
                            cell = document.createElementNS(ns, 'mtd');
                            cell.setAttribute('columnalign', 'left');
                            tr.append(cell);
                            table.append(tr);
                            lineWidth = 0;
                        }
                        cell.append(...nodes);
                        lineWidth += widths[index];
                    });
                    row.replaceWith(table);
                    wrapped++;
                    current = math.getBoundingClientRect().width;
                }
            }
            if (available > 0 && current > available) {
                scaled++;
                math.style.fontSize = `${parseFloat(getComputedStyle(math).fontSize)
                    * available / current}px`;
            }
        }
        return {wrapped, scaled, brokenImages: Array.from(document.images).filter(i => !i.naturalWidth).length};
    }""", {"format": options.page_format, "landscape": options.landscape,
          "margin": options.margin})

    if layout['wrapped']:
        warn('layout.math.wrapped', f"{layout['wrapped']} فرمول بلند چندسطری شد.")
    if layout['scaled']:
        warn('layout.math.scaled', f"{layout['scaled']} فرمول برای جا شدن در کاغذ کوچک شد.",
             suggestion='برای خوانایی بیشتر از کاغذ افقی استفاده کنید.')
    if layout['brokenImages']:
        warn('image.decode', 'بعضی تصویرها بارگذاری یا رمزگشایی نشدند.')
