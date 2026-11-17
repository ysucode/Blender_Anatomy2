"""manim (cairo) writes premultiplied alpha; Blender and ffmpeg expect straight alpha. Fix in place."""
import sys, glob
import numpy as np
from PIL import Image
for p in sorted(glob.glob(sys.argv[1] + "/*.png")):
    a = np.asarray(Image.open(p).convert("RGBA")).astype(np.float32)
    al = a[..., 3:4]
    a[..., :3] = np.where(al > 0, np.clip(a[..., :3] * 255.0 / np.maximum(al, 1), 0, 255), 0)
    Image.fromarray(a.round().astype(np.uint8), "RGBA").save(p)
