"""
Database mixins for common patterns in DotMac applications.

Provides reusable mixins for:
- Soft delete functionality
- Audit trail tracking  
- Multi-tenant awareness
"""

from datetime import datetime
from typing import Optional, Union, Any

import sqlalchemy as sa
from sqlalchemy import Index, CheckConstraint
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .base import create_index_name, create_check_constraint_name
from .types import TenantIdType, UserIdType, RequestIdType


class SoftDeleteMixin:
    """
    Mixin for soft delete functionality.
    
    Adds is_active flag and optional deleted_at timestamp.
    Provides methods for soft deletion and querying active records.
    """

    is_active: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=True,
        server_default=sa.text('true'),
        index=True
    )
    
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
        index=True
    )

    @hybrid_property
    def is_deleted(self) -> bool:
        """Check if the record is soft deleted."""
        return not self.is_active

    @is_deleted.expression
    def is_deleted(cls):  # type: ignore
        """SQLAlchemy expression for is_deleted property."""
        return ~cls.is_active

    def soft_delete(self, commit_timestamp: Optional[datetime] = None) -> None:
        """
        Soft delete this record.
        
        Args:
            commit_timestamp: Optional timestamp for deletion
                             (defaults to current time)
        """
        self.is_active = False
        self.deleted_at = commit_timestamp or datetime.utcnow()

    def restore(self) -> None:
        """Restore a soft deleted record."""
        self.is_active = True
        self.deleted_at = None

    @classmethod
    def active_only(cls):
        """Query filter for active (non-deleted) records only."""
        return cls.is_active == True  # noqa: E712

    @classmethod
    def deleted_only(cls):
        """Query filter for deleted records only."""
        return cls.is_active == False  # noqa: E712

    @classmethod
    def include_deleted(cls):
        """Query filter that includes all records (active and deleted)."""
        return sa.text('1=1')  # No filtering

    @declared_attr
    def __table_args__(cls):
        """Add database constraints for soft delete."""
        args = getattr(cls, '__table_args__', ()) or ()
        if isinstance(args, dict):
            args = (args,)
        
        table_name = getattr(cls, '__tablename__', cls.__name__.lower())
        
        # Add check constraint: if deleted_at is set, is_active must be False
        check_constraint = CheckConstraint(
            '(deleted_at IS NULL) OR (is_active = false)',
            name=create_check_constraint_name(table_name, 'soft_delete_consistency')
        )
        
        # Add composite index for efficient querying
        active_index = Index(
            create_index_name(table_name, 'is_active', 'deleted_at'),
            'is_active',
            'deleted_at'
        )
        
        return args + (check_constraint, active_index)


class AuditMixin:
    """
    Mixin for audit trail functionality.
    
    Tracks who created and last updated records, along with
    optional request correlation IDs for traceability.
    """

    created_by: Mapped[Optional[UserIdType]] = mapped_column(
        sa.String(255),
        nullable=True,
        index=True
    )
    
    updated_by: Mapped[Optional[UserIdType]] = mapped_column(
        sa.String(255),
        nullable=True,
        index=True
    )
    
    request_id: Mapped[Optional[RequestIdType]] = mapped_column(
        sa.String(255),
        nullable=True,
        index=True
    )

    def set_audit_fields(
        self,
        user_id: Optional[UserIdType] = None,
        request_id: Optional[RequestIdType] = None,
        is_update: bool = False
    ) -> None:
        """
        Set audit fields for create or update operations.
        
        Args:
            user_id: ID of the user performing the operation
            request_id: Request correlation ID
            is_update: True for updates, False for creates
        """
        if not is_update and user_id is not None:
            self.created_by = str(user_id)
        
        if user_id is not None:
            self.updated_by = str(user_id)
        
        if request_id is not None:
            self.request_id = str(request_id)

    @classmethod
    def by_user(cls, user_id: UserIdType):
        """Query filter for records created by a specific user."""
        return cls.created_by == str(user_id)

    @classmethod
    def updated_by_user(cls, user_id: UserIdType):
        """Query filter for records last updated by a specific user."""
        return cls.updated_by == str(user_id)

    @classmethod
    def by_request(cls, request_id: RequestIdType):
        """Query filter for records associated with a specific request."""
        return cls.request_id == str(request_id)

    @declared_attr
    def __table_args__(cls):
        """Add database indexes for audit fields."""
        args = getattr(cls, '__table_args__', ()) or ()
        if isinstance(args, dict):
            args = (args,)
        
        table_name = getattr(cls, '__tablename__', cls.__name__.lower())
        
        # Composite index for audit queries
        audit_index = Index(
            create_index_name(table_name, 'created_by', 'created_at'),
            'created_by',
            'created_at'
        )
        
        return args + (audit_index,)


