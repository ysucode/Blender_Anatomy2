"""Studio: screen-space backdrop for camera rays (light centre, diagonal beam, cool dark corners),
HDRI for reflections and light, a sun for shadows, emissive strip cards for crisp bevel highlights."""
import bpy, math
from math import radians
from mathutils import Vector

HDRI = "D:/tools/hdri/studio_small_09_2k.hdr"


def node(nt, kind, loc=(0, 0), **props):
    n = nt.nodes.new(kind)
    n.location = loc
    for k, v in props.items():
        setattr(n, k, v)
    return n


def math_node(nt, op, a=None, b=None, loc=(0, 0)):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    n.location = loc
    if a is not None:
        if isinstance(a, (int, float)):
            n.inputs[0].default_value = a
        else:
            nt.links.new(a, n.inputs[0])
    if b is not None:
        if isinstance(b, (int, float)):
            n.inputs[1].default_value = b
        else:
            nt.links.new(b, n.inputs[1])
    return n.outputs[0]


# softboxes in the reflection world: (direction, up, half-width, half-height, feather, intensity)
SOFTBOXES = [
    ((0.25, -0.35, 0.90), (0, 1, 0), 0.75, 0.45, 0.25, 5.0),    # big overhead box
    ((0.92, -0.25, 0.30), (0, 0, 1), 0.10, 1.40, 0.06, 9.0),    # tall right strip
    ((-0.85, 0.45, 0.25), (0, 0, 1), 0.08, 1.20, 0.05, 6.0),    # left rim strip
    ((0.0, -1.0, 0.05), (0, 0, 1), 0.70, 0.12, 0.10, 1.6),      # low front fill
    ((-0.2, 0.3, -0.93), (0, 1, 0), 0.6, 0.4, 0.3, 1.2),        # bounce from below (caseback shots)
]


