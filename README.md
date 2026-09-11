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
- 1 / 4 / 8 / 16 directions; configurable frame count and sprite dimensions.
- Automatic source preview, sprite/sheet views, direction switching, and animation playback.
- Configurable direction order, row/column layout, cycle phase, and reverse timing.
- Saved render/export settings and cancellable background renders.
- Presets (**Generic PBR**, **Tripo**, **Mixamo**) plus exposed camera, lighting,
  ambient, colour-management and material controls for anything else.
- Separate **Export sprite sheet** dialog with a processed preview: **PNG**, **TGA**,
  or **BMP**, 32/24/8-bit output, alpha or colour-key backgrounds, edge bleed,
  dithering, custom palettes, and target presets. Re-export without rendering again.
- Advanced first-frame replacement for specific engine layouts (see limitations below).
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
python -m venv .venv
# Activate: source .venv/bin/activate (Windows: .venv\Scripts\activate)
python -m pip install -e .
framemill            # launches the GUI
```

### Desktop workflow

Select a model to render a front-facing (South) preview automatically, independently
of the saved sheet start direction. South assumes the model uses the expected
front orientation; Framemill does not detect or realign the mesh. Set the appearance,
sprite dimensions, and layout, then choose **Render sheet**. Use the frame strip,
direction buttons, and playback to review the animation. **Export sprite sheet**
opens a separate output dialog and destination picker; rendering does not write
into your source folder. Export changes update the dialog preview without
starting Blender again. Appearance presets preserve your geometry and timing.

Drag the sprite or sheet to pan; scroll or pinch to zoom. The recenter button
resets pan and gesture zoom, while **Base size** sets the underlying display size.
Facing buttons request another Blender view before a sheet is rendered, and switch
instantly between rendered directions afterward. New sources start facing South.
These viewer controls do not change sheet ordering, sprite framing, or export
pixels. Use the Camera settings and render again to change output framing.
The viewer displays rendered sprites rather than a freely orbitable 3D model.

For a local browser preview of the same interface:

```bash
FRAMEMILL_WEB=1 framemill
# http://localhost:8000/
```

The browser preview loads models using absolute paths on this computer and exports
through browser downloads. The desktop app uses native file pickers.

### What animation does Framemill render?

Framemill renders the motion already present in your model. It does not create
animations, identify footsteps, or generate transitions. Walking is one use case;
idle breathing, running, talking, and other imported animations use the same pipeline.

A typical workflow is:

1. Create a textured character in Tripo or another modelling tool.
2. Rig it and apply an animation in Mixamo, Blender, or another animation tool.
   For Mixamo, upload a compatible model, apply the chosen motion, and download
   an animated FBX **with skin**, so the file contains the character mesh too.
   See [Adobe's rigging and animation guide](https://helpx.adobe.com/creative-cloud/help/mixamo-rigging-animation.html).
3. Load that animated file as Framemill's **main source**. Set the sprite count
   and directions; Framemill renders evenly spaced times from the source animation.
4. Export each animation separately: for example, load `walk.fbx` and export
   `hero_walk.png`, then load `idle.fbx` as the main source and export `hero_idle.png`.
   Use matching character scale, orientation, sprite dimensions and framing;
   inspect the anchors across sheets, since each source is framed independently.
5. Configure your game to select the idle or walk animation, its frame sequence,
   direction mapping, playback speed, and looping behavior. An image sheet does
   not encode those rules, and Framemill currently exports no animation metadata.

A static model works too: choose **1 frame** per direction. Requesting more frames
from a static source repeats the same pose; it does not animate the model.

### Sampling and current limits

- The renderer takes the range of the **first active action found on an imported
  object**. If none is found, it uses Blender's scene range. There is no clip/action
  selector, automatic stride detection, or automatic loop-boundary detection.
  Export one intended animation per source file.
- Sampling currently assumes a **loop**: with phase zero and forward playback,
  sample `i` is `start + (i / frame_count) * (end - start)`. Fractional frames are
  evaluated. The final endpoint is excluded to avoid repeating a loop's first pose.
- Odd counts such as 11 are valid; they change temporal sampling density, not
  the duration or content of the source motion. Phase shifts the starting point
  around that range, and reverse reverses its traversal.
- Non-looping actions such as attacks, jumps or deaths can be rendered, but
  **the exact ending pose is not included**, and preview playback loops them.
  There is no one-shot/include-end mode yet. Phase wrapping can also move the end
  of a one-shot action before its beginning. These actions need care; current
  output should not be assumed to preserve their full start-to-finish sequence.
- Source start/end overrides exist in the backend settings, but are not exposed
  in the desktop controls or CLI flags. Trim/select the intended clip in your
  animation tool before export. `framemill inspect model.fbx` reports the range
  used by the renderer.
- The preview FPS control changes only viewer playback. It neither resamples the
  sheet nor writes timing into the exported image. Set timing separately in-game.

### First-frame replacement (advanced)

**For a normal idle animation, load the idle FBX as the main source and export
its own sheet.** The second-model control is not an idle-sheet generator.

Under **Layout & timing → First-frame replacement (advanced)**, an optional second
model replaces the first output cell in each direction. CLI equivalent: `--idle`.
The total count stays unchanged: **11 requested frames = 1 replacement + 10 source
animation samples**, not 11 walking frames plus idle. The remaining source samples
keep their original sample times; they are not redistributed into a complete
10-frame cycle.

The replacement uses the second model's animation end pose by default, framed
with the main model's bounds. It must have matching scale, origin, orientation and
appearance. Framemill does not blend the poses or create start/stop transitions.
Preview playback includes the replacement; even skipping it in-engine leaves an
uneven sampling gap at the loop boundary.

Keep this option unset unless your target engine explicitly requires that layout
and you accept the timing tradeoff. A special idle slot has no universal meaning:
the engine must be configured or programmed to interpret it. This compatibility
option remains available; it is not the recommended way to author idle and walk
animations.

### CLI (for scripting / CI)

```bash
framemill render walk.fbx -o hero --preset mixamo --angles 8 --frames 8 --format png,tga
framemill render idle.fbx -o hero_idle --frames 16       # a separate idle animation sheet
# Advanced compatibility only: replaces the first sample, not an extra idle slot
framemill render walk.fbx -o hero_compat --frames 11 --idle idle.fbx
framemill inspect walk.fbx                                # print frame range + fps
```

## Troubleshooting and output conventions

- **Facing sideways or backward:** South is a camera convention, not automatic
  model alignment. Sheet start direction changes cell order. Preview facing
  buttons change only the view. There is no model-facing correction control yet;
  correct the source orientation in your modelling tool and export again.
- **Character drifts or looks too small:** motion that translates through space
  contributes to the whole-clip bounds. Prepare an in-place animation if your
  game moves the actor itself. Framemill does not remove root motion.
- **Weapons, feet or wide poses are clipped:** increase Camera → Framing and
  render again; larger values make the model smaller. Check all directions and
  extreme poses. Automatic framing uses model height and the compositor crops
  to the sprite aspect ratio; it is not guaranteed to fit every silhouette.
  Viewer panning and zoom do not change the exported crop.
- **Camera controls:** 90° is level; smaller values look down from above.
  Framing sets orthographic scale. Orbit distance is not a zoom control and
  also affects the light placement; use Framing to change sprite size.
- **Missing textures or no visible character:** confirm the source includes the
  mesh and its textures. Keep glTF sidecar buffers/textures and OBJ material files
  together. Open the source in Blender to check whether the issue is in the
  source or the render settings.
- **Transparency and edges:** use 32-bit PNG/TGA for alpha; use 24-bit or indexed
  output with a solid/key colour when the engine requires it. Soft edges are
  anti-aliasing. Dithering reduces colours for indexed output. Edge bleed copies
  RGB into transparent pixels without enlarging the silhouette; it does not add
  spacing between cells or remove an opaque outline.
- **Indexed engine palettes:** adaptive palettes can differ between sheets.
  Supply the same palette for related animations. If the key colour is absent,
  Framemill prepends it and truncates to 256 entries, which can change palette
  indices. Verify the result against your engine's exact index requirements.
- **Direction mapping:** clockwise from North is N → NE → E → SE → S → SW → W → NW.
  The layout panel lists the actual output order. Match that order in your game;
  do not assume its importer uses the same convention.
- **CLI scope:** the current CLI supports basic PNG/TGA export and fewer render
  controls than the desktop app. It does not load the GUI's saved settings or
  offer its export presets, palette controls, or BMP path.
- **Reporting a problem:** include OS, Blender and Framemill versions, source
  format, preset, dimensions/frame count/directions, steps, and the error text.
  A minimal source you are permitted to share helps reproduce rendering issues.

Settings are stored in `framemill/config.json` under the user configuration
directory: `$XDG_CONFIG_HOME` (or `~/.config`) on Linux,
`~/Library/Application Support` on macOS, and `%APPDATA%` on Windows.
These are application preferences, not a portable project file.

## Packaging

Desktop builds use [`flet build`](https://flet.dev). Linux distribution is
wrapped into a portable **AppImage** (see `packaging/build_appimage.sh`); the CI
workflow in `.github/workflows/build.yml` defines builds for all three
platforms. Packaging is still a development scaffold: the AppImage script uses
a placeholder icon and assumes a bundle layout. Validate clean installs and
launches on each platform before distributing binaries.

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
