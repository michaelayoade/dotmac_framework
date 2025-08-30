"""DateTime compatibility utilities."""

from datetime import datetime, timezone
from typing import Union


def ensure_timezone(dt: Union[datetime, str]) -> datetime:
    """Ensure datetime has timezone info."""
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt


def normalize_datetime(dt: Union[datetime, str]) -> datetime:
    """Normalize datetime to UTC."""
    dt = ensure_timezone(dt)
    return dt.astimezone(timezone.utc)


def utcnow() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)
