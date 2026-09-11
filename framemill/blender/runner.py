"""Drive Blender headless: render frames, and inspect FBX animation metadata."""
from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from ..settings import RenderSettings

_SCRIPT = Path(__file__).parent / "render_sprites.py"


@dataclass
class RenderProgress:
    current: int
    total: int
    stage: str


ProgressCb = Callable[[RenderProgress], None]


class BlenderError(RuntimeError):
    pass


def _run(blender_path: str, args: list[str],
         on_progress: Optional[ProgressCb], total: int) -> list[str]:
    cmd = [blender_path, "--background", "--python", str(_SCRIPT), "--", *args]
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
    )
    lines: list[str] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip("\n")
        lines.append(line)
        if line.startswith("FRAMEMILL: PROGRESS") and on_progress:
            try:
                cur, tot = line.split(" ")[-1].split("/")
                on_progress(RenderProgress(int(cur), int(tot), f"Rendering {cur}/{tot}"))
            except ValueError:
                pass
    code = proc.wait()
    if code != 0:
        tail = "\n".join(lines[-25:])
        raise BlenderError(f"Blender exited with code {code}.\n{tail}")
    return lines


def inspect(blender_path: str, model_path: str) -> dict:
    """Return {frame_start, frame_end, fps} for the model's animation."""
    with tempfile.TemporaryDirectory() as tmp:
        cfg = Path(tmp) / "config.json"
        cfg.write_text("{}")
        lines = _run(
            blender_path,
            ["--input", model_path, "--output", tmp, "--config", str(cfg), "--inspect"],
            None, 0,
        )
    for line in lines:
        if line.startswith("FRAMEMILL: INSPECT "):
            return json.loads(line[len("FRAMEMILL: INSPECT "):])
    raise BlenderError("Could not read animation metadata from model.")


def render(blender_path: str, model_path: str, out_frames_dir: Path,
           settings: RenderSettings, idle_path: str | None = None,
           preview: bool = False, on_progress: Optional[ProgressCb] = None) -> None:
    """Render all angle/frame PNGs into `out_frames_dir`."""
    out_frames_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        cfg = Path(tmp) / "config.json"
        cfg.write_text(json.dumps(settings.render_config()))
        args = ["--input", model_path, "--output", str(out_frames_dir), "--config", str(cfg)]
        if idle_path:
            args += ["--idle", idle_path]
        if preview:
            args += ["--preview"]
        total = 1 if preview else settings.angles * settings.frames
        _run(blender_path, args, on_progress, total)
