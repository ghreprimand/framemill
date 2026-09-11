"""Debounce and cancel must not be bypassed by render_job cleanup."""
from framemill.preview_schedule import after_render_job, user_cancel


def test_newer_seq_alone_does_not_start_preview_before_debounce():
    # Settings changed during a job: timer is still running, pending_preview is false.
    assert after_render_job(
        cancelled=False, pending_sheet=False, pending_preview=False) == "idle"


def test_elapsed_debounce_that_hit_busy_starts_preview():
    assert after_render_job(
        cancelled=False, pending_sheet=False, pending_preview=True) == "start_preview"


def test_queued_sheet_wins_over_preview_and_cancel_flag():
    assert after_render_job(
        cancelled=True, pending_sheet=True, pending_preview=True) == "start_sheet"


def test_user_cancel_invalidates_seq_and_clears_pending():
    seq, pending_preview, pending_sheet = user_cancel(4)
    assert seq == 5
    assert pending_preview is False and pending_sheet is False
    # Stale debounce token 4 must not start work after cancel.
    assert 4 != seq
    assert after_render_job(
        cancelled=True, pending_sheet=False, pending_preview=False) == "idle"


def test_user_cancel_drops_a_queued_preview():
    seq, pending_preview, pending_sheet = user_cancel(1)
    assert after_render_job(
        cancelled=True, pending_sheet=pending_sheet,
        pending_preview=pending_preview) == "idle"
    assert seq == 2
