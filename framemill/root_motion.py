"""Pure helpers for root-motion compensation. No Blender imports."""
from __future__ import annotations

import math

Bounds = tuple[tuple[float, float, float], tuple[float, float, float]]


def size_from_bounds(lo: tuple[float, float, float], hi: tuple[float, float, float]) -> tuple[float, float, float]:
    return (hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2])


def center_from_bounds(lo: tuple[float, float, float], hi: tuple[float, float, float]) -> tuple[float, float, float]:
    return ((lo[0] + hi[0]) / 2.0, (lo[1] + hi[1]) / 2.0, (lo[2] + hi[2]) / 2.0)


def fit_framing_size(per_frame: list[Bounds], remove_root_motion: bool) -> tuple[float, float, float]:
    """Fit-mode size from per-frame lo/hi bounds.

    remove_root_motion True: max single-frame extent (the character, not the travel).
    False: union of every corner across frames (legacy whole-clip box).
    """
    if not per_frame:
        return (1.0, 1.0, 1.0)
    if remove_root_motion:
        sizes = [size_from_bounds(lo, hi) for lo, hi in per_frame]
        return (
            max(s[0] for s in sizes),
            max(s[1] for s in sizes),
            max(s[2] for s in sizes),
        )
    lo = tuple(min(b[0][i] for b in per_frame) for i in range(3))
    hi = tuple(max(b[1][i] for b in per_frame) for i in range(3))
    return size_from_bounds(lo, hi)


def union_center(per_frame: list[Bounds]) -> tuple[float, float, float]:
    if not per_frame:
        return (0.0, 0.0, 0.0)
    lo = tuple(min(b[0][i] for b in per_frame) for i in range(3))
    hi = tuple(max(b[1][i] for b in per_frame) for i in range(3))
    return center_from_bounds(lo, hi)


def recentered_target(
    frame_center: tuple[float, float, float],
    aimed: tuple[float, float, float],
    remove_root_motion: bool,
) -> tuple[float, float, float]:
    """XY from this frame when compensating; Z stays whatever camera_target chose."""
    if remove_root_motion:
        return (frame_center[0], frame_center[1], aimed[2])
    return aimed


def xy_travel(positions: list[tuple[float, float, float]]) -> float:
    """Net ground-plane travel of a root (or bounds center) over the clip."""
    if len(positions) < 2:
        return 0.0
    dx = positions[-1][0] - positions[0][0]
    dy = positions[-1][1] - positions[0][1]
    return math.hypot(dx, dy)
