# framemill

Turn a rigged, animated **3D model into a directional 2D sprite sheet** — driven
by Blender in the background, wrapped in a small desktop app. **No Blender
knowledge required.**

Point framemill at an animated `.fbx` / `.glb` / `.gltf`, choose how many
directions and frames you want, pick a preset, and get a game-ready sheet. It's
built for the "I have a Mixamo/Tripo model and want 8-direction sprites" workflow.

![framemill](docs/images/screenshot.png)

## Why

Most 3D→sprite tools are Blender add-ons: you install them *inside* Blender and
learn its UI. framemill is the opposite — a standalone GUI that runs Blender
headless for you. The fiddly parts (consistent camera framing across an
animation, high-quality Lanczos downscaling, sprite-sheet layout, legacy-engine
TGA output) are handled automatically.

## Features

- Standalone desktop app (Windows / macOS / Linux) — Blender runs in the background.
- Import **FBX, glTF/GLB, OBJ**.
- 1 / 4 / 8 / 16 directions; any frame count; configurable frame size.
- Presets (**Generic PBR**, **Tripo**, **Mixamo**) plus exposed camera, lighting,
  ambient, colour-management and material controls for anything else.
- Export **PNG** (modern engines) or **TGA** (legacy 2D engines, optional
  magic-pink transparency).
- Optional separate *idle* model for a clean standing frame 0.
- Built-in guide: Blender setup + the drawing → Tripo → Mixamo → sheet pipeline.

## Requirements

- **Blender 4.2+** installed (framemill auto-detects it; you can also point it at
  the executable once). Blender is *not* bundled — install it separately from
  [blender.org](https://www.blender.org/download/).
- For running from source: Python 3.10+.

## Install / run from source

```bash
git clone https://github.com/framemill/framemill
cd framemill
pip install -e .
framemill            # launches the GUI
```

### CLI (for scripting / CI)

```bash
framemill render walk.fbx -o hero --preset mixamo --angles 8 --frames 8 --format png,tga
framemill render walk.fbx -o hero --idle idle.fbx        # separate idle pose
framemill inspect walk.fbx                                # print frame range + fps
```

## Packaging

Desktop builds use [`flet build`](https://flet.dev). Linux distribution is
wrapped into a portable **AppImage** (see `packaging/build_appimage.sh`); the CI
workflow in `.github/workflows/build.yml` produces artifacts for all three
platforms on tag pushes.

## How it works

```
model.fbx ──> Blender (headless, render_sprites.py) ──> per-angle PNG frames
                                                              │
                                                     compositor.py (Pillow)
                                                     crop → Lanczos → tile
                                                              │
                                                    sheet.png / sheet.tga
```

## License

MIT — see [LICENSE](LICENSE).
