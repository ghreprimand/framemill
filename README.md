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
- Configurable direction order, row/column layout, loop or one-shot sampling,
  source-range trim, cycle phase, and reverse timing.
- Source-facing yaw (quarter turns or a numeric angle), independent of sheet
  order and preview facing.
- Shared framing: fit or fixed world scale, centre/feet anchor, output offsets.
- Versioned portable recipes and an optional JSON animation-metadata sidecar.
- Settings and aggregate sheet-size validation before render.
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
of the saved sheet start direction. If the mesh faces the wrong axis, use
**Layout & timing → Source facing** (Left/Right 90° or a yaw value); that rotates
the imported source and its animation without changing sheet order. Set the appearance,
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
pixels. Camera, lighting, orientation and timing refresh the preview after a
short pause; **Render sheet** still replaces the exportable sheet.
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
   and directions. Choose **Loop** (walk cycles) or **One-shot** (attacks, deaths).
   Trim the detected source start/end if needed. Save a recipe to reopen the same
   setup later.
4. Export each animation separately: for example, load `walk.fbx` and export
   `hero_walk.png`, then load `idle.fbx` as the main source and export `hero_idle.png`.
   Lock **Fixed world scale** and the same world-unit origin (typically the
   character's root at 0,0,0) plus output offsets so related sheets match. Fit
   mode still sizes each clip from its own bounds and will shift if poses differ.
5. Configure your game to select the idle or walk animation, its frame sequence,
   direction mapping, playback speed, and looping behavior. Optionally enable
   **Write JSON sidecar** on export for layout, sample times, playback vs source
   FPS, loop mode and pivot. The image itself does not encode those rules.

A static model works too: choose **1 frame** per direction. Requesting more frames
from a static source repeats the same pose; it does not animate the model.

### Sampling and current limits

- The renderer takes the range of the **first active action found on an imported
  object**. If none is found, it uses Blender's scene range. The workspace shows
  the detected action, start, end, span and source FPS. Start/end fields trim
  that range. There is no full NLA / multi-clip selector or automatic stride
  detection. Export one intended animation per source file.
- **Loop** keeps the walk-cycle formula: with phase zero and forward playback,
  sample `i` is `start + (i / frame_count) * (end - start)`. Fractional frames are
  evaluated. The final endpoint is excluded to avoid repeating a loop's first pose.
  Phase wraps; reverse wraps.
- **One-shot** includes both endpoints when there are two or more frames, ignores
  phase, and reverses without wrapping. A single one-shot frame is the start pose
  (or the end pose if reverse is on). Preview playback stops on the last frame
  instead of looping.
- Odd counts such as 11 are valid; they change temporal sampling density, not
  the duration or content of the source motion.
- `framemill inspect model.fbx` reports the range, action name and source FPS
  used before overrides.
- The preview FPS control changes only viewer playback. Frame count changes
  sampling density. Optional metadata records both `playback_fps` and `source_fps`.

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
framemill render --recipe hero.recipe.json -o hero --metadata
# Advanced compatibility only: replaces the first sample, not an extra idle slot
framemill render walk.fbx -o hero_compat --frames 11 --idle idle.fbx
framemill inspect walk.fbx                                # print frame range, action, fps
```

`--frames` must be a positive integer. `--format` accepts `png` and/or `tga`.
Oversized sheets and inverted source ranges are rejected before Blender starts.

## Troubleshooting and output conventions

- **Facing sideways or backward:** South is a camera convention. Sheet start
  direction changes cell order. Preview facing buttons change only the view.
  Use **Source facing** (quarter turns or yaw) to rotate the imported source
  and its animation. That does not change sheet order.
- **Character drifts or looks too small:** motion that translates through space
  contributes to the whole-clip bounds. Prepare an in-place animation if your
  game moves the actor itself. Framemill does not remove root motion. For
  matching clips, use Fixed world scale and the same world-unit origin plus
  output offsets (+X right, +Y down in the cell) rather than Fit-this-clip.
- **Weapons, feet or wide poses are clipped:** increase Camera → Fit multiplier
  or Fixed world scale and render again; larger values make the model smaller.
  Check all directions and extreme poses. Fit mode uses model height and the
  compositor crops to the sprite aspect ratio; it is not guaranteed to fit every
  silhouette. Viewer panning and zoom do not change the exported crop.
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
- **CLI scope:** the CLI supports PNG/TGA export, `--recipe`, `--metadata`, and
  the same settings validation as the app. It does not offer the GUI export
  presets, palette controls, or BMP output. CLI recipes currently restore source
  and render settings; their export settings are used by the GUI only.
- **Reporting a problem:** include OS, Blender and Framemill versions, source
  format, preset, dimensions/frame count/directions, steps, and the error text.
  A minimal source you are permitted to share helps reproduce rendering issues.

Settings are stored in `framemill/config.json` under the user configuration
directory: `$XDG_CONFIG_HOME` (or `~/.config`) on Linux,
`~/Library/Application Support` on macOS, and `%APPDATA%` on Windows.
These are application preferences. Use **Save recipe** for a portable, versioned
project file with relative source paths; that is separate from the user config.

## Packaging

Desktop builds use [`flet build`](https://flet.dev) with the repository `main.py`
entrypoint; CI pins the tested Flet CLI to 0.86.5.
Linux bundles can be wrapped into an **AppImage** using
`packaging/build_appimage.sh` and a trusted local `appimagetool` executable.
The script does not download or execute packaging tools automatically.
CI uploads the Linux bundle if that tool is unavailable. The workflow in
`.github/workflows/build.yml` defines builds for all three platforms. Packaging
is still a development scaffold. This checkout has not validated clean installs
or launches on Windows, macOS, or a clean Linux machine — do that before
distributing binaries.

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
