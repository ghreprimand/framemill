"""Atomic file promotion: stage next to the destination, then os.replace."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path


def _stage_file(dest: Path, data: bytes) -> Path:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{dest.name}.", suffix=".tmp", dir=dest.parent)
    tmp = Path(name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    return tmp


def write_all(files: dict[Path, bytes]) -> list[Path]:
    """Stage every payload, then promote together. Failure promotes nothing."""
    staged: list[tuple[Path, Path]] = []
    try:
        for dest, data in files.items():
            dest = Path(dest)
            staged.append((_stage_file(dest, data), dest))
        promoted: list[Path] = []
        for tmp, dest in staged:
            os.replace(tmp, dest)
            promoted.append(dest)
        return promoted
    except Exception:
        for tmp, _dest in staged:
            tmp.unlink(missing_ok=True)
        raise


def atomic_write_bytes(path: Path, data: bytes) -> Path:
    """Write one file via a same-directory temp, then os.replace into place."""
    return write_all({Path(path): data})[0]
