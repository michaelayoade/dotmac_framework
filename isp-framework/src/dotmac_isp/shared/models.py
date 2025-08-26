"""Shared database models and base classes."""

from datetime import datetime
from typing import Optional
from uuid import uuid4
from sqlalchemy import Column, DateTime, String, Boolean, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr

from dotmac_isp.shared.database.base import Base


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Mixin for soft delete functionality."""

    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)

    def soft_delete(self):
        """Mark record as deleted."""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self):
        """Restore soft deleted record."""
        self.is_deleted = False
        self.deleted_at = None


class TenantMixin:
    """Mixin for multi-tenant support."""

    @declared_attr
    def tenant_id(cls):
        """Tenant Id operation."""
        return Column(UUID(as_uuid=True), nullable=False, index=True)


class BaseModel(Base, TimestampMixin, SoftDeleteMixin):
    """Base model class with common fields."""

    __abstract__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)

    def __repr__(self) -> str:
        """  Repr   operation."""
        return f"<{self.__class__.__name__}(id={self.id})>"


class TenantModel(BaseModel, TenantMixin):
    """Base model class for tenant-specific data."""

    __abstract__ = True


class AuditMixin:
    """Mixin for audit trail functionality."""

    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    notes = Column(Text, nullable=True)


class StatusMixin:
    """Mixin for status tracking."""

    status = Column(String(50), default="active", nullable=False, index=True)
    status_reason = Column(Text, nullable=True)
    status_changed_at = Column(DateTime(timezone=True), nullable=True)

    def change_status(self, new_status: str, reason: Optional[str] = None):
        """Change status with timestamp and reason."""
        self.status = new_status
        self.status_reason = reason
        self.status_changed_at = datetime.now(timezone.utc)


class AddressMixin:
    """Mixin for address fields."""

    street_address = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state_province = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country_code = Column(String(2), default="US", nullable=False)

    @property
    def full_address(self) -> str:
        """Get formatted full address."""
        parts = [
            self.street_address,
            self.city,
            self.state_province,
            self.postal_code,
        ]
        return ", ".join(filter(None, parts))


class ContactMixin:
    """Mixin for contact information."""

    phone_primary = Column(String(20), nullable=True)
    phone_secondary = Column(String(20), nullable=True)
    email_primary = Column(String(255), nullable=True, index=True)
    email_secondary = Column(String(255), nullable=True)
    website = Column(String(255), nullable=True)

    @property
    def primary_contact(self) -> str:
        """Get primary contact method."""
        return self.email_primary or self.phone_primary or "No contact info"
