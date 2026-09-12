# framemill documentation

Turn a rigged, animated 3D model into a directional 2D sprite sheet, driven by Blender
in the background. Start with the [project README](../README.md) for the overview; the
pages below go deeper.

## Guides

- **[Installation](installation.md):** install on Windows / macOS / Linux via pipx, the
  Linux AppImage, or from source, with per-platform update commands and Blender setup.
- **[Workflow and sampling](workflow.md):** the model-to-sheet pipeline, how frames are
  sampled, and first-frame replacement.
- **[Command line (CLI)](cli.md):** `render`, `inspect`, `--version`, shortcut commands, and every flag.
- **[Troubleshooting](troubleshooting.md):** facing, framing, textures, palettes, and output conventions.

## Reference

- **[Settings reference](settings-reference.md):** every render and export control, what
  it does, and its default.
- **[Export and palettes](export-and-palettes.md):** formats, colour depths, backgrounds,
  and the adaptive / master / fixed palette modes, including how to build a master palette.
- **[Recipes & metadata](recipes-and-metadata.md):** the portable recipe file and the
  optional JSON metadata sidecar, field by field.
- **[Direction & orientation](orientation.md):** the South-is-front convention, sheet
  ordering, and matching your game engine.
- **[Architecture](architecture.md):** how the model, Blender, compositor, and sheet
  pipeline fit together.

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for dev setup and testing notes.

---

framemill is part of **[Unfinished Works](https://unfinished-works.com)** · [source](https://github.com/ghreprimand/framemill)
