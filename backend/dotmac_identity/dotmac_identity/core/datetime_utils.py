"""
Datetime utilities for identity management.

Provides timezone-aware datetime functions using composition patterns.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional


def utc_now() -> datetime:
    """Get current UTC datetime with timezone info."""
    return datetime.now(timezone.utc)


def utc_timestamp() -> float:
    """Get current UTC timestamp."""
    return utc_now().timestamp()


def expires_in_hours(hours: int) -> datetime:
    """Get datetime that expires in specified hours."""
    return utc_now() + timedelta(hours=hours)


def expires_in_minutes(minutes: int) -> datetime:
    """Get datetime that expires in specified minutes."""
    return utc_now() + timedelta(minutes=minutes)


def expires_in_days(days: int) -> datetime:
    """Get datetime that expires in specified days."""
    return utc_now() + timedelta(days=days)


def is_expired(expires_at: Optional[datetime]) -> bool:
    """Check if datetime has expired."""
    if expires_at is None:
        return False
    return utc_now() > expires_at


def days_since(date: datetime) -> int:
    """Get number of days since a date."""
    return (utc_now() - date).days


def format_iso(dt: datetime) -> str:
    """Format datetime as ISO string."""
    return dt.isoformat()


def parse_iso(iso_string: str) -> datetime:
    """Parse ISO datetime string."""
    return datetime.fromisoformat(iso_string)