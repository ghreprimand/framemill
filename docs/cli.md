# Command line (CLI)

The `framemill` command installs with the package. Use it for scripting, batch jobs, and
CI. It shares the same settings validation as the GUI.

```bash
framemill <command> [options]
```

Commands: `render`, `inspect`, `gui`.

## render

Render a sprite sheet from a model.

```bash
framemill render walk.fbx -o hero --preset mixamo --angles 8 --frames 8 --format png,tga
framemill render idle.fbx -o hero_idle --frames 16          # a separate idle sheet
framemill render --recipe hero.recipe.json -o hero --metadata
framemill render walk.fbx -o hero_compat --frames 11 --idle idle.fbx   # advanced, see below
```

| Option | Description |
| --- | --- |
| `model` | Input `.fbx` / `.glb` / `.gltf` / `.obj`. Optional when `--recipe` supplies it. |
| `-o`, `--output` | Output path. The extension is set per `--format`. Required. |
| `--preset` | Appearance preset: `generic`, `tripo`, or `mixamo`. |
| `--angles` | Directions: `1`, `4`, `8`, or `16`. |
| `--frames` | Output frame count. Must be a positive integer (1 to 64). |
| `--recipe` | Load a versioned project recipe (JSON). |
| `--idle` | Advanced. Replace frame 0 with a second model's pose. Keeps the total count, no blending. See below. |
| `--format` | Comma list of `png` and/or `tga`. Default `png`. |
| `--magic-pink` | TGA only. Write transparent pixels as magenta for legacy engines. |
| `--metadata` | Write a JSON sidecar next to each image. |
| `--blender` | Path to the Blender executable, if auto-detection fails. |

Oversized sheets and inverted source ranges are rejected before Blender starts.

## inspect

Print the detected animation frame range, action name, and source FPS used before any
overrides.

```bash
framemill inspect walk.fbx
```

## gui

Launch the desktop app (same as running `framemill` with no command in most setups).

```bash
framemill gui
```

## CLI scope vs the GUI

The CLI supports PNG/TGA export, `--recipe`, `--metadata`, and the same settings
validation as the app. It does not offer the GUI export presets, palette controls, or BMP
output. CLI recipes restore the source and render settings; their export settings are used
by the GUI only.

## The `--idle` option (advanced)

`--idle` replaces the first output cell in each direction with a second model's pose. The
total count stays the same: `--frames 11 --idle idle.fbx` produces 1 replacement plus 10
source samples, not 11 walking frames plus an idle. There is no pose blending. For a
normal idle animation, render its own sheet instead: `framemill render idle.fbx -o hero_idle`.
See [Orientation](orientation.md) and the in-app Help for the full caveats.
