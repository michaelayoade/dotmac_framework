"""
Tests for idempotency functionality.
"""

import asyncio
import pytest
from datetime import datetime, timedelta, timezone

from dotmac.tasks import (
    BackgroundOperationsManager,
    MemoryStorage,
    OperationStatus,
)


class TestIdempotency:
    """Test idempotency operations."""

    @pytest.fixture
    async def manager(self):
        """Create manager with memory storage."""
        storage = MemoryStorage()
        manager = BackgroundOperationsManager(storage=storage)
        await manager.start()
        yield manager
        await manager.stop()

    def test_generate_idempotency_key(self, manager):
        """Test idempotency key generation."""
        key1 = manager.generate_idempotency_key(
            tenant_id="tenant1",
            user_id="user1", 
            operation_type="send_email",
            parameters={"to": "test@example.com", "subject": "Test"}
        )
        
        # Same inputs should generate same key
        key2 = manager.generate_idempotency_key(
            tenant_id="tenant1",
            user_id="user1",
            operation_type="send_email", 
            parameters={"to": "test@example.com", "subject": "Test"}
        )
        
        assert key1 == key2
        
        # Different inputs should generate different key
        key3 = manager.generate_idempotency_key(
            tenant_id="tenant1",
            user_id="user1",
            operation_type="send_email",
            parameters={"to": "different@example.com", "subject": "Test"}
        )
        
        assert key1 != key3

    async def test_create_idempotency_key(self, manager):
        """Test creating idempotency keys."""
        key_obj = await manager.create_idempotency_key(
            tenant_id="tenant1",
            user_id="user1",
            operation_type="send_email",
            parameters={"to": "test@example.com"}
        )
        
        assert key_obj.tenant_id == "tenant1"
        assert key_obj.user_id == "user1"
        assert key_obj.operation_type == "send_email"
        assert key_obj.status == OperationStatus.PENDING
        assert key_obj.result is None
        assert key_obj.error is None
        assert key_obj.expires_at > datetime.now(timezone.utc)

    async def test_check_idempotency(self, manager):
        """Test checking idempotency keys."""
        # Non-existent key
        result = await manager.check_idempotency("nonexistent")
        assert result is None
        
        # Create and check key
        key_obj = await manager.create_idempotency_key(
            tenant_id="tenant1",
            user_id="user1", 
            operation_type="send_email",
        )
        
        found_key = await manager.check_idempotency(key_obj.key)
        assert found_key is not None
        assert found_key.key == key_obj.key
        assert found_key.tenant_id == "tenant1"
        assert found_key.status == OperationStatus.PENDING

    async def test_complete_idempotent_operation(self, manager):
        """Test completing idempotent operations."""
        # Create key
        key_obj = await manager.create_idempotency_key(
            tenant_id="tenant1",
            user_id="user1",
            operation_type="send_email",
        )
        
        # Complete successfully
        result = {"message_id": "123", "status": "sent"}
        success = await manager.complete_idempotent_operation(
            key_obj.key, result
        )
        assert success is True
        
        # Check updated state
        updated_key = await manager.check_idempotency(key_obj.key)
        assert updated_key.status == OperationStatus.COMPLETED
        assert updated_key.result == result
        assert updated_key.error is None

    async def test_complete_idempotent_operation_with_error(self, manager):
        """Test completing idempotent operations with error."""
        # Create key
        key_obj = await manager.create_idempotency_key(
            tenant_id="tenant1",
            user_id="user1",
            operation_type="send_email",
        )
        
        # Complete with error
        error_msg = "SMTP connection failed"
        success = await manager.complete_idempotent_operation(
            key_obj.key, {}, error=error_msg
        )
        assert success is True
        
        # Check updated state  
        updated_key = await manager.check_idempotency(key_obj.key)
        assert updated_key.status == OperationStatus.FAILED
        assert updated_key.error == error_msg

    async def test_idempotency_key_expiration(self, manager):
        """Test idempotency key expiration."""
        # Create key with short TTL
        key_obj = await manager.create_idempotency_key(
            tenant_id="tenant1",
            user_id="user1",
            operation_type="send_email",
            ttl=1  # 1 second
        )
        
        # Key should exist initially
        found_key = await manager.check_idempotency(key_obj.key)
        assert found_key is not None
        
        # Wait for expiration
        await asyncio.sleep(1.5)
        
        # Key should be expired (memory storage checks expiry on access)
        expired_key = await manager.check_idempotency(key_obj.key)
        # Depending on implementation, might return None or expired object
        # Memory storage removes expired keys on access
        assert expired_key is None

    async def test_custom_idempotency_key(self, manager):
        """Test creating idempotency key with custom key."""
        custom_key = "my-custom-key-123"
        
        key_obj = await manager.create_idempotency_key(
            tenant_id="tenant1", 
            user_id="user1",
            operation_type="send_email",
            key=custom_key
        )
        
        assert key_obj.key == custom_key
        
        # Check it's stored
        found_key = await manager.check_idempotency(custom_key)
        assert found_key is not None
        assert found_key.key == custom_key

    async def test_concurrent_idempotency_operations(self, manager):
        """Test concurrent operations on same idempotency key."""
        key_obj = await manager.create_idempotency_key(
            tenant_id="tenant1",
            user_id="user1",
            operation_type="send_email",
        )
        
        # Start multiple completion operations concurrently
        async def complete_operation(result_suffix):
            result = {"message_id": f"123{result_suffix}", "status": "sent"}
            return await manager.complete_idempotent_operation(
                key_obj.key, result
            )
        
        # Run concurrent completions
        results = await asyncio.gather(
            complete_operation("a"),
            complete_operation("b"),
            complete_operation("c"),
            return_exceptions=True
        )
        
        # All should succeed (last one wins for result)
        assert all(r is True for r in results)
        
        # Check final state
        final_key = await manager.check_idempotency(key_obj.key)
        assert final_key.status == OperationStatus.COMPLETED
        assert final_key.result is not None

    async def test_idempotency_key_indexing(self, manager):
        """Test idempotency key indexing for cleanup."""
        key_obj = await manager.create_idempotency_key(
            tenant_id="tenant1",
            user_id="user1", 
            operation_type="send_email",
            ttl=60
        )
        
        # Check key is indexed
        now = datetime.now(timezone.utc).timestamp()
        expired_keys = await manager.storage.get_expired_idempotency_keys(now + 120)
        assert key_obj.key in expired_keys

    async def test_multiple_tenant_operations(self, manager):
        """Test idempotency isolation between tenants."""
        # Create keys for different tenants with same operation
        key1 = await manager.create_idempotency_key(
            tenant_id="tenant1",
            user_id="user1",
            operation_type="send_email",
            parameters={"to": "test@example.com"}
        )
        
        key2 = await manager.create_idempotency_key(
            tenant_id="tenant2",
            user_id="user1", 
            operation_type="send_email",
            parameters={"to": "test@example.com"}
        )
        
        # Keys should be different (different tenants)
        assert key1.key != key2.key
        
        # Complete operations with different results
        await manager.complete_idempotent_operation(
            key1.key, {"tenant": "tenant1"}
        )
        await manager.complete_idempotent_operation(
            key2.key, {"tenant": "tenant2"}
        )
        
        # Check results are isolated
        result1 = await manager.check_idempotency(key1.key)
        result2 = await manager.check_idempotency(key2.key)
        
        assert result1.result["tenant"] == "tenant1"
        assert result2.result["tenant"] == "tenant2"