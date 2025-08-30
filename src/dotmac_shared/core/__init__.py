"""
Core shared utilities for DotMac Framework.
Provides common functionality across all platforms.
"""

from .exceptions import (
    AuthorizationError,
    BusinessRuleError,
    EntityNotFoundError,
    ServiceError,
    ValidationError,
)

# Re-export commonly used classes and functions
from .pagination import PaginationParams, get_pagination_params

__all__ = [
    "PaginationParams",
    "get_pagination_params",
    "ValidationError",
    "AuthorizationError",
    "EntityNotFoundError",
    "BusinessRuleError",
    "ServiceError",
]
