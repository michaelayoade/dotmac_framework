"""
ID generation utilities for unique identifiers.

Provides functions for generating various types of unique identifiers
using secure random sources from the standard library.
"""

import uuid


def new_uuid() -> uuid.UUID:
    """
    Generate a new UUID4 (random UUID).
    
    Uses the system's cryptographically secure random number generator.
    
    Returns:
        New UUID4 instance
        
    Example:
        >>> id1 = new_uuid()
        >>> id2 = new_uuid()
        >>> id1 != id2  # UUIDs are unique
        True
        >>> id1.version
        4
        >>> len(str(id1))
        36  # Standard UUID string format
    """
    return uuid.uuid4()


def new_ulid() -> str:
    """
    Generate a new ULID (Universally Unique Lexicographically Sortable Identifier).
    
    Note: This is a stub implementation that returns a string representation
    of a UUID4. A true ULID implementation would require additional dependencies
    or more complex stdlib-only code for proper timestamp + randomness encoding.
    
    For production use with proper ULID features (lexicographic sorting),
    consider using a dedicated ULID library.
    
    Returns:
        String representation of a UUID4 as ULID placeholder
        
    Example:
        >>> ulid_str = new_ulid()
        >>> len(ulid_str)
        36  # UUID string length (ULID would be 26 chars)
        >>> isinstance(ulid_str, str)
        True
    """
    # Stub implementation - returns UUID4 string
    # In a full implementation, this would generate a proper ULID with:
    # - 48-bit timestamp (milliseconds since Unix epoch)
    # - 80-bit randomness
    # - Base32 encoding for 26-character string
    return str(uuid.uuid4())


__all__ = [
    "new_uuid",
    "new_ulid",
]
