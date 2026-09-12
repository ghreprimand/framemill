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


def test_dilation_does_not_wrap_image_edges():
    im = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    im.putpixel((0, 4), (255, 0, 0, 255))
    out = export.dilate_edges(im, 1)
    assert out.getpixel((1, 4)) == (255, 0, 0, 0)
    assert out.getpixel((7, 4)) == (0, 0, 0, 0)


def test_ordered_dither_preserves_exact_colour_key():
    # Nearby palette colours would otherwise dither the magenta background.
    cfg = ExportConfig(depth=8, background="magic_pink", dither="ordered",
                       palette_source="fixed", fixed_palette=[(255, 0, 255), (240, 0, 240), (200, 30, 30)])
    source = _sprite()
    out = export.process(source, cfg).convert("RGB")
    for y in range(8):
        for x in range(8):
            if source.getpixel((x, y))[3] == 0:
                assert out.getpixel((x, y)) == (255, 0, 255)


def test_solid_background_is_opaque_and_blends_soft_edges():
    source = Image.new("RGBA", (2, 2), (255, 0, 0, 128))
    source.putpixel((0, 0), (0, 0, 0, 0))
    out = export.process(source, ExportConfig(background="solid", solid_color="#0000ff"))
    assert out.getpixel((0, 0)) == (0, 0, 255, 255)
    assert out.getpixel((1, 1)) == (128, 0, 127, 255)


def test_missing_custom_palette_is_not_silently_adaptive():
    import pytest
    with pytest.raises(ValueError, match="palette file"):
        export.process(_sprite(), ExportConfig(depth=8, background="magic_pink", palette_source="file"))


def _indexed_image(path: Path, colors: list[tuple[int, int, int]], size=(2, 2)) -> Path:
    image = Image.new("P", size)
    flat: list[int] = []
    for color in colors:
        flat.extend(color)
    flat += [0] * (768 - len(flat))
    image.putpalette(flat)
    image.putpixel((0, 0), 0)
    if len(colors) > 1:
        image.putpixel((1, 0), 1)
    image.save(path)
    return path


def test_load_palette_indexed_bmp_preserves_order(tmp_path: Path):
    master = [(255, 0, 255), (200, 30, 30), (0, 0, 0), (10, 20, 40)]
    path = _indexed_image(tmp_path / "BG_00.BMP", master)
    colors = export.load_palette(str(path))
    assert colors[0] == (255, 0, 255)
    assert colors[:4] == master


def test_load_palette_rejects_truecolor_image(tmp_path: Path):
    import pytest
    path = tmp_path / "photo.png"
    Image.new("RGB", (2, 2), (10, 20, 30)).save(path)
    with pytest.raises(ValueError, match="no fixed palette"):
        export.load_palette(str(path))


def test_eight_bit_master_palette_keeps_order_and_maps_key(tmp_path: Path):
    master = [(255, 0, 255), (200, 30, 30), (0, 0, 0), (10, 20, 40)]
    path = _indexed_image(tmp_path / "scene.bmp", master)
    cfg = ExportConfig(depth=8, background="magic_pink", dither="none",
                       palette_source="file", palette_path=str(path))
    source = _sprite()
    out = export.process(source, cfg)
    assert out.mode == "P"
    palette = out.getpalette() or []
    got = [tuple(palette[i:i + 3]) for i in range(0, len(master) * 3, 3)]
    assert got == master
    for y in range(8):
        for x in range(8):
            if source.getpixel((x, y))[3] == 0:
                assert out.getpixel((x, y)) == 0
    assert out.getpixel((3, 3)) == 1


def test_supplied_palette_missing_key_is_an_error(tmp_path: Path):
    import pytest
    path = _indexed_image(tmp_path / "no_pink.bmp", [(0, 0, 0), (200, 30, 30)])
    with pytest.raises(ValueError, match="not in this master palette"):
        export.process(_sprite(), ExportConfig(
            depth=8, background="magic_pink", palette_source="file", palette_path=str(path)))
    with pytest.raises(ValueError, match="not in this master palette"):
        export.process(_sprite(), ExportConfig(
            depth=8, background="magic_pink", palette_source="fixed",
            fixed_palette=[(0, 0, 0), (200, 30, 30)]))


