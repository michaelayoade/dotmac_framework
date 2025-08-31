"""
Database base models for DotMac ISP Framework.

Provides base classes following DRY principles by using shared patterns
without circular dependencies.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import Boolean, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models in DotMac platforms."""
    
    pass


class TimestampMixin:
    """Mixin for models that need created_at and updated_at timestamps."""

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )


class TenantModel(Base, TimestampMixin):
    """
    Base model for tenant-aware entities.
    
    Follows the shared pattern used across DotMac platforms while avoiding
    circular dependencies.
    """
    
    __abstract__ = True

    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)

    @declared_attr
    def __tablename__(cls):
        """Generate table name from class name."""
        import re
        # Convert CamelCase to snake_case
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', cls.__name__)
        name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()
        return f"isp_{name}s"  # Add plural suffix

    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }

    def soft_delete(self) -> None:
        """Soft delete the record."""
        self.is_active = False
        self.updated_at = datetime.now(timezone.utc)

    def restore(self) -> None:
        """Restore a soft-deleted record."""
        self.is_active = True
        self.updated_at = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id}, tenant_id={self.tenant_id})>"


class AuditMixin:
    """Mixin for models that need audit trail information."""

    created_by = Column(String(36), nullable=True)
    updated_by = Column(String(36), nullable=True)
    notes = Column(Text, nullable=True)

    def set_audit_info(self, user_id: str, notes: str = None) -> None:
        """Set audit information for the current operation."""
        now = datetime.now(timezone.utc)
        
        if not hasattr(self, 'created_at') or not self.created_at:
            self.created_by = user_id
            if hasattr(self, 'created_at'):
                self.created_at = now
        
        self.updated_by = user_id
        if hasattr(self, 'updated_at'):
            self.updated_at = now
        
        if notes:
            self.notes = notes


class GlobalModel(Base, TimestampMixin):
    """
    Base model for global (non-tenant-specific) entities.
    """
    
    __abstract__ = True

    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    is_active = Column(Boolean, default=True, nullable=False)

    @declared_attr
    def __tablename__(cls):
        """Generate table name from class name with global prefix."""
        import re
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', cls.__name__)
        name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()
        return f"global_{name}s"

    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id})>"