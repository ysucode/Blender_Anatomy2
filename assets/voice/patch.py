"""Replace one stretch of the narration with a freshly generated block, cut at clean pauses.

  python patch.py <base.mp3> <block.mp3> <cut_in|start> <cut_out|end> <out.mp3> [context.mp3]

Find the pauses with:  ffmpeg -i base.mp3 -af silencedetect=n=-38dB:d=0.25 -f null -
and cut in the middle of a pause. Rules learned the hard way (video 11):
  * Never patch a word or phrase inside a sentence: the tone never matches. Regenerate up to the nearest
    paragraph pause, or the whole opening (cut_in = start) or the whole ending (cut_out = end).
  * When the user marks a word, write all its vowels for the TTS («رْكَضَتْ», not «رْكضت»).
  * Check every join by transcribing a context clip (measure.py): a wrong pause silently drops a line.
The block is loudness-matched to the 30 s of base next to the cut.
"""
import subprocess, sys, pathlib
import numpy as np
from scipy.io import wavfile

SR = 44100
LEAD, TAIL = 0.16, 0.18


def load(p):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)


def lufs(x, tmp):
    wavfile.write(tmp, SR, (np.clip(x, -1, 1) * 32767).astype(np.int16))
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(tmp), "-af", "ebur128=framelog=quiet", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    tmp.unlink()
    return float([l for l in out.splitlines() if l.strip().startswith("I:")][-1].split()[1])


def trim(x, thr=0.012):
    a = int(np.argmax(np.abs(x) > thr))
    b = len(x) - int(np.argmax(np.abs(x[::-1]) > thr))
    return x[max(0, a - int(0.02 * SR)): b + int(0.06 * SR)]


def main():
    base, block = load(sys.argv[1]), trim(load(sys.argv[2]))
    dur = len(base) / SR
    cin = 0.0 if sys.argv[3] == "start" else float(sys.argv[3])
    cout = dur if sys.argv[4] == "end" else float(sys.argv[4])
    out_p = pathlib.Path(sys.argv[5])
    tmp = out_p.with_suffix(".lufs.wav")
    ref = base[int(max(0, cin - 30) * SR):int(cin * SR)] if cin > 5 else base[int(cout * SR):int((cout + 30) * SR)]
    block = block * 10 ** ((lufs(ref, tmp) - lufs(block, tmp)) / 20)
    f = int(0.015 * SR); ramp = np.linspace(0, 1, f)
    pre, post = base[:int(cin * SR)].copy(), base[int(cout * SR):].copy()
    if len(pre): pre[-f:] *= ramp[::-1]
    if len(post): post[:f] *= ramp
    block[:f] *= ramp; block[-f:] *= ramp[::-1]
    lead = np.zeros(int((LEAD if len(pre) else 0.25) * SR))
    tail = np.zeros(int((TAIL if len(post) else 0.5) * SR))
    out = np.concatenate([pre, lead, block, tail, post])
    wav = out_p.with_suffix(".tmp.wav")
    wavfile.write(wav, SR, (np.clip(out, -1, 1) * 32767).astype(np.int16))
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(wav), "-b:a", "192k", str(out_p)], check=True)
    wav.unlink()
    print(out_p.name, "dur", round(len(out) / SR, 2), "block", round(len(block) / SR, 2), "shift", round(len(out) / SR - dur, 2))
    if len(sys.argv) > 6:
        s = max(0.0, cin - 5.0)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(s), "-t", str(len(block) / SR + 10.0),
                        "-i", str(out_p), "-b:a", "192k", sys.argv[6]], check=True)


main()
