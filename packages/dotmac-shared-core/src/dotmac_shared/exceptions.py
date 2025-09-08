"""
Backward compatibility shim for dotmac_shared.exceptions.

This module provides backward compatibility for code that imports exceptions
from the old dotmac_shared.exceptions module structure.

Note: This shim will be removed in a future version. Please migrate
to importing directly from dotmac_shared_core.exceptions.
"""

import warnings

warnings.warn(
    "Importing from 'dotmac_shared.exceptions' is deprecated. "
    "Please use 'dotmac_shared_core.exceptions' instead. "
    "This compatibility layer will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything from dotmac_shared_core.exceptions
from dotmac_shared_core.exceptions import *  # noqa: F403, F401
