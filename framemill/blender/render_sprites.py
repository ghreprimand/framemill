#!/usr/bin/env python3
"""framemill Blender render script (runs INSIDE Blender's Python).

    blender --background --python render_sprites.py -- \
        --input model.fbx --output frames/ --config config.json [--idle idle.fbx] [--preview] [--inspect]

Reads a JSON config produced from framemill.settings.RenderSettings and renders
one PNG per (direction, frame) named "<DIR>_<NN>.png". All tuning values come
from the config; nothing project-specific is hardcoded.
"""
import bpy
import mathutils
import sys
import os
import json
import math
from pathlib import Path

DIRECTIONS = {
    1: ["S"],
    4: ["S", "E", "N", "W"],
    8: ["S", "SE", "E", "NE", "N", "NW", "W", "SW"],
    16: ["S", "SSE", "SE", "ESE", "E", "ENE", "NE", "NNE",
         "N", "NNW", "NW", "WNW", "W", "WSW", "SW", "SSW"],
}


def log(msg):
    print(msg, flush=True)


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out, i = {}, 0
    flags = {"--input": "input", "--output": "output", "--config": "config", "--idle": "idle"}
    while i < len(argv):
        a = argv[i]
        if a in flags and i + 1 < len(argv):
            out[flags[a]] = argv[i + 1]; i += 2
        elif a == "--preview":
            out["preview"] = True; i += 1
        elif a == "--inspect":
            out["inspect"] = True; i += 1
        else:
            i += 1
    return out


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images):
        for block in list(coll):
            if block.users == 0:
                coll.remove(block)


def import_model(filepath):
    ext = Path(filepath).suffix.lower()
    try:
        if ext == ".fbx":
            bpy.ops.import_scene.fbx(filepath=filepath)
        elif ext in (".glb", ".gltf"):
            bpy.ops.import_scene.gltf(filepath=filepath)
        elif ext == ".obj":
            bpy.ops.wm.obj_import(filepath=filepath)
        else:
            raise RuntimeError(f"Unsupported model format: {ext}")
    except RuntimeError as e:
        # Some Blender/FBX combos throw on embedded lights after meshes load.
        if "cast_shadow" not in str(e):
            raise
        log("FRAMEMILL: warning - importer complained about embedded lights, continuing")
    objs = list(bpy.context.selected_objects) or \
        [o for o in bpy.data.objects if o.type in ("MESH", "ARMATURE")]
    return objs


