"""Procedural parts kit for the watch film. Units: 1 BU = 1 mm (scene scale_length 0.001).

Every builder returns a Blender object at the origin, lying in the XY plane, thickness along +Z
starting at z=0 unless noted. Callers place them.
"""
import bpy, bmesh, math
from math import pi, cos, sin, sqrt, asin
from mathutils import Vector

C = bpy.context
TAU = 2 * pi


# ---------------------------------------------------------------- collections / objects
def coll(name, parent=None):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    p = parent or bpy.context.scene.collection
    if c.name not in [x.name for x in p.children]:
        p.children.link(c)
    return c


def link(ob, c=None):
    (c or bpy.context.scene.collection).objects.link(ob)
    return ob


def empty(name, c=None, size=1.0):
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = size
    return link(e, c)


def set_mat(ob, m):
    if ob.data is None:
        return ob
    ob.data.materials.clear()
    ob.data.materials.append(m)
    return ob


def smooth(me, angle=32):
    for p in me.polygons:
        p.use_smooth = True
    try:
        me.set_sharp_from_angle(angle=math.radians(angle))
    except Exception:
        pass
    return me


# ---------------------------------------------------------------- materials
MATS = {}


def _principled(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    return m, m.node_tree.nodes["Principled BSDF"], m.node_tree


def _set(b, key, val):
    if key in b.inputs:
        b.inputs[key].default_value = val


def _radial_tangent(nt, b):
    """circular brushing around local Z (circular graining / sunburst)"""
    t = nt.nodes.new("ShaderNodeTangent")
    t.direction_type = "RADIAL"
    t.axis = "Z"
    nt.links.new(t.outputs[0], b.inputs["Tangent"])


def make_materials():
    def metal(name, col, rough, aniso=0.0, radial=False, coat=0.0):
        m, b, nt = _principled(name)
        _set(b, "Base Color", (*col, 1))
        _set(b, "Metallic", 1.0)
        _set(b, "Roughness", rough)
        if aniso:
            _set(b, "Anisotropic", aniso)
            if radial:
                _radial_tangent(nt, b)
        if coat:
            _set(b, "Coat Weight", coat)
        MATS[name] = m

    metal("steel", (0.80, 0.81, 0.83), 0.10)
    metal("steel_satin", (0.76, 0.77, 0.79), 0.26)
    metal("steel_grain", (0.78, 0.79, 0.81), 0.30, aniso=0.75, radial=True)     # circular graining
    metal("steel_brushed", (0.76, 0.77, 0.79), 0.28, aniso=0.7)                  # linear brushing (case)
    metal("steel_dark", (0.20, 0.21, 0.23), 0.35)
    metal("gold", (1.00, 0.77, 0.36), 0.16)
    metal("brass", (0.93, 0.74, 0.42), 0.22, aniso=0.6, radial=True)
    metal("rose", (0.95, 0.64, 0.52), 0.20)
    metal("blued", (0.06, 0.13, 0.48), 0.20, coat=0.3)

    # ruby (synthetic, a bit more saturated than life, like the reference)
    m, b, nt = _principled("ruby")
    _set(b, "Base Color", (0.95, 0.04, 0.22, 1))
    _set(b, "Metallic", 0.0)
    _set(b, "Roughness", 0.02)
    _set(b, "IOR", 1.77)
    _set(b, "Transmission Weight", 0.85)
    _set(b, "Coat Weight", 0.5)
    _set(b, "Emission Color", (0.9, 0.02, 0.2, 1))
    _set(b, "Emission Strength", 0.15)
    for attr in ("use_raytrace_refraction",):
        if hasattr(m, attr):
            setattr(m, attr, True)
    MATS["ruby"] = m

    m, b, nt = _principled("glass")
    _set(b, "Base Color", (1, 1, 1, 1))
    _set(b, "Roughness", 0.0)
    _set(b, "IOR", 1.5)
    _set(b, "Transmission Weight", 0.0)
    _set(b, "Specular IOR Level", 0.7)
    _set(b, "Alpha", 0.06)
    if hasattr(m, "surface_render_method"):
        m.surface_render_method = "BLENDED"
    MATS["glass"] = m

    m, b, nt = _principled("lume")
    _set(b, "Base Color", (0.95, 0.94, 0.86, 1))
    _set(b, "Roughness", 0.45)
    _set(b, "Emission Color", (0.6, 1.0, 0.75, 1))
    _set(b, "Emission Strength", 0.0)
    MATS["lume"] = m

    # cream sunburst dial
    m, b, nt = _principled("dial")
    _set(b, "Base Color", (0.84, 0.74, 0.55, 1))
    _set(b, "Metallic", 0.3)
    _set(b, "Roughness", 0.3)
    _set(b, "Anisotropic", 0.85)
    _set(b, "Coat Weight", 0.35)
    _radial_tangent(nt, b)
    MATS["dial"] = m

    m, b, nt = _principled("print_dark")      # dial printing, bezel insert
    _set(b, "Base Color", (0.035, 0.035, 0.04, 1))
    _set(b, "Roughness", 0.3)
    _set(b, "Coat Weight", 0.6)
    MATS["print_dark"] = m

    m, b, nt = _principled("print_white")
    _set(b, "Base Color", (0.92, 0.91, 0.87, 1))
    _set(b, "Roughness", 0.4)
    MATS["print_white"] = m

    m, b, nt = _principled("disc_white")       # date/day discs
    _set(b, "Base Color", (0.93, 0.92, 0.88, 1))
    _set(b, "Roughness", 0.5)
    MATS["disc_white"] = m

    m, b, nt = _principled("accent")           # brand orange highlight for the empty slot
    _set(b, "Base Color", (0.92, 0.37, 0.16, 1))
    _set(b, "Emission Color", (0.92, 0.37, 0.16, 1))
    _set(b, "Emission Strength", 0.7)
    MATS["accent"] = m
    return MATS


# ---------------------------------------------------------------- 2D helpers
def circle_pts(r, n=96, a0=0.0, cx=0.0, cy=0.0, reverse=False):
    pts = [(cx + r * cos(a0 + TAU * k / n), cy + r * sin(a0 + TAU * k / n)) for k in range(n)]
    return pts[::-1] if reverse else pts


def arc_pts(r, a0, a1, n, cx=0.0, cy=0.0):
    return [(cx + r * cos(a0 + (a1 - a0) * k / (n - 1)), cy + r * sin(a0 + (a1 - a0) * k / (n - 1))) for k in range(n)]


def rounded_poly(pts, r, seg=6):
    """round every corner of a closed polygon with radius r"""
    out = []
    n = len(pts)
    for i in range(n):
        p0, p1, p2 = Vector(pts[i - 1]), Vector(pts[i]), Vector(pts[(i + 1) % n])
        d0, d1 = (p0 - p1), (p2 - p1)
        l0, l1 = d0.length, d1.length
        if l0 < 1e-6 or l1 < 1e-6:
            continue
        d0.normalize(); d1.normalize()
        ang = math.acos(max(-1, min(1, d0.dot(d1))))
        t = min(r / max(math.tan(ang / 2), 1e-3), l0 * 0.45, l1 * 0.45)
        a, b = p1 + d0 * t, p1 + d1 * t
        for k in range(seg + 1):  # quadratic bezier through the corner
            s = k / seg
            q = (1 - s) ** 2 * a + 2 * (1 - s) * s * p1 + s * s * b
            out.append((q.x, q.y))
    return out


def catmull(ctrl, per=10):
    """closed Catmull-Rom spline through control points"""
    out = []
    n = len(ctrl)
    P = [Vector(c) for c in ctrl]
    for i in range(n):
        p0, p1, p2, p3 = P[i - 1], P[i], P[(i + 1) % n], P[(i + 2) % n]
        for k in range(per):
            t = k / per
            t2, t3 = t * t, t * t * t
            q = 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)
            out.append((q.x, q.y))
    return out


