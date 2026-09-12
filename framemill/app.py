"""Framemill's desktop sprite workspace and local browser preview."""
from __future__ import annotations

import asyncio
import copy
import dataclasses
import io
import os
import tempfile
import threading
from pathlib import Path

import flet as ft
from PIL import Image

from . import appconfig, blender, compositor, export, help_content, recipe
from .export import DEFAULT_EXPORT, EXPORT_PRESETS, ExportConfig
from .preview_schedule import PREVIEW_DEBOUNCE_S, after_render_job, user_cancel
from .settings import PRESETS, RenderSettings, direction_names, next_playback_frame

BG = "#101213"
PANEL = "#191c1d"
CARD = "#202425"
BORDER = "#303637"
TEXT = "#edf0ea"
MUTED = "#a2aca7"
FAINT = "#717e78"
ACCENT = "#d4ee95"
INK = "#202a17"
CENTER = ft.Alignment(0, 0)


def png_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def frame_at(sheet: Image.Image, settings: RenderSettings, direction: int, frame: int):
    w, h = settings.frame_width, settings.frame_height
    x, y = ((direction * w, frame * h) if settings.layout_axis == "cols"
            else (frame * w, direction * h))
    return sheet.crop((x, y, x + w, y + h))


def preview_settings(settings: RenderSettings, facing: str = "S") -> RenderSettings:
    """Independent view direction; never mutate the user's export layout."""
    return dataclasses.replace(settings, angles=8, start_direction=facing)


def reset_workspace_settings() -> tuple[RenderSettings, ExportConfig]:
    """Default render + export settings. Does not touch model or Blender path."""
    return RenderSettings(), copy.deepcopy(EXPORT_PRESETS[DEFAULT_EXPORT].config)


