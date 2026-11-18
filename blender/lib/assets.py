"""Import external models (Poly Haven, Sketchfab, Meshy, Tripo, TRELLIS, Hunyuan3D ...)
and convert them to the house cel style.

Put files in assets/models/ and reference them by path relative to the repo root.
Always check the licence of downloaded models (see docs/SCENES.md).
"""
import os

import bpy

from . import toon

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _principled_color(mat):
    if not mat or not mat.use_nodes:
        return None
    for node in mat.node_tree.nodes:
        if node.type == "BSDF_PRINCIPLED":
            c = node.inputs["Base Color"].default_value
            # linear -> rough sRGB
            return tuple(max(0.0, min(1.0, v)) ** (1 / 2.2) for v in c[:3])
    return None


def import_model(ctx, name, path, loc=(0, 0, 0), rot=(0, 0, 0), scale=1.0,
                 toonify=True, outline=True, fallback_color="white", parent=None):
    """Import .glb/.gltf/.fbx/.obj, parent all parts to an empty called `name`, return it.

    toonify=True swaps every material for a cel material using its base colour
    (textures are dropped, which suits the flat style; set False to keep them).
    """
    import math
    full = path if os.path.isabs(path) else os.path.join(REPO_ROOT, path)
    if not os.path.exists(full):
        raise FileNotFoundError(full)
    before = set(bpy.data.objects)
    ext = os.path.splitext(full)[1].lower()
    if ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=full)
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=full)
    elif ext == ".obj":
        if hasattr(bpy.ops.wm, "obj_import"):
            bpy.ops.wm.obj_import(filepath=full)
        else:
            bpy.ops.import_scene.obj(filepath=full)
    else:
        raise ValueError(f"Unsupported model type: {ext}")
    new = [o for o in bpy.data.objects if o not in before]

    root = bpy.data.objects.new(name, None)
    ctx.collection.objects.link(root)
    for o in new:
        if o.parent is None:
            o.parent = root
        if o.type == "MESH" and toonify:
            for i, slot in enumerate(o.material_slots):
                col = _principled_color(slot.material) or toon.PALETTE.get(fallback_color, (1, 1, 1))
                slot.material = toon.get(tuple(col))
            if outline:
                toon.add_outline(o, ctx.outline if outline is True else float(outline))
    root.location = loc
    root.rotation_euler = [math.radians(a) for a in rot]
    root.scale = (scale, scale, scale)
    if parent is not None:
        root.parent = ctx.get(parent) if isinstance(parent, str) else parent
    ctx.register(name, root)
    return root
