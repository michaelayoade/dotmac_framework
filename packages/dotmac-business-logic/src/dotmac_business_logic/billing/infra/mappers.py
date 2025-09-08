"""
SQLAlchemy ORM mappers and mixins.

This module contains the ORM-specific code including base mixins
and table mappings. This is separated from domain models to keep
the core domain framework-agnostic.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID


class BillingEntityMixin:
    """
    Base mixin for billing entities with common fields.

    Provides standard ID, timestamp, and audit fields that most
    billing entities need. Consuming packages can inherit from
    this along with their own base classes.
    """

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


# Legacy compatibility aliases for existing code
SharedBaseMixin = BillingEntityMixin


class AuditMixin:
    """Additional audit fields for entities that need detailed tracking."""

    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    version = Column('version', Integer, default=1, nullable=False)


class SoftDeleteMixin:
    """Soft delete functionality for entities that shouldn't be hard deleted."""

    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(UUID(as_uuid=True), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)

    def soft_delete(self, deleted_by_user_id: Optional[UUID] = None):
        """Mark entity as deleted."""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)
        self.deleted_by = deleted_by_user_id


class TenantMixin:
    """Tenant isolation mixin for multi-tenant entities."""

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)


# Complete base mixin combining common patterns
class FullBillingEntityMixin(BillingEntityMixin, TenantMixin, SoftDeleteMixin):
    """
    Complete entity mixin with ID, timestamps, tenant isolation, and soft delete.

    Use this for entities that need full auditing and tenant isolation.
    For simpler use cases, use BillingEntityMixin directly.
    """
    pass
