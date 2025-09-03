"""
Tests for memory storage backend.
"""

import asyncio
import pytest
import time
from datetime import datetime, timedelta, timezone

from dotmac.tasks.storage.memory import MemoryStorage


class TestMemoryStorage:
    """Test memory storage backend."""

    @pytest.fixture
    async def storage(self):
        """Create memory storage instance."""
        storage = MemoryStorage()
        yield storage
        await storage.close()

    async def test_idempotency_operations(self, storage):
        """Test idempotency key operations."""
        key = "test-key-123"
        data = {
            "key": key,
            "tenant_id": "tenant1",
            "user_id": "user1",
            "operation_type": "send_email",
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        }
        
        # Test set and get
        await storage.set_idempotency(key, data, 3600)
        retrieved = await storage.get_idempotency(key)
        
        assert retrieved is not None
        assert retrieved["key"] == key
        assert retrieved["tenant_id"] == "tenant1"
        
        # Test delete
        deleted = await storage.delete_idempotency(key)
        assert deleted is True
        
        # Should not exist after delete
        retrieved = await storage.get_idempotency(key)
        assert retrieved is None
        
        # Delete non-existent key
        deleted = await storage.delete_idempotency("nonexistent")
        assert deleted is False

    async def test_idempotency_expiration(self, storage):
        """Test idempotency key expiration."""
        key = "expiring-key"
        past_time = datetime.now(timezone.utc) - timedelta(seconds=1)
        
        data = {
            "key": key,
            "tenant_id": "tenant1",
            "status": "pending",
            "expires_at": past_time.isoformat(),
        }
        
        await storage.set_idempotency(key, data, 1)
        
        # Should be expired and return None
        retrieved = await storage.get_idempotency(key)
        assert retrieved is None

    async def test_idempotency_indexing(self, storage):
        """Test idempotency key indexing."""
        keys = ["key1", "key2", "key3"]
        timestamps = [
            time.time() - 3600,  # 1 hour ago
            time.time() - 1800,  # 30 minutes ago
            time.time() - 300,   # 5 minutes ago
        ]
        
        # Index keys with different timestamps
        for key, ts in zip(keys, timestamps):
            await storage.index_idempotency(key, ts)
        
        # Get expired keys (older than 45 minutes ago)
        cutoff = time.time() - 2700  # 45 minutes ago
        expired = await storage.get_expired_idempotency_keys(cutoff)
        
        # Should include key1 and key2
        assert len(expired) >= 2
        assert "key1" in expired
        assert "key2" in expired

    async def test_saga_operations(self, storage):
        """Test saga workflow operations."""
        saga_id = "saga-123"
        saga_data = {
            "saga_id": saga_id,
            "tenant_id": "tenant1",
            "workflow_type": "user_onboarding",
            "status": "pending",
            "steps": [],
        }
        
        # Test set and get
        await storage.set_saga(saga_id, saga_data)
        retrieved = await storage.get_saga(saga_id)
        
        assert retrieved is not None
        assert retrieved["saga_id"] == saga_id
        assert retrieved["workflow_type"] == "user_onboarding"
        
        # Test delete
        deleted = await storage.delete_saga(saga_id)
        assert deleted is True
        
        # Should not exist after delete
        retrieved = await storage.get_saga(saga_id)
        assert retrieved is None

    async def test_saga_history_operations(self, storage):
        """Test saga history operations."""
        saga_id = "saga-with-history"
        
        # Add history entries
        entries = [
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "step_id": "step1",
                "step_name": "First Step",
                "status": "completed",
            },
            {
                "timestamp": (datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat(),
                "step_id": "step2", 
                "step_name": "Second Step",
                "status": "failed",
                "error": "Something went wrong",
            }
        ]
        
        for entry in entries:
            await storage.append_saga_history(saga_id, entry)
        
        # Get all history
        history = await storage.get_saga_history(saga_id)
        assert len(history) == 2
        
        # Should be in reverse chronological order (newest first)
        assert history[0]["step_name"] == "Second Step"  
        assert history[1]["step_name"] == "First Step"
        
        # Get limited history
        limited = await storage.get_saga_history(saga_id, limit=1)
        assert len(limited) == 1
        assert limited[0]["step_name"] == "Second Step"
        
        # Clear history
        await storage.clear_saga_history(saga_id)
        history = await storage.get_saga_history(saga_id)
        assert len(history) == 0

    async def test_operation_operations(self, storage):
        """Test background operation operations."""
        op_id = "operation-123"
        op_data = {
            "operation_id": op_id,
            "tenant_id": "tenant1",
            "user_id": "user1",
            "operation_type": "send_email",
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        
        # Test set and get
        await storage.set_operation(op_id, op_data)
        retrieved = await storage.get_operation(op_id)
        
        assert retrieved is not None
        assert retrieved["operation_id"] == op_id
        assert retrieved["operation_type"] == "send_email"
        
        # Test delete
        deleted = await storage.delete_operation(op_id)
        assert deleted is True
        
        # Should not exist after delete
        retrieved = await storage.get_operation(op_id)
        assert retrieved is None

    async def test_list_operations_by_tenant(self, storage):
        """Test listing operations by tenant."""
        # Create operations for different tenants
        operations = [
            ("op1", "tenant1", "send_email", "2023-01-01T10:00:00Z"),
            ("op2", "tenant1", "create_user", "2023-01-01T11:00:00Z"),
            ("op3", "tenant2", "send_email", "2023-01-01T12:00:00Z"),
            ("op4", "tenant1", "provision_service", "2023-01-01T13:00:00Z"),
        ]
        
        for op_id, tenant_id, op_type, created_at in operations:
            op_data = {
                "operation_id": op_id,
                "tenant_id": tenant_id,
                "operation_type": op_type,
                "status": "completed",
                "created_at": created_at,
                "updated_at": created_at,
            }
            await storage.set_operation(op_id, op_data)
        
        # Get operations for tenant1
        tenant1_ops = await storage.list_operations_by_tenant("tenant1", limit=10)
        assert len(tenant1_ops) == 3
        
        # Should be sorted by created_at (newest first)
        assert tenant1_ops[0]["operation_id"] == "op4"  # Latest
        assert tenant1_ops[1]["operation_id"] == "op2"
        assert tenant1_ops[2]["operation_id"] == "op1"  # Earliest
        
        # Test pagination
        limited = await storage.list_operations_by_tenant("tenant1", limit=2)
        assert len(limited) == 2
        assert limited[0]["operation_id"] == "op4"
        
        # Test offset
        offset_results = await storage.list_operations_by_tenant("tenant1", limit=2, offset=1)
        assert len(offset_results) == 2
        assert offset_results[0]["operation_id"] == "op2"

    async def test_list_sagas_by_tenant(self, storage):
        """Test listing sagas by tenant.""" 
        # Create sagas for different tenants
        sagas = [
            ("saga1", "tenant1", "user_onboarding", "2023-01-01T10:00:00Z"),
            ("saga2", "tenant1", "service_provisioning", "2023-01-01T11:00:00Z"),
            ("saga3", "tenant2", "user_onboarding", "2023-01-01T12:00:00Z"),
        ]
        
        for saga_id, tenant_id, workflow_type, created_at in sagas:
            saga_data = {
                "saga_id": saga_id,
                "tenant_id": tenant_id,
                "workflow_type": workflow_type,
                "status": "completed",
                "created_at": created_at,
                "updated_at": created_at,
            }
            await storage.set_saga(saga_id, saga_data)
        
        # Get sagas for tenant1
        tenant1_sagas = await storage.list_sagas_by_tenant("tenant1", limit=10)
        assert len(tenant1_sagas) == 2
        
        # Should be sorted by created_at (newest first)
        assert tenant1_sagas[0]["saga_id"] == "saga2"
        assert tenant1_sagas[1]["saga_id"] == "saga1"

    async def test_distributed_locks(self, storage):
        """Test distributed lock operations.""" 
        lock_key = "test-lock"
        
        # Acquire lock
        acquired = await storage.acquire_lock(lock_key, timeout_seconds=60)
        assert acquired is True
        
        # Try to acquire same lock (should fail)
        acquired_again = await storage.acquire_lock(lock_key, timeout_seconds=60)
        assert acquired_again is False
        
        # Release lock
        released = await storage.release_lock(lock_key)
        assert released is True
        
        # Should be able to acquire again
        acquired_after_release = await storage.acquire_lock(lock_key, timeout_seconds=60)
        assert acquired_after_release is True
        
        # Clean up
        await storage.release_lock(lock_key)

    async def test_lock_expiration(self, storage):
        """Test lock expiration."""
        lock_key = "expiring-lock"
        
        # Acquire lock with short timeout
        acquired = await storage.acquire_lock(lock_key, timeout_seconds=1)
        assert acquired is True
        
        # Wait for expiration
        await asyncio.sleep(1.5)
        
        # Should be able to acquire expired lock
        acquired_again = await storage.acquire_lock(lock_key, timeout_seconds=60) 
        assert acquired_again is True
        
        await storage.release_lock(lock_key)

    async def test_cleanup_expired_data(self, storage):
        """Test cleanup of expired data."""
        # Add some data that will expire
        expired_key = "expired-key"
        current_key = "current-key"
        
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)
        
        expired_data = {
            "key": expired_key,
            "expires_at": past_time.isoformat(),
        }
        current_data = {
            "key": current_key,
            "expires_at": future_time.isoformat(),
        }
        
        await storage.set_idempotency(expired_key, expired_data, 3600)
        await storage.set_idempotency(current_key, current_data, 3600)
        await storage.index_idempotency(expired_key, past_time.timestamp())
        await storage.index_idempotency(current_key, future_time.timestamp())
        
        # Add expired lock
        expired_lock = "expired-lock"
        await storage.acquire_lock(expired_lock, timeout_seconds=1)
        await asyncio.sleep(1.5)  # Let lock expire
        
        # Run cleanup
        cleaned_count = await storage.cleanup_expired_data()
        
        assert cleaned_count > 0  # Should have cleaned something
        
        # Expired key should be gone
        retrieved = await storage.get_idempotency(expired_key)
        assert retrieved is None
        
        # Current key should still exist
        retrieved = await storage.get_idempotency(current_key)
        assert retrieved is not None

    async def test_health_check(self, storage):
        """Test health check."""
        health = await storage.health_check()
        
        assert health["status"] == "healthy"
        assert health["backend"] == "memory"
        assert "metrics" in health
        assert isinstance(health["metrics"]["idempotency_keys"], int)

    async def test_concurrent_operations(self, storage):
        """Test concurrent operations on storage."""
        # Run multiple operations concurrently
        async def set_key(i):
            key = f"concurrent-key-{i}"
            data = {"key": key, "data": f"value-{i}"}
            await storage.set_idempotency(key, data, 3600)
            return await storage.get_idempotency(key)
        
        # Run 10 concurrent operations
        tasks = [set_key(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        # All operations should succeed
        assert len(results) == 10
        for i, result in enumerate(results):
            assert result is not None
            assert result["key"] == f"concurrent-key-{i}"
            assert result["data"] == f"value-{i}"

    async def test_storage_statistics(self, storage):
        """Test storage statistics."""
        # Add some test data
        await storage.set_idempotency("test-key", {"data": "test"}, 3600)
        await storage.set_saga("test-saga", {"data": "test"})
        await storage.set_operation("test-op", {"data": "test"})
        await storage.acquire_lock("test-lock", 60)
        
        stats = await storage.get_stats()
        
        assert stats["idempotency_keys"] >= 1
        assert stats["sagas"] >= 1
        assert stats["operations"] >= 1
        assert stats["active_locks"] >= 1
        assert isinstance(stats["saga_histories"], int)
        assert isinstance(stats["total_history_entries"], int)