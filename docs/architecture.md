# Architecture

framemill is a thin desktop and CLI front end over a headless Blender render, followed by
a Pillow/NumPy compositor. There is no game engine and no 3D viewport of its own. It
renders sprites and lays them out.

## Pipeline

```
model.fbx ──> Blender (headless, render_sprites.py) ──> per-angle PNG frames
                                                              │
                                                     compositor.py (Pillow)
                                                     crop → Lanczos → tile
                                                              │
                                                    sheet.png / sheet.tga / .bmp
                                                              │
                                                     export.py (format, depth,
                                                     background, edge bleed, palette)
```

1. **Import and sampling** (`framemill/settings.py`, `framemill/blender/render_sprites.py`).
   Blender imports the source, reads the range of the first active action (or the scene
   range), and evaluates evenly spaced sample times, fractional frames included. Loop
   mode excludes the final endpoint; one-shot includes both. See
   [Settings reference](settings-reference.md) and [Recipes & metadata](recipes-and-metadata.md).

2. **Orientation** (`render_sprites.py`). The imported root is parented to a non-animated
   `FMOrient` empty so the source-facing yaw correction survives animation keys. The camera
   orbits around the model for each requested direction. See [Orientation](orientation.md).

3. **Render.** For every direction and frame, Blender renders a transparent PNG at the
   configured render resolution using the chosen engine, lighting, and colour management.

4. **Composite** (`framemill/compositor.py`). Each frame is cropped to the sprite aspect
   ratio (fit-this-clip bounds or a fixed world scale plus anchor), downscaled with Lanczos,
   and tiled into the sheet grid in the resolved direction and frame order.

5. **Export** (`framemill/export.py`). The composed sheet is written in the chosen format
   (PNG / TGA / BMP), bit depth (32 / 24 / 8), and background handling (alpha or colour key,
   including magic pink), with optional edge bleed, dithering, and a supplied or adaptive
   palette. Re-exporting reuses the composed sheet without rendering again.

## Modules

| Module | Responsibility |
| --- | --- |
| `framemill/app.py` | Flet desktop/web GUI: workspace, preview, export dialog, Help. |
| `framemill/cli.py` | Command-line entry point (`render`, `inspect`, `gui`). |
| `framemill/settings.py` | `RenderSettings`, sampling math, framing, validation, presets. |
| `framemill/blender/` | Blender location (`locate.py`), the headless runner, `render_sprites.py`. |
| `framemill/compositor.py` | Crop, Lanczos downscale, and sheet tiling. |
| `framemill/export.py` | Output format, depth, background, edge bleed, dithering, palettes. |
| `framemill/recipe.py` | Versioned portable project recipes. |
| `framemill/appconfig.py` | User settings and remembered Blender path. |
| `framemill/preview_schedule.py` | Debounce, latest-wins, and cancel logic for auto-preview. |
| `framemill/help_content.py` | In-app Help content model and search. |
| `framemill/guide.py` | Legacy quick-guide content (folded into help content). |

## Testing

Compositing, export, direction layout, preview settings, sampling, recipes, validation,
framing, and the preview scheduler have **Blender-free** tests (`tests/`). Sampling tests
use doubles; they do not validate Blender's actual mesh deformation, materials, or camera
output. Changes to `render_sprites.py` need a manual check against a real model. Note the
Blender version and model in your PR. Run the suite with `pytest -q`.
