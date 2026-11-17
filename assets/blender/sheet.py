"""Contact sheet with time labels: python sheet.py <dir> <out.jpg> [cols] [width]"""
import sys, os, subprocess, glob

d, out = sys.argv[1], sys.argv[2]
cols = int(sys.argv[3]) if len(sys.argv) > 3 else 5
w = int(sys.argv[4]) if len(sys.argv) > 4 else 300
files = sorted(glob.glob(os.path.join(d, "t*.jpg")))
inputs, filters = [], []
for i, f in enumerate(files):
    t = str(float(os.path.basename(f)[1:-4])).rstrip("0").rstrip(".")
    inputs += ["-i", f]
    filters.append(f"[{i}]scale={w}:{int(w*16/9)},drawtext=fontfile='C\\:/Windows/Fonts/arialbd.ttf':text='{t}s':x=8:y=8:fontsize=22:fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=5[v{i}]")
rows = (len(files) + cols - 1) // cols
pad = rows * cols - len(files)
for k in range(pad):
    i = len(files) + k
    inputs += ["-f", "lavfi", "-i", f"color=c=0xFFFCF2:s={w}x{int(w*16/9)}:d=1"]
    filters.append(f"[{i}]null[v{i}]")
layout = "|".join(f"{(j % cols)}_{0}" for j in range(0))
xs = []
chains = []
for r in range(rows):
    row = "".join(f"[v{r*cols+c}]" for c in range(cols))
    chains.append(f"{row}hstack=inputs={cols}[r{r}]")
final = "".join(f"[r{r}]" for r in range(rows)) + (f"vstack=inputs={rows}[out]" if rows > 1 else "null[out]")
fc = ";".join(filters + chains + [final])
subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", fc, "-map", "[out]", "-frames:v", "1", "-q:v", "3", out], check=True)
print(out, len(files))
