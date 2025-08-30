"""
DotMac Database Toolkit

Unified database toolkit providing:
- Sync/async repository patterns
- Tenant isolation
- Transaction management
- Query optimization
- Health monitoring
"""

from .health import DatabaseHealthChecker
from .pagination import DatabasePaginator, PaginationHelper
from .repositories import (
    AsyncRepository,
    AsyncTenantRepository,
    BaseRepository,
    BaseTenantRepository,
    create_async_repository,
    create_repository,
)
from .transactions import DatabaseTransaction, TransactionManager

__version__ = "0.1.0"

__all__ = [
    "BaseRepository",
    "BaseTenantRepository",
    "AsyncRepository",
    "AsyncTenantRepository",
    "create_repository",
    "create_async_repository",
    "DatabaseTransaction",
    "TransactionManager",
    "DatabaseHealthChecker",
    "DatabasePaginator",
    "PaginationHelper",
]
