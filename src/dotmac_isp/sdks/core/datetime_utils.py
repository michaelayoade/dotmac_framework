"""DateTime utilities for SDKs."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from dotmac_shared.api.exception_handlers import standard_exception_handler


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def to_iso_string(dt: datetime) -> str:
    """Convert datetime to ISO string."""
    return dt.isoformat()


def from_iso_string(iso_string: str) -> Optional[datetime]:
    """Convert ISO string to datetime."""
    try:
        return datetime.fromisoformat(iso_string)
    except ValueError:
        return None


def utc_now_iso() -> str:
    """Get current UTC datetime as ISO string."""
    return utc_now().isoformat()


# Alias for compatibility with old external services
def to_iso_string(dt: datetime) -> str:
    """Convert datetime to ISO string (alias)."""
    return dt.isoformat()


def expires_in_days(days: int) -> datetime:
    """Calculate expiration datetime N days from now."""
    return datetime.now(timezone.utc) + timedelta(days=days)


def expires_in_hours(hours: int) -> datetime:
    """Calculate expiration datetime N hours from now."""
    return datetime.now(timezone.utc) + timedelta(hours=hours)


def time_ago_minutes(minutes: int) -> datetime:
    """Calculate datetime N minutes ago."""
    return datetime.now(timezone.utc) - timedelta(minutes=minutes)


def time_ago_hours(hours: int) -> datetime:
    """Calculate datetime N hours ago."""
    return datetime.now(timezone.utc) - timedelta(hours=hours)


def is_expired_iso(iso_string: str) -> bool:
    """Check if an ISO date string represents an expired/past date."""
    try:
        dt = datetime.fromisoformat(iso_string)
        # Ensure datetime is timezone aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt < datetime.now(timezone.utc)
    except (ValueError, TypeError):
        # If we can't parse the date, consider it expired for safety
        return True


def is_valid_iso(iso_string: str) -> bool:
    """Check if a string is a valid ISO datetime."""
    try:
        datetime.fromisoformat(iso_string)
        return True
    except (ValueError, TypeError):
        return False


def add_business_days(start_date: datetime, business_days: int) -> datetime:
    """Add business days to a datetime (excluding weekends)."""
    current_date = start_date
    days_added = 0

    while days_added < business_days:
        current_date += timedelta(days=1)
        # Monday is 0, Sunday is 6
        if current_date.weekday() < 5:  # Monday to Friday
            days_added += 1

    return current_date
