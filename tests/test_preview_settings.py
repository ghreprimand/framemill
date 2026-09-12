"""Preview orientation must not rewrite export settings."""
from framemill.app import preview_settings
from framemill.settings import RenderSettings


def test_load_preview_faces_south_without_changing_north_first_sheet():
    source = RenderSettings(angles=16, frames=11, start_direction="N", rotation="ccw",
                            layout_axis="cols", phase_offset=.25)
    before = source.to_dict()
    view = preview_settings(source)
    assert view.direction_layout()[0] == ("S", 0)
    assert source.to_dict() == before
    assert view.frames == 11 and view.phase_offset == .25
    assert view.layout_axis == "cols" and view.rotation == "ccw"


def test_view_direction_is_independent_of_single_direction_export():
    source = RenderSettings(angles=1)
    view = preview_settings(source, "E")
    assert view.direction_layout()[0] == ("E", -90)
    assert source.angles == 1 and source.start_direction == "S"


def test_preview_keeps_source_yaw_loop_mode_and_framing():
    source = RenderSettings(source_yaw=90, loop_mode="oneshot", framing_mode="fixed",
                            framing_scale=3, anchor="feet", output_offset_x=4,
                            start_direction="N", remove_root_motion=True)
    view = preview_settings(source, "W")
    assert view.direction_layout()[0][0] == "W"
    assert view.source_yaw == 90 and source.source_yaw == 90
    assert view.loop_mode == "oneshot" and view.framing_mode == "fixed"
    assert view.anchor == "feet" and view.output_offset_x == 4
    assert view.remove_root_motion is True and source.remove_root_motion is True
    assert source.start_direction == "N"
