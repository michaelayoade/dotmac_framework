"""
Compatibility shim for legacy imports.

Re-exports canonical database session helpers from dotmac.database.session.
"""

from dotmac.database.session import (
    check_database_health,
    create_async_database_engine,
    get_async_db,
    get_async_db_session,
    get_database_session,
    get_db_session,
)

__all__ = [
    "check_database_health",
    "create_async_database_engine",
    "get_async_db",
    "get_async_db_session",
    "get_database_session",
    "get_db_session",
]
