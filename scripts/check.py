"""Check a draft and make the delivery copies.

  python check.py <video.mp4> [blender_frames_dir] [--project <project_dir>] [--copies]

Prints PASS/FAIL lines for the fixed rules, then the things you must read yourself:
  spec       1080x1920, 24 fps (official decision: every film with a Blender render is 24 fps)
  duration   80-120 s for an anatomy film (pick inside the range by what the script needs)
  loudness   -14 LUFS +-1 (style sheet), true peak under -1 dBFS
  jumps      hard cuts (scene > 0.3): expect only your planned wipes
  empty      near-empty frames in the Blender render (std < 12: something filled the lens)
  captions   (with --project) words.json is ordered, inside the film, speech rate 1.5-4 words/s, one key word
             per line at most, caption frames cover the film, and the pill sits inside x 200-880 and y <= 1320
  first      the first frame is not blank (the hook must read from frame 0)
Writes a 9x5 contact sheet next to the video and runs the safe-zone check at 8 times. Read both yourself.
Not checked here: identity colours inside the 3D picture, and how the sound feels. Say so to the user.
--copies also writes -phone (under 30 MB), -upload (Instagram) and -tiktok (denoise + sharpen) copies.
"""
import json, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path

import os
_vf = Path(__file__).resolve().parent.parent / ".vault"  # local, gitignored: one line, the vault path
VAULT = Path(os.environ.get("ANATOMY_VAULT") or (_vf.read_text(encoding="utf-8").strip() if _vf.exists() else Path.home() / "anatomy-vault"))
FAILS = []


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def rule(name, ok, detail):
    print(("PASS " if ok else "FAIL ") + name + ": " + str(detail))
    if not ok:
        FAILS.append(name)


