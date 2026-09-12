"""Atomic and all-or-nothing output writes, without Blender."""
from pathlib import Path

import pytest
from PIL import Image

from framemill import atomicio, cli, recipe


def _leftover_temps(folder: Path) -> list[Path]:
    return [path for path in folder.iterdir() if path.suffix == ".tmp" or (
        path.name.startswith(".") and path.name != folder.name)]


def test_atomic_write_bytes_success_leaves_no_temp(tmp_path: Path):
    dest = tmp_path / "out.png"
    assert atomicio.atomic_write_bytes(dest, b"hello") == dest
    assert dest.read_bytes() == b"hello"
    assert _leftover_temps(tmp_path) == []


def test_atomic_write_bytes_failure_does_not_clobber(tmp_path: Path, monkeypatch):
    dest = tmp_path / "out.png"
    dest.write_bytes(b"KEEP")

    def boom(_dest, _data):
        raise OSError("disk full")

    monkeypatch.setattr(atomicio, "_stage_file", boom)
    with pytest.raises(OSError, match="disk full"):
        atomicio.atomic_write_bytes(dest, b"NEW")
    assert dest.read_bytes() == b"KEEP"
    assert _leftover_temps(tmp_path) == []


def test_write_all_success_png_tga_and_sidecars(tmp_path: Path):
    sheet = Image.new("RGBA", (4, 4), (10, 20, 30, 255))
    written = cli._write_render_outputs(
        sheet, tmp_path / "hero", ["png", "tga"], False,
        metadata_payload={"version": 1, "clip": "walk"},
    )
    assert [path.name for path in written] == [
        "hero.png", "hero.json", "hero.tga", "hero.json",
    ]
    png = tmp_path / "hero.png"
    tga = tmp_path / "hero.tga"
    side = tmp_path / "hero.json"
    assert png.is_file() and png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert tga.is_file() and tga.stat().st_size > 18
    assert recipe.sidecar_path(png) == side
    assert recipe.sidecar_path(tga) == side
    assert recipe.encode_metadata({"version": 1, "clip": "walk"}) == side.read_bytes()
    assert _leftover_temps(tmp_path) == []


def test_write_all_failure_promotes_nothing(tmp_path: Path, monkeypatch):
    png = tmp_path / "hero.png"
    tga = tmp_path / "hero.tga"
    png.write_bytes(b"OLD-PNG")
    tga.write_bytes(b"OLD-TGA")
    real = atomicio._stage_file
    seen = {"n": 0}

    def fail_later(dest, data):
        seen["n"] += 1
        if seen["n"] >= 2:
            raise OSError("disk full")
        return real(dest, data)

    monkeypatch.setattr(atomicio, "_stage_file", fail_later)
    sheet = Image.new("RGBA", (4, 4), (1, 2, 3, 255))
    with pytest.raises(OSError, match="disk full"):
        cli._write_render_outputs(
            sheet, tmp_path / "hero", ["png", "tga"], False,
            metadata_payload={"version": 1},
        )
    assert png.read_bytes() == b"OLD-PNG"
    assert tga.read_bytes() == b"OLD-TGA"
    assert not (tmp_path / "hero.json").exists()
    assert _leftover_temps(tmp_path) == []
