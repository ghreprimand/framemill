"""Cross-feature regressions discovered during director review."""
import json

import pytest
from PIL import Image

from framemill import cli, compositor, export, recipe
from framemill.settings import RenderSettings


def test_offset_preserves_partial_alpha_and_hidden_rgb():
    sprite = Image.new("RGBA", (3, 3), (0, 0, 0, 0))
    sprite.putpixel((0, 0), (200, 90, 30, 128))
    sprite.putpixel((0, 1), (20, 40, 60, 0))
    shifted = compositor.apply_output_offset(sprite, 1, 0)
    assert shifted.getpixel((1, 0)) == (200, 90, 30, 128)
    assert shifted.getpixel((1, 1)) == (20, 40, 60, 0)


@pytest.mark.parametrize("changes", [
    {"frames": True}, {"frames": 2.5}, {"source_yaw": float("nan")},
    {"gamma": 0}, {"anim_start_override": 0, "anim_end_override": 10001},
])
def test_invalid_direct_settings_rejected(changes):
    with pytest.raises(ValueError):
        RenderSettings(**changes).validate()


def test_normal_longer_animation_is_not_counted_as_simultaneous_buffers():
    RenderSettings(angles=16, frames=64).validate()


def test_cli_frame_limit_is_not_silently_reset():
    with pytest.raises(SystemExit, match="Frames"):
        cli.main(["render", "unused.fbx", "-o", "unused", "--frames", "65"])


@pytest.mark.parametrize("changes", [
    {"frames": 2.5}, {"frames": True}, {"source_yaw": float("inf")},
])
def test_recipe_does_not_silently_change_invalid_settings(tmp_path, changes):
    path = tmp_path / "bad.recipe.json"
    payload = recipe.recipe_to_dict(
        recipe.Recipe("hero.glb", RenderSettings(), export.ExportConfig()), path)
    payload["settings"].update(changes)
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError):
        recipe.load_recipe(path)


@pytest.mark.parametrize("changes", [
    {"dilate": 100000}, {"dilate": True}, {"fixed_palette": [[0, 1, 999]]},
    {"palette_path": 34}, {"alpha_cutoff": 1.5},
])
def test_invalid_export_config_rejected_without_pixels(changes):
    with pytest.raises(ValueError):
        export.validate_config(export.ExportConfig(**changes))


def test_non_object_saved_preferences_do_not_crash_startup(tmp_path, monkeypatch):
    from framemill import appconfig
    config = tmp_path / "config.json"
    config.write_text("[]")
    monkeypatch.setattr(appconfig, "CONFIG_PATH", config)
    assert appconfig.load() == {}


def test_recipe_paths_are_relative_across_sibling_directories(tmp_path):
    path = tmp_path / "recipes/hero.recipe.json"
    source = tmp_path / "models/hero.glb"
    payload = recipe.recipe_to_dict(
        recipe.Recipe(str(source), RenderSettings(), export.ExportConfig()), path)
    assert payload["source"] == "../models/hero.glb"
