"""
Unified repository patterns for DotMac Framework.

This module consolidates repository logic from ISP and Management modules,
providing consistent CRUD operations, tenant isolation, and error handling.

Usage:
    # Async repositories
    from dotmac_shared.repositories import create_async_repository
    repo = create_async_repository(db, CustomerModel, tenant_id)

    # Sync repositories
    from dotmac_shared.repositories import create_sync_repository
    repo = create_sync_repository(db, CustomerModel, tenant_id)

    # Auto-detect session type
    from dotmac_shared.repositories import create_repository
    repo = create_repository(db, CustomerModel, tenant_id)
"""

from .async_base_repository import AsyncBaseRepository, AsyncTenantRepository
from .factory import RepositoryFactory, create_async_repository, create_repository, create_sync_repository
from .sync_base_repository import SyncBaseRepository, SyncTenantRepository

__all__ = [
    # Base repository classes
    "AsyncBaseRepository",
    "AsyncTenantRepository",
    "SyncBaseRepository",
    "SyncTenantRepository",
    # Factory and convenience functions
    "RepositoryFactory",
    "create_repository",
    "create_async_repository",
    "create_sync_repository",
]
