"""Template (replace the content, keep the method). Floating glass panel that shows the flat manim math (PNG sequence) on its face.
Transparent film: the identity background (#FFFCF2 + grid + shadow) is laid under it in ffmpeg.
usage: blender -b -P glass.py -- still <frame> <out.png>   |   blender -b -P glass.py -- anim <outdir>"""
import bpy, sys, math, os
from math import radians, sin, pi

HERE = os.path.dirname(os.path.abspath(__file__))
SEQ = os.path.join(HERE, "panel_frames")            # straight-alpha PNGs from panel2d.py + unpremul.py
sys.path.insert(0, os.path.join(HERE, "..", "blender"))
from timeline import FPS                             # 24: the film's one clock
SECS = max(1, len([f for f in os.listdir(SEQ) if f.endswith(".png")]) // FPS) if os.path.isdir(SEQ) else 10
W, H, THK = 0.96, 1.056, 0.05
CREAM = (1.0, 0.9734, 0.8879)  # #FFFCF2 in linear


def srgb(h):
    h = h.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in c) + (1,)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1080, 1920, 100
    sc.render.fps, sc.frame_start, sc.frame_end = FPS, 1, FPS * SECS
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.film_transparent = False                 # the identity backdrop is in the scene so the glass refracts it
    sc.view_settings.view_transform = "Standard"      # identity colours come out exact
    e = sc.eevee
    for k, v in (("taa_render_samples", 48), ("use_raytracing", True), ("ray_tracing_method", "SCREEN"),
                 ("use_shadows", True)):
        if hasattr(e, k): setattr(e, k, v)
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    return sc


def world():
    w = bpy.data.worlds.new("w"); bpy.context.scene.world = w; w.use_nodes = True
    nt = w.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    # cream room + two soft white strips so the glass edges catch a highlight
    tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    def band(axis, centre, width):
        d = nt.nodes.new("ShaderNodeMath"); d.operation = "SUBTRACT"; d.inputs[1].default_value = centre
        nt.links.new(sep.outputs[axis], d.inputs[0])
        a = nt.nodes.new("ShaderNodeMath"); a.operation = "ABSOLUTE"; nt.links.new(d.outputs[0], a.inputs[0])
        r = nt.nodes.new("ShaderNodeMapRange"); r.inputs[1].default_value = width; r.inputs[2].default_value = 0
        nt.links.new(a.outputs[0], r.inputs[0]); return r.outputs[0]
    m = nt.nodes.new("ShaderNodeMath"); m.operation = "MAXIMUM"
    nt.links.new(band(2, .82, .06), m.inputs[0]); nt.links.new(band(0, .2, .03), m.inputs[1])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.inputs[6].default_value = CREAM + (1,); mix.inputs[7].default_value = (3, 3, 3, 1)
    nt.links.new(m.outputs[0], mix.inputs[0])
    bg = nt.nodes.new("ShaderNodeBackground"); bg.inputs[1].default_value = 1.0
    nt.links.new(mix.outputs[2], bg.inputs[0]); nt.links.new(bg.outputs[0], out.inputs[0])


def glass_mat():
    m = bpy.data.materials.new("glass"); m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (1, 1, 1, 1)
    p.inputs["Roughness"].default_value = 0.10
    p.inputs["IOR"].default_value = 1.45
    p.inputs["Transmission Weight"].default_value = 1.0
    for k, v in (("use_raytrace_refraction", True), ("surface_render_method", "DITHERED")):
        if hasattr(m, k): setattr(m, k, v)
    if hasattr(m, "thickness_mode"): m.thickness_mode = "SLAB"
    return m


