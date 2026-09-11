"""Render settings, direction layouts, and built-in presets.

Everything here is engine-agnostic and JSON-serialisable so it can be handed
to the Blender-side render script unchanged. No project- or machine-specific
values live here.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import List

# Clockwise-from-South ordering. This is the most common convention for
# top-down / isometric games; change `direction_names` if your engine differs.
DIRECTIONS_8 = ["S", "SE", "E", "NE", "N", "NW", "W", "SW"]
DIRECTIONS_16 = [
    "S", "SSE", "SE", "ESE", "E", "ENE", "NE", "NNE",
    "N", "NNW", "NW", "WNW", "W", "WSW", "SW", "SSW",
]
DIRECTIONS_4 = ["S", "E", "N", "W"]


def direction_names(angles: int) -> List[str]:
    if angles == 4:
        return list(DIRECTIONS_4)
    if angles == 8:
        return list(DIRECTIONS_8)
    if angles == 16:
        return list(DIRECTIONS_16)
    if angles == 1:
        return ["S"]
    return [f"angle{i}" for i in range(angles)]


@dataclass
class RenderSettings:
    """One complete, reproducible sprite-render configuration."""

    # --- Output geometry ---
    angles: int = 8                 # camera directions around the model
    frames: int = 4                 # animation frames per direction
    frame_width: int = 96
    frame_height: int = 128

    # --- Supersampling (render big, downscale with Lanczos for crisp edges) ---
    render_width: int = 1920
    render_height: int = 1080

    # --- Camera ---
    ortho_scale_mult: float = 1.8   # * model height; adds animation headroom
    camera_distance: float = 2.52
    camera_pitch: float = 90.0      # 90 = level; lower = more top-down

    # --- Lighting (point light following the camera) ---
    light_energy: float = 1000.0
    light_color: str = "#FFFFFF"
    shadow_soft_size: float = 0.1

    # --- Ambient / world ---
    ambient_color: str = "#FFFFFF"
    ambient_strength: float = 1.0

    # --- Colour management ---
    view_transform: str = "Standard"   # "Standard" | "AgX" | "Filmic"
    look: str = "None"
    exposure: float = 0.0
    gamma: float = 1.0

    # --- Material tweak ---
    specular_ior: float = 0.5       # 1.0 brightens textured PBR materials

    # --- Render engine ---
    engine: str = "BLENDER_EEVEE"
    samples: int = 64

    # --- Animation ---
    anim_start_override: int | None = None
    anim_end_override: int | None = None
    idle_frame_index: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "RenderSettings":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class Preset:
    key: str
    label: str
    description: str
    settings: RenderSettings


# Neutral, works-anywhere defaults.
_GENERIC = RenderSettings()

# Tuned for models exported from Tripo (fresh imports render dark without a
# lifted ambient and the AgX high-contrast look).
_TRIPO = RenderSettings(
    view_transform="AgX",
    look="AgX - High Contrast",
    ambient_color="#E7D38D",
    ambient_strength=4.8,
    specular_ior=1.0,
)

# Mixamo rigs usually carry sensible materials; keep colour management neutral
# but lift ambient a touch so the front face reads clearly.
_MIXAMO = RenderSettings(
    view_transform="Standard",
    ambient_color="#FFFFFF",
    ambient_strength=1.5,
    specular_ior=0.5,
)

PRESETS: dict[str, Preset] = {
    "generic": Preset("generic", "Generic PBR", "Neutral colour + lighting. Safe starting point for any model.", _GENERIC),
    "tripo": Preset("tripo", "Tripo", "Warm ambient + AgX high contrast, tuned for Tripo-generated meshes.", _TRIPO),
    "mixamo": Preset("mixamo", "Mixamo", "Neutral colour with a gentle ambient lift for Mixamo-rigged FBX.", _MIXAMO),
}

DEFAULT_PRESET = "generic"
