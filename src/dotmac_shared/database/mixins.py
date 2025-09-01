"""Database model mixins for DRY patterns across all ISP modules."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy import String as SQLString
import uuid


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


class TenantMixin:
    """Mixin for tenant-aware models."""
    
    tenant_id = Column(String(255), nullable=False, index=True)


class TimestampMixin:
    """Mixin for created/updated timestamp fields."""
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UUIDMixin:
    """Mixin for UUID primary key."""
    
    id = Column(GUID(), primary_key=True, default=uuid4)


class ISPModelMixin(UUIDMixin, TenantMixin, TimestampMixin):
    """Complete mixin combining all common ISP model patterns.
    
    Provides:
    - UUID primary key
    - Tenant isolation 
    - Automatic timestamps
    
    Usage:
        class MyModel(Base, ISPModelMixin):
            __tablename__ = "my_table"
            # ... other fields
    """
    pass