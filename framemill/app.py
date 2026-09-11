"""framemill desktop GUI (Flet).

Two-pane layout: settings on the left, live preview + render on the right, with
Guide and Setup tabs. Long renders run on a worker thread and stream progress.
"""
from __future__ import annotations

import tempfile
import threading
from pathlib import Path

import flet as ft

from . import appconfig, blender, compositor, guide
from .settings import PRESETS, DEFAULT_PRESET, RenderSettings

ACCENT = "#4f8cff"


class AppState:
    def __init__(self) -> None:
        self.settings: RenderSettings = RenderSettings.from_dict(
            PRESETS[DEFAULT_PRESET].settings.to_dict()
        )
        self.model_path: str | None = None
        self.idle_path: str | None = None
        self.blender_path: str | None = blender.find_blender()
        self.formats: list[str] = ["png"]
        self.magic_pink: bool = False
        self.rendering: bool = False


def main(page: ft.Page) -> None:
    page.title = "framemill"
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = ft.Theme(color_scheme_seed=ACCENT)
    page.window.width = 1180
    page.window.height = 820
    page.padding = 0

    st = AppState()

    # ---- shared right-pane controls ----
    preview_img = ft.Image(
        src=None, width=420, height=420, fit=ft.ImageFit.CONTAIN,
        error_content=ft.Container(
            content=ft.Text("Preview appears here", color=ft.Colors.WHITE54),
            alignment=ft.alignment.center,
        ),
    )
    progress = ft.ProgressBar(value=0, width=420, color=ACCENT, bgcolor="#333")
    status = ft.Text("", size=12, color=ft.Colors.WHITE70)

    def set_status(msg: str) -> None:
        status.value = msg
        page.update()

    # ---- blender banner ----
    banner = ft.Container(padding=10, border_radius=8)

    def refresh_banner() -> None:
        if st.blender_path:
            ver = blender.blender_version(st.blender_path) or "Blender"
            banner.bgcolor = "#16351f"
            banner.content = ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE, color="#5fd08a", size=18),
                ft.Text(f"{ver}", color=ft.Colors.WHITE, size=12),
                ft.Text(st.blender_path, color=ft.Colors.WHITE54, size=11),
            ], spacing=8)
        else:
            banner.bgcolor = "#3a1f1f"
            banner.content = ft.Row([
                ft.Icon(ft.Icons.WARNING, color="#e0a24f", size=18),
                ft.Text("Blender not found — locate it to enable rendering.",
                        color=ft.Colors.WHITE, size=12),
                ft.TextButton("Locate Blender", on_click=lambda _: blender_picker.pick_files(
                    allow_multiple=False)),
            ], spacing=8)
        page.update()

    # ---- file pickers ----
    def on_model(e: ft.FilePickerResultEvent) -> None:
        if e.files:
            st.model_path = e.files[0].path
            model_label.value = Path(st.model_path).name
            page.update()

    def on_idle(e: ft.FilePickerResultEvent) -> None:
        if e.files:
            st.idle_path = e.files[0].path
            idle_label.value = Path(st.idle_path).name
            page.update()

    def on_blender(e: ft.FilePickerResultEvent) -> None:
        if e.files:
            st.blender_path = e.files[0].path
            appconfig.set_blender_path(st.blender_path)
            refresh_banner()

    model_picker = ft.FilePicker(on_result=on_model)
    idle_picker = ft.FilePicker(on_result=on_idle)
    blender_picker = ft.FilePicker(on_result=on_blender)
    page.overlay.extend([model_picker, idle_picker, blender_picker])

    model_label = ft.Text("No model selected", color=ft.Colors.WHITE54, size=12)
    idle_label = ft.Text("(optional)", color=ft.Colors.WHITE54, size=12)

    # ---- settings helpers ----
    def upd(field: str, value) -> None:
        setattr(st.settings, field, value)

    def slider_row(label: str, field: str, lo: float, hi: float, step: float,
                   fmt: str = "{:.2f}") -> ft.Column:
        val = getattr(st.settings, field)
        value_text = ft.Text(fmt.format(val), size=11, color=ft.Colors.WHITE70)

        def changed(e: ft.ControlEvent) -> None:
            v = float(e.control.value)
            upd(field, v)
            value_text.value = fmt.format(v)
            page.update()

        return ft.Column([
            ft.Row([ft.Text(label, size=12), value_text],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Slider(min=lo, max=hi, divisions=max(1, int((hi - lo) / step)),
                      value=val, active_color=ACCENT, on_change=changed),
        ], spacing=0)

    def section(title: str, controls: list[ft.Control]) -> ft.ExpansionTile:
        return ft.ExpansionTile(
            title=ft.Text(title, size=13, weight=ft.FontWeight.W_600),
            controls=[ft.Container(ft.Column(controls, spacing=6), padding=12)],
            initially_expanded=False,
        )

    # ---- preset ----
    def apply_preset(key: str) -> None:
        st.settings = RenderSettings.from_dict(PRESETS[key].settings.to_dict())
        rebuild_sections()
        set_status(f"Applied preset: {PRESETS[key].label}")

    preset_dd = ft.Dropdown(
        label="Preset",
        value=DEFAULT_PRESET,
        options=[ft.dropdown.Option(k, PRESETS[k].label) for k in PRESETS],
        on_change=lambda e: apply_preset(e.control.value),
        width=280,
    )

    angles_dd = ft.Dropdown(
        label="Directions", value=str(st.settings.angles),
        options=[ft.dropdown.Option(str(n)) for n in (1, 4, 8, 16)],
        on_change=lambda e: upd("angles", int(e.control.value)), width=135,
    )
    frames_dd = ft.Dropdown(
        label="Frames", value=str(st.settings.frames),
        options=[ft.dropdown.Option(str(n)) for n in (1, 4, 8, 12, 16)],
        on_change=lambda e: upd("frames", int(e.control.value)), width=135,
    )

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
                    label="View transform", value=st.settings.view_transform,
                    options=[ft.dropdown.Option(v) for v in ("Standard", "AgX", "Filmic")],
                    on_change=lambda e: upd("view_transform", e.control.value)),
                slider_row("Exposure", "exposure", -3.0, 3.0, 0.1),
                slider_row("Gamma", "gamma", 0.2, 3.0, 0.05),
            ]),
            section("Material", [
                slider_row("Specular IOR level", "specular_ior", 0.0, 1.0, 0.05),
            ]),
            section("Animation", [
                ft.Text("Leave blank to auto-detect the model's range.",
                        size=11, color=ft.Colors.WHITE54),
            ]),
        ]
        page.update()

    # ---- render / preview ----
    def _run_render(preview: bool) -> None:
        if not st.blender_path:
            set_status("Blender not found — locate it first."); return
        if not st.model_path:
            set_status("Select a model first."); return
        st.rendering = True
        progress.value = None  # indeterminate
        set_status("Rendering preview…" if preview else "Rendering…")

        def worker() -> None:
            try:
                with tempfile.TemporaryDirectory() as tmp:
                    frames_dir = Path(tmp) / "frames"

                    def prog(p: blender.RenderProgress) -> None:
                        progress.value = p.current / p.total if p.total else None
                        status.value = p.stage
                        page.update()

                    blender.render(st.blender_path, st.model_path, frames_dir,
                                   st.settings, idle_path=st.idle_path,
                                   preview=preview, on_progress=prog)
                    out = Path(tempfile.gettempdir()) / "framemill_preview.png"
                    prev_settings = st.settings
                    if preview:
                        prev_settings = RenderSettings.from_dict(
                            {**st.settings.to_dict(), "angles": 1, "frames": 1})
                    compositor.composite(frames_dir, out, prev_settings, ["png"],
                                         magic_pink=st.magic_pink)
                    preview_img.src = str(out)
                    preview_img.src_base64 = None
                    progress.value = 1.0
                    set_status("Preview ready." if preview else "Render complete.")
                    if not preview:
                        _last_frames_hint()
            except Exception as ex:  # noqa: BLE001 - surface any Blender failure
                progress.value = 0
                set_status(f"Failed: {ex}")
            finally:
                st.rendering = False
                page.update()

        threading.Thread(target=worker, daemon=True).start()

    def _last_frames_hint() -> None:
        # Full export uses a Save dialog; preview writes to temp only.
        pass

    def do_export(_: ft.ControlEvent) -> None:
        if not st.blender_path or not st.model_path:
            set_status("Need Blender + a model first."); return

        def worker() -> None:
            st.rendering = True
            progress.value = None
            set_status("Rendering full sheet…")
            try:
                out_dir = Path(st.model_path).parent
                stem = Path(st.model_path).stem
                with tempfile.TemporaryDirectory() as tmp:
                    frames_dir = Path(tmp) / "frames"

                    def prog(p: blender.RenderProgress) -> None:
                        progress.value = p.current / p.total if p.total else None
                        status.value = p.stage
                        page.update()

                    blender.render(st.blender_path, st.model_path, frames_dir,
                                   st.settings, idle_path=st.idle_path, on_progress=prog)
                    written = compositor.composite(
                        frames_dir, out_dir / f"{stem}_sheet", st.settings,
                        st.formats, magic_pink=st.magic_pink,
                        progress=lambda c, t, s: None)
                preview_img.src = str(next((w for w in written if w.suffix == ".png"), written[0]))
                progress.value = 1.0
                set_status("Saved: " + ", ".join(w.name for w in written)
                           + f"  (in {out_dir})")
            except Exception as ex:  # noqa: BLE001
                progress.value = 0
                set_status(f"Failed: {ex}")
            finally:
                st.rendering = False
                page.update()

        threading.Thread(target=worker, daemon=True).start()

    # ---- left pane ----
    left = ft.Container(
        width=430,
        bgcolor="#1b1d22",
        padding=16,
        content=ft.Column([
            preset_dd,
            ft.Divider(height=8, color="transparent"),
            ft.Row([
                ft.OutlinedButton("Select model", icon=ft.Icons.VIEW_IN_AR,
                                  on_click=lambda _: model_picker.pick_files(
                                      allow_multiple=False,
                                      allowed_extensions=["fbx", "glb", "gltf", "obj"])),
                model_label,
            ], spacing=8, wrap=True),
            ft.Row([
                ft.OutlinedButton("Idle model", icon=ft.Icons.ACCESSIBILITY_NEW,
                                  on_click=lambda _: idle_picker.pick_files(
                                      allow_multiple=False,
                                      allowed_extensions=["fbx", "glb", "gltf", "obj"])),
                idle_label,
            ], spacing=8, wrap=True),
            ft.Divider(height=8, color="transparent"),
            ft.Row([angles_dd, frames_dd], spacing=10),
            ft.Row([png_cb, tga_cb], spacing=10),
            pink_cb,
            ft.Divider(),
            ft.Text("Advanced", size=12, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE70),
            sections_col,
        ], scroll=ft.ScrollMode.AUTO, spacing=8, expand=True),
    )

    right = ft.Container(
        expand=True,
        padding=20,
        content=ft.Column([
            banner,
            ft.Container(
                content=preview_img, alignment=ft.alignment.center,
                bgcolor="#101114", border_radius=10, padding=10, expand=True,
            ),
            progress,
            status,
            ft.Row([
                ft.OutlinedButton("Quick preview", icon=ft.Icons.VISIBILITY,
                                  on_click=lambda _: _run_render(preview=True)),
                ft.FilledButton("Render sheet", icon=ft.Icons.MOVIE_FILTER,
                                style=ft.ButtonStyle(bgcolor=ACCENT),
                                on_click=do_export),
            ], alignment=ft.MainAxisAlignment.END, spacing=12),
        ], spacing=14, expand=True),
    )

    render_tab = ft.Row([left, right], expand=True, spacing=0)

    # ---- guide tab ----
    def step_card(step: guide.Step) -> ft.Card:
        body: list[ft.Control] = [
            ft.Text(step.title, weight=ft.FontWeight.W_600),
            ft.Text(step.body, size=13, color=ft.Colors.WHITE70),
        ]
        if step.action and step.url:
            body.append(ft.TextButton(step.action, icon=ft.Icons.OPEN_IN_NEW,
                                      url=step.url))
        return ft.Card(ft.Container(ft.Column(body, spacing=6), padding=14))

    guide_tab = ft.Container(
        padding=24,
        content=ft.Column([
            ft.Text("From a drawing to a sprite sheet", size=18, weight=ft.FontWeight.BOLD),
            *[step_card(s) for s in guide.WORKFLOW_STEPS],
        ], scroll=ft.ScrollMode.AUTO, spacing=10),
    )

    setup_tab = ft.Container(
        padding=24,
        content=ft.Column([
            ft.Text("First-time setup", size=18, weight=ft.FontWeight.BOLD),
            *[step_card(s) for s in guide.SETUP_STEPS],
        ], scroll=ft.ScrollMode.AUTO, spacing=10),
    )

    page.add(ft.Tabs(
        selected_index=0, expand=True,
        tabs=[
            ft.Tab(text="Render", icon=ft.Icons.GRID_VIEW, content=render_tab),
            ft.Tab(text="Guide", icon=ft.Icons.MENU_BOOK, content=guide_tab),
            ft.Tab(text="Setup", icon=ft.Icons.SETTINGS, content=setup_tab),
        ],
    ))

    rebuild_sections()
    refresh_banner()


def run() -> None:
    ft.app(target=main)


if __name__ == "__main__":
    run()
