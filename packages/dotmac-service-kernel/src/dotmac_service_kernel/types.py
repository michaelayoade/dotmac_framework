"""
Type definitions for the service kernel.

This module provides common type aliases and generic type variables used throughout
the service kernel components.
"""

from typing import TypeVar, Union
from uuid import UUID

# Type aliases for common ID types
ID = Union[int, str, UUID]

# Generic type variables for entities and schemas
T = TypeVar("T")  # Entity type
CreateSchema = TypeVar("CreateSchema")  # Create schema type
UpdateSchema = TypeVar("UpdateSchema")  # Update schema type

# Generic type variable for any type
Any = TypeVar("Any")

__all__ = [
    "ID",
    "T",
    "CreateSchema",
    "UpdateSchema",
    "Any",
]
