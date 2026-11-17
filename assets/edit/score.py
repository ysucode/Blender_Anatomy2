"""Sound design + mix (worked example: the watch film, video 11). Rewrite the events for a new subject;
keep the helpers (whoosh, thump, tink, click, ticks) and the mix at the bottom. Every event time comes from the film's own timeline (film.py T after WARP).

  python score.py [music_version]   -> edit/sfx.wav, edit/mix.wav  (music v2 by default)
Layers: synthesised escapement ticks (sfx/tick.py timbre, 6 beats/s), runaway whir, explosion thump, part clicks,
Magic Lever ratchet clicks, whooshes for camera moves, the jewel 'tink', and the voice + Eleven Music v2 ducked
under the voice. Loudness target -14 LUFS (style sheet), true peak -3 dBTP.
"""
import sys, math, subprocess, pathlib, wave
import numpy as np
from scipy.signal import butter, sosfilt

HERE = pathlib.Path(__file__).parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "sfx"))
import tick as TK

SR = 48000
rng = np.random.default_rng(11)

sys.path.insert(0, str(ROOT / "blender"))
from timeline import W, T as TT, DUR as FILM_DUR   # same clock as the picture
DUR = FILM_DUR
T = dict(explode=W(1.2), ai_start=W(5.6), ai_end=W(7.3), run0=W(10.0), run1=W(12.6), dead=W(13.0), flip0=W(15.0),
         flip1=W(18.6), rotor1=W(29.0), dark0=W(43.0), fix0=W(62.0), fix_place=W(66.0), back0=W(71.0),
         flipback0=W(78.0), assembled=W(82.0))
OUT = np.zeros(int(SR * (DUR + 1)))


def put(sig, t, gain=1.0):
    i = int(t * SR)
    if i < 0 or i >= len(OUT):
        return
    n = min(len(sig), len(OUT) - i)
    OUT[i:i + n] += sig[:n] * gain


def env(n, a, d):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / d)


def bp(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], btype="band", fs=SR, output="sos"), x)


def whoosh(dur=1.0, lo=300, hi=3000, peak=0.6):
    n = int(SR * dur)
    x = rng.standard_normal(n)
    t = np.linspace(0, 1, n)
    shape = np.sin(np.pi * np.clip(t / peak, 0, 1) * 0.5) ** 2 * np.where(t < peak, 1, np.cos(np.pi * 0.5 * (t - peak) / (1 - peak)) ** 2)
    # sweep the band upward through the swell
    out = np.zeros(n)
    seg = 8
    for k in range(seg):
        a, b = k * n // seg, (k + 1) * n // seg
        f = lo * (hi / lo) ** (k / (seg - 1))
        out[a:b] = bp(x[a:b], f * 0.6, min(f * 1.8, SR / 2 - 100))
    return out * shape * 0.5


def thump(f=52, dur=0.9):
    n = int(SR * dur)
    t = np.arange(n) / SR
    fr = f * (1 + 1.5 * np.exp(-t / 0.03))
    ph = 2 * np.pi * np.cumsum(fr) / SR
    return np.sin(ph) * env(n, 0.002, 0.22) + 0.25 * bp(rng.standard_normal(n), 60, 400) * env(n, 0.001, 0.05)


def tink():
    n = int(SR * 0.6)
    t = np.arange(n) / SR
    y = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t / d) for f, a, d in ((3150, 1, .18), (4720, .6, .12), (7900, .35, .06)))
    return y * env(n, 0.0005, 1.0)


def click(level=1.0, pitch=1.0):
    return TK.click(level, pitch)


def beat(tock):
    return TK.beat(tock)


# ---------------------------------------------------------------- ticks (the watch running)
def ticks(t0, t1, gain_fn):
    k0 = math.ceil(t0 * 6)
    k = k0
    while k / 6 < t1:
        t = k / 6
        put(beat(k % 2 == 1), t, gain_fn(t))
        k += 1


ticks(0.0, T["explode"], lambda t: 0.55)
ticks(T["fix_place"] + 0.4, DUR - 0.3, lambda t: 0.75 if t < T["back0"] else (0.5 if t < T["assembled"] else 0.42 * min(1, (DUR - 0.3 - t) / 1.5 + 0.0) if t > DUR - 1.8 else 0.42))

# ---------------------------------------------------------------- runaway: ticks accelerate into a whir, then dead stop
t = T["run0"]
while t < T["run1"]:
    u = (t - T["run0"]) / (T["run1"] - T["run0"])
    rate = 6 + 70 * u ** 1.6
    put(click(0.55 + 0.3 * u, 1.0 + 0.25 * u), t, 0.6)
    t += 1 / rate
put(click(1.2, 0.9), T["run1"], 0.9)

# ---------------------------------------------------------------- explosion
put(thump(48, 1.2), T["explode"] - 0.02, 1.4)
put(whoosh(0.9, 400, 6000, 0.25), T["explode"] - 0.15, 0.9)
for _ in range(26):
    put(click(rng.uniform(.3, .8), rng.uniform(.8, 1.3)), T["explode"] + rng.uniform(0.05, 1.1), 0.5)