def hex_to_rgb(s):
    s = (s or "#FFFFFF").lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    try:
        return tuple(int(s[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    except ValueError:
        return (1.0, 1.0, 1.0)


def adjust_materials(cfg):
    ior = cfg.get("specular_ior", 0.5)
    for mat in bpy.data.materials:
        if not mat.node_tree:
            continue
        has_tex = False
        for node in mat.node_tree.nodes:
            if node.type == "TEX_IMAGE" and node.image:
                has_tex = True
                node.image.colorspace_settings.name = "sRGB"
        if has_tex:
            for node in mat.node_tree.nodes:
                if node.type == "BSDF_PRINCIPLED" and "Specular IOR Level" in node.inputs:
                    node.inputs["Specular IOR Level"].default_value = ior


def anim_range(objs):
    for o in objs:
        ad = o.animation_data
        if ad and ad.action:
            return int(ad.action.frame_range[0]), int(ad.action.frame_range[1])
    return bpy.context.scene.frame_start, bpy.context.scene.frame_end


def max_bounds(objs, start, end):
    lo = [float("inf")] * 3
    hi = [float("-inf")] * 3
    orig = bpy.context.scene.frame_current
    for f in range(int(start), int(end) + 1):
        bpy.context.scene.frame_set(f)
        for o in objs:
            if o.type != "MESH":
                continue
            for corner in o.bound_box:
                wc = o.matrix_world @ mathutils.Vector(corner)
                for i in range(3):
                    lo[i] = min(lo[i], wc[i]); hi[i] = max(hi[i], wc[i])
    bpy.context.scene.frame_set(orig)
    if lo[0] == float("inf"):
        return (0, 0, 0), (1, 1, 1)
    center = tuple((lo[i] + hi[i]) / 2 for i in range(3))
    size = tuple(hi[i] - lo[i] for i in range(3))
    return center, size


def setup_camera(center, size, angle_deg, cfg):
    for o in [o for o in bpy.data.objects if o.type == "CAMERA"]:
        bpy.data.objects.remove(o)
    cam = bpy.data.cameras.new("FMCamera")
    cam.type = "ORTHO"
    cam.ortho_scale = max(size[2], 1e-3) * cfg.get("ortho_scale_mult", 1.8)
    obj = bpy.data.objects.new("FMCamera", cam)
    bpy.context.scene.collection.objects.link(obj)
    dist = cfg.get("camera_distance", 2.52)
    pitch = cfg.get("camera_pitch", 90.0)
    a = math.radians(angle_deg)
    obj.location = (center[0] + math.sin(a) * dist,
                    center[1] - math.cos(a) * dist,
                    center[2])
    obj.rotation_euler = (math.radians(pitch), 0, a)
    bpy.context.scene.camera = obj


def setup_light(center, angle_deg, cfg):
    for o in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        bpy.data.objects.remove(o)
    data = bpy.data.lights.new("FMLight", type="POINT")
    data.energy = cfg.get("light_energy", 1000.0)
    data.color = hex_to_rgb(cfg.get("light_color", "#FFFFFF"))
    data.shadow_soft_size = cfg.get("shadow_soft_size", 0.1)
    obj = bpy.data.objects.new("FMLight", data)
    bpy.context.scene.collection.objects.link(obj)
    a = math.radians(angle_deg)
    d = cfg.get("camera_distance", 2.52) * 1.2
    obj.location = (center[0] + math.sin(a) * d, center[1] - math.cos(a) * d, center[2] + 4.0)


def pick_engine(name):
    try:
        avail = bpy.context.scene.render.bl_rna.properties["engine"].enum_items.keys()
    except Exception:
        avail = []
    if name in avail:
        return name
    for cand in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"):
        if cand in avail:
            return cand
    return name


def setup_render(cfg, preview):
    s = bpy.context.scene
    if preview:
        s.render.resolution_x = max(2, cfg.get("render_width", 1920) // 2)
        s.render.resolution_y = max(2, cfg.get("render_height", 1080) // 2)
    else:
        s.render.resolution_x = cfg.get("render_width", 1920)
        s.render.resolution_y = cfg.get("render_height", 1080)
    s.render.resolution_percentage = 100
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_mode = "RGBA"
    s.render.film_transparent = True
    s.render.engine = pick_engine(cfg.get("engine", "BLENDER_EEVEE"))
    if hasattr(s, "eevee"):
        try:
            s.eevee.taa_render_samples = cfg.get("samples", 64)
        except Exception:
            pass
    # Colour management
    try:
        s.view_settings.view_transform = cfg.get("view_transform", "Standard")
        look = cfg.get("look", "None")
        s.view_settings.look = look if look else "None"
    except (TypeError, KeyError):
        pass
    s.view_settings.exposure = cfg.get("exposure", 0.0)
    s.view_settings.gamma = cfg.get("gamma", 1.0)
    # World / ambient
    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    s.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()
    bg = nodes.new("ShaderNodeBackground")
    r, g, b = hex_to_rgb(cfg.get("ambient_color", "#FFFFFF"))
    bg.inputs["Color"].default_value = (r, g, b, 1.0)
    bg.inputs["Strength"].default_value = cfg.get("ambient_strength", 1.0)
    out = nodes.new("ShaderNodeOutputWorld")
    links.new(bg.outputs["Background"], out.inputs["Surface"])


def render_all(model, out_dir, cfg, idle=None, preview=False):
    full_layout = cfg.get("_layout")
    if not full_layout:
        n = cfg.get("angles", 8)
        names = DIRECTIONS.get(n, [f"angle{i}" for i in range(n)])
        full_layout = [[nm, -(360.0 / n) * i] for i, nm in enumerate(names)]

    if preview:
        layout = [full_layout[0]]
        frames = 1
    else:
        layout = full_layout
        frames = cfg.get("frames", 4)

    phase = float(cfg.get("phase_offset", 0.0) or 0.0)
    reverse = bool(cfg.get("reverse", False))
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    total = len(layout) * frames

    def sample_frame(fi, start, length):
        if length <= 0:
            return start
        frac = (fi / max(frames, 1)) + phase
        frac = frac % 1.0
        if reverse:
            frac = (1.0 - frac) % 1.0
        return start + frac * length

    def render_from(path, frame_indices, ref=None):
        clear_scene()
        objs = import_model(path)
        adjust_materials(cfg)
        start = cfg.get("anim_start_override") or anim_range(objs)[0]
        end = cfg.get("anim_end_override") or anim_range(objs)[1]
        center, size = ref if ref else max_bounds(objs, start, end)
        setup_render(cfg, preview)
        length = end - start
        counter = render_from.counter
        for name, deg in layout:
            setup_camera(center, size, deg, cfg)
            setup_light(center, deg, cfg)
            for fi in frame_indices:
                if len(frame_indices) == 1 and length > 0:
                    idle_idx = cfg.get("idle_frame_index")
                    af = idle_idx if idle_idx is not None else end
                else:
                    af = sample_frame(fi, start, length)
                bpy.context.scene.frame_set(int(af))
                bpy.context.scene.render.filepath = os.path.join(out_dir, f"{name}_{fi:02d}.png")
                bpy.ops.render.render(write_still=True)
                counter += 1
                log(f"FRAMEMILL: PROGRESS {counter}/{total}")
        render_from.counter = counter
        return center, size

    render_from.counter = 0
    if idle and not preview:
        ref = render_from(model, list(range(1, frames)))
        render_from(idle, [0], ref=ref)
    else:
        render_from(model, list(range(frames)))
    log("FRAMEMILL: COMPLETE")


def do_inspect(model):
    clear_scene()
    objs = import_model(model)
    start, end = anim_range(objs)
    log("FRAMEMILL: INSPECT " + json.dumps(
        {"frame_start": int(start), "frame_end": int(end),
         "fps": int(bpy.context.scene.render.fps)}))


def main():
    args = parse_args()
    if not args.get("input") or not args.get("config"):
        log("FRAMEMILL: ERROR missing --input/--config")
        sys.exit(1)
    cfg = json.loads(Path(args["config"]).read_text() or "{}")
    if args.get("inspect"):
        do_inspect(args["input"])
        return
    render_all(args["input"], args["output"], cfg,
               idle=args.get("idle"), preview=args.get("preview", False))


if __name__ == "__main__":
    main()
