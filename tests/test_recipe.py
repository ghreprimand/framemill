"""Portable recipes and animation metadata sidecars."""
import json
from pathlib import Path

import pytest

from framemill.export import ExportConfig
from framemill.recipe import (
    RECIPE_VERSION,
    animation_metadata,
    build_recipe,
    load_recipe,
    save_recipe,
    sidecar_path,
    write_metadata,
)
from framemill.settings import RenderSettings


def test_recipe_roundtrip_uses_relative_source(tmp_path: Path):
    source = tmp_path / "hero" / "walk.fbx"
    source.parent.mkdir()
    source.write_text("x")
    pal = tmp_path / "hero" / "game.gpl"
    pal.write_text("GIMP Palette\n0 0 0\n")
    dest = tmp_path / "hero" / "walk.recipe.json"
    settings = RenderSettings(frames=11, loop_mode="oneshot", source_yaw=90,
                              framing_mode="fixed", framing_scale=2.4, anchor="feet")
    export = ExportConfig(format="tga", write_metadata=True, depth=32,
                          background="magic_pink", palette_source="file",
                          palette_path=str(pal))
    save_recipe(dest, build_recipe(str(source), settings, export))
    payload = json.loads(dest.read_text())
    assert payload["version"] == RECIPE_VERSION
    assert payload["source"] == "walk.fbx"
    assert payload["export"]["palette_path"] == "game.gpl"
    loaded = load_recipe(dest)
    assert loaded.source == str(source.resolve())
    assert loaded.settings.loop_mode == "oneshot"
    assert loaded.settings.source_yaw == 90
    assert loaded.settings.framing_scale == 2.4
    assert loaded.export.write_metadata is True
    assert loaded.export.palette_path == str(pal.resolve())


def test_load_recipe_rejects_bad_version_and_missing_source(tmp_path: Path):
    dest = tmp_path / "bad.json"
    dest.write_text(json.dumps({"version": 99, "source": "a.fbx", "settings": {}}))
    with pytest.raises(ValueError, match="version"):
        load_recipe(dest)
    dest.write_text(json.dumps({"version": 1, "settings": {}}))
    with pytest.raises(ValueError, match="source"):
        load_recipe(dest)
    dest.write_text("{")
    with pytest.raises(ValueError, match="JSON"):
        load_recipe(dest)


def test_load_recipe_rejects_malformed_values(tmp_path: Path):
    dest = tmp_path / "bad-types.json"
    dest.write_text(json.dumps({
        "version": 1, "source": "a.fbx",
        "settings": {"frames": True},
    }))
    with pytest.raises(ValueError, match="invalid"):
        load_recipe(dest)
    dest.write_text(json.dumps({
        "version": 1, "source": "a.fbx",
        "settings": {"frames": 4},
        "export": {"format": "gif"},
    }))
    with pytest.raises(ValueError, match="format"):
        load_recipe(dest)


def test_load_recipe_rejects_invalid_settings(tmp_path: Path):
    dest = tmp_path / "huge.json"
    dest.write_text(json.dumps({
        "version": 1, "source": "a.fbx",
        "settings": {"frame_width": 1024, "frame_height": 1024, "frames": 64, "angles": 16},
    }))
    with pytest.raises(ValueError, match="invalid"):
        load_recipe(dest)


def test_metadata_distinguishes_playback_and_source_timing():
    settings = RenderSettings(frames=4, loop_mode="oneshot", start_direction="N",
                              rotation="cw", layout_axis="cols", source_yaw=-90,
                              output_offset_x=2, anchor="feet")
    meta = animation_metadata(
        settings, clip_name="slash", source_start=0, source_end=10,
        source_fps=24, playback_fps=8,
    )
    assert meta["timing"]["looping"] is False
    assert meta["timing"]["playback_fps"] == 8
    assert meta["timing"]["source_fps"] == 24
    assert meta["timing"]["sample_times"][0] == 0
    assert meta["timing"]["sample_times"][-1] == 10
    assert meta["layout"]["directions"][0]["name"] == "N"
    assert meta["orientation"]["source_yaw"] == -90
    assert meta["pivot"]["anchor"] == "feet"
    assert meta["replacement"]["enabled"] is False
    assert meta["replacement"]["adds_slot"] is False
    assert "/home/" not in json.dumps(meta)


def test_metadata_records_replacement_slot_without_absolute_paths():
    settings = RenderSettings(frames=11)
    meta = animation_metadata(
        settings, clip_name="/secret/models/slash.fbx",
        source_start=1, source_end=21, source_fps=24, playback_fps=8,
        replacement_used=True, replacement_name="/secret/models/idle.fbx",
    )
    assert meta["clip"] == "slash"
    assert meta["replacement"]["enabled"] is True
    assert meta["replacement"]["slot_index"] == 0
    assert meta["replacement"]["replaces_existing_sample"] is True
    assert meta["replacement"]["name"] == "idle.fbx"
    dumped = json.dumps(meta)
    assert "/secret/" not in dumped
    assert meta["timing"]["sample_times"][0] == 1


def test_write_metadata_sidecar_name(tmp_path: Path):
    image = tmp_path / "hero_walk.png"
    image.write_bytes(b"x")
    dest = write_metadata(image, {"version": 1})
    assert dest == sidecar_path(image)
    assert dest.name == "hero_walk.json"
    assert json.loads(dest.read_text())["version"] == 1
