"""Build crisp, size-specific monochrome Windows icons from vector geometry.

Pillow is a build-only dependency. Small taskbar/titlebar frames use wider
strokes and a simpler RTL arrow instead of shrinking a detailed document.
"""
from io import BytesIO
from pathlib import Path
import struct

from PIL import Image, ImageDraw

ASSETS = Path(__file__).resolve().parents[1] / 'src/fa_md_pdf/assets'
SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def render(size):
    scale = 8
    factor = size * scale / 256
    image = Image.new('RGBA', (size * scale, size * scale))
    draw = ImageDraw.Draw(image)
    def pts(values):
        return [(round(x * factor), round(y * factor)) for x, y in values]
    def line(values, width, color='white'):
        draw.line(pts(values), fill=color, width=round(width * factor), joint='curve')
    draw.rounded_rectangle(pts([(12, 12), (244, 244)]), radius=round(40 * factor),
                           fill='#111111', outline='white', width=max(1, round(6 * factor)))
    weight = 18 if size <= 24 else 15
    line([(48, 155), (48, 78), (82, 122), (116, 78), (116, 155)], weight)
    line([(146, 78), (146, 155), (175, 155), (204, 137), (204, 96), (175, 78), (146, 78)], weight)
    line([(202, 196), (57, 196), (79, 176)], 14 if size <= 24 else 12)
    line([(57, 196), (79, 216)], 14 if size <= 24 else 12)
    return image.resize((size, size), Image.Resampling.LANCZOS)


def main():
    render(512).save(ASSETS / 'mdpersia.png')
    frames = []
    for size in SIZES:
        data = BytesIO()
        render(size).save(data, format='PNG')
        frames.append((size, data.getvalue()))
    offset = 6 + len(frames) * 16
    headers = []
    for size, data in frames:
        headers.append(struct.pack('<BBBBHHII', size % 256, size % 256, 0, 0, 1, 32, len(data), offset))
        offset += len(data)
    (ASSETS / 'mdpersia.ico').write_bytes(struct.pack('<HHH', 0, 1, len(frames)) + b''.join(headers) + b''.join(data for _, data in frames))
    (ASSETS / 'mdpersia.svg').write_text('''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none">
  <rect x="12" y="12" width="232" height="232" rx="40" fill="#111" stroke="#fff" stroke-width="6"/>
  <path d="M48 155V78l34 44 34-44v77M146 78v77h29l29-18V96l-29-18h-29Z" stroke="#fff" stroke-width="15" stroke-linejoin="round"/>
  <path d="M202 196H57l22-20m-22 20 22 20" stroke="#fff" stroke-width="12" stroke-linejoin="round"/>
</svg>
''', encoding='utf-8')
    print('Generated 512px PNG, SVG and 9 independently rasterized Windows ICO frames.')


if __name__ == '__main__':
    main()
