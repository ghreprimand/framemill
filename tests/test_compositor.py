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


def test_layout_axis_cols(tmp_path: Path) -> None:
    s = RenderSettings(angles=8, frames=4, layout_axis="cols")
    _fake_frames(tmp_path, s)
    sheet = build_sheet(tmp_path, s)
    # cols => directions across (8), frames down (4)
    assert sheet.size == (96 * 8, 128 * 4)


def test_start_direction_reorders_rows(tmp_path: Path) -> None:
    from framemill.settings import build_layout
    from PIL import Image
    s = RenderSettings(angles=8, frames=1, start_direction="N", rotation="cw",
                       frame_width=4, frame_height=4, render_width=4, render_height=4)
    # Tag each direction's frame with a unique red value so we can identify rows.
    names = [n for n, _ in build_layout(8, "S", "cw")]  # canonical set
    for i, d in enumerate(build_layout(8, "N", "cw")):
        name = d[0]
        Image.new("RGBA", (4, 4), (i * 10, 0, 0, 255)).save(tmp_path / f"{name}_00.png")
    sheet = build_sheet(tmp_path, s)
    # Row 0 must be 'N' (start), row 1 'NW' for cw
    assert [n for n, _ in build_layout(8, "N", "cw")][0] == "N"
    assert sheet.getpixel((0, 0))[0] == 0        # row0 tagged i=0
    assert sheet.getpixel((0, 4))[0] == 10       # row1 tagged i=1
