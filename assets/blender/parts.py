"""Watch + 4R36-style movement, built from kit.py. 1 BU = 1 mm.

Watch frame: dial faces +Z, 12 o'clock +Y, 3 o'clock +X. The movement is designed caseback-up
(bridges at +h) and flipped into the watch frame by place_mov(): (x, y, z) -> (x, -y, -z), rot X = pi.

Every part is registered in PARTS[name] = {ob, base_loc, base_rot, layer, spin_axis, group}.
"""
import math, bpy
from math import pi, cos, sin, atan2, hypot, radians
from mathutils import Vector, Euler
import kit
from kit import MATS, TAU

PARTS = {}
FONT_BEZEL = "C:/Windows/Fonts/bahnschrift.ttf"
FONT_SCRIPT = "C:/Windows/Fonts/segoesc.ttf"
FONT_DAY = "C:/Windows/Fonts/arialbd.ttf"


def reg(ob, layer, group, spin=False, sub=0.0):
    PARTS[ob.name] = dict(ob=ob, base_loc=ob.location.copy(), base_rot=ob.rotation_euler.copy(),
                          layer=layer, group=group, spin=spin, sub=sub)
    return ob


def place_mov(ob, x, y, z, rot=0.0):
    ob.location = (x, -y, -z)
    ob.rotation_euler = (pi, 0, rot)
    return ob


def place(ob, x, y, z, rot=0.0):
    ob.location = (x, y, z)
    ob.rotation_euler = (0, 0, rot)
    return ob


# ---------------------------------------------------------------- movement geometry (caseback-up, mm)
R_MOV = 13.7
Pb = (-4.35, 4.35)    # barrel
Pc = (0.0, 0.0)       # centre wheel
Pt = (4.84, 1.76)     # third
Pf = (5.60, -2.57)    # fourth
Pe = (2.22, -4.52)    # escape
Pp = (0.77, -7.03)    # pallet pivot
Pbal = (-1.83, -8.53)  # balance
Pr1 = (-2.14, -1.80)  # first reduction wheel (eccentric)
Ptw = (-4.60, 0.40)   # transmission wheel (driven by the Magic Lever)


def V(p):
    return Vector((p[0], p[1]))


def ang(a, b):
    return atan2(b[1] - a[1], b[0] - a[0])


def bridge_loop(points, r=1.4):
    return kit.rounded_poly(points, r, 8)


