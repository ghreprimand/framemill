"""Install and remove a per-user desktop launcher for the framemill GUI."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

_ASSET_DIR = Path(__file__).resolve().parent / "assets"


class ShortcutError(Exception):
    """User-facing failure while creating or removing a launcher."""


def asset_file(name: str) -> Path:
    path = _ASSET_DIR / name
    if not path.is_file():
        raise ShortcutError(f"Missing packaged icon: {path.name}")
    return path


def resolve_gui_target() -> Path:
    found = shutil.which("framemill-gui") or shutil.which("framemill")
    if not found:
        raise ShortcutError(
            "Could not find framemill-gui or framemill on PATH. "
            "Install framemill so those commands are available."
        )
    return Path(found)


def linux_desktop_entry(exec_path: str, icon_name: str = "framemill") -> str:
    """Pure .desktop body. Exec is quoted when it contains spaces."""
    executable = f'"{exec_path}"' if any(ch.isspace() for ch in exec_path) else exec_path
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=framemill\n"
        "Comment=Turn a rigged 3D model into a directional 2D sprite sheet\n"
        f"Exec={executable}\n"
        f"Icon={icon_name}\n"
        "Terminal=false\n"
        "Categories=Graphics;Development;2DGraphics;\n"
    )


def linux_desktop_path() -> Path:
    return Path.home() / ".local" / "share" / "applications" / "framemill.desktop"


def linux_icon_path() -> Path:
    return (
        Path.home() / ".local" / "share" / "icons" / "hicolor" / "scalable" / "apps"
        / "framemill.svg"
    )


def macos_app_dir() -> Path:
    return Path.home() / "Applications" / "framemill.app"


def windows_start_menu_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    return Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs"


def windows_data_dir() -> Path:
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return Path(local) / "framemill"
    return Path.home() / "AppData" / "Local" / "framemill"


def write_ico(png: Path, dest: Path) -> None:
    image = Image.open(png).convert("RGBA")
    dest.parent.mkdir(parents=True, exist_ok=True)
    image.save(dest, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])


def write_icns(png: Path, dest: Path) -> None:
    image = Image.open(png).convert("RGBA")
    dest.parent.mkdir(parents=True, exist_ok=True)
    image.save(dest, format="ICNS")


def macos_launcher_script(exec_path: str) -> str:
    quoted = json.dumps(exec_path)
    return f"#!/bin/sh\nexec {quoted} \"$@\"\n"


def macos_info_plist() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0">\n'
        "<dict>\n"
        "  <key>CFBundleName</key><string>framemill</string>\n"
        "  <key>CFBundleDisplayName</key><string>framemill</string>\n"
        "  <key>CFBundleIdentifier</key><string>com.unfinished-works.framemill</string>\n"
        "  <key>CFBundleExecutable</key><string>framemill</string>\n"
        "  <key>CFBundleIconFile</key><string>framemill</string>\n"
        "  <key>CFBundlePackageType</key><string>APPL</string>\n"
        "  <key>LSMinimumSystemVersion</key><string>11.0</string>\n"
        "</dict>\n"
        "</plist>\n"
    )


def _refresh_linux_database(applications: Path) -> None:
    updater = shutil.which("update-desktop-database")
    if not updater:
        return
    try:
        subprocess.run([updater, str(applications)], check=False, capture_output=True)
    except OSError:
        return


def _install_linux(target: Path) -> Path:
    desktop = linux_desktop_path()
    icon = linux_icon_path()
    desktop.parent.mkdir(parents=True, exist_ok=True)
    icon.parent.mkdir(parents=True, exist_ok=True)
    desktop.write_text(linux_desktop_entry(str(target)), encoding="utf-8")
    shutil.copyfile(asset_file("icon.svg"), icon)
    _refresh_linux_database(desktop.parent)
    return desktop


def _install_macos(target: Path) -> Path:
    app = macos_app_dir()
    contents = app / "Contents"
    macos = contents / "MacOS"
    resources = contents / "Resources"
    macos.mkdir(parents=True, exist_ok=True)
    resources.mkdir(parents=True, exist_ok=True)
    launcher = macos / "framemill"
    launcher.write_text(macos_launcher_script(str(target)), encoding="utf-8")
    launcher.chmod(0o755)
    (contents / "Info.plist").write_text(macos_info_plist(), encoding="utf-8")
    write_icns(asset_file("icon.png"), resources / "framemill.icns")
    return app


def _create_windows_shortcut(lnk: Path, target: Path, icon: Path) -> None:
    script = (
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut("
        f"{json.dumps(str(lnk))}); "
        f"$s.TargetPath = {json.dumps(str(target))}; "
        f"$s.IconLocation = {json.dumps(str(icon))}; "
        f"$s.WorkingDirectory = {json.dumps(str(target.parent))}; "
        "$s.Save()"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        check=True, capture_output=True, text=True,
    )


def _install_windows(target: Path) -> Path:
    icon = windows_data_dir() / "framemill.ico"
    write_ico(asset_file("icon.png"), icon)
    lnk = windows_start_menu_dir() / "framemill.lnk"
    lnk.parent.mkdir(parents=True, exist_ok=True)
    _create_windows_shortcut(lnk, target, icon)
    return lnk


def install_shortcut() -> Path:
    target = resolve_gui_target()
    if sys.platform.startswith("linux"):
        return _install_linux(target)
    if sys.platform == "darwin":
        return _install_macos(target)
    if sys.platform == "win32":
        return _install_windows(target)
    raise ShortcutError(f"Desktop shortcuts are not supported on {sys.platform}.")


def _remove(path: Path) -> Path | None:
    if path.is_symlink() or path.is_file():
        path.unlink()
        return path
    if path.is_dir():
        shutil.rmtree(path)
        return path
    return None


def uninstall_shortcut() -> list[Path]:
    if sys.platform.startswith("linux"):
        candidates = [linux_desktop_path(), linux_icon_path()]
        applications = linux_desktop_path().parent
    elif sys.platform == "darwin":
        candidates = [macos_app_dir()]
        applications = None
    elif sys.platform == "win32":
        candidates = [windows_start_menu_dir() / "framemill.lnk",
                      windows_data_dir() / "framemill.ico"]
        applications = None
    else:
        raise ShortcutError(f"Desktop shortcuts are not supported on {sys.platform}.")
    removed = [path for path in (_remove(item) for item in candidates) if path is not None]
    if applications is not None:
        _refresh_linux_database(applications)
    return removed
