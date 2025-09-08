"""Idempotency utilities for ensuring operations run exactly once."""
from __future__ import annotations

import functools
import hashlib
import json
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, TypeVar

from typing_extensions import Self

if TYPE_CHECKING:
    from .storage.base import IdempotencyStore, SyncIdempotencyStore

F = TypeVar("F", bound=Callable[..., Any])
AsyncF = TypeVar("AsyncF", bound=Callable[..., Awaitable[Any]])


class IdempotencyError(Exception):
    """Raised when idempotency operations fail."""


def generate_key(*args: Any, **kwargs: Any) -> str:
    """
    Generate a deterministic key from function arguments.

    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        SHA256 hash of serialized arguments
    """
    # Create a deterministic representation of arguments
    key_data = {
        "args": args,
        "kwargs": dict(sorted(kwargs.items())),  # Sort for consistency
    }

    try:
        # Serialize to JSON for hashing
        serialized = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()
    except (TypeError, ValueError):
        # Fallback for non-JSON serializable arguments
        fallback = f"args:{len(args)}_kwargs:{len(kwargs)}_{hash(str(args))}_{hash(str(kwargs))}"
        return hashlib.sha256(fallback.encode()).hexdigest()


def with_idempotency(
    store: IdempotencyStore,
    key: str | Callable[..., str] | None = None,
    ttl: int | None = 3600,
    include_result: bool = True,
) -> Callable[[AsyncF], AsyncF]:
    """
    Async decorator for idempotent operations.

    Args:
        store: Storage backend for idempotency tracking
        key: Static key, key generator function, or None for auto-generation
        ttl: Time-to-live for stored results in seconds (None for no expiration)
        include_result: Whether to store and return cached results

    Returns:
        Decorated function that ensures idempotent execution

    Example:
        @with_idempotency(store, key="user_signup", ttl=300)
        async def signup_user(email: str):
            # This will only run once per email within 300 seconds
            return create_user_account(email)
    """
    def decorator(func: AsyncF) -> AsyncF:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Generate idempotency key
            if callable(key):
                idem_key = key(*args, **kwargs)
            elif key is not None:
                idem_key = key
            else:
                # Auto-generate key from function name and arguments
                func_name = f"{func.__module__}.{func.__qualname__}"
                arg_key = generate_key(*args, **kwargs)
                idem_key = f"{func_name}:{arg_key}"

            # Check if operation was already performed
            if await store.exists(idem_key):
                if include_result:
                    cached_result = await store.get(idem_key)
                    if cached_result is not None:
                        return cached_result
                else:
                    # Just return None for operations without stored results
                    return None

            # Perform the operation
            result = await func(*args, **kwargs)

            # Store the result or marker
            if include_result:
                await store.set(idem_key, result, ttl)
            else:
                # Store a marker indicating operation was performed
                await store.set(idem_key, True, ttl)

            return result

        return wrapper
    return decorator


def with_sync_idempotency(
    store: SyncIdempotencyStore,
    key: str | Callable[..., str] | None = None,
    ttl: int | None = 3600,
    include_result: bool = True,
) -> Callable[[F], F]:
    """
    Synchronous decorator for idempotent operations.

    Args:
        store: Storage backend for idempotency tracking
        key: Static key, key generator function, or None for auto-generation
        ttl: Time-to-live for stored results in seconds (None for no expiration)
        include_result: Whether to store and return cached results

    Returns:
        Decorated function that ensures idempotent execution

    Example:
        @with_sync_idempotency(store, key="batch_process", ttl=300)
        def process_batch(batch_id: str):
            # This will only run once per batch_id within 300 seconds
            return process_data(batch_id)
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Generate idempotency key
            if callable(key):
                idem_key = key(*args, **kwargs)
            elif key is not None:
                idem_key = key
            else:
                # Auto-generate key from function name and arguments
                func_name = f"{func.__module__}.{func.__qualname__}"
                arg_key = generate_key(*args, **kwargs)
                idem_key = f"{func_name}:{arg_key}"

            # Check if operation was already performed
            if store.exists(idem_key):
                if include_result:
                    cached_result = store.get(idem_key)
                    if cached_result is not None:
                        return cached_result
                else:
                    # Just return None for operations without stored results
                    return None

            # Perform the operation
            result = func(*args, **kwargs)

            # Store the result or marker
            if include_result:
                store.set(idem_key, result, ttl)
            else:
                # Store a marker indicating operation was performed
                store.set(idem_key, True, ttl)

            return result

        return wrapper
    return decorator


class IdempotencyManager:
    """Context manager for manual idempotency control."""

    def __init__(
        self,
        store: IdempotencyStore,
        key: str,
        ttl: int | None = 3600,
        include_result: bool = True,
    ):
        self.store = store
        self.key = key
        self.ttl = ttl
        self.include_result = include_result
        self._performed = False

    async def __aenter__(self) -> Self:
        # Check if operation was already performed
        if await self.store.exists(self.key):
            self._performed = True
            if self.include_result:
                self.cached_result = await self.store.get(self.key)
            else:
                # For marker-only mode, store the marker value
                self.cached_result = await self.store.get(self.key)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Store result if operation was successful and not already performed
        if not self._performed and exc_type is None and hasattr(self, "_result"):
            if self.include_result:
                await self.store.set(self.key, self._result, self.ttl)
            else:
                await self.store.set(self.key, True, self.ttl)

    @property
    def already_performed(self) -> bool:
        """Check if the operation was already performed."""
        return self._performed

    def set_result(self, result: Any) -> None:
        """Set the result to be stored."""
        self._result = result

    def get_cached_result(self) -> Any:
        """Get the cached result if operation was already performed."""
        if not self._performed:
            msg = "Operation was not already performed"
            raise IdempotencyError(msg)
        return getattr(self, "cached_result", None)


class SyncIdempotencyManager:
    """Synchronous context manager for manual idempotency control."""

    def __init__(
        self,
        store: SyncIdempotencyStore,
        key: str,
        ttl: int | None = 3600,
        include_result: bool = True,
    ):
        self.store = store
        self.key = key
        self.ttl = ttl
        self.include_result = include_result
        self._performed = False

    def __enter__(self) -> Self:
        # Check if operation was already performed
        if self.store.exists(self.key):
            self._performed = True
            if self.include_result:
                self.cached_result = self.store.get(self.key)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Store result if operation was successful and not already performed
        if not self._performed and exc_type is None and hasattr(self, "_result"):
            if self.include_result:
                self.store.set(self.key, self._result, self.ttl)
            else:
                self.store.set(self.key, True, self.ttl)

    @property
    def already_performed(self) -> bool:
        """Check if the operation was already performed."""
        return self._performed

    def set_result(self, result: Any) -> None:
        """Set the result to be stored."""
        self._result = result

    def get_cached_result(self) -> Any:
        """Get the cached result if operation was already performed."""
        if not self._performed:
            msg = "Operation was not already performed"
            raise IdempotencyError(msg)
        return getattr(self, "cached_result", None)
