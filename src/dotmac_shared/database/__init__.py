"""
Database module for DotMac Framework.
Provides database connectivity and session management.
"""

from .base import Base, BaseModel, TenantModel, AuditableMixin, VersionedMixin
from .mixins import TenantMixin, TimestampMixin, UUIDMixin, ISPModelMixin

try:
    from .session import get_db, get_db_session, DatabaseManager
except ImportError:
    # Graceful fallback if session module not available
    def get_db():
        """Fallback database dependency."""
        raise NotImplementedError("Database session not configured")
    
    def get_db_session():
        """Fallback database session."""
        raise NotImplementedError("Database session not configured")
    
    class DatabaseManager:
        """Fallback database manager."""
        def __init__(self):
            raise NotImplementedError("Database manager not configured")

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
]