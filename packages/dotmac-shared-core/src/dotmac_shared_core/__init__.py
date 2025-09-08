"""
DotMac Shared Core - Foundational utilities for the DotMac framework.

Provides lightweight, dependency-free utilities for exceptions, validation,
common operations, and type definitions that are used across all services.

Example:
    >>> from dotmac_shared_core import ValidationError, ensure_range
    >>> from dotmac_shared_core.common import time, ids
    >>> from dotmac_shared_core.types import Result
    
    >>> # Validate input
    >>> ensure_range(5, min_val=1, max_val=10)  # OK
    
    >>> # Generate IDs  
    >>> user_id = ids.new_uuid()
    >>> timestamp = time.utcnow()
    
    >>> # Handle results
    >>> result = Result.success("operation completed")
    >>> if result.ok:
    ...     print(result.value)
"""

__version__ = "1.0.0"

# Re-export stable public API
from . import common, exceptions, types, validation
from .exceptions import (
    ConflictError,
    CoreError,
    ExternalServiceError,
    ForbiddenError,
    NotFoundError,
    TimeoutError,
    UnauthorizedError,
    ValidationError,
    to_dict,
)
from .types import JSON, Result
from .validation import ensure_in, ensure_range, is_email, is_uuid, sanitize_text

__all__ = [
    # Version
    "__version__",

    # Modules
    "common",
    "exceptions",
    "types",
    "validation",

    # Direct imports from exceptions
    "CoreError",
    "ValidationError",
    "NotFoundError",
    "ConflictError",
    "UnauthorizedError",
    "ForbiddenError",
    "ExternalServiceError",
    "TimeoutError",
    "to_dict",

    # Direct imports from types
    "JSON",
    "Result",

    # Direct imports from validation
    "is_email",
    "is_uuid",
    "ensure_in",
    "ensure_range",
    "sanitize_text",
]
