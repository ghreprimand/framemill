# Contributing

Thanks for your interest in framemill!

## Dev setup

```bash
pip install -e ".[dev]"
pytest -q          # compositor tests (no Blender needed)
ruff check .
```

## Testing changes that touch rendering

The compositor is covered by Blender-free tests. Changes to
`framemill/blender/render_sprites.py` need a manual check against a real model —
please note in your PR which Blender version and model you tested with.

## Scope

framemill aims to stay a focused "model → directional sprite sheet" tool. Engine
-specific export quirks are welcome as optional formats; please keep defaults
neutral so the tool works for any model out of the box.
