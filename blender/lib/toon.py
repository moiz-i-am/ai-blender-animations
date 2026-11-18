"""Flat / cel-shaded materials, glowing materials and ink outlines.

Look: two-tone cel shading (lit / shadow) made in Eevee with
Diffuse -> Shader to RGB -> constant Color Ramp -> x base colour -> Emission.
Outlines use the "inverted hull" trick (Solidify modifier + flipped normals +
back-face culled black material), which is fast and works in Eevee and Workbench.

Colours in PALETTE are written as normal display (sRGB) colours, the same values
you would pick in a colour picker. They are converted to linear for Blender.
"""
import bpy

PALETTE = {
    # ground / street
    "ground": (0.58, 0.76, 0.44),
    "asphalt": (0.24, 0.25, 0.29),
    "lane": (0.97, 0.96, 0.90),
    "sidewalk": (0.82, 0.80, 0.76),
    "curb": (0.66, 0.64, 0.62),
    # buildings
    "wall_a": (0.97, 0.87, 0.70),
    "wall_b": (0.80, 0.88, 0.95),
    "wall_c": (0.95, 0.77, 0.74),
    "wall_d": (0.86, 0.92, 0.80),
    "roof": (0.76, 0.33, 0.27),
    "roof_b": (0.34, 0.38, 0.48),
    "window": (0.58, 0.80, 0.95),
    "door": (0.48, 0.32, 0.24),
    # nature
    "trunk": (0.48, 0.33, 0.22),
    "leaf": (0.36, 0.64, 0.34),
    "leaf_b": (0.45, 0.72, 0.38),
    # hardware
    "metal": (0.60, 0.63, 0.67),
    "metal_dark": (0.20, 0.21, 0.24),
    "pole": (0.46, 0.49, 0.54),
    "camera_body": (0.93, 0.93, 0.90),
    "glass": (0.12, 0.15, 0.20),
    "sensor": (0.12, 0.12, 0.14),
    "accent": (0.95, 0.22, 0.22),
    "accent_b": (1.00, 0.82, 0.25),
    # vehicles
    "car": (0.16, 0.48, 0.88),
    "car_b": (0.95, 0.55, 0.20),
    "tire": (0.08, 0.08, 0.09),
    "plate": (0.98, 0.98, 0.95),
    "white": (1.0, 1.0, 1.0),
    "black": (0.02, 0.02, 0.02),
}

GLOW_NODE = "Glow"          # name of the Emission node in every material
OUTLINE_MAT = "_ink_outline"