# ---------------------------------------------------------------- outline extrusion (curves fill holes)
def outline(name, loops, thick, mat, bevel=0.04, c=None, res=2):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "2D"
    cu.fill_mode = "BOTH"
    b = min(bevel, thick * 0.45)
    cu.extrude = max(thick / 2 - b, 0.0001)
    cu.bevel_depth = b
    cu.bevel_resolution = res
    for loop in loops:
        sp = cu.splines.new("POLY")
        sp.points.add(len(loop) - 1)
        for i, (x, y) in enumerate(loop):
            sp.points[i].co = (x, y, 0, 1)
        sp.use_cyclic_u = True
    ob = bpy.data.objects.new(name, cu)
    link(ob, c)
    # put bottom face at z=0 by shifting the data, so location.z = seat height
    ob.data.offset = 0
    set_mat(ob, mat)
    ob["half"] = thick / 2
    return to_mesh(ob, shift=thick / 2)


def to_mesh(ob, shift=0.0):
    """convert a curve object to a mesh with its bottom at z=0"""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    for v in me.vertices:
        v.co.z += shift
    smooth(me, 35)
    name = ob.name
    cols = list(ob.users_collection)
    old_cu = ob.data
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(old_cu)
    me.name = name
    new = bpy.data.objects.new(name, me)
    for c in cols:
        c.objects.link(new)
    return new