def content_mat():
    m = bpy.data.materials.new("content"); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tex = nt.nodes.new("ShaderNodeTexImage")
    if not os.path.isdir(SEQ):
        sys.exit("motion/panel_frames is missing: render panel2d.py, extract PNG frames, run unpremul.py (motion-tools.md, section 3)")
    first = sorted(f for f in os.listdir(SEQ) if f.startswith("frame") and f.endswith(".png"))[0]
    img = bpy.data.images.load(os.path.join(SEQ, first)); img.source = "SEQUENCE"
    tex.image = img
    u = tex.image_user; u.frame_duration = FPS * SECS; u.frame_start = 1; u.use_auto_refresh = True
    u.frame_offset = int("".join(ch for ch in first if ch.isdigit()) or 0) - 1
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs[1].default_value = 1.0
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(tex.outputs["Color"], em.inputs[0]); nt.links.new(tex.outputs["Alpha"], mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    if hasattr(m, "surface_render_method"): m.surface_render_method = "BLENDED"
    return m


def tex_plane(name, path, size, loc, blended=False):
    bpy.ops.mesh.primitive_plane_add(size=1); o = bpy.context.object; o.name = name
    o.scale = (size[0], size[1], 1); o.rotation_euler = (radians(90), 0, 0); o.location = loc
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); t = nt.nodes.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(path); t.interpolation = "Cubic"
    em = nt.nodes.new("ShaderNodeEmission"); nt.links.new(t.outputs["Color"], em.inputs[0])
    if blended:
        tr = nt.nodes.new("ShaderNodeBsdfTransparent"); mx = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(t.outputs["Alpha"], mx.inputs[0]); nt.links.new(tr.outputs[0], mx.inputs[1])
        nt.links.new(em.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], out.inputs[0])
        if hasattr(m, "surface_render_method"): m.surface_render_method = "BLENDED"
    else:
        nt.links.new(em.outputs[0], out.inputs[0])
    o.data.materials.append(m)
    return o


def build():
    sc = reset(); world()
    TEX = os.path.join(HERE, "tex")
    tex_plane("backdrop", os.path.join(TEX, "backdrop.png"), (2.6, 4.4), (0, 1.2, 0))
    shadow = tex_plane("shadow", os.path.join(TEX, "shadow.png"), (W * 1.45, H * 1.45), (.07, 1.19, .08), blended=True)
    rig = bpy.data.objects.new("rig", None); sc.collection.objects.link(rig)
    bpy.ops.mesh.primitive_cube_add(size=1); g = bpy.context.object; g.name = "glass"
    g.scale = (W, THK, H); bpy.ops.object.transform_apply(scale=True)
    bev = g.modifiers.new("bev", "BEVEL"); bev.width = .018; bev.segments = 6
    g.data.materials.append(glass_mat()); g.parent = rig
    bpy.ops.object.shade_smooth()
    bpy.ops.mesh.primitive_plane_add(size=1); c = bpy.context.object; c.name = "content"
    c.scale = (W * .94, H * .94, 1); c.rotation_euler = (radians(90), 0, 0)
    c.location = (0, -THK / 2 - .002, 0); c.data.materials.append(content_mat()); c.parent = rig
    # camera: panel spans ~x 238-842, y 460-1180 of 1080x1920 (identity card zone 420-1150, captions below)
    cam = bpy.data.cameras.new("cam"); cam.lens = 50
    co = bpy.data.objects.new("cam", cam); sc.collection.objects.link(co); sc.camera = co
    co.rotation_euler = (radians(90), 0, 0)
    n = FPS * SECS
    for f in range(1, n + 1):
        t = (f - 1) / FPS; k = t / SECS
        rig.location = (0, 0, .2 + .012 * sin(2 * pi * t / 4.2))
        rig.rotation_euler = (radians(2.5 * sin(2 * pi * t / 5.0)), 0, radians(-11 + 18 * (3 * k * k - 2 * k ** 3)))
        rig.keyframe_insert("location", frame=f); rig.keyframe_insert("rotation_euler", frame=f)
        shadow.location = (.07, 1.19, rig.location.z - .12); shadow.keyframe_insert("location", frame=f)
        co.location = (0, -3.92 + .15 * k, 0); co.keyframe_insert("location", frame=f)
    return sc


if __name__ == "__main__":
    a = sys.argv[sys.argv.index("--") + 1:]
    sc = build()
    if a[0] == "still":
        sc.frame_set(int(a[1])); sc.render.filepath = a[2]; bpy.ops.render.render(write_still=True)
    else:
        sc.render.filepath = os.path.join(a[1], "")
        bpy.ops.render.render(animation=True)
