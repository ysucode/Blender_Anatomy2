# اللوحة الزجاجية وأدوات الحركة — manim، GSAP، anime.js، WhisperX

مرجع واحد للطريقة المعتمدة. كل القوالب في `motion/` و`edit/` داخل المشروع (منسوخة من `assets/`).
السرعة 24 إطار من `blender/timeline.py`، والألوان والخطوط من `content-studio/style-sheet.md`.

المحتويات: 1 القاعدة · 2 الأدوات · 3 سلسلة اللوحة الزجاجية · 4 manim · 5 Blender: الزجاج والعالم ·
6 طبقة العنوان (anime.js) · 7 الترجمة (GSAP) · 8 WhisperX · 9 أخطاء صارت

## 1. القاعدة

**العالم 3D، والكتابة 2D داخل اللوح الزجاجي.** أي معادلة أو رسم بياني أو رقم يتغير ينرسم مسطح، وينعرض على لوح
زجاج طاير داخل مشهد Blender. الرسم البياني 3D من manim انرفض لأنه مو واضح. الشكل المعتمد من المستخدم (2026-11-11):
`content-studio/zz-anatomy2-test/export/world-test.mp4`.

- العالم بألوان الهوية المحايدة فقط (كريمي، `#CCC5B9`، `#403D39`). **البرتقالي محجوز للرياضيات والكلمة المفتاحية.**
- اللوح في منطقة البطاقة (y 420–1150)، والعنوان فوقه، والترجمة تحته.
- أول إطار يقرأ كامل: الرسم والمعادلة موجودين من الإطار 0.

## 2. الأدوات

| الأداة | وين | دورها |
|---|---|---|
| manim 0.22 | `D:/tools/venvs/manim` | يرسم محتوى اللوح المسطح على خلفية شفافة |
| Blender | `D:/tools/blender-5.2.3-windows-x64` | الزجاج والعالم والكاميرا |
| GSAP 3.15 | `vendor/gsap` في السكل | الترجمة كلمة بكلمة (معتمد) |
| anime.js 4.5 | `vendor/animejs` في السكل | رسم خط SVG ودخول عناصر بالتتابع (العنوان وشارة الخطوة) |
| WhisperX 3.8 | `D:/tools/venvs/whisperx` (CUDA) | توقيت الكلمات فقط |
| playwright-core | `vendor/node_modules` في السكل | يشغّل Chrome لتصيير صفحات GSAP وanime.js |

## 3. سلسلة اللوحة الزجاجية (من مجلد المشروع)

```bash
# 1) manim: فيديو شفاف
cd motion && PYTHONUTF8=1 D:/tools/venvs/manim/Scripts/manim.exe --transparent -o panel panel2d.py Panel2D
# 2) إطارات PNG ثم تصحيح الشفافية
mkdir panel_frames && ffmpeg -v error -i media/videos/panel2d/1320p24/panel.mov -pix_fmt rgba panel_frames/frame%04d.png
python unpremul.py panel_frames
# 3) خامات الخلفية (مرة وحدة) ثم Blender
python textures.py tex
B=/d/tools/blender-5.2.3-windows-x64/blender.exe
"$B" -b -P world.py -- still 100 D:/renders/<slug>/panel_still.png     # جرّب صورة أول واقراها
"$B" -b -P world.py -- anim D:/renders/<slug>/panel
```

`glass.py` لوح على خلفية مسطحة، و`world.py` (المعتمد) لوح داخل عالم 3D ويستورد `glass.py`. طول اللوحة يتحدد من عدد
إطارات `panel_frames`. القياس: 240 إطار 1080×1920 قرابة 7–8 دقايق على RTX 2070، وmanim قرابة دقيقتين.

## 4. manim (`motion/panel2d.py`)

- 1200×1320 (نسبة اللوح)، `config.background_opacity = 0.0` (لازم float)، والسرعة من `timeline.FPS`.
- الخط `IBM Plex Sans Arabic` لكل شي. فيه ∫ ² ₀ ⁄ − بس **ما فيه ′**، فاكتب `f'(x)` بفاصلة عادية. بدون LaTeX.
- **Pango يطلّع بعض الكلمات العربية المفردة فاضية بصمت** («الميل»، «ميل»). الدالة `T()` في القالب فيها `assert` يوقف الرندر.
- **لا تخلط عربي وأرقام في Text واحد** (bidi يقلب الترتيب). قطعتين مرتبتين بـ `next_to`.
- رقم يتغير: كائن ثابت + `add_updater(lambda m: m.become(mk()))`.
- **لا `ReplacementTransform`** بين معادلتين أو بين مستطيلات ومساحة (الحروف تتلخبط). FadeOut/FadeIn بإزاحة 0.2.
- التأكيد: تكبير 1.06 لمدة 0.25 ث ثم رجوع (الهوية).
- `--format png` يحفظ آخر إطار بس. صيّر mov شفاف واستخرج الإطارات.
- **manim يكتب alpha مضروب مسبقاً:** البرتقالي الشفاف يطلع بني في Blender. `unpremul.py` يصلحه (فلتر ffmpeg ما نفع).
- وقّت الأحداث على الكلمات: اقرأ الأوقات من `edit/words.json` (القالب يقرا `edit/beats.json`: `d_start`, `i_start`, `a_start`).

