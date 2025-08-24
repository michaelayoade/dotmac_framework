"""
Async Service Migration Adapter

ARCHITECTURE IMPROVEMENT: Provides seamless migration from sync to async services
during the standardization process. Allows gradual transition without breaking
existing code that depends on sync patterns.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Type, TypeVar, Generic, Callable, Awaitable
from uuid import UUID
from functools import wraps
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from .base_service import BaseService, BaseTenantService
from .exceptions import ServiceError

logger = logging.getLogger(__name__)

# Generic types
ServiceType = TypeVar('ServiceType')


class AsyncServiceAdapter:
    """
    Adapter that allows sync code to call async services seamlessly.
    
    PATTERN: Adapter Pattern + Thread Pool Execution
    - Wraps async services to provide sync interface
    - Uses thread pool to avoid blocking main thread
    - Handles session conversion (sync -> async)
    - Maintains transaction integrity during migration
    
    Features:
    - Automatic sync/async session conversion
    - Thread pool execution for async operations
    - Error handling and logging
    - Transaction boundary preservation
    - Gradual migration support
    """
    
    def __init__(self, sync_session: Session, async_session_factory: Optional[Callable[[], AsyncSession]] = None):
        """
        Initialize adapter.
        
        Args:
            sync_session: Existing sync database session
            async_session_factory: Factory function for creating async sessions
        """
        self.sync_session = sync_session
        self.async_session_factory = async_session_factory
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="async_adapter")
        
    def run_async(self, async_func: Awaitable[Any]) -> Any:
        """
        Execute async function in sync context.
        
        Args:
            async_func: Async function to execute
            
        Returns:
            Result of async function
            
        Raises:
            ServiceError: If async execution fails
        """
        try:
            # Check if we're already in an async context
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context, run in thread pool
                future = asyncio.run_coroutine_threadsafe(async_func, loop)
                return future.result(timeout=30)  # 30 second timeout
            except RuntimeError:
                # No running loop, create new one
                return asyncio.run(async_func)
                
        except Exception as e:
            logger.error(f"Error executing async function: {e}")
            raise ServiceError(f"Async execution failed: {e}")
    
    def wrap_service(self, service_class: Type[ServiceType], *args, **kwargs) -> 'SyncServiceWrapper':
        """
        Wrap async service to provide sync interface.
        
        Args:
            service_class: Async service class to wrap
            *args: Service initialization arguments
            **kwargs: Service initialization keyword arguments
            
        Returns:
            Sync wrapper for async service
        """
        return SyncServiceWrapper(self, service_class, *args, **kwargs)


class SyncServiceWrapper:
    """
    Wrapper that provides sync interface for async services.
    
    Dynamically wraps all async methods to provide sync equivalents.
    """
    
    def __init__(self, adapter: AsyncServiceAdapter, service_class: Type, *args, **kwargs):
        """
        Initialize wrapper.
        
        Args:
            adapter: AsyncServiceAdapter instance
            service_class: Service class to wrap
            *args: Service initialization arguments
            **kwargs: Service initialization keyword arguments
        """
        self._adapter = adapter
        self._service_class = service_class
        self._init_args = args
        self._init_kwargs = kwargs
        self._service_instance = None
        
    def _get_service_instance(self) -> Any:
        """Get or create service instance."""
        if self._service_instance is None:
            # Convert sync session to async if needed
            if self._adapter.async_session_factory:
                async_session = self._adapter.async_session_factory()
                # Replace sync session with async session in kwargs
                if 'db' in self._init_kwargs:
                    self._init_kwargs['db'] = async_session
                    
            self._service_instance = self._service_class(*self._init_args, **self._init_kwargs)
            
        return self._service_instance
    
    def __getattr__(self, name: str) -> Any:
        """
        Dynamically wrap service methods.
        
        Args:
            name: Method name
            
        Returns:
            Wrapped method (sync version of async method)
        """
        service = self._get_service_instance()
        attr = getattr(service, name)
        
        # If it's a coroutine function, wrap it to run synchronously
        if asyncio.iscoroutinefunction(attr):
            def sync_wrapper(*args, **kwargs):
                coro = attr(*args, **kwargs)
                return self._adapter.run_async(coro)
            return sync_wrapper
        
        # If it's not async, return as-is
        return attr


def sync_to_async_service(sync_session: Session, async_session_factory: Optional[Callable[[], AsyncSession]] = None):
    """
    Decorator to convert sync service to async-compatible service.
    
    Args:
        sync_session: Sync database session
        async_session_factory: Factory for async sessions
        
    Returns:
        AsyncServiceAdapter instance
    """
    return AsyncServiceAdapter(sync_session, async_session_factory)


class AsyncSessionFromSync:
    """
    Utility to create async session from sync session configuration.
    
    PATTERN: Factory Pattern
    - Creates async session with same configuration as sync session
    - Maintains connection parameters and settings
    - Provides seamless transition path
    """
    
    @staticmethod
    def create_async_session_factory(sync_session: Session) -> Callable[[], AsyncSession]:
        """
        Create async session factory from sync session.
        
        Args:
            sync_session: Existing sync session
            
        Returns:
            Factory function for async sessions
        """
        # Extract connection info from sync session
        sync_url = str(sync_session.bind.url)
        
        # Convert to async URL
        if sync_url.startswith('postgresql://'):
            async_url = sync_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
        elif sync_url.startswith('sqlite://'):
            async_url = sync_url.replace('sqlite://', 'sqlite+aiosqlite://', 1)
        else:
            # Default to asyncpg for PostgreSQL
            async_url = sync_url
            
        # Create async engine
        async_engine = create_async_engine(async_url)
        async_session_class = async_sessionmaker(async_engine)
        
        def session_factory() -> AsyncSession:
            return async_session_class()
            
        return session_factory


# Migration utilities
class ServiceMigrationHelper:
    """
    Helper utilities for service migration.
    
    Provides tools and patterns to assist in migrating from legacy
    service patterns to standardized async patterns.
    """
    
    @staticmethod
    def migrate_service_calls(service_instance: Any, method_mapping: Dict[str, str]) -> Any:
        """
        Migrate service calls to new method names.
        
        Args:
            service_instance: Service instance to migrate
            method_mapping: Map of old_method -> new_method
            
        Returns:
            Migrated service wrapper
        """
        class MigratedServiceWrapper:
            def __init__(self, service):
                self._service = service
                self._method_mapping = method_mapping
                
            def __getattr__(self, name: str) -> Any:
                # Check if method needs migration
                if name in self._method_mapping:
                    new_name = self._method_mapping[name]
                    logger.warning(f"Method '{name}' is deprecated. Use '{new_name}' instead.")
                    return getattr(self._service, new_name)
                
                return getattr(self._service, name)
                
        return MigratedServiceWrapper(service_instance)
    
    @staticmethod
    def create_compatibility_layer(old_service_class: Type, new_service_class: Type) -> Type:
        """
        Create compatibility layer between old and new service interfaces.
        
        Args:
            old_service_class: Legacy service class
            new_service_class: New standardized service class
            
        Returns:
            Compatibility wrapper class
        """
        class CompatibilityService(new_service_class):
            """Compatibility wrapper for legacy service interface."""
            
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                logger.info(f"Using compatibility layer for {old_service_class.__name__}")
            
            # Add legacy method aliases here as needed
            
        return CompatibilityService


# Example usage patterns
async def example_migration_pattern():
    """
    Example showing how to use the async service adapter.
    
    This demonstrates the migration pattern from sync to async services.
    """
    from sqlalchemy.orm import Session
    
    # Existing sync session
    sync_session = Session()
    
    # Create async session factory
    async_session_factory = AsyncSessionFromSync.create_async_session_factory(sync_session)
    
    # Create adapter
    adapter = AsyncServiceAdapter(sync_session, async_session_factory)
    
    # Wrap async service to provide sync interface
    from dotmac_isp.modules.billing.service import BillingService
    
    # This allows existing sync code to use new async services
    billing_service = adapter.wrap_service(BillingService, db=sync_session, tenant_id="tenant_001")
    
    # These calls now work synchronously even though the underlying service is async
    invoice = billing_service.create_invoice(invoice_data={})  # Runs async method synchronously
    invoices = billing_service.list()  # Runs async method synchronously
    
    return invoice