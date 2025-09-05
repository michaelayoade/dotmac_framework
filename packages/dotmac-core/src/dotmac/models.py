"""
DotMac Core Models - Stub Implementation
"""

from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict
from pydantic import BaseModel as PydanticBaseModel


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
        return cls(
            tenant_id=str(uuid4()),
            tenant_name="Test Tenant",
            domain="test.example.com",
            is_active=True,
        )
