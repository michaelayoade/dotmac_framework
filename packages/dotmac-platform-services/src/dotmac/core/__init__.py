"""
DotMac Core - Convenience Import Aliases

This module provides core exceptions and models expected by the framework.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic import BaseModel as PydanticBaseModel


class DotMacError(Exception):
    """Base exception for DotMac Framework."""


class ValidationError(DotMacError):
    """Validation error."""


class AuthorizationError(DotMacError):
    """Authorization error."""


class ConfigurationError(DotMacError):
    """Configuration error."""


class BaseModel(PydanticBaseModel):
    """Base model for DotMac Framework entities."""

    model_config = ConfigDict(from_attributes=True, validate_assignment=True)


class TenantContext(BaseModel):
    """Tenant context information."""

    tenant_id: str
    tenant_name: str | None = None
    domain: str | None = None
    is_active: bool = True
    metadata: dict[str, Any] = {}

    @classmethod
    def create_default(cls) -> "TenantContext":
        """Create a default tenant context for testing."""
        from uuid import uuid4

        return cls(
            tenant_id=str(uuid4()),
            tenant_name="Test Tenant",
            domain="test.example.com",
            is_active=True,
        )


# Database compatibility functions
class DatabaseManager:
    """Compatibility database manager."""

    def __init__(self, config=None) -> None:
        self.config = config

    def get_session(self) -> None:
        """Get database session."""
        return

    def check_health(self):
        """Check database health."""
        return {"status": "ok"}


def get_db() -> None:
    """Get database connection."""
    return


def get_db_session() -> None:
    """Get database session."""
    return


def check_database_health():
    """Check database health."""
    return {"status": "ok", "message": "Database health check not implemented"}


__all__ = [
    "DotMacError",
    "ValidationError",
    "AuthorizationError",
    "ConfigurationError",
    "BaseModel",
    "TenantContext",
    "DatabaseManager",
    "get_db",
    "get_db_session",
    "check_database_health",
]
