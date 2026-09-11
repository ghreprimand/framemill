"""framemill desktop GUI (Flet 0.86+) — polished two-pane layout."""
from __future__ import annotations

import tempfile
from pathlib import Path

import flet as ft

from . import appconfig, blender, compositor, guide
from .settings import PRESETS, DEFAULT_PRESET, RenderSettings

# ---------------------------------------------------------------- design tokens
BG        = "#0d0e12"
PANEL     = "#14161c"
CARD      = "#1a1d24"
CARD_HI   = "#20242d"
BORDER    = "#2a2f3a"
TEXT      = "#e7e9f0"
MUTED     = "#9096a6"
FAINT     = "#6b7280"
ACCENT    = "#6d8bff"
OK        = "#4ad07f"
WARN      = "#e0a24f"
CENTER    = ft.Alignment(0, 0)
RADIUS    = 12


def _border(w: int = 1, c: str = BORDER) -> ft.Border:
    s = ft.BorderSide(w, c)
    return ft.Border(left=s, top=s, right=s, bottom=s)


def _round(r: int = RADIUS) -> ft.RoundedRectangleBorder:
    return ft.RoundedRectangleBorder(radius=r)


class AppState:
    def __init__(self) -> None:
        self.settings = RenderSettings.from_dict(PRESETS[DEFAULT_PRESET].settings.to_dict())
        self.model_path: str | None = None
        self.idle_path: str | None = None
        self.blender_path: str | None = blender.find_blender()
        self.formats: list[str] = ["png"]
        self.magic_pink = False
        self.rendering = False


