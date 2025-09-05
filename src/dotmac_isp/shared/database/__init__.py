"""
ISP Framework Database Module

Provides database connectivity and session management for ISP framework.
Uses shared patterns from dotmac_shared for consistency.
"""

from dotmac.core import DatabaseManager, check_database_health, get_db, get_db_session

from .base import Base, BaseModel

__all__ = [
    # Database session management
    "get_db",
    "get_db_session",
    "DatabaseManager",
    "check_database_health",
    # Base model classes
    "Base",
    "BaseModel",
]
