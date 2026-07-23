"""
AlphaPass – Shared utility helpers.
Single source of truth for helpers used across multiple routers.
"""
from datetime import datetime, timezone
from typing import Any, Optional


def format_dt(val: Any) -> Optional[datetime]:
    """Parse any date-ish value into a timezone-aware datetime, or return None."""
    if not val:
        return None
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc)
        return val
    try:
        dt = datetime.fromisoformat(str(val))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None
