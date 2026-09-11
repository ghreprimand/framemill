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