def join(objs, name):
    """join objects into one new object whose origin is the world origin (keeps world positions)"""
    me = bpy.data.meshes.new(name)
    host = bpy.data.objects.new(name, me)
    cols = objs[0].users_collection
    for c in cols:
        c.objects.link(host)
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    host.select_set(True)
    bpy.context.view_layer.objects.active = host
    bpy.ops.object.join()
    host.name = name
    return host


# ---------------------------------------------------------------- lathe (round parts)
def lathe(name, prof, mat, seg=96, c=None, closed=True, angle=32):
    """prof: [(r, z), ...] traced as a closed loop around the Z axis"""
    bm = bmesh.new()
    vs = [bm.verts.new((max(r, 0.0), 0, z)) for r, z in prof]
    es = [bm.edges.new((vs[i], vs[i + 1])) for i in range(len(vs) - 1)]
    if closed:
        es.append(bm.edges.new((vs[-1], vs[0])))
    bmesh.ops.spin(bm, geom=vs + es, cent=(0, 0, 0), axis=(0, 0, 1), angle=TAU, steps=seg, use_merge=True)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    smooth(me, angle)
    ob = bpy.data.objects.new(name, me)
    link(ob, c)
    return set_mat(ob, mat)


def ring(name, r_out, r_in, h, mat, bev=0.05, seg=128, c=None):
    b = min(bev, h * 0.4, (r_out - r_in) * 0.4)
    prof = [(r_in, 0), (r_out - b, 0), (r_out, b), (r_out, h - b), (r_out - b, h), (r_in + b, h), (r_in, h - b)]
    return lathe(name, prof, mat, seg, c)


def disc(name, r, h, mat, bev=0.05, seg=128, c=None):
    b = min(bev, h * 0.4)
    prof = [(0, 0), (r - b, 0), (r, b), (r, h - b), (r - b, h), (0, h)]
    return lathe(name, prof, mat, seg, c)


