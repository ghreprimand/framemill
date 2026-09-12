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
    scene = SimpleNamespace(render=SimpleNamespace(filepath=""), frame_current=1)
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


def test_oneshot_preview_matches_first_sheet_pose(renderer, tmp_path):
    module, sampled = renderer
    cfg = RenderSettings(angles=1, frames=5, loop_mode="oneshot",
                         anim_start_override=0, anim_end_override=10).render_config()
    module.render_all("walk.fbx", tmp_path, cfg, preview=True)
    first = sampled[0]
    sampled.clear()
    module.render_all("walk.fbx", tmp_path, cfg)
    assert first == sampled[0] == 0
    assert sampled[-1] == 10


def test_oneshot_samples_include_final_endpoint(renderer, tmp_path):
    module, sampled = renderer
    cfg = RenderSettings(angles=1, frames=4, loop_mode="oneshot",
                         anim_start_override=0, anim_end_override=10,
                         phase_offset=.5).render_config()
    module.render_all("walk.fbx", tmp_path, cfg)
    assert sampled[0] == 0
    assert sampled[-1] == 10
    assert sampled == pytest.approx([0, 10 / 3, 20 / 3, 10])


def test_oneshot_reverse_does_not_wrap(renderer, tmp_path):
    module, sampled = renderer
    cfg = RenderSettings(angles=1, frames=3, loop_mode="oneshot", reverse=True,
                         anim_start_override=0, anim_end_override=10).render_config()
    module.render_all("walk.fbx", tmp_path, cfg)
    assert sampled == [10, 5, 0]


def test_apply_source_yaw_parents_roots_so_animation_can_update_local(renderer):
    module, _ = renderer

    class FakeMatrix:
        def __init__(self):
            self.identity_called = False

        def identity(self):
            self.identity_called = True

    class FakeObj:
        def __init__(self, name, parent=None):
            self.name = name
            self.parent = parent
            self.matrix_parent_inverse = FakeMatrix()
            self.matrix_world = "local-pose"

    empty = type("Empty", (), {"rotation_euler": (0, 0, 0)})()
    linked = []
    module.bpy.data = SimpleNamespace(objects=SimpleNamespace(new=lambda *a, **k: empty))
    module.bpy.context.scene.collection = SimpleNamespace(
        objects=SimpleNamespace(link=lambda obj: linked.append(obj)))
    root = FakeObj("MovingArm")
    child = FakeObj("Mesh", parent=root)
    module.apply_source_yaw([root, child], 90)
    assert linked == [empty]
    assert root.parent is empty
    assert child.parent is root
    assert root.matrix_parent_inverse.identity_called
    assert root.matrix_world == "local-pose"
    assert empty.rotation_euler[2] != 0
    module.apply_source_yaw([root], 0)
    assert root.parent is empty


def test_source_yaw_is_applied_once_and_does_not_reorder_sheet(renderer, tmp_path, monkeypatch):
    module, _ = renderer
    seen = []
    monkeypatch.setattr(module, "apply_source_yaw", lambda objs, yaw: seen.append(yaw))
    written = []
    monkeypatch.setattr(module.bpy.ops.render, "render", lambda **kw: written.append(
        Path(module.bpy.context.scene.render.filepath).stem))
    cfg = RenderSettings(angles=4, frames=1, start_direction="S", rotation="cw",
                         source_yaw=90).render_config()
    module.render_all("walk.fbx", tmp_path, cfg)
    assert seen == [90]
    assert [name.split("_")[0] for name in written] == ["S", "W", "N", "E"]


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


def test_single_override_is_checked_against_detected_range(renderer, tmp_path):
    module, _ = renderer
    cfg = RenderSettings(angles=1, anim_start_override=100).render_config()
    with pytest.raises(ValueError, match="Source start"):
        module.render_all("walk.fbx", tmp_path, cfg)


def test_remove_root_motion_calls_setup_camera_per_frame(renderer, tmp_path, monkeypatch):
    module, _ = renderer
    cameras = []
    monkeypatch.setattr(module, "setup_camera",
                        lambda center, size, angle, cfg: cameras.append((center, size)))
    boxes = [
        ((0.0, 0.0, 0.0), (1.0, 1.0, 2.0)),
        ((2.0, 0.0, 0.0), (3.0, 1.0, 2.0)),
        ((4.0, 0.0, 0.0), (5.0, 1.0, 2.0)),
        ((6.0, 0.0, 0.0), (7.0, 1.0, 2.0)),
    ]
    calls = {"n": 0}

    def fake_bounds(objs):
        box = boxes[calls["n"] % 4]
        calls["n"] += 1
        return box

    monkeypatch.setattr(module, "mesh_bounds", fake_bounds)
    cfg = RenderSettings(angles=1, frames=4, remove_root_motion=True, anchor="center",
                         anim_start_override=0, anim_end_override=10).render_config()
    module.render_all("walk.fbx", tmp_path, cfg)
    assert len(cameras) == 4
    assert cameras[0][1] == (1.0, 1.0, 2.0)
    assert cameras[0][0][0] == 0.5
    assert cameras[-1][0][0] == 6.5
    assert cameras[0][0][2] == 1.0


def test_camera_ortho_scale_matches_host_fit_basis(renderer):
    from framemill.settings import framing_ortho_scale

    module, _ = renderer
    size = (6.0, 2.0, 2.0)
    for basis in ("height", "width", "contain"):
        cfg = RenderSettings(fit_basis=basis, ortho_scale_mult=2).render_config()
        assert module.camera_ortho_scale(size, cfg) == pytest.approx(
            framing_ortho_scale(RenderSettings(fit_basis=basis, ortho_scale_mult=2), size))


def test_inspect_includes_dimensions_and_mesh_count(renderer, monkeypatch):
    import json

    module, _ = renderer
    logs = []
    monkeypatch.setattr(module, "clear_scene", lambda: None)
    monkeypatch.setattr(module, "import_model", lambda path: [
        SimpleNamespace(type="MESH"), SimpleNamespace(type="MESH"),
        SimpleNamespace(type="ARMATURE"),
    ])
    monkeypatch.setattr(module, "mesh_bounds", lambda objs: ((0.0, 0.0, 0.0), (1.25, 0.5, 2.0)))
    monkeypatch.setattr(module, "first_action_name", lambda objs: "Walk")
    monkeypatch.setattr(module, "log", logs.append)
    module.bpy.context.scene.render.fps = 30
    module.do_inspect("walk.fbx")
    payload = json.loads(logs[-1].split("INSPECT ", 1)[1])
    assert payload["action"] == "Walk"
    assert payload["dimensions"] == [1.25, 0.5, 2.0]
    assert payload["mesh_count"] == 2
    assert "frame_start" in payload and "duration_frames" in payload


def test_root_motion_off_sets_camera_once_per_direction(renderer, tmp_path, monkeypatch):
    module, _ = renderer
    cameras = []
    monkeypatch.setattr(module, "setup_camera", lambda *args: cameras.append(args))
    cfg = RenderSettings(angles=2, frames=3, remove_root_motion=False).render_config()
    module.render_all("walk.fbx", tmp_path, cfg)
    assert len(cameras) == 2
