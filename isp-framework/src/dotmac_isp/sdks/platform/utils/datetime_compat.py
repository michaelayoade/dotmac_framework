"""DateTime compatibility utilities for cross-platform support."""

from datetime import datetime, timezone, timedelta
from typing import Union, Optional


# UTC timezone constant
UTC = timezone.utc


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def utcnow() -> datetime:
    """Get current UTC datetime (deprecated name compatibility)."""
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    """Get current UTC datetime as ISO string."""
    return datetime.now(timezone.utc).isoformat()


def expires_in_days(days: int) -> datetime:
    """Get datetime that expires in specified days."""
    return datetime.now(timezone.utc) + timedelta(days=days)


def expires_in_hours(hours: int) -> datetime:
    """Get datetime that expires in specified hours."""
    return datetime.now(timezone.utc) + timedelta(hours=hours)


def is_expired(dt: datetime) -> bool:
    """Check if datetime has expired."""
    return datetime.now(timezone.utc) > dt


def parse_datetime(dt_string: str) -> Optional[datetime]:
    """Parse datetime string to datetime object."""
    if not dt_string:
        return None
    
    try:
        # Try parsing ISO format first
        if 'T' in dt_string:
            if dt_string.endswith('Z'):
                dt_string = dt_string[:-1] + '+00:00'
            return datetime.fromisoformat(dt_string)
        
        # Try parsing basic formats
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%d',
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(dt_string, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue
                
        return None
    except (ValueError, TypeError):
        return None


def format_datetime(dt: Union[datetime, None], fmt: str = None) -> Optional[str]:
    """Format datetime to string."""
    if dt is None:
        return None
    
    if fmt is None:
        return dt.isoformat()
    
    return dt.strftime(fmt)


def ensure_utc(dt: datetime) -> datetime:
    """Ensure datetime is in UTC timezone."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    elif dt.tzinfo != timezone.utc:
        return dt.astimezone(timezone.utc)
    return dt


def timestamp_to_datetime(timestamp: Union[int, float]) -> datetime:
    """Convert timestamp to UTC datetime."""
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def datetime_to_timestamp(dt: datetime) -> float:
    """Convert datetime to timestamp."""
    return dt.timestamp()