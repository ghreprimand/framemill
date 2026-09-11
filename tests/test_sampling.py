"""Loop / one-shot sampling and playback, independent of Blender."""
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from framemill.settings import (
    RenderSettings,
    next_playback_frame,
    sample_source_times,
)


def _blender_sample(fi, frames, start, end, loop_mode="loop", phase=0.0, reverse=False):
    path = Path(__file__).parents[1] / "framemill/blender/render_sprites.py"
    bpy = SimpleNamespace()
    mathutils = SimpleNamespace()
    sys.modules.setdefault("bpy", bpy)
    sys.modules.setdefault("mathutils", mathutils)
    spec = importlib.util.spec_from_file_location("render_sample_fn", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.sample_source_time(fi, frames, start, end, loop_mode, phase, reverse)


def test_loop_excludes_endpoint_and_matches_historical_samples():
    assert sample_source_times(0, 10, 4) == [0, 2.5, 5, 7.5]


def test_oneshot_includes_both_endpoints():
    assert sample_source_times(0, 10, 4, loop_mode="oneshot") == pytest.approx(
        [0, 10 / 3, 20 / 3, 10])


def test_oneshot_reverse_does_not_wrap():
    assert sample_source_times(0, 10, 4, loop_mode="oneshot", reverse=True) == pytest.approx(
        [10, 20 / 3, 10 / 3, 0])


def test_loop_reverse_still_wraps():
    times = sample_source_times(0, 10, 4, reverse=True)
    assert times[0] == 0
    assert times == [0, 7.5, 5, 2.5]


def test_oneshot_ignores_phase():
    assert sample_source_times(0, 10, 4, loop_mode="oneshot", phase_offset=.25) == (
        sample_source_times(0, 10, 4, loop_mode="oneshot")
    )


def test_one_frame_loop_uses_phase():
    assert sample_source_times(0, 10, 1, phase_offset=.25) == [2.5]


def test_one_frame_oneshot_is_start_or_end():
    assert sample_source_times(0, 10, 1, loop_mode="oneshot") == [0]
    assert sample_source_times(0, 10, 1, loop_mode="oneshot", reverse=True) == [10]


def test_zero_length_clip_repeats_start():
    assert sample_source_times(7, 7, 4, loop_mode="oneshot") == [7, 7, 7, 7]


def test_settings_oneshot_drops_phase():
    s = RenderSettings(frames=3, loop_mode="oneshot", phase_offset=.9)
    assert s.sample_times(1, 11) == [1, 6, 11]


@pytest.mark.parametrize("phase,reverse,mode", [
    (0, False, "loop"), (.25, True, "loop"), (0.4, False, "oneshot"), (0, True, "oneshot"),
])
def test_blender_sampler_matches_host(phase, reverse, mode):
    start, end, frames = 1, 21, 5
    host = sample_source_times(start, end, frames, loop_mode=mode,
                               phase_offset=phase, reverse=reverse)
    for i, expected in enumerate(host):
        assert _blender_sample(i, frames, start, end, mode, phase, reverse) == expected


def test_oneshot_playback_stops_at_end():
    assert next_playback_frame(0, 4, "oneshot") == 1
    assert next_playback_frame(2, 4, "oneshot") == 3
    assert next_playback_frame(3, 4, "oneshot") is None
    assert next_playback_frame(0, 1, "oneshot") is None


def test_loop_playback_wraps():
    assert next_playback_frame(3, 4, "loop") == 0
    assert next_playback_frame(0, 1, "loop") == 0
