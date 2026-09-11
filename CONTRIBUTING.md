# Contributing

Thanks for your interest in framemill!

## Dev setup (project-local virtualenv)

framemill's Python dependencies live in a **per-project virtualenv** — they are
not installed system-wide. Nothing here needs to be registered with your OS
package manager; `pyproject.toml` is the source of truth for dependencies.

```bash
python3 -m venv .venv
. .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"     # framemill + Flet, Pillow, pytest, ruff

framemill                    # launch the GUI
pytest -q                    # compositor tests (no Blender needed)
ruff check .
```

Blender is **not** a pip dependency — install it separately from
[blender.org](https://www.blender.org/download/). framemill auto-detects it.

## Testing changes that touch rendering

The compositor is covered by Blender-free tests. Changes to
`framemill/blender/render_sprites.py` need a manual check against a real model —
please note in your PR which Blender version and model you tested with.

## Scope

framemill aims to stay a focused "model -> directional sprite sheet" tool.
Engine-specific export quirks are welcome as optional formats; please keep
defaults neutral so the tool works for any model out of the box.
