"""Versioned portable project recipes and optional animation metadata sidecars."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from .export import ExportConfig, validate_config
from .settings import RenderSettings, resolved_anim_range

RECIPE_VERSION = 1
METADATA_VERSION = 1


@dataclass
class Recipe:
    source: str
    settings: RenderSettings
    export: ExportConfig
    idle: str | None = None
    version: int = RECIPE_VERSION
    path: Path | None = None


def _as_rel(path: str | None, base: Path) -> str | None:
    if not path:
        return None
    p = Path(path).expanduser()
    try:
        return os.path.relpath(p.resolve(), base.resolve())
    except ValueError:
        return str(p)


def resolve_ref(ref: str | None, recipe_path: Path) -> str | None:
    if not ref:
        return None
    if not isinstance(ref, str):
        raise ValueError("Path references must be strings.")  # noqa: TRY004
    p = Path(ref).expanduser()
    if p.is_absolute():
        return str(p)
    return str((recipe_path.parent / p).resolve())


def export_from_dict(data: dict | None, *, strict: bool = False) -> ExportConfig:
    if data is None:
        return ExportConfig()
    if not isinstance(data, dict):
        raise ValueError("Export settings must be a JSON object.")  # noqa: TRY004
    known = {f.name for f in fields(ExportConfig)}
    proto = ExportConfig()
    kwargs = {}
    problems = []
    for key, value in data.items():
        if key not in known:
            problems.append(f"Unknown export field {key!r}.")
            continue
        default = getattr(proto, key)
        try:
            if isinstance(default, bool):
                if not isinstance(value, bool):
                    raise ValueError("expected true or false")  # noqa: TRY004
                kwargs[key] = value
            elif isinstance(default, int) and not isinstance(default, bool):
                if isinstance(value, bool):
                    raise ValueError("expected a number, not true/false")  # noqa: TRY004
                if isinstance(value, float) and (not value.is_integer()):
                    raise ValueError("expected a finite whole number")
                kwargs[key] = int(value)
            elif isinstance(default, str):
                if not isinstance(value, str):
                    raise ValueError("expected text")  # noqa: TRY004
                kwargs[key] = value
            elif default is None:
                kwargs[key] = value
            else:
                kwargs[key] = value
        except (TypeError, ValueError) as exc:
            problems.append(f"Invalid export {key} ({exc}).")
    if problems and strict:
        raise ValueError(" ".join(problems))
    cfg = ExportConfig(**kwargs)
    validate_config(cfg)
    return cfg


def build_recipe(source: str, settings: RenderSettings, export: ExportConfig,
                 idle: str | None = None) -> Recipe:
    return Recipe(source=source, idle=idle, settings=settings, export=export)


def recipe_to_dict(recipe: Recipe, recipe_path: Path) -> dict:
    base = recipe_path.parent
    export_data = asdict(recipe.export)
    if export_data.get("palette_path"):
        export_data["palette_path"] = _as_rel(export_data["palette_path"], base)
    return {
        "version": RECIPE_VERSION,
        "source": _as_rel(recipe.source, base) or "",
        "idle": _as_rel(recipe.idle, base),
        "settings": recipe.settings.to_dict(),
        "export": export_data,
    }


def save_recipe(path: Path, recipe: Recipe) -> Path:
    path = Path(path)
    recipe.settings.validate()
    validate_config(recipe.export)
    payload = recipe_to_dict(recipe, path)
    if not payload["source"]:
        raise ValueError("Recipe needs a source model path.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")
    return path


def load_recipe(path: Path) -> Recipe:
    path = Path(path)
    try:
        if path.stat().st_size > 1024 * 1024:
            raise ValueError("Recipe exceeds the 1 MiB size limit.")
        data = json.loads(path.read_text())
    except FileNotFoundError:
        raise ValueError(f"Recipe not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"Recipe is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Recipe must be a JSON object.")  # noqa: TRY004
    version = data.get("version")
    if type(version) is not int or version != RECIPE_VERSION:
        raise ValueError(
            f"Unsupported recipe version {version!r}. This app reads version {RECIPE_VERSION}."
        )
    extra = set(data) - {"version", "source", "idle", "settings", "export"}
    if extra:
        raise ValueError(f"Recipe has unknown fields: {', '.join(sorted(extra))}.")
    source = data.get("source")
    if not source or not isinstance(source, str):
        raise ValueError("Recipe is missing a source path.")
    settings_data = data.get("settings")
    if not isinstance(settings_data, dict):
        raise ValueError("Recipe is missing a settings object.")  # noqa: TRY004
    try:
        settings = RenderSettings.from_dict(settings_data, strict=True)
    except ValueError as exc:
        raise ValueError(f"Recipe settings are invalid: {exc}") from exc
    export = export_from_dict(data.get("export"), strict=True)
    resolved = resolve_ref(source, path)
    idle = resolve_ref(data.get("idle"), path) if data.get("idle") else None
    if export.palette_path:
        export.palette_path = resolve_ref(export.palette_path, path)
    return Recipe(source=resolved or source, idle=idle, settings=settings,
                  export=export, path=path)


def animation_metadata(
    settings: RenderSettings,
    *,
    clip_name: str | None = None,
    source_start: int | None = None,
    source_end: int | None = None,
    source_fps: int | None = None,
    playback_fps: int | None = None,
    replacement_used: bool = False,
    replacement_name: str | None = None,
    pivot: dict | None = None,
) -> dict:
    """Neutral sidecar: layout, sample times, playback vs source timing, pivot.

    Paths are names only; never absolute local source locations.
    """
    start, end = resolved_anim_range(settings, source_start, source_end)
    samples = settings.sample_times(start, end) if start is not None and end is not None else []
    sw, sh = settings.sheet_size()
    return {
        "version": METADATA_VERSION,
        "clip": Path(clip_name).stem if clip_name else None,
        "dimensions": {
            "frame_width": settings.frame_width,
            "frame_height": settings.frame_height,
            "sheet_width": sw,
            "sheet_height": sh,
            "layout_axis": settings.layout_axis,
        },
        "layout": {
            "start_direction": settings.start_direction,
            "rotation": settings.rotation,
            "directions": [
                {"name": name, "index": i, "camera_azimuth": angle,
                 "x": (i * settings.frame_width if settings.layout_axis == "cols"
                       else 0),
                 "y": (i * settings.frame_height if settings.layout_axis == "rows"
                       else 0)}
                for i, (name, angle) in enumerate(settings.direction_layout())
            ],
            "cell": {
                "frame_across": settings.layout_axis != "cols",
            },
        },
        "timing": {
            "loop_mode": settings.loop_mode,
            "looping": settings.loop_mode == "loop",
            "frames": settings.frames,
            "playback_fps": playback_fps,
            "source_fps": source_fps,
            "source_start": start,
            "source_end": end,
            "sample_times": samples,
            "phase_offset": 0.0 if settings.loop_mode == "oneshot" else settings.phase_offset,
            "reverse": settings.reverse,
        },
        "orientation": {"source_yaw": settings.source_yaw},
        "framing": {
            "mode": settings.framing_mode,
            "scale": settings.framing_scale if settings.framing_mode == "fixed" else None,
            "origin": [settings.framing_origin_x, settings.framing_origin_y,
                       settings.framing_origin_z] if settings.framing_mode == "fixed" else None,
            "anchor": settings.anchor,
            "output_offset": [settings.output_offset_x, settings.output_offset_y],
            "output_offset_units": "cell_pixels",
            "output_offset_sign": {"x": "right", "y": "down"},
        },
        "pivot": pivot or {
            "anchor": settings.anchor if settings.framing_mode != "fixed" else "origin",
            "origin": [settings.framing_origin_x, settings.framing_origin_y,
                       settings.framing_origin_z],
            "offset": [settings.output_offset_x, settings.output_offset_y],
        },
        "replacement": {
            "enabled": bool(replacement_used),
            "slot_index": 0,
            "replaces_existing_sample": True,
            "adds_slot": False,
            "blends": False,
            "name": Path(replacement_name).name if replacement_name else None,
        },
    }


def sidecar_path(image_path: Path) -> Path:
    return Path(image_path).with_name(Path(image_path).stem + ".json")


def write_metadata(image_path: Path, payload: dict) -> Path:
    dest = sidecar_path(image_path)
    dest.write_text(json.dumps(payload, indent=2) + "\n")
    return dest
