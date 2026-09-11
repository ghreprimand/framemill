"""Direction ordering follows character facings on a compass, not camera orbit."""
import pytest

from framemill.settings import build_layout, direction_names


@pytest.mark.parametrize("count,clockwise", [
    (4, ["N", "E", "S", "W"]),
    (8, ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]),
    (16, ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
          "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]),
])
def test_every_start_direction_in_both_rotations(count, clockwise):
    for rotation, ring in (("cw", clockwise), ("ccw", clockwise[:1] + clockwise[1:][::-1])):
        for i, start in enumerate(ring):
            assert [name for name, _ in build_layout(count, start, rotation)] == ring[i:] + ring[:i]


def test_direction_order_preserves_camera_mapping():
    expected = {"S": 0, "SE": -45, "E": -90, "NE": -135,
                "N": -180, "NW": -225, "W": -270, "SW": -315}
    for rotation in ("cw", "ccw"):
        for start in expected:
            assert dict(build_layout(8, start, rotation)) == expected


def test_direction_names_matches_default_layout():
    assert direction_names(8) == ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]
