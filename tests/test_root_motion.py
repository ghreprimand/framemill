"""Root-motion helpers and settings (no Blender)."""
from framemill.root_motion import (
    fit_framing_size,
    recentered_target,
    xy_travel,
)
from framemill.settings import RenderSettings


def test_fit_framing_size_uses_max_frame_or_union():
    travelling = [
        ((0.0, 0.0, 0.0), (1.0, 1.0, 2.0)),
        ((4.0, 0.0, 0.0), (5.0, 1.0, 2.0)),
        ((8.0, 0.0, 0.0), (9.5, 1.0, 2.0)),
    ]
    assert fit_framing_size(travelling, True) == (1.5, 1.0, 2.0)
    assert fit_framing_size(travelling, False) == (9.5, 1.0, 2.0)
    assert fit_framing_size([], True) == (1.0, 1.0, 1.0)


def test_xy_travel_is_net_ground_distance():
    assert xy_travel([(0.0, 0.0, 1.0)]) == 0.0
    assert xy_travel([(0.0, 0.0, 1.0), (3.0, 4.0, 9.0)]) == 5.0


def test_recentered_target_keeps_shared_z():
    frame = (6.0, 2.0, 1.0)
    aimed = (0.0, 0.0, 4.0)
    assert recentered_target(frame, aimed, True) == (6.0, 2.0, 4.0)
    assert recentered_target(frame, aimed, False) == aimed


def test_remove_root_motion_roundtrips_in_settings():
    settings = RenderSettings(remove_root_motion=True)
    loaded = RenderSettings.from_dict(settings.to_dict())
    assert loaded.remove_root_motion is True
    assert settings.render_config()["remove_root_motion"] is True
    assert RenderSettings().remove_root_motion is False
