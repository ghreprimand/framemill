# Export and palettes

The **Export sprite sheet** dialog turns the composed sheet into a file for your engine.
Re-exporting reuses the composed sheet without rendering again, so you can try formats and
palettes quickly. This page covers the format, depth, and background options, the palette
modes, and how to build a master palette. For the exact field list and defaults see the
[Settings reference](settings-reference.md).

## Format, depth, and background

| Option | Values | Notes |
| --- | --- | --- |
| Format | `png`, `tga`, `bmp` | PNG for modern engines, TGA for legacy 2D, BMP for 8-bit indexed. |
| Colour depth | `32`, `24`, `8` | 32-bit RGBA keeps alpha; 24-bit is opaque RGB; 8-bit is indexed (a palette). |
| Background | `transparent`, `magic_pink`, `solid` | How non-character pixels are filled. Transparent needs a 32-bit PNG or TGA. |
| Alpha edges | `soft`, `hard` | `soft` keeps anti-aliased edges; `hard` thresholds them at the alpha cutoff. |
| Edge bleed | pixels | Copies border colour outward into transparent pixels so downscaling does not leave a halo. It does not enlarge the silhouette. |
| Dither | `none`, `ordered`, `floyd` | Only affects reduced-colour (indexed) output. |

The dialog keeps these to reachable combinations. For example, switching to 8-bit or to BMP
drops the transparent background option and moves you to a colour key, because an indexed or
BMP image cannot store alpha.

Built-in presets: PNG RGBA (modern), PNG engine atlas (dilated), TGA magic-pink (legacy 2D),
and BMP 8-bit indexed (DOS).

### Transparency by target

- **Modern engines (PNG or TGA, 32-bit):** use `transparent` with `soft` edges. The alpha
  channel carries the cutout; the RGB under transparent pixels does not matter.
- **Legacy 2D that keys a colour (TGA or BMP):** use `magic_pink`. Fully transparent pixels
  are filled with magic pink (`#ff00ff`) so the engine can key it out.
- **8-bit indexed (DOS-style):** use `magic_pink` with 8-bit depth. The key must live in the
  palette, usually at index 0. See palettes below.

## Palettes (8-bit indexed output)

Indexed output stores a palette of up to 256 colours plus one index per pixel. framemill has
three ways to decide that palette:

- **Adaptive (from this sheet):** framemill picks the best colours from the rendered sheet.
  Fast and good-looking, but two sheets can end up with different palettes, so it is not
  ideal when several sheets must share one palette. The transparent key is placed at index 0
  automatically.
- **Master palette (file):** load a fixed palette from a file. It accepts an indexed image
  (`.bmp`, `.png`, `.gif`) or a palette list (`.pal`, `.gpl`, `.hex`). The colour order is
  read and kept exactly.
- **Custom fixed colours:** enter an ordered list of colours in the dialog. Add them one at a
  time or paste several `#RRGGBB` values at once, reorder them by dragging, and remove any you
  do not want. The first colour is index 0, the second index 1, and so on.

### Why colour order matters

A DOS-style scene shares one 256-colour palette across its background and its sprites (for
example the game's `BG_00.BMP`). If framemill reordered the colours, the sheet would no longer
line up with that shared palette, so a master palette and a fixed colour list are **never
reordered or prepended**. For indexed output the transparent key (magic pink `#ff00ff`) must
be present in the palette, usually at index 0; if it is missing, the export stops with a clear
message rather than guessing. Adaptive palettes place the key at index 0 for you.

### How to build a master palette

To share a scene's exact palette:

1. Open the scene image (for example `BG_00.BMP`) in an editor such as GIMP or Aseprite.
2. Convert it to indexed mode with the exact palette you want. Keep magic pink (`#ff00ff`) at
   index 0 for DOS transparency.
3. Either save that indexed image and point framemill at it, or export the palette on its own
   as `.pal` or `.gpl`.

You can also point framemill straight at an existing indexed BMP that already carries the
shared palette. Either way the sheet comes out using the same indices as the scene, so the
sprite and the background stay in sync.

For a small hand-authored palette, **Custom fixed colours** is quicker than making a file:
type the colours in order, magic pink first for DOS, and framemill uses them exactly.