def build_movement(c):
    M = MATS
    out = {}
    # main plate ------------------------------------------------------
    holes = [kit.circle_pts(0.9, 32, cx=Pc[0], cy=Pc[1])]
    plate = kit.outline("main_plate", [kit.circle_pts(R_MOV, 256)] + holes, 1.3, M["steel_satin"], bevel=0.08, c=c)
    place_mov(plate, 0, 0, 0); reg(plate, 5, "plate")
    # pillars on the plate under the bridges
    for i, (x, y) in enumerate([(-9.6, 6.5), (-1.5, 9.8), (8.6, 5.6), (9.6, -5.6), (-6.4, -6.6), (3.6, -10.6)]):
        p = kit.lathe(f"pillar_{i}", [(0, 0), (0.75, 0), (0.75, 2.1), (0.55, 2.2), (0, 2.2)], M["steel_satin"], 32, c)
        place_mov(p, x, y, 1.3); reg(p, 5, "plate", sub=0.2)

    # barrel -----------------------------------------------------------
    bt = kit.wheel("barrel_teeth", 80, 5.2, 0.35, M["brass"], spokes=0, arbor=0.9, c=c)
    place_mov(bt, *Pb, 1.5); reg(bt, 6, "barrel", spin=True)
    drum = kit.lathe("barrel_drum", [(0.9, 0), (4.85, 0), (4.85, 2.0), (4.6, 2.0), (4.6, 0.25), (0.9, 0.25)], M["brass"], 128, c)
    place_mov(drum, *Pb, 1.5); reg(drum, 6, "barrel", spin=True)
    spring = kit.spiral_strip("mainspring", 1.1, 4.4, 9, 1.6, 0.08, M["steel_dark"], c=c)
    place_mov(spring, *Pb, 1.75); reg(spring, 6, "barrel", spin=True, sub=0.6)
    cover = kit.disc("barrel_cover", 4.62, 0.18, M["brass"], c=c)
    place_mov(cover, *Pb, 3.5); reg(cover, 6, "barrel", spin=True, sub=1.2)
    arb = kit.arbor("barrel_arbor", 0.55, 1.2, 4.6, M["steel"], c=c)
    place_mov(arb, *Pb, 0); reg(arb, 6, "barrel", spin=True, sub=1.4)

    # train -------------------------------------------------------------
    def train(name, n, R, z, leaves, pr, pz0, pz1, mat, spokes=4, kind="cycloid", az0=0.0, layer=6):
        w = kit.wheel(name, n, R, 0.2 if kind == "cycloid" else 0.16, mat, spokes=spokes, kind=kind, c=c, a0=az0)
        pin = kit.pinion(name + "_pinion", leaves, pr, pz1 - pz0, M["steel"], c=c)
        arb = kit.arbor(name + "_arbor", 0.17, 0.2, 3.7, M["steel"], c=c)
        out[name] = w
        return w, pin, arb, z, pz0

    specs = [
        ("center_wheel", 64, 4.4, 2.0, 10, 0.95, 1.4, 2.0, M["gold"], 4, "cycloid", Pc, 0.0),
        ("third_wheel", 60, 3.8, 2.5, 8, 0.75, 1.9, 2.5, M["gold"], 4, "cycloid", Pt, 0.3),
        ("fourth_wheel", 84, 3.4, 3.0, 8, 0.60, 2.4, 3.0, M["gold"], 4, "cycloid", Pf, 0.1),
        ("escape_wheel", 15, 2.3, 1.95, 7, 0.50, 2.1, 3.2, M["steel"], 5, "club", Pe, 0.0),
    ]
    for name, n, R, z, lv, pr, pz0, pz1, mat, sp, kind, P, a0 in specs:
        w, pin, arb, z, pz0 = train(name, n, R, z, lv, pr, pz0, pz1, mat, sp, kind, a0)
        place_mov(w, *P, z); reg(w, 6, name, spin=True, sub=0.3)
        place_mov(pin, *P, pz0); reg(pin, 6, name, spin=True, sub=0.3)
        place_mov(arb, *P, 0); reg(arb, 6, name, spin=True, sub=0.3)

    # pallet fork -------------------------------------------------------
    fork_objs = []
    to_e = ang(Pp, Pe)
    to_b = ang(Pp, Pbal)
    hub = kit.ring("pf_hub", 0.55, 0.15, 0.22, M["steel"], c=c)
    fork_objs.append(hub)
    # arms to the two pallet stones (stones sit on escape wheel tip circle at +-~32 deg about line Pe->Pp)
    base = ang(Pe, Pp)
    stones = {}
    for side, sgn in (("entry", 1), ("exit", -1)):
        a = base + sgn * radians(33)
        sp = (Pe[0] + 2.62 * cos(a), Pe[1] + 2.62 * sin(a))   # just outside the tooth tips (r_tip ~ 2.6)
        L = hypot(sp[0] - Pp[0], sp[1] - Pp[1])
        arm = kit.box(f"pf_arm_{side}", L + 0.3, 0.42, 0.22, M["steel"], c=c)
        mid = ((sp[0] + Pp[0]) / 2, (sp[1] + Pp[1]) / 2)
        arm.location = (mid[0] - Pp[0], mid[1] - Pp[1], 0)
        arm.rotation_euler = (0, 0, ang(Pp, sp))
        fork_objs.append(arm)
        st = kit.box(f"pallet_stone_{side}", 0.95, 0.24, 0.26, M["ruby"], c=c, bev=0.02)
        # stone points toward the escape wheel centre
        inward = ang(sp, Pe)
        st_pos = (sp[0] + 0.25 * cos(inward), sp[1] + 0.25 * sin(inward))
        place_mov(st, *st_pos, 1.93, rot=inward)
        stones[side] = st
    lever = kit.box("pf_lever", 2.4, 0.34, 0.2, M["steel"], c=c)
    lever.location = (1.2 * cos(to_b), 1.2 * sin(to_b), 0)
    lever.rotation_euler = (0, 0, to_b)
    fork_objs.append(lever)
    for s in (1, -1):
        horn = kit.box(f"pf_horn{s}", 0.7, 0.18, 0.2, M["steel"], c=c)
        a = to_b + s * radians(16)
        horn.location = (2.55 * cos(to_b) + 0.32 * cos(a + s * 1.2), 2.55 * sin(to_b) + 0.32 * sin(a + s * 1.2), 0)
        horn.rotation_euler = (0, 0, to_b + s * radians(35))
        fork_objs.append(horn)
    # join fork pieces into one object, origin at the pivot
    fork = kit.join(fork_objs, "pallet_fork")
    place_mov(fork, *Pp, 1.93); reg(fork, 6, "pallet", spin=True, sub=0.35)
    parb = kit.arbor("pallet_arbor", 0.14, 0.4, 3.6, M["steel"], c=c)
    place_mov(parb, *Pp, 0); reg(parb, 6, "pallet", spin=True, sub=0.35)
    for side, st in stones.items():
        reg(st, 6, "pallet", spin=True, sub=0.35)
        st["pivot"] = (Pp[0], -Pp[1])
    out["stones"] = stones

    # balance -----------------------------------------------------------
    bal_rim = kit.ring("bal_rim", 4.4, 3.95, 0.42, M["gold"], c=c)
    arms = []
    for k in range(3):
        a = k * TAU / 3 + 0.2
        arm = kit.box(f"bal_arm{k}", 3.6, 0.45, 0.3, M["gold"], c=c)
        arm.location = (1.95 * cos(a), 1.95 * sin(a), 0.06)
        arm.rotation_euler = (0, 0, a)
        arms.append(arm)
    bhub = kit.ring("bal_hub", 0.6, 0.15, 0.36, M["gold"], c=c)
    bal = kit.join(arms + [bhub, bal_rim], "balance")
    place_mov(bal, *Pbal, 2.9); reg(bal, 6, "balance", spin=True, sub=0.8)
    hs = kit.spiral_strip("hairspring", 0.55, 2.7, 11, 0.13, 0.045, M["blued"], c=c, outer_tail=0.4)
    place_mov(hs, *Pbal, 3.42); reg(hs, 6, "balance", spin=True, sub=1.0)
    roller = kit.disc("roller", 0.62, 0.16, M["steel"], c=c)
    place_mov(roller, *Pbal, 2.0); reg(roller, 6, "balance", spin=True, sub=0.8)
    ij = kit.lathe("impulse_jewel", [(0, 0), (0.09, 0), (0.09, 0.5), (0, 0.5)], M["ruby"], 16, c)
    for vv in ij.data.vertices:
        vv.co.x += 0.48
    place_mov(ij, Pbal[0], Pbal[1], 1.7); reg(ij, 6, "balance", spin=True, sub=0.8)
    bstaff = kit.arbor("balance_staff", 0.2, 0.3, 3.9, M["steel"], c=c)
    place_mov(bstaff, *Pbal, 0); reg(bstaff, 6, "balance", spin=True, sub=0.8)

    # bridges -----------------------------------------------------------
    def bridge(name, pts, z, th, holes_at, r_round=1.6, mat=None, layer=7):
        loops = [bridge_loop(pts, r_round)] + [kit.circle_pts(0.65, 32, cx=x, cy=y) for x, y in holes_at]
        b = kit.outline(name, loops, th, mat or M["steel_grain"], bevel=0.1, c=c)
        place_mov(b, 0, 0, z); reg(b, layer, "bridges")
        return b

    bridge("barrel_bridge", [(-12.6, 4.5), (-9.8, 9.9), (-4.5, 11.2), (-0.6, 9.4), (-1.6, 4.6), (-3.2, 1.8), (-7.0, -2.4), (-11.4, -0.4)],
           3.7, 0.6, [Pb, Ptw])
    bridge("train_bridge", [(1.6, 5.4), (6.0, 6.6), (10.4, 3.4), (10.8, -3.4), (7.6, -6.4), (3.4, -6.6), (0.6, -3.4), (-1.6, -1.0), (-1.0, 1.8), (0.6, 2.6)],
           3.4, 0.6, [Pc, Pt, Pf, Pe])
    bridge("pallet_bridge", [(-0.6, -6.0), (2.4, -6.3), (2.2, -8.1), (-0.4, -8.0)], 3.0, 0.45, [Pp], r_round=0.6)
    cock = bridge("balance_cock", [(-11.2, -6.2), (-7.0, -7.4), (-3.8, -10.4), (-1.0, -11.0), (0.6, -9.4), (-1.2, -6.9), (-5.4, -5.1), (-10.6, -3.6)],
                  3.9, 0.7, [Pbal], r_round=1.2)
    # jewels on bridges (dome outward = toward caseback)
    for i, (P, z) in enumerate([(Pc, 4.05), (Pt, 4.05), (Pf, 4.05), (Pe, 4.05), (Pp, 3.5), (Pbal, 4.65), (Ptw, 4.35)]):
        j = kit.jewel(f"jewel_{i}", c=c)
        place_mov(j, *P, z + 0.12); reg(j, 7, "bridges", sub=0.6)
    # shock spring (lyre) on the balance jewel
    shock = kit.ring("shock_spring", 1.05, 0.75, 0.08, M["steel"], c=c)
    place_mov(shock, *Pbal, 4.82); reg(shock, 7, "bridges", sub=0.9)
    # screws on bridges
    for i, (x, y, z) in enumerate([(-11.0, 2.8, 4.3), (-6.2, 9.6, 4.3), (-1.2, 7.8, 4.3), (8.6, 3.0, 4.0), (8.9, -3.0, 4.0),
                                   (4.6, -5.6, 4.0), (1.75, -7.55, 3.45), (-9.3, -5.0, 4.6), (-0.5, -9.9, 4.6)]):
        s = kit.screw(f"screw_{i}", r=0.62, h=0.42, c=c)
        place_mov(s, x, y, z, rot=i * 0.7); reg(s, 7, "screws", sub=1.4)

    # automatic winding: ratchet, Magic Lever, reduction wheels, rotor ------------------
    ratchet = kit.wheel("ratchet_wheel", 40, 3.2, 0.35, M["steel_grain"], spokes=0, kind="ratchet", arbor=0.6, c=c)
    place_mov(ratchet, *Pb, 4.32); reg(ratchet, 8, "winding", spin=True)
    rs = kit.screw("ratchet_screw", r=1.0, h=0.5, c=c)
    place_mov(rs, *Pb, 4.67); reg(rs, 8, "winding", spin=True, sub=0.5)
    click = kit.box("click", 2.2, 0.55, 0.3, M["steel"], c=c)
    place_mov(click, Pb[0] + 3.6, Pb[1] + 1.4, 4.35, rot=radians(-60)); reg(click, 8, "winding")

    tw = kit.wheel("transmission_wheel", 24, 1.8, 0.25, M["steel"], spokes=0, kind="ratchet", arbor=0.3, c=c)
    place_mov(tw, *Ptw, 4.62); reg(tw, 8, "winding", spin=True, sub=0.3)
    r1 = kit.wheel("reduction_wheel", 48, 2.2, 0.22, M["gold"], spokes=3, c=c)
    place_mov(r1, *Pr1, 4.55); reg(r1, 8, "winding", spin=True, sub=0.3)
    ecc = kit.lathe("eccentric_pin", [(0, 0), (0.28, 0), (0.28, 0.6), (0, 0.6)], M["steel"], 24, c)
    for vv in ecc.data.vertices:
        vv.co.x += 0.55
    place_mov(ecc, Pr1[0], Pr1[1], 4.75); reg(ecc, 8, "winding", spin=True, sub=0.5)
    # Magic Lever: one-piece Y lever, ring on the eccentric pin, two pawls reaching the transmission wheel
    mlp = []
    ringm = kit.ring("ml_ring", 0.55, 0.3, 0.14, M["steel"], c=c)
    mlp.append(ringm)
    to_tw = ang(Pr1, Ptw)
    Ltw = hypot(Ptw[0] - Pr1[0], Ptw[1] - Pr1[1])
    stem = kit.box("ml_stem", Ltw * 0.55, 0.42, 0.14, M["steel"], c=c)
    stem.location = (Ltw * 0.27 * cos(to_tw), Ltw * 0.27 * sin(to_tw), 0)
    stem.rotation_euler = (0, 0, to_tw)
    mlp.append(stem)
    for s in (1, -1):
        a = to_tw + s * radians(30)
        prong = kit.box(f"ml_prong{s}", Ltw * 0.55, 0.3, 0.14, M["steel"], c=c)
        base_pt = (Ltw * 0.52 * cos(to_tw), Ltw * 0.52 * sin(to_tw))
        prong.location = (base_pt[0] + Ltw * 0.25 * cos(a), base_pt[1] + Ltw * 0.25 * sin(a), 0)
        prong.rotation_euler = (0, 0, a)
        mlp.append(prong)
        hook = kit.box(f"ml_hook{s}", 0.5, 0.26, 0.14, M["steel"], c=c)
        tip = (base_pt[0] + Ltw * 0.5 * cos(a), base_pt[1] + Ltw * 0.5 * sin(a))
        hook.location = (tip[0], tip[1], 0)
        hook.rotation_euler = (0, 0, a - s * radians(70))
        mlp.append(hook)
    ml = kit.join(mlp, "magic_lever")
    place_mov(ml, Pr1[0] + 0.55, Pr1[1], 4.95); reg(ml, 8, "winding", sub=0.8)

    # rotor
    rotor_loop = kit.arc_pts(12.9, pi, TAU, 96) + kit.arc_pts(2.2, TAU, pi, 24)
    rotor = kit.outline("rotor", [kit.rounded_poly(rotor_loop, 0.8, 4)], 0.5, M["steel_grain"], bevel=0.12, c=c)
    weight = kit.outline("rotor_weight", [kit.arc_pts(12.9, pi + 0.05, TAU - 0.05, 80) + kit.arc_pts(10.6, TAU - 0.05, pi + 0.05, 80)],
                         1.1, M["steel_satin"], bevel=0.15, c=c)
    weight.location.z = -0.3
    rhub = kit.lathe("rotor_hub", [(0.5, -0.4), (2.3, -0.4), (2.3, 0.7), (1.6, 0.9), (0.5, 0.9)], M["steel"], 64, c)
    rotor = kit.join([rotor, weight, rhub], "rotor")
    place_mov(rotor, 0, 0, 5.3); reg(rotor, 9, "rotor", spin=True)
    rpin = kit.screw("rotor_screw", r=0.9, h=0.45, c=c)
    place_mov(rpin, 0, 0, 6.2); reg(rpin, 9, "rotor", spin=True, sub=0.5)
    return out


