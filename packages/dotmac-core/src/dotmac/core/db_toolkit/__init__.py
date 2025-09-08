"""
DotMac Database Toolkit

Unified database toolkit providing:
- Sync/async repository patterns
- Tenant isolation
- Transaction management
- Query optimization
- Health monitoring
"""

from dotmac.core.db_toolkit.health import DatabaseHealthChecker
from dotmac.core.db_toolkit.pagination import DatabasePaginator, PaginationHelper
from dotmac.core.db_toolkit.repositories import (
    AsyncRepository,
    AsyncTenantRepository,
    BaseRepository,
    BaseTenantRepository,
    create_async_repository,
    create_repository,
)
from dotmac.core.db_toolkit.transactions import DatabaseTransaction, TransactionManager

__version__ = "0.1.0"

__all__ = [
    "AsyncRepository",
    "AsyncTenantRepository",
    "BaseRepository",
    "BaseTenantRepository",
    "DatabaseHealthChecker",
    "DatabasePaginator",
    "DatabaseTransaction",
    "PaginationHelper",
    "TransactionManager",
    "create_async_repository",
    "create_repository",
]
