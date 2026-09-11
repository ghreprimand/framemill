"""Headless CLI. The GUI is the primary interface; this exists for scripting/CI."""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import tempfile
from pathlib import Path

from . import blender, compositor, recipe
from .settings import DEFAULT_PRESET, PRESETS, RenderSettings

CLI_FORMATS = {"png", "tga"}


def _resolve_blender(explicit: str | None) -> str:
    path = explicit or blender.find_blender()
    if not path:
        sys.exit("Blender not found. Pass --blender /path/to/blender or add it to PATH.")
    return path


def _parse_formats(raw: str) -> list[str]:
    formats = [f.strip().lower() for f in (raw or "").split(",") if f.strip()]
    if not formats:
        raise ValueError("Choose at least one output format: png, tga.")
    unknown = [f for f in formats if f not in CLI_FORMATS]
    if unknown:
        raise ValueError(
            f"Unknown format: {', '.join(unknown)}. CLI export supports png and tga."
        )
    return formats


def _settings_from_args(a: argparse.Namespace) -> tuple[RenderSettings, str, str | None]:
    idle = a.idle
    if a.recipe:
        rec = recipe.load_recipe(Path(a.recipe))
        settings = rec.settings
        model = a.model or rec.source
        idle = a.idle or rec.idle
        if not model:
            raise ValueError("Recipe has no source path. Pass a model argument.")
    else:
        if not a.model:
            raise ValueError("Pass a model path or --recipe.")
        settings = PRESETS[a.preset].settings
        model = a.model
    if a.angles:
        settings = dataclasses.replace(settings, angles=a.angles)
    if a.frames is not None:
        if a.frames < 1:
            raise ValueError("--frames must be a positive integer.")
        settings = dataclasses.replace(settings, frames=a.frames)
    settings.validate()
    return settings, model, idle


def _cmd_render(a: argparse.Namespace) -> None:
    try:
        settings, model, idle = _settings_from_args(a)
        formats = _parse_formats(a.format)
    except ValueError as exc:
        sys.exit(str(exc))
    bpath = _resolve_blender(a.blender)
    out = Path(a.output)
    inspected = None
    if a.metadata:
        try:
            inspected = blender.inspect(bpath, model)
        except Exception as exc:  # noqa: BLE001 — metadata needs the live range
            sys.exit(f"Could not inspect source for metadata: {exc}")

    with tempfile.TemporaryDirectory() as tmp:
        frames_dir = Path(tmp) / "frames"

        def prog(p: blender.RenderProgress) -> None:
            print(f"\r{p.stage}", end="", flush=True)

        blender.render(bpath, model, frames_dir, settings,
                       idle_path=idle, on_progress=prog)
        print()
        written = compositor.composite(frames_dir, out, settings, formats,
                                       magic_pink=a.magic_pink)
    for p in written:
        print(f"wrote {p}")
        if a.metadata:
            dest = recipe.write_metadata(p, recipe.animation_metadata(
                settings, clip_name=Path(model).stem,
                source_start=None if inspected is None else inspected.get("frame_start"),
                source_end=None if inspected is None else inspected.get("frame_end"),
                source_fps=None if inspected is None else inspected.get("fps"),
                replacement_used=bool(idle),
                replacement_name=Path(idle).name if idle else None,
            ))
            print(f"wrote {dest}")


def _cmd_inspect(a: argparse.Namespace) -> None:
    bpath = _resolve_blender(a.blender)
    print(json.dumps(blender.inspect(bpath, a.model), indent=2))


def _cmd_gui(_: argparse.Namespace) -> None:
    from .app import run
    run()


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="framemill", description="3D model -> directional sprite sheet.")
    p.add_argument("--blender", help="path to the Blender executable")
    sub = p.add_subparsers(dest="cmd", required=False)

    r = sub.add_parser("render", help="render a sprite sheet")
    r.add_argument("model", nargs="?", help="input .fbx/.glb/.gltf/.obj")
    r.add_argument("-o", "--output", required=True, help="output path (extension set per --format)")
    r.add_argument("--preset", choices=list(PRESETS), default=DEFAULT_PRESET)
    r.add_argument("--angles", type=int, choices=[1, 4, 8, 16])
    r.add_argument("--frames", type=int, help="output frame count (1–64)")
    r.add_argument("--recipe", help="versioned project recipe (JSON)")
    r.add_argument("--idle", help="advanced: replace frame 0 with a second model pose; keeps total count, no blending")
    r.add_argument("--format", default="png", help="comma list: png,tga")
    r.add_argument("--magic-pink", action="store_true", help="TGA: transparent -> magenta (legacy engines)")
    r.add_argument("--metadata", action="store_true", help="write a JSON sidecar next to each image")
    r.set_defaults(func=_cmd_render)

    i = sub.add_parser("inspect", help="print animation frame range + fps")
    i.add_argument("model")
    i.set_defaults(func=_cmd_inspect)

    g = sub.add_parser("gui", help="launch the desktop app")
    g.set_defaults(func=_cmd_gui)

    args = p.parse_args(argv)
    if not args.cmd:
        _cmd_gui(args)
        return
    args.func(args)


if __name__ == "__main__":
    main()
