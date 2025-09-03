"""
Storage abstraction layer for background operations.

Provides base interfaces for storing idempotency keys, saga workflows,
and operation history with pluggable backends.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class Storage(ABC):
    """
    Abstract base class for storage backends.
    
    Defines the interface for storing and retrieving idempotency keys,
    saga workflows, and operation history. Implementations can use
    in-memory storage, Redis, or other persistence layers.
    """

    @abstractmethod
    async def get_idempotency(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get idempotency data by key.
        
        Args:
            key: The idempotency key
            
        Returns:
            Dictionary with idempotency data or None if not found
        """
        pass

    @abstractmethod
    async def set_idempotency(
        self, 
        key: str, 
        mapping: Dict[str, Any], 
        ttl_seconds: int
    ) -> None:
        """
        Set idempotency data with TTL.
        
        Args:
            key: The idempotency key
            mapping: Dictionary with idempotency data
            ttl_seconds: Time to live in seconds
        """
        pass

    @abstractmethod
    async def delete_idempotency(self, key: str) -> bool:
        """
        Delete idempotency data by key.
        
        Args:
            key: The idempotency key
            
        Returns:
            True if key existed and was deleted, False otherwise
        """
        pass

    @abstractmethod
    async def index_idempotency(self, key: str, timestamp: float) -> None:
        """
        Index idempotency key by timestamp for cleanup.
        
        Args:
            key: The idempotency key
            timestamp: Unix timestamp when key was created
        """
        pass

    @abstractmethod
    async def get_expired_idempotency_keys(self, before_timestamp: float) -> List[str]:
        """
        Get idempotency keys that expired before the given timestamp.
        
        Args:
            before_timestamp: Unix timestamp cutoff
            
        Returns:
            List of expired idempotency keys
        """
        pass

    @abstractmethod
    async def get_saga(self, saga_id: str) -> Optional[Dict[str, Any]]:
        """
        Get saga workflow data by ID.
        
        Args:
            saga_id: The saga workflow ID
            
        Returns:
            Dictionary with saga data or None if not found
        """
        pass

    @abstractmethod
    async def set_saga(self, saga_id: str, mapping: Dict[str, Any]) -> None:
        """
        Set saga workflow data.
        
        Args:
            saga_id: The saga workflow ID
            mapping: Dictionary with saga data
        """
        pass

    @abstractmethod
    async def delete_saga(self, saga_id: str) -> bool:
        """
        Delete saga workflow data by ID.
        
        Args:
            saga_id: The saga workflow ID
            
        Returns:
            True if saga existed and was deleted, False otherwise
        """
        pass

    @abstractmethod
    async def append_saga_history(
        self, 
        saga_id: str, 
        entry: Dict[str, Any]
    ) -> None:
        """
        Append an entry to saga execution history.
        
        Args:
            saga_id: The saga workflow ID
            entry: Dictionary with history entry data
        """
        pass

    @abstractmethod
    async def get_saga_history(
        self, 
        saga_id: str, 
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get saga execution history.
        
        Args:
            saga_id: The saga workflow ID
            limit: Maximum number of entries to return
            
        Returns:
            List of history entries ordered by timestamp (newest first)
        """
        pass

    @abstractmethod
    async def clear_saga_history(self, saga_id: str) -> None:
        """
        Clear saga execution history.
        
        Args:
            saga_id: The saga workflow ID
        """
        pass

    @abstractmethod
    async def get_operation(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get background operation data by ID.
        
        Args:
            operation_id: The operation ID
            
        Returns:
            Dictionary with operation data or None if not found
        """
        pass

    @abstractmethod
    async def set_operation(
        self, 
        operation_id: str, 
        mapping: Dict[str, Any]
    ) -> None:
        """
        Set background operation data.
        
        Args:
            operation_id: The operation ID
            mapping: Dictionary with operation data
        """
        pass

    @abstractmethod
    async def delete_operation(self, operation_id: str) -> bool:
        """
        Delete background operation data by ID.
        
        Args:
            operation_id: The operation ID
            
        Returns:
            True if operation existed and was deleted, False otherwise
        """
        pass

    @abstractmethod
    async def list_operations_by_tenant(
        self, 
        tenant_id: str, 
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List background operations for a tenant.
        
        Args:
            tenant_id: The tenant ID
            limit: Maximum number of operations to return
            offset: Number of operations to skip
            
        Returns:
            List of operation data dictionaries
        """
        pass

    @abstractmethod
    async def list_sagas_by_tenant(
        self, 
        tenant_id: str, 
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List saga workflows for a tenant.
        
        Args:
            tenant_id: The tenant ID
            limit: Maximum number of sagas to return
            offset: Number of sagas to skip
            
        Returns:
            List of saga data dictionaries
        """
        pass

    @abstractmethod
    async def acquire_lock(
        self, 
        lock_key: str, 
        timeout_seconds: int = 30
    ) -> bool:
        """
        Acquire a distributed lock for saga execution.
        
        Args:
            lock_key: The lock key
            timeout_seconds: Lock timeout in seconds
            
        Returns:
            True if lock was acquired, False otherwise
        """
        pass

    @abstractmethod
    async def release_lock(self, lock_key: str) -> bool:
        """
        Release a distributed lock.
        
        Args:
            lock_key: The lock key
            
        Returns:
            True if lock was released, False if it didn't exist
        """
        pass

    @abstractmethod
    async def cleanup_expired_data(self) -> int:
        """
        Clean up expired data (idempotency keys, locks, etc.).
        
        Returns:
            Number of items cleaned up
        """
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform storage health check.
        
        Returns:
            Dictionary with health status and metrics
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """
        Close storage connections and clean up resources.
        """
        pass


class StorageException(Exception):
    """Base exception for storage-related errors."""
    pass


class StorageConnectionError(StorageException):
    """Raised when storage connection fails."""
    pass


class StorageTimeoutError(StorageException):
    """Raised when storage operation times out."""
    pass


class LockAcquisitionError(StorageException):
    """Raised when lock acquisition fails."""
    pass