"""Reset helper returns factory defaults without Blender or Flet widgets."""
from framemill.app import reset_workspace_settings
from framemill.export import DEFAULT_EXPORT, EXPORT_PRESETS, ExportConfig
from framemill.settings import RenderSettings


def test_reset_workspace_settings_matches_factory_defaults():
    dirty_render = RenderSettings(frames=11, angles=16, camera_pitch=45, source_yaw=90,
                                  loop_mode="oneshot", framing_mode="fixed")
    dirty_export = ExportConfig(format="bmp", depth=8, background="magic_pink")
    render, export_cfg = reset_workspace_settings()
    assert render == RenderSettings()
    assert export_cfg == EXPORT_PRESETS[DEFAULT_EXPORT].config
    assert export_cfg.format == "png" and export_cfg.depth == 32
    assert export_cfg.background == "transparent"
    assert dirty_render.frames == 11 and dirty_export.format == "bmp"
