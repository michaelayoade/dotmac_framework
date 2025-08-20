"""
Datetime utilities for API Gateway.

Provides timezone-aware datetime functions using composition patterns.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional


def utc_now() -> datetime:
    """Get current UTC datetime with timezone info."""
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    """Get current UTC datetime as ISO string."""
    return utc_now().isoformat()


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


def expires_in_hours_iso(hours: int) -> str:
    """Get ISO string for datetime that expires in specified hours."""
    return expires_in_hours(hours).isoformat()


def expires_in_days_iso(days: int) -> str:
    """Get ISO string for datetime that expires in specified days."""
    return expires_in_days(days).isoformat()


def is_expired(expires_at: Optional[datetime]) -> bool:
    """Check if datetime has expired."""
    if expires_at is None:
        return False
    return utc_now() > expires_at


def is_expired_iso(expires_at_iso: Optional[str]) -> bool:
    """Check if ISO datetime string has expired."""
    if expires_at_iso is None:
        return False
    try:
        expires_at = datetime.fromisoformat(expires_at_iso)
        return utc_now() > expires_at
    except (ValueError, TypeError):
        return True


def format_iso(dt: datetime) -> str:
    """Format datetime as ISO string."""
    return dt.isoformat()


def parse_iso(iso_string: str) -> datetime:
    """Parse ISO datetime string."""
    return datetime.fromisoformat(iso_string)


def time_ago_minutes(minutes: int) -> datetime:
    """Get datetime from minutes ago."""
    return utc_now() - timedelta(minutes=minutes)


def time_ago_hours(hours: int) -> datetime:
    """Get datetime from hours ago."""
    return utc_now() - timedelta(hours=hours)