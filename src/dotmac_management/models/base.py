"""
Management Platform base models using DRY shared patterns.
"""

from sqlalchemy import JSON, Boolean, Column
from sqlalchemy.ext.declarative import declared_attr

from dotmac.database.base import AuditableMixin
from dotmac.database.base import BaseModel as SharedBaseModel

__all__ = ["BaseModel"]


class BaseModel(SharedBaseModel, AuditableMixin):
    """Management platform base model with extended capabilities."""

    __abstract__ = True

    # Soft delete support
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)

    # Metadata for extensibility
    metadata_json = Column(JSON, default=dict, nullable=False)

    @declared_attr
    def __tablename__(cls) -> str:
        """Generate table name from class name."""
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

        return name

    @property
    def is_active(self) -> bool:
        """Check if record is active (not deleted)."""
        return not self.is_deleted