class TenantAwareMixin:
    """
    Mixin for multi-tenant aware models.
    
    Adds tenant_id field with proper indexing and constraints.
    This is a pure database mixin without framework coupling.
    """

    tenant_id: Mapped[TenantIdType] = mapped_column(
        sa.String(255),
        nullable=False,
        index=True
    )

    @classmethod
    def by_tenant(cls, tenant_id: TenantIdType):
        """Query filter for records belonging to a specific tenant."""
        return cls.tenant_id == str(tenant_id)

    @classmethod
    def exclude_tenant(cls, tenant_id: TenantIdType):
        """Query filter to exclude records from a specific tenant."""
        return cls.tenant_id != str(tenant_id)

    def belongs_to_tenant(self, tenant_id: TenantIdType) -> bool:
        """Check if this record belongs to the specified tenant."""
        return str(self.tenant_id) == str(tenant_id)

    @declared_attr
    def __table_args__(cls):
        """Add database constraints and indexes for tenant awareness."""
        args = getattr(cls, '__table_args__', ()) or ()
        if isinstance(args, dict):
            args = (args,)
        
        table_name = getattr(cls, '__tablename__', cls.__name__.lower())
        
        # Primary tenant index for efficient filtering
        tenant_index = Index(
            create_index_name(table_name, 'tenant_id'),
            'tenant_id'
        )
        
        # Composite index with created_at for tenant-specific time queries
        tenant_time_index = Index(
            create_index_name(table_name, 'tenant_id', 'created_at'),
            'tenant_id',
            'created_at'
        )
        
        return args + (tenant_index, tenant_time_index)


class TimestampMixin:
    """
    Standalone timestamp mixin for models that don't extend BaseModel.
    
    Provides created_at and updated_at fields with automatic management.
    """

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        index=True
    )

    def touch(self) -> None:
        """Manually update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()


class VersionedMixin:
    """
    Mixin for optimistic concurrency control using version numbers.
    
    Adds version field that is automatically incremented on updates.
    Useful for preventing concurrent update conflicts.
    """

    version: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=1
    )

    def increment_version(self) -> None:
        """Increment the version number."""
        self.version += 1

    @declared_attr
    def __mapper_args__(cls):
        """Configure optimistic concurrency control."""
        return {
            'version_id_col': cls.version,
            'version_id_generator': False,  # We handle incrementing manually
        }


# Convenience combination mixins
class SoftDeleteAuditMixin(SoftDeleteMixin, AuditMixin):
    """Combination mixin for soft delete with audit trail."""
    pass


class TenantAuditMixin(TenantAwareMixin, AuditMixin):
    """Combination mixin for tenant awareness with audit trail."""
    pass


class FullAuditMixin(SoftDeleteMixin, AuditMixin, TenantAwareMixin):
    """Full audit mixin combining soft delete, audit trail, and tenant awareness."""
    
    @declared_attr
    def __table_args__(cls):
        """Combine all table args from parent mixins."""
        # Get args from all parent mixins
        soft_delete_args = SoftDeleteMixin.__table_args__.fget(cls)
        audit_args = AuditMixin.__table_args__.fget(cls)  
        tenant_args = TenantAwareMixin.__table_args__.fget(cls)
        
        # Combine all args
        all_args = []
        for args in [soft_delete_args, audit_args, tenant_args]:
            if isinstance(args, tuple):
                all_args.extend(args)
            elif args:
                all_args.append(args)
        
        return tuple(all_args)