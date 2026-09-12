"""Settings validation, memory bounds, and CLI input errors."""
import pytest

from framemill import cli
from framemill.settings import (
    MAX_SHEET_PIXELS,
    RenderSettings,
    framing_ortho_scale,
    framing_target,
)


def test_valid_defaults_pass():
    RenderSettings().validate()


def test_rejects_zero_and_negative_frames():
    with pytest.raises(ValueError, match="Frames"):
        RenderSettings(frames=0).validate()
    with pytest.raises(ValueError, match="Frames"):
        RenderSettings(frames=-3).validate()


def test_rejects_inverted_source_range():
    with pytest.raises(ValueError, match="Source start"):
        RenderSettings(anim_start_override=20, anim_end_override=4).validate()


def test_from_dict_skips_invalid_types():
    s, warnings = RenderSettings.from_dict_recovering(
        {"frames": "nope", "angles": 8, "loop_mode": "oneshot"})
    assert s.frames == 8
    assert s.loop_mode == "oneshot"
    assert any("frames" in w for w in warnings)


def test_from_dict_rejects_bool_and_nonfinite_in_strict_mode():
    with pytest.raises(ValueError, match="true/false"):
        RenderSettings.from_dict({"frames": True}, strict=True)
    with pytest.raises(ValueError, match="finite"):
        RenderSettings.from_dict({"framing_scale": float("nan")}, strict=True)


def test_from_dict_recovering_does_not_crash_on_invalid_persist():
    s, warnings = RenderSettings.from_dict_recovering(
        {"frames": True, "angles": 99, "ortho_scale_mult": float("inf")})
    assert s.frames == 8
    assert s.angles == 8
    assert warnings


def test_aggregate_sheet_memory_cap():
    s = RenderSettings(frame_width=1024, frame_height=1024, frames=64, angles=16)
    assert s.sheet_pixels() > MAX_SHEET_PIXELS
    with pytest.raises(ValueError, match="Sheet would be"):
        s.validate()


def test_individual_limits_are_not_enough_without_aggregate_cap():
    s = RenderSettings(frame_width=512, frame_height=512, frames=16, angles=8,
                       render_width=256, render_height=256)
    s.validate()  # 33.5 Mpx sheet, under the aggregate cap
    s.frames = 48
    with pytest.raises(ValueError, match="pixels"):
        s.validate()


def test_fixed_framing_ignores_clip_height():
    s = RenderSettings(framing_mode="fixed", framing_scale=3.5, ortho_scale_mult=1.8)
    assert framing_ortho_scale(s, 10) == 3.5
    fit = RenderSettings(framing_mode="fit", ortho_scale_mult=2)
    assert framing_ortho_scale(fit, 4) == 8


def test_feet_anchor_frames_full_body_with_feet_low():
    # Feet anchor sits the feet near the bottom of the framed window with the
    # whole body above, not centred on the feet (which would clip the head).
    from framemill.settings import framing_ortho_scale
    s = RenderSettings(anchor="feet")
    center, size = (0, 0, 2), (1, 1, 4)
    scale = framing_ortho_scale(s, size[2])
    aim = framing_target(center, size, s)
    feet_z = center[2] - size[2] / 2.0
    head_z = center[2] + size[2] / 2.0
    window_bottom = aim[2] - scale / 2.0
    window_top = aim[2] + scale / 2.0
    assert window_bottom < feet_z            # a little ground below the feet
    assert feet_z - window_bottom < scale * 0.1
    assert window_top > head_z               # head stays inside the frame
    assert framing_target(center, size, RenderSettings(anchor="center")) == (0, 0, 2)


def test_fixed_framing_uses_explicit_origin_not_clip_bounds():
    s = RenderSettings(framing_mode="fixed", framing_origin_x=0, framing_origin_y=0,
                       framing_origin_z=0, anchor="feet")
    assert framing_target((4, -3, 2), (8, 6, 4), s) == (0, 0, 0)
    s.framing_origin_x, s.framing_origin_y, s.framing_origin_z = 1, 2, 3
    assert framing_target((99, 99, 99), (1, 1, 10), s) == (1, 2, 3)


def test_cli_rejects_invalid_frames_and_formats(capsys):
    with pytest.raises(SystemExit) as exited:
        cli.main(["render", "walk.fbx", "-o", "out", "--frames", "0"])
    assert exited.value.code not in (0, None)
    with pytest.raises(SystemExit):
        cli.main(["render", "walk.fbx", "-o", "out", "--format", "gif"])


def test_parse_formats_lists_supported_only():
    assert cli._parse_formats("png,tga") == ["png", "tga"]
    with pytest.raises(ValueError, match="gif"):
        cli._parse_formats("png,gif")
    with pytest.raises(ValueError, match="at least one"):
        cli._parse_formats(" , ")
