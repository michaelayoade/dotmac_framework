"""
Unit of Work implementations and utilities.

This module provides concrete implementations and utilities for the Unit of Work pattern,
which maintains a list of objects affected by a business transaction and coordinates
writing out changes and resolving concurrency problems.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, TypeVar
from uuid import uuid4

from .errors import RepositoryError
from .protocols import UnitOfWork

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BaseUnitOfWork(ABC):
    """Abstract base class for Unit of Work implementations.

    This class provides a framework for implementing the Unit of Work pattern
    with transaction management and object tracking capabilities.
    """

    def __init__(self) -> None:
        """Initialize the unit of work."""
        self._transaction_id: str = str(uuid4())
        self._is_committed: bool = False
        self._is_rolled_back: bool = False
        self._tracked_objects: list[Any] = []
        self._metadata: dict[str, Any] = {}

    @property
    def transaction_id(self) -> str:
        """Get the unique transaction identifier."""
        return self._transaction_id

    @property
    def is_committed(self) -> bool:
        """Check if the transaction has been committed."""
        return self._is_committed

    @property
    def is_rolled_back(self) -> bool:
        """Check if the transaction has been rolled back."""
        return self._is_rolled_back

    @property
    def is_active(self) -> bool:
        """Check if the transaction is still active."""
        return not (self._is_committed or self._is_rolled_back)

    async def __aenter__(self) -> "BaseUnitOfWork":
        """Enter the unit of work context."""
        await self._begin()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the unit of work context."""
        if exc_type is not None:
            # Exception occurred, rollback
            await self.rollback()
        elif not self._is_committed and not self._is_rolled_back:
            # No exception but not committed or rolled back, auto-commit
            await self.commit()

    async def commit(self) -> None:
        """Commit the transaction."""
        if self._is_committed:
            raise RepositoryError(
                "Transaction already committed",
                error_code="transaction_already_committed"
            )

        if self._is_rolled_back:
            raise RepositoryError(
                "Cannot commit rolled back transaction",
                error_code="transaction_rolled_back"
            )

        try:
            await self._commit()
            self._is_committed = True
        except Exception as e:
            # Commit failed, attempt rollback
            try:
                await self._rollback()
                self._is_rolled_back = True
            except Exception as rollback_error:
                # Rollback also failed, but we want to raise the original commit error
                logger.warning(f"Rollback failed during commit error handling: {rollback_error}")
            raise RepositoryError(f"Transaction commit failed: {e}") from e

    async def rollback(self) -> None:
        """Rollback the transaction."""
        if self._is_rolled_back:
            return  # Already rolled back, nothing to do

        if self._is_committed:
            raise RepositoryError(
                "Cannot rollback committed transaction",
                error_code="transaction_already_committed"
            )

        try:
            await self._rollback()
            self._is_rolled_back = True
        except Exception as e:
            raise RepositoryError(f"Transaction rollback failed: {e}") from e

    def track_object(self, obj: T) -> T:
        """Track an object for changes within this unit of work.

        Args:
            obj: The object to track

        Returns:
            The tracked object
        """
        if obj not in self._tracked_objects:
            self._tracked_objects.append(obj)
        return obj

    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata for this unit of work.

        Args:
            key: Metadata key
            value: Metadata value
        """
        self._metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata for this unit of work.

        Args:
            key: Metadata key
            default: Default value if key not found

        Returns:
            Metadata value or default
        """
        return self._metadata.get(key, default)

    @abstractmethod
    async def _begin(self) -> None:
        """Begin the transaction (implemented by subclasses)."""
        pass

    @abstractmethod
    async def _commit(self) -> None:
        """Commit the transaction (implemented by subclasses)."""
        pass

    @abstractmethod
    async def _rollback(self) -> None:
        """Rollback the transaction (implemented by subclasses)."""
        pass


class MemoryUnitOfWork(BaseUnitOfWork):
    """In-memory unit of work implementation for testing.

    This implementation provides a simple in-memory unit of work that doesn't
    actually perform any persistence operations. Useful for testing scenarios.
    """

    def __init__(self) -> None:
        """Initialize the memory unit of work."""
        super().__init__()
        self._operations: list[dict[str, Any]] = []

    async def _begin(self) -> None:
        """Begin the in-memory transaction."""
        self._operations.clear()

    async def _commit(self) -> None:
        """Commit the in-memory transaction."""
        # In a real implementation, this would persist all operations
        # For testing, we just log that commit was called
        self._operations.append({
            "type": "commit",
            "transaction_id": self.transaction_id,
            "tracked_objects_count": len(self._tracked_objects)
        })

    async def _rollback(self) -> None:
        """Rollback the in-memory transaction."""
        # Clear all operations and tracked objects
        self._operations.clear()
        self._tracked_objects.clear()

    def get_operations(self) -> list[dict[str, Any]]:
        """Get the list of operations performed in this unit of work.

        Returns:
            List of operations for testing/debugging
        """
        return self._operations.copy()


class CompositeUnitOfWork(BaseUnitOfWork):
    """Unit of work that coordinates multiple child units of work.

    This implementation allows you to compose multiple units of work together,
    ensuring that all child units are committed or rolled back together.
    """

    def __init__(self, child_uows: list[UnitOfWork]) -> None:
        """Initialize the composite unit of work.

        Args:
            child_uows: List of child units of work to coordinate
        """
        super().__init__()
        self._child_uows = child_uows

    async def _begin(self) -> None:
        """Begin all child transactions."""
        for uow in self._child_uows:
            if hasattr(uow, '_begin'):
                await uow._begin()  # type: ignore

    async def _commit(self) -> None:
        """Commit all child transactions."""
        committed_uows = []
        try:
            for uow in self._child_uows:
                await uow.commit()
                committed_uows.append(uow)
        except Exception as e:
            # If any commit fails, rollback all previously committed units
            for committed_uow in committed_uows:
                try:
                    await committed_uow.rollback()
                except Exception as rollback_error:
                    # Log rollback errors during cleanup but continue
                    logger.warning(
                        f"Rollback failed during composite UoW cleanup: {rollback_error}"
                    )
            raise e

    async def _rollback(self) -> None:
        """Rollback all child transactions."""
        for uow in self._child_uows:
            try:
                await uow.rollback()
            except Exception as rollback_error:
                # Continue rolling back other units even if one fails
                logger.warning(f"Rollback failed for unit in composite UoW: {rollback_error}")


__all__ = [
    "BaseUnitOfWork",
    "MemoryUnitOfWork",
    "CompositeUnitOfWork",
]
