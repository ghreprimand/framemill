# Installing framemill

framemill runs on **Windows, macOS, and Linux**. There are two ways to get it:

1. **From source** (recommended). A small Python install. Best if you already have
   Python, or want the latest code and the command-line tool.
2. **Packaged binaries.** A prebuilt desktop app. No Python needed, but the builds
   are **unsigned and alpha**, so your OS will warn you the first time (see
   [Security warnings](#security-warnings-on-unsigned-builds)).

Either way you must install **Blender** separately. It is the render engine and is
**not bundled** (see [Blender](#blender-required)).

---

## Blender (required)

framemill drives **Blender 4.2 or newer** in the background; you never open Blender
yourself. Install it once from [blender.org/download](https://www.blender.org/download/).

framemill auto-detects Blender on your `PATH` and in the usual install locations. If it
cannot find it, use the **Locate Blender** control at the bottom of the workspace to pick
the executable once. The choice is remembered.

---

## Option 1: From source (recommended)

Requires **Python 3.10+**.

```bash
git clone https://github.com/ghreprimand/framemill
cd framemill
python -m venv .venv
```

Activate the virtualenv:

- **Linux / macOS:** `source .venv/bin/activate`
- **Windows (PowerShell):** `.venv\Scripts\Activate.ps1`
- **Windows (cmd):** `.venv\Scripts\activate.bat`

Then install and run:

```bash
python -m pip install -e .
framemill            # launches the desktop GUI
```

`pip install -e .` pulls framemill's Python dependencies (Flet, Pillow, NumPy) into the
project virtualenv only; nothing is installed system-wide. Blender is not a pip package.

For a browser preview of the same interface (useful on a headless box):

```bash
FRAMEMILL_WEB=1 framemill
# open http://localhost:8000/
```

The command-line tool ships with the same install:

```bash
framemill render walk.fbx -o hero --preset mixamo --angles 8 --frames 8 --format png,tga
framemill inspect walk.fbx
```

See the [CLI reference](cli.md) for all commands and flags.

---

## Option 2: Packaged binaries

Each tagged release attaches the from-source **wheel and sdist** (the primary artifacts),
and, when the build succeeds, best-effort desktop bundles produced per platform with
[`flet build`](https://flet.dev) (see `.github/workflows/release.yml`); Linux bundles can
additionally be wrapped into a portable **AppImage**. Grab them from the
[releases page](https://github.com/ghreprimand/framemill/releases).

Install the wheel directly if you prefer not to clone:

```bash
pip install framemill-0.1.0-py3-none-any.whl
framemill
```

> **The platform binaries are unsigned, best-effort, and pre-release.** They are a
> convenience, not the primary distribution channel. If anything looks off, prefer
> [installing from source](#option-1-from-source-recommended) or the wheel. You still need
> [Blender](#blender-required) installed separately.

### Security warnings on unsigned builds

Because the binaries are not code-signed or notarized, each OS shows a first-run warning.
This is expected for small open-source tools without a paid signing certificate.

**Windows (SmartScreen: "Windows protected your PC")**
1. Click **More info**.
2. Click **Run anyway**.

Only do this for a build you downloaded from the official
[releases page](https://github.com/ghreprimand/framemill/releases).

**macOS (Gatekeeper: "cannot be opened because the developer cannot be verified")**

Right-click (or Control-click) the app, choose **Open**, then **Open** again in the
dialog. Or clear the quarantine attribute from a terminal:

```bash
xattr -dr com.apple.quarantine /Applications/framemill.app
```

**Linux (AppImage)**

```bash
chmod +x framemill-x86_64.AppImage
./framemill-x86_64.AppImage
```

If it will not start, install FUSE (`libfuse2` on Debian/Ubuntu) or run with
`--appimage-extract-and-run`.

---

## Build your own binary

You can produce a bundle yourself with the Flet CLI. This needs the **Flutter SDK** plus
platform build dependencies (Linux, for example, needs GTK/mpv development packages; see
the `package` job in `.github/workflows/build.yml` for the exact list).

```bash
pip install "flet[cli]==0.86.5"        # the CI-pinned, tested version
flet build linux   --module-name main --artifact framemill      # or windows / macos
```

Wrap a verified Linux bundle into an AppImage with a **trusted local** `appimagetool`:

```bash
APPIMAGETOOL=/path/to/appimagetool bash packaging/build_appimage.sh
```

The script never downloads or executes packaging tools for you; supply a tool you trust.

---

## Where framemill stores things

- **User settings** (`config.json`) live under your OS config directory:
  `$XDG_CONFIG_HOME` or `~/.config` (Linux), `~/Library/Application Support` (macOS),
  `%APPDATA%` (Windows). These are app preferences.
- **Recipes** are portable, versioned project files you save yourself with relative
  source paths, separate from user settings. See [Recipes & metadata](recipes-and-metadata.md).

---

## Uninstall

- **From source:** delete the cloned folder and its `.venv`. Optionally remove the
  `config.json` from the config directory above.
- **Binary:** delete the app bundle or AppImage. Remove `config.json` if you want a
  clean slate.
