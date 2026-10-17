#!/usr/bin/env python3
"""Generate 1200x630 OG image for Eylenburg's Tech Website (eylenburg.github.io).
Neutral dark #222 card per maintainer review: site name + real tagline only,
no ranking/"best option" content. Pillow-only, portable (FONT_DIR override)."""
import os
from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
BG = (34, 34, 34)         # site #222 dark
ACCENT = (86, 156, 214)   # lightblue tech accent
GREY = (200, 200, 200)
DIM = (150, 150, 150)

FONT_DIR = os.environ.get("FONT_DIR", "/usr/share/fonts/truetype")
def f(path, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, path), size)

img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)

# subtle top accent bar
d.rectangle([0, 0, W, 10], fill=ACCENT)

# site wordmark
d.text((60, 90), "Eylenburg's Tech Website", font=f("dejavu/DejaVuSans-Bold.ttf", 52), fill=(255, 255, 255))

# real tagline (wrapped to two lines)
d.text((60, 190), "Comprehensive comparisons, histories, and other", font=f("dejavu/DejaVuSans.ttf", 32), fill=GREY)
d.text((60, 246), "information across many areas of computing and technology.", font=f("dejavu/DejaVuSans.ttf", 32), fill=GREY)

# neutral comparison motif: three simple horizontal bars of differing lengths
# (data, not rankings) inside a light card
tx0, ty0, tx1, ty1 = 60, 340, 1080, 540
d.rounded_rectangle([tx0, ty0, tx1, ty1], radius=12, fill=(245, 245, 245))
labels = ["Comparisons", "Histories", "Data"]
widths = [760, 560, 660]
y = ty0 + 36
for label, wd in zip(labels, widths):
    d.text((tx0 + 40, y), label, font=f("dejavu/DejaVuSans-Bold.ttf", 26), fill=(34, 34, 34))
    d.rounded_rectangle([tx0 + 300, y + 4, tx0 + 300 + wd, y + 48], radius=8, fill=ACCENT)
    y += 72

# footer
d.text((60, 572), "https://eylenburg.github.io", font=f("dejavu/DejaVuSans.ttf", 22), fill=DIM)

out = "og-image.png"
img.save(out, "PNG")
print("wrote", out, img.size)