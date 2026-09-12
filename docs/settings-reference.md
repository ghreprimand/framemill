# Settings reference

Defaults shown are the built-in values before any preset or saved config. The GUI groups
these under **Sprite geometry**, **Appearance**, and **Layout & timing**; the values live
in `framemill/settings.py` (`RenderSettings`) and `framemill/export.py` (`ExportConfig`).

**Reset to defaults** in the export dialog returns the render and export settings to the
values in this table (export goes back to PNG RGBA). It keeps the loaded model and the
Blender path, and asks for confirmation first.

## Sprite geometry

| Setting | Default | Notes |
| --- | --- | --- |
| `angles` | `8` | Directions rendered: 1, 4, 8, or 16. |
| `frames` | `8` | Output frames per direction (1 to 64). Changes sampling density, not clip duration. |
| `frame_width` | `96` | Sprite cell width in pixels. |
| `frame_height` | `128` | Sprite cell height in pixels. |
| `render_width` | `1080` | Blender render width before downscale. Matches the 3:4 cell so no rendered pixels are cropped away. |
| `render_height` | `1440` | Blender render height before downscale. |

## Direction and layout

| Setting | Default | Notes |
| --- | --- | --- |
| `start_direction` | `S` | Which direction is the first cell. |
| `rotation` | `ccw` | `cw` or `ccw`. Clockwise from North is N, NE, E, SE, S, SW, W, NW. |
| `layout_axis` | `rows` | `rows` = directions down, frames across; `cols` = transposed. |

See [Orientation](orientation.md) for the full direction model.

## Animation and timing

| Setting | Default | Notes |
| --- | --- | --- |
| `loop_mode` | `loop` | `loop` excludes the final endpoint and wraps phase; `oneshot` includes both endpoints. |
| `phase_offset` | `0.0` | 0 to 1, shifts which pose is frame 0. Loop only. |
| `reverse` | `false` | Play the cycle backwards. |
| `anim_start_override` | none | Trim the detected source start frame. |
| `anim_end_override` | none | Trim the detected source end frame. |
| `idle_frame_index` | none | Advanced first-frame replacement slot. |
| `remove_root_motion` | `false` | Re-center the camera and light on the character every frame so a travelling clip stays centered in the cell. Fit sizing then uses the largest single-frame extent. Leave off when the source is already in-place (for example Mixamo In Place). |

## Source facing

| Setting | Default | Notes |
| --- | --- | --- |
| `source_yaw` | `0.0` | Degrees around world Z after import. Rotates the source and its animation, independent of sheet order and preview facing. |

## Framing and anchor

| Setting | Default | Notes |
| --- | --- | --- |
| `framing_mode` | `fit` | `fit` sizes each clip from its own bounds; `fixed` uses a world-unit scale and origin. |
| `fit_basis` | `height` | Fit mode only. `height` (default) scales to character height; `width` scales to the wider of X and Y; `contain` uses the larger of those so a wide pose is not cropped. |
| `ortho_scale_mult` | `1.8` | Fit multiplier. Larger values make the model smaller in the cell. |
| `framing_scale` | `2.0` | World-unit orthographic scale in fixed mode. |
| `framing_origin_x/y/z` | `0.0` | World-unit look-at point, fixed mode only. |
| `anchor` | `feet` | `feet` keeps the lowest point at a consistent cell position (best when the engine places actors by their feet); `center` uses the bounds centre. Fit mode only; fixed mode uses the origin. |
| `output_offset_x/y` | `0` | Finished-cell pixels. +X right, +Y down. |

Use fixed world scale plus a shared origin and offsets so related sheets (walk, idle,
attack) line up. Fit mode can shift between clips whose poses differ.

## Camera, light, and colour

| Setting | Default | Notes |
| --- | --- | --- |
| `camera_pitch` | `90.0` | 90 is level; smaller looks down from above. |
| `camera_distance` | `2.52` | Places the camera and the light. Not a zoom control. |
| `light_energy` | `1000.0` | Key light power. |
| `light_color` | `#FFFFFF` | Key light colour. |
| `shadow_soft_size` | `0.1` | Light softness. |
| `ambient_color` | `#FFFFFF` | Ambient/world colour. |
| `ambient_strength` | `1.0` | Ambient contribution. |
| `view_transform` | `Standard` | `Standard`, `AgX`, or `Filmic`. |
| `look` | `None` | Colour-management look. |
| `exposure` | `0.0` | Exposure stops. |
| `gamma` | `1.0` | Gamma. |
| `specular_ior` | `0.5` | Specular IOR for materials. |

## Render engine

| Setting | Default | Notes |
| --- | --- | --- |
| `engine` | `BLENDER_EEVEE` | Blender render engine. |
| `samples` | `64` | Render samples. |

## Export (`ExportConfig`)

Applied in the **Export sprite sheet** dialog. Re-exporting reuses the composed sheet
without rendering again.

| Setting | Default | Notes |
| --- | --- | --- |
| `format` | `png` | `png`, `tga`, or `bmp`. |
| `depth` | `32` | `32`, `24`, or `8` bit. |
| `background` | `transparent` | `transparent`, `magic_pink`, or `solid`. |
| `solid_color` | `#000000` | Background colour when `solid`. |
| `alpha_mode` | `soft` | `soft` keeps anti-aliased edges; `hard` thresholds them. |
| `alpha_cutoff` | `128` | Threshold for `hard` alpha. |
| `dilate` | `0` | Edge-bleed iterations in pixels. Extends hidden RGB, not the silhouette. |
| `dither` | `none` | `none`, `ordered`, or `floyd`. For reduced-colour output. |
| `palette_source` | `auto` | `auto` builds an adaptive palette from the sheet; `file` loads a master palette; `fixed` uses colours you enter. |
| `palette_path` | none | Master palette file when `palette_source` is `file`. Accepts an indexed BMP, PNG, or GIF, or a `.pal`, `.gpl`, or `.hex` file. |
| `palette_colors` | `256` | Colours for the adaptive (`auto`) palette. |
| `fixed_palette` | none | Ordered colour list when `palette_source` is `fixed`. The first colour is index 0. |
| `write_metadata` | `false` | Write a JSON sidecar next to the image. |

The `file` and `fixed` palettes keep their colour order exactly and are never reordered
or prepended, so an 8-bit sheet can share a scene's global palette (for example the
game's `BG_00.BMP`). For indexed output the transparent key (magic pink) must be present
in the palette, usually at index 0; if it is missing the export stops with a clear error.
Adaptive palettes place the key at index 0 automatically. See
[Export and palettes](export-and-palettes.md) for the palette modes and how to build and
share a master palette.

Built-in export presets: PNG RGBA (modern), PNG engine atlas (dilated), TGA magic-pink
(legacy 2D), and BMP 8-bit indexed (DOS). See [Recipes & metadata](recipes-and-metadata.md)
for the sidecar contents.
