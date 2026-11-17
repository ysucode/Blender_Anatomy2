# Blender_Anatomy2

سكيل لـ Claude Code تصنع فيلم أناتومي عمودي (80–120 ثانية، 24 إطار) لآلة تتفكك قدام المشاهد، مبني بالكود في Blender مع لوحة زجاجية تعرض الرياضيات داخل عالم 3D، وترجمة كلمة بكلمة على توقيت WhisperX.

التفاصيل الكاملة في [SKILL.md](SKILL.md).

## التثبيت

```bash
git clone https://github.com/ysucode/Blender_Anatomy2 ~/.claude/skills/Blender_Anatomy2
cd ~/.claude/skills/Blender_Anatomy2/vendor && npm install
```

## الإعداد

- مجلد الخزنة (اللي فيه `content-studio/`): حطه في متغير البيئة `ANATOMY_VAULT`، أو في ملف `.vault` بجذر السكيل (سطر واحد فيه المسار). الافتراضي `~/anatomy-vault`.
- الأدوات المتوقعة: Blender 5.2، بيئة manim، بيئة WhisperX، ffmpeg، Chrome. المسارات الافتراضية تحت `D:/tools` وتقدر تعدلها في `scripts/new_project.py`.
- `new_project.py` ينسخ أدوات الصوت والموسيقى من سكيل «رواية» (`~/.claude/skills/رواية`)، وهي مو داخل هذا الريبو.
