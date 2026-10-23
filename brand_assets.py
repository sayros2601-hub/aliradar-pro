"""Stable search icons drawn from the site's own simple vector monogram."""
from pathlib import Path
from PIL import Image, ImageDraw


def build_brand_icons(root):
    root = Path(root)
    scale = 4
    icon = Image.new('RGBA', (180*scale, 180*scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(icon)
    def box(values): return tuple(round(x*scale) for x in values)
    draw.rounded_rectangle(box((0,0,180,180)), radius=38*scale, fill='#153fbd')
    draw.line([box((52,40)),box((78,40))], fill='white', width=12*scale)
    draw.arc(box((28,40,128,140)), start=-90, end=90, fill='white', width=12*scale)
    draw.line([box((78,140)),box((52,140)),box((52,40))], fill='white', width=12*scale)
    draw.line([box((71,89)),box((83,101)),box((106,77))], fill='#61dcff', width=9*scale)
    for name, size in [('favicon.png',96), ('apple-touch-icon.png',180),
                       ('favicon-192.png',192), ('favicon-512.png',512)]:
        icon.resize((size,size), Image.Resampling.LANCZOS).save(root/name)
    icon.save(root/'favicon.ico', sizes=[(16,16),(32,32),(48,48),(64,64)])
