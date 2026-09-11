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

from . import appconfig, blender, compositor, export, guide
from .export import DEFAULT_EXPORT, EXPORT_PRESETS, ExportConfig
from .settings import PRESETS, RenderSettings, direction_names

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


def main(page: ft.Page) -> None:
    page.title = "Framemill — Sprite workspace"
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = ft.Theme(color_scheme_seed=ACCENT, font_family="Inter", use_material3=True)
    page.bgcolor = BG
    page.padding = 0
    page.window.width, page.window.height = 1440, 940
    page.window.min_width, page.window.min_height = 1050, 740
    saved = appconfig.load()
    settings = RenderSettings.from_dict(saved.get("render_settings", {}))
    cfg_fields = ExportConfig.__dataclass_fields__
    export_cfg = ExportConfig(**{k: v for k, v in saved.get("export_settings", {}).items()
                                 if k in cfg_fields}) if saved.get("export_settings") else copy.deepcopy(
                                     EXPORT_PRESETS[DEFAULT_EXPORT].config)
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
                                        side=ft.BorderSide(0 if primary else 1, BORDER)), **kwargs)

    def field(label, value, on_change, width=None, **kwargs):
        return ft.TextField(label=label, value=str(value), on_change=on_change, width=width,
                            text_size=12, dense=True, filled=True, fill_color=BG,
                            border_color=BORDER, focused_border_color=ACCENT,
                            border_radius=7, **kwargs)

    def dropdown(label, value, options, callback, width=None, **kwargs):
        return ft.Dropdown(label=label, value=str(value), width=width if width is not None else (None if kwargs.get("expand") else 270), text_size=12,
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
    idle_name = text("No replacement model", 11, MUTED, expand=True,
                     no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS)
    headline = text("Your next character starts here.", 24, TEXT, ft.FontWeight.W_600)
    subtitle = text("A 3D source. Every direction. Ready for your game.", 12, MUTED)
    result_badge = text("WORKSPACE", 10, ACCENT, ft.FontWeight.W_600)
    dimensions = text("—", 11, MUTED)
    frame_label = text("FRAME  — / —", 10, MUTED)
    direction_buttons = ft.Row(spacing=5, wrap=True)
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

    empty = ft.Column([
        ft.Container(ft.Icon(ft.Icons.VIEW_IN_AR_OUTLINED, size=42, color=ACCENT),
                     padding=26, bgcolor="#242e23", border_radius=24),
        text("From model to motion", 25, TEXT, ft.FontWeight.W_600),
        text("Load an animated model to see your first sprite.\nFine-tune the look, build the sheet, then export.",
             13, MUTED, text_align=ft.TextAlign.CENTER),
        button("Choose a model", ft.Icons.ADD, lambda e: page.run_task(pick_source), True),
        text("RENDERED WITH BLENDER  /  BUILT FOR GAMES", 9, FAINT),
    ], spacing=20, alignment=ft.MainAxisAlignment.CENTER,
       horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    viewport = ft.Container(content=empty, expand=True, alignment=CENTER, bgcolor="#151919",
        image=ft.DecorationImage(src="checker.png", repeat=ft.ImageRepeat.REPEAT),
        border=border(), border_radius=12, clip_behavior=ft.ClipBehavior.HARD_EDGE)

    def notify(message):
        status.value = message
        page.update()

    def mark_changed():
        nonlocal stale, playing
        stale = result is not None
        playing = False
        play_btn.icon = ft.Icons.PLAY_ARROW_ROUNDED
        result_badge.value = "CHANGES PENDING" if stale else "WORKSPACE"
        appearance_dd.value = appearance_key()
        persist()
        update_geometry()
        page.update()

    def change(name, value):
        setattr(settings, name, value)
        mark_changed()

    def integer(name, event):
        try:
            value = int(event.control.value)
            maximum = 64 if name == "frames" else 1024
            if not 1 <= value <= maximum:
                raise ValueError
            event.control.error = None
            change(name, value)
        except ValueError:
            event.control.error = f"Enter 1–{maximum}"
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
        return ft.Column([caption(label), *controls], spacing=12)

    def update_geometry():
        w, h = settings.frame_width, settings.frame_height
        sw, sh = ((w * settings.angles, h * settings.frames) if settings.layout_axis == "cols"
                  else (w * settings.frames, h * settings.angles))
        geometry.value = f"{sw} × {sh} px sheet  ·  {settings.angles * settings.frames} sprites"
        axis = "Row" if settings.layout_axis == "rows" else "Column"
        names = [name if name != "angle0" else "Front" for name, _ in settings.direction_layout()]
        layout_order.value = f"{axis} order: " + " → ".join(names)

    geometry = text("", 10, ACCENT)
    layout_order = text("", 11, ACCENT)
    inspector = ft.Column(spacing=20, scroll=ft.ScrollMode.AUTO, expand=True)
    inspector_tab = "look"
    tab_buttons = ft.Row(spacing=4)

    def build_inspector():
        tab_buttons.controls = []
        for key, title in (("look", "Appearance"), ("motion", "Layout & timing")):
            def select(e, key=key):
                nonlocal inspector_tab
                inspector_tab = key
                build_inspector()
                page.update()
            tab_buttons.controls.append(ft.Container(text(title, 11, ACCENT if key == inspector_tab else MUTED),
                padding=ft.Padding(12, 10, 12, 10), border_radius=6,
                bgcolor="#2a3325" if key == inspector_tab else PANEL, on_click=select, expand=True))
        if inspector_tab == "look":
            inspector.controls = [
                section("Camera", [slider("Elevation · 90° is level", "camera_pitch", 30, 120, 90, "°"),
                                   slider("Framing", "ortho_scale_mult", .5, 4, 70, "×"),
                                   slider("Orbit distance", "camera_distance", .5, 10, 95)]),
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
                    text("Direction names assume your model faces the front camera. Ordering varies by engine.", 11, MUTED)]),
                section("Animation cycle", [slider("First pose / phase", "phase_offset", 0, 1, 100),
                    ft.Switch(label="Reverse playback", value=settings.reverse, active_color=ACCENT,
                              on_change=lambda e: change("reverse", e.control.value)),
                    text("Evenly samples the source action as a loop; the final endpoint is excluded. "
                         "Phase wraps within that range. See Quick guide for one-shot limits.", 11, MUTED)]),
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
        mark_changed()

    def clear_idle(e=None):
        nonlocal idle
        idle = None
        idle_name.value = "No replacement model"
        mark_changed()

    async def pick_source(for_idle=False):
        if busy:
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
        start_render(True)

    def show_result(rebuild_strip=False):
        if result is None or result_settings is None:
            return
        empty.visible = False
        sprite_image.visible = True
        viewport.content = viewer
        img = result if view == "sheet" or is_preview else frame_at(result, result_settings, direction, frame)
        sprite_image.src = png_bytes(img)
        if view == "sheet":
            sprite_image.width = sprite_image.height = None
            sprite_image.expand = True
        else:
            sprite_image.expand = False
            sprite_image.width = img.width * zoom
            sprite_image.height = img.height * zoom
        count = 1 if is_preview else result_settings.frames
        frame_label.value = f"FRAME  {frame + 1:02d} / {count:02d}"
        dimensions.value = f"{img.width} × {img.height} px  ·  RGBA"
        if rebuild_strip:
            direction_buttons.controls = []
            names = [n for n, _ in result_settings.direction_layout()]
            if is_preview:
                names = direction_names(8)
            selected_direction = names.index(result_settings.start_direction) if is_preview else direction
            for i, name in enumerate(names):
                direction_buttons.controls.append(ft.Container(
                    text(name if name != "angle0" else "Front", 10, INK if i == selected_direction else MUTED),
                    padding=ft.Padding(11, 8, 11, 8), border_radius=6,
                    bgcolor=ACCENT if i == selected_direction else CARD,
                    on_click=lambda e, i=i: select_direction(i)))
            timeline.controls = []
            for i in range(count):
                thumb = result if is_preview else frame_at(result, result_settings, direction, i)
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
        play_btn.disabled = is_preview or busy
        export_btn.disabled = is_preview or busy
        page.update()

    def select_direction(value):
        nonlocal direction, preview_facing
        if busy:
            return
        if is_preview:
            preview_facing = direction_names(8)[value]
            start_render(True)
        else:
            direction = value
            preview_facing = result_settings.direction_layout()[value][0]
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
        nonlocal frame
        while playing and generation == play_generation and not busy and result_settings:
            await asyncio.sleep(1 / fps)
            if not playing or generation != play_generation or busy or not result_settings:
                break
            frame = (frame + 1) % result_settings.frames
            show_result()

    def toggle_play(e):
        nonlocal playing, play_generation
        play_generation += 1
        playing = not playing
        play_btn.icon = ft.Icons.PAUSE_ROUNDED if playing else ft.Icons.PLAY_ARROW_ROUNDED
        if playing:
            set_view("sprite")
            page.run_task(animate, play_generation)
        page.update()

    def disconnected(e):
        nonlocal playing
        playing = False
        cancel.set()

    page.on_disconnect = disconnected

    def set_busy(value):
        nonlocal busy
        busy = value
        sidebar.disabled = value
        direction_buttons.disabled = value
        preview_btn.disabled = render_btn.disabled = value
        export_btn.disabled = value or result is None or is_preview
        cancel_btn.visible = value
        progress.visible = value
        play_btn.disabled = value or is_preview

    def start_render(preview):
        nonlocal playing
        if busy:
            return
        if not model:
            page.run_task(pick_source)
            return
        if not bpath:
            notify("Locate Blender using the connection control below.")
            return
        if any(c.error for c in (width_field, height_field, frames_field)):
            notify("Correct the sprite dimensions or frame count before rendering.")
            return
        playing = False
        play_btn.icon = ft.Icons.PLAY_ARROW_ROUNDED
        cancel.clear()
        set_busy(True)
        progress.value = None
        notify("Preparing first sprite…" if preview else "Rendering directions and animation frames…")
        job = preview_settings(settings, preview_facing if preview_facing != "angle0" else "S") if preview else copy.deepcopy(settings)
        page.run_thread(render_job, preview, job, model, idle, bpath)

    def render_job(preview, job, source, idle_source, executable):
        nonlocal result, result_settings, result_source, is_preview, stale, direction, frame, view_reset_pending

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
            result, result_settings, result_source = image, job, source
            is_preview, stale, direction, frame = preview, False, 0, 0
            if not preview:
                names = [name for name, _ in job.direction_layout()]
                direction = names.index(preview_facing) if preview_facing in names else 0
            result_badge.value = "SOURCE PREVIEW" if preview else "SHEET READY"
            status.value = ("Preview ready. Facing buttons request another view; sheet order stays unchanged." if preview
                            else "Sheet ready. Review the motion, then choose Export sprite sheet.")
            persist()
            show_result(True)
            if view_reset_pending:
                page.run_task(reset_view)
                view_reset_pending = False
        except Exception as ex:  # noqa: BLE001 — report worker failures in the UI
            status.value = str(ex) if cancel.is_set() else f"Render failed: {ex}"
        finally:
            set_busy(False)
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

    def open_guide(e):
        page.show_dialog(ft.AlertDialog(title=text("From model to sprite", 22), bgcolor=PANEL,
            content=ft.Container(width=620, height=430, content=ft.Column([
                *[ft.Column([
                    text(step.title, 13, ACCENT), text(step.body, 12, MUTED),
                    *([ft.TextButton(step.action, url=step.url,
                                    style=ft.ButtonStyle(color=ACCENT))]
                      if step.action and step.url else []),
                ], spacing=6) for step in guide.WORKFLOW_STEPS + guide.ANIMATION_STEPS + guide.SETUP_STEPS
                   + guide.TROUBLESHOOTING_STEPS],
            ], spacing=16, scroll=ft.ScrollMode.AUTO)),
            actions=[button("Back to workspace", ft.Icons.ARROW_BACK, lambda e: page.pop_dialog())]))

    def open_export(e):
        nonlocal playing
        if result is None or is_preview:
            return
        playing = False
        play_btn.icon = ft.Icons.PLAY_ARROW_ROUNDED
        draft = copy.deepcopy(export_cfg)
        selected_preset = next((k for k, preset in EXPORT_PRESETS.items()
                                if preset.config == draft), "")
        original = result.copy()
        export_image = ft.Image(src=png_bytes(original), fit=ft.BoxFit.CONTAIN, expand=True,
                               filter_quality=ft.FilterQuality.NONE)
        export_info = text("", 11, MUTED)
        export_error = text("", 11, "#f1ac91")
        palette_note = text(Path(draft.palette_path).name if draft.palette_path else "No palette selected", 11, MUTED)
        export_controls = ft.Column(spacing=14, scroll=ft.ScrollMode.AUTO)
        dialog = None

        def normalize():
            if draft.format == "bmp" and draft.depth == 32:
                draft.depth = 24
            if (draft.depth != 32 or draft.format == "bmp") and draft.background == "transparent":
                draft.background = "magic_pink"
            if draft.background == "magic_pink":
                draft.alpha_mode = "hard"

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
            normalize()
            if rebuild:
                build_export_controls()
            refresh()

        async def choose_palette():
            if page.web:
                export_error.value = "Enter the palette file path below."
                page.update()
                return
            files = await picker.pick_files(file_type=ft.FilePickerFileType.CUSTOM,
                                            allowed_extensions=["pal", "gpl", "hex", "txt"])
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
            backgrounds = [("magic_pink", "Magic pink · colour key"), ("solid", "Solid colour")]
            if draft.depth == 32 and draft.format != "bmp":
                backgrounds.insert(0, ("transparent", "Transparent · alpha"))
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
                         [("none", "None · clean colours"), ("ordered", "Ordered · Bayer"), ("floyd", "Floyd–Steinberg")],
                         lambda v: change_export("dither", v), disabled=not indexed),
                dropdown("Palette", draft.palette_source,
                         [("auto", "Adaptive · from this sheet"), ("file", "Load a palette file"), ("fixed", "Custom fixed colours")],
                         lambda v: change_export("palette_source", v, True), disabled=not indexed),
            ]
            if indexed and draft.palette_source == "auto":
                export_controls.controls.append(dropdown("Maximum colours", draft.palette_colors,
                    [(n, str(n)) for n in sorted({2, 4, 8, 16, 32, 64, 128, 256, draft.palette_colors})],
                    lambda v: change_export("palette_colors", int(v))))
            if indexed and draft.palette_source == "file":
                export_controls.controls += [button("Load .pal / .gpl / .hex", ft.Icons.FOLDER_OPEN,
                                                     lambda e: page.run_task(choose_palette)),
                    field("Palette path", draft.palette_path or "", lambda e: change_export("palette_path", e.control.value)),
                    palette_note]
            if indexed and draft.palette_source == "fixed":
                export_controls.controls.append(field("Fixed colours · #RRGGBB", " ".join(
                    f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}" for c in draft.fixed_palette or []), fixed_changed,
                    multiline=True, min_lines=2, max_lines=4))
            if not indexed:
                export_controls.controls.append(text("Choose 8-bit indexed to enable palettes and dithering.", 11, FAINT))

        async def save_output(e):
            nonlocal export_cfg
            try:
                # Validate again before displaying a save picker.
                export.process(original, draft)
                filename = f"{Path(result_source).stem}_sheet.{draft.format}"
                if page.web:
                    with tempfile.TemporaryDirectory() as tmp:
                        p = export.save(original, Path(tmp) / filename, draft)
                        await picker.save_file(file_name=filename, src_bytes=p.read_bytes())
                    message = f"Export prepared: {filename}"
                else:
                    destination = await picker.save_file(file_name=filename,
                        initial_directory=str(Path(result_source).parent),
                        file_type=ft.FilePickerFileType.CUSTOM, allowed_extensions=[draft.format])
                    if not destination:
                        return
                    p = export.save(original, Path(destination), draft)
                    message = f"Exported {p.name} → {p.parent}"
                export_cfg = copy.deepcopy(draft)
                persist()
                page.pop_dialog()
                notify(message)
            except Exception as exc:  # noqa: BLE001 — keep export errors in the dialog
                export_error.value = f"Export failed: {exc}"
                page.update()

        save_btn = button("Export sprite sheet", ft.Icons.DOWNLOAD_ROUNDED, save_output, True)
        build_export_controls()
        dialog = ft.AlertDialog(bgcolor=PANEL, shape=ft.RoundedRectangleBorder(radius=16),
            title=ft.Row([ft.Column([text("Ready for your game.", 24, TEXT, ft.FontWeight.W_600),
                                    text("Fine-tune the output. Your render stays untouched.", 12, MUTED)], spacing=6),
                          ft.Container(expand=True), ft.IconButton(ft.Icons.CLOSE, on_click=lambda e: page.pop_dialog())]),
            content=ft.Container(width=940, height=570, content=ft.Row([
                ft.Container(expand=5, padding=18, bgcolor=BG, border_radius=10,
                    content=ft.Column([caption("Export preview"),
                        ft.Container(export_image, expand=True, alignment=CENTER,
                                     image=ft.DecorationImage(src="checker.png", repeat=ft.ImageRepeat.REPEAT)),
                        export_info, text("Exporting the last rendered sheet. Changes are pending." if stale else
                                          "Updates as you change export settings. No Blender render needed.", 11, MUTED)], spacing=12)),
                ft.Container(expand=4, content=export_controls, padding=ft.Padding(12, 0, 0, 0)),
            ], spacing=16, vertical_alignment=ft.CrossAxisAlignment.STRETCH)),
            actions=[export_error, button("Cancel", ft.Icons.CLOSE, lambda e: page.pop_dialog()), save_btn])
        page.show_dialog(dialog)
        refresh()

    # Workspace chrome
    connection = text("Blender connected" if bpath else "Locate Blender", 11, ACCENT if bpath else "#f1ac91")
    width_field = field("Width · px", settings.frame_width, lambda e: integer("frame_width", e), expand=True)
    height_field = field("Height · px", settings.frame_height, lambda e: integer("frame_height", e), expand=True)
    frames_field = field("Frames", settings.frames, lambda e: integer("frames", e), expand=True)
    appearance_dd = dropdown("Appearance preset", appearance_key(),
        [(k, v.label) for k, v in PRESETS.items()] + [("custom", "Custom appearance")], choose_preset)
    sidebar = ft.Container(width=310, bgcolor=PANEL, padding=20,
        border=ft.Border(right=ft.BorderSide(1, BORDER)), content=ft.Column([
            section("01 / Source", [ft.Container(ft.Row([
                ft.Icon(ft.Icons.VIEW_IN_AR_OUTLINED, size=24, color=ACCENT),
                ft.Column([model_name, model_detail], spacing=4, expand=True),
                ft.IconButton(ft.Icons.FOLDER_OPEN_OUTLINED, icon_size=18, icon_color=MUTED,
                              tooltip="Choose model", on_click=lambda e: page.run_task(pick_source)),
            ], spacing=12), bgcolor=CARD, padding=12, border_radius=9),
                appearance_dd]),
            ft.Divider(color=BORDER, height=1),
            section("02 / Sprite geometry", [ft.Row([width_field, height_field], spacing=10),
                ft.Row([dropdown("Directions", settings.angles, [(n, str(n)) for n in (1, 4, 8, 16)],
                                 angles_changed, expand=True), frames_field], spacing=10), geometry]),
            ft.Divider(color=BORDER, height=1), tab_buttons, inspector,
        ], spacing=18, expand=True))
    preview_btn = button("Preview", ft.Icons.VISIBILITY_OUTLINED, lambda e: start_render(True))
    render_btn = button("Render sheet", ft.Icons.GRID_VIEW_ROUNDED, lambda e: start_render(False))
    export_btn = button("Export sprite sheet", ft.Icons.NORTH_EAST, open_export, True, disabled=True)
    cancel_btn = button("Cancel render", ft.Icons.CLOSE, lambda e: cancel.set(), visible=False)
    play_btn = ft.IconButton(ft.Icons.PLAY_ARROW_ROUNDED, icon_color=ACCENT, bgcolor="#303a2a",
                             on_click=toggle_play, disabled=True, tooltip="Play / pause animation")
    sprite_tab = ft.Container(text("Sprite", 11), bgcolor="#303a2a", padding=ft.Padding(15, 9, 15, 9),
                              border_radius=6, on_click=lambda e: set_view("sprite"))
    sheet_tab = ft.Container(text("Sheet", 11), bgcolor=PANEL, padding=ft.Padding(15, 9, 15, 9),
                             border_radius=6, on_click=lambda e: set_view("sheet"))
    workspace = ft.Container(expand=True, padding=ft.Padding(28, 25, 28, 18), content=ft.Column([
        ft.Row([ft.Column([result_badge, headline, subtitle], spacing=7, expand=True),
                preview_btn, render_btn], spacing=10),
        ft.Row([ft.Row([sprite_tab, sheet_tab], spacing=3), ft.Container(expand=True),
                ft.IconButton(ft.Icons.CENTER_FOCUS_STRONG, icon_size=18, icon_color=MUTED,
                              tooltip="Recenter and reset gesture zoom", on_click=lambda e: page.run_task(reset_view)),
                text("BASE SIZE", 9, FAINT),
                dropdown(None, zoom, [(n, f"{n * 100}%") for n in (1, 2, 3, 4, 6)], set_zoom, width=100),
                ft.IconButton(ft.Icons.CONTRAST, icon_size=18, icon_color=MUTED, tooltip="Toggle checkerboard",
                              on_click=lambda e: toggle_checker())], spacing=10),
        viewport,
        text("Drag to pan · scroll / pinch to zoom · facing buttons change the view only", 10, FAINT),
        ft.Row([direction_buttons, ft.Container(expand=True), dimensions], spacing=10),
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

    topbar = ft.Container(padding=ft.Padding(22, 14, 22, 14), bgcolor=PANEL,
        border=ft.Border(bottom=ft.BorderSide(1, BORDER)), content=ft.Row([
            ft.Container(ft.Icon(ft.Icons.FILTER_FRAMES_OUTLINED, size=21, color=INK),
                         bgcolor=ACCENT, padding=8, border_radius=8),
            text("framemill", 20, TEXT, ft.FontWeight.W_600),
            ft.Container(width=14), text("/", 18, FAINT), text("Sprite workspace", 12, MUTED),
            ft.Container(expand=True),
            ft.TextButton("Quick guide", icon=ft.Icons.HELP_OUTLINE, on_click=open_guide,
                          style=ft.ButtonStyle(color=MUTED)), export_btn,
        ], spacing=12))
    footer = ft.Container(padding=ft.Padding(20, 8, 20, 8), bgcolor=PANEL,
        border=ft.Border(top=ft.BorderSide(1, BORDER)), content=ft.Row([
            ft.Container(ft.Row([ft.Icon(ft.Icons.CIRCLE, size=7, color=ACCENT if bpath else "#f1ac91"), connection], spacing=7),
                         on_click=lambda e: page.run_task(locate_blender), tooltip=bpath or "Locate Blender"),
            ft.Container(width=12), ft.Container(status, expand=True), cancel_btn,
            text("LOCAL RENDERING", 9, FAINT),
        ], spacing=10))
    update_geometry()
    build_inspector()
    page.add(ft.Column([topbar, ft.Row([sidebar, workspace], expand=True, spacing=0), progress, footer],
                       spacing=0, expand=True))


def run() -> None:
    web = os.environ.get("FRAMEMILL_WEB") == "1"
    if web:
        os.environ["FLET_FORCE_WEB_SERVER"] = "true"
    ft.run(main, assets_dir=str(Path(__file__).parent / "assets"),
           view=ft.AppView.WEB_BROWSER if web else ft.AppView.FLET_APP,
           host="127.0.0.1", port=8000 if web else 0)


if __name__ == "__main__":
    run()
