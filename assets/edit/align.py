"""Give every word of the approved script a time on the final voice track, with WhisperX forced alignment.

The approved text itself (edit/lines.txt) is aligned to voice/voice.wav (or .mp3), so spelling never comes
from a transcription. WhisperX is used for timing only. Run it with the WhisperX venv:

  PYTHONUTF8=1 D:/tools/venvs/whisperx/Scripts/python.exe edit/align.py   -> edit/words.json [{w, s, e, line, ai, key}]

lines.txt: one approved line per row. "AI:" prefix = the AI character's line. Mark ONE key word per line with
*stars* (it gets the orange background, style sheet). Numbers must be written as spoken words.
If a word gets no time (rare), it is spread between its neighbours and listed; if more than 10 % fail, use
align_fallback.py (difflib against voice/timing.json) and tell the user.
"""
import json, re, sys, pathlib
sys.stdout.reconfigure(encoding="utf-8")
HERE = pathlib.Path(__file__).parent
V = HERE.parent / "voice"
DIAC = re.compile("[\u064b-\u0652\u0640]")
PUNCT = re.compile(r"[^\w\s]")


def main():
    import whisperx, torch
    audio_p = next(p for p in (V / "voice.wav", V / "voice.mp3") if p.exists())
    lines = [l.strip() for l in (HERE / "lines.txt").read_text(encoding="utf-8").splitlines() if l.strip()]
    words = []
    for li, line in enumerate(lines):
        ai = line.startswith("AI:")
        for tok in line.replace("AI:", "").split():
            words.append(dict(w=tok.replace("*", ""), line=li, ai=ai, key=tok.count("*") >= 2))
    spoken = [PUNCT.sub("", DIAC.sub("", w["w"])) for w in words]
    idx = [i for i, s in enumerate(spoken) if s]
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    audio = whisperx.load_audio(str(audio_p))
    dur = len(audio) / 16000
    model, meta = whisperx.load_align_model(language_code="ar", device=dev)
    res = whisperx.align([dict(text=" ".join(spoken[i] for i in idx), start=0.0, end=dur)], model, meta, audio, dev,
                         return_char_alignments=False)
    got = [w for seg in res["segments"] for w in seg["words"]]
    if len(got) != len(idx):
        sys.exit(f"aligned {len(got)} words but the script has {len(idx)}: check lines.txt against the voice")
    missing = []
    for i, g in zip(idx, got):
        if "start" in g:
            words[i]["s"], words[i]["e"] = float(g["start"]), float(g["end"])
        else:
            missing.append(words[i]["w"])
    i = 0                                   # spread words without a time between their neighbours
    while i < len(words):
        if "s" in words[i]:
            i += 1
            continue
        j = i
        while j < len(words) and "s" not in words[j]:
            j += 1
        t0 = words[i - 1]["e"] if i else 0.0
        t1 = words[j]["s"] if j < len(words) else dur
        for k in range(i, j):
            words[k]["s"] = t0 + (t1 - t0) * (k - i) / (j - i)
            words[k]["e"] = t0 + (t1 - t0) * (k - i + 1) / (j - i)
        i = j
    last = 0.0
    for w in words:
        w["s"] = round(max(w["s"], last), 3)
        w["e"] = round(max(w["e"], w["s"] + 0.08), 3)
        last = w["s"]
    (HERE / "words.json").write_text(json.dumps(words, ensure_ascii=False, indent=1), encoding="utf-8")
    print("words", len(words), "timed", len(words) - len(missing), "untimed", missing, "dur", round(dur, 2))
    if len(missing) > 0.1 * len(words):
        print("WARNING: more than 10% untimed. Use align_fallback.py and tell the user.")


main()
