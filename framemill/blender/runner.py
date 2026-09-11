"""Drive Blender headless: render frames, and inspect FBX animation metadata."""
from __future__ import annotations

import json
import subprocess
import tempfile
import threading
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

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
         on_progress: ProgressCb | None, total: int,
         cancel: threading.Event | None = None) -> list[str]:
    cmd = [blender_path, "--background", "--python-exit-code", "1", "--python", str(_SCRIPT), "--", *args]
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
    )
    finished = threading.Event()

    def watch_cancel():
        while not finished.wait(0.1):
            if cancel is not None and cancel.is_set():
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                return

    if cancel is not None:
        threading.Thread(target=watch_cancel, daemon=True).start()
    lines = deque(maxlen=200)

    assert proc.stdout is not None
    try:
        for line in proc.stdout:
            line = line.rstrip("\n")
            lines.append(line)
            if line.startswith("FRAMEMILL: PROGRESS") and on_progress:
                try:
                    cur, tot = line.split(" ")[-1].split("/")
                    current, count = int(cur), int(tot)
                except ValueError:
                    continue
                on_progress(RenderProgress(current, count, f"Rendering {current}/{count}"))
        code = proc.wait()
    finally:
        finished.set()
        proc.stdout.close()
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
    if cancel is not None and cancel.is_set():
        raise BlenderError("Render cancelled.")
    if code != 0:
        tail = "\n".join(list(lines)[-25:])
        raise BlenderError(f"Blender exited with code {code}.\n{tail}")
    return list(lines)


def inspect(blender_path: str, model_path: str) -> dict:
    """Return {frame_start, frame_end, fps, action, duration_frames} for the model."""
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
           preview: bool = False, on_progress: ProgressCb | None = None,
           cancel: threading.Event | None = None) -> None:
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
        _run(blender_path, args, on_progress, total, cancel)
