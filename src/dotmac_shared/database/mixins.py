"""Database model mixins for DRY patterns across all ISP modules."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID


class TenantMixin:
    """Mixin for tenant-aware models."""
    
    tenant_id = Column(String(255), nullable=False, index=True)


class TimestampMixin:
    """Mixin for created/updated timestamp fields."""
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UUIDMixin:
    """Mixin for UUID primary key."""
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)


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