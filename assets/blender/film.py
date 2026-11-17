"""Film template (worked example: the watch film «قطعة ناقصة»). Every value is a pure function of film time t.
Copy, then replace the subject: parts.py builds it, this file choreographs it (explode, lifts, spins, camera).
Beat times come from timeline.py.

  blender -b --factory-startup --python film.py -- stills <outdir> <t1,t2,...> [pct] [samples]
  blender -b --factory-startup --python film.py -- anim <outdir> <f0> <f1> [pct] [samples]
"""
import sys, os, math, time
from math import pi, sin, cos, radians, floor, tanh
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy
from mathutils import Vector, Euler, Matrix
import kit, parts, studio
from parts import PARTS, Pp, Pbal, Pe, Pf, Pt, Pc, Pb, Pr1, Ptw

from timeline import FPS, T, W, DUR   # beats and the voice warp live in timeline.py (shared with edit/score.py)
MISSING = "pallet_stone_entry"     # watch example: the jewel the fast assembly leaves out


# ---------------------------------------------------------------- math helpers
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def seg(t, a, b):
    return clamp((t - a) / (b - a)) if b > a else float(t >= b)


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease(x):  # cubic in-out
    x = clamp(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def ease_out(x, p=3):
    return 1 - (1 - clamp(x)) ** p


def ease_in(x, p=2):
    return clamp(x) ** p


def back_out(x, s=1.25):
    x = clamp(x) - 1
    return x * x * ((s + 1) * x + s) + 1


def lerp(a, b, s):
    return a + (b - a) * s


def windows(t, wins, v0=0.0, fn=ease):
    """piecewise value: wins = [(t0, t1, value_after), ...] in order"""
    v = v0
    for a, b, val in wins:
        if t <= a:
            return v
        if t < b:
            return lerp(v, val, fn(seg(t, a, b)))
        v = val
    return v


def snap_steps(x, k=0.18):
    """stepping counter: integer steps with a quick eased snap at the start of each step"""
    n = floor(x)
    return n + smooth((x - n) / k)


# ---------------------------------------------------------------- integrated speed tables
DT = 1 / 240.0
NT = int(DUR / DT) + 2


def table(speed_fn):
    acc, out = 0.0, [0.0] * NT
    for i in range(1, NT):
        tt = i * DT
        acc += speed_fn(tt) * DT
        out[i] = acc
    return out


def look(tab, t):
    x = clamp(t, 0, DUR) / DT
    i = int(x)
    f = x - i
    return tab[i] * (1 - f) + tab[min(i + 1, NT - 1)] * f


def hands_run_speed(t, peak):
    if t < T["run0"] or t > T["run1"]:
        return 0.0
    u = seg(t, T["run0"], T["run1"])
    return peak * smooth(u / 0.25) * (1 - smooth((u - 0.7) / 0.3))


def rotor_angle(t):
    """rotor swings both ways while we explain the winding"""
    a, b = T["flip1"] + 0.6, T["rotor1"] + 0.5
    if t < a or t > b + 2:
        return 0.0
    u = t - a
    env = smooth(u / 1.0) * (1 - smooth((t - b) / 2.0))
    return env * (2.6 * sin(2 * pi * 0.32 * u) + 0.9 * sin(2 * pi * 0.71 * u + 1.0))


def rotor_speed_abs(t):
    h = 1e-3
    return abs(rotor_angle(t + h) - rotor_angle(t - h)) / (2 * h)


def leak_speed(t):
    """escape wheel free-running (rev/s) while the pallet stone is missing"""
    s = hands_run_speed(t, 14.0)
    if T["flip1"] <= t < T["fix_place"]:
        s += 3.0 * smooth(seg(t, T["flip1"], T["flip1"] + 2.0)) * (1 - smooth(seg(t, T["fix_place"] - 0.6, T["fix_place"])))
    return s


TAB = {}


def build_tables():
    TAB["sec_run"] = table(lambda t: hands_run_speed(t, 2.2))
    TAB["min_run"] = table(lambda t: hands_run_speed(t, 0.9))
    TAB["hour_run"] = table(lambda t: hands_run_speed(t, 0.075))
    TAB["esc"] = table(leak_speed)
    TAB["tw"] = table(lambda t: rotor_speed_abs(t) * 0.27 * 0.6)


# ---------------------------------------------------------------- mechanism state
BEAT_HZ = 6.0  # 21,600 vph


def running_beats(t):
    """beats counted while the watch runs normally: before the failure and after the fix"""
    b = 0.0
    b += BEAT_HZ * min(t, T["run0"])
    if t > T["fix_place"] + 0.4:
        b += BEAT_HZ * (t - T["fix_place"] - 0.4)
    return b


def mech(t):
    s = {}
    beats = snap_steps(running_beats(t))
    esc_rev = -beats / 30.0 + -look(TAB["esc"], t)           # half a tooth (12 deg) per beat, 15 teeth
    s["escape"] = 2 * pi * esc_rev
    s["fourth"] = -s["escape"] / 12.0
    s["third"] = -s["fourth"] / 7.5
    s["center"] = -s["third"] / 8.0
    s["barrel"] = -s["center"] / 8.0
    # hands (clockwise = negative)
    sec_rev = beats / 360.0 + look(TAB["sec_run"], t)
    s["hand_second"] = -2 * pi * sec_rev
    s["hand_minute"] = -2 * pi * (beats / 21600.0 + look(TAB["min_run"], t))
    s["hand_hour"] = -2 * pi * (beats / 259200.0 + look(TAB["hour_run"], t))
    # balance: still while broken, amplitude grows after the fix
    tb = t - T["fix_place"] - 0.4
    if tb > 0:
        amp = 4.4 * smooth(tb / 1.2)
        s["balance"] = amp * sin(2 * pi * 3.0 * tb)
    elif t < T["run0"]:
        s["balance"] = 4.4 * sin(2 * pi * 3.0 * t)
    else:
        s["balance"] = 0.08 * sin(2 * pi * 0.4 * t) * smooth(seg(t, T["run1"], T["run1"] + 0.5))
    s["pallet"] = 0.15 * tanh(3.0 * s["balance"]) if (tb > 0 or t < T["run0"]) else 0.15
    # automatic winding
    s["rotor"] = rotor_angle(t)
    s["reduction"] = -s["rotor"] * 0.27
    s["transmission"] = 2 * pi * 0.0 + look(TAB["tw"], t)
    s["ratchet"] = -s["transmission"] * (0.7 / 3.2)
    return s


SPIN_OF = {
    "barrel_teeth": "barrel", "barrel_drum": "barrel", "barrel_cover": "barrel",
    "mainspring": "ratchet", "barrel_arbor": "ratchet",
    "ratchet_wheel": "ratchet", "ratchet_screw": "ratchet",
    "transmission_wheel": "transmission", "reduction_wheel": "reduction", "eccentric_pin": "reduction",
    "rotor": "rotor", "rotor_screw": "rotor",
    "hand_hour": "hand_hour", "hand_minute": "hand_minute", "hand_second": "hand_second",
}
for g in ("center_wheel", "third_wheel", "fourth_wheel", "escape_wheel"):
    key = g.split("_")[0]
    for suf in ("", "_pinion", "_arbor"):
        SPIN_OF[g + suf] = key
for n in ("balance", "roller", "impulse_jewel", "balance_staff"):
    SPIN_OF[n] = "balance"
for n in ("pallet_fork", "pallet_arbor"):
    SPIN_OF[n] = "pallet"


# ---------------------------------------------------------------- explode / lifts
def tower_offset(name, d, gap=5.2, tilt=7.0):
    L, sub, g = d["layer"], d["sub"], d["group"]
    if g == "case":
        return Vector((0, 0, -110)), Vector((0, 0, 0))
    if g == "crown":
        a = radians(-30)
        return Vector((cos(a) * 16, sin(a) * 16, 0)), Vector((0, 0, 0))
    sign = 1 if L < 5 else -1
    dz = (5 - L) * gap + sign * sub * gap * 0.55
    rx = radians(tilt) * sin(L * 1.7)
    ry = radians(tilt) * cos(L * 1.3)
    rz = 0.35 * sin(L * 2.1 + sub)
    return Vector((0, 0, dz)), Vector((rx, ry, rz))


RANK = {}


def explode_amount(name, d, t):
    if t < T["explode"]:
        return 0.0
    if t < T["ai_start"]:
        return back_out(seg(t, T["explode"], T["explode"] + 0.95))
    if name == MISSING:
        return 1.0 if t < T["fix0"] else 0.0   # left behind by the fast assembly
    r = RANK.get(name, 0.5)
    st = T["ai_start"] + r * (T["ai_end"] - T["ai_start"] - 0.28)
    return 1.0 - ease_in(seg(t, st, st + 0.28), 2)


LIFTS = {
    "caseback": [(16.2, 18.2, 150.0), (76.0, 78.0, 0.0)],
    "rotor": [(21.6, 23.4, 9.0), (24.0, 25.4, 48.0), (29.0, 31.2, 95.0), (74.6, 76.6, 0.0)],
    "winding": [(29.3, 31.5, 75.0), (73.6, 75.8, 0.0)],
    "bridges": [(29.6, 31.8, 16.0), (35.6, 37.6, 80.0), (71.0, 73.6, 0.0)],
    "screws": [(29.6, 31.8, 19.0), (35.6, 37.6, 86.0), (71.0, 73.6, 0.0)],
    "case": [(34.6, 36.6, -30.0), (44.0, 46.0, 0.0)],
    "bezel": [(34.6, 36.6, -30.0), (44.0, 46.0, 0.0)],
    "crown": [(34.6, 36.6, -30.0), (44.0, 46.0, 0.0)],
}
LIFT_NAME = {"barrel_cover": [(31.0, 33.0, 6.5), (70.4, 71.8, 0.0)]}
LIFTS = {g: [(W(a), W(b), v) for a, b, v in w] for g, w in LIFTS.items()}
LIFT_NAME = {g: [(W(a), W(b), v) for a, b, v in w] for g, w in LIFT_NAME.items()}


def lift(name, d, t):
    w = LIFT_NAME.get(name) or LIFTS.get(d["group"])
    return windows(t, w) if w else 0.0


def dark(t):
    return windows(t, [(T["dark0"], T["dark0"] + 2.2, 1.0), (T["fix0"], T["fix_place"] + 0.8, 0.0)], fn=smooth)


# ---------------------------------------------------------------- root (flip + turntable)
def root_rot(t):
    fl = pi * windows(t, [(T["flip0"], T["flip1"] - 0.6, 1.0), (T["flipback0"], T["assembled"] - 0.8, 0.0)])
    sp = radians(6) * sin(0.25 * t) if t < T["explode"] else 0.0
    if t > T["assembled"] - 1.5:
        sp += radians(2.2) * (t - (T["assembled"] - 1.5)) * smooth(seg(t, T["assembled"] - 1.5, T["assembled"] + 1))
    return Euler((0, fl, sp), "XYZ")


# ---------------------------------------------------------------- camera path
def sph(target, D, az, el):
    tg = Vector(target)
    a, e = radians(az), radians(el)
    return tg + D * Vector((cos(e) * cos(a), cos(e) * sin(a), sin(e)))


def MW(P, z=0.0):
    """movement design point -> world, after the flip (caseback up)"""
    return Vector((-P[0], -P[1], z))


MID_ESC = (2.3, -6.0)      # between the escape wheel and the entry pallet
CAM = [  # t, target, distance, azimuth, elevation, lens, fstop
    (0.0, (0, 1, -2), 215, -84, 62, 85, 11),
    (1.2, (0, 1, -3), 190, -86, 58, 85, 11),
    (2.4, (0, 0, -9), 182, -66, 15, 85, 16),
    (5.4, (0, 0, -9), 175, -50, 13, 85, 16),
    (7.3, (0, 2, -2), 175, -88, 60, 85, 11),
    (9.6, (1.5, -1.5, 2), 96, -90, 72, 85, 6.3),
    (12.8, (1.5, -1.5, 2), 88, -90, 74, 85, 6.3),
    (15.0, (1.5, -1.5, 2), 86, -91, 74, 85, 6.3),
    (16.6, (0, 0, 0), 120, -100, 40, 85, 9),
    (18.6, (0, 0, 4), 62, -96, 70, 85, 8),
    (22.0, (0, 0, 5), 58, -80, 66, 85, 8),
    (25.5, (*MW(((Pr1[0] + Ptw[0]) / 2, (Pr1[1] + Ptw[1]) / 2))[:2], 4.8), 27, -150, 52, 85, 5.6),
    (29.0, (*MW(((Pr1[0] + Ptw[0]) / 2, (Pr1[1] + Ptw[1]) / 2))[:2], 4.8), 30, -165, 50, 85, 5.6),
    (31.5, (*MW(Pb)[:2], 3.0), 46, -120, 55, 85, 6.3),
    (35.5, (*MW(Pb)[:2], 3.0), 40, -140, 50, 85, 6.3),
    (37.2, (*MW(Pc)[:2], 2.2), 12, -150, 20, 24, 3.5),
    (40.0, (*MW(Pt)[:2], 2.5), 9.5, -168, 18, 24, 3.5),
    (42.6, (*MW(Pf)[:2], 3.0), 9.0, -185, 24, 24, 3.5),
    (45.5, (*MW(MID_ESC)[:2], 2.2), 26, -150, 64, 85, 4.5),
    (50.0, (*MW(MID_ESC)[:2], 2.2), 22, -140, 66, 85, 4.5),
    (55.0, (*MW(MID_ESC)[:2], 2.2), 19, -134, 67, 85, 4.0),
    (61.5, (*MW(MID_ESC)[:2], 2.2), 15, -130, 68, 85, 4.0),
    (66.0, (*MW(MID_ESC)[:2], 2.2), 17, -128, 66, 85, 4.0),
    (70.5, (*MW(((Pbal[0] + Pp[0]) / 2, (Pbal[1] + Pp[1]) / 2))[:2], 3.0), 32, -120, 58, 85, 6.3),
    (74.0, (0, 0, 4), 70, -86, 62, 85, 8),
    (78.0, (0, 0, 2), 110, -92, 60, 85, 9),
    (82.0, (0, 1, -2), 180, -88, 58, 85, 11),
    (92.0, (0, 1, -2), 168, -86, 60, 85, 11),
]


CAM = [(W(k[0]),) + tuple(k[1:]) for k in CAM]


def _hermite(keys, t, get):
    ts = [k[0] for k in keys]
    if t <= ts[0]:
        return get(keys[0])
    if t >= ts[-1]:
        return get(keys[-1])
    i = max(j for j in range(len(ts)) if ts[j] <= t)
    t0, t1 = ts[i], ts[i + 1]
    p0, p1 = get(keys[i]), get(keys[i + 1])
    pm = get(keys[i - 1]) if i > 0 else p0
    pp = get(keys[i + 2]) if i + 2 < len(keys) else p1
    tm = ts[i - 1] if i > 0 else t0 - 1
    tp = ts[i + 2] if i + 2 < len(keys) else t1 + 1
    m0 = (p1 - pm) / (t1 - tm)
    m1 = (pp - p0) / (tp - t0)
    s = (t - t0) / (t1 - t0)
    h = t1 - t0
    h00, h10, h01, h11 = 2 * s ** 3 - 3 * s ** 2 + 1, s ** 3 - 2 * s ** 2 + s, -2 * s ** 3 + 3 * s ** 2, s ** 3 - s ** 2
    return h00 * p0 + h10 * h * m0 + h01 * p1 + h11 * h * m1


def cam_state(t):
    pos = _hermite(CAM, t, lambda k: sph(k[1], k[2], k[3], k[4]))
    tgt = _hermite(CAM, t, lambda k: Vector(k[1]))
    ts = [k[0] for k in CAM]
    i = max([j for j in range(len(ts)) if ts[j] <= t] or [0])
    j = min(i + 1, len(CAM) - 1)
    s = smooth(seg(t, CAM[i][0], CAM[j][0])) if j != i else 0
    lens = lerp(CAM[i][5], CAM[j][5], s)
    fstop = lerp(CAM[i][6], CAM[j][6], s)
    return pos, tgt, lens, fstop


# ---------------------------------------------------------------- scene setup
def setup(pct=100, samples=32, mblur=False):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    parts.build_all()
    build_tables()
    root = kit.empty("WATCH")
    for n, d in PARTS.items():
        d["ob"].parent = root
    tw = bpy.data.objects["tweezers"]
    order = sorted(PARTS.items(), key=lambda kv: (-(kv[1]["layer"]), kv[1]["sub"]))
    for i, (n, d) in enumerate(order):
        RANK[n] = i / max(len(order) - 1, 1)
    studio.render_settings(pct=pct, samples=samples, mblur=mblur)
    studio.world()
    sun = studio.sun()
    spot_d = bpy.data.lights.new("beam", "SPOT")
    spot_d.energy = 0
    spot_d.spot_size = radians(16)
    spot_d.spot_blend = 0.6
    spot = bpy.data.objects.new("beam", spot_d)
    bpy.context.scene.collection.objects.link(spot)
    spot.location = Vector((-MW(MID_ESC)[0], 0, 0)) * 0 + Vector((MW(MID_ESC)[0] + 20, MW(MID_ESC)[1] - 30, 70))
    tgt = MW(MID_ESC, 2)
    spot.rotation_euler = (tgt - spot.location).to_track_quat("-Z", "Y").to_euler()
    cam = studio.camera()
    # orange outline that marks the empty jewel slot
    fr = kit.rounded_poly([(-0.75, -0.32), (0.75, -0.32), (0.75, 0.32), (-0.75, 0.32)], 0.12, 3)
    inner = kit.rounded_poly([(-0.6, -0.2), (0.6, -0.2), (0.6, 0.2), (-0.6, 0.2)], 0.08, 3)
    mk = kit.outline("slot_marker", [fr, inner], 0.05, kit.MATS["accent"], bevel=0.01)
    mk.parent = root
    mk.hide_render = True
    return dict(root=root, tw=tw, sun=sun, spot=spot, cam=cam, marker=mk)


WORLD_NODES = {}


def world_dark_hook():
    """insert a darkness multiplier into the world: camera background and lighting both dim"""
    nt = bpy.context.scene.world.node_tree
    out = [n for n in nt.nodes if n.type == "OUTPUT_WORLD"][0]
    src = out.inputs[0].links[0].from_socket
    val = nt.nodes.new("ShaderNodeValue")
    val.name = "DARK"
    val.outputs[0].default_value = 1.0
    blk = nt.nodes.new("ShaderNodeBackground")
    blk.inputs[0].default_value = (0.004, 0.005, 0.007, 1)
    mx = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(val.outputs[0], mx.inputs[0])
    nt.links.new(src, mx.inputs[1])
    nt.links.new(blk.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs[0])
    WORLD_NODES["dark"] = val


def mk_home(d, m):
    piv = Vector((Pp[0], -Pp[1], 0))
    rel = d["base_loc"] - piv
    return piv + Matrix.Rotation(m["pallet"], 3, "Z") @ rel


def pose(t, S):
    root, tw, cam = S["root"], S["tw"], S["cam"]
    m = mech(t)
    root.rotation_euler = root_rot(t)
    for n, d in PARTS.items():
        ob = d["ob"]
        loc = d["base_loc"].copy()
        rot = d["base_rot"].copy()
        e = explode_amount(n, d, t)
        if e:
            off, tl = tower_offset(n, d)
            # gentle float while the tower hangs in the air
            fl = 1.0 + 0.05 * sin(1.3 * t + d["layer"])
            loc += off * e * fl
            rot.x += tl.x * e
            rot.y += tl.y * e
            rot.z += tl.z * e
        L = lift(n, d, t)
        loc.z -= L
        key = SPIN_OF.get(n)
        ang = m[key] if key else 0.0
        if n.startswith("pallet_stone"):
            ang = m["pallet"]
            piv = Vector((Pp[0], -Pp[1], 0))
            rel = d["base_loc"] - piv
            rel2 = Matrix.Rotation(ang, 3, "Z") @ rel
            loc = loc + (rel2 - rel)
        if n == "magic_lever":
            phi = m["reduction"]
            c0 = Vector((Pr1[0], -Pr1[1], d["base_loc"].z))
            loc = Vector((c0.x + 0.55 * cos(phi), c0.y + 0.55 * sin(phi), loc.z)) + (loc - d["base_loc"])
            ang = 0.12 * sin(phi)
        rot.z += ang
        ob.location = loc
        ob.rotation_euler = rot
        if n == "hairspring":
            b = m["balance"]
            ob.rotation_euler.z = d["base_rot"].z + 0.18 * b
            k = 1 + 0.035 * b / 4.4
            ob.scale = (k, k, 1)
        hide = False
        if d["group"] == "caseback" and W(18.3) < t < W(75.8):
            hide = True
        if n == MISSING:
            hide = T["ai_end"] + 1.2 < t < T["fix0"]
            if T["ai_start"] < t <= T["ai_end"] + 1.2:     # left behind: drifts down and away
                u = seg(t, T["ai_start"] + 0.6, T["ai_end"] + 1.2)
                ob.location = ob.location + Vector((6 * u, -3 * u, -40 * ease_in(u, 2)))
        ob.hide_render = hide
    # tweezers bring the stone back
    st = PARTS[MISSING]["ob"]
    a, pl, b = T["fix0"] + 0.5, T["fix_place"], T["fix_place"] + 1.6
    if a < t < b:
        bpy.context.view_layer.update()
        home = st.matrix_world.translation.copy()
        u_in = ease(seg(t, a, pl))
        u_out = ease(seg(t, pl + 0.3, b))
        dirv = Vector((0.50, 0.63, 0.59)).normalized()     # enters from the top of the frame
        away = dirv * 16
        tip = home + away * (1 - u_in) + away * u_out
        tw.hide_render = False
        tw.location = tip
        tw.rotation_euler = dirv.to_track_quat("X", "Z").to_euler()
        if t < pl:
            st.matrix_world.translation = tip
            bpy.context.view_layer.update()
            # convert to parent space
            st.location = root.matrix_world.inverted() @ tip
    else:
        tw.hide_render = True
    mk = S.get("marker")
    if mk:
        st_home = PARTS[MISSING]
        mk.location = mk_home(st_home, m) + Vector((0, 0, -0.45))
        mk.rotation_euler = st.rotation_euler.copy()
        pulse = 1.0 + 0.08 * sin(2 * pi * 1.2 * t)
        mk.scale = (pulse, pulse, 1)
        mk.hide_render = not (T["fault"] + 0.6 < t < T["fix0"] + 1.6)
    # light
    dk = dark(t)
    if "dark" in WORLD_NODES:
        WORLD_NODES["dark"].outputs[0].default_value = 0.88 * dk
    S["sun"].data.energy = 3.0 * (1 - 0.9 * dk)
    S["spot"].data.energy = 2.5e5 * dk
    # camera
    pos, tgt, lens, fstop = cam_state(t)
    studio.aim(cam, pos, tgt, lens=lens, fstop=fstop)


# ---------------------------------------------------------------- render entry points
def stills(outdir, times, pct, samples):
    S = setup(pct, samples)
    world_dark_hook()
    os.makedirs(outdir, exist_ok=True)
    for t in times:
        pose(t, S)
        bpy.context.view_layer.update()
        bpy.context.scene.render.filepath = f"{outdir}/t{t:06.2f}.jpg"
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        print("STILL", t, round(time.time() - t0, 2))


def anim(outdir, f0, f1, pct, samples):
    S = setup(pct, samples, mblur=True)
    world_dark_hook()
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = f0, f1
    sc.render.motion_blur_shutter = 0.5
    try:
        sc.render.motion_blur_steps = 3
    except Exception:
        pass
    objs = [d["ob"] for d in PARTS.values()] + [S["root"], S["tw"], S["cam"], S["marker"]]
    t0 = time.time()
    for f in range(f0, f1 + 1):
        t = f / FPS
        pose(t, S)
        for ob in objs:
            ob.keyframe_insert("location", frame=f)
            ob.keyframe_insert("rotation_euler", frame=f)
            if ob.name in ("hairspring", "slot_marker"):
                ob.keyframe_insert("scale", frame=f)
            ob.keyframe_insert("hide_render", frame=f)
        S["cam"].data.keyframe_insert("lens", frame=f)
        S["cam"].data.dof.keyframe_insert("focus_distance", frame=f)
        S["cam"].data.dof.keyframe_insert("aperture_fstop", frame=f)
        WORLD_NODES["dark"].outputs[0].keyframe_insert("default_value", frame=f)
        S["sun"].data.keyframe_insert("energy", frame=f)
        S["spot"].data.keyframe_insert("energy", frame=f)
    print("BAKED", f1 - f0 + 1, "frames in", round(time.time() - t0, 1), "s")
    for ad in [o.animation_data for o in objs] + [S["cam"].data.animation_data]:
        if ad and ad.action:
            for fc in ad.action.fcurves if hasattr(ad.action, "fcurves") else []:
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"
    os.makedirs(outdir, exist_ok=True)
    sc.render.filepath = outdir + "/"
    t0 = time.time()
    bpy.ops.render.render(animation=True)
    print("RENDERED", f1 - f0 + 1, "frames in", round(time.time() - t0, 1), "s")


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    mode = argv[0] if argv else "stills"
    if mode == "stills":
        times = [float(x) for x in argv[2].split(",")]
        stills(argv[1], times, int(argv[3]) if len(argv) > 3 else 50, int(argv[4]) if len(argv) > 4 else 24)
    elif mode == "anim":
        anim(argv[1], int(argv[2]), int(argv[3]), int(argv[4]) if len(argv) > 4 else 100, int(argv[5]) if len(argv) > 5 else 24)
