#!/usr/bin/env bash
# Wrap the `flet build linux` output into a portable .AppImage.
# Expects the Flet/Flutter bundle under build/linux (adjust if flet changes layout).
set -euo pipefail

APP=framemill
BUNDLE_DIR="${BUNDLE_DIR:-build/linux}"
OUT_DIR="dist"
APPDIR="build/${APP}.AppDir"

mkdir -p "$OUT_DIR" "$APPDIR/usr/bin"

# Copy the built app payload.
cp -r "$BUNDLE_DIR"/* "$APPDIR/usr/bin/" 2>/dev/null || {
  echo "ERROR: no bundle at $BUNDLE_DIR — run 'flet build linux' first." >&2
  exit 1
}

# Minimal desktop entry + AppRun.
cat > "$APPDIR/${APP}.desktop" <<DESK
[Desktop Entry]
Name=framemill
Exec=${APP}
Icon=${APP}
Type=Application
Categories=Graphics;Development;
DESK

# Placeholder icon (replace with docs/images/icon.png in the real project).
touch "$APPDIR/${APP}.png"

cat > "$APPDIR/AppRun" <<'RUN'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/framemill" "$@"
RUN
chmod +x "$APPDIR/AppRun"

# Fetch appimagetool if not present.
if ! command -v appimagetool >/dev/null 2>&1; then
  TOOL=build/appimagetool
  if [ ! -x "$TOOL" ]; then
    curl -sSL -o "$TOOL" \
      "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x "$TOOL"
  fi
  APPIMAGETOOL="$TOOL"
else
  APPIMAGETOOL="$(command -v appimagetool)"
fi

ARCH=x86_64 "$APPIMAGETOOL" "$APPDIR" "$OUT_DIR/${APP}-x86_64.AppImage"
echo "Wrote $OUT_DIR/${APP}-x86_64.AppImage"
