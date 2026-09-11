#!/usr/bin/env bash
# Wrap a verified Flet Linux bundle. Supply a trusted appimagetool executable.
set -euo pipefail

APP=framemill
OUT_DIR=dist

find_bundle() {
  if [ -n "${BUNDLE_DIR:-}" ]; then
    if [ -f "$BUNDLE_DIR/$APP" ] && [ -x "$BUNDLE_DIR/$APP" ]; then
      printf '%s\n' "$BUNDLE_DIR"
      return
    fi
    echo "ERROR: BUNDLE_DIR must contain an executable named framemill." >&2
    exit 1
  fi
  local candidate
  for candidate in build/linux build/flutter/linux/x64/release/bundle build/linux/x64/release/bundle; do
    if [ -f "$candidate/$APP" ] && [ -x "$candidate/$APP" ]; then
      printf '%s\n' "$candidate"
      return
    fi
  done
  echo "ERROR: no runnable bundle found. Run flet build linux --artifact framemill first." >&2
  exit 1
}

BUNDLE_DIR="$(find_bundle)"
APPIMAGETOOL="${APPIMAGETOOL:-$(command -v appimagetool || true)}"
if [ -z "$APPIMAGETOOL" ] || [ ! -x "$APPIMAGETOOL" ]; then
  echo "ERROR: install a trusted appimagetool, or set APPIMAGETOOL to its executable path." >&2
  exit 1
fi

mkdir -p build "$OUT_DIR"
# A fresh directory prevents stale files from a previous build entering a release.
APPDIR="$(mktemp -d build/framemill.AppDir.XXXXXX)"
mkdir -p "$APPDIR/usr/bin"
cp -a "$BUNDLE_DIR"/. "$APPDIR/usr/bin/"
cp framemill/assets/icon.svg "$APPDIR/$APP.svg"

cat > "$APPDIR/$APP.desktop" <<'DESKTOP'
[Desktop Entry]
Name=framemill
Exec=framemill
Icon=framemill
Type=Application
Categories=Graphics;Development;
DESKTOP

cat > "$APPDIR/AppRun" <<'RUN'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/framemill" "$@"
RUN
chmod +x "$APPDIR/AppRun"
ARCH=x86_64 "$APPIMAGETOOL" "$APPDIR" "$OUT_DIR/$APP-x86_64.AppImage"
echo "Wrote $OUT_DIR/$APP-x86_64.AppImage"
