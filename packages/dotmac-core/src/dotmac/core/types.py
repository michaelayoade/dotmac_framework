"""
Core types for DotMac Framework.

Provides common type definitions and SQLAlchemy custom types
used across the framework.
"""

import uuid
from typing import Any

from sqlalchemy import String, TypeDecorator
from sqlalchemy.dialects import postgresql


class GUID(TypeDecorator):
    """
    Platform-independent GUID type.

    Uses PostgreSQL's UUID type when available, otherwise
    uses String(36) for compatibility with other databases.
    """

    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        """Load appropriate implementation for dialect."""
        if dialect.name == "postgresql":
            return dialect.type_descriptor(postgresql.UUID())
        else:
            return dialect.type_descriptor(String(36))

    def process_bind_param(self, value: Any, dialect) -> str | None:
        """Process parameter for database binding."""
        if value is None:
            return value
        elif dialect.name == "postgresql":
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(value))
            return str(value)

    def process_result_value(self, value: Any, dialect) -> uuid.UUID | None:
        """Process value from database result."""
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            return value
