"""Glass panel (2D math on its face) floating in a simple 3D world in the identity palette.
World: cream floor with a thin grid, a big parabola arch (the curve, in 3D) behind the panel, short
Riemann pillars (the integral), a few spheres. Neutral tones only: orange stays with the math.
Real sun + shadows, light depth of field, slow camera drift for parallax.
usage: blender -b -P world.py -- still <frame> <out.png>   |   blender -b -P world.py -- anim <outdir>"""
import bpy, sys, os
from math import radians, sin, pi
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glass as G

FLOOR = -0.95
C = {k: G.srgb(v) for k, v in dict(bg="#FFFCF2", line="#CCC5B9", ink2="#403D39", ink="#252422").items()}


def mat(name, color, rough=.6, spec=.3):
    m = bpy.data.materials.new(name); m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = color; p.inputs["Roughness"].default_value = rough
    if "Specular IOR Level" in p.inputs: p.inputs["Specular IOR Level"].default_value = spec
    return m


def floor_mat():
    m = bpy.data.materials.new("floor"); m.use_nodes = True; nt = m.node_tree
    p = nt.nodes["Principled BSDF"]; p.inputs["Roughness"].default_value = .85
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / .3, 1 / .3, 1)               # 30 cm grid cells
    br = nt.nodes.new("ShaderNodeTexBrick")                                # brick with offset 0 = square grid
    br.offset = 0; br.squash = 1
    dim = tuple(c * .72 for c in C["bg"][:3]) + (1,)          # lit by world 1.0 + sun, lands back on cream
    br.inputs["Color1"].default_value = dim; br.inputs["Color2"].default_value = dim
    br.inputs["Mortar"].default_value = tuple(.72 * (a + b) / 2 for a, b in zip(C["line"][:3], C["bg"][:3])) + (1,); br.inputs["Scale"].default_value = 1
    br.inputs["Mortar Size"].default_value = .012; br.inputs["Brick Width"].default_value = 1
    br.inputs["Row Height"].default_value = 1; br.inputs["Mortar Smooth"].default_value = .4
    nt.links.new(tc.outputs["Object"], mp.inputs[0]); nt.links.new(mp.outputs[0], br.inputs[0])
    nt.links.new(br.outputs["Color"], p.inputs["Base Color"])
    # far floor melts into the cream sky: no hard horizon line
    out = nt.nodes["Material Output"]; cd = nt.nodes.new("ShaderNodeCameraData")
    fr = nt.nodes.new("ShaderNodeMapRange"); fr.inputs[1].default_value = 5; fr.inputs[2].default_value = 13
    fr.interpolation_type = "SMOOTHSTEP"; nt.links.new(cd.outputs["View Distance"], fr.inputs[0])
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs[0].default_value = C["bg"]
    mx = nt.nodes.new("ShaderNodeMixShader"); nt.links.new(fr.outputs[0], mx.inputs[0])
    nt.links.new(p.outputs[0], mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs[0])
    return m


def tube_curve(name, pts, radius, m):
    cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "3D"
    cu.bevel_depth = radius; cu.bevel_resolution = 6; cu.use_fill_caps = True
    sp = cu.splines.new("POLY"); sp.points.add(len(pts) - 1)
    for p, (x, y, z) in zip(sp.points, pts): p.co = (x, y, z, 1)
    o = bpy.data.objects.new(name, cu); bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(m); return o


def box(name, size, loc, m, bevel=.01):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc); o = bpy.context.object; o.name = name
    o.scale = size; bpy.ops.object.transform_apply(scale=True)
    b = o.modifiers.new("b", "BEVEL"); b.width = bevel; b.segments = 3
    o.data.materials.append(m); bpy.ops.object.shade_smooth(); return o


def sphere(name, r, loc, m):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=48, ring_count=24)
    o = bpy.context.object; o.name = name; o.data.materials.append(m); bpy.ops.object.shade_smooth(); return o


