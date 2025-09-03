"""Database model mixins for DRY patterns across all ISP modules."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, String, Boolean, Index, event
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy import String as SQLString
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Session
import uuid

from .tenant_isolation import get_current_tenant, TenantIsolationError


class GUID(TypeDecorator):
    """Platform-independent GUID type.
    
    Uses PostgreSQL's UUID type when available, otherwise 
    uses CHAR(32) storing as stringified hex values.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PGUUID())
        else:
            return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return "%.32x" % uuid.UUID(value).int
            else:
                return "%.32x" % value.int

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            else:
                return value


class TenantIsolationMixin:
    """Enhanced tenant isolation mixin with automatic tenant detection."""
    
    @declared_attr
    def tenant_id(cls):
        """Tenant ID column with automatic population."""
        return Column(String(255), nullable=False, index=True)
    
    @declared_attr
    def __table_args__(cls):
        """Add tenant-specific indexes to all tenant-aware tables."""
        base_args = getattr(cls, '_table_args_base', ())
        tenant_indexes = (
            Index(f'idx_{cls.__tablename__}_tenant_id', 'tenant_id'),
            Index(f'idx_{cls.__tablename__}_tenant_created', 'tenant_id', 'created_at'),
        )
        return base_args + tenant_indexes
    
    def __init__(self, *args, **kwargs):
        # Auto-populate tenant_id if not provided
        if 'tenant_id' not in kwargs:
            current_tenant = get_current_tenant()
            if current_tenant:
                kwargs['tenant_id'] = current_tenant
            elif not kwargs.get('_skip_tenant_validation', False):
                raise TenantIsolationError("No tenant context set and tenant_id not provided")
        
        super().__init__(*args, **kwargs)
    
    def validate_tenant_access(self, session: Session) -> bool:
        """Validate that current user can access this record."""
        current_tenant = get_current_tenant()
        if not current_tenant:
            return False
        return self.tenant_id == current_tenant


class TenantMixin(TenantIsolationMixin):
    """Legacy alias for TenantIsolationMixin."""
    pass


class TimestampMixin:
    """Mixin for created/updated timestamp fields."""
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)


class UUIDMixin:
    """Mixin for UUID primary key."""
    
    id = Column(GUID(), primary_key=True, default=uuid4, index=True)


class AuditableTenantMixin(TenantIsolationMixin):
    """Tenant-aware mixin with full audit trail."""
    
    @declared_attr
    def created_by(cls):
        return Column(String(255), nullable=True, index=True)
    
    @declared_attr
    def updated_by(cls):
        return Column(String(255), nullable=True, index=True)
    
    @declared_attr
    def deleted_at(cls):
        return Column(DateTime, nullable=True, index=True)
    
    @declared_attr
    def deleted_by(cls):
        return Column(String(255), nullable=True)
    
    @declared_attr
    def __table_args__(cls):
        """Add audit-specific indexes."""
        base_args = super().__table_args__
        audit_indexes = (
            Index(f'idx_{cls.__tablename__}_tenant_created_by', 'tenant_id', 'created_by'),
            Index(f'idx_{cls.__tablename__}_tenant_audit', 'tenant_id', 'created_at', 'updated_at'),
        )
        return base_args + audit_indexes
    
    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
    
    def soft_delete(self, deleted_by: Optional[str] = None):
        """Perform auditable soft delete."""
        self.deleted_at = datetime.utcnow()
        self.deleted_by = deleted_by
        self.updated_at = datetime.utcnow()
    
    def restore(self, updated_by: Optional[str] = None):
        """Restore with audit trail."""
        self.deleted_at = None
        self.deleted_by = None
        self.updated_at = datetime.utcnow()
        self.updated_by = updated_by


class ISPModelMixin(UUIDMixin, TenantIsolationMixin, TimestampMixin):
    """Complete mixin combining all common ISP model patterns.
    
    Provides:
    - UUID primary key with index
    - Enhanced tenant isolation with automatic tenant detection
    - Automatic timestamps with indexes
    - Soft delete support
    
    Usage:
        class MyModel(Base, ISPModelMixin):
            __tablename__ = "my_table"
            # ... other fields
    """
    
    @declared_attr
    def is_active(cls):
        """Soft delete support."""
        return Column(Boolean, default=True, nullable=False, index=True)
    
    @declared_attr
    def __table_args__(cls):
        """Add ISP-specific indexes."""
        base_args = super().__table_args__
        isp_indexes = (
            Index(f'idx_{cls.__tablename__}_tenant_active', 'tenant_id', 'is_active'),
        )
        return base_args + isp_indexes
    
    @property
    def is_deleted(self) -> bool:
        """Check if record is soft deleted."""
        return not self.is_active
    
    def soft_delete(self):
        """Perform soft delete."""
        self.is_active = False
        self.updated_at = datetime.utcnow()
    
    def restore(self):
        """Restore soft deleted record."""
        self.is_active = True
        self.updated_at = datetime.utcnow()


class ManagementModelMixin(UUIDMixin, AuditableTenantMixin, TimestampMixin):
    """Complete mixin for Management platform models.
    
    Provides:
    - UUID primary key with index
    - Enhanced tenant isolation with automatic tenant detection
    - Full audit trail (created_by, updated_by, deleted_by)
    - Soft delete with timestamps
    - Automatic timestamps with indexes
    
    Usage:
        class MyModel(Base, ManagementModelMixin):
            __tablename__ = "my_table"
            # ... other fields
    """
    pass


# Event listeners for automatic tenant validation
@event.listens_for(Session, "before_flush")
def validate_tenant_isolation(session, flush_context, instances):
    """Validate tenant isolation before flush."""
    current_tenant = get_current_tenant()
    
    # Skip validation if no tenant context (system operations)
    if not current_tenant:
        return
    
    for instance in session.new:
        if hasattr(instance, 'tenant_id'):
            if not instance.tenant_id:
                instance.tenant_id = current_tenant
            elif instance.tenant_id != current_tenant:
                raise TenantIsolationError(
                    f"Cannot create {instance.__class__.__name__} with tenant_id "
                    f"'{instance.tenant_id}' in context of tenant '{current_tenant}'"
                )
    
    for instance in session.dirty:
        if hasattr(instance, 'tenant_id'):
            if hasattr(instance, '__dict__'):
                # Check if tenant_id was changed
                history = session.query(instance.__class__).filter_by(id=instance.id).first()
                if history and history.tenant_id != instance.tenant_id:
                    raise TenantIsolationError(
                        f"Cannot change tenant_id of {instance.__class__.__name__}"
                    )
                
                # Validate tenant access
                if instance.tenant_id != current_tenant:
                    raise TenantIsolationError(
                        f"Cannot modify {instance.__class__.__name__} belonging to "
                        f"different tenant '{instance.tenant_id}'"
                    )


# Utility functions for tenant-aware queries
def tenant_filter(query, model_class):
    """Add tenant filter to query."""
    current_tenant = get_current_tenant()
    if current_tenant and hasattr(model_class, 'tenant_id'):
        return query.filter(model_class.tenant_id == current_tenant)
    return query


def tenant_scope_query(session: Session, model_class):
    """Create a tenant-scoped query."""
    query = session.query(model_class)
    return tenant_filter(query, model_class)


# Legacy compatibility aliases
class AuditMixin(AuditableTenantMixin):
    """Legacy alias for AuditableTenantMixin.""" 
    pass