# ---------------------------------------------------------------- AI assembly: dense clicks, final clunk
for i in range(46):
    u = i / 45
    put(click(rng.uniform(.5, 1.0), rng.uniform(.9, 1.2)), T["ai_start"] + (T["ai_end"] - T["ai_start"] - 0.1) * u ** 0.8, 0.55)
put(thump(90, 0.35), T["ai_end"], 0.7)
put(click(1.4, 0.8), T["ai_end"], 0.8)

# ---------------------------------------------------------------- flip and dive through the caseback
put(whoosh(2.6, 200, 2500, 0.55), T["flip0"] + 0.2, 0.8)
put(whoosh(0.9, 500, 7000, 0.4), W(17.6) - 0.3, 0.9)

# ---------------------------------------------------------------- Magic Lever ratchet clicks follow the rotor
def rotor_angle(t):
    a, b = T["flip1"] + 0.6, T["rotor1"] + 0.5
    if t < a or t > b + 2:
        return 0.0
    u = t - a
    sm = lambda x: max(0, min(1, x)) ** 2 * (3 - 2 * max(0, min(1, x)))
    e = sm(u / 1.0) * (1 - sm((t - b) / 2.0))
    return e * (2.6 * math.sin(2 * math.pi * 0.32 * u) + 0.9 * math.sin(2 * math.pi * 0.71 * u + 1.0))


acc, prev, step = 0.0, rotor_angle(T["flip1"]), 2 * math.pi / 24
tt = T["flip1"]
while tt < T["rotor1"] + 2.5:
    a = rotor_angle(tt)
    acc += abs(a - prev) * 0.27 * 0.6 * 6
    prev = a
    if acc >= step:
        acc -= step
        put(click(0.35, 1.35), tt, 0.35)
    tt += 1 / 480

# ---------------------------------------------------------------- lifts, barrel, drone, dark, fix
put(whoosh(1.6, 300, 4000, 0.5), W(29.0), 0.6)                 # rotor + bridges rise
put(whoosh(1.2, 600, 5000, 0.4), W(31.0), 0.4)                  # barrel cover
put(click(0.8, 0.85), W(33.0), 0.5)
put(whoosh(2.0, 250, 3500, 0.5), W(35.6), 0.6)                  # bridges leave, drone starts
put(whoosh(5.5, 150, 1200, 0.5), T["rotor1"] + 5.6, 0.35)       # drone air
put(thump(40, 1.4), T["dark0"] + 0.25, 1.1)                     # «وهنا الغلط»
# free-running escape wheel: soft rattling whir in the dark
n = int(SR * (T["fix0"] + 1.0 - T["dark0"]))
tt = np.arange(n) / SR
whir = bp(rng.standard_normal(n), 1800, 6500) * (0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 180 * tt)))
fade = np.minimum(1, tt / 1.5) * np.minimum(1, (tt[-1] - tt) / 1.5)
put(whir * fade * 0.05, T["dark0"])
put(whoosh(2.4, 400, 3000, 0.7), T["fix0"] + 0.4, 0.35)          # tweezers come in
put(tink(), T["fix_place"], 0.9)
put(click(1.2, 1.0), T["fix_place"], 0.8)

# ---------------------------------------------------------------- reassembly: parts land, flip back
for tland, g in ((W(73.6), 0.9), (W(75.8), 0.7), (W(76.6), 0.9), (W(78.0), 1.0)):
    put(whoosh(0.7, 500, 4000, 0.7), tland - 0.6, 0.35)
    put(click(1.3, 0.85), tland, g)
    put(thump(110, 0.25), tland, 0.35 * g)
put(whoosh(3.0, 200, 2200, 0.5), T["flipback0"] + 0.3, 0.6)
put(thump(60, 1.0), T["assembled"] - 0.1, 0.6)


def write(path, x):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


sfx = OUT[: int(SR * DUR)]
sfx = sfx / (np.max(np.abs(sfx)) + 1e-9) * 0.7
write(HERE / "sfx.wav", sfx)
mv = sys.argv[1] if len(sys.argv) > 1 else "v2"
music = ROOT / "music" / f"{mv}.mp3"
voice = ROOT / "voice" / "voice.wav"
fc = (f"[0:a]aformat=sample_rates=48000:channel_layouts=stereo,apad=whole_dur={DUR},asplit=2[vo][sc];"
      f"[1:a]aformat=sample_rates=48000:channel_layouts=stereo,volume=-10dB[m];"
      f"[m][sc]sidechaincompress=threshold=0.04:ratio=5:attack=15:release=260[md];"
      f"[2:a]aformat=sample_rates=48000:channel_layouts=stereo,volume=-4dB[fx];"
      f"[vo][md][fx]amix=inputs=3:normalize=0:duration=first,atrim=0:{DUR},afade=t=out:st={DUR - 0.8}:d=0.8,"
      f"loudnorm=I=-14:TP=-3:LRA=11[out]")
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(voice), "-i", str(music), "-i", str(HERE / "sfx.wav"),
                "-filter_complex", fc, "-map", "[out]", "-ar", "48000", str(HERE / "mix.wav")], check=True)
print("sfx + mix written;", {k: round(v, 2) for k, v in T.items()})
