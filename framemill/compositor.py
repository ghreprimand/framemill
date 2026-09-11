"""Composite per-angle/per-frame PNGs into a sprite sheet.

Honours the configured direction order (start + rotation) and layout axis.
Pure Pillow: centre-crop to target aspect, Lanczos downscale, tile, encode.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PIL import Image

from .settings import RenderSettings

ProgressFn = Callable[[int, int, str], None]


def _crop_to_aspect(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    src_w, src_h = img.size
    target_aspect = target_w / target_h
    src_aspect = src_w / src_h
    if abs(src_aspect - target_aspect) < 1e-6:
        return img
    if src_aspect > target_aspect:
        crop_w, crop_h = int(src_h * target_aspect), src_h
    else:
        crop_w, crop_h = src_w, int(src_w / target_aspect)
    x = (src_w - crop_w) // 2
    y = (src_h - crop_h) // 2
    return img.crop((x, y, x + crop_w, y + crop_h))


def build_preview(frames_dir: Path, settings: RenderSettings) -> Image.Image:
    """Read the first rendered direction without changing its filename/layout."""
    name = settings.direction_layout()[0][0]
    with Image.open(frames_dir / f"{name}_00.png") as source:
        return _crop_to_aspect(source.convert("RGBA"), settings.frame_width,
                               settings.frame_height).resize(
            (settings.frame_width, settings.frame_height), Image.Resampling.LANCZOS)


def build_sheet(frames_dir: Path, settings: RenderSettings,
                progress: ProgressFn | None = None) -> Image.Image:
    dirs = [name for name, _ in settings.direction_layout()]
    fw, fh = settings.frame_width, settings.frame_height
    n = len(dirs)

    if settings.layout_axis == "cols":
        sheet_w, sheet_h = fw * n, fh * settings.frames

        def cell(di: int, fi: int):
            return di * fw, fi * fh
    else:
        sheet_w, sheet_h = fw * settings.frames, fh * n

        def cell(di: int, fi: int):
            return fi * fw, di * fh

    sheet = Image.new("RGBA", (sheet_w, sheet_h), (0, 0, 0, 0))
    total = n * settings.frames
    done = 0
    for di, direction in enumerate(dirs):
        for fi in range(settings.frames):
            done += 1
            fpath = frames_dir / f"{direction}_{fi:02d}.png"
            if progress:
                progress(done, total, f"Stitching {direction} {fi + 1}/{settings.frames}")
            if not fpath.exists():
                raise FileNotFoundError(f"Render is incomplete: missing {fpath.name}")
            frame = Image.open(fpath).convert("RGBA")
            if frame.size != (fw, fh):
                frame = _crop_to_aspect(frame, fw, fh).resize((fw, fh), Image.LANCZOS)
            sheet.paste(frame, cell(di, fi))
    return sheet


def save_png(sheet: Image.Image, out_path: Path) -> None:
    sheet.save(out_path, format="PNG")


def encode_tga(sheet: Image.Image, magic_pink: bool = False) -> bytes:
    """32-bit bottom-left-origin TGA (descriptor 0x08)."""
    img = sheet.convert("RGBA")
    w, h = img.size
    px = img.load()
    header = bytes([0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                    w & 0xFF, (w >> 8) & 0xFF, h & 0xFF, (h >> 8) & 0xFF, 32, 0x08])
    body = bytearray()
    for y in range(h - 1, -1, -1):
        for x in range(w):
            r, g, b, a = px[x, y]
            if magic_pink and a == 0:
                r, g, b = 255, 0, 255
            body += bytes((b, g, r, a))
    return header + bytes(body)


def save_tga(sheet: Image.Image, out_path: Path, magic_pink: bool = False) -> None:
    out_path.write_bytes(encode_tga(sheet, magic_pink=magic_pink))


def composite(frames_dir: Path, out_path: Path, settings: RenderSettings,
              formats: list[str], magic_pink: bool = False,
              progress: ProgressFn | None = None) -> list[Path]:
    sheet = build_sheet(frames_dir, settings, progress=progress)
    written: list[Path] = []
    stem = out_path.with_suffix("")
    if "png" in formats:
        p = stem.with_suffix(".png")
        save_png(sheet, p)
        written.append(p)
    if "tga" in formats:
        p = stem.with_suffix(".tga")
        save_tga(sheet, p, magic_pink=magic_pink)
        written.append(p)
    return written