# ---------------------------------------------------------------- wheels
def tooth_profile(n, r_pitch, kind="cycloid", add=None, ded=None, steps=5):
    m = 2 * r_pitch / n
    add = add if add is not None else 1.0 * m
    ded = ded if ded is not None else 1.3 * m
    rr, rt = r_pitch - ded, r_pitch + add
    da = TAU / n
    pts = []
    if kind == "cycloid":
        hw = 0.23 * da                        # half tooth width (angle) at pitch circle
        for i in range(n):
            ac = i * da
            # root between previous tooth and this one (rounded valley)
            for k in range(steps):
                s = k / (steps - 1)
                a = ac - da / 2 + (da / 2 - hw) * (0.15 + 0.7 * s)
                r = rr + (0.25 * ded) * (1 - sin(pi * s)) * 0 + 0.0
                pts.append((rr * cos(a), rr * sin(a)))
            # flank up
            pts.append((r_pitch * cos(ac - hw), r_pitch * sin(ac - hw)))
            # ogival tip
            for k in range(1, steps * 2):
                s = k / (steps * 2)
                ang = -pi / 2 + pi * s
                a = ac + hw * sin(ang) * (1 - 0.15 * cos(ang))
                r = r_pitch + add * cos(ang)
                pts.append((r * cos(a), r * sin(a)))
            pts.append((r_pitch * cos(ac + hw), r_pitch * sin(ac + hw)))
    elif kind == "club":                      # Swiss lever escape wheel
        for i in range(n):
            a0 = i * da
            for f, r in ((0.05, rr), (0.50, rr), (0.86, rt), (0.99, rt * 0.985), (1.0, rr * 1.03)):
                a = a0 + f * da
                pts.append((r * cos(a), r * sin(a)))
    elif kind == "ratchet":                   # sawtooth (ratchet / transmission wheel)
        for i in range(n):
            a0 = i * da
            for f, r in ((0.0, rr), (0.85, rt), (0.9, rt), (0.92, rr)):
                a = a0 + f * da
                pts.append((r * cos(a), r * sin(a)))
    return pts


