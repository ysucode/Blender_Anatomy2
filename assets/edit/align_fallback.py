"""Give every word of the approved script a time on the final voice track.

Whisper's words (voice/timing.json) carry the times but not the spelling; the script carries the spelling.
Both are reduced to bare letters, aligned with difflib, and each script word takes the time span of the
Whisper letters it matched. Numbers said as words («خمس مية وثمانطعش ألف») are not in Whisper's text
(«518»), so unmatched words are spread evenly over the gap their neighbours leave.

  python align.py   -> edit/words.json  [{w, s, e, line, ai}]
"""
import json, re, difflib, pathlib, sys
sys.stdout.reconfigure(encoding="utf-8")
HERE = pathlib.Path(__file__).parent
V = HERE.parent / "voice"

# One script line per line in edit/lines.txt, exactly as approved (diacritics kept). Prefix a line with "AI:" when
# the AI character says it; those words take the robot span from voice/timing.json. A «...» word gets the
# orange "CTA" pill if its line is the last one.
LINES = [l.strip() for l in (HERE / "lines.txt").read_text(encoding="utf-8").splitlines() if l.strip()]

DIAC = re.compile(r"[ً-ْـ]")


def bare(s):
    s = DIAC.sub("", s.lower())
    s = s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه").replace("ى", "ي")
    s = s.replace("ق", "ج").replace("ظ", "ض").replace("ذ", "ز").replace("ث", "ت")   # dialect sounds Whisper swaps
    return re.sub(r"[^\w]", "", s)


def main():
    tm = json.loads((V / "timing.json").read_text(encoding="utf-8"))
    ww = tm["words"]
    robot = tm["robot"]
    # whisper letter stream with a time per letter
    wl, wt = [], []
    for w in ww:
        b = bare(w["w"])
        for i, ch in enumerate(b):
            wl.append(ch)
            wt.append(w["s"] + (w["e"] - w["s"]) * (i + 0.5) / max(len(b), 1))
    words = []
    for li, line in enumerate(LINES):
        ai = line.startswith("AI:")
        for tok in line.replace("AI:", "").split():
            words.append(dict(w=tok, line=li, ai=ai))
    # AI words take the robot span
    ai_words = [w for w in words if w["ai"]]
    n = len(ai_words)
    for k, w in enumerate(ai_words):
        w["s"] = robot[0] + (robot[1] - robot[0]) * k / n
        w["e"] = robot[0] + (robot[1] - robot[0]) * (k + 1) / n
    nar = [w for w in words if not w["ai"]]
    sl, owner = [], []
    for i, w in enumerate(nar):
        for ch in bare(w["w"]):
            sl.append(ch)
            owner.append(i)
    sm = difflib.SequenceMatcher(None, "".join(sl), "".join(wl), autojunk=False)
    hits = {}
    for a, b, size in sm.get_matching_blocks():
        for k in range(size):
            hits.setdefault(owner[a + k], []).append(wt[b + k])
    for i, w in enumerate(nar):
        if i in hits and len(hits[i]) >= max(1, len(bare(w["w"])) // 3):
            w["s"], w["e"] = min(hits[i]) - 0.06, max(hits[i]) + 0.06
    # fill unmatched runs between matched neighbours
    i = 0
    while i < len(nar):
        if "s" in nar[i]:
            i += 1
            continue
        j = i
        while j < len(nar) and "s" not in nar[j]:
            j += 1
        t0 = nar[i - 1]["e"] if i > 0 else 0.0
        t1 = nar[j]["s"] if j < len(nar) else tm["dur"]
        for k in range(i, j):
            nar[k]["s"] = t0 + (t1 - t0) * (k - i) / (j - i)
            nar[k]["e"] = t0 + (t1 - t0) * (k - i + 1) / (j - i)
        i = j
    # keep order monotonic
    last = 0.0
    for w in words:
        w["s"] = round(max(w["s"], last), 3)
        w["e"] = round(max(w["e"], w["s"] + 0.08), 3)
        last = w["s"]
    (HERE / "words.json").write_text(json.dumps(words, ensure_ascii=False, indent=1), encoding="utf-8")
    matched = sum(1 for i in range(len(nar)) if i in hits)
    print("words", len(words), "matched", matched, "of", len(nar))
    for w in words:
        if w["line"] in (0, len(LINES) - 1):
            print(f'{w["s"]:6.2f}-{w["e"]:6.2f} {w["w"]}')


main()
