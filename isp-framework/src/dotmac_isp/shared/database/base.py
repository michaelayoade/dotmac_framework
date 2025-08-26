"""Shared database base for DotMac ISP Framework.

This module provides the single source of truth for SQLAlchemy declarative base,
ensuring all models across the framework can be properly joined and migrated together.
"""

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, DateTime, Boolean, Text, UUID, func
from datetime import datetime, timezone
from typing import Any
import uuid


class Base(DeclarativeBase):
    """Base class for all database models in the DotMac ISP Framework.

    This ensures consistent metadata and allows for cross-module joins
    and unified migrations across all modules.
    """

    pass


class TimestampMixin:
    """Mixin for adding created_at and updated_at timestamps to models."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="When the record was created",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="When the record was last updated",
    )


class SoftDeleteMixin:
    """Mixin for adding soft delete functionality to models."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the record was soft deleted",
    )

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether the record is soft deleted",
    )

    def soft_delete(self) -> None:
        """Mark the record as soft deleted."""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self) -> None:
        """Restore a soft deleted record."""
        self.is_deleted = False
        self.deleted_at = None


class TenantMixin:
    """Mixin for adding multi-tenant support to models."""

    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        nullable=False,
        index=True,
        comment="Tenant identifier for multi-tenant isolation",
    )


class StatusMixin:
    """Mixin for adding status tracking to models."""

    status: Mapped[str] = mapped_column(
        String(50),
        default="active",
        nullable=False,
        index=True,
        comment="Current status of the record",
    )

    status_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Reason for the current status"
    )

    status_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the status was last changed",
    )

    def change_status(self, new_status: str, reason: str = None) -> None:
        """Change the status of the record."""
        self.status = new_status
        self.status_reason = reason
        self.status_changed_at = datetime.now(timezone.utc)


class AuditMixin:
    """Mixin for adding audit trail fields to models."""

    created_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
        comment="ID of the user who created the record",
    )

    updated_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
        comment="ID of the user who last updated the record",
    )

    notes: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Additional notes about the record"
    )


class BaseModel(
    Base, TimestampMixin, SoftDeleteMixin, TenantMixin, StatusMixin, AuditMixin
):
    """Complete base model with all common mixins.

    This is the recommended base class for most models in the framework.
    It includes:
    - Timestamps (created_at, updated_at)
    - Soft delete functionality
    - Multi-tenant support
    - Status tracking
    - Audit trail
    """

    __abstract__ = True

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Primary key identifier",
    )


class TenantModel(Base, TimestampMixin, StatusMixin):
    """Base model for tenant-specific entities that don't need full audit trail."""

    __abstract__ = True

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Primary key identifier",
    )

    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        nullable=False,
        index=True,
        comment="Tenant identifier for multi-tenant isolation",
    )


class SimpleModel(Base, TimestampMixin):
    """Simple base model with just timestamps for lookup tables and configurations."""

    __abstract__ = True

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Primary key identifier",
    )
