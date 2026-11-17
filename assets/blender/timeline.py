"""The film's clock, shared by film.py (picture, inside Blender) and edit/score.py (sound, plain Python).
No bpy here, so both can import it.

1. Storyboard first: write the beats in STORY (seconds) and choreograph against them.
2. After the voice is approved, fill WARP with (storyboard time -> voice time) pairs taken from
   voice/timing.json word times. W() remaps every beat, lift window and camera key at once, so the
   choreography keeps its shape and lands on the words. Leave WARP = [(0, 0)] until then.

The values below are the watch film's («قطعة ناقصة», video 11) as a worked example. Replace them.
"""
FPS = 24

STORY = dict(
    explode=1.2, tower=2.3, ai_start=5.6, ai_end=7.3, dial=7.8, run0=10.0, run1=12.6, dead=13.0,
    flip0=15.0, flip1=18.6, rotor1=29.0, barrel1=36.0, train1=43.0,
    dark0=43.0, fault=46.0, twist0=55.0, fix0=62.0, fix_place=66.0, fix1=71.0,
    back0=71.0, flipback0=78.0, assembled=82.0, end=92.0)

# storyboard time -> voice time (each pair is one word the beat must land on)
WARP = [
    (0.0, 0.0), (1.2, 1.6), (2.3, 2.7), (5.6, 7.0), (7.3, 8.6), (9.6, 12.4),
    (10.0, 14.4), (12.6, 16.7), (13.0, 17.0), (15.0, 17.9), (18.6, 21.4), (25.5, 26.0),
    (29.0, 32.4), (36.0, 37.9), (43.0, 43.9), (46.0, 46.4), (55.0, 57.4), (62.0, 59.4),
    (66.0, 62.9), (71.0, 73.8), (78.0, 82.4), (82.0, 86.0), (92.0, 96.0),
]


def W(t):
    if len(WARP) < 2:
        return t
    for (a0, b0), (a1, b1) in zip(WARP, WARP[1:]):
        if t <= a1:
            return b0 + (b1 - b0) * (t - a0) / (a1 - a0)
    a0, b0 = WARP[-1]
    return b0 + (t - a0)


T = {k: W(v) for k, v in STORY.items()}
DUR = T["end"]