def build():
    sc = G.reset()
    sc.eevee.use_shadows = True
    if hasattr(sc.eevee, "shadow_ray_count"): sc.eevee.shadow_ray_count = 2
    # world: plain cream (the horizon melts into it), lighting from a soft sun
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
    nt = w.node_tree; bgn = nt.nodes["Background"]; bgn.inputs[0].default_value = C["bg"]
    lp = nt.nodes.new("ShaderNodeLightPath"); mr = nt.nodes.new("ShaderNodeMapRange")   # camera sees exact cream,
    mr.inputs[3].default_value = 1.0; mr.inputs[4].default_value = 1.0                   # the scene is lit at 0.55
    nt.links.new(lp.outputs["Is Camera Ray"], mr.inputs[0]); nt.links.new(mr.outputs[0], bgn.inputs[1])
    sun = bpy.data.lights.new("sun", "SUN"); sun.energy = 1.2; sun.angle = radians(8); sun.color = (1, .97, .92)
    so = bpy.data.objects.new("sun", sun); sc.collection.objects.link(so)
    so.rotation_euler = (radians(38), radians(-24), radians(-28))

    m_ink2, m_line = mat("ink2", C["ink2"], .45, .4), mat("line", C["line"], .7)
    m_bg = mat("cream", tuple(c * .78 for c in C["bg"][:3]) + (1,), .35, .5)

    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 10, FLOOR)); fl = bpy.context.object
    fl.data.materials.append(floor_mat())

    # the curve, in 3D: a big parabola arch standing behind the panel
    xs = [i / 40 * 4.4 - 2.2 for i in range(41)]
    tube_curve("arch", [(x, 4.2, FLOOR + .03 + .38 * x * x) for x in xs], .028, m_ink2)
    tube_curve("arch_shadow_rail", [(x, 4.2, FLOOR + .012) for x in (-2.2, 2.2)], .012, m_line)
    # the integral: Riemann pillars on the floor, left and behind
    n = 7
    for i in range(n):
        x = (i + .5) / n * 1.2; h = .08 + .55 * x * x
        box(f"bar{i}", (.15, .15, h), (-1.3 + i * .17, 1.9, FLOOR + h / 2), m_line if i % 2 else m_bg)
    # a few spheres for scale and depth
    sphere("s1", .22, (1.25, 1.5, FLOOR + .22), m_bg)
    sphere("s2", .11, (1.6, 2.4, FLOOR + .11), m_ink2)
    sphere("s3", .16, (-.9, 4.2, FLOOR + .16), m_line)

    # panel (glass + flat math)
    rig = bpy.data.objects.new("rig", None); sc.collection.objects.link(rig)
    bpy.ops.mesh.primitive_cube_add(size=1); g = bpy.context.object; g.name = "glass"
    g.scale = (G.W, G.THK, G.H); bpy.ops.object.transform_apply(scale=True)
    bev = g.modifiers.new("bev", "BEVEL"); bev.width = .018; bev.segments = 6
    g.data.materials.append(G.glass_mat()); g.parent = rig; bpy.ops.object.shade_smooth()
    bpy.ops.mesh.primitive_plane_add(size=1); c = bpy.context.object; c.name = "content"
    c.scale = (G.W * .94, G.H * .94, 1); c.rotation_euler = (radians(90), 0, 0)
    c.location = (0, -G.THK / 2 - .002, 0); c.data.materials.append(G.content_mat()); c.parent = rig
    c.visible_shadow = False

    cam = bpy.data.cameras.new("cam"); cam.lens = 50
    cam.dof.use_dof = True; cam.dof.aperture_fstop = 2.2
    co = bpy.data.objects.new("cam", cam); sc.collection.objects.link(co); sc.camera = co
    for f in range(1, G.FPS * G.SECS + 1):
        t = (f - 1) / G.FPS; k = t / G.SECS; e = 3 * k * k - 2 * k ** 3
        rig.location = (0, 0, .2 + .012 * sin(2 * pi * t / 4.2))
        rig.rotation_euler = (radians(2.5 * sin(2 * pi * t / 5.0)), 0, radians(-8 + 12 * e))
        rig.keyframe_insert("location", frame=f); rig.keyframe_insert("rotation_euler", frame=f)
        # drift sideways and in: the world shows parallax, the panel stays in its zone
        pos = Vector((-.35 + .7 * e, -3.92 + .15 * k, .32))
        co.location = pos
        aim = Vector((0, 0, -.02)) - pos             # aim below the panel so it sits in the 460-1180 px card zone
        co.rotation_euler = aim.to_track_quat("-Z", "Y").to_euler()
        cam.dof.focus_distance = (Vector((0, 0, .2)) - pos).length
        co.keyframe_insert("location", frame=f); co.keyframe_insert("rotation_euler", frame=f)
        cam.dof.keyframe_insert("focus_distance", frame=f)
    return sc


if __name__ == "__main__":
    a = sys.argv[sys.argv.index("--") + 1:]
    sc = build()
    if a[0] == "still":
        sc.frame_set(int(a[1])); sc.render.filepath = a[2]; bpy.ops.render.render(write_still=True)
    else:
        sc.render.filepath = os.path.join(a[1], "")
        bpy.ops.render.render(animation=True)