def world(dark=(0.055, 0.068, 0.092), light=(0.93, 0.915, 0.87), hdri_strength=0.12, hdri_rot=0.0, beam=1.0, room=0.035):
    sc = bpy.context.scene
    w = bpy.data.worlds.get("studio") or bpy.data.worlds.new("studio")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = node(nt, "ShaderNodeOutputWorld", (900, 0))
    tc = node(nt, "ShaderNodeTexCoord", (-900, 200))
    sep = node(nt, "ShaderNodeSeparateXYZ", (-700, 200))
    nt.links.new(tc.outputs["Window"], sep.inputs[0])
    x, y = sep.outputs[0], sep.outputs[1]
    # distance from the beam line through (0.86, 1.0) and (0.22, 0.0)
    nx, ny = 0.8423, -0.5390
    dx = math_node(nt, "SUBTRACT", x, 0.86)
    dy = math_node(nt, "SUBTRACT", y, 1.0)
    d = math_node(nt, "ADD", math_node(nt, "MULTIPLY", dx, nx), math_node(nt, "MULTIPLY", dy, ny))
    d2 = math_node(nt, "MULTIPLY", d, d)
    beam_v = math_node(nt, "EXPONENT", math_node(nt, "MULTIPLY", d2, -1.0 / (0.30 ** 2)))
    # broad vignette from the centre
    cx = math_node(nt, "SUBTRACT", x, 0.55)
    cy = math_node(nt, "SUBTRACT", y, 0.58)
    r2 = math_node(nt, "ADD", math_node(nt, "MULTIPLY", cx, cx), math_node(nt, "MULTIPLY", math_node(nt, "MULTIPLY", cy, cy), 0.55))
    vig = math_node(nt, "EXPONENT", math_node(nt, "MULTIPLY", r2, -1.0 / (0.36 ** 2)))
    t = math_node(nt, "MAXIMUM", math_node(nt, "MULTIPLY", beam_v, beam), math_node(nt, "MULTIPLY", vig, 0.78))
    t = math_node(nt, "MINIMUM", t, 1.0)
    t = math_node(nt, "POWER", t, 0.8)
    mix = node(nt, "ShaderNodeMix", (300, 200))
    mix.data_type = "RGBA"
    nt.links.new(t, mix.inputs["Factor"])
    mix.inputs[6].default_value = (*dark, 1)
    mix.inputs[7].default_value = (*light, 1)
    emit = node(nt, "ShaderNodeBackground", (500, 200))
    nt.links.new(mix.outputs[2], emit.inputs[0])
    emit.inputs[1].default_value = 1.0
    # reflection/lighting world for everything that is not a camera ray:
    # dark room + defined softboxes (product-shot look) + a little HDRI for texture
    mp = node(nt, "ShaderNodeMapping", (-500, -250))
    mp.inputs["Rotation"].default_value = (0, 0, radians(hdri_rot))
    tc2 = node(nt, "ShaderNodeTexCoord", (-700, -250))
    nt.links.new(tc2.outputs["Generated"], mp.inputs[0])
    env = node(nt, "ShaderNodeTexEnvironment", (-300, -250))
    env.image = bpy.data.images.load(HDRI, check_existing=True)
    nt.links.new(mp.outputs[0], env.inputs[0])
    vdir = node(nt, "ShaderNodeVectorMath", (-500, -600), operation="NORMALIZE")
    nt.links.new(tc2.outputs["Generated"], vdir.inputs[0])
    v = vdir.outputs[0]
    acc = None
    for D, U, w, h, f, I in SOFTBOXES:
        Dv = Vector(D).normalized()
        Uv = (Vector(U) - Dv * Vector(U).dot(Dv)).normalized()
        Rv = Dv.cross(Uv)
        def dot(vec):
            n_ = node(nt, "ShaderNodeVectorMath", operation="DOT_PRODUCT")
            nt.links.new(v, n_.inputs[0])
            n_.inputs[1].default_value = tuple(vec)
            return n_.outputs["Value"]
        d = dot(Dv)
        a = math_node(nt, "ABSOLUTE", math_node(nt, "DIVIDE", dot(Rv), math_node(nt, "MAXIMUM", d, 0.001)))
        b = math_node(nt, "ABSOLUTE", math_node(nt, "DIVIDE", dot(Uv), math_node(nt, "MAXIMUM", d, 0.001)))
        def soft(x, lo, hi):
            mr = node(nt, "ShaderNodeMapRange", interpolation_type="SMOOTHSTEP")
            nt.links.new(x, mr.inputs["Value"])
            mr.inputs["From Min"].default_value = lo
            mr.inputs["From Max"].default_value = hi
            mr.inputs["To Min"].default_value = 1.0
            mr.inputs["To Max"].default_value = 0.0
            return mr.outputs["Result"]
        front = math_node(nt, "GREATER_THAN", d, 0.0)
        m = math_node(nt, "MULTIPLY", math_node(nt, "MULTIPLY", soft(a, w, w + f), soft(b, h, h + f)), front)
        m = math_node(nt, "MULTIPLY", m, I)
        acc = m if acc is None else math_node(nt, "ADD", acc, m)
    # base: dark floor, slightly lifted ceiling
    sepv = node(nt, "ShaderNodeSeparateXYZ")
    nt.links.new(v, sepv.inputs[0])
    base = math_node(nt, "ADD", math_node(nt, "MULTIPLY", math_node(nt, "ADD", sepv.outputs[2], 1.0), 0.5 * room), room * 0.25)
    lum = math_node(nt, "ADD", acc, base)
    tint = node(nt, "ShaderNodeMix")
    tint.data_type = "RGBA"
    tint.blend_type = "MULTIPLY"
    tint.inputs["Factor"].default_value = 1.0
    nt.links.new(lum, tint.inputs[6])
    tint.inputs[7].default_value = (1.0, 0.985, 0.95, 1)
    hd = node(nt, "ShaderNodeMix")
    hd.data_type = "RGBA"
    hd.blend_type = "ADD"
    hd.inputs["Factor"].default_value = hdri_strength
    nt.links.new(tint.outputs[2], hd.inputs[6])
    nt.links.new(env.outputs[0], hd.inputs[7])
    bg = node(nt, "ShaderNodeBackground", (500, -150))
    nt.links.new(hd.outputs[2], bg.inputs[0])
    bg.inputs[1].default_value = 1.0
    lp = node(nt, "ShaderNodeLightPath", (300, 450))
    ms = node(nt, "ShaderNodeMixShader", (720, 0))
    nt.links.new(lp.outputs["Is Camera Ray"], ms.inputs[0])
    nt.links.new(bg.outputs[0], ms.inputs[1])
    nt.links.new(emit.outputs[0], ms.inputs[2])
    nt.links.new(ms.outputs[0], out.inputs[0])
    return w