def test_adaptive_palette_prepends_missing_key_at_index_zero():
    rgb = Image.new("RGB", (4, 4), (200, 30, 30))
    cfg = ExportConfig(depth=8, palette_source="auto", palette_colors=8)
    colors = export._resolve_palette(rgb, cfg, (255, 0, 255))
    assert colors[0] == (255, 0, 255)
    out = export.process(_sprite(), ExportConfig(
        depth=8, background="magic_pink", palette_source="auto", palette_colors=8, dither="none"))
    palette = out.getpalette() or []
    key_index = next(i for i in range(256) if tuple(palette[i * 3:i * 3 + 3]) == (255, 0, 255))
    assert out.getpixel((0, 0)) == key_index


def test_parse_hex_colours_accepts_spaces_and_commas():
    assert export.parse_hex_colours("") == []
    assert export.parse_hex_colours("  #ff00ff, #c81e1e  #00f") == [
        (255, 0, 255), (200, 30, 30), (0, 0, 255)]


def test_reorder_palette_matches_flutter_index_shift():
    colors = [(255, 0, 255), (200, 30, 30), (0, 0, 0)]
    assert export.reorder_palette(colors, 0, 2) == [(200, 30, 30), (255, 0, 255), (0, 0, 0)]
    assert export.reorder_palette(colors, 2, 0) == [(0, 0, 0), (255, 0, 255), (200, 30, 30)]
    assert export.rgb_to_hex((255, 0, 255)) == "#ff00ff"


def test_unknown_palette_suffix_is_rejected():
    import pytest
    with pytest.raises(ValueError, match="Palette file must"):
        export.validate_config(ExportConfig(
            depth=8, background="magic_pink", palette_source="file", palette_path="scene.xyz"))


def test_unsupported_transparency_combination_is_explicit():
    import pytest
    with pytest.raises(ValueError, match="32-bit PNG or TGA"):
        export.process(_sprite(), ExportConfig(format="bmp", depth=8, background="transparent"))


def test_valid_backgrounds_match_format_depth():
    assert export.valid_backgrounds("png", 32) == ["transparent", "solid"]
    assert export.valid_backgrounds("tga", 32) == ["transparent", "solid", "magic_pink"]
    assert export.valid_backgrounds("png", 24) == ["magic_pink", "solid"]
    assert export.valid_backgrounds("png", 8) == ["magic_pink", "solid"]
    assert export.valid_backgrounds("bmp", 32) == ["magic_pink", "solid"]
    assert export.valid_backgrounds("bmp", 24) == ["magic_pink", "solid"]
    assert "magic_pink" not in export.valid_backgrounds("png", 32)
    assert "transparent" not in export.valid_backgrounds("tga", 24)


def test_format_depth_switch_never_leaves_invalid_background():
    cfg = ExportConfig(format="tga", depth=32, background="magic_pink", alpha_mode="hard")
    cfg.format = "png"
    export.apply_export_capabilities(cfg, capability_changed=True)
    assert cfg.background in export.valid_backgrounds(cfg.format, cfg.depth)
    assert cfg.background == "transparent"

    cfg.format = "bmp"
    cfg.depth = 32
    export.apply_export_capabilities(cfg, capability_changed=True)
    assert cfg.format == "bmp"
    assert cfg.depth == 24
    assert cfg.background == "magic_pink"
    assert cfg.alpha_mode == "hard"

    cfg.background = "solid"
    cfg.alpha_mode = "soft"
    export.apply_export_capabilities(cfg, capability_changed=False)
    assert cfg.background == "solid"
    assert cfg.alpha_mode == "soft"

    cfg.format = "tga"
    cfg.depth = 32
    cfg.background = "magic_pink"
    export.apply_export_capabilities(cfg, capability_changed=True)
    assert cfg.background == "magic_pink"

    import pytest
    with pytest.raises(ValueError, match="background that matches"):
        export.validate_config(ExportConfig(format="png", depth=32, background="magic_pink"))
