"""
Backward compatibility shim for dotmac_shared.common.ids.

This module provides backward compatibility for code that imports ID utilities
from the old dotmac_shared.common.ids module structure.

Note: This shim will be removed in a future version. Please migrate
to importing directly from dotmac_shared_core.common.ids.
"""

import warnings

warnings.warn(
    "Importing from 'dotmac_shared.common.ids' is deprecated. "
    "Please use 'dotmac_shared_core.common.ids' instead. "
    "This compatibility layer will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything from dotmac_shared_core.common.ids
from dotmac_shared_core.common.ids import *  # noqa: F403, F401