def spoke_windows(n_spokes, r_hub, r_rim, w, a0=0.0, steps=24):
    h = w / 2
    holes = []
    for i in range(n_spokes):
        t0 = a0 + TAU * i / n_spokes
        t1 = a0 + TAU * (i + 1) / n_spokes
        ao0, ao1 = t0 + asin(h / r_rim), t1 - asin(h / r_rim)
        ai0, ai1 = t0 + asin(h / r_hub), t1 - asin(h / r_hub)
        if ai1 <= ai0:
            continue
        loop = arc_pts(r_rim, ao0, ao1, steps) + arc_pts(r_hub, ai1, ai0, max(4, steps // 3))
        holes.append(rounded_poly(loop, w * 0.35, 3))
    return holes


def wheel(name, n, r_pitch, thick, mat, spokes=4, kind="cycloid", hub=None, rim=None, arbor=0.18,
          spoke_w=None, c=None, a0=0.0):
    prof = tooth_profile(n, r_pitch, kind)
    loops = [prof]
    m = 2 * r_pitch / n
    r_root = r_pitch - 1.3 * m
    rim_w = rim if rim is not None else max(0.18 * r_pitch, 0.25)
    r_rim = r_root - rim_w
    r_hub = hub if hub is not None else max(0.22 * r_pitch, arbor * 2.4)
    if spokes and r_rim > r_hub + 0.2:
        loops += spoke_windows(spokes, r_hub, r_rim, spoke_w or max(0.09 * r_pitch, 0.18), a0)
    loops.append(circle_pts(arbor, 24))
    return outline(name, loops, thick, mat, bevel=min(0.035, thick * 0.3), c=c)


def pinion(name, leaves, r, length, mat, arbor_r=0.16, arbor_len=None, c=None):
    """pinion leaves (z 0..length) on an arbor that extends both ways"""
    p = outline(name, [tooth_profile(leaves, r, "cycloid", add=0.55 * 2 * r / leaves * 1.6, ded=0.6 * 2 * r / leaves * 1.8),
                       circle_pts(0.001, 6)], length, mat, bevel=0.02, c=c)
    return p


def arbor(name, r, z0, z1, mat, c=None, pivot=0.6):
    """staff with conical pivots"""
    L = z1 - z0
    pr = r * pivot
    prof = [(0, z0), (pr, z0), (pr, z0 + 0.25), (r, z0 + 0.45), (r, z1 - 0.45), (pr, z1 - 0.25), (pr, z1), (0, z1)]
    return lathe(name, prof, mat, 32, c, angle=40)


# ---------------------------------------------------------------- jewels, screws, springs
def jewel(name, r=0.55, h=0.32, hole=0.1, mat=None, c=None):
    prof = [(hole, -h / 2), (r * 0.92, -h / 2), (r, -h / 2 + 0.05), (r, h * 0.25), (r * 0.8, h / 2),
            (r * 0.45, h / 2 - 0.02), (r * 0.25, h * 0.1), (hole, h * 0.05)]
    return lathe(name, prof, mat or MATS["ruby"], 48, c, angle=50)


_screw_mesh = {}


def screw(name, r=0.62, h=0.42, mat=None, c=None, slot=True):
    key = (round(r, 3), round(h, 3), slot)
    if key not in _screw_mesh:
        prof = [(0, 0), (r, 0), (r, h * 0.55), (r * 0.82, h * 0.92), (r * 0.5, h), (0, h)]
        ob = lathe("_screw_proto", prof, MATS["steel"], 40)
        if slot:
            bm = bmesh.new()
            bmesh.ops.create_cube(bm, size=1.0)
            bmesh.ops.scale(bm, vec=(2.4 * r, 0.18 * r, h * 0.7), verts=bm.verts)
            bmesh.ops.translate(bm, vec=(0, 0, h), verts=bm.verts)
            cme = bpy.data.meshes.new("_cut")
            bm.to_mesh(cme)
            bm.free()
            cut = bpy.data.objects.new("_cut", cme)
            link(cut)
            mod = ob.modifiers.new("slot", "BOOLEAN")
            mod.object = cut
            mod.operation = "DIFFERENCE"
            mod.solver = "EXACT"
            bpy.context.view_layer.objects.active = ob
            dg = bpy.context.evaluated_depsgraph_get()
            me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
            bpy.data.objects.remove(cut)
            bpy.data.meshes.remove(cme)
            old = ob.data
            ob.modifiers.clear()
            ob.data = me
            bpy.data.meshes.remove(old)
        _screw_mesh[key] = ob.data
        bpy.data.objects.remove(ob)
    ob = bpy.data.objects.new(name, _screw_mesh[key])
    link(ob, c)
    if mat:
        ob.material_slots and None
    return ob


def spiral_strip(name, r0, r1, turns, height, thick, mat, c=None, pts_per_turn=90, outer_tail=0.0):
    """flat spiral (hairspring / mainspring) as a thin vertical strip"""
    n = int(turns * pts_per_turn)
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "2D"
    cu.fill_mode = "NONE"
    cu.extrude = height / 2
    cu.bevel_depth = thick / 2
    cu.bevel_resolution = 1
    sp = cu.splines.new("POLY")
    pts = []
    for k in range(n + 1):
        t = k / n
        a = TAU * turns * t
        r = r0 + (r1 - r0) * t
        pts.append((r * cos(a), r * sin(a)))
    if outer_tail:
        a = TAU * turns
        pts.append(((r1 + outer_tail) * cos(a + 0.35), (r1 + outer_tail) * sin(a + 0.35)))
    sp.points.add(len(pts) - 1)
    for i, (x, y) in enumerate(pts):
        sp.points[i].co = (x, y, 0, 1)
    ob = bpy.data.objects.new(name, cu)
    link(ob, c)
    set_mat(ob, mat)
    return to_mesh(ob, shift=height / 2)


def box(name, sx, sy, sz, mat, c=None, bev=0.03):
    loop = rounded_poly([(-sx / 2, -sy / 2), (sx / 2, -sy / 2), (sx / 2, sy / 2), (-sx / 2, sy / 2)], bev * 2, 2)
    return outline(name, [loop], sz, mat, bevel=bev, c=c)


def text_obj(name, body, size, depth, mat, font=None, c=None, align="CENTER"):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.size = size
    cu.extrude = depth / 2
    cu.align_x = align
    cu.align_y = "CENTER"
    if font:
        try:
            cu.font = bpy.data.fonts.load(font, check_existing=True)
        except Exception:
            pass
    ob = bpy.data.objects.new(name, cu)
    link(ob, c)
    set_mat(ob, mat)
    return to_mesh(ob, shift=depth / 2)