def _s2l(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear(rgb):
    """sRGB (0-1) tuple -> linear RGBA tuple for Blender."""
    return tuple(_s2l(float(x)) for x in rgb[:3]) + (1.0,)


def _new_material(name):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.node_tree.nodes.clear()
    return mat


def _set_blended(mat):
    """Enable alpha blending across Eevee Legacy (<4.2) and Eevee Next (4.2+)."""
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "BLENDED"
    if hasattr(mat, "blend_method"):
        try:
            mat.blend_method = "BLEND"
        except TypeError:
            pass
    if hasattr(mat, "shadow_method"):
        try:
            mat.shadow_method = "NONE"
        except TypeError:
            pass


def toon(name, color=None, shadow=0.62, threshold=0.18):
    """Return (creating if needed) a two-tone cel material.

    name   -- material name; if it is a PALETTE key and color is None, uses that colour.
    color  -- sRGB tuple.
    shadow -- brightness multiplier of the shadow tone (0-1).
    """
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    if color is None:
        color = PALETTE[name]
    rgba = linear(color)
    mat = _new_material(name)
    mat.diffuse_color = rgba            # used by Workbench / viewport
    nt = mat.node_tree
    n, links = nt.nodes, nt.links

    out = n.new("ShaderNodeOutputMaterial")
    diff = n.new("ShaderNodeBsdfDiffuse")
    diff.inputs["Color"].default_value = (1, 1, 1, 1)
    s2r = n.new("ShaderNodeShaderToRGB")
    ramp = n.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.interpolation = "CONSTANT"
    cr.elements[0].position = 0.0
    cr.elements[0].color = (shadow, shadow, shadow, 1)
    cr.elements[1].position = threshold
    cr.elements[1].color = (1, 1, 1, 1)
    mul = n.new("ShaderNodeVectorMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = rgba[:3]
    emit = n.new("ShaderNodeEmission")
    emit.name = GLOW_NODE
    emit.inputs["Strength"].default_value = 1.0

    links.new(diff.outputs[0], s2r.inputs[0])
    links.new(s2r.outputs["Color"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], mul.inputs[0])
    links.new(mul.outputs[0], emit.inputs["Color"])
    links.new(emit.outputs[0], out.inputs["Surface"])

    for i, node in enumerate((diff, s2r, ramp, mul, emit, out)):
        node.location = (i * 220, 0)
    return mat


def glow(name, color, strength=1.0, alpha=1.0):
    """Unlit emissive material (lamps, screens, LEDs, beams).

    The Emission node is named GLOW_NODE so actions can keyframe its Strength.
    alpha < 1 makes it see-through (e.g. a radar beam).
    """
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    rgba = linear(color)
    mat = _new_material(name)
    mat.diffuse_color = rgba[:3] + (alpha,)
    nt = mat.node_tree
    n, links = nt.nodes, nt.links
    out = n.new("ShaderNodeOutputMaterial")
    emit = n.new("ShaderNodeEmission")
    emit.name = GLOW_NODE
    emit.inputs["Color"].default_value = rgba
    emit.inputs["Strength"].default_value = strength
    if alpha < 1.0:
        transp = n.new("ShaderNodeBsdfTransparent")
        mix = n.new("ShaderNodeMixShader")
        mix.inputs["Fac"].default_value = alpha
        links.new(transp.outputs[0], mix.inputs[1])
        links.new(emit.outputs[0], mix.inputs[2])
        links.new(mix.outputs[0], out.inputs["Surface"])
        _set_blended(mat)
    else:
        links.new(emit.outputs[0], out.inputs["Surface"])
    return mat


def get(mat):
    """Accept a Material, a material/palette name, or an sRGB tuple."""
    if mat is None:
        return None
    if isinstance(mat, bpy.types.Material):
        return mat
    if isinstance(mat, str):
        if mat in bpy.data.materials:
            return bpy.data.materials[mat]
        if mat in PALETTE:
            return toon(mat)
        raise KeyError(f"Unknown material/palette colour '{mat}'. Palette: {sorted(PALETTE)}")
    if isinstance(mat, (tuple, list)):
        key = "col_%02x%02x%02x" % tuple(int(max(0, min(1, c)) * 255) for c in mat[:3])
        return toon(key, tuple(mat))
    raise TypeError(f"Bad material spec: {mat!r}")


def outline_material():
    if OUTLINE_MAT in bpy.data.materials:
        return bpy.data.materials[OUTLINE_MAT]
    mat = _new_material(OUTLINE_MAT)
    mat.diffuse_color = (0.0, 0.0, 0.0, 1.0)
    mat.use_backface_culling = True
    n, links = mat.node_tree.nodes, mat.node_tree.links
    out = n.new("ShaderNodeOutputMaterial")
    emit = n.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = linear((0.06, 0.06, 0.08))
    links.new(emit.outputs[0], out.inputs["Surface"])
    return mat


def add_outline(obj, thickness=0.025):
    """Ink outline via inverted hull. Thickness is in world units (objects use scale 1)."""
    if obj.type != "MESH" or thickness <= 0:
        return
    mats = obj.data.materials
    om = outline_material()
    names = [m.name if m else None for m in mats]
    if not names:
        mats.append(get("white"))
        names = [mats[0].name]
    if OUTLINE_MAT not in names:
        mats.append(om)
        names.append(OUTLINE_MAT)
    idx = names.index(OUTLINE_MAT)
    mod = obj.modifiers.new("InkOutline", "SOLIDIFY")
    mod.thickness = thickness
    mod.offset = 1.0
    mod.use_flip_normals = True
    mod.use_rim = False
    mod.material_offset = idx
    if hasattr(mod, "use_quality_normals"):
        mod.use_quality_normals = True


def set_glow(mat_name, strength, frame=None):
    """Set (and optionally keyframe) the Strength of a material's Glow node."""
    node = bpy.data.materials[mat_name].node_tree.nodes[GLOW_NODE]
    sock = node.inputs["Strength"]
    sock.default_value = strength
    if frame is not None:
        sock.keyframe_insert("default_value", frame=frame)
