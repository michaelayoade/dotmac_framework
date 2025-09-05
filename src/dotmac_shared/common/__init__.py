"""
Common utilities and base classes for DotMac Framework.
This module provides shared exceptions, schemas, and decorators.
"""

from .exceptions import standard_exception_handler
from .schemas import (
    BaseCreateSchema,
    BaseResponseSchema,
    BaseUpdateSchema,
    PaginatedResponseSchema,
)

__all__ = [
    "standard_exception_handler",
    "BaseCreateSchema",
    "BaseResponseSchema",
    "BaseUpdateSchema",
    "PaginatedResponseSchema",
]
