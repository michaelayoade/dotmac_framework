"""
In-memory storage backend for background operations.

Provides a simple in-memory implementation of the storage interface
suitable for development, testing, and single-instance deployments.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional

from .base import Storage, StorageException


class MemoryStorage(Storage):
    """
    In-memory storage backend using Python dictionaries.
    
    This implementation stores all data in memory and does not persist
    across application restarts. It's suitable for development and
    testing, but not for production use in multi-instance deployments.
    """

    def __init__(self) -> None:
        """Initialize in-memory storage."""
        # Idempotency storage
        self._idempotency_data: Dict[str, Dict[str, Any]] = {}
        self._idempotency_index: Dict[str, float] = {}  # key -> timestamp
        
        # Saga storage
        self._saga_data: Dict[str, Dict[str, Any]] = {}
        self._saga_history: Dict[str, List[Dict[str, Any]]] = {}
        
        # Background operations storage
        self._operations: Dict[str, Dict[str, Any]] = {}
        
        # Distributed locks (best effort for single instance)
        self._locks: Dict[str, float] = {}  # lock_key -> expiry_time
        
        # Lock for thread safety
        self._lock = asyncio.Lock()

    async def get_idempotency(self, key: str) -> Optional[Dict[str, Any]]:
        """Get idempotency data by key."""
        async with self._lock:
            data = self._idempotency_data.get(key)
            if data is None:
                return None
            
            # Check if expired
            expires_at = data.get("expires_at")
            if expires_at:
                from datetime import datetime
                try:
                    exp_time = datetime.fromisoformat(expires_at)
                    if datetime.now(exp_time.tzinfo or datetime.now().astimezone().tzinfo) > exp_time:
                        # Remove expired data
                        self._idempotency_data.pop(key, None)
                        self._idempotency_index.pop(key, None)
                        return None
                except (ValueError, TypeError):
                    pass
            
            return data.copy()

    async def set_idempotency(
        self, 
        key: str, 
        mapping: Dict[str, Any], 
        ttl_seconds: int
    ) -> None:
        """Set idempotency data with TTL."""
        async with self._lock:
            self._idempotency_data[key] = mapping.copy()
            self._idempotency_index[key] = time.time()

    async def delete_idempotency(self, key: str) -> bool:
        """Delete idempotency data by key."""
        async with self._lock:
            existed = key in self._idempotency_data
            self._idempotency_data.pop(key, None)
            self._idempotency_index.pop(key, None)
            return existed

    async def index_idempotency(self, key: str, timestamp: float) -> None:
        """Index idempotency key by timestamp."""
        async with self._lock:
            self._idempotency_index[key] = timestamp

    async def get_expired_idempotency_keys(self, before_timestamp: float) -> List[str]:
        """Get idempotency keys that expired before the given timestamp."""
        async with self._lock:
            expired_keys = []
            for key, ts in self._idempotency_index.items():
                if ts < before_timestamp:
                    # Double-check by looking at actual expiry time
                    data = self._idempotency_data.get(key)
                    if data:
                        expires_at = data.get("expires_at")
                        if expires_at:
                            from datetime import datetime
                            try:
                                exp_time = datetime.fromisoformat(expires_at)
                                if datetime.now(exp_time.tzinfo or datetime.now().astimezone().tzinfo) > exp_time:
                                    expired_keys.append(key)
                            except (ValueError, TypeError):
                                # If we can't parse the date, consider it expired
                                expired_keys.append(key)
            return expired_keys

    async def get_saga(self, saga_id: str) -> Optional[Dict[str, Any]]:
        """Get saga workflow data by ID."""
        async with self._lock:
            data = self._saga_data.get(saga_id)
            return data.copy() if data else None

    async def set_saga(self, saga_id: str, mapping: Dict[str, Any]) -> None:
        """Set saga workflow data."""
        async with self._lock:
            self._saga_data[saga_id] = mapping.copy()

    async def delete_saga(self, saga_id: str) -> bool:
        """Delete saga workflow data by ID."""
        async with self._lock:
            existed = saga_id in self._saga_data
            self._saga_data.pop(saga_id, None)
            self._saga_history.pop(saga_id, None)
            return existed

    async def append_saga_history(
        self, 
        saga_id: str, 
        entry: Dict[str, Any]
    ) -> None:
        """Append an entry to saga execution history."""
        async with self._lock:
            if saga_id not in self._saga_history:
                self._saga_history[saga_id] = []
            self._saga_history[saga_id].append(entry.copy())

    async def get_saga_history(
        self, 
        saga_id: str, 
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get saga execution history."""
        async with self._lock:
            history = self._saga_history.get(saga_id, [])
            # Return newest first (reverse chronological order)
            result = list(reversed(history))
            if limit is not None:
                result = result[:limit]
            return [entry.copy() for entry in result]

    async def clear_saga_history(self, saga_id: str) -> None:
        """Clear saga execution history."""
        async with self._lock:
            self._saga_history.pop(saga_id, None)

    async def get_operation(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get background operation data by ID."""
        async with self._lock:
            data = self._operations.get(operation_id)
            return data.copy() if data else None

    async def set_operation(
        self, 
        operation_id: str, 
        mapping: Dict[str, Any]
    ) -> None:
        """Set background operation data."""
        async with self._lock:
            self._operations[operation_id] = mapping.copy()

    async def delete_operation(self, operation_id: str) -> bool:
        """Delete background operation data by ID."""
        async with self._lock:
            existed = operation_id in self._operations
            self._operations.pop(operation_id, None)
            return existed

    async def list_operations_by_tenant(
        self, 
        tenant_id: str, 
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List background operations for a tenant."""
        async with self._lock:
            tenant_ops = []
            for op_data in self._operations.values():
                if op_data.get("tenant_id") == tenant_id:
                    tenant_ops.append(op_data.copy())
            
            # Sort by created_at (newest first)
            tenant_ops.sort(
                key=lambda x: x.get("created_at", ""), 
                reverse=True
            )
            
            # Apply pagination
            end_idx = offset + limit
            return tenant_ops[offset:end_idx]

    async def list_sagas_by_tenant(
        self, 
        tenant_id: str, 
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List saga workflows for a tenant."""
        async with self._lock:
            tenant_sagas = []
            for saga_data in self._saga_data.values():
                if saga_data.get("tenant_id") == tenant_id:
                    tenant_sagas.append(saga_data.copy())
            
            # Sort by created_at (newest first)
            tenant_sagas.sort(
                key=lambda x: x.get("created_at", ""), 
                reverse=True
            )
            
            # Apply pagination
            end_idx = offset + limit
            return tenant_sagas[offset:end_idx]

    async def acquire_lock(
        self, 
        lock_key: str, 
        timeout_seconds: int = 30
    ) -> bool:
        """Acquire a distributed lock for saga execution."""
        async with self._lock:
            now = time.time()
            
            # Clean up expired locks
            expired_keys = [
                key for key, expiry in self._locks.items() 
                if now > expiry
            ]
            for key in expired_keys:
                self._locks.pop(key, None)
            
            # Try to acquire lock
            if lock_key in self._locks:
                return False  # Already locked
            
            self._locks[lock_key] = now + timeout_seconds
            return True

    async def release_lock(self, lock_key: str) -> bool:
        """Release a distributed lock."""
        async with self._lock:
            existed = lock_key in self._locks
            self._locks.pop(lock_key, None)
            return existed

    async def cleanup_expired_data(self) -> int:
        """Clean up expired data."""
        async with self._lock:
            now = time.time()
            cleaned_count = 0
            
            # Clean up expired idempotency keys
            expired_keys = await self.get_expired_idempotency_keys(now)
            for key in expired_keys:
                self._idempotency_data.pop(key, None)
                self._idempotency_index.pop(key, None)
                cleaned_count += 1
            
            # Clean up expired locks
            expired_locks = [
                key for key, expiry in self._locks.items() 
                if now > expiry
            ]
            for key in expired_locks:
                self._locks.pop(key, None)
                cleaned_count += 1
            
            return cleaned_count

    async def health_check(self) -> Dict[str, Any]:
        """Perform storage health check."""
        async with self._lock:
            return {
                "status": "healthy",
                "backend": "memory",
                "metrics": {
                    "idempotency_keys": len(self._idempotency_data),
                    "sagas": len(self._saga_data),
                    "operations": len(self._operations),
                    "active_locks": len(self._locks),
                }
            }

    async def close(self) -> None:
        """Close storage connections and clean up resources."""
        async with self._lock:
            self._idempotency_data.clear()
            self._idempotency_index.clear()
            self._saga_data.clear()
            self._saga_history.clear()
            self._operations.clear()
            self._locks.clear()

    # Additional helper methods for testing and debugging
    
    async def get_all_idempotency_keys(self) -> List[str]:
        """Get all idempotency keys (for testing)."""
        async with self._lock:
            return list(self._idempotency_data.keys())

    async def get_all_saga_ids(self) -> List[str]:
        """Get all saga IDs (for testing)."""
        async with self._lock:
            return list(self._saga_data.keys())

    async def get_all_operation_ids(self) -> List[str]:
        """Get all operation IDs (for testing)."""
        async with self._lock:
            return list(self._operations.keys())

    async def get_stats(self) -> Dict[str, int]:
        """Get storage statistics."""
        async with self._lock:
            return {
                "idempotency_keys": len(self._idempotency_data),
                "sagas": len(self._saga_data),
                "operations": len(self._operations),
                "active_locks": len(self._locks),
                "saga_histories": len(self._saga_history),
                "total_history_entries": sum(
                    len(history) for history in self._saga_history.values()
                ),
            }