"""
Backward compatibility shim for dotmac_shared.types.

This module provides backward compatibility for code that imports types
from the old dotmac_shared.types module structure.

Note: This shim will be removed in a future version. Please migrate
to importing directly from dotmac_shared_core.types.
"""

import warnings

warnings.warn(
    "Importing from 'dotmac_shared.types' is deprecated. "
    "Please use 'dotmac_shared_core.types' instead. "
    "This compatibility layer will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything from dotmac_shared_core.types
from dotmac_shared_core.types import *  # noqa: F403, F401
