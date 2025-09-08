"""
dotmac-service-kernel

Service and repository kernel for DotMac applications providing consistent
patterns for service architecture and data access.

This package provides core abstractions and protocols for building services and repositories
with consistent patterns across DotMac applications. It includes base classes, protocols,
pagination utilities, and error handling.
"""

from .errors import (
    RepositoryError,
    ServiceError,
    ValidationError,
    NotFoundError,
    ConflictError,
    ServicePermissionError,
)
from .pagination import Page
from .protocols import RepositoryProtocol, ServiceProtocol, UnitOfWork
from .types import ID, CreateSchema, UpdateSchema

__version__ = "1.0.0"

__all__ = [
    # Core protocols
    "RepositoryProtocol",
    "ServiceProtocol",
    "UnitOfWork",

    # Utilities
    "Page",

    # Exceptions
    "ServiceError",
    "RepositoryError",
    "ValidationError", 
    "NotFoundError",
    "ConflictError",
    "ServicePermissionError",

    # Types
    "ID",
    "CreateSchema",
    "UpdateSchema",
]
