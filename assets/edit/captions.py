"""Word-by-word captions (GSAP) from words.json, rendered frame by frame through Chrome.

  python edit/captions.py      -> caps/chunks.json and caps/f/%05d.png (transparent 1080x200, one per film frame)
Style sheet: IBM Plex Sans Arabic 700, 56 px, dark pill #252422 with cream text, 2-3 words at a time, each word
arrives 0.05 s before it is spoken, the line's *key* word sits on orange #EB5E28 with dark text. AI lines use an
orange pill. The pill's bottom edge is at y=1320 (composite.py pastes the strip at y=1120).
"""
import json, re, pathlib, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")
HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "blender"))
from timeline import FPS, DUR
CAPS = HERE / "caps"
CAPS.mkdir(exist_ok=True)
PUNCT = re.compile(r"[.،«»…]+")
MAXW = 3


def main():
    words = json.loads((HERE / "words.json").read_text(encoding="utf-8"))
    groups, cur = [], []
    for i, w in enumerate(words):
        cur.append(i)
        end_line = i + 1 >= len(words) or words[i + 1]["line"] != w["line"]
        stop = re.search(r"[.،؟?…]$", w["w"])
        if end_line or len(cur) >= MAXW or (stop and len(cur) >= 2):
            groups.append(cur)
            cur = []
    last_line = max(w["line"] for w in words)
    chunks, seen = [], set()
    for g, idx in enumerate(groups):
        nxt = words[groups[g + 1][0]]["s"] - 0.2 if g + 1 < len(groups) else 1e9
        end = min(nxt, words[idx[-1]]["e"] + 0.45)
        style = "ai" if words[idx[0]]["ai"] else ("cta" if words[idx[0]]["line"] == last_line else "nar")
        ws = []
        for i in idx:
            key = bool(words[i].get("key")) and words[i]["line"] not in seen     # one key word per script line
            if key:
                seen.add(words[i]["line"])
            ws.append(dict(w=PUNCT.sub("", words[i]["w"]), s=words[i]["s"], key=key))
        chunks.append(dict(style=style, end=round(max(end, words[idx[-1]]["s"] + 0.1), 3), words=ws))
    (CAPS / "chunks.json").write_text(json.dumps(chunks, ensure_ascii=False, indent=1), encoding="utf-8")
    n = round(DUR * FPS) + 1
    print("chunks", len(chunks), "frames", n, "fps", FPS)
    subprocess.run(["node", str(HERE / "captions.js"), str(FPS), str(n)], check=True)


main()
