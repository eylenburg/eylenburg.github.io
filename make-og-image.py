#!/usr/bin/env python3
"""Generate 1200x630 OG image for Eylenburg's Tech Website (eylenburg.github.io).
Pillow-only, portable (reads FONT_DIR override for font paths)."""
import os
from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
BG = (34, 34, 34)        # site #222 dark
CARD = (245, 245, 245)   # light card
ACCENT = (86, 156, 214)  # lightblue-ish tech accent
GREEN = (120, 180, 120)
AMBER = (230, 180, 90)
RED = (214, 110, 110)

FONT_DIR = os.environ.get("FONT_DIR", "/usr/share/fonts/truetype")
def f(path, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, path), size)

img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)

# subtle top accent bar
d.rectangle([0, 0, W, 10], fill=ACCENT)

# header: site wordmark
d.text((60, 45), "Eylenburg's Tech Website", font=f("dejavu/DejaVuSans-Bold.ttf", 46), fill=(255, 255, 255))
d.text((60, 112), "Comparisons, histories & data across computing and technology", font=f("dejavu/DejaVuSans.ttf", 24), fill=(200, 200, 200))

# comparison-table motif: draw a stylized 2-col x 5-row table card
tx0, ty0, tx1, ty1 = 60, 180, 1080, 540
d.rounded_rectangle([tx0, ty0, tx1, ty1], radius=12, fill=CARD)

def cell(x, y, w, h, color, label, lw=2):
    d.rectangle([x, y, x + w, y + h], outline=color, width=lw)

col_w = 340
row_h = 52
x = tx0 + 30
y = ty0 + 24

# header row
d.rectangle([x, y, x + 2 * col_w, y + 40], fill=(222, 222, 222))
d.text((x + 20, y + 6), "Topic", font=f("dejavu/DejaVuSans-Bold.ttf", 20), fill=(34, 34, 34))
d.text((x + col_w + 20, y + 6), "Best option", font=f("dejavu/DejaVuSans-Bold.ttf", 20), fill=(34, 34, 34))
y += 40

rows = [
    ("Operating systems", GREEN, "Linux / BSD"),
    ("Linux distributions", GREEN, "Debian, Arch, Fedora"),
    ("Web browsers", ACCENT, "Firefox, Safari, Chromium"),
    ("Instant messengers", AMBER, "Signal, Element, IRC"),
    ("Cloud & email", RED, "Privacy-first providers"),
]
for name, color, val in rows:
    cell(x, y, col_w, row_h, (180, 180, 180), name)
    cell(x + col_w, y, col_w, row_h, color, val)
    d.text((x + 16, y + (row_h - 24) // 2), name, font=f("dejavu/DejaVuSans-Bold.ttf", 18), fill=(34, 34, 34))
    d.text((x + col_w + 16, y + (row_h - 24) // 2), val, font=f("dejavu/DejaVuSans.ttf", 17), fill=(50, 50, 50))
    y += row_h

# footer
d.text((60, 562), "Sitemap of comparisons & deep dives — eylenburg.github.io", font=f("dejavu/DejaVuSans.ttf", 20), fill=(160, 160, 160))
d.text((60, 594), "data-backed tech comparisons", font=f("dejavu/DejaVuSans-Bold.ttf", 18), fill=ACCENT)

out = "/home/paperclip/scratch/eylenburg.github.io/og-image.png"
img.save(out, "PNG")
print("wrote", out, img.size)