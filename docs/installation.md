# Installing framemill

framemill runs on **Windows, macOS, and Linux**. Pick one:

1. **pipx** (recommended, all platforms). One command; isolated; easy updates.
2. **AppImage** (Linux). A single self-contained file; no Python needed.
3. **From source**. Best if you want the latest code or plan to hack on it.

Every method needs **Blender** installed separately. It is the render engine and is
**not bundled** (see [Blender](#blender-required)).

---

## Blender (required)

framemill drives **Blender 4.2 or newer** in the background; you never open Blender
yourself. Install it once from [blender.org/download](https://www.blender.org/download/).

framemill auto-detects Blender on your `PATH` and in the usual install locations. If it
cannot find it, use the **Locate Blender** control at the bottom of the workspace to pick
the executable once. The choice is remembered.

---

## Option 1: pipx (recommended)

[pipx](https://pipx.pypa.io) installs framemill into its own isolated environment and puts
the `framemill` command on your PATH. It needs **Python 3.10+**.

Install pipx if you do not have it:

- **Windows:** `py -m pip install --user pipx` then `py -m pipx ensurepath`
- **macOS:** `brew install pipx` then `pipx ensurepath` (or `python3 -m pip install --user pipx`)
- **Linux:** `sudo apt install pipx` (or `python3 -m pip install --user pipx`) then `pipx ensurepath`

Then install framemill:

```bash
pipx install framemill
framemill            # launches the desktop GUI
```

**Update:**

```bash
pipx upgrade framemill
```

**Uninstall:**

```bash
pipx uninstall framemill
```

Because pipx installs from source into a local environment, there is no unsigned-binary
warning from Windows SmartScreen or macOS Gatekeeper.

---

## Option 2: AppImage (Linux)

Download `framemill-x86_64.AppImage` from the
[releases page](https://github.com/ghreprimand/framemill/releases), then:

```bash
chmod +x framemill-x86_64.AppImage
./framemill-x86_64.AppImage
```

The AppImage bundles Python and framemill; you still need Blender installed. If it will not
start, install FUSE (`libfuse2` on Debian/Ubuntu) or run with `--appimage-extract-and-run`.

**Update:** download the newer AppImage and replace the old file. There is no OS security
prompt to clear for an AppImage; it is not code-signed by design, and running it is just
`chmod +x` and launch.

---

## Option 3: From source

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

**Update:** `git pull` then `python -m pip install -e .` again.

For a browser preview of the same interface (useful on a headless box):

```bash
FRAMEMILL_WEB=1 framemill
# open http://localhost:8000/
```

The command-line tool ships with every install method:

```bash
framemill render walk.fbx -o hero --preset mixamo --angles 8 --frames 8 --format png,tga
framemill inspect walk.fbx
```

See the [CLI reference](cli.md) for all commands and flags.

---

## Installing a specific version or the wheel

Every release also attaches the **wheel** and **sdist** to the
[releases page](https://github.com/ghreprimand/framemill/releases). To pin a version:

```bash
pipx install framemill==0.1.1
# or install a downloaded wheel directly:
pipx install ./framemill-0.1.1-py3-none-any.whl
```

---

## Where framemill stores things

- **User settings** (`config.json`) live under your OS config directory:
  `$XDG_CONFIG_HOME` or `~/.config` (Linux), `~/Library/Application Support` (macOS),
  `%APPDATA%` (Windows). These are app preferences.
- **Recipes** are portable, versioned project files you save yourself with relative
  source paths, separate from user settings. See [Recipes & metadata](recipes-and-metadata.md).

---

## Uninstall

- **pipx:** `pipx uninstall framemill`.
- **AppImage:** delete the file.
- **From source:** delete the cloned folder and its `.venv`.

Optionally remove `config.json` from the config directory above for a clean slate.
