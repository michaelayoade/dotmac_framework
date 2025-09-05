"""
ISP Framework base models using DRY shared patterns.
"""

from dotmac.database.base import Base
from dotmac.database.base import BaseModel as SharedBaseModel
from dotmac.database.mixins import ISPModelMixin
from sqlalchemy import Boolean, Column, String
from sqlalchemy.ext.declarative import declared_attr

__all__ = ["BaseModel", "Base"]


class BaseModel(SharedBaseModel, ISPModelMixin):
    """ISP framework base model with tenant-aware capabilities."""

    __abstract__ = True

    # Tenant isolation
    tenant_id = Column(String(255), nullable=False, index=True)

    # Soft delete support
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    @declared_attr
    def __tablename__(cls) -> str:
        """Generate ISP table names with prefix."""
        import re

        name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", cls.__name__)
        name = re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()

        # Simple pluralization
        if name.endswith("y"):
            name = name[:-1] + "ies"
        elif name.endswith(("s", "sh", "ch", "x", "z")):
            name = name + "es"
        else:
            name = name + "s"

        return f"isp_{name}"

    @property
    def is_deleted(self) -> bool:
        """Check if record is soft deleted."""
        return not self.is_active
