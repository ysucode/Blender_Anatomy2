"""Set up a Blender_Anatomy2 film.

  python new_project.py <slug> ["عنوان المجلد في الخزنة"]

Creates content-studio/<slug>/ with:
  حالة.md   the project's state: which gate is approved, what is next (update it at every gate)
  blender/  kit, studio, sheet, timeline (24 fps) + the watch film as a worked template (parts.py, film.py)
  motion/   glass panel templates: panel2d.py (manim), glass.py + world.py (Blender), overlay.js, helpers
  edit/     align (WhisperX), captions (GSAP through Chrome), composite, score (template), lines.example.txt
  voice/    رواية's voice tools (measure, robot, assemble, config) + patch.py; takes/ agent/ patch/
  music/    رواية's generate.py + a sections.json template
  sfx/      tick.py (click synth matched to a reference recording)
  figure/   empty: the anatomy figure is built there (best in a parallel session)
and D:/renders/<slug>/ for frames, plus the vault folder with مرجع/.
Chrome (playwright-core), GSAP and anime.js are shared from the skill's vendor/ folder: nothing is installed per project.
"""
import shutil, sys
sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
A = SKILL / "assets"
RIWAYA = Path.home() / ".claude/skills/رواية/assets"
import os
_vf = Path(__file__).resolve().parent.parent / ".vault"  # local, gitignored: one line, the vault path
VAULT = Path(os.environ.get("ANATOMY_VAULT") or (_vf.read_text(encoding="utf-8").strip() if _vf.exists() else Path.home() / "anatomy-vault"))
STUDIO = VAULT / "content-studio"
RENDERS = Path("D:/renders")
TOOLS = {
    "Blender": Path("D:/tools/blender-5.2.3-windows-x64/blender.exe"),
    "manim venv": Path("D:/tools/venvs/manim/Scripts/manim.exe"),
    "WhisperX venv": Path("D:/tools/venvs/whisperx/Scripts/python.exe"),
    "playwright-core (skill vendor)": SKILL / "vendor/node_modules/playwright-core",
    "GSAP (skill vendor)": SKILL / "vendor/gsap/dist/gsap.min.js",
    "Arabic font": STUDIO / "node_modules/@fontsource/ibm-plex-sans-arabic",
    "style sheet": STUDIO / "style-sheet.md",
}
STATE = """# حالة المشروع: {slug}

حدّث هالملف عند كل بوابة. أي جلسة جديدة تقراه أول شي.

| البوابة | الحالة | التاريخ | ملاحظات |
|---|---|---|---|
| 1. الفكرة والخطاف | ما بدأت | | |
| 2. النص والستوريبورد | ما بدأت | | |
| 3. الصوت | ما بدأت | | |
| 4. الموسيقى | ما بدأت | | |
| 5. المسودة السريعة (نص الدقة مع الصوت) | ما بدأت | | |
| 6. المسودة النهائية | ما بدأت | | |
| 7. النشر | ما بدأت | | |

## القرارات
- السرعة 24 إطار، المدة بين 80 و120 ثانية (المدة المختارة: ؟ والسبب: ؟)

## وين وقفنا
-

## الملفات المهمة
- الإطارات: D:/renders/{slug}/
"""


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    slug = sys.argv[1]
    root = STUDIO / slug
    if root.exists():
        sys.exit(f"{root} already exists; choose another name")
    for part in ("blender", "edit", "sfx", "motion"):
        shutil.copytree(A / part, root / part)
    (root / "edit/caps").mkdir()
    (root / "edit/inserts").mkdir()
    shutil.copytree(RIWAYA / "voice", root / "voice")
    shutil.copy(A / "voice/patch.py", root / "voice/patch.py")
    for d in ("takes", "agent", "patch"):
        (root / "voice" / d).mkdir(exist_ok=True)
    (root / "music").mkdir()
    shutil.copy(RIWAYA / "music/generate.py", root / "music/generate.py")
    shutil.copy(A / "music/sections.json", root / "music/sections.json")
    (root / "figure").mkdir()
    (root / "حالة.md").write_text(STATE.format(slug=slug), encoding="utf-8")
    (RENDERS / slug).mkdir(parents=True, exist_ok=True)
    if len(sys.argv) > 2:
        v = VAULT / "2-المحتوى والعمل الحر" / sys.argv[2]
        (v / "مرجع").mkdir(parents=True, exist_ok=True)
        print("vault:", v)
    print("ready:", root)
    print("renders:", RENDERS / slug)
    for name, p in TOOLS.items():
        if not p.exists():
            print("MISSING:", name, "->", p)


main()
