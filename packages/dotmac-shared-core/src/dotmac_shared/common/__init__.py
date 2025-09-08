"""
Backward compatibility shim for dotmac_shared.common.

This module provides backward compatibility for code that imports common
utilities from the old dotmac_shared.common module structure.

Note: This shim will be removed in a future version. Please migrate
to importing directly from dotmac_shared_core.common.
"""

import warnings

warnings.warn(
    "Importing from 'dotmac_shared.common' is deprecated. "
    "Please use 'dotmac_shared_core.common' instead. "
    "This compatibility layer will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything from dotmac_shared_core.common
from dotmac_shared_core.common import *  # noqa: F403, F401
