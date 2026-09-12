# framemill documentation

Turn a rigged, animated 3D model into a directional 2D sprite sheet, driven by Blender
in the background. Start with the [project README](../README.md) for the overview; the
pages below go deeper.

## Guides

- **[Installation](installation.md):** install on Windows / macOS / Linux, from source
  or prebuilt binaries, plus Blender setup and unsigned-build security warnings.
- **[Command line (CLI)](cli.md):** `render`, `inspect`, and every flag, for scripting and CI.

## Reference

- **[Settings reference](settings-reference.md):** every render and export control, what
  it does, and its default.
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