def main(page: ft.Page) -> None:
    page.title = "Framemill: Sprite workspace"
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = ft.Theme(color_scheme_seed=ACCENT, font_family="Inter", use_material3=True)
    page.bgcolor = BG
    page.padding = 0
    page.window.width, page.window.height = 1440, 940
    page.window.min_width, page.window.min_height = 1050, 740
    saved = appconfig.load()
    settings, setting_warnings = RenderSettings.from_dict_recovering(saved.get("render_settings", {}))
    cfg_fields = ExportConfig.__dataclass_fields__
    try:
        export_cfg = ExportConfig(**{k: v for k, v in saved.get("export_settings", {}).items()
                                     if k in cfg_fields}) if saved.get("export_settings") else copy.deepcopy(
                                         EXPORT_PRESETS[DEFAULT_EXPORT].config)
        export.validate_config(export_cfg)
    except (TypeError, ValueError) as exc:
        setting_warnings.append(f"Saved export settings were reset: {exc}")
        export_cfg = copy.deepcopy(EXPORT_PRESETS[DEFAULT_EXPORT].config)
    model: str | None = None
    idle: str | None = None
    bpath = blender.find_blender()
    result: Image.Image | None = None
    result_settings: RenderSettings | None = None
    result_source = ""
    is_preview = True
    busy = False
    stale = False
    playing = False
    play_generation = 0
    direction = 0
    preview_facing = "S"
    view_reset_pending = True
    frame = 0
    view = "sprite"
    zoom = 3
    fps = 8
    resize_dialog = None
    refresh_open_export = None
    preview_seq = 0
    pending_preview = False
    pending_sheet = False
    last_sheet = None
    last_sheet_settings = None
    last_sheet_source = ""
    last_sheet_detected: dict = {}
    PREVIEW_FIELDS = {
        "camera_pitch", "ortho_scale_mult", "camera_distance", "framing_mode",
        "framing_scale", "framing_origin_x", "framing_origin_y", "framing_origin_z",
        "anchor", "output_offset_x", "output_offset_y", "light_energy", "light_color",
        "shadow_soft_size", "ambient_color", "ambient_strength", "view_transform",
        "look", "exposure", "gamma", "specular_ior", "source_yaw", "loop_mode",
        "phase_offset", "reverse", "anim_start_override", "anim_end_override",
        "frames", "frame_width", "frame_height", "samples", "engine",
        "remove_root_motion",
    }
    detected = {"frame_start": None, "frame_end": None, "fps": None,
                "action": None, "duration_frames": None}
    result_detected: dict = {}
    inspect_token = 0
    cancel = threading.Event()
    picker = ft.FilePicker()
    page.services.append(picker)

    def text(value, size=12, color=TEXT, weight=None, **kwargs):
        return ft.Text(value, size=size, color=color, weight=weight, **kwargs)

    def border():
        return ft.Border.all(1, BORDER)

    def button(label, icon, action, primary=False, **kwargs):
        cls = ft.FilledButton if primary else ft.OutlinedButton
        return cls(label, icon=icon, on_click=action, height=40,
                   style=ft.ButtonStyle(bgcolor={ft.ControlState.DEFAULT: ACCENT if primary else PANEL,
                                                ft.ControlState.DISABLED: CARD},
                                        color={ft.ControlState.DEFAULT: INK if primary else TEXT,
                                               ft.ControlState.DISABLED: FAINT},
                                        shape=ft.RoundedRectangleBorder(radius=8),
                                        side=ft.BorderSide(0 if primary else 1, BORDER),
                                        text_style=ft.TextStyle(size=12)), **kwargs)

    def field(label, value, on_change, width=None, **kwargs):
        kwargs.setdefault("label_style", ft.TextStyle(size=11))
        return ft.TextField(label=label, value=str(value), on_change=on_change or (lambda e: None), width=width,
                            text_size=12, dense=True, filled=True, fill_color=BG,
                            border_color=BORDER, focused_border_color=ACCENT,
                            border_radius=7, **kwargs)

    def dropdown(label, value, options, callback, width=None, **kwargs):
        if width is None and not kwargs.get("expand"):
            width = 270
        return ft.Dropdown(label=label, value=str(value), width=width, text_size=12,
                           filled=True, fill_color=BG, border_color=BORDER, border_radius=7,
                           content_padding=ft.Padding(12, 10, 10, 10),
                           options=[ft.dropdown.Option(str(k), str(v)) for k, v in options],
                           on_select=lambda e: callback(e.control.value), **kwargs)

    def caption(value):
        return text(value.upper(), 10, FAINT, ft.FontWeight.W_600)

    appearance_fields = (
        "ortho_scale_mult", "camera_distance", "camera_pitch", "light_energy", "light_color",
        "shadow_soft_size", "ambient_color", "ambient_strength", "view_transform", "look",
        "exposure", "gamma", "specular_ior",
    )

    def appearance_key():
        return next((key for key, preset in PRESETS.items()
                     if all(getattr(settings, name) == getattr(preset.settings, name)
                            for name in appearance_fields)), "custom")

    def persist():
        data = appconfig.load()
        data.update(render_settings=settings.to_dict(), export_settings=dataclasses.asdict(export_cfg))
        appconfig.save(data)

    status = text("Choose a model to begin", 11, MUTED)
    progress = ft.ProgressBar(value=0, color=ACCENT, bgcolor=BORDER, bar_height=2, visible=False)
    model_name = text("No source loaded", 13, TEXT, ft.FontWeight.W_500,
                      no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS)
    model_detail = text("FBX, GLB, glTF or OBJ", 10, FAINT)
    source_clip = text("Load a model to read its animation range.", 11, MUTED)
    source_clip_motion = text("Load a model to read its animation range.", 11, MUTED)
    idle_name = text("No replacement model", 11, MUTED, expand=True,
                     no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS)
    headline = text("Your next character starts here.", 24, TEXT, ft.FontWeight.W_600)
    subtitle = text("A 3D source. Every direction. Ready for your game.", 12, MUTED)
    result_badge = text("WORKSPACE", 10, ACCENT, ft.FontWeight.W_600)
    dimensions = text("-", 11, MUTED)
    frame_label = text("FRAME  - / -", 10, MUTED)
    direction_buttons = ft.Row(spacing=5, wrap=True, expand=True)
    timeline = ft.Row(spacing=8, scroll=ft.ScrollMode.AUTO)
    sprite_image = ft.Image(src=b"", fit=ft.BoxFit.CONTAIN, gapless_playback=True,
                            filter_quality=ft.FilterQuality.NONE, visible=False)
    pan_x = pan_y = 0.0
    gesture_zoom = gesture_start_zoom = 1.0

    def apply_view_transform():
        sprite_image.transform = ft.Transform(
            matrix=ft.Matrix4.identity().translate(pan_x, pan_y).scale(gesture_zoom),
            alignment=CENTER,
        )
        page.update()

    def begin_gesture(e):
        nonlocal gesture_start_zoom
        gesture_start_zoom = gesture_zoom

    def update_gesture(e):
        nonlocal pan_x, pan_y, gesture_zoom
        pan_x += e.focal_point_delta.x
        pan_y += e.focal_point_delta.y
        gesture_zoom = max(.25, min(8, gesture_start_zoom * e.scale))
        apply_view_transform()

    def scroll_zoom(e):
        nonlocal gesture_zoom
        factor = 2 ** max(-2, min(2, -e.scroll_delta.y / 400))
        gesture_zoom = max(.25, min(8, gesture_zoom * factor))
        apply_view_transform()

    viewer = ft.GestureDetector(
        content=ft.Container(sprite_image, alignment=CENTER), expand=True,
        on_scale_start=begin_gesture, on_scale_update=update_gesture,
        on_scroll=scroll_zoom, drag_interval=16,
    )

    async def reset_view():
        nonlocal pan_x, pan_y, gesture_zoom
        pan_x = pan_y = 0.0
        gesture_zoom = 1.0
        apply_view_transform()

    empty_icon = ft.Container(ft.Icon(ft.Icons.VIEW_IN_AR_OUTLINED, size=36, color=ACCENT),
                              padding=20, bgcolor="#242e23", border_radius=20)
    empty_tagline = text("RENDERED WITH BLENDER  /  BUILT FOR GAMES", 9, FAINT)
    empty = ft.Column([
        empty_icon,
        text("From model to motion", 25, TEXT, ft.FontWeight.W_600),
        text("Load an animated model to see your first sprite.\nFine-tune the look, build the sheet, then export.",
             13, MUTED, text_align=ft.TextAlign.CENTER),
        button("Choose a model", ft.Icons.ADD, lambda e: page.run_task(pick_source), True),
        empty_tagline,
    ], spacing=12, scroll=ft.ScrollMode.AUTO, alignment=ft.MainAxisAlignment.CENTER,
       horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    viewport = ft.Container(content=empty, expand=True, alignment=CENTER, bgcolor="#151919",
        image=ft.DecorationImage(src="checker.png", repeat=ft.ImageRepeat.REPEAT),
        border=border(), border_radius=12, clip_behavior=ft.ClipBehavior.HARD_EDGE)

    def notify(message):
        status.value = message
        page.update()

    def mark_changed(preview=True):
        nonlocal stale, playing
        stale = last_sheet is not None
        playing = False
        play_btn.icon = ft.Icons.PLAY_ARROW_ROUNDED
        result_badge.value = "CHANGES PENDING" if stale else "WORKSPACE"
        appearance_dd.value = appearance_key()
        persist()
        update_geometry()
        if preview:
            schedule_preview()
        page.update()

    def change(name, value):
        setattr(settings, name, value)
        mark_changed(preview=name in PREVIEW_FIELDS)

    def schedule_preview():
        nonlocal preview_seq
        if not model or not bpath:
            return
        preview_seq += 1
        seq = preview_seq

        async def wait():
            await asyncio.sleep(PREVIEW_DEBOUNCE_S)
            if seq != preview_seq:
                return
            start_render(True, seq=seq)

        page.run_task(wait)

    def integer(name, event):
        try:
            value = int(event.control.value)
            maximum = 64 if name == "frames" else 1024
            if not 1 <= value <= maximum:
                raise ValueError
            event.control.error = None
            change(name, value)
        except ValueError:
            event.control.error = f"Enter 1-{maximum}"
            page.update()

    def optional_frame(name, event):
        raw = (event.control.value or "").strip()
        if raw == "":
            event.control.error = None
            change(name, None)
            return
        try:
            event.control.error = None
            change(name, int(raw))
        except ValueError:
            event.control.error = "Enter a frame number"
            page.update()

    def signed_int(name, event):
        try:
            event.control.error = None
            change(name, int(event.control.value))
        except ValueError:
            event.control.error = "Enter a whole number"
            page.update()

    def decimal(name, event):
        try:
            event.control.error = None
            change(name, float(event.control.value))
        except ValueError:
            event.control.error = "Enter a number"
            page.update()

    def color_change(name, event):
        try:
            export.hex_to_rgb(event.control.value)
            if len(event.control.value.lstrip("#")) not in (3, 6):
                raise ValueError
            event.control.error = None
            change(name, event.control.value)
        except ValueError:
            event.control.error = "Use #RGB or #RRGGBB"
            page.update()

    def slider(label, name, lo, hi, divisions, suffix=""):
        current = text(f"{getattr(settings, name):g}{suffix}", 11, ACCENT)

        def update(e):
            current.value = f"{e.control.value:g}{suffix}"
            change(name, float(e.control.value))

        return ft.Column([ft.Row([text(label, 11, MUTED), current],
                                 alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                          ft.Slider(value=getattr(settings, name), min=lo, max=hi,
                                    divisions=divisions, active_color=ACCENT,
                                    inactive_color=BORDER, on_change=update)], spacing=0)

    def section(label, controls):
        return ft.Column([caption(label), *controls], spacing=12,
                         horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    def update_geometry():
        sw, sh = settings.sheet_size()
        mib = settings.estimated_sheet_bytes() / (1024 ** 2)
        geometry.value = (
            f"{sw} × {sh} px sheet  ·  {settings.angles * settings.frames} sprites  ·  ~{mib:.1f} MiB RGBA"
        )
        axis = "Row" if settings.layout_axis == "rows" else "Column"
        names = [name if name != "angle0" else "Front" for name, _ in settings.direction_layout()]
        layout_order.value = f"{axis} order: " + " → ".join(names)

    def update_source_clip():
        if detected.get("frame_start") is None:
            message = "Load a model to read its animation range."
        else:
            action = detected.get("action") or "scene range"
            span = detected.get("duration_frames")
            fps_v = detected.get("fps")
            message = (
                f"Detected: {action} · frames {detected['frame_start']}-{detected['frame_end']}"
                + (f" · {span}-frame span" if span is not None else "")
                + (f" · {fps_v} fps source" if fps_v else "")
            )
        source_clip.value = message
        source_clip_motion.value = message

    geometry = text("", 10, ACCENT)
    layout_order = text("", 11, ACCENT)
    inspector = ft.Column(spacing=20, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
    inspector_tab = "look"
    tab_buttons = ft.Row(spacing=4)
    studio_panel = section("03 / Studio", [
        ft.Container(tab_buttons, padding=3, border=border(), border_radius=9, bgcolor=BG),
    ])

    def build_inspector():
        tab_buttons.controls = []
        for key, title in (("look", "Appearance"), ("motion", "Layout & timing")):
            def select(e, key=key):
                nonlocal inspector_tab
                inspector_tab = key
                build_inspector()
                page.update()
            selected = key == inspector_tab
            tab_buttons.controls.append(ft.Container(
                text(title, 13, ACCENT if selected else TEXT, ft.FontWeight.W_600,
                     text_align=ft.TextAlign.CENTER),
                padding=ft.Padding(14, 12, 14, 12), border_radius=7,
                bgcolor="#2a3325" if selected else None, alignment=CENTER,
                on_click=select, expand=True))
        if inspector_tab == "look":
            inspector.controls = [
                section("Camera", [slider("Elevation · 90° is level", "camera_pitch", 30, 120, 90, "°"),
                                   dropdown("Framing mode", settings.framing_mode,
                                            [("fit", "Fit this clip"), ("fixed", "Fixed world scale")],
                                            framing_mode_changed),
                                   ft.Container(slider("Fit multiplier", "ortho_scale_mult", .5, 4, 70, "×"),
                                                visible=settings.framing_mode == "fit"),
                                   ft.Column([
                                   field("Fixed world scale", settings.framing_scale,
                                         lambda e: decimal("framing_scale", e),
                                         disabled=settings.framing_mode != "fixed"),
                                   caption("World origin"),
                                   ft.Row([
                                       field("X", settings.framing_origin_x,
                                             lambda e: decimal("framing_origin_x", e), expand=True,
                                             disabled=settings.framing_mode != "fixed"),
                                       field("Y", settings.framing_origin_y,
                                             lambda e: decimal("framing_origin_y", e), expand=True,
                                             disabled=settings.framing_mode != "fixed"),
                                       field("Z", settings.framing_origin_z,
                                             lambda e: decimal("framing_origin_z", e), expand=True,
                                             disabled=settings.framing_mode != "fixed"),
                                   ], spacing=8),
                                   ], visible=settings.framing_mode == "fixed", spacing=12,
                                      horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
                                   dropdown("Anchor", settings.anchor,
                                            [("center", "Bounds centre"), ("feet", "Feet / lowest point")],
                                            lambda v: change("anchor", v),
                                            visible=settings.framing_mode != "fixed"),
                                   ft.Row([
                                       field("Offset X · px", settings.output_offset_x,
                                             lambda e: signed_int("output_offset_x", e), expand=True),
                                       field("Offset Y · px", settings.output_offset_y,
                                             lambda e: signed_int("output_offset_y", e), expand=True),
                                   ], spacing=10),
                                   text("Fixed scale and origin are world units and stay identical across clips. "
                                        "Fit mode may use this clip's bounds. Output offsets are finished-cell "
                                        "pixels (+X right, +Y down). Viewer pan/zoom is display-only.", 11, MUTED),
                                   slider("Orbit distance · camera and light", "camera_distance", .5, 10, 95),
                                   text("Orbit distance is not zoom: it places the camera and the light. "
                                        "Use Framing or Fixed world scale to change how large the character is.", 11, MUTED)]),
                section("Light & environment", [slider("Light energy", "light_energy", 0, 3000, 60),
                    slider("Softness", "shadow_soft_size", 0, 2, 40),
                    field("Light colour", settings.light_color, lambda e: color_change("light_color", e)),
                    slider("Ambient strength", "ambient_strength", 0, 8, 80),
                    field("Ambient colour", settings.ambient_color, lambda e: color_change("ambient_color", e))]),
                section("Colour & material", [
                    dropdown("View transform", settings.view_transform,
                             [(v, v) for v in ("Standard", "AgX", "Filmic")],
                             lambda v: change("view_transform", v)),
                    slider("Exposure", "exposure", -3, 3, 60),
                    slider("Gamma", "gamma", .2, 3, 56),
                    slider("Specular IOR", "specular_ior", 0, 1, 20)]),
            ]
        else:
            names = [n for n, _ in settings.direction_layout()]
            inspector.controls = [
                section("Direction order", [
                    dropdown("First direction", settings.start_direction,
                             [(n, n) for n in names] if settings.angles > 1 else [("S", "Front")],
                             lambda v: change("start_direction", v)),
                    dropdown("Rotation", settings.rotation, [("cw", "Clockwise"), ("ccw", "Counter-clockwise")],
                             lambda v: change("rotation", v)),
                    dropdown("Sheet layout", settings.layout_axis,
                             [("rows", "Directions as rows"), ("cols", "Directions as columns")],
                             lambda v: change("layout_axis", v)),
                    layout_order,
                    text("Sheet order only changes cell sequence. It does not rotate the mesh.", 11, MUTED)]),
                section("Source facing", [
                    ft.Row([
                        button("Left 90°", ft.Icons.ROTATE_LEFT, lambda e: nudge_yaw(90), expand=True),
                        button("Right 90°", ft.Icons.ROTATE_RIGHT, lambda e: nudge_yaw(-90), expand=True),
                    ], spacing=8),
                    field("Yaw · degrees", settings.source_yaw, lambda e: decimal("source_yaw", e)),
                    text("Rotates the imported source (and its animation) around world Z. "
                         "Independent of preview facing and sheet order.", 11, MUTED)]),
                section("Animation", [
                    dropdown("Playback / sampling", settings.loop_mode,
                             [("loop", "Loop · exclude end pose"), ("oneshot", "One-shot · include end pose")],
                             loop_mode_changed),
                    source_clip_motion,
                    ft.Row([
                        field("Source start", "" if settings.anim_start_override is None else settings.anim_start_override,
                              lambda e: optional_frame("anim_start_override", e), expand=True,
                              hint_text="detected"),
                        field("Source end", "" if settings.anim_end_override is None else settings.anim_end_override,
                              lambda e: optional_frame("anim_end_override", e), expand=True,
                              hint_text="detected"),
                    ], spacing=10),
                    slider("First pose / phase", "phase_offset", 0, 1, 100) if settings.loop_mode != "oneshot"
                    else text("Phase is ignored for one-shot clips.", 11, MUTED),
                    ft.Switch(label="Reverse playback", value=settings.reverse, active_color=ACCENT,
                              on_change=lambda e: change("reverse", e.control.value)),
                    ft.Switch(label="Remove root motion (re-center each frame)",
                              value=settings.remove_root_motion, active_color=ACCENT,
                              on_change=lambda e: change("remove_root_motion", e.control.value)),
                    text("For animations that travel across the ground. Keeps the character centered "
                         "in every frame. Not needed if your source is already in-place "
                         "(for example Mixamo In Place).", 11, MUTED),
                    text("Loop wraps and skips the final endpoint so a walk cycle does not repeat its first pose. "
                         "One-shot includes both endpoints when there are two or more frames; "
                         "a single frame is the start pose (or the end pose if reversed). "
                         "Preview playback stops at the last one-shot frame. "
                         "Full action/NLA clip picking remains future work: one intended action per file.", 11, MUTED)]),
                section("First-frame replacement (advanced)", [ft.Row([idle_name, ft.IconButton(ft.Icons.CLOSE, icon_size=16,
                                                                 on_click=clear_idle)]),
                    button("Choose replacement model", ft.Icons.ACCESSIBILITY_NEW, lambda e: page.run_task(pick_source, True)),
                    text("For a normal idle sheet, load the idle FBX as the main source and export separately.", 11, MUTED),
                    text("Compatibility only: replaces frame 01; does not add a slot or blend poses. "
                         "11 frames becomes 1 replacement + 10 original samples. "
                         "Playback includes it; skipping it still leaves uneven loop timing.", 11, MUTED)]),
            ]

    def choose_preset(key):
        # Appearance presets leave output layout and animation choices intact.
        if key == "custom":
            return
        preset = PRESETS[key].settings
        for name in appearance_fields:
            setattr(settings, name, getattr(preset, name))
        build_inspector()
        mark_changed()

    def angles_changed(value):
        settings.angles = int(value)
        if settings.start_direction not in [n for n, _ in settings.direction_layout()]:
            settings.start_direction = "S"
        build_inspector()
        mark_changed(preview=False)

    def loop_mode_changed(value):
        settings.loop_mode = value
        build_inspector()
        mark_changed()

    def framing_mode_changed(value):
        settings.framing_mode = value
        build_inspector()
        mark_changed()

    def nudge_yaw(delta):
        settings.source_yaw = float(settings.source_yaw or 0) + delta
        build_inspector()
        mark_changed()

    def sync_chrome():
        width_field.value = str(settings.frame_width)
        height_field.value = str(settings.frame_height)
        frames_field.value = str(settings.frames)
        width_field.error = height_field.error = frames_field.error = None
        angles_dd.value = str(settings.angles)
        appearance_dd.value = appearance_key()
        build_inspector()
        update_geometry()

    def apply_workspace_defaults():
        nonlocal settings, export_cfg
        settings, export_cfg = reset_workspace_settings()
        sync_chrome()
        persist()
        if refresh_open_export is not None:
            refresh_open_export()
        mark_changed()
        notify("Render and export settings reset to defaults.")

    def confirm_reset(e=None):
        def accept(ev):
            page.pop_dialog()
            apply_workspace_defaults()

        page.show_dialog(ft.AlertDialog(
            title=text("Reset to defaults", 20),
            content=text(
                "Reset all render and export settings to defaults? "
                "Your loaded model and Blender connection stay.",
                13, MUTED),
            actions=[
                button("Cancel", ft.Icons.CLOSE, lambda ev: page.pop_dialog()),
                button("Reset", ft.Icons.RESTART_ALT, accept, True),
            ],
            bgcolor=PANEL))

    def inspect_job(executable, source, token):
        try:
            info = blender.inspect(executable, source)
        except Exception as exc:  # noqa: BLE001  inspect is best-effort UI metadata
            if token != inspect_token or model != source:
                return
            detected.update(frame_start=None, frame_end=None, fps=None,
                            action=None, duration_frames=None)
            source_clip.value = source_clip_motion.value = f"Could not inspect animation: {exc}"
            page.update()
            return
        if token != inspect_token or model != source:
            return
        detected.update({key: info.get(key) for key in
                         ("frame_start", "frame_end", "fps", "action", "duration_frames")})
        if result_source == source:
            result_detected.update(detected)
        update_source_clip()
        page.update()

    def start_inspect():
        nonlocal inspect_token
        if not bpath or not model:
            return
        inspect_token += 1
        page.run_thread(inspect_job, bpath, model, inspect_token)

    def clear_idle(e=None):
        nonlocal idle
        idle = None
        idle_name.value = "No replacement model"
        mark_changed()

    async def pick_source(for_idle=False):
        if busy and not is_preview:
            return
        if page.web:
            path_field = field("Absolute path on this computer", "", None, width=500,
                               hint_text="/path/to/character.fbx")

            def load(e):
                path = Path(path_field.value).expanduser()
                if not path.is_file() or path.suffix.lower() not in (".fbx", ".glb", ".gltf", ".obj"):
                    path_field.error = "Enter an existing FBX, GLB, glTF or OBJ path."
                    page.update()
                    return
                page.pop_dialog()
                set_source(str(path), for_idle)

            page.show_dialog(ft.AlertDialog(title=text("Choose replacement model" if for_idle else "Open a source model", 20),
                content=ft.Column([text("Browser preview uses a file path on this computer.", 12, MUTED),
                                   path_field], tight=True),
                actions=[button("Cancel", ft.Icons.CLOSE, lambda e: page.pop_dialog()),
                         button("Load model", ft.Icons.ARROW_FORWARD, load, True)], bgcolor=PANEL))
            return
        files = await picker.pick_files(allow_multiple=False, file_type=ft.FilePickerFileType.CUSTOM,
                                        allowed_extensions=["fbx", "glb", "gltf", "obj"])
        if files and files[0].path:
            set_source(files[0].path, for_idle)

    def set_source(path, for_idle=False):
        nonlocal model, idle, result, result_settings, playing, preview_facing, view, view_reset_pending
        nonlocal last_sheet, last_sheet_settings, last_sheet_source
        if for_idle:
            idle = path
            idle_name.value = Path(path).name
            mark_changed()
        else:
            model = path
            preview_facing = "S"
            view_reset_pending = True
            view = "sprite"
            sprite_tab.bgcolor, sheet_tab.bgcolor = "#303a2a", PANEL
            result = result_settings = None
            last_sheet = last_sheet_settings = None
            last_sheet_source = ""
            last_sheet_detected.clear()
            playing = False
            model_name.value = Path(path).name
            model_detail.value = f"{Path(path).suffix[1:].upper()}  ·  {Path(path).stat().st_size / 1024**2:.1f} MB"
            headline.value = Path(path).stem.replace("_", " ")
            subtitle.value = "Shape the look. Find the motion. Make it yours."
            timeline.controls.clear()
            sprite_image.visible = False
            empty.visible = True
            viewport.content = empty
            export_btn.disabled = True
            start_inspect()
        start_render(True)

    async def pick_recipe(saving=False):
        if page.web:
            path_field = field("Absolute path on this computer", "", None, width=500,
                               hint_text="/path/to/character.recipe.json")

            def confirm(e):
                if not (path_field.value or "").strip():
                    path_field.error = "Enter a recipe file path."
                    page.update()
                    return
                path = Path(path_field.value).expanduser()
                page.pop_dialog()
                if saving:
                    save_recipe_to(path)
                else:
                    load_recipe_from(path)

            page.show_dialog(ft.AlertDialog(
                title=text("Save recipe" if saving else "Load recipe", 20),
                content=ft.Column([
                    text("Browser preview uses a file path on this computer.", 12, MUTED),
                    path_field], tight=True),
                actions=[button("Cancel", ft.Icons.CLOSE, lambda e: page.pop_dialog()),
                         button("Save" if saving else "Load", ft.Icons.ARROW_FORWARD, confirm, True)],
                bgcolor=PANEL))
            return
        if saving:
            dest = await picker.save_file(
                file_name=f"{Path(model).stem if model else 'character'}.recipe.json",
                file_type=ft.FilePickerFileType.CUSTOM, allowed_extensions=["json"])
            if dest:
                save_recipe_to(dest)
            return
        files = await picker.pick_files(allow_multiple=False, file_type=ft.FilePickerFileType.CUSTOM,
                                        allowed_extensions=["json"])
        if files and files[0].path:
            load_recipe_from(files[0].path)

    def save_recipe_to(path):
        if not model:
            notify("Choose a source model before saving a recipe.")
            return
        try:
            recipe.save_recipe(Path(path), recipe.build_recipe(model, settings, export_cfg, idle=idle))
            notify(f"Saved recipe {Path(path).name}")
        except (ValueError, OSError) as exc:
            notify(str(exc))

    def load_recipe_from(path):
        nonlocal settings, export_cfg, idle
        try:
            rec = recipe.load_recipe(Path(path))
        except (ValueError, OSError) as exc:
            notify(str(exc))
            return
        if not rec.source or not Path(rec.source).is_file():
            notify(f"Recipe source not found at {rec.source}. Current project was left unchanged.")
            return
        settings = rec.settings
        export_cfg = rec.export
        idle = rec.idle
        idle_name.value = Path(idle).name if idle else "No replacement model"
        sync_chrome()
        persist()
        set_source(rec.source)
        notify(f"Loaded recipe {Path(path).name}")

    def show_result(rebuild_strip=False):
        sheet_view = view == "sheet" and last_sheet is not None and last_sheet_settings is not None
        playing_sheet = playing and last_sheet is not None and last_sheet_settings is not None
        use_sheet = sheet_view or playing_sheet
        display = last_sheet if use_sheet else result
        display_settings = last_sheet_settings if use_sheet else result_settings
        previewing = is_preview and not use_sheet
        if display is None or display_settings is None:
            return
        empty.visible = False
        sprite_image.visible = True
        viewport.content = viewer
        img = display if previewing or sheet_view else frame_at(display, display_settings, direction, frame)
        sprite_image.src = png_bytes(img)
        if view == "sheet":
            sprite_image.width = sprite_image.height = None
            sprite_image.expand = True
        else:
            sprite_image.expand = False
            sprite_image.width = img.width * zoom
            sprite_image.height = img.height * zoom
        count = 1 if previewing else display_settings.frames
        frame_label.value = f"FRAME  {frame + 1:02d} / {count:02d}"
        dimensions.value = f"{img.width} × {img.height} px  ·  RGBA"
        if rebuild_strip:
            direction_buttons.controls = []
            names = [n for n, _ in display_settings.direction_layout()]
            if previewing:
                names = direction_names(8)
            selected_direction = names.index(display_settings.start_direction) if previewing else direction
            for i, name in enumerate(names):
                direction_buttons.controls.append(ft.Container(
                    text(name if name != "angle0" else "Front", 10, INK if i == selected_direction else MUTED),
                    padding=ft.Padding(11, 8, 11, 8), border_radius=6,
                    bgcolor=ACCENT if i == selected_direction else CARD,
                    on_click=lambda e, i=i: select_direction(i)))
            timeline.controls = []
            for i in range(count):
                thumb = display if previewing else frame_at(display, display_settings, direction, i)
                timeline.controls.append(ft.Container(ft.Column([
                    ft.Image(src=png_bytes(thumb), width=42, height=54, fit=ft.BoxFit.CONTAIN,
                             filter_quality=ft.FilterQuality.NONE),
                    text(f"{i + 1:02d}", 9, MUTED),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
                    width=64, padding=6, border_radius=7,
                    bgcolor="#2a3325" if i == frame else CARD,
                    border=ft.Border.all(1, ACCENT if i == frame else BORDER),
                    on_click=lambda e, i=i: select_frame(i)))
        else:
            for i, tile in enumerate(timeline.controls):
                tile.border = ft.Border.all(1, ACCENT if i == frame else BORDER)
                tile.bgcolor = "#2a3325" if i == frame else CARD
        play_btn.disabled = busy or (previewing and last_sheet is None)
        export_btn.disabled = last_sheet is None or busy
        page.update()

    def select_direction(value):
        nonlocal direction, preview_facing
        if busy:
            return
        if is_preview and not (view == "sheet" and last_sheet is not None):
            preview_facing = direction_names(8)[value]
            start_render(True)  # bumps preview_seq so a pending debounce cannot race this view
        else:
            layout_settings = last_sheet_settings if last_sheet_settings is not None else result_settings
            direction = value
            if layout_settings is not None:
                preview_facing = layout_settings.direction_layout()[value][0]
            show_result(True)

    def select_frame(value):
        nonlocal frame
        frame = value
        show_result()

    def set_view(value):
        nonlocal view, playing
        view = value
        if view == "sheet":
            playing = False
            play_btn.icon = ft.Icons.PLAY_ARROW_ROUNDED
        sprite_tab.bgcolor = "#303a2a" if view == "sprite" else PANEL
        sheet_tab.bgcolor = "#303a2a" if view == "sheet" else PANEL
        show_result()
        page.run_task(reset_view)
        page.update()

    def set_zoom(value):
        nonlocal zoom
        zoom = int(value)
        show_result()
        page.run_task(reset_view)

    def set_fps(value):
        nonlocal fps
        fps = int(value)

    async def animate(generation):
        nonlocal frame, playing
        play_settings = last_sheet_settings or result_settings
        while playing and generation == play_generation and not busy and play_settings:
            await asyncio.sleep(1 / fps)
            play_settings = last_sheet_settings or result_settings
            if not playing or generation != play_generation or busy or not play_settings:
                break
            nxt = next_playback_frame(frame, play_settings.frames, play_settings.loop_mode)
            if nxt is None:
                playing = False
                play_btn.icon = ft.Icons.PLAY_ARROW_ROUNDED
                show_result()
                break
            frame = nxt
            show_result()

    def toggle_play(e):
        nonlocal playing, play_generation, frame
        play_generation += 1
        playing = not playing
        play_btn.icon = ft.Icons.PAUSE_ROUNDED if playing else ft.Icons.PLAY_ARROW_ROUNDED
        if playing:
            play_settings = last_sheet_settings or result_settings
            if (play_settings and play_settings.loop_mode == "oneshot"
                    and frame >= play_settings.frames - 1):
                frame = 0
            set_view("sprite")
            show_result(True)
            page.run_task(animate, play_generation)
        page.update()

    def cancel_render(e=None):
        nonlocal preview_seq, pending_preview, pending_sheet
        preview_seq, pending_preview, pending_sheet = user_cancel(preview_seq)
        cancel.set()

    def disconnected(e):
        nonlocal playing
        playing = False
        cancel_render()

    page.on_disconnect = disconnected

    def set_busy(value, lock_sidebar=False):
        nonlocal busy
        busy = value
        sidebar.disabled = value and lock_sidebar
        direction_buttons.disabled = value and lock_sidebar
        preview_btn.disabled = render_btn.disabled = value
        export_btn.disabled = value or last_sheet is None
        cancel_btn.visible = value
        progress.visible = value
        play_btn.disabled = value or (is_preview and last_sheet is None)

    def start_render(preview, seq=None):
        nonlocal playing, preview_seq, pending_preview, pending_sheet
        if preview and seq is None:
            preview_seq += 1
            seq = preview_seq
        if preview and seq is not None and seq != preview_seq:
            return
        if not preview:
            preview_seq += 1
            pending_preview = False
        if busy:
            if preview:
                pending_preview = True
            else:
                pending_sheet = True
                pending_preview = False
                cancel.set()
            return
        if not model:
            page.run_task(pick_source)
            return
        if not bpath:
            notify("Locate Blender using the connection control below.")
            return
        def input_error(control):
            if isinstance(control, ft.TextField) and control.error:
                return True
            children = list(getattr(control, "controls", None) or [])
            content = getattr(control, "content", None)
            if isinstance(content, ft.Control):
                children.append(content)
            return any(input_error(child) for child in children)

        if any(input_error(c) for c in (width_field, height_field, frames_field, inspector)):
            notify("Correct the highlighted settings before rendering.")
            return
        try:
            settings.validate()
        except (ValueError, OSError) as exc:
            notify(str(exc))
            return
        playing = False
        play_btn.icon = ft.Icons.PLAY_ARROW_ROUNDED
        cancel.clear()
        set_busy(True, lock_sidebar=not preview)
        progress.value = None
        notify("Preparing first sprite…" if preview else "Rendering directions and animation frames…")
        job = preview_settings(settings, preview_facing if preview_facing != "angle0" else "S") if preview else copy.deepcopy(settings)
        page.run_thread(render_job, preview, job, model, idle, bpath, seq if preview else None)

    def render_job(preview, job, source, idle_source, executable, seq):
        nonlocal result, result_settings, result_source, is_preview, stale, direction, frame, view_reset_pending
        nonlocal last_sheet, last_sheet_settings, last_sheet_source
        nonlocal pending_preview, pending_sheet

        def update(p):
            progress.value = p.current / p.total if p.total else None
            status.value = p.stage
            page.update()

        try:
            with tempfile.TemporaryDirectory(prefix="framemill-") as tmp:
                frames_dir = Path(tmp) / "frames"
                blender.render(executable, source, frames_dir, job, idle_path=idle_source,
                               preview=preview, on_progress=update, cancel=cancel)
                image = compositor.build_preview(frames_dir, job) if preview else compositor.build_sheet(frames_dir, job)
            if preview and seq is not None and seq != preview_seq:
                return
            result, result_settings, result_source = image, job, source
            result_detected.clear()
            if model == source:
                result_detected.update(detected)
            is_preview = preview
            if preview:
                stale = last_sheet is not None
                direction, frame = 0, 0
            else:
                last_sheet = image.copy()
                last_sheet_settings = job
                last_sheet_source = source
                last_sheet_detected.clear()
                last_sheet_detected.update(result_detected)
                stale, direction, frame = False, 0, 0
                names = [name for name, _ in job.direction_layout()]
                direction = names.index(preview_facing) if preview_facing in names else 0
            result_badge.value = ("CHANGES PENDING" if preview and last_sheet is not None
                                  else "SOURCE PREVIEW" if preview else "SHEET READY")
            status.value = ("Preview updated. Render sheet to replace the exportable sheet." if preview
                            else "Sheet ready. Review the motion, then choose Export sprite sheet.")
            persist()
            show_result(True)
            if view_reset_pending:
                page.run_task(reset_view)
                view_reset_pending = False
        except Exception as ex:  # noqa: BLE001  report worker failures in the UI
            status.value = str(ex) if cancel.is_set() else f"Render failed: {ex}"
        finally:
            action = after_render_job(
                cancelled=cancel.is_set(),
                pending_sheet=pending_sheet,
                pending_preview=pending_preview,
            )
            pending_preview = False
            pending_sheet = False
            set_busy(False)
            if action == "start_sheet":
                start_render(False)
            elif action == "start_preview" and model and bpath:
                start_render(True, seq=preview_seq)
            page.update()

    async def locate_blender():
        nonlocal bpath
        if page.web:
            notify("Set Blender in the desktop app, or put its executable on PATH, then restart this preview.")
            return
        files = await picker.pick_files(allow_multiple=False)
        if files and files[0].path:
            version = blender.blender_version(files[0].path)
            if not version or not version.startswith("Blender"):
                notify("That executable did not report a Blender version.")
                return
            bpath = files[0].path
            appconfig.set_blender_path(bpath)
            connection.value = version
            page.update()

    def open_help(e=None):
        nonlocal resize_dialog
        selected_id = help_content.articles_in("getting-started")[0].id
        query = ""
        nav = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, expand=True)
        article_col = ft.Column(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)
        heading = text("", 22, TEXT, ft.FontWeight.W_600)
        blurb = text("", 12, MUTED)

        def render_block(block):
            kind = block[0]
            if kind == "h":
                return text(block[1], 14, ACCENT, ft.FontWeight.W_600)
            if kind == "p":
                return text(block[1], 13, MUTED)
            if kind == "note":
                return ft.Container(text(block[1], 12, TEXT), padding=12, bgcolor="#2a3325",
                                    border=border(), border_radius=8)
            if kind == "li":
                return ft.Column([text(f"· {item}", 13, MUTED) for item in block[1]], spacing=4)
            if kind == "link":
                return ft.TextButton(block[1], url=block[2], style=ft.ButtonStyle(color=ACCENT))
            if kind == "kbd":
                return ft.Container(text(block[1], 12, ACCENT, font_family="monospace"),
                                    padding=10, bgcolor=CARD, border_radius=6)
            return text(str(block), 12, MUTED)

        def paint_nav():
            nav.controls.clear()
            if query.strip():
                hits = help_content.search(query)
                if not hits:
                    nav.controls.append(text("No matching articles.", 12, MUTED))
                    return
                for article in hits:
                    cat = next(c for c in help_content.CATEGORIES if c.id == article.category)
                    chosen = article.id == selected_id
                    nav.controls.append(ft.Container(
                        ft.Column([
                            text(article.title, 12, ACCENT if chosen else TEXT, ft.FontWeight.W_600),
                            text(cat.title, 10, MUTED),
                        ], spacing=2),
                        padding=10, border_radius=7,
                        bgcolor="#2a3325" if chosen else None,
                        on_click=lambda e, aid=article.id: show_article(aid)))
                return
            for cat in sorted(help_content.CATEGORIES, key=lambda c: c.order):
                nav.controls.append(caption(cat.title))
                for article in help_content.articles_in(cat.id):
                    chosen = article.id == selected_id
                    nav.controls.append(ft.Container(
                        text(article.title, 12, ACCENT if chosen else TEXT),
                        padding=ft.Padding(10, 8, 10, 8), border_radius=6,
                        bgcolor="#2a3325" if chosen else None,
                        on_click=lambda e, aid=article.id: show_article(aid)))

        def show_article(article_id):
            nonlocal selected_id
            selected_id = article_id
            article = help_content.article_by_id(article_id)
            heading.value = article.title
            cat = next(c for c in help_content.CATEGORIES if c.id == article.category)
            blurb.value = cat.blurb
            article_col.controls = [render_block(block) for block in article.body]
            paint_nav()
            page.update()

        def on_search(event):
            nonlocal query, selected_id
            query = event.control.value or ""
            hits = help_content.search(query)
            if hits and selected_id not in {article.id for article in hits}:
                show_article(hits[0].id)
                return
            paint_nav()
            page.update()

        search_field = field("Search help", "", on_search, hint_text="Find a control or topic")
        nav_panel = ft.Container(width=260, padding=ft.Padding(0, 0, 12, 0), content=nav,
                                 border=ft.Border(right=ft.BorderSide(1, BORDER)))
        content_side = ft.Column([heading, blurb, article_col], spacing=10, expand=True)
        body = ft.Container()

        def fit_help():
            width, height = page.width or 1440, page.height or 940
            body.width = min(980, max(320, width - 80))
            body.height = min(640, max(280, height - 160))
            wide = width >= 900
            nav_panel.visible = wide
            nav_panel.width = 260 if wide else 0
            body.content = ft.Row(
                [nav_panel, content_side] if wide else [content_side],
                spacing=16, expand=True,
                vertical_alignment=ft.CrossAxisAlignment.STRETCH)

        dialog = ft.AlertDialog(
            bgcolor=PANEL, shape=ft.RoundedRectangleBorder(radius=16),
            title=ft.Row([
                text("Help", 22, TEXT, ft.FontWeight.W_600),
                ft.Container(search_field, expand=True),
            ], spacing=16),
            content=body,
            actions=[button("Back to workspace", ft.Icons.ARROW_BACK, lambda ev: page.pop_dialog())])
        resize_dialog = fit_help
        fit_help()
        show_article(selected_id)
        page.show_dialog(dialog)

    def open_export(e):
        nonlocal playing, resize_dialog, refresh_open_export
        if last_sheet is None or last_sheet_settings is None:
            return
        playing = False
        play_btn.icon = ft.Icons.PLAY_ARROW_ROUNDED
        draft = copy.deepcopy(export_cfg)
        selected_preset = next((k for k, preset in EXPORT_PRESETS.items()
                                if preset.config == draft), "")
        original = last_sheet.copy()
        export_image = ft.Image(src=png_bytes(original), fit=ft.BoxFit.CONTAIN, expand=True,
                               filter_quality=ft.FilterQuality.NONE)
        export_info = text("", 11, MUTED)
        export_error = text("", 11, "#f1ac91")
        palette_note = text(Path(draft.palette_path).name if draft.palette_path else "No palette selected", 11, MUTED)
        export_controls = ft.Column(spacing=14, scroll=ft.ScrollMode.AUTO, expand=True,
                                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        dialog = None

        def normalize(capability_changed=False):
            export.apply_export_capabilities(draft, capability_changed=capability_changed)

        def refresh():
            try:
                processed = export.process(original, draft)
                export_image.src = png_bytes(processed)
                export_info.value = f"{original.width} × {original.height} px  ·  {draft.depth}-bit {draft.format.upper()}"
                export_error.value = ""
                save_btn.disabled = False
            except (ValueError, OSError, IndexError) as exc:
                export_error.value = str(exc)
                save_btn.disabled = True
            page.update()

        def change_export(name, value, rebuild=False):
            nonlocal selected_preset
            selected_preset = ""
            export_controls.controls[1].value = ""
            setattr(draft, name, value)
            normalize(capability_changed=name in {"format", "depth"})
            if rebuild:
                build_export_controls()
            refresh()

        async def choose_palette():
            if page.web:
                export_error.value = "Enter the palette file path below."
                page.update()
                return
            files = await picker.pick_files(file_type=ft.FilePickerFileType.CUSTOM,
                                            allowed_extensions=["pal", "gpl", "hex", "txt",
                                                                "bmp", "png", "gif"])
            if files and files[0].path:
                draft.palette_path = files[0].path
                palette_note.value = files[0].name
                build_export_controls()
                refresh()

        def fixed_changed(e):
            try:
                draft.fixed_palette = [export.hex_to_rgb(v.strip()) for v in e.control.value.replace(",", " ").split()]
                refresh()
            except ValueError:
                export_error.value = "Enter colours as #RRGGBB separated by spaces."
                save_btn.disabled = True
                page.update()

        def load_preset(key):
            nonlocal draft, selected_preset
            if not key:
                return
            selected_preset = key
            draft = copy.deepcopy(EXPORT_PRESETS[key].config)
            build_export_controls()
            refresh()

        def build_export_controls():
            indexed = draft.depth == 8
            depths = [(32, "32-bit · RGBA"), (24, "24-bit · RGB"), (8, "8-bit · Indexed")]
            if draft.format == "bmp":
                depths = depths[1:]
            allowed = export.valid_backgrounds(draft.format, draft.depth)
            if draft.background not in allowed:
                draft.background = allowed[0]
            backgrounds = [(key, export.BACKGROUND_LABELS[key]) for key in allowed]
            export_controls.controls = [
                caption("Target preset"),
                dropdown("Output preset", selected_preset,
                         [("", "Custom output")] + [(k, v.label) for k, v in EXPORT_PRESETS.items()], load_preset),
                ft.Row([
                    dropdown("Format", draft.format, [(v, v.upper()) for v in ("png", "tga", "bmp")],
                             lambda v: change_export("format", v, True), expand=True),
                    dropdown("Colour depth", draft.depth, depths,
                             lambda v: change_export("depth", int(v), True), expand=True),
                ], spacing=10),
                dropdown("Background", draft.background, backgrounds,
                         lambda v: change_export("background", v, True)),
            ]
            if draft.background == "solid":
                export_controls.controls.append(field("Background colour", draft.solid_color,
                    lambda e: change_export("solid_color", e.control.value)))
            export_controls.controls += [
                ft.Divider(color=BORDER), caption("Character edges"),
                dropdown("Alpha treatment", draft.alpha_mode,
                         [("hard", "Hard · 1-bit cutout")] if draft.background == "magic_pink" else
                         [("soft", "Soft · anti-aliased"), ("hard", "Hard · 1-bit cutout")],
                         lambda v: change_export("alpha_mode", v, True)),
                text(f"Alpha cutoff · {draft.alpha_cutoff}", 11, MUTED),
                ft.Slider(value=draft.alpha_cutoff, min=1, max=255, divisions=254, label="{value}",
                          active_color=ACCENT, disabled=draft.alpha_mode != "hard",
                          on_change_end=lambda e: change_export("alpha_cutoff", int(e.control.value), True)),
                dropdown("Edge bleed", draft.dilate, [(n, "Off" if n == 0 else f"{n} pixel" if n == 1 else f"{n} pixels") for n in (0, 1, 2, 4, 8)],
                         lambda v: change_export("dilate", int(v))),
                text("Bleed extends RGB into transparent pixels without enlarging the silhouette. It is not dithering.", 11, MUTED),
                ft.Divider(color=BORDER), caption("Indexed colour"),
                dropdown("Dithering", draft.dither,
                         [("none", "None · clean colours"), ("ordered", "Ordered · Bayer"), ("floyd", "Floyd-Steinberg")],
                         lambda v: change_export("dither", v), disabled=not indexed),
                dropdown("Palette", draft.palette_source,
                         [("auto", "Adaptive · from this sheet"),
                          ("file", "Master palette (share a scene palette)"),
                          ("fixed", "Custom fixed colours")],
                         lambda v: change_export("palette_source", v, True), disabled=not indexed),
            ]
            if indexed and draft.palette_source == "auto":
                export_controls.controls.append(dropdown("Maximum colours", draft.palette_colors,
                    [(n, str(n)) for n in sorted({2, 4, 8, 16, 32, 64, 128, 256, draft.palette_colors})],
                    lambda v: change_export("palette_colors", int(v))))
            if indexed and draft.palette_source == "file":
                export_controls.controls += [
                    text("For DOS: load the scene's master palette (for example BG_00.BMP) so this "
                         "sheet shares the scene's global 256-colour palette. Transparent pixels "
                         "use the palette's magic-pink index.", 11, MUTED),
                    button("Load palette (BMP / PNG / PAL / GPL / HEX)", ft.Icons.FOLDER_OPEN,
                           lambda e: page.run_task(choose_palette)),
                    field("Palette path", draft.palette_path or "", lambda e: change_export("palette_path", e.control.value)),
                    palette_note]
            if indexed and draft.palette_source == "fixed":
                export_controls.controls.append(field("Fixed colours · #RRGGBB", " ".join(
                    f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}" for c in draft.fixed_palette or []), fixed_changed,
                    multiline=True, min_lines=2, max_lines=4))
            export_controls.controls += [
                ft.Divider(color=BORDER), caption("Animation metadata"),
                ft.Switch(label="Write JSON sidecar", value=draft.write_metadata, active_color=ACCENT,
                          on_change=lambda e: change_export("write_metadata", e.control.value)),
                text("Optional sidecar: cell layout, sample times, source vs playback FPS, loop mode and pivot. "
                     "It does not change the image.", 11, MUTED),
            ]
            if not indexed:
                export_controls.controls.append(text("Choose 8-bit indexed to enable palettes and dithering.", 11, FAINT))

        async def save_output(e):
            nonlocal export_cfg
            try:
                export.validate_config(draft)
                export_source = last_sheet_source or result_source
                filename = f"{Path(export_source).stem}_sheet.{draft.format}"
                meta = None
                if draft.write_metadata and last_sheet_settings is not None:
                    snap = last_sheet_detected or detected
                    meta = recipe.animation_metadata(
                        last_sheet_settings, clip_name=Path(export_source).name,
                        source_start=snap.get("frame_start"),
                        source_end=snap.get("frame_end"),
                        source_fps=snap.get("fps") or None,
                        playback_fps=fps,
                        replacement_used=bool(idle),
                        replacement_name=Path(idle).name if idle else None,
                    )
                if page.web:
                    with tempfile.TemporaryDirectory() as tmp:
                        p = export.save(original, Path(tmp) / filename, draft)
                        await picker.save_file(file_name=filename, src_bytes=p.read_bytes())
                        if meta is not None:
                            side = recipe.write_metadata(p, meta)
                            await picker.save_file(file_name=side.name, src_bytes=side.read_bytes())
                    message = f"Export prepared: {filename}"
                else:
                    destination = await picker.save_file(file_name=filename,
                        initial_directory=str(Path(export_source).parent),
                        file_type=ft.FilePickerFileType.CUSTOM, allowed_extensions=[draft.format])
                    if not destination:
                        return
                    p = export.save(original, Path(destination), draft)
                    message = f"Exported {p.name} → {p.parent}"
                    if meta is not None:
                        side = recipe.write_metadata(p, meta)
                        message += f" · {side.name}"
                export_cfg = copy.deepcopy(draft)
                persist()
                page.pop_dialog()
                notify(message)
            except Exception as exc:  # noqa: BLE001  keep export errors in the dialog
                export_error.value = f"Export failed: {exc}"
                page.update()

        save_btn = button("Export sprite sheet", ft.Icons.DOWNLOAD_ROUNDED, save_output, True)
        build_export_controls()
        preview_panel = ft.Container(expand=5, padding=18, bgcolor=BG, border_radius=10,
            content=ft.Column([caption("Export preview"),
                ft.Container(export_image, expand=True, alignment=CENTER,
                             image=ft.DecorationImage(src="checker.png", repeat=ft.ImageRepeat.REPEAT)),
                export_info], spacing=10, expand=True,
                              horizontal_alignment=ft.CrossAxisAlignment.STRETCH))
        settings_panel = ft.Container(expand=4, padding=ft.Padding(0, 0, 14, 0),
                                      content=export_controls)
        dialog_body = ft.Container()
        dialog = ft.AlertDialog(bgcolor=PANEL, shape=ft.RoundedRectangleBorder(radius=16),
            title=ft.Row([ft.Column([text("Ready for your game.", 24, TEXT, ft.FontWeight.W_600),
                                    text("Fine-tune the output. Your render stays untouched.", 12, MUTED)], spacing=6, expand=True), ft.IconButton(ft.Icons.CLOSE, on_click=lambda e: page.pop_dialog())]),
            content=dialog_body,
            actions=[export_error, button("Cancel", ft.Icons.CLOSE, lambda e: page.pop_dialog()), save_btn])
        def fit_export_dialog():
            width, height = page.width or 1440, page.height or 940
            wide = width >= 1100
            dialog_body.width = min(940, max(320, width - 96))
            dialog_body.height = min(570, max(280, height - 220))
            preview_panel.expand = 5 if wide else False
            preview_panel.height = None if wide else 140
            preview_panel.width = None
            settings_panel.expand = 4 if wide else True
            settings_panel.width = None
            settings_panel.padding = ft.Padding(0, 0, 14, 0) if wide else ft.Padding(0, 0, 0, 0)
            if wide:
                dialog_body.content = ft.Row(
                    [preview_panel, settings_panel], spacing=16, expand=True,
                    vertical_alignment=ft.CrossAxisAlignment.STRETCH)
            else:
                dialog_body.content = ft.Column(
                    [preview_panel, settings_panel], spacing=16, expand=True,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        def sync_draft_from_cfg():
            nonlocal draft, selected_preset
            draft = copy.deepcopy(export_cfg)
            selected_preset = next((k for k, preset in EXPORT_PRESETS.items()
                                    if preset.config == draft), "")
            build_export_controls()
            refresh()

        refresh_open_export = sync_draft_from_cfg
        resize_dialog = fit_export_dialog
        fit_export_dialog()
        page.show_dialog(dialog)
        refresh()

    # Workspace chrome
    connection = text("Blender connected" if bpath else "Locate Blender", 11, ACCENT if bpath else "#f1ac91")
    width_field = field("Width · px", settings.frame_width, lambda e: integer("frame_width", e), expand=True)
    height_field = field("Height · px", settings.frame_height, lambda e: integer("frame_height", e), expand=True)
    frames_field = field("Frames", settings.frames, lambda e: integer("frames", e), expand=True)
    angles_dd = dropdown("Directions", settings.angles, [(n, str(n)) for n in (1, 4, 8, 16)],
                         angles_changed, expand=True)
    appearance_dd = dropdown("Appearance preset", appearance_key(),
        [(k, v.label) for k, v in PRESETS.items()] + [("custom", "Custom appearance")], choose_preset)
    sidebar = ft.Container(width=340, bgcolor=PANEL, padding=ft.Padding(20, 20, 6, 20),
        border=ft.Border(right=ft.BorderSide(1, BORDER)), content=ft.Column([
          ft.Container(padding=ft.Padding(0, 0, 14, 8), content=ft.Column([
            section("01 / Source", [ft.Container(ft.Row([
                ft.Icon(ft.Icons.VIEW_IN_AR_OUTLINED, size=24, color=ACCENT),
                ft.Column([model_name, model_detail], spacing=4, expand=True),
                ft.IconButton(ft.Icons.FOLDER_OPEN_OUTLINED, icon_size=18, icon_color=MUTED,
                              tooltip="Choose model", on_click=lambda e: page.run_task(pick_source)),
            ], spacing=12), bgcolor=CARD, padding=12, border_radius=9),
                source_clip,
                ft.Row([
                    button("Load recipe", ft.Icons.FOLDER_OPEN, lambda e: page.run_task(pick_recipe, False), expand=True),
                    button("Save recipe", ft.Icons.SAVE_OUTLINED, lambda e: page.run_task(pick_recipe, True), expand=True),
                ], spacing=8),
                appearance_dd]),
            ft.Divider(color=BORDER, height=1),
            section("02 / Sprite geometry", [ft.Row([width_field, height_field], spacing=10),
                ft.Row([angles_dd, frames_field], spacing=10), geometry]),
            ft.Divider(color=BORDER, height=1), studio_panel, inspector,
          ], spacing=18, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)),
        ], scroll=ft.ScrollMode.AUTO, expand=True,
           horizontal_alignment=ft.CrossAxisAlignment.STRETCH))
    preview_btn = button("Preview", ft.Icons.VISIBILITY_OUTLINED, lambda e: start_render(True))
    render_btn = button("Render sheet", ft.Icons.GRID_VIEW_ROUNDED, lambda e: start_render(False))
    export_btn = button("Export sprite sheet", ft.Icons.NORTH_EAST, open_export, True, disabled=True)
    cancel_btn = button("Cancel render", ft.Icons.CLOSE, cancel_render, visible=False)
    play_btn = ft.IconButton(ft.Icons.PLAY_ARROW_ROUNDED, icon_color=ACCENT, bgcolor="#303a2a",
                             on_click=toggle_play, disabled=True, tooltip="Play / pause animation")
    sprite_tab = ft.Container(text("Sprite", 11), bgcolor="#303a2a", padding=ft.Padding(15, 9, 15, 9),
                              border_radius=6, on_click=lambda e: set_view("sprite"))
    sheet_tab = ft.Container(text("Sheet", 11), bgcolor=PANEL, padding=ft.Padding(15, 9, 15, 9),
                             border_radius=6, on_click=lambda e: set_view("sheet"))
    workspace = ft.Container(expand=True, padding=ft.Padding(28, 25, 28, 18), content=ft.Column([
        ft.ResponsiveRow([
            ft.Column([result_badge, headline, subtitle], spacing=7, col={"xs": 12, "wide": 7}),
            ft.Row([preview_btn, render_btn], spacing=8,
                   alignment=ft.MainAxisAlignment.END, col={"xs": 12, "wide": 5}),
        ], breakpoints={"xs": 0, "wide": 1200}, spacing=12, run_spacing=10),
        ft.Row([ft.Row([sprite_tab, sheet_tab], spacing=3, tight=True),
                ft.Row([ft.IconButton(ft.Icons.CENTER_FOCUS_STRONG, icon_size=18, icon_color=MUTED,
                              tooltip="Recenter and reset gesture zoom", on_click=lambda e: page.run_task(reset_view)),
                text("BASE SIZE", 9, FAINT),
                dropdown(None, zoom, [(n, f"{n * 100}%") for n in (1, 2, 3, 4, 6)], set_zoom, width=100),
                ft.IconButton(ft.Icons.CONTRAST, icon_size=18, icon_color=MUTED, tooltip="Toggle checkerboard",
                              on_click=lambda e: toggle_checker())], spacing=6, tight=True)],
               wrap=True, spacing=10, run_spacing=8,
               alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        viewport,
        text("Drag to pan · scroll / pinch to zoom · facing buttons change the view only", 10, FAINT),
        ft.Row([direction_buttons, dimensions], spacing=10),
        ft.Container(bgcolor=PANEL, border=border(), border_radius=10, padding=14,
                     content=ft.Column([
                         ft.Row([play_btn, text("ANIMATION", 10, MUTED),
                                 dropdown(None, fps, [(n, f"{n} fps") for n in (4, 6, 8, 12, 16, 24)], set_fps, width=100),
                                 ft.Container(expand=True), frame_label], spacing=10),
                         timeline,
                     ], spacing=10)),
    ], spacing=16, expand=True))

    def toggle_checker():
        viewport.image = None if viewport.image else ft.DecorationImage(src="checker.png", repeat=ft.ImageRepeat.REPEAT)
        page.update()

    breadcrumb = ft.Row([text("/", 18, FAINT), text("Sprite workspace", 12, MUTED)], tight=True)
    guide_btn = ft.TextButton("Help", icon=ft.Icons.HELP_OUTLINE, on_click=open_help,
                              style=ft.ButtonStyle(color=MUTED))
    topbar = ft.Container(padding=ft.Padding(22, 14, 22, 14), bgcolor=PANEL,
        border=ft.Border(bottom=ft.BorderSide(1, BORDER)), content=ft.Row([
            ft.Container(ft.Icon(ft.Icons.FILTER_FRAMES_OUTLINED, size=21, color=INK),
                         bgcolor=ACCENT, padding=8, border_radius=8),
            text("framemill", 20, TEXT, ft.FontWeight.W_600),
            breadcrumb,
            ft.Container(expand=True),
            guide_btn, export_btn,
        ], spacing=12))
    reset_btn = ft.TextButton("Reset to defaults", icon=ft.Icons.RESTART_ALT, on_click=confirm_reset,
                              style=ft.ButtonStyle(color=MUTED, text_style=ft.TextStyle(size=11)))
    footer = ft.Container(padding=ft.Padding(20, 8, 20, 8), bgcolor=PANEL,
        border=ft.Border(top=ft.BorderSide(1, BORDER)), content=ft.Row([
            ft.Container(ft.Row([ft.Icon(ft.Icons.CIRCLE, size=7, color=ACCENT if bpath else "#f1ac91"), connection], spacing=7),
                         on_click=lambda e: page.run_task(locate_blender), tooltip=bpath or "Locate Blender"),
            reset_btn,
            ft.Container(width=12), ft.Container(status, expand=True), cancel_btn,
            text("LOCAL RENDERING", 9, FAINT),
        ], spacing=10))
    def fit_window(e=None):
        width, height = page.width or 1440, page.height or 940
        breadcrumb.visible = width >= 1200
        guide_btn.visible = width >= 1000
        empty_icon.visible = height >= 850 and width >= 1000
        empty_tagline.visible = height >= 950
        workspace.padding = ft.Padding(16, 14, 16, 12) if width < 1100 else (
            ft.Padding(18, 18, 18, 14) if width < 1200 else ft.Padding(28, 25, 28, 18))
        if resize_dialog is not None:
            resize_dialog()
        if e is not None:
            page.update()

    page.on_resize = fit_window
    fit_window()
    update_geometry()
    build_inspector()
    page.add(ft.Column([topbar, ft.Row([sidebar, workspace], expand=True, spacing=0), progress, footer],
                       spacing=0, expand=True))
    if setting_warnings:
        notify("Restored usable defaults from saved settings. " + " ".join(setting_warnings[:3]))


def run() -> None:
    web = os.environ.get("FRAMEMILL_WEB") == "1"
    if web:
        os.environ["FLET_FORCE_WEB_SERVER"] = "true"
    ft.run(main, assets_dir=str(Path(__file__).parent / "assets"),
           view=ft.AppView.WEB_BROWSER if web else ft.AppView.FLET_APP,
           host="127.0.0.1", port=8000 if web else 0)


if __name__ == "__main__":
    run()
