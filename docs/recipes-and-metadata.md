# Recipes and metadata

framemill writes two optional JSON files. A **recipe** is a portable project file you save
to reopen a setup later. A **metadata sidecar** is a neutral description of an exported
sheet for your game engine. Both are separate from the user `config.json` preferences.

## Recipes

Save a recipe from the GUI (**Save recipe**) or load one (**Load recipe**, or `--recipe`
on the CLI). Recipes are versioned JSON with **relative** source paths, so a project folder
stays portable.

Current recipe version: `1`. Loader limits: 1 MiB max, strict field set, exact version
match. Unknown fields are rejected.

```json
{
  "version": 1,
  "source": "walk.fbx",
  "idle": null,
  "settings": { "...": "render settings (see settings-reference.md)" },
  "export": { "...": "export config (see settings-reference.md)" }
}
```

- `source` is required and stored relative to the recipe file.
- `idle` is the optional advanced first-frame replacement model, or `null`.
- `export.palette_path`, if set, is also stored relative to the recipe.
- CLI recipes restore `source` and `settings`; the `export` block is used by the GUI.

## Master palettes

For 8-bit indexed output you can lock a sheet to a specific palette instead of letting
framemill build an adaptive one. Two ways:

- **Master palette (file)**: point framemill at a palette file. It accepts an indexed
  image (`.bmp`, `.png`, `.gif`) or a palette list (`.pal`, `.gpl`, `.hex`). The colour
  order is read and kept exactly.
- **Custom fixed colours**: type an ordered list of `#RRGGBB` colours in the export dialog.
  The first colour is index 0, the second index 1, and so on.

Why the order matters: a DOS scene shares one 256-colour palette across its background and
its sprites (for example the game's `BG_00.BMP`). If framemill reordered the colours, the
sheet would no longer line up with that shared palette, so it never reorders or prepends a
supplied palette. For indexed output the transparent key (magic pink `#ff00ff`) must exist
in the palette, usually at index 0; if it is missing the export stops with a clear message.
Adaptive palettes place the key at index 0 automatically.

To build a master palette from a scene image: open it in an editor such as GIMP or Aseprite,
convert to indexed mode with the exact palette you want (magic pink at index 0 for DOS),
then either save that indexed image and point framemill at it, or export the palette itself
as `.pal` or `.gpl`. You can also point framemill straight at the shared indexed BMP.

## Metadata sidecar

Enable **Write JSON sidecar** on export (or `--metadata` on the CLI) to write
`sheet.json` next to `sheet.png`. The image does not encode layout or timing rules; the
sidecar makes them explicit for an engine importer. Paths are names only, never absolute
local source locations.

Top-level keys:

| Key | Contents |
| --- | --- |
| `version` | Metadata format version. |
| `clip` | Source clip name (stem only), or `null`. |
| `dimensions` | `frame_width`, `frame_height`, `sheet_width`, `sheet_height`, `layout_axis`. |
| `layout` | `start_direction`, `rotation`, and a `directions` list with per-direction `name`, `index`, `camera_azimuth`, and cell `x`/`y`. |
| `timing` | `loop_mode`, `looping`, `frames`, `playback_fps`, `source_fps`, `source_start`, `source_end`, `sample_times`, `phase_offset`, `reverse`. |
| `orientation` | `source_yaw`. |
| `framing` | `mode`, `scale`, `origin`, `anchor`, `output_offset`, and offset unit/sign. |
| `pivot` | Resolved anchor/origin/offset for placement in-engine. |
| `replacement` | First-frame replacement info: `enabled`, `slot_index`, `replaces_existing_sample`, `adds_slot`, `blends`, `name`. |

Note the two distinct timing values: `playback_fps` is the speed you intend in-engine,
while `source_fps` is the animation's authored frame rate. framemill's frame count controls
sampling density, not playback speed.
