"""Persistent app config (e.g. the Blender executable path).

Stored in the OS user-config dir, NEVER in the repo. Nothing here is committed.
"""
from __future__ import annotations

import json
import os
from pathlib import Path


def _config_dir() -> Path:
    if os.name == "nt":
        base = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
    elif os.sys.platform == "darwin":  # type: ignore[attr-defined]
        base = str(Path.home() / "Library" / "Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    return Path(base) / "framemill"


CONFIG_PATH = _config_dir() / "config.json"


def load() -> dict:
    try:
        data = json.loads(CONFIG_PATH.read_text())
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save(data: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(data, indent=2))


def get_blender_path() -> str | None:
    return load().get("blender_path")


def set_blender_path(path: str) -> None:
    data = load()
    data["blender_path"] = path
    save(data)
