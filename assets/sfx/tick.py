"""Synthesised escapement tick, matched to the user's reference timbre, at the 4R36's real 6 beats/s.

Reference (Downloads/videoplayback.m4a, measured 2026-11-08): a beat every 128 ms (8/s), spectral peaks
near 2.6 kHz and 7.4 kHz, energy up to ~11 kHz, -20 dB after 16 ms, -30 dB after 27 ms, and each beat made
of several sub-clicks a few ms apart. The reference itself is never used in the film.

  python tick.py <out.wav> [seconds] [beats_per_s]
"""
import sys, wave
import numpy as np

SR = 48000
rng = np.random.default_rng(7)

MODES = [  # freq Hz, decay s, amplitude  (tuned against the reference: 6-9 kHz carries ~45 %)
    (2620, 0.0045, 0.42),
    (3350, 0.0030, 0.18),
    (4900, 0.0028, 0.22),
    (6880, 0.0032, 0.80),
    (7380, 0.0034, 1.00),
    (8300, 0.0024, 0.40),
    (9600, 0.0020, 0.30),
    (11200, 0.0015, 0.22),
]


def click(amp=1.0, pitch=1.0, length=0.04):
    n = int(SR * length)
    t = np.arange(n) / SR
    y = np.zeros(n)
    for f, tau, a in MODES:
        ph = rng.uniform(0, 2 * np.pi)
        y += a * np.exp(-t / tau) * np.sin(2 * np.pi * f * pitch * t + ph)
    noise = rng.standard_normal(n) * np.exp(-t / 0.0007) * 0.5
    y += noise
    attack = np.minimum(1.0, t / 0.00015)
    return amp * y * attack


def beat(tock=False):
    # unlock, impulse, drop (the loudest), a few ms apart
    parts = [(0.0000, 0.45), (0.0042, 0.30), (0.0105, 1.0)]
    pitch = 0.97 if tock else 1.0
    gain = 0.86 if tock else 1.0
    n = int(SR * 0.06)
    y = np.zeros(n)
    for off, a in parts:
        c = click(a * gain * rng.uniform(0.94, 1.06), pitch)
        i = int(off * SR)
        y[i:i + len(c)] += c[: n - i]
    return y


def room(y):
    ir_n = int(SR * 0.035)
    t = np.arange(ir_n) / SR
    ir = rng.standard_normal(ir_n) * np.exp(-t / 0.006) * 0.03
    ir[0] = 1.0
    return np.convolve(y, ir)[: len(y)]


def track(seconds=10.0, bps=6.0):
    n = int(SR * seconds)
    y = np.zeros(n + SR)
    k = 0
    while k / bps < seconds:
        b = beat(tock=bool(k % 2))
        i = int(k / bps * SR)
        y[i:i + len(b)] += b
        k += 1
    y = room(y[:n])
    return y / np.max(np.abs(y)) * 10 ** (-6 / 20)


def write(path, y):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes())


if __name__ == "__main__":
    out = sys.argv[1]
    sec = float(sys.argv[2]) if len(sys.argv) > 2 else 10.0
    bps = float(sys.argv[3]) if len(sys.argv) > 3 else 6.0
    write(out, track(sec, bps))
    print(out)
