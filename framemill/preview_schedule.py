"""Preview job sequencing: debounce, latest-wins, and cancel rules.

UI code keeps timers and Blender workers; this module only decides whether a
finished job may start another render immediately. A sequence bump while a
job is running is not enough — that would skip the debounce window.
"""
from __future__ import annotations

PREVIEW_DEBOUNCE_S = 0.45


def after_render_job(*, cancelled: bool, pending_sheet: bool, pending_preview: bool) -> str:
    """What to start when a render thread exits.

    ``start_sheet`` — a full sheet was requested while busy (internal cancel).
    ``start_preview`` — debounce already elapsed and queued a preview.
    ``idle`` — wait for an armed debounce timer, or stay stopped after user cancel.

    A newer ``preview_seq`` alone must not start a preview here.
    """
    if pending_sheet:
        return "start_sheet"
    if cancelled:
        return "idle"
    if pending_preview:
        return "start_preview"
    return "idle"


def user_cancel(seq: int) -> tuple[int, bool, bool]:
    """Invalidate debounce tokens and drop queued work. Returns new seq and cleared flags."""
    return seq + 1, False, False
