"""
Backward compatibility shim for dotmac_shared package.

This module provides backward compatibility for code that imports from
the old dotmac_shared package structure. All functionality has been 
moved to dotmac_shared_core.

Usage:
    # Old import (still works)
    from dotmac_shared.exceptions import ValidationError
    
    # New import (preferred)
    from dotmac_shared_core.exceptions import ValidationError

Note: This shim will be removed in a future version. Please migrate
to importing directly from dotmac_shared_core.
"""

import warnings

# Issue deprecation warning on import
warnings.warn(
    "Importing from 'dotmac_shared' is deprecated. "
    "Please use 'dotmac_shared_core' instead. "
    "This compatibility layer will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything from dotmac_shared_core for compatibility
from dotmac_shared_core import *  # noqa: F403, F401

# Also provide module-level access
from dotmac_shared_core import (  # noqa: F401
    __version__,  # noqa: F401
    common,
    exceptions,
    types,
    validation,
)

__all__ = [
    # Re-export everything from dotmac_shared_core
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
