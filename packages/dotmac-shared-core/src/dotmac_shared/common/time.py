"""
Backward compatibility shim for dotmac_shared.common.time.

This module provides backward compatibility for code that imports time utilities
from the old dotmac_shared.common.time module structure.

Note: This shim will be removed in a future version. Please migrate
to importing directly from dotmac_shared_core.common.time.
"""

import warnings

warnings.warn(
    "Importing from 'dotmac_shared.common.time' is deprecated. "
    "Please use 'dotmac_shared_core.common.time' instead. "
    "This compatibility layer will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything from dotmac_shared_core.common.time
from dotmac_shared_core.common.time import *  # noqa: F403, F401
