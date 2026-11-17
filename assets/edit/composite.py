"""Composite draft frames: Blender render + anatomy inserts (scan-line wipe) + GSAP caption strip (caps/f).

  python composite.py <blender_frames_dir> <out_dir> [f0] [f1]
edit/inserts.json: [[start_seconds, "folder under edit/inserts"], ...], each insert placed on its line.
Watch example: [[47.3,"a2_escape_normal"],[53.1,"a1_missing"],[64.1,"a3_escape_readout"],[89.6,"a4_explode"]]
"""
import sys, json, os, pathlib
import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "blender"))
from timeline import FPS      # 24: one clock for the whole film
W, H = 1080, 1920
INSERTS = [tuple(x) for x in json.loads((HERE / "inserts.json").read_text(encoding="utf-8"))] if (HERE / "inserts.json").exists() else []
WIPE = 10                        # frames
ACCENT = np.array([235, 94, 40], dtype=np.float32)
CAP_TOP = 1120                   # 200 px caption strip, pill bottom at y=1320 (style sheet)
SHIFT = 0                        # raise if an anatomy card runs under the caption strip (card zone is y 420-1150)



def insert_at(f):
    for s, name in INSERTS:
        d = HERE / "inserts" / name
        n = len(os.listdir(d))
        f0 = round(s * FPS)
        if f0 <= f < f0 + n:
            return d / f"{f - f0:04d}.png", f - f0, n
    return None


def frame(base_dir, f):
    p = pathlib.Path(base_dir) / f"{f:04d}.jpg"
    if not p.exists():
        p = p.with_suffix(".png")
    img = np.asarray(Image.open(p).convert("RGB"), dtype=np.float32)
    ins = insert_at(f)
    if ins:
        path, k, n = ins
        a = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32)
        a = np.concatenate([a[SHIFT:], np.repeat(a[-1:], SHIFT, axis=0)])   # lift the card clear of the caption
        # reveal top-down at the start, hide bottom-up at the end, with a thin accent scan line
        if k < WIPE:
            edge = int(H * ((k + 1) / WIPE) ** 0.8)
        elif k >= n - WIPE:
            edge = int(H * ((n - k) / WIPE) ** 0.8)
        else:
            edge = H
        img[:edge] = a[:edge]
        if edge < H:
            img[max(0, edge - 3):edge + 3] = ACCENT
    out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    cap = HERE / "caps" / "f" / f"{f:05d}.png"
    if cap.exists():
        c = Image.open(cap).convert("RGBA")
        if c.getextrema()[3][1]:
            out.paste(c, (0, CAP_TOP), c)
    return out


def main():
    base, outd = sys.argv[1], pathlib.Path(sys.argv[2])
    f0 = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    f1 = int(sys.argv[4]) if len(sys.argv) > 4 else len(os.listdir(base)) - 2
    outd.mkdir(parents=True, exist_ok=True)
    for f in range(f0, f1 + 1):
        frame(base, f).save(outd / f"{f:05d}.jpg", quality=94)
        if f % 300 == 0:
            print("frame", f, flush=True)
    print("done", f1 - f0 + 1)


main()
