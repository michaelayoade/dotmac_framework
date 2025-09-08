"""Base protocols for storage backends."""
from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import asynccontextmanager, contextmanager
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator


class IdempotencyStore(Protocol):
    """Protocol for idempotency storage backends."""

    async def get(self, key: str) -> Any | None:
        """Get a stored result by key."""

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store a result with optional TTL in seconds."""

    async def exists(self, key: str) -> bool:
        """Check if a key exists in the store."""

    async def delete(self, key: str) -> None:
        """Delete a key from the store."""


class LockStore(Protocol):
    """Protocol for distributed lock storage backends."""

    @asynccontextmanager
    async def acquire_lock(
        self,
        key: str,
        timeout: float = 10.0,
        ttl: float = 60.0,
    ) -> AsyncIterator[bool]:
        """
        Acquire a distributed lock.

        Args:
            key: Lock identifier
            timeout: Maximum time to wait for lock acquisition
            ttl: Lock time-to-live in seconds

        Yields:
            True if lock was acquired, False otherwise
        """

    async def is_locked(self, key: str) -> bool:
        """Check if a lock is currently held."""

    async def release_lock(self, key: str) -> None:
        """Force release a lock (use with caution)."""


class SyncIdempotencyStore(ABC):
    """Base class for synchronous idempotency stores."""

    @abstractmethod
    def get(self, key: str) -> Any | None:
        """Get a stored result by key."""

    @abstractmethod
    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store a result with optional TTL in seconds."""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if a key exists in the store."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete a key from the store."""


class SyncLockStore(ABC):
    """Base class for synchronous lock stores."""

    @abstractmethod
    @contextmanager
    def acquire_lock(
        self,
        key: str,
        timeout: float = 10.0,
        ttl: float = 60.0,
    ) -> Iterator[bool]:
        """
        Acquire a distributed lock.

        Args:
            key: Lock identifier
            timeout: Maximum time to wait for lock acquisition
            ttl: Lock time-to-live in seconds

        Yields:
            True if lock was acquired, False otherwise
        """

    @abstractmethod
    def is_locked(self, key: str) -> bool:
        """Check if a lock is currently held."""

    @abstractmethod
    def release_lock(self, key: str) -> None:
        """Force release a lock (use with caution)."""
