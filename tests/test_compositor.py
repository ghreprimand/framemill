"""Blender-free tests for the compositor (crop/resize/tile + TGA header)."""
from pathlib import Path

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


def test_missing_frame_is_transparent(tmp_path: Path) -> None:
    s = RenderSettings(angles=4, frames=4)
    _fake_frames(tmp_path, s)
    (tmp_path / "S_00.png").unlink()  # drop one frame
    sheet = build_sheet(tmp_path, s)
    assert sheet.getpixel((0, 0))[3] == 0  # top-left frame slot stays transparent


def test_tga_header_bottom_origin(tmp_path: Path) -> None:
    s = RenderSettings(angles=1, frames=1, frame_width=8, frame_height=8)
    _fake_frames(tmp_path, s)
    data = encode_tga(build_sheet(tmp_path, s))
    assert data[2] == 2          # uncompressed truecolour
    assert data[16] == 32        # 32 bpp
    assert data[17] == 0x08      # bottom-left origin, 8 alpha bits


def test_tga_magic_pink(tmp_path: Path) -> None:
    s = RenderSettings(angles=1, frames=1, frame_width=4, frame_height=4)
    sheet = Image.new("RGBA", (4, 4), (0, 0, 0, 0))  # fully transparent
    data = encode_tga(sheet, magic_pink=True)
    body = data[18:]
    # first pixel BGRA -> magenta with alpha 0
    assert body[0:4] == bytes((255, 0, 255, 0))
