from pydantic import BaseModel

"""
Core database utilities for DotMac Framework.

Consolidates database foundation classes from dotmac-database package
with production-ready patterns and error handling.
"""

import re
import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func

from .types import GUID


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models in the DotMac ecosystem.

    Provides the declarative base with type mapping for UUID support
    and common configuration for production environments.
    """

    # Type mapping for cross-database compatibility
    type_annotation_map = {
        uuid.UUID: GUID,
    }


class TimestampMixin:
    """Mixin for automatic timestamp management."""

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
        comment="Record creation timestamp",
    )

    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        server_onupdate=func.now(),
        nullable=False,
        comment="Record last update timestamp",
    )


class UUIDMixin:
    """Mixin for UUID primary key."""

    @declared_attr
    def id(cls) -> Mapped[uuid.UUID]:
        """UUID primary key column."""
        return mapped_column(
            GUID, primary_key=True, default=uuid.uuid4, nullable=False, comment="Primary key UUID"
        )


class TableNamingMixin:
    """Mixin for consistent table naming conventions."""

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Generate table name from class name."""
        # Convert CamelCase to snake_case
        name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", cls.__name__)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()


class AuditMixin:
    """Mixin for audit trail support."""

    created_by: Mapped[str | None] = mapped_column(
        sa.String(255), nullable=True, comment="User who created the record"
    )

    updated_by: Mapped[str | None] = mapped_column(
        sa.String(255), nullable=True, comment="User who last updated the record"
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True, comment="Soft delete timestamp"
    )

    deleted_by: Mapped[str | None] = mapped_column(
        sa.String(255), nullable=True, comment="User who deleted the record"
    )

    @property
    def is_deleted(self) -> bool:
        """Check if record is soft deleted."""
        return self.deleted_at is not None


class BaseModel(Base, UUIDMixin, TimestampMixin, TableNamingMixin, AuditMixin):
    """
    Base model with all common mixins applied.

    Provides:
    - UUID primary key
    - Automatic timestamps
    - Consistent table naming
    - Audit trail support
    """

    __abstract__ = True


class TenantMixin:
    """Mixin for multi-tenant models."""

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        GUID, nullable=False, index=True, comment="Tenant identifier for multi-tenancy"
    )

    @declared_attr
    def __table_args__(cls):
        """Add tenant-based constraints."""
        args = getattr(cls, "_table_args", ())
        if isinstance(args, dict):
            args = (args,)

        # Add tenant index if not already present
        has_tenant_index = any(
            hasattr(arg, "columns") and "tenant_id" in [col.name for col in arg.columns]
            for arg in args
            if hasattr(arg, "columns")
        )

        if not has_tenant_index:
            args = (*args, sa.Index(f"ix_{cls.__tablename__}_tenant_id", "tenant_id"))

        return args


class TenantBaseModel(BaseModel, TenantMixin):
    """Base model for tenant-isolated data."""

    __abstract__ = True


# Make database toolkit components available
# Import everything from the db_toolkit directory
try:
    from .db_toolkit import (
        AsyncRepository,
        BaseRepository,
        DatabaseHealthChecker,
        DatabasePaginator,
        TransactionManager,
    )
except ImportError:
    # Fallback - database toolkit not available
    BaseRepository = None
    AsyncRepository = None
    TransactionManager = None
    DatabaseHealthChecker = None
    DatabasePaginator = None