def sun(name="key", rot=(radians(38), radians(18), radians(35)), strength=3.0, angle=12):
    l = bpy.data.lights.get(name) or bpy.data.lights.new(name, "SUN")
    l.energy = strength
    l.angle = radians(angle)
    o = bpy.data.objects.get(name) or bpy.data.objects.new(name, l)
    if o.name not in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.link(o)
    o.rotation_euler = rot
    return o


def strip_card(name, loc, look_at, w, h, strength=6.0):
    """emissive softbox card: shows up as long highlights on polished bevels"""
    import bmesh
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    bmesh.ops.scale(bm, vec=(w, h, 1), verts=bm.verts)
    bm.to_mesh(me)
    bm.free()
    m = bpy.data.materials.new(name + "_m")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    o_ = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs[1].default_value = strength
    nt.links.new(em.outputs[0], o_.inputs[0])
    me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    d = Vector(look_at) - Vector(loc)
    ob.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    ob.visible_camera = False
    ob.visible_shadow = False
    return ob


def camera(name="cam"):
    sc = bpy.context.scene
    cd = bpy.data.cameras.get(name) or bpy.data.cameras.new(name)
    cam = bpy.data.objects.get(name) or bpy.data.objects.new(name, cd)
    if cam.name not in sc.collection.objects:
        sc.collection.objects.link(cam)
    sc.camera = cam
    cd.sensor_fit = "VERTICAL"
    cd.sensor_height = 36
    cd.clip_start = 0.5
    cd.clip_end = 5000
    cd.dof.use_dof = True
    return cam


def aim(cam, loc, target, lens=80, fstop=8.0, focus=None, roll=0.0):
    cam.location = loc
    d = Vector(target) - Vector(loc)
    q = d.to_track_quat("-Z", "Y")
    cam.rotation_euler = q.to_euler()
    cam.rotation_euler.rotate_axis("Z", math.radians(roll))
    cam.data.lens = lens
    cam.data.dof.aperture_fstop = fstop
    cam.data.dof.focus_distance = focus if focus is not None else d.length


def render_settings(w=1080, h=1920, pct=100, samples=64, engine="EEVEE", mblur=False):
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 0.001
    r = sc.render
    r.resolution_x, r.resolution_y, r.resolution_percentage = w, h, pct
    r.image_settings.file_format = "JPEG"
    r.image_settings.quality = 93
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    r.use_motion_blur = mblur
    if engine == "CYCLES":
        r.engine = "CYCLES"
        p = bpy.context.preferences.addons["cycles"].preferences
        p.compute_device_type = "OPTIX"
        p.get_devices()
        for d in p.devices:
            d.use = d.type == "OPTIX"
        sc.cycles.device = "GPU"
        sc.cycles.samples = samples
        sc.cycles.use_denoising = True
        sc.cycles.denoiser = "OPTIX"
    else:
        r.engine = "BLENDER_EEVEE"
        e = sc.eevee
        e.taa_render_samples = samples
        for k, v in (("use_raytracing", True), ("use_shadows", True), ("ray_tracing_method", "SCREEN"),
                     ("use_fast_gi", True), ("shadow_ray_count", 2), ("shadow_step_count", 8)):
            try:
                setattr(e, k, v)
            except Exception:
                pass
        try:
            e.ray_tracing_options.resolution_scale = "1"
        except Exception:
            pass
