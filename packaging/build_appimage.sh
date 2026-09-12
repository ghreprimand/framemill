#!/usr/bin/env bash
# Build a self-contained framemill AppImage with python-appimage.
#
# This bundles a relocatable manylinux CPython plus framemill and its Python
# dependencies (flet-desktop, Pillow, NumPy, ...). The user still needs Blender
# installed separately; framemill auto-detects it. Requires network access to
# fetch the manylinux base and pip dependencies, so it runs in CI, not as part
# of the offline test suite.
set -euo pipefail

PYVER="${PYVER:-3.12}"
OUT_DIR="dist"
mkdir -p "$OUT_DIR"

python -m pip install --upgrade pip build python-appimage

# Build the wheel so the AppImage installs the exact current tree.
python -m build --wheel
WHEEL_ABS="$(readlink -f "$(ls -1 dist/*.whl | head -1)")"

RECIPE_ROOT="$(mktemp -d)"
RECIPE="$RECIPE_ROOT/framemill"
mkdir -p "$RECIPE"

# python-appimage installs everything listed here into the bundled environment.
printf '%s\n' "$WHEEL_ABS" > "$RECIPE/requirements.txt"

cat > "$RECIPE/framemill.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=framemill
Exec=framemill
Icon=framemill
Categories=Graphics;Development;
Terminal=false
DESKTOP

# python-appimage expects an icon file named after the app.
cp framemill/assets/icon.svg "$RECIPE/framemill.svg"

# The entrypoint is what the AppImage runs. Launch the GUI module with the
# bundled interpreter (python-appimage puts it on PATH as python3).
cat > "$RECIPE/entrypoint" <<'ENTRY'
#! /bin/bash
exec python3 -m framemill.app "$@"
ENTRY
chmod +x "$RECIPE/entrypoint"

# Produces framemill-<pyver>-x86_64.AppImage in the current directory.
python-appimage build app -p "$PYVER" "$RECIPE"

# Normalise the output name and location.
BUILT="$(ls -1 framemill*-x86_64.AppImage 2>/dev/null | head -1 || true)"
if [ -z "$BUILT" ]; then
  echo "ERROR: python-appimage did not produce an AppImage." >&2
  exit 1
fi
mv "$BUILT" "$OUT_DIR/framemill-x86_64.AppImage"
chmod +x "$OUT_DIR/framemill-x86_64.AppImage"
echo "Wrote $OUT_DIR/framemill-x86_64.AppImage"
