"""
ISP Framework Database Module

Provides database connectivity and session management for ISP framework.
Uses shared patterns from dotmac_shared for consistency.
"""

# Import from shared database management
from dotmac_shared.database import (
    get_db,
    get_db_session,
    DatabaseManager,
    check_database_health
)

# Import local base models
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