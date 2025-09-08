"""
Timezone-aware time utilities.

Provides functions for consistent datetime handling across services,
ensuring all datetime objects are timezone-aware and properly formatted.
"""

from datetime import datetime, timezone


def utcnow() -> datetime:
    """
    Get current UTC time as timezone-aware datetime.
    
    Returns:
        Current datetime in UTC with timezone info
        
    Example:
        >>> dt = utcnow()
        >>> dt.tzinfo == timezone.utc
        True
        >>> dt.tzinfo is not None  # Always timezone-aware
        True
    """
    return datetime.now(timezone.utc)


def to_utc(dt: datetime) -> datetime:
    """
    Convert datetime to UTC timezone.
    
    If the datetime is naive (no timezone), assumes it's already in UTC
    and attaches UTC timezone. If it has timezone info, converts to UTC.
    
    Args:
        dt: Datetime to convert
        
    Returns:
        Datetime converted to UTC timezone
        
    Example:
        >>> # Naive datetime - assumes UTC
        >>> naive_dt = datetime(2023, 1, 1, 12, 0, 0)
        >>> utc_dt = to_utc(naive_dt)
        >>> utc_dt.tzinfo == timezone.utc
        True
        
        >>> # Timezone-aware datetime - converts to UTC
        >>> from datetime import timezone, timedelta
        >>> eastern = timezone(timedelta(hours=-5))
        >>> eastern_dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=eastern)
        >>> utc_dt = to_utc(eastern_dt)
        >>> utc_dt.hour
        17  # 12 PM Eastern = 5 PM UTC
    """
    if dt.tzinfo is None:
        # Naive datetime - assume UTC and attach timezone info
        return dt.replace(tzinfo=timezone.utc)
    else:
        # Timezone-aware datetime - convert to UTC
        return dt.astimezone(timezone.utc)


def isoformat(dt: datetime) -> str:
    """
    Format datetime as ISO string with UTC timezone indicator.
    
    Always converts to UTC first, then formats with '+00:00' suffix to
    indicate UTC timezone for consistent API responses.
    
    Args:
        dt: Datetime to format
        
    Returns:
        ISO format string ending with '+00:00'
        
    Example:
        >>> dt = datetime(2023, 1, 1, 12, 30, 45, tzinfo=timezone.utc)
        >>> isoformat(dt)
        '2023-01-01T12:30:45+00:00'
        
        >>> # Converts to UTC first
        >>> from datetime import timezone, timedelta
        >>> eastern = timezone(timedelta(hours=-5))  
        >>> eastern_dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=eastern)
        >>> isoformat(eastern_dt)
        '2023-01-01T17:00:00+00:00'
    """
    utc_dt = to_utc(dt)
    return utc_dt.isoformat()


__all__ = [
    "utcnow",
    "to_utc",
    "isoformat",
]
