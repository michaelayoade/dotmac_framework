"""
Backward compatibility shim for dotmac_shared.validation.

This module provides backward compatibility for code that imports validation
functions from the old dotmac_shared.validation module structure.

Note: This shim will be removed in a future version. Please migrate
to importing directly from dotmac_shared_core.validation.
"""

import warnings

warnings.warn(
    "Importing from 'dotmac_shared.validation' is deprecated. "
    "Please use 'dotmac_shared_core.validation' instead. "
    "This compatibility layer will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything from dotmac_shared_core.validation
from dotmac_shared_core.validation import *  # noqa: F403, F401
