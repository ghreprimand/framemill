"""Blender-free tests for the compositor (crop/resize/tile + TGA header)."""
from pathlib import Path

import pytest
from PIL import Image

from framemill.compositor import build_sheet, encode_tga
from framemill.settings import RenderSettings, direction_names


def _fake_frames(tmp: Path, settings: RenderSettings) -> None:
    for row, d in enumerate(direction_names(settings.angles)):
        for col in range(settings.frames):
            # Render-sized frame; compositor must crop+downscale it.
            img = Image.new("RGBA", (settings.render_width, settings.render_height),
                            (row * 20 % 256, col * 40 % 256, 128, 255))
            img.save(tmp / f"{d}_{col:02d}.png")


def test_sheet_dimensions(tmp_path: Path) -> None:
    s = RenderSettings(angles=8, frames=4, frame_width=96, frame_height=128)
    _fake_frames(tmp_path, s)
    sheet = build_sheet(tmp_path, s)
    assert sheet.size == (96 * 4, 128 * 8)


def test_missing_frame_reports_incomplete_render(tmp_path: Path) -> None:
    s = RenderSettings(angles=4, frames=4)
    _fake_frames(tmp_path, s)
    (tmp_path / "S_00.png").unlink()  # drop one frame
    with pytest.raises(FileNotFoundError, match="S_00.png"):
        build_sheet(tmp_path, s)


def test_tga_header_bottom_origin(tmp_path: Path) -> None:
    s = RenderSettings(angles=1, frames=1, frame_width=8, frame_height=8)
    _fake_frames(tmp_path, s)
    data = encode_tga(build_sheet(tmp_path, s))
    assert data[2] == 2          # uncompressed truecolour
    assert data[16] == 32        # 32 bpp
    assert data[17] == 0x08      # bottom-left origin, 8 alpha bits


def test_tga_magic_pink(tmp_path: Path) -> None:
    sheet = Image.new("RGBA", (4, 4), (0, 0, 0, 0))  # fully transparent
    data = encode_tga(sheet, magic_pink=True)
    body = data[18:]
    # first pixel BGRA -> magenta with alpha 0
    assert body[0:4] == bytes((255, 0, 255, 0))


def test_layout_axis_cols(tmp_path: Path) -> None:
    s = RenderSettings(angles=8, frames=4, layout_axis="cols")
    _fake_frames(tmp_path, s)
    sheet = build_sheet(tmp_path, s)
    # cols => directions across (8), frames down (4)
    assert sheet.size == (96 * 8, 128 * 4)


@pytest.mark.parametrize("axis", ["rows", "cols"])
def test_north_clockwise_sheet_uses_compass_order(tmp_path: Path, axis: str) -> None:
    s = RenderSettings(angles=8, frames=1, start_direction="N", rotation="cw",
                       layout_axis=axis, frame_width=4, frame_height=4)
    expected = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    # Tag files independently of the layout implementation.
    for i, name in enumerate(expected):
        Image.new("RGBA", (4, 4), (i * 20, 0, 0, 255)).save(tmp_path / f"{name}_00.png")
    sheet = build_sheet(tmp_path, s)
    for i in range(8):
        xy = (0, i * 4) if axis == "rows" else (i * 4, 0)
        assert sheet.getpixel(xy)[0] == i * 20


@pytest.mark.parametrize("angles,start", [(8, "S"), (8, "N"), (4, "E"), (1, "S")])
def test_preview_reads_actual_first_direction(tmp_path, angles, start):
    from framemill.compositor import build_preview
    s = RenderSettings(angles=angles, start_direction=start, frame_width=8, frame_height=8)
    name = s.direction_layout()[0][0]
    Image.new("RGBA", (16, 16), (240, 80, 20, 255)).save(tmp_path / f"{name}_00.png")
    preview = build_preview(tmp_path, s)
    assert preview.size == (8, 8)
    assert preview.getpixel((4, 4)) == (240, 80, 20, 255)
