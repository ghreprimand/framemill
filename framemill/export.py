"""Sprite-sheet export: colour depth, backgrounds, edge dilation, indexing,
dithering, palettes, and per-platform presets.

The compositor produces a clean 32-bit RGBA sheet; this module turns that into
whatever a given engine needs. All passes are pure Pillow + numpy and unit
tested without Blender.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

RGB = tuple[int, int, int]
MAGENTA: RGB = (255, 0, 255)

# 4x4 Bayer matrix (normalised 0..1) for ordered dithering.
_BAYER4 = np.array([
    [0, 8, 2, 10],
    [12, 4, 14, 6],
    [3, 11, 1, 9],
    [15, 7, 13, 5],
], dtype=np.float32) / 16.0 - 0.5


@dataclass
class ExportConfig:
    format: str = "png"                 # png | tga | bmp
    depth: int = 32                     # 32 | 24 | 8
    background: str = "transparent"     # transparent | magic_pink | solid
    solid_color: str = "#000000"
    alpha_mode: str = "soft"            # soft | hard
    alpha_cutoff: int = 128
    dilate: int = 0                     # edge-bleed iterations (pixels)
    dither: str = "none"                # none | ordered | floyd
    palette_source: str = "auto"        # auto | file | fixed
    palette_path: str | None = None
    palette_colors: int = 256           # for auto
    fixed_palette: list[RGB] | None = None


# ----------------------------------------------------------------- colour utils
def hex_to_rgb(s: str) -> RGB:
    s = (s or "#000000").lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


# ----------------------------------------------------------------- passes
def dilate_edges(img: Image.Image, iterations: int) -> Image.Image:
    """Bleed border colour outward into transparent pixels (alpha preserved).

    Prevents dark fringing when the sheet is later keyed, hard-thresholded, or
    bilinear-filtered. This is the "pull the outer pixel around the perimeter"
    operation.
    """
    if iterations <= 0:
        return img
    arr = np.array(img.convert("RGBA"))
    rgb = arr[:, :, :3].astype(np.float32)
    alpha = arr[:, :, 3]
    valid = alpha > 0
    for _ in range(iterations):
        if valid.all():
            break
        acc = np.zeros_like(rgb)
        cnt = np.zeros(alpha.shape, np.float32)
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)):
            sv = np.roll(np.roll(valid, dy, 0), dx, 1)
            sr = np.roll(np.roll(rgb, dy, 0), dx, 1)
            if dy > 0:
                sv[:dy, :] = False
            elif dy < 0:
                sv[dy:, :] = False
            if dx > 0:
                sv[:, :dx] = False
            elif dx < 0:
                sv[:, dx:] = False
            acc += np.where(sv[:, :, None], sr, 0.0)
            cnt += sv
        fill = (~valid) & (cnt > 0)
        mean = acc / np.maximum(cnt, 1)[:, :, None]
        rgb = np.where(fill[:, :, None], mean, rgb)
        valid = valid | fill
    out = arr.copy()
    out[:, :, :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def threshold_alpha(img: Image.Image, cutoff: int) -> Image.Image:
    arr = np.array(img.convert("RGBA"))
    arr[:, :, 3] = np.where(arr[:, :, 3] >= cutoff, 255, 0).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def flatten(img: Image.Image, key: RGB) -> Image.Image:
    """Drop alpha, filling fully-transparent pixels with `key` (RGB out)."""
    arr = np.array(img.convert("RGBA"))
    transparent = arr[:, :, 3] == 0
    rgb = arr[:, :, :3].copy()
    rgb[transparent] = key
    return Image.fromarray(rgb, "RGB")


# ----------------------------------------------------------------- palettes
def load_palette(path: str) -> list[RGB]:
    """Parse a GIMP .gpl, JASC .pal, or plain hex/rgb list."""
    text = Path(path).read_text(errors="ignore").splitlines()
    colors: list[RGB] = []
    lower = path.lower()
    if lower.endswith(".gpl"):
        for line in text:
            line = line.strip()
            if not line or line.startswith("#") or line[0].isalpha():
                continue
            parts = line.split()
            if len(parts) >= 3 and parts[0].isdigit():
                colors.append((int(parts[0]), int(parts[1]), int(parts[2])))
    elif lower.endswith(".pal"):
        started = False
        for line in text:
            line = line.strip()
            if line.startswith("JASC") or line == "0100":
                started = True
                continue
            if not started:
                continue
            parts = line.split()
            if len(parts) >= 3 and parts[0].isdigit():
                colors.append((int(parts[0]), int(parts[1]), int(parts[2])))
    else:  # hex or "r,g,b" per line
        for line in text:
            line = line.strip()
            if not line or line.startswith("#") and " " in line:
                pass
            if line.startswith("#") and len(line) in (4, 7):
                colors.append(hex_to_rgb(line))
            elif "," in line:
                p = [int(x) for x in line.split(",")[:3]]
                colors.append((p[0], p[1], p[2]))
    if not colors:
        raise ValueError(f"No colours parsed from palette: {path}")
    return colors[:256]


def _palette_image(colors: list[RGB]) -> Image.Image:
    flat: list[int] = []
    for c in colors[:256]:
        flat.extend(c)
    flat += list(colors[-1]) * (256 - len(colors))
    pal = Image.new("P", (1, 1))
    pal.putpalette(flat)
    return pal


def _resolve_palette(rgb: Image.Image, cfg: ExportConfig, key: RGB | None) -> list[RGB]:
    if cfg.palette_source == "file":
        if not cfg.palette_path:
            raise ValueError("Choose a palette file first.")
        colors = load_palette(cfg.palette_path)
    elif cfg.palette_source == "fixed":
        if not cfg.fixed_palette:
            raise ValueError("Enter at least one fixed palette colour.")
        colors = [tuple(c) for c in cfg.fixed_palette]
    else:  # auto — adaptive palette from the image
        q = rgb.quantize(colors=min(cfg.palette_colors, 256), dither=Image.Dither.NONE)
        pal = q.getpalette() or []
        colors = [tuple(pal[i:i + 3]) for i in range(0, min(len(pal), 256 * 3), 3)]
    if key is not None and key not in colors:
        colors = ([key] + colors)[:256]
    return colors


def to_indexed(rgb: Image.Image, cfg: ExportConfig, key: RGB | None) -> Image.Image:
    colors = _resolve_palette(rgb, cfg, key)
    palimg = _palette_image(colors)
    if cfg.dither == "floyd":
        return rgb.quantize(palette=palimg, dither=Image.Dither.FLOYDSTEINBERG)
    if cfg.dither == "ordered":
        arr = np.array(rgb).astype(np.float32)
        h, w = arr.shape[:2]
        tile = np.tile(_BAYER4, (h // 4 + 1, w // 4 + 1))[:h, :w]
        arr = np.clip(arr + tile[:, :, None] * 32.0, 0, 255).astype(np.uint8)
        rgb = Image.fromarray(arr, "RGB")
    return rgb.quantize(palette=palimg, dither=Image.Dither.NONE)


# ----------------------------------------------------------------- TGA encoders
def _tga(img: Image.Image, bits: int, magic_pink: bool = False) -> bytes:
    """Bottom-left-origin TGA (descriptor 0x08). 32 or 24 bit."""
    im = img.convert("RGBA")
    w, h = im.size
    px = im.load()
    header = bytes([0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                    w & 0xFF, (w >> 8) & 0xFF, h & 0xFF, (h >> 8) & 0xFF, bits, 0x08])
    body = bytearray()
    for y in range(h - 1, -1, -1):
        for x in range(w):
            r, g, b, a = px[x, y]
            if magic_pink and a == 0:
                r, g, b = MAGENTA
            if bits == 32:
                body += bytes((b, g, r, a))
            else:
                body += bytes((b, g, r))
    return header + bytes(body)


# ----------------------------------------------------------------- main entry
def process(sheet: Image.Image, cfg: ExportConfig) -> Image.Image:
    """Apply the full pixel pipeline, returning a PIL image in final mode."""
    if cfg.format not in ("png", "tga", "bmp") or cfg.depth not in (8, 24, 32):
        raise ValueError("Choose a supported format and colour depth.")
    if cfg.background not in ("transparent", "magic_pink", "solid"):
        raise ValueError("Choose a supported background.")
    if cfg.background == "transparent" and (cfg.depth != 32 or cfg.format == "bmp"):
        raise ValueError("Transparent output requires 32-bit PNG or TGA. Use a colour key for indexed output.")
    if cfg.format == "bmp" and cfg.depth == 32:
        raise ValueError("Choose 24-bit or indexed 8-bit for BMP.")
    if not 2 <= cfg.palette_colors <= 256:
        raise ValueError("Palette size must be between 2 and 256 colours.")
    img = sheet.convert("RGBA")
    if cfg.dilate:
        img = dilate_edges(img, cfg.dilate)
    if cfg.alpha_mode == "hard":
        img = threshold_alpha(img, cfg.alpha_cutoff)

    key: RGB | None = None
    if cfg.background == "magic_pink":
        key = MAGENTA
    elif cfg.background == "solid":
        key = hex_to_rgb(cfg.solid_color)
        backdrop = Image.new("RGBA", img.size, (*key, 255))
        img = Image.alpha_composite(backdrop, img)

    if cfg.depth == 32 and cfg.background == "transparent":
        return img  # RGBA
    if cfg.depth == 32:  # keep alpha but also stamp key colour into holes
        if key is not None:
            arr = np.array(img)
            arr[arr[:, :, 3] == 0, :3] = key
            img = Image.fromarray(arr, "RGBA")
        return img

    # 24 / 8 bit -> must flatten. Transparent with no alpha channel falls back to key.
    fill = key if key is not None else MAGENTA
    rgb = flatten(img, fill)
    if cfg.depth == 24:
        return rgb
    indexed = to_indexed(rgb, cfg, key=fill)
    # Dithering must never perturb the exact key in transparent pixels.
    palette = indexed.getpalette()
    key_index = next(i for i in range(256)
                     if tuple(palette[i * 3:i * 3 + 3]) == fill)
    pixels = np.array(indexed)
    pixels[np.array(img)[:, :, 3] == 0] = key_index
    result = Image.fromarray(pixels, "P")
    result.putpalette(palette)
    return result


def save(sheet: Image.Image, out_path: Path, cfg: ExportConfig) -> Path:
    img = process(sheet, cfg)
    stem = out_path.with_suffix("")
    if cfg.format == "png":
        p = stem.with_suffix(".png")
        img.save(p)
    elif cfg.format == "bmp":
        p = stem.with_suffix(".bmp")
        if cfg.depth == 32:
            img = img.convert("RGB")  # BMP alpha is unreliable; downgrade
        img.save(p)
    elif cfg.format == "tga":
        p = stem.with_suffix(".tga")
        if cfg.depth == 8:
            img.save(p)  # Pillow writes colour-mapped TGA
        else:
            p.write_bytes(_tga(img, 32 if cfg.depth == 32 else 24,
                               magic_pink=cfg.background == "magic_pink"))
    else:
        raise ValueError(f"Unknown format: {cfg.format}")
    return p


# ----------------------------------------------------------------- presets
@dataclass
class ExportPreset:
    key: str
    label: str
    config: ExportConfig


EXPORT_PRESETS: dict[str, ExportPreset] = {
    "png_rgba": ExportPreset("png_rgba", "PNG · RGBA (modern)",
                             ExportConfig(format="png", depth=32, background="transparent",
                                          alpha_mode="soft", dilate=2)),
    "png_engine": ExportPreset("png_engine", "PNG · engine atlas (dilated)",
                               ExportConfig(format="png", depth=32, background="transparent",
                                            alpha_mode="soft", dilate=4)),
    "tga_legacy": ExportPreset("tga_legacy", "TGA · magic-pink (legacy 2D)",
                               ExportConfig(format="tga", depth=32, background="magic_pink",
                                            alpha_mode="hard", alpha_cutoff=128, dilate=2)),
    "bmp_dos8": ExportPreset("bmp_dos8", "BMP · 8-bit indexed (DOS)",
                             ExportConfig(format="bmp", depth=8, background="magic_pink",
                                          alpha_mode="hard", alpha_cutoff=128, dilate=1,
                                          dither="ordered", palette_source="auto",
                                          palette_colors=256)),
}

DEFAULT_EXPORT = "png_rgba"
