"""framemill desktop GUI (Flet 0.86+).

Two-pane layout with a simple top nav (Render / Guide / Setup). Settings on the
left, live preview + render on the right. Long renders run off the UI thread.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import flet as ft

from . import appconfig, blender, compositor, guide
from .settings import PRESETS, DEFAULT_PRESET, RenderSettings

ACCENT = "#4f8cff"
CENTER = ft.Alignment(0, 0)


class AppState:
    def __init__(self) -> None:
        self.settings: RenderSettings = RenderSettings.from_dict(
            PRESETS[DEFAULT_PRESET].settings.to_dict())
        self.model_path: str | None = None
        self.idle_path: str | None = None
        self.blender_path: str | None = blender.find_blender()
        self.formats: list[str] = ["png"]
        self.magic_pink: bool = False
        self.rendering: bool = False


def main(page: ft.Page) -> None:
    page.title = "framemill"
    page.theme_mode = ft.ThemeMode.DARK
    try:
        page.theme = ft.Theme(color_scheme_seed=ACCENT)
    except Exception:
        pass
    try:
        page.window.width = 1180
        page.window.height = 820
    except Exception:
        pass
    page.padding = 0

    st = AppState()

    # ---------- right pane ----------
    preview_img = ft.Image(
        src=None, width=440, height=440, fit=ft.BoxFit.CONTAIN,
        error_content=ft.Container(
            content=ft.Text("Preview appears here", color=ft.Colors.WHITE54),
            alignment=CENTER),
    )
    progress = ft.ProgressBar(value=0, color=ACCENT, bgcolor="#333333")
    status = ft.Text("", size=12, color=ft.Colors.WHITE70)

    def set_status(msg: str) -> None:
        status.value = msg
        page.update()

    banner = ft.Container(padding=10, border_radius=8)

    def refresh_banner() -> None:
        if st.blender_path:
            ver = blender.blender_version(st.blender_path) or "Blender"
            banner.bgcolor = "#16351f"
            banner.content = ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE, color="#5fd08a", size=18),
                ft.Text(ver, color=ft.Colors.WHITE, size=12),
                ft.Text(st.blender_path, color=ft.Colors.WHITE54, size=11),
            ], spacing=8, wrap=True)
        else:
            banner.bgcolor = "#3a1f1f"
            banner.content = ft.Row([
                ft.Icon(ft.Icons.WARNING, color="#e0a24f", size=18),
                ft.Text("Blender not found — locate it to enable rendering.",
                        color=ft.Colors.WHITE, size=12),
                ft.TextButton("Locate Blender", on_click=pick_blender),
            ], spacing=8, wrap=True)
        page.update()

    # ---------- file pickers (services in 0.86; pick_files is async) ----------
    model_picker = ft.FilePicker()
    idle_picker = ft.FilePicker()
    blender_picker = ft.FilePicker()
    page.services.append(model_picker)
    page.services.append(idle_picker)
    page.services.append(blender_picker)

    model_label = ft.Text("No model selected", color=ft.Colors.WHITE54, size=12)
    idle_label = ft.Text("(optional)", color=ft.Colors.WHITE54, size=12)

    _MODEL_EXT = ["fbx", "glb", "gltf", "obj"]

    async def pick_model(e: ft.Event) -> None:
        files = await model_picker.pick_files(allow_multiple=False, allowed_extensions=_MODEL_EXT)
        if files:
            st.model_path = files[0].path
            model_label.value = files[0].name
            page.update()

    async def pick_idle(e: ft.Event) -> None:
        files = await idle_picker.pick_files(allow_multiple=False, allowed_extensions=_MODEL_EXT)
        if files:
            st.idle_path = files[0].path
            idle_label.value = files[0].name
            page.update()

    async def pick_blender(e: ft.Event) -> None:
        files = await blender_picker.pick_files(allow_multiple=False)
        if files:
            st.blender_path = files[0].path
            appconfig.set_blender_path(st.blender_path)
            refresh_banner()

    # ---------- settings controls ----------
    def upd(field: str, value) -> None:
        setattr(st.settings, field, value)

    def slider_row(label: str, field: str, lo: float, hi: float, step: float,
                   fmt: str = "{:.2f}") -> ft.Column:
        val = getattr(st.settings, field)
        vtext = ft.Text(fmt.format(val), size=11, color=ft.Colors.WHITE70)

        def changed(e: ft.Event) -> None:
            v = float(e.control.value)
            upd(field, v)
            vtext.value = fmt.format(v)
            page.update()

        return ft.Column([
            ft.Row([ft.Text(label, size=12), vtext],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Slider(min=lo, max=hi, divisions=max(1, int((hi - lo) / step)),
                      value=val, active_color=ACCENT, on_change=changed),
        ], spacing=0)

    def section(title: str, controls: list[ft.Control]) -> ft.ExpansionTile:
        return ft.ExpansionTile(
            title=ft.Text(title, size=13, weight=ft.FontWeight.W_600),
            controls=[ft.Container(ft.Column(controls, spacing=6), padding=12)],
            expanded=False)

    def apply_preset(key: str) -> None:
        st.settings = RenderSettings.from_dict(PRESETS[key].settings.to_dict())
        rebuild_sections()
        set_status(f"Applied preset: {PRESETS[key].label}")

    preset_dd = ft.Dropdown(
        label="Preset", value=DEFAULT_PRESET, width=300,
        options=[ft.dropdown.Option(k, PRESETS[k].label) for k in PRESETS],
        on_select=lambda e: apply_preset(e.control.value))
    angles_dd = ft.Dropdown(
        label="Directions", value=str(st.settings.angles), width=140,
        options=[ft.dropdown.Option(str(n)) for n in (1, 4, 8, 16)],
        on_select=lambda e: upd("angles", int(e.control.value)))
    frames_dd = ft.Dropdown(
        label="Frames", value=str(st.settings.frames), width=140,
        options=[ft.dropdown.Option(str(n)) for n in (1, 4, 8, 12, 16)],
        on_select=lambda e: upd("frames", int(e.control.value)))

    def set_format(png: bool, tga: bool) -> None:
        st.formats = [f for f, on in (("png", png), ("tga", tga)) if on] or ["png"]

    png_cb = ft.Checkbox(label="PNG", value=True,
                         on_change=lambda e: set_format(e.control.value, tga_cb.value))
    tga_cb = ft.Checkbox(label="TGA", value=False,
                         on_change=lambda e: set_format(png_cb.value, e.control.value))
    pink_cb = ft.Checkbox(label="Magic-pink transparency (legacy)", value=False,
                          on_change=lambda e: setattr(st, "magic_pink", e.control.value))

    sections_col = ft.Column(spacing=4)

    def rebuild_sections() -> None:
        angles_dd.value = str(st.settings.angles)
        frames_dd.value = str(st.settings.frames)
        sections_col.controls = [
            section("Camera", [
                slider_row("Ortho scale x model height", "ortho_scale_mult", 0.5, 4.0, 0.1),
                slider_row("Distance", "camera_distance", 0.5, 10.0, 0.1),
                slider_row("Pitch (90=level, lower=top-down)", "camera_pitch", 30, 120, 1, "{:.0f}"),
            ]),
            section("Lighting", [
                slider_row("Light energy", "light_energy", 0, 3000, 50, "{:.0f}"),
                slider_row("Shadow softness", "shadow_soft_size", 0, 2.0, 0.05),
            ]),
            section("Ambient / World", [
                slider_row("Ambient strength", "ambient_strength", 0, 8.0, 0.1),
            ]),
            section("Colour management", [
                ft.Dropdown(
                    label="View transform", value=st.settings.view_transform, width=260,
                    options=[ft.dropdown.Option(v) for v in ("Standard", "AgX", "Filmic")],
                    on_select=lambda e: upd("view_transform", e.control.value)),
                slider_row("Exposure", "exposure", -3.0, 3.0, 0.1),
                slider_row("Gamma", "gamma", 0.2, 3.0, 0.05),
            ]),
            section("Material", [
                slider_row("Specular IOR level", "specular_ior", 0.0, 1.0, 0.05),
            ]),
        ]
        page.update()

    # ---------- render actions ----------
    def _do_render(preview: bool) -> None:
        if not st.blender_path:
            set_status("Blender not found — locate it first."); return
        if not st.model_path:
            set_status("Select a model first."); return
        if st.rendering:
            return
        st.rendering = True
        progress.value = None
        set_status("Rendering preview…" if preview else "Rendering sheet…")

        def prog(p: blender.RenderProgress) -> None:
            progress.value = (p.current / p.total) if p.total else None
            status.value = p.stage
            page.update()

        try:
            with tempfile.TemporaryDirectory() as tmp:
                frames_dir = Path(tmp) / "frames"
                blender.render(st.blender_path, st.model_path, frames_dir, st.settings,
                               idle_path=st.idle_path, preview=preview, on_progress=prog)
                if preview:
                    s = RenderSettings.from_dict({**st.settings.to_dict(), "angles": 1, "frames": 1})
                    out = Path(tempfile.gettempdir()) / "framemill_preview.png"
                    compositor.composite(frames_dir, out, s, ["png"], magic_pink=st.magic_pink)
                    preview_img.src = str(out)
                    set_status("Preview ready.")
                else:
                    out_dir = Path(st.model_path).parent
                    stem = Path(st.model_path).stem
                    written = compositor.composite(frames_dir, out_dir / f"{stem}_sheet",
                                                   st.settings, st.formats, magic_pink=st.magic_pink)
                    png = next((w for w in written if w.suffix == ".png"), written[0])
                    preview_img.src = str(png)
                    set_status("Saved: " + ", ".join(w.name for w in written) + f"  ({out_dir})")
            progress.value = 1.0
        except Exception as ex:  # noqa: BLE001 - surface any Blender/compositor failure
            progress.value = 0
            set_status(f"Failed: {ex}")
        finally:
            st.rendering = False
            page.update()

    # ---------- layout ----------
    def spacer(h: int) -> ft.Container:
        return ft.Container(height=h)

    left = ft.Container(
        width=440, bgcolor="#1b1d22", padding=16,
        content=ft.Column([
            preset_dd,
            spacer(6),
            ft.Row([ft.OutlinedButton("Select model", icon=ft.Icons.VIEW_IN_AR,
                                      on_click=pick_model), model_label],
                   spacing=8, wrap=True),
            ft.Row([ft.OutlinedButton("Idle model", icon=ft.Icons.ACCESSIBILITY_NEW,
                                      on_click=pick_idle), idle_label],
                   spacing=8, wrap=True),
            spacer(6),
            ft.Row([angles_dd, frames_dd], spacing=10),
            ft.Row([png_cb, tga_cb], spacing=10),
            pink_cb,
            ft.Divider(),
            ft.Text("Advanced", size=12, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE70),
            sections_col,
        ], scroll=ft.ScrollMode.AUTO, spacing=8, expand=True))

    right = ft.Container(
        expand=True, padding=20,
        content=ft.Column([
            banner,
            ft.Container(content=preview_img, alignment=CENTER, bgcolor="#101114",
                         border_radius=10, padding=10, expand=True),
            progress, status,
            ft.Row([
                ft.OutlinedButton("Quick preview", icon=ft.Icons.VISIBILITY,
                                  on_click=lambda e: page.run_thread(_do_render, True)),
                ft.FilledButton("Render sheet", icon=ft.Icons.MOVIE_FILTER, bgcolor=ACCENT,
                                on_click=lambda e: page.run_thread(_do_render, False)),
            ], alignment=ft.MainAxisAlignment.END, spacing=12),
        ], spacing=14, expand=True))

    render_view = ft.Row([left, right], expand=True, spacing=0)

    def step_card(step: guide.Step) -> ft.Card:
        body: list[ft.Control] = [
            ft.Text(step.title, weight=ft.FontWeight.W_600),
            ft.Text(step.body, size=13, color=ft.Colors.WHITE70),
        ]
        if step.action and step.url:
            body.append(ft.TextButton(step.action, icon=ft.Icons.OPEN_IN_NEW, url=step.url))
        return ft.Card(ft.Container(ft.Column(body, spacing=6), padding=14))

    guide_view = ft.Container(padding=24, content=ft.Column(
        [ft.Text("From a drawing to a sprite sheet", size=18, weight=ft.FontWeight.BOLD),
         *[step_card(s) for s in guide.WORKFLOW_STEPS]],
        scroll=ft.ScrollMode.AUTO, spacing=10))
    setup_view = ft.Container(padding=24, content=ft.Column(
        [ft.Text("First-time setup", size=18, weight=ft.FontWeight.BOLD),
         *[step_card(s) for s in guide.SETUP_STEPS]],
        scroll=ft.ScrollMode.AUTO, spacing=10))

    body = ft.Container(content=render_view, expand=True)
    views = {"Render": render_view, "Guide": guide_view, "Setup": setup_view}

    def nav_to(name: str) -> None:
        body.content = views[name]
        for b in nav_buttons:
            b.style = ft.ButtonStyle(color=ACCENT if b.data == name else ft.Colors.WHITE70)
        page.update()

    nav_buttons = [
        ft.TextButton(n, data=n, icon=ic, on_click=lambda e: nav_to(e.control.data))
        for n, ic in (("Render", ft.Icons.GRID_VIEW), ("Guide", ft.Icons.MENU_BOOK),
                      ("Setup", ft.Icons.SETTINGS))
    ]
    topbar = ft.Container(
        bgcolor="#141519", padding=ft.Padding(12, 6, 12, 6),
        content=ft.Row([ft.Text("framemill", weight=ft.FontWeight.BOLD, size=16),
                        ft.Container(width=20), *nav_buttons], spacing=4))

    page.add(ft.Column([topbar, body], spacing=0, expand=True))
    rebuild_sections()
    refresh_banner()
    nav_to("Render")


def run() -> None:
    ft.run(main)


if __name__ == "__main__":
    run()
