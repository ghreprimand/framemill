"""Render settings, direction layout, and built-in presets.

Engine-agnostic and JSON-serialisable. No convention is hardcoded as universal:
direction order, rotation, layout axis and animation phase are all configurable,
with defaults chosen to match the most common top-down/isometric setup.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, fields

# Canonical counter-clockwise character facings and their camera azimuths.
# Preserve name-to-camera mappings: orbiting the camera and turning the
# character are opposite operations (0 = South / facing camera).
_RINGS = {
    4: ["S", "E", "N", "W"],
    8: ["S", "SE", "E", "NE", "N", "NW", "W", "SW"],
    16: ["S", "SSE", "SE", "ESE", "E", "ENE", "NE", "NNE",
         "N", "NNW", "NW", "WNW", "W", "WSW", "SW", "SSW"],
}

VALID_ANGLES = (1, 4, 8, 16)
VALID_LOOP_MODES = ("loop", "oneshot")
VALID_FRAMING_MODES = ("fit", "fixed")
VALID_ANCHORS = ("center", "feet")
MAX_FRAMES = 64
MAX_CELL = 1024
MIN_RENDER = 16
MAX_RENDER = 8192
# Feet anchor leaves this fraction of the framed height as ground below the feet.
FEET_GROUND_MARGIN = 0.05
# Sheet RGBA budget (~256 MiB). Individual dimensions can still pass on their own.
MAX_SHEET_PIXELS = 64_000_000
# Limit each sequential render buffer, independently of animation length.
MAX_RENDER_PIXELS = 16_000_000


def _angle_for(count: int, index: int) -> float:
    return -(360.0 / count) * index  # camera azimuth, not character rotation


_ANGLES = {c: {name: _angle_for(c, i) for i, name in enumerate(ring)}
           for c, ring in _RINGS.items()}


def direction_names(angles: int) -> list[str]:
    """Names only, in default clockwise-from-S order (compat helper)."""
    return [name for name, _ in build_layout(angles)]


def build_layout(angles: int, start: str = "S", rotation: str = "cw") -> list[tuple[str, float]]:
    """Ordered [(name, camera_angle_deg)] honouring start direction + rotation.

    Each name keeps its canonical azimuth so the camera is always placed
    correctly; only the row/column ORDER changes.
    """
    ring = _RINGS.get(angles)
    if not ring:
        return [(f"angle{i}", _angle_for(angles, i)) for i in range(angles)]
    order = list(ring)
    if rotation == "cw":
        order = [order[0]] + order[1:][::-1]
    if start in order:
        i = order.index(start)
        order = order[i:] + order[:i]
    return [(name, _ANGLES[angles][name]) for name in order]


def sample_source_times(
    start: float,
    end: float,
    frames: int,
    *,
    loop_mode: str = "loop",
    phase_offset: float = 0.0,
    reverse: bool = False,
) -> list[float]:
    """Source times for each output frame.

    Loop keeps the historical wrap: ``start + (i / frames + phase) * (end - start)``,
    so the final endpoint is excluded (the usual walk-cycle case). Reverse wraps.

    One-shot includes both endpoints when ``frames >= 2``, ignores phase, and
    reverses without wrapping. A single one-shot frame is the start pose, or the
    end pose when reverse is set. A single loop frame is ``start + phase * length``.
    """
    length = float(end) - float(start)
    count = max(int(frames), 1)
    mode = loop_mode if loop_mode in VALID_LOOP_MODES else "loop"
    if length == 0:
        return [float(start)] * count
    times: list[float] = []
    for fi in range(count):
        if mode == "oneshot":
            frac = 0.0 if count == 1 else fi / (count - 1)
            if reverse:
                frac = 1.0 - frac
        else:
            frac = (fi / count) + float(phase_offset or 0.0)
            frac %= 1.0
            if reverse:
                frac = (1.0 - frac) % 1.0
        times.append(float(start) + frac * length)
    return times


def next_playback_frame(frame: int, frames: int, loop_mode: str) -> int | None:
    """Advance the viewer. ``None`` means a one-shot clip has finished."""
    count = max(int(frames), 1)
    nxt = int(frame) + 1
    if loop_mode == "oneshot":
        return nxt if nxt < count else None
    return nxt % count


def resolved_anim_range(
    settings: RenderSettings,
    detected_start: int | None,
    detected_end: int | None,
) -> tuple[int | None, int | None]:
    start = settings.anim_start_override if settings.anim_start_override is not None else detected_start
    end = settings.anim_end_override if settings.anim_end_override is not None else detected_end
    return start, end


def framing_ortho_scale(settings: RenderSettings, height: float) -> float:
    """World-unit orthographic scale. Fixed mode ignores per-clip height."""
    if settings.framing_mode == "fixed" and settings.framing_scale > 0:
        return float(settings.framing_scale)
    return max(float(height), 1e-3) * float(settings.ortho_scale_mult)


def framing_target(
    center: tuple[float, float, float],
    size: tuple[float, float, float],
    settings: RenderSettings,
) -> tuple[float, float, float]:
    """Camera look-at in world units.

    Fixed mode uses the explicit origin so related clips do not shift when
    their bounds change. Fit mode may use clip-bounds centre or lowest Z.
    Never recenters per frame.
    """
    if settings.framing_mode == "fixed":
        return (float(settings.framing_origin_x), float(settings.framing_origin_y),
                float(settings.framing_origin_z))
    if settings.anchor == "feet":
        # Sit the feet near the bottom of the framed area with the full body
        # above, rather than centring the window on the feet.
        scale = framing_ortho_scale(settings, size[2])
        feet_z = center[2] - size[2] / 2.0
        return (center[0], center[1], feet_z + scale / 2.0 - scale * FEET_GROUND_MARGIN)
    return (center[0], center[1], center[2])


@dataclass
class RenderSettings:
    # --- Output geometry ---
    angles: int = 8
    frames: int = 8
    frame_width: int = 96
    frame_height: int = 128

    # --- Supersampling (portrait, matches the default 3:4 cell) ---
    render_width: int = 1080
    render_height: int = 1440

    # --- Layout (no universal standard; all configurable) ---
    start_direction: str = "S"      # S | N | E | W (which direction is first)
    rotation: str = "ccw"           # cw | ccw
    layout_axis: str = "rows"       # rows = directions down / frames across; cols = transpose

    # --- Animation timing ---
    phase_offset: float = 0.0       # 0..1, shifts which pose is frame 0 (loop only)
    reverse: bool = False           # play the cycle backwards
    loop_mode: str = "loop"         # loop | oneshot

    # --- Source orientation (independent of sheet order and preview facing) ---
    source_yaw: float = 0.0         # degrees around world Z after import
    remove_root_motion: bool = False  # re-center travelling clips per frame

    # --- Shared framing (locked scale / anchor for related clips) ---
    framing_mode: str = "fit"       # fit | fixed
    framing_scale: float = 2.0      # world-unit ortho scale when framing_mode is fixed
    framing_origin_x: float = 0.0   # world-unit look-at; used only in fixed mode
    framing_origin_y: float = 0.0
    framing_origin_z: float = 0.0
    anchor: str = "feet"            # center | feet (fit mode); fixed mode uses origin
    output_offset_x: int = 0        # finished-cell pixels; +X right, +Y down
    output_offset_y: int = 0

    # --- Camera ---
    ortho_scale_mult: float = 1.8
    camera_distance: float = 2.52
    camera_pitch: float = 90.0

    # --- Lighting ---
    light_energy: float = 1000.0
    light_color: str = "#FFFFFF"
    shadow_soft_size: float = 0.1

    # --- Ambient / world ---
    ambient_color: str = "#FFFFFF"
    ambient_strength: float = 1.0

    # --- Colour management ---
    view_transform: str = "Standard"
    look: str = "None"
    exposure: float = 0.0
    gamma: float = 1.0

    # --- Material ---
    specular_ior: float = 0.5

    # --- Render engine ---
    engine: str = "BLENDER_EEVEE"
    samples: int = 64

    # --- Animation range override ---
    anim_start_override: int | None = None
    anim_end_override: int | None = None
    idle_frame_index: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict, *, strict: bool = False) -> RenderSettings:
        settings, warnings = cls.from_dict_recovering(data)
        if strict:
            if warnings:
                raise ValueError(" ".join(warnings))
            settings.validate()
        return settings

    @classmethod
    def from_dict_recovering(cls, data: dict) -> tuple[RenderSettings, list[str]]:
        """Lenient persist load: bad values fall back to defaults with messages."""
        warnings: list[str] = []
        if not isinstance(data, dict):
            return cls(), ["Saved render settings were not an object; using defaults."]
        known = {f.name for f in fields(cls)}
        proto = cls()
        kwargs: dict = {}
        for key, value in data.items():
            if key not in known:
                warnings.append(f"Ignored unknown setting {key!r}.")
                continue
            default = getattr(proto, key)
            try:
                kwargs[key] = _coerce_setting(default, value)
            except (TypeError, ValueError) as exc:
                warnings.append(f"Invalid {key} ({exc}); using default {default!r}.")
        settings = cls(**kwargs)
        try:
            settings.validate()
        except ValueError as exc:
            warnings.append(f"{exc} Restored default render settings.")
            return cls(), warnings
        return settings, warnings

    def direction_layout(self) -> list[tuple[str, float]]:
        return build_layout(self.angles, self.start_direction, self.rotation)

    def sheet_size(self) -> tuple[int, int]:
        w, h = int(self.frame_width), int(self.frame_height)
        if self.layout_axis == "cols":
            return w * int(self.angles), h * int(self.frames)
        return w * int(self.frames), h * int(self.angles)

    def sheet_pixels(self) -> int:
        sw, sh = self.sheet_size()
        return max(sw, 0) * max(sh, 0)

    def render_pixels(self) -> int:
        return (max(int(self.render_width), 0) * max(int(self.render_height), 0)
                )

    def estimated_sheet_bytes(self) -> int:
        return self.sheet_pixels() * 4

    def sample_times(self, start: float, end: float) -> list[float]:
        phase = 0.0 if self.loop_mode == "oneshot" else self.phase_offset
        return sample_source_times(
            start, end, self.frames,
            loop_mode=self.loop_mode, phase_offset=phase, reverse=self.reverse,
        )

    def validate(self) -> None:
        problems: list[str] = []
        defaults = RenderSettings()
        for field in fields(self):
            value, default = getattr(self, field.name), getattr(defaults, field.name)
            valid = True
            if default is None:
                valid = value is None or type(value) is int
            elif type(default) is bool:
                valid = type(value) is bool
            elif type(default) is int:
                valid = type(value) is int
            elif type(default) is float:
                valid = type(value) in (int, float) and math.isfinite(value)
            elif type(default) is str:
                valid = isinstance(value, str)
            if not valid:
                problems.append(f"Invalid type or non-finite value for {field.name}.")
        if problems:
            raise ValueError(" ".join(problems))
        for name in ("ortho_scale_mult", "camera_distance", "gamma", "framing_scale"):
            if getattr(self, name) <= 0:
                problems.append(f"{name} must be greater than zero.")
        for name in ("anim_start_override", "anim_end_override", "idle_frame_index"):
            value = getattr(self, name)
            if value is not None and abs(value) > 1_000_000:
                problems.append(f"{name} must be within -1000000 to 1000000.")
        if self.angles > 1 and self.start_direction not in _RINGS.get(self.angles, []):
            problems.append("Start direction must be one of the selected directions.")
        if not 0 <= self.phase_offset <= 1:
            problems.append("Phase must be between 0 and 1.")
        if (self.anim_start_override is not None and self.anim_end_override is not None
                and self.anim_end_override - self.anim_start_override > 10000):
            problems.append("Source range must span at most 10000 frames.")
        if self.angles not in VALID_ANGLES:
            problems.append("Directions must be 1, 4, 8 or 16.")
        if not 1 <= int(self.frames) <= MAX_FRAMES:
            problems.append(f"Frames must be between 1 and {MAX_FRAMES}.")
        if not 1 <= int(self.frame_width) <= MAX_CELL:
            problems.append(f"Sprite width must be between 1 and {MAX_CELL}.")
        if not 1 <= int(self.frame_height) <= MAX_CELL:
            problems.append(f"Sprite height must be between 1 and {MAX_CELL}.")
        if not MIN_RENDER <= int(self.render_width) <= MAX_RENDER:
            problems.append(f"Render width must be between {MIN_RENDER} and {MAX_RENDER}.")
        if not MIN_RENDER <= int(self.render_height) <= MAX_RENDER:
            problems.append(f"Render height must be between {MIN_RENDER} and {MAX_RENDER}.")
        if self.loop_mode not in VALID_LOOP_MODES:
            problems.append("Loop mode must be 'loop' or 'oneshot'.")
        if self.framing_mode not in VALID_FRAMING_MODES:
            problems.append("Framing mode must be 'fit' or 'fixed'.")
        if self.anchor not in VALID_ANCHORS:
            problems.append("Anchor must be 'center' or 'feet'.")
        if self.layout_axis not in ("rows", "cols"):
            problems.append("Sheet layout must be 'rows' or 'cols'.")
        if self.rotation not in ("cw", "ccw"):
            problems.append("Rotation must be 'cw' or 'ccw'.")
        if (self.anim_start_override is not None and self.anim_end_override is not None
                and int(self.anim_start_override) > int(self.anim_end_override)):
            problems.append("Source start must be at or before source end.")
        if self.framing_mode == "fixed" and float(self.framing_scale) <= 0:
            problems.append("Fixed framing needs a world scale greater than 0.")
        pixels = self.sheet_pixels()
        if pixels > MAX_SHEET_PIXELS:
            sw, sh = self.sheet_size()
            problems.append(
                f"Sheet would be {sw}×{sh} ({pixels:,} pixels, "
                f"~{self.estimated_sheet_bytes() / (1024 ** 2):.0f} MiB RGBA). "
                f"Reduce size, frames or directions (limit {MAX_SHEET_PIXELS:,} pixels)."
            )
        rendered = self.render_pixels()
        if rendered > MAX_RENDER_PIXELS:
            problems.append(
                f"Each render would be {rendered:,} pixels. "
                f"Reduce render resolution "
                f"(limit {MAX_RENDER_PIXELS:,} pixels)."
            )
        if problems:
            raise ValueError(" ".join(problems))

    def render_config(self) -> dict:
        """Config handed to the Blender-side script: settings + explicit layout,
        so the render script needs no direction/rotation logic of its own."""
        d = self.to_dict()
        d["_layout"] = [[name, angle] for name, angle in self.direction_layout()]
        return d


def _coerce_setting(default, value):
    if value is None:
        if default is None:
            return None
        raise ValueError("expected a value")
    if isinstance(default, bool):
        if isinstance(value, bool):
            return value
        raise ValueError("expected true or false")
    if isinstance(default, int) and not isinstance(default, bool):
        if isinstance(value, bool):
            raise ValueError("expected a number, not true/false")  # noqa: TRY004
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("expected a finite number")
        if isinstance(value, str) and value.strip() == "":
            raise ValueError("expected a number")
        if isinstance(value, float) and not value.is_integer():
            raise ValueError("expected a whole number")
        return int(value)
    if isinstance(default, float):
        if isinstance(value, bool):
            raise ValueError("expected a number, not true/false")  # noqa: TRY004
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("expected a finite number")
        return number
    if isinstance(default, str):
        if not isinstance(value, str):
            raise ValueError("expected text")  # noqa: TRY004
        return value
    if default is None:
        if isinstance(value, bool):
            raise ValueError("expected a number, not true/false")
        return _coerce_setting(0, value)
    return value


@dataclass
class Preset:
    key: str
    label: str
    description: str
    settings: RenderSettings


_GENERIC = RenderSettings()
_TRIPO = RenderSettings(
    view_transform="AgX", look="AgX - High Contrast",
    ambient_color="#E7D38D", ambient_strength=4.8, specular_ior=1.0)
_MIXAMO = RenderSettings(
    view_transform="Standard", ambient_color="#FFFFFF",
    ambient_strength=1.5, specular_ior=0.5)

PRESETS: dict[str, Preset] = {
    "generic": Preset("generic", "Generic PBR", "Neutral colour + lighting. Safe starting point for any model.", _GENERIC),
    "tripo": Preset("tripo", "Tripo", "Warm ambient + AgX high contrast, tuned for Tripo-generated meshes.", _TRIPO),
    "mixamo": Preset("mixamo", "Mixamo", "Neutral colour with a gentle ambient lift for Mixamo-rigged FBX.", _MIXAMO),
}

DEFAULT_PRESET = "generic"
