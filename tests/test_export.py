"""Tests for the export engine (no Blender needed)."""
from pathlib import Path

import numpy as np
from PIL import Image

from framemill import export
from framemill.export import ExportConfig


def _sprite() -> Image.Image:
    """8x8 with an opaque red center block, transparent border."""
    im = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    for y in range(3, 5):
        for x in range(3, 5):
            im.putpixel((x, y), (200, 30, 30, 255))
    return im


def test_dilate_fills_border_without_touching_alpha():
    im = _sprite()
    out = export.dilate_edges(im, 1)
    arr = np.array(out)
    # A pixel adjacent to the block was transparent; alpha stays 0 but RGB bled.
    assert arr[3, 2, 3] == 0            # still transparent
    assert tuple(arr[3, 2, :3]) != (0, 0, 0)   # colour bled in


def test_threshold_alpha_is_binary():
    im = Image.new("RGBA", (4, 4), (10, 10, 10, 100))
    out = np.array(export.threshold_alpha(im, 128))
    assert set(np.unique(out[:, :, 3])) == {0}
    out2 = np.array(export.threshold_alpha(im, 64))
    assert set(np.unique(out2[:, :, 3])) == {255}


def test_depth24_flatten_magenta():
    cfg = ExportConfig(depth=24, background="magic_pink")
    out = export.process(_sprite(), cfg)
    assert out.mode == "RGB"
    assert out.getpixel((0, 0)) == (255, 0, 255)


def test_depth8_indexed_within_palette():
    cfg = ExportConfig(depth=8, background="magic_pink", palette_colors=16, dither="none")
    out = export.process(_sprite(), cfg)
    assert out.mode == "P"


def test_ordered_and_floyd_produce_indexed():
    for d in ("ordered", "floyd", "none"):
        cfg = ExportConfig(depth=8, background="solid", solid_color="#101010",
                           palette_colors=32, dither=d)
        assert export.process(_sprite(), cfg).mode == "P"


def test_save_all_formats(tmp_path: Path):
    combos = [
        ExportConfig(format="png", depth=32, background="transparent", dilate=1),
        ExportConfig(format="tga", depth=32, background="magic_pink", alpha_mode="hard"),
        ExportConfig(format="tga", depth=24, background="solid", solid_color="#204080"),
        ExportConfig(format="bmp", depth=24, background="magic_pink"),
        ExportConfig(format="bmp", depth=8, background="magic_pink", dither="ordered"),
    ]
    for i, cfg in enumerate(combos):
        p = export.save(_sprite(), tmp_path / f"out{i}", cfg)
        assert p.exists() and p.stat().st_size > 0
        Image.open(p).load()  # re-readable


def test_load_palette_gpl(tmp_path: Path):
    gpl = tmp_path / "p.gpl"
    gpl.write_text("GIMP Palette\nName: test\n#\n255 0 0 red\n0 255 0 green\n0 0 255\n")
    colors = export.load_palette(str(gpl))
    assert (255, 0, 0) in colors and (0, 0, 255) in colors


def test_load_palette_jasc(tmp_path: Path):
    pal = tmp_path / "p.pal"
    pal.write_text("JASC-PAL\n0100\n2\n255 255 0\n0 0 0\n")
    colors = export.load_palette(str(pal))
    assert (255, 255, 0) in colors


def test_load_palette_hex(tmp_path: Path):
    hexf = tmp_path / "p.hex"
    hexf.write_text("#ff0000\n#00ff00\n#0000ff\n")
    colors = export.load_palette(str(hexf))
    assert colors == [(255, 0, 0), (0, 255, 0), (0, 0, 255)]


def test_presets_all_save(tmp_path: Path):
    for key, preset in export.EXPORT_PRESETS.items():
        p = export.save(_sprite(), tmp_path / key, preset.config)
        assert p.exists()
