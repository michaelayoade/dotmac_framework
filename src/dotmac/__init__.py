"""
Top-level dotmac package shims for tests.
"""

from __future__ import annotations

import importlib
import sys

# Eagerly import common subpackages to ensure availability
for subpkg in ("communications", "secrets", "core"):
    try:
        importlib.import_module(f"{__name__}.{subpkg}")
    except Exception:
        # Leave it to consumers to handle; this only aids import-time availability
        pass

__all__: list[str] = []
