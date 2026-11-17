# Blender_Anatomy2 — technical reference

Everything here was measured or broke on the first film (video 11, the Seiko 4R36 watch, 2026-11-08).
Fixed rules since 2026-11-11: 24 fps everywhere (`timeline.FPS`), 80–120 s, −14 LUFS, identity colours for
anything drawn. The glass panel, captions and WhisperX are in `motion-tools.md`.
The worked files are in `assets/` and in `content-studio/watch-anatomy/`.

Contents: 1 Scene and units · 2 Kit · 3 Lighting · 4 Choreography · 5 Camera in 9:16 · 6 Pitfalls seen on
the first frames · 7 Render · 8 Anatomy session brief · 9 Captions · 10 Sound · 11 Commands

## 1. Scene and units

- 1 BU = 1 mm, `scene.unit_settings.scale_length = 0.001`. Real DOF then behaves like macro: f/4–8 at 15–60 mm
  is shallow, f/11–16 keeps a 40 mm watch sharp. Clip start 0.5.
- Build the mechanism "back side up" in design coordinates and flip it into the object frame
  (`place_mov`: (x, y, z) → (x, −y, −z), euler X = π). Spins are then plain euler-Z additions.
- Everything is a child of one root empty (`WATCH`). Turning the whole object over (to show its back)
  = rotate the root about Y by π. After the flip a design point P maps to world `(−Px, −Py, z)` (`MW()`).
- Exploded tower: offset along local Z by `(5 − layer) * gap ± sub * gap * 0.55`, a few degrees of tilt
  per layer so thickness reads, a little Z twist; big housings drop away (−110 mm) instead of joining the tower.
  9:16 fits ~10 layers at gap 5.2 mm with the camera at elevation ~15°.

## 2. Kit (`assets/blender/kit.py`)

- `outline(name, loops, thick, mat)`: 2D curve fill; any inner loop becomes a hole (even-odd). Bridges,
  plates, hands, wheels. Bevel comes from the curve's `bevel_depth`.
- `wheel(name, n, r_pitch, thick, mat, spokes, kind)`: `cycloid` (watch train), `club` (escape wheel),
  `ratchet`. Spoke windows are real holes. `pinion`, `arbor` (conical pivots).
- `lathe(name, profile, mat)`: round parts (case, crystal, jewels, screws, barrel). `ring`, `disc`.
- `jewel`, `screw` (one boolean-cut mesh shared by every copy), `spiral_strip` (hairspring/mainspring),
  `box`, `text_obj` (Windows fonts: bahnschrift for bezels, segoesc for script, arialbd for discs).
- `join(objs, name)` joins into a new object at the world origin. Joining into an existing object
  and then moving it shifts everything (that bug happened once).
- `to_mesh` removes the curve first, then names the mesh (otherwise names get `.001`).

## 3. Lighting (`assets/blender/studio.py`)

- World shader splits by `Light Path → Is Camera Ray`:
  - camera rays see a screen-space backdrop (light centre, diagonal beam, cool dark corners, like the reference);
  - everything else sees a dark room plus five procedural softboxes, plus 12 % HDRI (Poly Haven `studio_small_09`, CC0,
    in `D:/tools/hdri/`).
  The first try with a bright HDRI made all the steel flat grey. Metal needs dark things to reflect.
- One sun lamp for shadows. Emissive cards off-camera do nothing in EEVEE screen-space reflections, so the
  softboxes live in the world.
- A "dark moment": `world_dark_hook()` inserts a mix to near-black driven by a value node, plus a spot on the
  subject (energy ~2.5e5 W at ~80 mm in mm units).
- AgX, look "Medium High Contrast". Dial colour needs metallic ≤ 0.3, or it reads grey.

## 4. Choreography (`assets/blender/film.py`)

- Pure functions of t: `mech(t)` (all spin angles), `explode_amount`, `lift` windows per group, `dark(t)`,
  `root_rot(t)`, `cam_state(t)`. Speeds that must integrate (runaway, ratchet) use precomputed tables.
- Real ratios where they show: escape wheel half a tooth per beat; fourth = escape / 12 (seconds hand),
  third /7.5, centre /8, barrel /8. Balance A·sin(2π·3·t) for 21,600 vph. Pallet = tanh of balance angle.
- Camera: keys (t, target, distance, azimuth, elevation, lens, fstop) with a cubic Hermite through time.
  Close keys = drift, a far key soon after = whip. DOF focus = distance to target every frame.
- `timeline.py`: STORY beats + WARP (storyboard → voice time). Lifts and camera keys are written in storyboard
  time and remapped with W().

## 5. Camera in 9:16

- Vertical sensor fit 36 mm. At 85 mm the horizontal half-angle is only 6.8°: at 15 mm distance the frame
  is ±1.8 mm wide. Anything entering from the side leaves the frame at once. Bring hands and tools
  (tweezers) in **from the top of the frame** (the far side, away from the camera).
- Low, wide "drone" shots skimming the parts (lens 24–28, 9–12 mm away, elevation ~20°) read like the
  reference's best shot. Drop housings out of the way first (lift the case −30 mm), or the camera sits behind
  the case wall.

## 6. Pitfalls seen on the first frames (check stills for each)

- **Occlusion by something swinging:** the rotor swung between the camera and the Magic Lever, giving
  3 s of plain metal. Lift the occluder clear when the line names the part underneath. `check.py` flags
  near-empty frames (std < 12).
