"""
utils/analytics.py
-------------------
Thread-safe in-memory analytics tracker for the summarization app.

Tracks:
  - Total summaries generated (across the server lifetime)
  - Breakdown by method (extractive vs. abstractive)
  - File-based summaries count
  - Session start timestamp

No external database required — data resets on server restart.
"""

import logging
import threading
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ── Global state protected by a Lock ────────────────────────────────────────────
_lock = threading.Lock()

_stats = {
    "total": 0,
    "extractive": 0,
    "abstractive": 0,
    "file_uploads": 0,
    "started_at": datetime.now(timezone.utc).isoformat(),
}


def record_summary(method: str, from_file: bool = False) -> None:
    """
    Record a single summarization event.

    Args:
        method    : "extractive" or "abstractive"
        from_file : True if the input came from a file upload
    """
    with _lock:
        _stats["total"] += 1
        if method in ("extractive", "abstractive"):
            _stats[method] += 1
        if from_file:
            _stats["file_uploads"] += 1
    logger.debug("Recorded summary: method=%s, from_file=%s", method, from_file)


def get_stats() -> dict:
    """Return a snapshot of current analytics stats."""
    with _lock:
        return dict(_stats)
