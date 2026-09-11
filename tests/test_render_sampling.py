"""Exercise Blender-side sampling without needing Blender in the unit suite."""
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from framemill.settings import RenderSettings


@pytest.fixture
def renderer(monkeypatch):
    sampled = []
    scene = SimpleNamespace(render=SimpleNamespace(filepath=""))
    scene.frame_set = lambda f, subframe=0: sampled.append(f + subframe)
    bpy = SimpleNamespace(context=SimpleNamespace(scene=scene),
                          ops=SimpleNamespace(render=SimpleNamespace(render=lambda **kw: None)))
    monkeypatch.setitem(sys.modules, "bpy", bpy)
    monkeypatch.setitem(sys.modules, "mathutils", SimpleNamespace())
    path = Path(__file__).parents[1] / "framemill/blender/render_sprites.py"
    spec = importlib.util.spec_from_file_location("render_sampling_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in ("clear_scene", "adjust_materials", "setup_render", "setup_camera", "setup_light"):
        monkeypatch.setattr(module, name, lambda *args: None)
    monkeypatch.setattr(module, "import_model", lambda path: [])
    monkeypatch.setattr(module, "anim_range", lambda objs: (1, 21))
    monkeypatch.setattr(module, "max_bounds", lambda *args: ((0, 0, 0), (1, 1, 2)))
    return module, sampled


@pytest.mark.parametrize("phase,reverse", [(0, False), (.25, False), (.25, True)])
def test_preview_pose_matches_first_sheet_pose(renderer, tmp_path, phase, reverse):
    module, sampled = renderer
    cfg = RenderSettings(angles=1, frames=4, phase_offset=phase, reverse=reverse).render_config()
    module.render_all("walk.fbx", tmp_path, cfg, preview=True)
    first = sampled[0]
    sampled.clear()
    module.render_all("walk.fbx", tmp_path, cfg)
    assert first == sampled[0]
    assert len(set(sampled)) == 4


def test_zero_frame_override_and_fractional_sampling(renderer, tmp_path):
    module, sampled = renderer
    cfg = RenderSettings(angles=1, frames=4, anim_start_override=0,
                         anim_end_override=10).render_config()
    module.render_all("walk.fbx", tmp_path, cfg)
    assert sampled == [0, 2.5, 5, 7.5]


def test_idle_preview_uses_same_idle_pose_as_sheet(renderer, tmp_path):
    module, sampled = renderer
    cfg = RenderSettings(angles=1, frames=4, phase_offset=.25, idle_frame_index=3).render_config()
    module.render_all("walk.fbx", tmp_path, cfg, idle="idle.fbx", preview=True)
    assert sampled == [3]
    sampled.clear()
    module.render_all("walk.fbx", tmp_path, cfg, idle="idle.fbx")
    assert sampled[-1] == 3
    assert len(sampled) == 4


@pytest.mark.parametrize("explicit_layout", [True, False])
@pytest.mark.parametrize("rotation,expected", [
    ("cw", ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]),
    ("ccw", ["N", "NW", "W", "SW", "S", "SE", "E", "NE"]),
])
def test_renderer_visits_directions_in_compass_order(renderer, tmp_path, monkeypatch,
                                                     explicit_layout, rotation, expected):
    module, _ = renderer
    written = []
    monkeypatch.setattr(module.bpy.ops.render, "render", lambda **kw: written.append(
        Path(module.bpy.context.scene.render.filepath).stem))
    cfg = RenderSettings(angles=8, frames=1, start_direction="N", rotation=rotation).render_config()
    if not explicit_layout:
        cfg.pop("_layout")
    module.render_all("walk.fbx", tmp_path, cfg)
    assert written == [f"{name}_00" for name in expected]
