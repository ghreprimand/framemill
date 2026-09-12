# Troubleshooting and output conventions

## Facing and framing

- **Facing sideways or backward:** South is a camera convention. Sheet start direction
  changes cell order; preview facing buttons change only the view. Use **Source facing**
  (quarter turns or yaw) to rotate the imported source and its animation. That does not
  change sheet order. See [Orientation](orientation.md).
- **Character drifts or looks too small:** motion that translates through space contributes
  to the whole-clip bounds. Prefer an in-place animation if your game moves the actor, or
  enable **Remove root motion** (Layout & timing) to re-center each frame at render time.
  For matching clips across sheets, use Fixed world scale and the same world-unit origin
  plus output offsets (+X right, +Y down in the cell) rather than Fit-this-clip.
- **Weapons, feet, or wide poses are clipped:** increase Camera → Fit multiplier or Fixed
  world scale and render again; larger values make the model smaller. Check all directions
  and extreme poses. Fit mode defaults to character height (Fit basis); switch to Fit whole
  character if a wide pose crops at the sides. Viewer pan and zoom do not change the
  exported crop.
- **Character looks tiny or the fit box is huge:** the Source line shows mesh count and
  world-space W x D x H after inspect. Many meshes or unexpected dimensions usually mean
  stray geometry (a ground plane, oversized effect mesh) is enlarging the frame. Remove or
  hide that geometry in the source; framemill does not auto-exclude meshes.
- **Camera controls:** 90 degrees is level; smaller values look down from above. Framing
  sets orthographic scale. Orbit distance is not a zoom control and also affects light
  placement; use Framing to change sprite size.

## Textures, transparency, and palettes

- **Missing textures or no visible character:** confirm the source includes the mesh and its
  textures. Keep glTF sidecar buffers and textures, and OBJ material files, together. Open
  the source in Blender to check whether the issue is in the source or the render settings.
- **Transparency and edges:** use 32-bit PNG/TGA for alpha; use 24-bit or indexed output
  with a solid or key colour when the engine requires it. Soft edges are anti-aliasing.
  Dithering reduces colours for indexed output. Edge bleed copies RGB into transparent
  pixels without enlarging the silhouette; it does not add spacing between cells or remove
  an opaque outline.
- **Indexed engine palettes:** adaptive palettes can differ between sheets, so supply the
  same master palette (a file or a fixed colour list) for related animations. A supplied
  palette keeps its colour order exactly and is never reordered, so the sheet stays in sync
  with a scene's shared palette. For indexed output the transparent key (magic pink) must be
  present, usually at index 0; if it is missing the export stops with a clear message.
  Adaptive palettes place the key at index 0 automatically. See
  [Recipes & metadata](recipes-and-metadata.md) for building a master palette.

## Layout and mapping

- **Direction mapping:** clockwise from North is N, NE, E, SE, S, SW, W, NW. The layout
  panel lists the actual output order. Match that order in your game; do not assume its
  importer uses the same convention.
- **Recipes, validation, and size limits:** Save recipe writes a versioned JSON file with
  relative source paths. Invalid frames, inverted ranges, and oversized sheets are rejected
  before render. The CLI also rejects zero or negative `--frames` and unknown `--format`
  values. See [Recipes & metadata](recipes-and-metadata.md).

## Where settings live

Settings are stored in `config.json` under the user configuration directory:
`$XDG_CONFIG_HOME` or `~/.config` on Linux, `~/Library/Application Support` on macOS, and
`%APPDATA%` on Windows. These are application preferences. Use **Save recipe** for a
portable, versioned project file; that is separate from the user config.

## Reporting a problem

Open an issue at [github.com/ghreprimand/framemill/issues](https://github.com/ghreprimand/framemill/issues).
Include your OS, Blender and framemill versions, source format, preset, dimensions, frame
count, directions, the steps you took, and the error text. A minimal model you are permitted
to share helps reproduce rendering issues. The CLI currently has fewer controls and export
formats than the app.
