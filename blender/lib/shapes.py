"""Primitive builders (box, cylinder, cone, sphere, roof, empty, light).

All meshes are built with bmesh (no bpy.ops), so they work headless.
Sizes are baked into the mesh, so object scale stays 1 and outline thickness stays even.
By default the origin is at the *bottom centre* (origin="bottom"), which makes
placing things on the ground easy: loc=(x, y, 0) sits on the floor.

Common keyword arguments
  loc      (x, y, z) location (relative to parent if parent is given)
  rot      (x, y, z) rotation in DEGREES
  mat      palette name / material name / sRGB tuple / Material
  outline  True (episode default thickness), False, or a float thickness
  parent   object or registered name
  bevel    bevel width (0 = none) - softens edges for a toy look
  register False to skip adding to ctx.objects (for tiny details)
"""
import math

import bmesh
import bpy
from mathutils import Vector

from . import toon


def _finish(ctx, name, bm, loc, rot, mat, outline, parent, bevel, register=True):
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    ctx.collection.objects.link(obj)
    if mat is not None:
        me.materials.append(toon.get(mat))
    obj.location = loc
    if rot:
        obj.rotation_euler = [math.radians(a) for a in rot]
    if parent is not None:
        obj.parent = ctx.get(parent) if isinstance(parent, str) else parent
    if bevel:
        mod = obj.modifiers.new("Bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        mod.limit_method = "ANGLE"
    if outline:
        toon.add_outline(obj, ctx.outline if outline is True else float(outline))
    if register:
        ctx.register(name, obj)
    return obj


def box(ctx, name, size=(1, 1, 1), loc=(0, 0, 0), rot=None, mat="white",
        outline=True, parent=None, bevel=0.0, origin="bottom", register=True):
    sx, sy, sz = size
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    zoff = sz / 2 if origin == "bottom" else 0.0
    for v in bm.verts:
        v.co = Vector((v.co.x * sx, v.co.y * sy, v.co.z * sz + zoff))
    return _finish(ctx, name, bm, loc, rot, mat, outline, parent, bevel, register)


def cone(ctx, name, radius1=0.5, radius2=0.0, depth=1.0, segments=24, loc=(0, 0, 0),
         rot=None, mat="white", outline=True, parent=None, origin="bottom", register=True):
    """radius1 = bottom radius, radius2 = top radius. Axis along local Z."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segments,
                          radius1=radius1, radius2=radius2, depth=depth)
    if origin == "bottom":
        bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, depth / 2))
    elif origin == "top":
        bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, -depth / 2))
    return _finish(ctx, name, bm, loc, rot, mat, outline, parent, 0, register)


def cylinder(ctx, name, radius=0.5, depth=1.0, segments=24, **kw):
    return cone(ctx, name, radius1=radius, radius2=radius, depth=depth, segments=segments, **kw)


def sphere(ctx, name, radius=0.5, segments=12, rings=8, loc=(0, 0, 0), rot=None,
           mat="white", outline=True, parent=None, register=True):
    """Low-poly UV sphere (origin at centre). Low segment counts look toy-like."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=radius)
    return _finish(ctx, name, bm, loc, rot, mat, outline, parent, 0, register)


def roof(ctx, name, width=4.0, depth=4.0, height=1.5, loc=(0, 0, 0), rot=None,
         mat="roof", outline=True, parent=None, register=True):
    """Gable roof (triangular prism). Ridge runs along local Y. Origin at base centre."""
    hw, hd = width / 2, depth / 2
    pts = [(-hw, -hd, 0), (hw, -hd, 0), (0, -hd, height),
           (-hw, hd, 0), (hw, hd, 0), (0, hd, height)]
    bm = bmesh.new()
    v = [bm.verts.new(p) for p in pts]
    for f in ((0, 1, 2), (5, 4, 3), (0, 3, 4, 1), (0, 2, 5, 3), (1, 4, 5, 2)):
        bm.faces.new([v[i] for i in f])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _finish(ctx, name, bm, loc, rot, mat, outline, parent, 0, register)


def empty(ctx, name, loc=(0, 0, 0), parent=None, register=True, size=0.3):
    """Invisible helper: group parent or anchor point for labels / camera targets."""
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_size = size
    ctx.collection.objects.link(obj)
    obj.location = loc
    if parent is not None:
        obj.parent = ctx.get(parent) if isinstance(parent, str) else parent
    if register:
        ctx.register(name, obj)
    return obj


def point_light(ctx, name, loc=(0, 0, 0), energy=0.0, color=(1, 1, 1), radius=0.2, parent=None):
    data = bpy.data.lights.new(name, "POINT")
    data.energy = energy
    data.color = color
    data.shadow_soft_size = radius
    obj = bpy.data.objects.new(name, data)
    ctx.collection.objects.link(obj)
    obj.location = loc
    if parent is not None:
        obj.parent = ctx.get(parent) if isinstance(parent, str) else parent
    ctx.register(name, obj)
    return obj


def aim(obj, target):
    """Rotate obj so its local -Z axis points at target (Vector or tuple)."""
    bpy.context.view_layer.update()
    direction = Vector(target) - obj.matrix_world.translation
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
