"""Locate a Blender executable across platforms.

Resolution order: saved app config -> PATH -> common install locations.
Contains no machine-specific paths.
"""
from __future__ import annotations

import glob
import os
import shutil
import subprocess
from pathlib import Path

from .. import appconfig


def _candidates() -> list[str]:
    if os.name == "nt":
        pf = os.environ.get("ProgramFiles", r"C:\Program Files")
        return sorted(glob.glob(str(Path(pf) / "Blender Foundation" / "*" / "blender.exe")), reverse=True)
    if os.sys.platform == "darwin":  # type: ignore[attr-defined]
        return ["/Applications/Blender.app/Contents/MacOS/Blender"]
    # Linux
    out = ["/usr/local/bin/blender", "/usr/bin/blender", "/opt/blender/blender"]
    out += sorted(glob.glob(str(Path("/opt") / "blender*" / "blender")), reverse=True)
    out += sorted(glob.glob(str(Path.home() / "*blender*" / "blender")), reverse=True)
    return out


def find_blender() -> str | None:
    configured = appconfig.get_blender_path()
    if configured and Path(configured).is_file():
        return configured

    on_path = shutil.which("blender") or shutil.which("blender.exe")
    if on_path:
        return on_path

    for c in _candidates():
        if Path(c).is_file():
            return c
    return None


def blender_version(blender_path: str) -> str | None:
    try:
        out = subprocess.run(
            [blender_path, "--version"], capture_output=True, text=True, timeout=20, check=False
        )
        first = out.stdout.strip().splitlines()[0] if out.stdout else ""
        return first or None
    except (OSError, subprocess.SubprocessError):
        return None
