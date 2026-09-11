"""Composite per-angle/per-frame PNGs into a sprite sheet.

Pure-Pillow port of the original Rust compositor: centre-crop each frame to the
target aspect, Lanczos downscale, tile into a directions x frames grid, then
encode. PNG is always produced; TGA is optional for engines that need it.
"""
from __future__ import annotations

import struct
from pathlib import Path
from typing import Callable, List, Optional

from PIL import Image

from .settings import RenderSettings, direction_names

ProgressFn = Callable[[int, int, str], None]


def _crop_to_aspect(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    src_w, src_h = img.size
    target_aspect = target_w / target_h
    src_aspect = src_w / src_h
    if abs(src_aspect - target_aspect) < 1e-6:
        return img
    if src_aspect > target_aspect:
        crop_w = int(src_h * target_aspect)
        crop_h = src_h
    else:
        crop_w = src_w
        crop_h = int(src_w / target_aspect)
    x = (src_w - crop_w) // 2
    y = (src_h - crop_h) // 2
    return img.crop((x, y, x + crop_w, y + crop_h))


def build_sheet(frames_dir: Path, settings: RenderSettings,
                progress: Optional[ProgressFn] = None) -> Image.Image:
    dirs = direction_names(settings.angles)
    fw, fh = settings.frame_width, settings.frame_height
    sheet = Image.new("RGBA", (fw * settings.frames, fh * settings.angles), (0, 0, 0, 0))

    total = settings.angles * settings.frames
    done = 0
    for row, direction in enumerate(dirs):
        for col in range(settings.frames):
            done += 1
            fpath = frames_dir / f"{direction}_{col:02d}.png"
            if progress:
                progress(done, total, f"Stitching {direction} {col + 1}/{settings.frames}")
            if not fpath.exists():
                continue
            frame = Image.open(fpath).convert("RGBA")
            if frame.size != (fw, fh):
                frame = _crop_to_aspect(frame, fw, fh).resize((fw, fh), Image.LANCZOS)
            sheet.paste(frame, (col * fw, row * fh))
    return sheet


def save_png(sheet: Image.Image, out_path: Path) -> None:
    sheet.save(out_path, format="PNG")


def encode_tga(sheet: Image.Image, magic_pink: bool = False) -> bytes:
    """32-bit bottom-left-origin TGA (image descriptor 0x08).

    Some legacy 2D engines require bottom-left origin and treat fully
    transparent pixels as magic pink (255,0,255). Enable `magic_pink` for those.
    """
    img = sheet.convert("RGBA")
    w, h = img.size
    px = img.load()

    header = bytes([
        0, 0, 2, 0, 0, 0, 0, 0,          # no ID, no colour map, uncompressed truecolour
        0, 0, 0, 0,                       # x/y origin
        w & 0xFF, (w >> 8) & 0xFF,
        h & 0xFF, (h >> 8) & 0xFF,
        32,                               # bits per pixel
        0x08,                             # descriptor: bottom-left origin, 8 alpha bits
    ])

    body = bytearray()
    for y in range(h - 1, -1, -1):        # bottom-to-top
        for x in range(w):
            r, g, b, a = px[x, y]
            if magic_pink and a == 0:
                r, g, b = 255, 0, 255
            body += bytes((b, g, r, a))    # BGRA
    return header + bytes(body)


def save_tga(sheet: Image.Image, out_path: Path, magic_pink: bool = False) -> None:
    out_path.write_bytes(encode_tga(sheet, magic_pink=magic_pink))


def composite(frames_dir: Path, out_path: Path, settings: RenderSettings,
              formats: List[str], magic_pink: bool = False,
              progress: Optional[ProgressFn] = None) -> List[Path]:
    """Build the sheet and write it in each requested format.

    `formats` may contain "png" and/or "tga". Returns the written paths.
    """
    sheet = build_sheet(frames_dir, settings, progress=progress)
    written: List[Path] = []
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