def main(page: ft.Page) -> None:
    page.title = "framemill"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = BG
    page.padding = 0
    try:
        page.theme = ft.Theme(color_scheme_seed=ACCENT, use_material3=True)
    except Exception:
        pass
    try:
        page.window.width = 1240
        page.window.height = 860
        page.window.min_width = 980
        page.window.min_height = 680
    except Exception:
        pass

    st = AppState()

    # ============================================================ right: preview
    preview_slot = ft.Container(alignment=CENTER, expand=True)

    def empty_state() -> ft.Control:
        return ft.Column([
            ft.Icon(ft.Icons.IMAGE_OUTLINED, size=54, color=FAINT),
            ft.Text("Load a model, then Quick preview", color=MUTED, size=13),
        ], alignment=ft.MainAxisAlignment.CENTER,
           horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)

    preview_slot.content = empty_state()

    try:
        preview_deco = ft.DecorationImage(src="checker.png", repeat=ft.ImageRepeat.REPEAT)
        preview_panel = ft.Container(content=preview_slot, image=preview_deco,
                                     border=_border(), border_radius=RADIUS, expand=True)
    except Exception:
        preview_panel = ft.Container(content=preview_slot, bgcolor="#101114",
                                     border=_border(), border_radius=RADIUS, expand=True)

    progress = ft.ProgressBar(value=0, color=ACCENT, bgcolor="#22252e",
                              bar_height=6, border_radius=4)
    status = ft.Text("", size=12, color=MUTED)

    def set_status(msg: str) -> None:
        status.value = msg
        page.update()

    def show_sprite(path: str) -> None:
        preview_slot.content = ft.Image(src=path, fit=ft.BoxFit.CONTAIN, expand=True,
                                        filter_quality=ft.FilterQuality.MEDIUM)

    # ============================================================ blender bar
    blender_bar = ft.Container(padding=ft.Padding(14, 10, 10, 10), border_radius=RADIUS)

    async def pick_blender(e=None) -> None:
        files = await blender_picker.pick_files(allow_multiple=False)
        if files:
            st.blender_path = files[0].path
            appconfig.set_blender_path(st.blender_path)
            refresh_blender_bar()

    def refresh_blender_bar() -> None:
        change_btn = ft.IconButton(ft.Icons.FOLDER_OPEN, icon_size=18, icon_color=MUTED,
                                   tooltip="Choose a different Blender executable",
                                   on_click=pick_blender)
        if st.blender_path:
            ver = blender.blender_version(st.blender_path) or "Blender"
            blender_bar.bgcolor = "#13251a"
            blender_bar.border = _border(1, "#1f4a33")
            blender_bar.content = ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color=OK, size=18),
                ft.Column([
                    ft.Text(ver, color=TEXT, size=12, weight=ft.FontWeight.W_600),
                    ft.Text(st.blender_path, color=FAINT, size=11),
                ], spacing=0, expand=True),
                change_btn,
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        else:
            blender_bar.bgcolor = "#2a1a1a"
            blender_bar.border = _border(1, "#5a2f2f")
            blender_bar.content = ft.Row([
                ft.Icon(ft.Icons.WARNING_ROUNDED, color=WARN, size=18),
                ft.Text("Blender not found — point framemill at it to enable rendering.",
                        color=TEXT, size=12, expand=True),
                ft.FilledButton("Locate Blender", icon=ft.Icons.FOLDER_OPEN,
                                on_click=pick_blender,
                                style=ft.ButtonStyle(bgcolor=ACCENT, color="#0b1020",
                                                     shape=_round(10))),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        page.update()

    # ============================================================ file pickers
    model_picker = ft.FilePicker()
    idle_picker = ft.FilePicker()
    blender_picker = ft.FilePicker()
    page.services.extend([model_picker, idle_picker, blender_picker])
    _EXT = ["fbx", "glb", "gltf", "obj"]

    model_label = ft.Text("No model selected", color=MUTED, size=12, expand=True,
                          no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS)
    idle_label = ft.Text("Optional — clean standing frame 0", color=MUTED, size=12,
                         expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS)

    async def pick_model(e) -> None:
        files = await model_picker.pick_files(allow_multiple=False, allowed_extensions=_EXT)
        if files:
            st.model_path = files[0].path
            model_label.value = files[0].name
            model_label.color = TEXT
            page.update()

    async def pick_idle(e) -> None:
        files = await idle_picker.pick_files(allow_multiple=False, allowed_extensions=_EXT)
        if files:
            st.idle_path = files[0].path
            idle_label.value = files[0].name
            idle_label.color = TEXT
            page.update()

    # ============================================================ settings widgets
    def upd(field: str, value) -> None:
        setattr(st.settings, field, value)

    def label(t: str) -> ft.Text:
        return ft.Text(t, size=11, color=MUTED, weight=ft.FontWeight.W_500)

    def dd_style(dd: ft.Dropdown) -> ft.Dropdown:
        dd.filled = True
        dd.fill_color = CARD_HI
        dd.border_color = BORDER
        dd.border_radius = 10
        dd.focused_border_color = ACCENT
        dd.text_size = 13
        return dd

    def slider_row(text: str, field: str, lo: float, hi: float, step: float,
                   fmt: str = "{:.2f}") -> ft.Column:
        val = getattr(st.settings, field)
        vtext = ft.Text(fmt.format(val), size=11, color=ACCENT, weight=ft.FontWeight.W_600)

        def changed(e) -> None:
            v = float(e.control.value)
            upd(field, v)
            vtext.value = fmt.format(v)
            page.update()

        return ft.Column([
            ft.Row([label(text), vtext], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Slider(min=lo, max=hi, divisions=max(1, int((hi - lo) / step)), value=val,
                      active_color=ACCENT, inactive_color="#2a2f3a", on_change=changed),
        ], spacing=0)

    def section(title: str, icon: str, controls: list[ft.Control]) -> ft.ExpansionTile:
        return ft.ExpansionTile(
            title=ft.Text(title, size=13, weight=ft.FontWeight.W_600, color=TEXT),
            leading=ft.Icon(icon, size=18, color=MUTED),
            controls=[ft.Container(ft.Column(controls, spacing=10),
                                   padding=ft.Padding(16, 4, 12, 14))],
            expanded=False, bgcolor=CARD, collapsed_bgcolor=CARD,
            text_color=TEXT, collapsed_text_color=TEXT,
            icon_color=ACCENT, collapsed_icon_color=MUTED,
            shape=_round(), collapsed_shape=_round(),
            tile_padding=ft.Padding(14, 4, 10, 4))

    def apply_preset(key: str) -> None:
        st.settings = RenderSettings.from_dict(PRESETS[key].settings.to_dict())
        rebuild_sections()
        set_status(f"Applied preset · {PRESETS[key].label}")

    preset_dd = dd_style(ft.Dropdown(
        value=DEFAULT_PRESET, expand=True,
        options=[ft.dropdown.Option(k, PRESETS[k].label) for k in PRESETS],
        on_select=lambda e: apply_preset(e.control.value)))
    angles_dd = dd_style(ft.Dropdown(
        value=str(st.settings.angles), expand=True,
        options=[ft.dropdown.Option(str(n)) for n in (1, 4, 8, 16)],
        on_select=lambda e: upd("angles", int(e.control.value))))
    frames_dd = dd_style(ft.Dropdown(
        value=str(st.settings.frames), expand=True,
        options=[ft.dropdown.Option(str(n)) for n in (1, 4, 8, 12, 16)],
        on_select=lambda e: upd("frames", int(e.control.value))))

    def set_format(png: bool, tga: bool) -> None:
        st.formats = [f for f, on in (("png", png), ("tga", tga)) if on] or ["png"]

    png_cb = ft.Checkbox(label="PNG", value=True, active_color=ACCENT,
                         on_change=lambda e: set_format(e.control.value, tga_cb.value))
    tga_cb = ft.Checkbox(label="TGA", value=False, active_color=ACCENT,
                         on_change=lambda e: set_format(png_cb.value, e.control.value))
    pink_cb = ft.Checkbox(label="Magic-pink transparency (legacy engines)", value=False,
                          active_color=ACCENT, scale=0.95,
                          on_change=lambda e: setattr(st, "magic_pink", e.control.value))

    sections_col = ft.Column(spacing=8)

    def rebuild_sections() -> None:
        angles_dd.value = str(st.settings.angles)
        frames_dd.value = str(st.settings.frames)
        vt = dd_style(ft.Dropdown(
            value=st.settings.view_transform, expand=True,
            options=[ft.dropdown.Option(v) for v in ("Standard", "AgX", "Filmic")],
            on_select=lambda e: upd("view_transform", e.control.value)))
        sections_col.controls = [
            section("Camera", ft.Icons.VIDEOCAM_OUTLINED, [
                slider_row("Ortho scale × model height", "ortho_scale_mult", 0.5, 4.0, 0.1),
                slider_row("Distance", "camera_distance", 0.5, 10.0, 0.1),
                slider_row("Pitch  (90 = level · lower = top-down)", "camera_pitch", 30, 120, 1, "{:.0f}"),
            ]),
            section("Lighting", ft.Icons.LIGHTBULB_OUTLINE, [
                slider_row("Light energy", "light_energy", 0, 3000, 50, "{:.0f}"),
                slider_row("Shadow softness", "shadow_soft_size", 0, 2.0, 0.05),
            ]),
            section("Ambient / World", ft.Icons.PUBLIC, [
                slider_row("Ambient strength", "ambient_strength", 0, 8.0, 0.1),
            ]),
            section("Colour management", ft.Icons.PALETTE_OUTLINED, [
                ft.Column([label("View transform"), vt], spacing=6),
                slider_row("Exposure", "exposure", -3.0, 3.0, 0.1),
                slider_row("Gamma", "gamma", 0.2, 3.0, 0.05),
            ]),
            section("Material", ft.Icons.LAYERS_OUTLINED, [
                slider_row("Specular IOR level", "specular_ior", 0.0, 1.0, 0.05),
            ]),
        ]
        page.update()

    # ============================================================ render actions
    def _do_render(preview: bool) -> None:
        if not st.blender_path:
            set_status("Point framemill at Blender first."); return
        if not st.model_path:
            set_status("Select a model first."); return
        if st.rendering:
            return
        st.rendering = True
        progress.value = None
        set_status("Rendering preview…" if preview else "Rendering sheet…")
        page.update()

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
                    show_sprite(str(out))
                    set_status("Preview ready.")
                else:
                    out_dir = Path(st.model_path).parent
                    stem = Path(st.model_path).stem
                    written = compositor.composite(frames_dir, out_dir / f"{stem}_sheet",
                                                   st.settings, st.formats, magic_pink=st.magic_pink)
                    png = next((w for w in written if w.suffix == ".png"), written[0])
                    show_sprite(str(png))
                    set_status("Saved  " + " · ".join(w.name for w in written) + f"   → {out_dir}")
            progress.value = 1.0
        except Exception as ex:  # noqa: BLE001
            progress.value = 0
            set_status(f"Failed — {ex}")
        finally:
            st.rendering = False
            page.update()

    # ============================================================ layout helpers
    def card(title: str, controls: list[ft.Control]) -> ft.Container:
        return ft.Container(
            bgcolor=CARD, border=_border(), border_radius=RADIUS,
            padding=16,
            content=ft.Column([
                ft.Text(title.upper(), size=10, color=FAINT, weight=ft.FontWeight.W_700),
                ft.Container(height=4),
                *controls,
            ], spacing=10))

    def field_row(btn: ft.Control, lbl: ft.Control) -> ft.Row:
        return ft.Row([btn, lbl], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    def outlined(text: str, icon: str, on_click) -> ft.OutlinedButton:
        return ft.OutlinedButton(text, icon=icon, on_click=on_click,
                                 style=ft.ButtonStyle(color=TEXT, shape=_round(10),
                                                      side=ft.BorderSide(1, BORDER),
                                                      padding=ft.Padding(14, 14, 14, 14)))

    left = ft.Container(
        width=444, bgcolor=PANEL, border=ft.Border(right=ft.BorderSide(1, BORDER)),
        padding=ft.Padding(16, 18, 16, 18),
        content=ft.Column([
            card("Source", [
                ft.Column([label("Preset"), preset_dd], spacing=6),
                field_row(outlined("Select model", ft.Icons.VIEW_IN_AR_OUTLINED, pick_model), model_label),
                field_row(outlined("Idle model", ft.Icons.ACCESSIBILITY_NEW_ROUNDED, pick_idle), idle_label),
            ]),
            card("Output", [
                ft.Row([
                    ft.Column([label("Directions"), angles_dd], spacing=6, expand=True),
                    ft.Column([label("Frames"), frames_dd], spacing=6, expand=True),
                ], spacing=12),
                ft.Row([png_cb, tga_cb], spacing=18),
                pink_cb,
            ]),
            ft.Container(height=2),
            ft.Text("ADVANCED", size=10, color=FAINT, weight=ft.FontWeight.W_700),
            sections_col,
        ], scroll=ft.ScrollMode.AUTO, spacing=14, expand=True))

    right = ft.Container(
        expand=True, padding=ft.Padding(22, 18, 22, 18),
        content=ft.Column([
            blender_bar,
            preview_panel,
            ft.Column([progress, status], spacing=6),
            ft.Row([
                outlined("Quick preview", ft.Icons.VISIBILITY_OUTLINED,
                         lambda e: page.run_thread(_do_render, True)),
                ft.FilledButton("Render sheet", icon=ft.Icons.AUTO_AWESOME_MOTION,
                                on_click=lambda e: page.run_thread(_do_render, False),
                                style=ft.ButtonStyle(bgcolor=ACCENT, color="#0b1020",
                                                     shape=_round(10),
                                                     padding=ft.Padding(20, 16, 20, 16))),
            ], alignment=ft.MainAxisAlignment.END, spacing=12),
        ], spacing=16, expand=True))

    render_view = ft.Row([left, right], expand=True, spacing=0)

    # ============================================================ guide / setup
    def step_card(step: guide.Step) -> ft.Container:
        body: list[ft.Control] = [
            ft.Text(step.title, weight=ft.FontWeight.W_700, color=TEXT, size=14),
            ft.Text(step.body, size=13, color=MUTED),
        ]
        if step.action and step.url:
            body.append(ft.FilledButton(step.action, icon=ft.Icons.OPEN_IN_NEW, url=step.url,
                                        style=ft.ButtonStyle(bgcolor=CARD_HI, color=ACCENT,
                                                             shape=_round(10))))
        return ft.Container(bgcolor=CARD, border=_border(), border_radius=RADIUS,
                            padding=18, content=ft.Column(body, spacing=8))

    def doc_view(heading: str, sub: str, steps: list[guide.Step]) -> ft.Container:
        return ft.Container(
            padding=ft.Padding(40, 30, 40, 30),
            content=ft.Column([
                ft.Text(heading, size=22, weight=ft.FontWeight.BOLD, color=TEXT),
                ft.Text(sub, size=13, color=MUTED),
                ft.Container(height=8),
                ft.Column([step_card(s) for s in steps], spacing=12, width=720),
            ], scroll=ft.ScrollMode.AUTO, spacing=6,
               horizontal_alignment=ft.CrossAxisAlignment.CENTER))

    guide_view = doc_view("From a drawing to a sprite sheet",
                          "The full pipeline, one step at a time.", guide.WORKFLOW_STEPS)
    setup_view = doc_view("First-time setup",
                          "Get Blender wired up — you only do this once.", guide.SETUP_STEPS)

    body = ft.Container(content=render_view, expand=True)
    views = {"Render": render_view, "Guide": guide_view, "Setup": setup_view}

    # ============================================================ top nav
    nav_buttons: list[ft.Container] = []

    def nav_to(name: str) -> None:
        body.content = views[name]
        for b in nav_buttons:
            active = b.data == name
            b.bgcolor = ft.Colors.with_opacity(0.16, ACCENT) if active else None
            b.content.controls[0].color = ACCENT if active else MUTED  # icon
            b.content.controls[1].color = ACCENT if active else MUTED  # text
        page.update()

    def nav_pill(name: str, icon: str) -> ft.Container:
        c = ft.Container(
            data=name, border_radius=9, padding=ft.Padding(14, 8, 14, 8),
            on_click=lambda e: nav_to(e.control.data), ink=True,
            content=ft.Row([ft.Icon(icon, size=17, color=MUTED),
                            ft.Text(name, size=13, weight=ft.FontWeight.W_600, color=MUTED)],
                           spacing=7))
        nav_buttons.append(c)
        return c

    wordmark = ft.Row([
        ft.Container(width=18, height=18, border_radius=5,
                     gradient=ft.LinearGradient(begin=ft.Alignment(-1, -1),
                                                end=ft.Alignment(1, 1),
                                                colors=[ACCENT, "#8f6dff"])),
        ft.Text("framemill", size=16, weight=ft.FontWeight.BOLD, color=TEXT),
    ], spacing=9)

    topbar = ft.Container(
        bgcolor="#0f1116", border=ft.Border(bottom=ft.BorderSide(1, BORDER)),
        padding=ft.Padding(18, 10, 18, 10),
        content=ft.Row([wordmark, ft.Container(width=26),
                        nav_pill("Render", ft.Icons.GRID_VIEW_ROUNDED),
                        nav_pill("Guide", ft.Icons.MENU_BOOK_ROUNDED),
                        nav_pill("Setup", ft.Icons.SETTINGS_ROUNDED)],
                       spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER))

    page.add(ft.Column([topbar, body], spacing=0, expand=True))
    rebuild_sections()
    refresh_blender_bar()
    nav_to("Render")


def run() -> None:
    assets = str(Path(__file__).parent / "assets")
    ft.run(main, assets_dir=assets)


if __name__ == "__main__":
    run()
