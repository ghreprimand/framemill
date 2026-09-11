"""Headless CLI. The GUI is the primary interface; this exists for scripting/CI."""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from . import blender, compositor
from .settings import DEFAULT_PRESET, PRESETS, RenderSettings


def _resolve_blender(explicit: str | None) -> str:
    path = explicit or blender.find_blender()
    if not path:
        sys.exit("Blender not found. Pass --blender /path/to/blender or add it to PATH.")
    return path


def _cmd_render(a: argparse.Namespace) -> None:
    bpath = _resolve_blender(a.blender)
    settings = PRESETS[a.preset].settings
    if a.angles:
        settings = RenderSettings.from_dict({**settings.to_dict(), "angles": a.angles})
    if a.frames:
        settings = RenderSettings.from_dict({**settings.to_dict(), "frames": a.frames})
    out = Path(a.output)
    formats = [f.strip() for f in a.format.split(",") if f.strip()]

    with tempfile.TemporaryDirectory() as tmp:
        frames_dir = Path(tmp) / "frames"

        def prog(p: blender.RenderProgress) -> None:
            print(f"\r{p.stage}", end="", flush=True)

        blender.render(bpath, a.model, frames_dir, settings,
                       idle_path=a.idle, on_progress=prog)
        print()
        written = compositor.composite(frames_dir, out, settings, formats,
                                       magic_pink=a.magic_pink)
    for p in written:
        print(f"wrote {p}")


def _cmd_inspect(a: argparse.Namespace) -> None:
    bpath = _resolve_blender(a.blender)
    print(blender.inspect(bpath, a.model))


def _cmd_gui(_: argparse.Namespace) -> None:
    from .app import run
    run()


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="framemill", description="3D model -> directional sprite sheet.")
    p.add_argument("--blender", help="path to the Blender executable")
    sub = p.add_subparsers(dest="cmd", required=False)

    r = sub.add_parser("render", help="render a sprite sheet")
    r.add_argument("model", help="input .fbx/.glb/.gltf/.obj")
    r.add_argument("-o", "--output", required=True, help="output path (extension set per --format)")
    r.add_argument("--preset", choices=list(PRESETS), default=DEFAULT_PRESET)
    r.add_argument("--angles", type=int, choices=[1, 4, 8, 16])
    r.add_argument("--frames", type=int)
    r.add_argument("--idle", help="advanced: replace frame 0 with a second model pose; keeps total count, no blending")
    r.add_argument("--format", default="png", help="comma list: png,tga")
    r.add_argument("--magic-pink", action="store_true", help="TGA: transparent -> magenta (legacy engines)")
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
