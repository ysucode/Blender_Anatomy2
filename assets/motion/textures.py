"""Backdrop texture (identity cream + thin #CCC5B9 grid, 500 px per metre) and a soft panel shadow."""
import sys, os
from PIL import Image, ImageDraw, ImageFilter
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
W, H = 1300, 2200
im = Image.new("RGB", (W, H), (255, 252, 242)); d = ImageDraw.Draw(im, "RGBA")
for x in range(10, W, 60): d.line([(x, 0), (x, H)], fill=(204, 197, 185, 90), width=2)
for y in range(10, H, 60): d.line([(0, y), (W, y)], fill=(204, 197, 185, 90), width=2)
im.save(os.path.join(out, "backdrop.png"))
s = Image.new("RGBA", (600, 660), (37, 36, 34, 0)); ds = ImageDraw.Draw(s)
ds.rounded_rectangle([90, 90, 510, 570], radius=30, fill=(37, 36, 34, 120))
s.filter(ImageFilter.GaussianBlur(38)).save(os.path.join(out, "shadow.png"))
