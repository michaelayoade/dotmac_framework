"""
Tests for Unit of Work implementations.
"""

import pytest

from dotmac_service_kernel.errors import RepositoryError
from dotmac_service_kernel.uow import (
    CompositeUnitOfWork,
    MemoryUnitOfWork,
)


class TestMemoryUnitOfWork:
    """Test MemoryUnitOfWork implementation."""

    async def test_basic_workflow(self):
        """Test basic commit workflow."""
        uow = MemoryUnitOfWork()

        # Initial state
        assert uow.is_active is True
        assert uow.is_committed is False
        assert uow.is_rolled_back is False

        # Begin and commit
        async with uow:
            uow.track_object("test_object")
            uow.set_metadata("test", "value")

        # After context exit, should be committed
        assert uow.is_committed is True
        assert uow.is_rolled_back is False
        assert uow.is_active is False

        operations = uow.get_operations()
        assert len(operations) == 1
        assert operations[0]["type"] == "commit"
        assert operations[0]["tracked_objects_count"] == 1

    async def test_explicit_commit(self):
        """Test explicit commit."""
        uow = MemoryUnitOfWork()

        async with uow:
            await uow.commit()

        assert uow.is_committed is True
        assert len(uow.get_operations()) == 1

    async def test_rollback_on_exception(self):
        """Test automatic rollback on exception."""
        uow = MemoryUnitOfWork()

        with pytest.raises(ValueError):
            async with uow:
                uow.track_object("test")
                raise ValueError("Test error")

        assert uow.is_rolled_back is True
        assert uow.is_committed is False
        assert len(uow.get_operations()) == 0  # Operations cleared on rollback

    async def test_explicit_rollback(self):
        """Test explicit rollback."""
        uow = MemoryUnitOfWork()

        async with uow:
            uow.track_object("test")
            await uow.rollback()

        assert uow.is_rolled_back is True
        assert uow.is_committed is False

    async def test_double_commit_error(self):
        """Test that double commit raises error."""
        uow = MemoryUnitOfWork()

        await uow._begin()
        await uow.commit()

        with pytest.raises(RepositoryError) as exc_info:
            await uow.commit()

        assert "already committed" in str(exc_info.value)
        assert exc_info.value.error_code == "transaction_already_committed"

    async def test_commit_after_rollback_error(self):
        """Test that commit after rollback raises error."""
        uow = MemoryUnitOfWork()

        await uow._begin()
        await uow.rollback()

        with pytest.raises(RepositoryError) as exc_info:
            await uow.commit()

        assert "rolled back" in str(exc_info.value)

    async def test_rollback_after_commit_error(self):
        """Test that rollback after commit raises error."""
        uow = MemoryUnitOfWork()

        await uow._begin()
        await uow.commit()

        with pytest.raises(RepositoryError) as exc_info:
            await uow.rollback()

        assert "committed" in str(exc_info.value)

    async def test_object_tracking(self):
        """Test object tracking functionality."""
        uow = MemoryUnitOfWork()

        await uow._begin()

        obj1 = "object1"
        obj2 = "object2"

        # Track objects
        tracked1 = uow.track_object(obj1)
        tracked2 = uow.track_object(obj2)

        assert tracked1 is obj1
        assert tracked2 is obj2

        # Track same object again (should not duplicate)
        tracked_again = uow.track_object(obj1)
        assert tracked_again is obj1
        assert len(uow._tracked_objects) == 2

    async def test_metadata(self):
        """Test metadata functionality."""
        uow = MemoryUnitOfWork()

        # Set and get metadata
        uow.set_metadata("user_id", "123")
        uow.set_metadata("action", "create")

        assert uow.get_metadata("user_id") == "123"
        assert uow.get_metadata("action") == "create"
        assert uow.get_metadata("nonexistent") is None
        assert uow.get_metadata("nonexistent", "default") == "default"

    def test_transaction_id(self):
        """Test transaction ID generation."""
        uow1 = MemoryUnitOfWork()
        uow2 = MemoryUnitOfWork()

        assert isinstance(uow1.transaction_id, str)
        assert isinstance(uow2.transaction_id, str)
        assert uow1.transaction_id != uow2.transaction_id


class TestCompositeUnitOfWork:
    """Test CompositeUnitOfWork implementation."""

    async def test_successful_composite_commit(self):
        """Test successful commit of all child UoWs."""
        child1 = MemoryUnitOfWork()
        child2 = MemoryUnitOfWork()

        composite = CompositeUnitOfWork([child1, child2])

        async with composite:
            child1.track_object("obj1")
            child2.track_object("obj2")

        # All should be committed
        assert composite.is_committed is True
        assert child1.is_committed is True
        assert child2.is_committed is True

    async def test_rollback_on_exception(self):
        """Test rollback of all child UoWs on exception."""
        child1 = MemoryUnitOfWork()
        child2 = MemoryUnitOfWork()

        composite = CompositeUnitOfWork([child1, child2])

        with pytest.raises(ValueError):
            async with composite:
                child1.track_object("obj1")
                raise ValueError("Test error")

        # All should be rolled back
        assert composite.is_rolled_back is True
        assert child1.is_rolled_back is True
        assert child2.is_rolled_back is True

    async def test_empty_composite(self):
        """Test composite UoW with no children."""
        composite = CompositeUnitOfWork([])

        async with composite:
            pass

        assert composite.is_committed is True


class MockFailingUoW:
    """Mock UoW that fails on commit for testing."""

    def __init__(self):
        self.committed = False
        self.rolled_back = False

    async def commit(self):
        raise RepositoryError("Commit failed")

    async def rollback(self):
        self.rolled_back = True


class MockSuccessUoW:
    """Mock UoW that succeeds for testing."""

    def __init__(self):
        self.committed = False
        self.rolled_back = False

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True


class TestCompositeFailureHandling:
    """Test CompositeUnitOfWork failure scenarios."""

    async def test_partial_commit_failure_rollback(self):
        """Test that if one child fails to commit, others are rolled back."""
        success_uow = MockSuccessUoW()
        failing_uow = MockFailingUoW()

        composite = CompositeUnitOfWork([success_uow, failing_uow])

        await composite._begin()

        with pytest.raises(RepositoryError):
            await composite._commit()

        # Success UoW should have been committed then rolled back
        assert success_uow.committed is True
        assert success_uow.rolled_back is True
