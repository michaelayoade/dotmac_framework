"""
Platform integration facade for business logic package.

Provides clean abstractions for platform services with graceful fallbacks
when optional dependencies are not available.
"""

from .dependencies import get_dependencies_facade
from .facade import PlatformFacade
from .logging import get_logger_facade

__all__ = [
    "PlatformFacade",
    "get_dependencies_facade",
    "get_logger_facade",
]