def captions(proj, dur, fps):
    import numpy as np
    from PIL import Image
    wp = proj / "edit/words.json"
    if not wp.exists():
        return rule("captions", False, "edit/words.json missing")
    words = json.loads(wp.read_text(encoding="utf-8"))
    order = all(a["s"] <= b["s"] for a, b in zip(words, words[1:]))
    rule("caption order", order and words[-1]["e"] <= dur + 0.5, f"{len(words)} words, last ends {words[-1]['e']:.2f}s of {dur:.2f}s")
    span = words[-1]["e"] - words[0]["s"]
    rate = len(words) / max(span, 1)
    rule("speech rate", 1.5 <= rate <= 4, f"{rate:.2f} words/s")
    keys = {}
    for w in words:
        if w.get("key"):
            keys[w["line"]] = keys.get(w["line"], 0) + 1
    rule("key words", all(v == 1 for v in keys.values()), f"{len(keys)} lines have a key word")
    fdir = proj / "edit/caps/f"
    files = sorted(fdir.glob("*.png")) if fdir.exists() else []
    need = round(dur * fps)
    rule("caption frames", len(files) >= need, f"{len(files)} frames for {need}")
    bad, shown = [], 0
    for f in files[::max(1, len(files) // 60)]:
        a = np.asarray(Image.open(f).convert("RGBA"))[..., 3]
        xs = np.where(a.max(axis=0) > 8)[0]
        if len(xs):
            shown += 1
            ys = np.where(a.max(axis=1) > 8)[0]
            if xs[0] < 200 or xs[-1] > 880 or ys[-1] > 199:
                bad.append(f.stem)
    rule("caption safe box", not bad and shown > 0, f"{shown} sampled frames show a caption, outside the box: {bad[:8]}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    proj = None
    if "--project" in sys.argv:
        proj = Path(sys.argv[sys.argv.index("--project") + 1])
        args = [a for a in args if Path(a) != proj]
    v = Path(args[0])
    frames = Path(args[1]) if len(args) > 1 else None
    p = json.loads(run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size:stream=codec_name,width,height,r_frame_rate",
                        "-of", "json", str(v)]).stdout)
    dur = float(p["format"]["duration"])
    vs = [s for s in p["streams"] if s.get("width")][0]
    num, den = vs["r_frame_rate"].split("/")
    fps = float(num) / float(den)
    rule("spec", (vs["width"], vs["height"]) == (1080, 1920) and abs(fps - 24) < 0.01,
         f"{vs['width']}x{vs['height']} {fps:g} fps {int(p['format']['size'])/2**20:.1f} MB")
    rule("duration", 80 <= dur <= 120, f"{dur:.2f}s (anatomy films: 80-120 s)")
    err = run(["ffmpeg", "-hide_banner", "-i", str(v), "-vf", "select='gt(scene,0.3)',showinfo", "-an", "-f", "null", "-"]).stderr
    print("READ jumps (only planned wipes belong here):", re.findall(r"pts_time:([\d.]+)", err))
    err = run(["ffmpeg", "-hide_banner", "-i", str(v), "-af", "ebur128=framelog=quiet:peak=true", "-f", "null", "-"]).stderr
    tail = err[err.rfind("Summary"):]
    i = re.search(r"I:\s+(-?[\d.]+) LUFS", tail)
    pk = re.search(r"Peak:\s+(-?[\d.]+) dBFS", tail)
    if i and pk:
        rule("loudness", abs(float(i.group(1)) + 14) <= 1 and float(pk.group(1)) <= -1, f"{i.group(1)} LUFS, peak {pk.group(1)} dBFS (target -14)")
    else:
        rule("loudness", False, "no audio stream")
    import numpy as np
    from PIL import Image
    first = v.with_name(v.stem + "-first.png")
    run(["ffmpeg", "-v", "error", "-y", "-i", str(v), "-frames:v", "1", str(first)])
    if first.exists():
        a = np.asarray(Image.open(first).convert("L").resize((108, 192)), dtype=float)
        rule("first frame", a.std() >= 12, f"std {a.std():.1f} (read {first.name}: the hook must be readable)")
    if frames:
        files = sorted(list(frames.glob("*.jpg")) + list(frames.glob("*.png")))
        low = []
        for f in files[::5]:
            a = np.asarray(Image.open(f).convert("L").resize((108, 192)), dtype=float)
            if a.std() < 12:
                low.append(f.stem)
        rule("empty frames", not low, f"{len(files)} frames, near-empty: {low[:40]}")
    if proj:
        captions(proj, dur, fps)
    sheet = v.with_name(v.stem + "-sheet.jpg")
    run(["ffmpeg", "-v", "error", "-y", "-i", str(v), "-vf", f"fps=1/{dur/45:.3f},scale=216:384,tile=9x5", "-frames:v", "1", str(sheet)])
    print("READ sheet:", sheet)
    times = [f"{dur * (k + 0.5) / 8:.1f}" for k in range(8)]
    sz = VAULT / "content-studio/safe-zone/safe_zone.py"
    if sz.exists():
        out = run([sys.executable, str(sz), "check", str(v), *times]).stdout
        print("READ safe-zone pngs:", len(out.split()))
    if "--copies" in sys.argv:
        base = v.with_suffix("")
        kbps = int(26 * 8 * 1024 / dur) - 140
        run(["ffmpeg", "-v", "error", "-y", "-i", str(v), "-c:v", "libx264", "-preset", "slow", "-b:v", f"{kbps}k", "-maxrate", f"{int(kbps*1.2)}k",
             "-bufsize", f"{kbps*2}k", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", f"{base}-phone.mp4"])
        run(["ffmpeg", "-v", "error", "-y", "-i", str(v), "-c:v", "libx264", "-preset", "slow", "-crf", "23", "-maxrate", "14M", "-bufsize", "28M",
             "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", f"{base}-upload.mp4"])
        run(["ffmpeg", "-v", "error", "-y", "-i", str(v), "-vf", "hqdn3d=1.5:1.5:4:4,unsharp=5:5:0.4", "-c:v", "libx264", "-preset", "slow",
             "-crf", "21", "-maxrate", "12M", "-bufsize", "24M", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart",
             f"{base}-tiktok.mp4"])
        for s in ("phone", "upload", "tiktok"):
            f = Path(f"{base}-{s}.mp4")
            print(s, f, f"{f.stat().st_size/2**20:.1f} MB" if f.exists() else "FAILED")
    print("RESULT:", "all fixed rules pass" if not FAILS else "FAILED: " + ", ".join(FAILS))


main()
