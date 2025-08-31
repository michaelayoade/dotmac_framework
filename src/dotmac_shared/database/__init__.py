"""
Database module for DotMac Framework.
Provides database connectivity and session management.
"""

from .base import Base, BaseModel, TenantModel, AuditableMixin, VersionedMixin
from .mixins import TenantMixin, TimestampMixin, UUIDMixin, ISPModelMixin

# Import database session management
from .session import (
    get_async_db as get_db,
    get_async_db_session as get_db_session,
    create_async_database_engine as DatabaseManager,
    check_database_health,
)

__all__ = [
    "Base",
    "BaseModel", 
    "TenantModel",
    "AuditableMixin",
    "VersionedMixin",
    "TenantMixin",
    "TimestampMixin", 
    "UUIDMixin",
    "ISPModelMixin",
    "get_db",
    "get_db_session", 
    "DatabaseManager",
    "check_database_health",
]