# ---------------------------------------------------------------- dial side (watch frame, +Z up)
def hand_outline(kind):
    if kind == "hour":
        return [(-0.55, -2.2), (0.55, -2.2), (0.95, 0.2), (0.95, 5.6), (0, 7.9), (-0.95, 5.6), (-0.95, 0.2)]
    if kind == "minute":
        return [(-0.45, -2.6), (0.45, -2.6), (0.62, 0.3), (0.62, 9.6), (1.3, 9.9), (0, 12.4), (-1.3, 9.9), (-0.62, 9.6), (-0.62, 0.3)]
    return [(-0.22, -4.2), (0.22, -4.2), (0.14, 12.9), (0, 13.2), (-0.14, 12.9)]


def build_dial_side(c):
    M = MATS
    # calendar discs
    date_ring = kit.ring("date_ring", 12.8, 10.0, 0.14, M["disc_white"], c=c)
    nums = []
    for d in range(1, 32):
        a = -TAU * (d - 6) / 31            # day 6 sits at 3 o'clock (angle 0)
        t = kit.text_obj(f"date_{d}", str(d), 1.45, 0.03, M["print_dark"], FONT_DAY, c=c)
        t.location = (11.35 * cos(a), 11.35 * sin(a), 0.14)
        t.rotation_euler = (0, 0, a - pi / 2 + pi / 2)
        nums.append(t)
    date_ring = kit.join(nums + [date_ring], "date_ring")
    place(date_ring, 0, 0, 0.18); reg(date_ring, 4, "calendar", spin=True)
    day_disc = kit.ring("day_disc", 9.95, 3.0, 0.12, M["disc_white"], c=c)
    days = []
    for k, dname in enumerate(["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]):
        a = -TAU * k / 7
        t = kit.text_obj(f"day_{dname}", dname, 1.35, 0.03, M["print_dark"], FONT_DAY, c=c)
        t.location = (8.05 * cos(a), 8.05 * sin(a), 0.12)
        t.rotation_euler = (0, 0, a)
        days.append(t)
    day_disc = kit.join(days + [day_disc], "day_disc")
    place(day_disc, 0, 0, 0.36); reg(day_disc, 4, "calendar", spin=True, sub=0.3)

    # dial with day-date window at 3 o'clock
    win = kit.rounded_poly([(6.4, -1.05), (13.0, -1.05), (13.0, 1.05), (6.4, 1.05)], 0.25, 3)
    dial = kit.outline("dial", [kit.circle_pts(14.3, 256), win, kit.circle_pts(0.7, 24)], 0.35, M["dial"], bevel=0.06, c=c)
    place(dial, 0, 0, 0.6); reg(dial, 3, "dial")
    deco = []
    z0 = 0.95
    # minute track
    for k in range(60):
        a = pi / 2 - TAU * k / 60
        L = 1.0 if k % 5 == 0 else 0.55
        tk = kit.box(f"tick{k}", L, 0.16 if k % 5 else 0.22, 0.02, M["print_dark"], c=c, bev=0.005)
        tk.location = ((13.55 - L / 2) * cos(a), (13.55 - L / 2) * sin(a), z0)
        tk.rotation_euler = (0, 0, a)
        deco.append(tk)
    # hour markers
    for h in range(12):
        a = pi / 2 - TAU * h / 12
        x, y = 10.9 * cos(a), 10.9 * sin(a)
        if h == 3:
            fr = kit.outline("window_frame", [kit.rounded_poly([(6.2, -1.3), (13.2, -1.3), (13.2, 1.3), (6.2, 1.3)], 0.4, 3), win],
                             0.18, M["steel"], bevel=0.04, c=c)
            fr.location.z = z0
            deco.append(fr)
            continue
        if h == 0:
            tri = [(0, -1.4), (1.25, 1.15), (-1.25, 1.15)]
            sur = kit.outline("idx12", [kit.rounded_poly([(0, -1.75), (1.6, 1.4), (-1.6, 1.4)], 0.3, 4)], 0.3, M["steel"], bevel=0.05, c=c)
            lum = kit.outline("idx12_lume", [kit.rounded_poly(tri, 0.2, 4)], 0.36, M["lume"], bevel=0.05, c=c)
            for o in (sur, lum):
                o.location = (x, y + 0.2, z0)
                deco.append(o)
            continue
        if h in (6, 9):
            L = 3.0
            sur = kit.box(f"idx{h}", L + 0.7, 1.7, 0.3, M["steel"], c=c, bev=0.05)
            lum = kit.box(f"idx{h}_lume", L, 1.15, 0.36, M["lume"], c=c, bev=0.05)
            for o in (sur, lum):
                o.location = (x * 0.98, y * 0.98, z0)
                o.rotation_euler = (0, 0, a)
                deco.append(o)
            continue
        sur = kit.disc(f"idx{h}", 1.12, 0.3, M["steel"], c=c)
        lum = kit.disc(f"idx{h}_lume", 0.9, 0.36, M["lume"], c=c)
        for o in (sur, lum):
            o.location = (x, y, z0)
            deco.append(o)
    auto = kit.text_obj("txt_auto", "Automatic", 1.55, 0.02, M["print_dark"], FONT_SCRIPT, c=c)
    auto.location = (0, -5.2, z0)
    deco.append(auto)
    reg(kit.join(deco, "dial_print"), 3, "dial", sub=0.25)

    # hands (10:10:35 pose)
    hands = {}
    for kind, z, th, mat in (("hour", 1.5, 0.18, M["steel"]), ("minute", 1.8, 0.18, M["steel"]), ("second", 2.1, 0.12, M["steel_dark"])):
        h = kit.outline(f"hand_{kind}", [kit.rounded_poly(hand_outline(kind), 0.12, 3)], th, mat, bevel=0.04, c=c)
        parts = [h]
        if kind in ("hour", "minute"):
            L0, L1 = (1.2, 5.4) if kind == "hour" else (1.4, 9.3)
            w = 0.62 if kind == "hour" else 0.38
            lm = kit.outline(f"hand_{kind}_lume", [kit.rounded_poly([(-w, L0), (w, L0), (w, L1), (-w, L1)], 0.15, 3)], th + 0.06, M["lume"], bevel=0.03, c=c)
            parts.append(lm)
        else:
            lol = kit.ring("sec_lollipop", 1.0, 0.7, th, M["steel_dark"], c=c)
            lol.location = (0, 9.8, 0)
            lum = kit.disc("sec_lume", 0.72, th + 0.04, M["lume"], c=c)
            lum.location = (0, 9.8, 0)
            parts += [lol, lum]
        cap = kit.disc(f"hand_{kind}_cap", 0.7 if kind != "second" else 0.55, th + 0.12, mat, c=c)
        parts.append(cap)
        h = kit.join(parts, f"hand_{kind}")
        rot = {"hour": radians(55), "minute": radians(-60), "second": radians(-105)}[kind]
        place(h, 0, 0, z, rot); reg(h, 2, "hands", spin=True, sub={"hour": 0, "minute": 0.35, "second": 0.7}[kind])
        hands[kind] = h
    return hands


# ---------------------------------------------------------------- case, bezel, crystal, crown, bracelet
def build_case(c):
    M = MATS
    case = kit.lathe("case_middle", [(14.6, -4.6), (19.3, -4.6), (19.8, -4.1), (20.2, -2.0), (20.2, 0.6), (19.7, 2.0), (16.0, 2.4), (14.6, 2.4)],
                     M["steel_brushed"], 192, c)
    # lugs
    lugs = []
    for sx in (1, -1):
        for sy in (1, -1):
            pts = [(0, 0), (3.8, 0), (3.8, 6.4), (0.2, 6.6)]
            lg = kit.outline("lug", [kit.rounded_poly([(x - 1.9, y) for x, y in pts], 0.9, 6)], 5.6, M["steel_brushed"], bevel=0.35, c=c)
            lg.location = (sx * 9.4, sy * 16.6, -3.9)
            if sy < 0:
                lg.rotation_euler = (0, 0, pi)
            lugs.append(lg)
    case = kit.join(lugs + [case], "case_middle")
    reg(case, 1, "case")

    # bezel with coin edge + black insert
    bz = kit.outline("bezel", [kit.tooth_profile(120, 20.05, "cycloid", add=0.22, ded=0.22), kit.circle_pts(15.6, 192)], 1.5, M["steel"], bevel=0.12, c=c)
    place(bz, 0, 0, 2.4); reg(bz, 1, "bezel", sub=0.4)
    ins = kit.ring("bezel_insert", 19.0, 15.9, 0.25, M["print_dark"], bev=0.04, c=c)
    marks = [ins]
    for k in range(60):
        a = pi / 2 - TAU * k / 60
        if k == 0:
            tri = kit.outline("bz_tri", [[(0, -0.9), (1.05, 0.75), (-1.05, 0.75)]], 0.06, M["print_white"], bevel=0.01, c=c)
            tri.location = (17.45 * cos(a), 17.45 * sin(a), 0.25)
            marks.append(tri)
            pip = kit.disc("bz_pip", 0.42, 0.1, M["lume"], c=c)
            pip.location = (17.6 * cos(a), 17.6 * sin(a), 0.27)
            marks.append(pip)
        elif k % 10 == 0:
            t = kit.text_obj(f"bz_{k}", str(k), 2.0, 0.05, M["print_white"], FONT_BEZEL, c=c)
            t.location = (17.45 * cos(a), 17.45 * sin(a), 0.25)
            t.rotation_euler = (0, 0, a - pi / 2)
            marks.append(t)
        elif k % 5 == 0:
            b = kit.box(f"bz_bar{k}", 1.5, 0.45, 0.05, M["print_white"], c=c, bev=0.01)
            b.location = (17.45 * cos(a), 17.45 * sin(a), 0.25)
            b.rotation_euler = (0, 0, a)
            marks.append(b)
        elif k < 15:
            d = kit.disc(f"bz_dot{k}", 0.22, 0.05, M["print_white"], c=c)
            d.location = (17.9 * cos(a), 17.9 * sin(a), 0.25)
            marks.append(d)
    ins = kit.join(marks, "bezel_insert")
    place(ins, 0, 0, 3.9); reg(ins, 1, "bezel", sub=0.6)

    crystal = kit.lathe("crystal", [(0, 3.8), (15.6, 3.8), (15.6, 4.5), (15.2, 4.75), (0, 4.8)], M["glass"], 128, c)
    reg(crystal, 0, "crystal")

    # caseback with window (movement visible)
    cb = kit.lathe("caseback", [(11.4, -7.2), (17.6, -7.2), (18.6, -6.6), (18.8, -4.6), (14.6, -4.6), (14.6, -5.4), (11.4, -6.3)], M["steel_brushed"], 160, c)
    reg(cb, 10, "caseback")
    cbg = kit.disc("caseback_glass", 11.6, 0.4, M["glass"], c=c)
    place(cbg, 0, 0, -7.2); reg(cbg, 10, "caseback", sub=0.2)

    # crown at 4 o'clock + stem
    a = radians(-30)
    crown = kit.outline("crown", [kit.tooth_profile(36, 3.0, "cycloid", add=0.2, ded=0.2), kit.circle_pts(0.3, 16)], 3.2, M["steel"], bevel=0.3, c=c)
    crown.location = (21.0 * cos(a), 21.0 * sin(a), -1.2)
    crown.rotation_euler = (0, pi / 2, a)   # lay the axis along +X, then turn to 4 o'clock
    reg(crown, 5, "crown")
    stem = kit.arbor("stem", 0.35, 0.0, 9.0, M["steel"], c=c, pivot=0.7)
    stem.location = (12.6 * cos(a), 12.6 * sin(a), -1.2)
    stem.rotation_euler = (0, pi / 2, a)
    reg(stem, 5, "crown", sub=0.3)

    # bracelet: 3-link segments following the wrist curve
    segs = []
    R_w = 70.0
    for side in (1, -1):
        for i in range(9):
            th = 0.082 * (i + 0.5)
            y = side * (23.2 + R_w * sin(th))
            z = -3.0 - R_w * (1 - cos(th))
            for k, (w, x) in enumerate(((8.6, 0.0), (5.4, 7.15), (5.4, -7.15))):
                L = kit.box(f"link_{side}_{i}_{k}", w, 5.4, 3.2, MATS["steel_brushed"] if k else MATS["steel_satin"], c=c, bev=0.9)
                L.location = (x, y, z - 1.5)
                L.rotation_euler = (side * -th, 0, 0)
                segs.append(L)
    reg(kit.join(segs, "bracelet"), 1, "case", sub=0.0)


def build_tweezers(c):
    M = MATS
    blades = []
    for s_ in (1, -1):
        pts = [(0, s_ * 0.12), (60, s_ * 2.6), (60, s_ * 3.4), (0, s_ * 0.62)]
        b = kit.outline(f"tw_blade{s_}", [pts], 0.9, M["steel_satin"], bevel=0.12, c=c)
        b.location = (0, 0, -0.45)
        blades.append(b)
    grip = kit.box("tw_grip", 14, 7.4, 1.0, M["steel_brushed"], c=c, bev=0.3)
    grip.location = (58, 0, -0.5)
    tw = kit.join(blades + [grip], "tweezers")
    tw.hide_render = True
    return tw


def build_all():
    kit.make_materials()
    c = kit.coll("watch")
    build_movement(c)
    build_dial_side(c)
    build_case(c)
    build_tweezers(c)
    return PARTS
