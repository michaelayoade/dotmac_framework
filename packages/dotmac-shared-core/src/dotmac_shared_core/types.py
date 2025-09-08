"""
Common type definitions for the DotMac framework.

Provides lightweight type aliases and result containers for consistent
typing across services without requiring external dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypeVar, Union

from .exceptions import CoreError

# JSON-serializable type union
JSON = Union[dict[str, Any], list[Any], str, int, float, bool, None]

# Generic type variable for Result container
T = TypeVar('T')


@dataclass
class Result[T]:
    """
    Container for operation results that may succeed or fail.
    
    Provides a structured way to return either a successful value or an error
    without raising exceptions, useful for functional-style error handling.
    
    Attributes:
        ok: True if the operation succeeded, False if it failed
        value: The successful result value (None if ok=False)  
        error: The error that occurred (None if ok=True)
        
    Example:
        >>> # Success case
        >>> success = Result.success("Hello world")
        >>> success.ok
        True
        >>> success.value
        'Hello world'
        >>> success.error is None
        True
        
        >>> # Error case
        >>> error = Result.error(ValidationError("Invalid input", "INVALID"))
        >>> error.ok
        False
        >>> error.value is None
        True
        >>> error.error.message
        'Invalid input'
    """

    ok: bool
    value: T | None
    error: CoreError | None

    @classmethod
    def success(cls, value: T) -> Result[T]:
        """
        Create a successful result.
        
        Args:
            value: The successful value
            
        Returns:
            Result instance with ok=True and the provided value
        """
        return cls(ok=True, value=value, error=None)

    @classmethod
    def failure(cls, error: CoreError) -> Result[T]:
        """
        Create a failed result.
        
        Args:
            error: The error that occurred
            
        Returns:
            Result instance with ok=False and the provided error
        """
        return cls(ok=False, value=None, error=error)

    # Alias for consistency with common naming patterns
    @classmethod
    def error(cls, error: CoreError) -> Result[T]:
        """Alias for failure() to match common naming patterns."""
        return cls.failure(error)

    def unwrap(self) -> T:
        """
        Get the success value or raise the error.
        
        Returns:
            The success value
            
        Raises:
            The contained error if ok=False
            
        Example:
            >>> Result.success("value").unwrap()
            'value'
            >>> Result.error(ValidationError("Bad")).unwrap()
            ValidationError: Bad
        """
        if self.ok and self.value is not None:
            return self.value
        elif self.error is not None:
            raise self.error
        else:
            # This shouldn't happen with proper usage
            raise RuntimeError("Result is in invalid state")

    def unwrap_or(self, default: T) -> T:
        """
        Get the success value or return a default.
        
        Args:
            default: Value to return if the result is an error
            
        Returns:
            The success value or the default
            
        Example:
            >>> Result.success("value").unwrap_or("default")
            'value'
            >>> Result.error(ValidationError("Bad")).unwrap_or("default")
            'default'
        """
        return self.value if self.ok else default


__all__ = [
    "JSON",
    "Result",
]
