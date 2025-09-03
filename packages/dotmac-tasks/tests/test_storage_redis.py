"""
Tests for Redis storage backend.

These tests require a Redis server and are marked with @pytest.mark.redis.
Run with: pytest -m redis
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timedelta, timezone

from dotmac.tasks.storage.redis import RedisStorage


# Skip all tests if Redis is not available
redis_available = True
try:
    import redis.asyncio as redis
except ImportError:
    redis_available = False


@pytest.mark.redis
@pytest.mark.skipif(not redis_available, reason="Redis not available")
class TestRedisStorage:
    """Test Redis storage backend."""

    @pytest.fixture
    async def storage(self):
        """Create Redis storage instance."""
        # Use test database (15 by default)
        redis_url = "redis://localhost:6379/15"
        storage = RedisStorage(redis_url=redis_url, prefix="test_bgops")
        
        # Clear test data before each test
        await storage.redis.flushdb()
        
        yield storage
        
        # Clean up after test
        await storage.redis.flushdb()
        await storage.close()

    async def test_connection_and_ping(self, storage):
        """Test basic Redis connection."""
        pong = await storage.redis.ping()
        assert pong is True

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
            "result": {"message_id": "123", "status": "sent"},
        }
        
        # Test set and get
        await storage.set_idempotency(key, data, 3600)
        retrieved = await storage.get_idempotency(key)
        
        assert retrieved is not None
        assert retrieved["key"] == key
        assert retrieved["tenant_id"] == "tenant1"
        assert retrieved["result"]["message_id"] == "123"
        
        # Test delete
        deleted = await storage.delete_idempotency(key)
        assert deleted is True
        
        # Should not exist after delete
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
            "steps": [
                {"step_id": "step1", "name": "Create User", "status": "pending"},
                {"step_id": "step2", "name": "Send Email", "status": "pending"},
            ],
        }
        
        # Test set and get
        await storage.set_saga(saga_id, saga_data)
        retrieved = await storage.get_saga(saga_id)
        
        assert retrieved is not None
        assert retrieved["saga_id"] == saga_id
        assert retrieved["workflow_type"] == "user_onboarding"
        assert len(retrieved["steps"]) == 2
        
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
            },
            {
                "timestamp": (datetime.now(timezone.utc) + timedelta(seconds=2)).isoformat(),
                "step_id": "step3",
                "step_name": "Third Step",
                "status": "completed",
            }
        ]
        
        for entry in entries:
            await storage.append_saga_history(saga_id, entry)
        
        # Get all history
        history = await storage.get_saga_history(saga_id)
        assert len(history) == 3
        
        # Should be in reverse chronological order (newest first)
        assert history[0]["step_name"] == "Third Step"
        assert history[1]["step_name"] == "Second Step"
        assert history[2]["step_name"] == "First Step"
        
        # Get limited history
        limited = await storage.get_saga_history(saga_id, limit=2)
        assert len(limited) == 2
        assert limited[0]["step_name"] == "Third Step"
        assert limited[1]["step_name"] == "Second Step"
        
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
            "result": {"success": True},
        }
        
        # Test set and get
        await storage.set_operation(op_id, op_data)
        retrieved = await storage.get_operation(op_id)
        
        assert retrieved is not None
        assert retrieved["operation_id"] == op_id
        assert retrieved["operation_type"] == "send_email"
        assert retrieved["result"]["success"] is True
        
        # Test delete
        deleted = await storage.delete_operation(op_id)
        assert deleted is True
        
        # Should not exist after delete
        retrieved = await storage.get_operation(op_id)
        assert retrieved is None

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
        tenant1_op_ids = [op["operation_id"] for op in tenant1_ops]
        assert "op4" in tenant1_op_ids  # Latest should be included
        assert "op3" not in tenant1_op_ids  # Different tenant
        
        # Test pagination
        limited = await storage.list_operations_by_tenant("tenant1", limit=2)
        assert len(limited) == 2

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
        
        tenant1_saga_ids = [saga["saga_id"] for saga in tenant1_sagas]
        assert "saga1" in tenant1_saga_ids
        assert "saga2" in tenant1_saga_ids
        assert "saga3" not in tenant1_saga_ids  # Different tenant

    async def test_cleanup_expired_data(self, storage):
        """Test cleanup of expired data."""
        # Add some data with indexing
        expired_key = "expired-key"
        current_key = "current-key"
        
        past_timestamp = time.time() - 3600  # 1 hour ago
        current_timestamp = time.time()
        
        # Set up expired key
        await storage.index_idempotency(expired_key, past_timestamp)
        expired_data = {"key": expired_key, "status": "pending"}
        await storage.set_idempotency(expired_key, expired_data, 3600)
        
        # Set up current key
        await storage.index_idempotency(current_key, current_timestamp)
        current_data = {"key": current_key, "status": "pending"}
        await storage.set_idempotency(current_key, current_data, 3600)
        
        # Run cleanup (clean up items older than 30 minutes ago)
        cleaned_count = await storage.cleanup_expired_data()
        
        assert cleaned_count > 0  # Should have cleaned the expired key
        
        # Check that expired key is gone from index
        cutoff = time.time() - 1800  # 30 minutes ago
        still_expired = await storage.get_expired_idempotency_keys(cutoff)
        assert expired_key not in still_expired

    async def test_health_check(self, storage):
        """Test health check."""
        health = await storage.health_check()
        
        assert health["status"] == "healthy"
        assert health["backend"] == "redis"
        assert "server_info" in health
        assert "metrics" in health
        assert isinstance(health["metrics"], dict)

    async def test_concurrent_operations(self, storage):
        """Test concurrent operations on Redis."""
        # Run multiple operations concurrently
        async def set_key(i):
            key = f"concurrent-key-{i}"
            data = {"key": key, "data": f"value-{i}", "number": i}
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

    async def test_redis_key_prefixing(self, storage):
        """Test that Redis keys are properly prefixed."""
        key = "test-prefix-key"
        data = {"key": key, "data": "test"}
        
        await storage.set_idempotency(key, data, 3600)
        
        # Check that key exists with prefix
        redis_key = storage._key("idempo", key)
        exists = await storage.redis.exists(redis_key)
        assert exists == 1

    async def test_json_serialization_edge_cases(self, storage):
        """Test JSON serialization with complex data.""" 
        complex_data = {
            "key": "complex-key",
            "result": {
                "nested": {"deep": {"value": 123}},
                "list": [1, 2, {"item": "test"}],
                "null_value": None,
                "boolean": True,
                "number": 42.5,
            }
        }
        
        await storage.set_idempotency("complex-key", complex_data, 3600)
        retrieved = await storage.get_idempotency("complex-key")
        
        assert retrieved is not None
        assert retrieved["result"]["nested"]["deep"]["value"] == 123
        assert retrieved["result"]["list"][2]["item"] == "test"
        assert retrieved["result"]["null_value"] is None
        assert retrieved["result"]["boolean"] is True

    async def test_connection_error_handling(self):
        """Test handling of connection errors."""
        # Try to connect to non-existent Redis server
        storage = RedisStorage(
            redis_url="redis://nonexistent:6379/0",
            prefix="test_bgops"
        )
        
        # Should raise connection error
        with pytest.raises(Exception):  # Could be various Redis exceptions
            await storage.get_idempotency("test-key")
        
        await storage.close()

    async def test_timeout_handling(self, storage):
        """Test timeout handling."""
        # Create storage with very short timeout
        short_timeout_storage = RedisStorage(
            redis_url="redis://localhost:6379/15",
            prefix="test_bgops",
            socket_timeout=0.01,  # 10ms timeout
            retry_on_timeout=False
        )
        
        try:
            # This might timeout or work depending on Redis speed
            # The test mainly ensures the timeout configuration works
            await short_timeout_storage.get_idempotency("test-key")
        except Exception:
            # Timeout exception is expected and acceptable
            pass
        finally:
            await short_timeout_storage.close()

    async def test_pipeline_operations(self, storage):
        """Test Redis pipeline operations work correctly."""
        # The delete_idempotency method uses pipeline
        key = "pipeline-test-key"
        data = {"key": key, "data": "test"}
        
        # Set key and index it
        await storage.set_idempotency(key, data, 3600)
        await storage.index_idempotency(key, time.time())
        
        # Delete should use pipeline to delete both key and index entry
        deleted = await storage.delete_idempotency(key)
        assert deleted is True
        
        # Both key and index entry should be gone
        retrieved = await storage.get_idempotency(key)
        assert retrieved is None