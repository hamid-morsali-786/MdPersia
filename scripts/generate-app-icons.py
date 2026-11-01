"""Build crisp, size-specific monochrome Windows icons from vector geometry.

Pillow is a build-only dependency. Preserve the original document/MD/RTL mark. Small frames use hinted strokes;
large PNG frames are available for browser app windows and high-DPI taskbars.
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
    draw.polygon(pts([(48,16),(160,16),(208,64),(208,240),(40,240),(40,16)]), fill='white')
    line([(48,16),(160,16),(208,64),(208,240),(40,240),(40,16),(48,16)],12,'#111111')
    line([(156,18),(156,70),(206,70)],10,'#111111')
    weight = 14 if size <= 24 else 12
    line([(66,150),(66,102),(90,132),(114,102),(114,150)],weight,'#111111')
    line([(136,150),(136,102),(151,102)],weight,'#111111')
    draw.arc(tuple(round(v * factor) for v in (127,102,175,150)), -90,90,fill='#111111',width=round(weight*factor))
    line([(151,150),(136,150)],weight,'#111111')
    draw.rounded_rectangle(pts([(60,174),(188,218)]),radius=round(8*factor),fill='#111111')
    line([(161,196),(88,196),(103,185)],8)
    line([(88,196),(103,207)],8)
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
    print('Generated 512px PNG and 9 Windows frames; original SVG identity preserved.')


if __name__ == '__main__':
    main()
