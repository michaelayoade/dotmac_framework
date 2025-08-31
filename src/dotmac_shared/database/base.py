"""
Database base classes and models for DotMac Framework.
Provides unified database foundation for all platforms.
"""

import uuid
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import declared_attr

# Create the base class for all models
Base = declarative_base()


class BaseModel(Base):
    """Base model with common fields for all entities."""
    
    __abstract__ = True
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }


class TenantModel(BaseModel):
    """Base model for tenant-aware entities."""
    
    __abstract__ = True
    
    @declared_attr
    def tenant_id(cls):
        return Column(String(255), nullable=False, index=True)
    
    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id}, tenant_id={self.tenant_id})>"


class AuditableMixin:
    """Mixin for models that need audit trail."""
    
    created_by = Column(String(255), nullable=True)
    updated_by = Column(String(255), nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(String(255), nullable=True)
    
    @property
    def is_deleted(self) -> bool:
        """Check if entity is soft deleted."""
        return self.deleted_at is not None


class VersionedMixin:
    """Mixin for models that need versioning."""
    
    version = Column(String(50), nullable=True)
    version_number = Column(String(20), nullable=True, default="1.0")
    
    def increment_version(self):
        """Increment version number."""
        if not self.version_number:
            self.version_number = "1.0"
        else:
            parts = self.version_number.split(".")
            if len(parts) >= 2:
                minor = int(parts[1]) + 1
                self.version_number = f"{parts[0]}.{minor}"


# Export commonly used classes
__all__ = [
    "Base",
    "BaseModel", 
    "TenantModel",
    "AuditableMixin",
    "VersionedMixin",
]