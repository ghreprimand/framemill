"""Render settings, direction layout, and built-in presets.

Engine-agnostic and JSON-serialisable. No convention is hardcoded as universal:
direction order, rotation, layout axis and animation phase are all configurable,
with defaults chosen to match the most common top-down/isometric setup.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Tuple

# Canonical clockwise rings and each name's camera azimuth (degrees).
# Angle sign matches the render camera math (0 = South / facing camera).
_RINGS = {
    4: ["S", "E", "N", "W"],
    8: ["S", "SE", "E", "NE", "N", "NW", "W", "SW"],
    16: ["S", "SSE", "SE", "ESE", "E", "ENE", "NE", "NNE",
         "N", "NNW", "NW", "WNW", "W", "WSW", "SW", "SSW"],
}


def _angle_for(count: int, index: int) -> float:
    return -(360.0 / count) * index  # negative = clockwise


_ANGLES = {c: {name: _angle_for(c, i) for i, name in enumerate(ring)}
           for c, ring in _RINGS.items()}


def direction_names(angles: int) -> List[str]:
    """Names only, in default clockwise-from-S order (compat helper)."""
    return list(_RINGS.get(angles, [f"angle{i}" for i in range(angles)]))


def build_layout(angles: int, start: str = "S", rotation: str = "cw") -> List[Tuple[str, float]]:
    """Ordered [(name, camera_angle_deg)] honouring start direction + rotation.

    Each name keeps its canonical azimuth so the camera is always placed
    correctly; only the row/column ORDER changes.
    """
    ring = _RINGS.get(angles)
    if not ring:
        return [(f"angle{i}", _angle_for(angles, i)) for i in range(angles)]
    order = list(ring)
    if rotation == "ccw":
        order = [order[0]] + order[1:][::-1]
    if start in order:
        i = order.index(start)
        order = order[i:] + order[:i]
    return [(name, _ANGLES[angles][name]) for name in order]


@dataclass
class RenderSettings:
    # --- Output geometry ---
    angles: int = 8
    frames: int = 4
    frame_width: int = 96
    frame_height: int = 128

    # --- Supersampling ---
    render_width: int = 1920
    render_height: int = 1080

    # --- Layout (no universal standard — all configurable) ---
    start_direction: str = "S"      # S | N | E | W (which direction is first)
    rotation: str = "cw"            # cw | ccw
    layout_axis: str = "rows"       # rows = directions down / frames across; cols = transpose

    # --- Animation timing ---
    phase_offset: float = 0.0       # 0..1, shifts which pose is frame 0
    reverse: bool = False           # play the cycle backwards

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
    def from_dict(cls, data: dict) -> "RenderSettings":
        known = set(cls.__dataclass_fields__)  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})

    def direction_layout(self) -> List[Tuple[str, float]]:
        return build_layout(self.angles, self.start_direction, self.rotation)

    def render_config(self) -> dict:
        """Config handed to the Blender-side script: settings + explicit layout,
        so the render script needs no direction/rotation logic of its own."""
        d = self.to_dict()
        d["_layout"] = [[name, angle] for name, angle in self.direction_layout()]
        return d


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
