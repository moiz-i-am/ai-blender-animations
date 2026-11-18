"""Render settings, lighting and world."""
import math

import bpy


def engine_ids():
    return [i.identifier for i in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]


def configure(scene, episode, engine="eevee", scale=100, samples=None):
    w, h = episode.get("resolution", [1080, 1920])
    r = scene.render
    r.resolution_x, r.resolution_y = int(w), int(h)
    r.resolution_percentage = int(scale)
    r.fps = int(episode.get("fps", 30))
    r.fps_base = 1.0
    # Transparent film: the sky/background is painted later by the compositor (pipeline/overlays.py)
    r.film_transparent = True
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGBA"
    r.image_settings.color_depth = "8"
    r.image_settings.compression = 15
    # "Standard" keeps flat colours exactly as picked (Filmic/AgX would wash them out)
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"

    ids = engine_ids()
    if engine == "eevee":
        r.engine = next((e for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE") if e in ids), ids[0])
        ee = scene.eevee
        ee.taa_render_samples = int(samples or 16)
        for attr, val in (("use_gtao", False), ("use_bloom", False), ("use_ssr", False),
                          ("use_soft_shadows", True)):
            if hasattr(ee, attr):
                setattr(ee, attr, val)
    elif engine == "workbench":
        # No-GPU / quick-check fallback: flat studio lighting + object outlines.
        r.engine = "BLENDER_WORKBENCH"
        sh = scene.display.shading
        sh.light = "STUDIO"
        sh.color_type = "MATERIAL"
        sh.show_object_outline = True
        sh.object_outline_color = (0, 0, 0)
        sh.show_backface_culling = True
        sh.show_shadows = True
        scene.display.render_aa = "8"
    else:
        raise ValueError(f"Unknown engine '{engine}' (use eevee or workbench)")
    return r.engine


def lighting(ctx, sun_rotation=(48, 8, 35), sun_strength=2.5, ambient=0.05):
    """Single sun = crisp two-tone cel shading. Ambient world light stays low so
    shadow sides fall below the cel threshold."""
    sun_data = bpy.data.lights.new("Sun", "SUN")
    sun_data.energy = float(sun_strength)
    sun_data.angle = math.radians(2.0)
    sun = bpy.data.objects.new("Sun", sun_data)
    ctx.collection.objects.link(sun)
    sun.rotation_euler = [math.radians(a) for a in sun_rotation]

    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes.get("Background")
    if bg is None:  # newer Blender versions may create worlds without default nodes
        bg = nt.nodes.new("ShaderNodeBackground")
        out = nt.nodes.get("World Output") or nt.nodes.new("ShaderNodeOutputWorld")
        nt.links.new(bg.outputs[0], out.inputs["Surface"])
    bg.inputs[0].default_value = (1, 1, 1, 1)
    bg.inputs[1].default_value = float(ambient)
    ctx.scene.world = world
    return sun
