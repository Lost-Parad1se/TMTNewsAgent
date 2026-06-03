"""Time helpers for consistent timestamps."""

from __future__ import annotations

from datetime import datetime, timezone


def now_iso() -> str:
    """Return the current local timestamp in ISO-8601 format."""

    return datetime.now().astimezone().isoformat(timespec="seconds")


def today_str() -> str:
    """Return the current local date in YYYY-MM-DD format."""

    return datetime.now().strftime("%Y-%m-%d")


def utc_now_iso() -> str:
    """Return the current UTC timestamp in ISO-8601 format."""

    return datetime.now(timezone.utc).isoformat(timespec="seconds")