- **Hidden subject:** the balance rim hid the exit jewel's slot from every good angle, so the *entry* jewel
  became the missing one. Choose the hero part by what the camera can see.
- **Spinning too fast:** 12 rev/s turns a wheel into a ghost under motion blur. Keep ≤ 3 rev/s on
  screen; "fast" still reads.
- **Emissive marker spill:** an orange emission of 2–6 bloomed into smoke on the blurred wheel. Use ≤ 0.7.
- **Darkness hides tools:** dark steel tweezers vanished in the dark scene. Bring the light back as the
  repair starts (it also tells the story).
- **State left over:** a part kept its "exploded" offset after the repair (explode_amount returned 1 forever).
  Test the after-states, not just the before.
- Blocky bracelet links and no perlage were left for later; fix them if the shot lingers on them.

## 7. Render

- Stills: `film.py -- stills <dir> t1,t2,.. 50 32` ~0.5 s each after a ~20 s shader compile.
- Anim: `film.py -- anim <dir> f0 f1 100 24` bakes keyframes per frame (fast, seconds), then renders with
  EEVEE motion blur (shutter 0.5, steps 3). Measured on the first film (30 fps then): 2,881 frames in 2,505 s
  (~0.9–2 s/frame on RTX 2070). Films are 24 fps now: 120 s = 2,880 frames.
- Quick draft (gate 5): `film.py -- anim <dir>/draft 0 <last> 50 8` renders the whole film at half size with 8
  samples; add the voice and captions and send it before the full render.
  Frames are `####.jpg`. Re-render only the frame range a fix touches into the same folder.
- Test 30 frames first and compare pixel differences across frames; a fast "BAKED" line is normal.

## 8. Anatomy session brief (parallel session, own_initiative card)

Ask for a Hero-size anatomy figure in `figure/` (framework-free `build.mjs`), from one pure `model.mjs`:
the mechanism in energy order, states the film needs (e.g. normal / missing / fixed / explode / wind),
switchable by URL or JS for baking; readouts from the model in Arabic (IBM Plex Sans Arabic, no letter-spacing)
with Latin digits; English part names if the user wants them; brand colours paper `#FFFCF2`, ink `#252422`,
accent `#EB5E28`; `bake.mjs` on a virtual clock at 1080×1920/24 fps with readable text inside x 200–880 and the card
between y 420 and 1150 (captions sit at y 1220–1320); A4 poster/drawing/detailed PDFs via the skill's `print.mjs` (the comment-word reward); done =
`--audit` passes, `line ends: 0`, test bakes and PDFs sent. Tell it not to touch `blender/` or `D:/renders`.
If a card still runs under the caption strip, raise `SHIFT` in `composite.py`.

## 9. Captions

- Pillow here has no raqm, so it can't shape Arabic. `captions.js` renders each state through Chrome (playwright-core in
  `vendor/`) from a real file page: fonts from `file://` don't load in `setContent` (it fell back to Arial).
- `align.py` force-aligns the approved script (`lines.txt`) to the voice with WhisperX (timing only). The old
  difflib method is kept as `align_fallback.py`.
- Captions are GSAP frames (`captions.py` + `captions.js`): pill bottom at y = 1320, 2–3 words arriving one by one,
  one key word per line on orange, AI lines on an orange pill. Details in `motion-tools.md`, section 7.

## 10. Sound

- Measure a reference tick: onsets on the 4 kHz high-passed envelope, the interval, FFT peaks of the strongest
  tick, and the decay to −20/−30 dB (`tick.py` docstring). The watch reference had peaks at 2.6/6.9/7.4 kHz and decayed
  in ~15 ms, with 3 sub-clicks per beat (unlock, impulse, drop). Synthesise at the subject's true rate.
- `score.py`: events from `timeline.T`; whoosh = noise with a rising band sweep; thump = falling sine + noise;
  tink = three decaying partials; ratchet clicks follow the integrated rotor speed. Mix: voice + music −10 dB
  sidechained to the voice + SFX −4 dB → loudnorm −14 LUFS (style sheet), TP −3.

## 11. Commands (from the project folder)

```bash
B=/d/tools/blender-5.2.3-windows-x64/blender.exe
"$B" -b --factory-startup --python blender/film.py -- stills D:/renders/<slug>/sb 0.6,2,4 50 32
python blender/sheet.py D:/renders/<slug>/sb D:/renders/<slug>/sb.jpg 5 300
"$B" -b --factory-startup --python blender/film.py -- anim D:/renders/<slug>/draft 0 <last> 50 8     # quick draft
"$B" -b --factory-startup --python blender/film.py -- anim D:/renders/<slug>/frames 0 <last> 100 24
node figure/bake.mjs normal --cam escape --seconds 3      # then move frames/normal -> edit/inserts/<name>
PYTHONUTF8=1 D:/tools/venvs/whisperx/Scripts/python.exe edit/align.py && PYTHONUTF8=1 python edit/captions.py
python edit/score.py v2
python edit/composite.py D:/renders/<slug>/frames D:/renders/<slug>/edit
ffmpeg -framerate 24 -i D:/renders/<slug>/edit/%05d.jpg -i edit/mix.wav -c:v libx264 -preset slow -crf 20 \
  -pix_fmt yuv420p -c:a aac -b:a 256k -movflags +faststart -shortest ../export/<slug>-v1.mp4
python ~/.claude/skills/Blender_Anatomy2/scripts/check.py ../export/<slug>-v1.mp4 D:/renders/<slug>/frames --project . --copies
```