## 5. Blender: الزجاج والعالم

- الزجاج: Principled، Transmission 1، Roughness 0.10، IOR 1.45، سماكة 0.05، حواف Bevel. المحتوى على وجهه كـ emission بشفافية (BLENDED)، وما يرمي ظل.
- **الزجاج يحتاج شي يكسره**، فالخلفية والعالم داخل Blender، مو مركبة بعدين.
- `view_transform = "Standard"` يطلّع ألوان الهوية مضبوطة.
- **ألوان مضبوطة مع إضاءة حقيقية:** العالم كريمي بقوة 1.0 لكل الأشعة (لو خفضته لغير أشعة الكاميرا، الزجاج يكسر سماء رمادية). خفّض بياض الأرضية ×0.72 والكرات ×0.78، والشمس 1.2. النتيجة: السماء `#FFFCF2` بالضبط.
- **بدون خط أفق:** الأرضية تذوب بالكريمي حسب المسافة (View Distance 5–13 م).
- عناصر العالم بسيطة ومرتبطة بالموضوع (في القالب: قوس القطع المكافئ = المنحنى، أعمدة = التكامل). لا تمر خلف العنوان: بعيدة ورفيعة.
- شمس بظلال ناعمة، عمق ميدان f/2.2 مركّز على اللوح، والكاميرا تنزلق جانبياً (parallax) واللوح يبقى في منطقته (صوّب تحت اللوح شوي).

## 6. طبقة العنوان (`motion/overlay.js`، anime.js + GSAP)

- `node motion/overlay.js <cues.json> <outdir> 24 <seconds>` ← إطارات شفافة 1080×1920 تتركب فوق رندر اللوحة.
- anime.js (UMD): `anime.svg.createDrawable` + `draw:['0 0','0 1']` للخط البرتقالي الواحد، و`anime.stagger(90)` لدخول كلمات شارة الخطوة. `createTimeline({autoplay:false}).seek(ms)`. (`anime.version` يرجع undefined، طبيعي.)
- العناصر اللي تبدأ مخفية لازم `opacity:0` في CSS، لأن tween بمدة 1ms عند الصفر ما يطبق مع `seek(0)`.

## 7. الترجمة (`edit/captions.py` + `captions.js`، GSAP)

- تقرأ `edit/words.json` وتطلّع إطار شفاف 1080×200 لكل إطار فيلم في `edit/caps/f/`. `composite.py` يلصقه عند y=1120، فأسفل الحبة عند 1320.
- 2–3 كلمات، كل كلمة تطلع قبل نطقها بـ 0.05 ث (0.3 ث، `power3.out`، إزاحة 14)، والحبة تكبر كلمة بكلمة (`display:none` ثم `tl.set(display)`).
- الكلمة المفتاحية (نجمتين في `lines.txt`): خلفية برتقالية ونص داكن، وحدة لكل سطر. جملة الذكاء الاصطناعي على حبة برتقالية.
- نهاية كل جملة = بداية اللي بعدها − 0.2 ث، وإلا يتداخلون.
- **حتمي:** `gsap.ticker.remove(gsap.updateRoot)` ثم `tl.seek(t, false)` لكل إطار.
- **دالة seek لازم ما ترجّع شي** (`t => { tl.seek(t,false); }`). لو رجّعت الـ timeline، playwright يحاول ينقله وتتعطل الصفحة ("Target crashed").
- الخطوط من `file://` تحتاج صفحة ملف حقيقية (`goto`)، مو `setContent`.

## 8. WhisperX (`edit/align.py`)

- **محاذاة مباشرة للنص المعتمد على الصوت** (`whisperx.align` بدون تفريغ)، فالإملاء دايماً من النص. جُرّب: 19 من 19 كلمة.
- شغّله بـ `PYTHONUTF8=1` وببايثون الـ venv. التشكيل وعلامات الترقيم تنشال للمحاذاة وترجع للعرض.
- الأرقام تنكتب كلمات مثل ما تنقال. لو عدد الكلمات المحاذاة ما طابق النص، السكربت يوقف: راجع `lines.txt` مع الصوت.
- `align_fallback.py` (الطريقة القديمة: difflib على `voice/timing.json`) للطوارئ فقط.
- التنصيب (تم): pip يجيب torch للمعالج، فبعده `pip install --force-reinstall --no-deps torch==2.8.0+cu126 torchaudio==2.8.0+cu126 torchvision==0.23.0+cu126 --index-url https://download.pytorch.org/whl/cu126`.
- التفريغ (transcribe) إملاؤه العربي يغلط («المماز»)، فلا تاخذ منه كلمات أبداً.

## 9. أخطاء صارت (لا تكررها)

- اختبار طلع بخلفية داكنة ولون تمييز ثاني وخط غير Plex: **مخالفة للهوية**. ملفات `zz-anatomy2-test/manim/calc3d.py` و`overlay/render.js` من هالاختبار ولا تُنسخ.
- صوت ويندوز (Naayf) انستخدم للاختبار وطلع سيء. الصوت من ElevenLabs فقط.
- قالب معتمد على مجلد مشروع ثاني (`zz-skilltest`). كل شي مشترك مكانه `vendor/` في السكل.
- `-ql` في manim ما يغيّر الدقة إذا الملف يحدد `config.pixel_width`.
