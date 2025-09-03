"""
Distributed locking and coordination primitives.

Provides Redis-based distributed locks and PostgreSQL advisory locks
for coordinating operations across multiple application instances.
"""

import asyncio
import hashlib
import logging
import time
import uuid
from typing import Optional, Union, Any
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

try:
    import redis
    from redis import Redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
    Redis = None

logger = logging.getLogger(__name__)


class LockError(Exception):
    """Base exception for lock-related errors."""
    pass


class LockTimeout(LockError):
    """Raised when lock acquisition times out."""
    pass


class LockNotAcquired(LockError):
    """Raised when lock cannot be acquired."""
    pass


class LockAlreadyReleased(LockError):
    """Raised when attempting to release an already released lock."""
    pass


class RedisLock:
    """
    Distributed lock using Redis with automatic expiration and renewal.
    
    Features:
    - Automatic lock expiration to prevent deadlocks
    - Lock renewal for long-running operations
    - Unique lock identifiers to prevent accidental releases
    - Lua script-based atomic operations
    """
    
    # Lua script for atomic lock release
    RELEASE_SCRIPT = """
    if redis.call("GET", KEYS[1]) == ARGV[1] then
        return redis.call("DEL", KEYS[1])
    else
        return 0
    end
    """
    
    # Lua script for atomic lock renewal
    RENEW_SCRIPT = """
    if redis.call("GET", KEYS[1]) == ARGV[1] then
        return redis.call("EXPIRE", KEYS[1], ARGV[2])
    else
        return 0
    end
    """
    
    def __init__(
        self,
        name: str,
        ttl: int = 30,
        redis_client: Optional[Redis] = None,
        key_prefix: str = "dotmac:lock:",
        auto_renewal: bool = False,
        renewal_interval: float = 0.7,  # Renew at 70% of TTL
    ):
        """
        Initialize Redis lock.
        
        Args:
            name: Lock name/identifier
            ttl: Lock TTL in seconds
            redis_client: Redis client (uses global if None)
            key_prefix: Key prefix for lock keys
            auto_renewal: Enable automatic lock renewal
            renewal_interval: Renewal interval as fraction of TTL
        """
        if not REDIS_AVAILABLE:
            raise LockError(
                "Redis not available. Install with: pip install dotmac-database[redis]"
            )
        
        self.name = name
        self.ttl = ttl
        self.key_prefix = key_prefix
        self.auto_renewal = auto_renewal
        self.renewal_interval = renewal_interval
        
        # Redis client
        if redis_client:
            self.redis = redis_client
        else:
            from ..caching import get_redis_client
            self.redis = get_redis_client()
        
        # Lock state
        self.key = f"{key_prefix}{name}"
        self.identifier = str(uuid.uuid4())
        self.acquired = False
        self.acquisition_time: Optional[float] = None
        
        # Auto-renewal task
        self._renewal_task: Optional[asyncio.Task] = None
        
        # Compile Lua scripts
        self._release_script = self.redis.register_script(self.RELEASE_SCRIPT)
        self._renew_script = self.redis.register_script(self.RENEW_SCRIPT)
    
    async def acquire(self, timeout: Optional[float] = None, blocking: bool = True) -> bool:
        """
        Acquire the lock.
        
        Args:
            timeout: Maximum time to wait for lock (None = no timeout)
            blocking: Whether to block waiting for the lock
            
        Returns:
            True if lock was acquired, False if not (non-blocking mode)
            
        Raises:
            LockTimeout: If timeout expires while waiting
            LockError: If lock acquisition fails
        """
        if self.acquired:
            logger.warning(f"Lock {self.name} already acquired")
            return True
        
        start_time = time.time()
        
        while True:
            try:
                # Attempt to acquire lock using SET with NX and EX
                result = self.redis.set(
                    self.key,
                    self.identifier,
                    nx=True,  # Only set if key doesn't exist
                    ex=self.ttl  # Set expiration
                )
                
                if result:
                    self.acquired = True
                    self.acquisition_time = time.time()
                    
                    logger.debug(f"Acquired lock {self.name} (TTL: {self.ttl}s)")
                    
                    # Start auto-renewal if enabled
                    if self.auto_renewal:
                        await self._start_renewal()
                    
                    return True
                
                # Lock not acquired
                if not blocking:
                    return False
                
                # Check timeout
                if timeout is not None:
                    elapsed = time.time() - start_time
                    if elapsed >= timeout:
                        raise LockTimeout(
                            f"Timeout waiting for lock {self.name} after {elapsed:.2f}s"
                        )
                
                # Wait before retrying
                await asyncio.sleep(0.1)
                
            except redis.RedisError as e:
                logger.error(f"Redis error acquiring lock {self.name}: {e}")
                raise LockError(f"Failed to acquire lock {self.name}: {e}") from e
    
    async def release(self) -> bool:
        """
        Release the lock.
        
        Returns:
            True if lock was released, False if lock was not held
            
        Raises:
            LockError: If release operation fails
        """
        if not self.acquired:
            return True
        
        try:
            # Stop auto-renewal
            await self._stop_renewal()
            
            # Use Lua script for atomic release
            result = self._release_script(keys=[self.key], args=[self.identifier])
            
            if result == 1:
                self.acquired = False
                self.acquisition_time = None
                logger.debug(f"Released lock {self.name}")
                return True
            else:
                logger.warning(f"Lock {self.name} was not held or expired")
                self.acquired = False
                return False
                
        except redis.RedisError as e:
            logger.error(f"Redis error releasing lock {self.name}: {e}")
            raise LockError(f"Failed to release lock {self.name}: {e}") from e
    
    async def renew(self, new_ttl: Optional[int] = None) -> bool:
        """
        Renew the lock with a new TTL.
        
        Args:
            new_ttl: New TTL in seconds (uses original TTL if None)
            
        Returns:
            True if lock was renewed, False if lock was not held
        """
        if not self.acquired:
            logger.warning(f"Cannot renew lock {self.name}: not acquired")
            return False
        
        ttl = new_ttl or self.ttl
        
        try:
            # Use Lua script for atomic renewal
            result = self._renew_script(keys=[self.key], args=[self.identifier, str(ttl)])
            
            if result == 1:
                logger.debug(f"Renewed lock {self.name} with TTL {ttl}s")
                return True
            else:
                logger.warning(f"Lock {self.name} was not held or expired during renewal")
                self.acquired = False
                await self._stop_renewal()
                return False
                
        except redis.RedisError as e:
            logger.error(f"Redis error renewing lock {self.name}: {e}")
            return False
    
    async def is_locked(self) -> bool:
        """
        Check if the lock is currently held (by anyone).
        
        Returns:
            True if lock exists, False otherwise
        """
        try:
            return self.redis.exists(self.key) > 0
        except redis.RedisError as e:
            logger.error(f"Redis error checking lock {self.name}: {e}")
            return False
    
    async def get_lock_holder(self) -> Optional[str]:
        """
        Get the identifier of the current lock holder.
        
        Returns:
            Lock holder identifier or None if not locked
        """
        try:
            holder = self.redis.get(self.key)
            return holder.decode('utf-8') if holder else None
        except redis.RedisError as e:
            logger.error(f"Redis error getting lock holder {self.name}: {e}")
            return None
    
    async def get_ttl(self) -> int:
        """
        Get the remaining TTL of the lock.
        
        Returns:
            TTL in seconds (-1 if no expiry, -2 if not exists)
        """
        try:
            return self.redis.ttl(self.key)
        except redis.RedisError as e:
            logger.error(f"Redis error getting TTL for lock {self.name}: {e}")
            return -2
    
    async def _start_renewal(self) -> None:
        """Start automatic lock renewal task."""
        if self._renewal_task and not self._renewal_task.done():
            return
        
        renewal_interval_seconds = self.ttl * self.renewal_interval
        self._renewal_task = asyncio.create_task(self._renewal_loop(renewal_interval_seconds))
    
    async def _stop_renewal(self) -> None:
        """Stop automatic lock renewal task."""
        if self._renewal_task and not self._renewal_task.done():
            self._renewal_task.cancel()
            try:
                await self._renewal_task
            except asyncio.CancelledError:
                pass
    
    async def _renewal_loop(self, interval: float) -> None:
        """Automatic renewal loop."""
        try:
            while self.acquired:
                await asyncio.sleep(interval)
                
                if not self.acquired:
                    break
                
                renewed = await self.renew()
                if not renewed:
                    logger.warning(f"Failed to renew lock {self.name}")
                    break
                    
        except asyncio.CancelledError:
            logger.debug(f"Renewal loop cancelled for lock {self.name}")
        except Exception as e:
            logger.error(f"Error in renewal loop for lock {self.name}: {e}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.release()
    
    def __del__(self):
        """Ensure lock is released on deletion."""
        if self.acquired:
            logger.warning(f"Lock {self.name} was not explicitly released")


class PgAdvisoryLock:
    """
    PostgreSQL advisory lock for database-level coordination.
    
    Uses PostgreSQL's advisory locking mechanism for coordination
    within the database without affecting table data.
    """
    
    def __init__(
        self,
        key: Union[int, str],
        session: Optional[AsyncSession] = None,
        shared: bool = False,
    ):
        """
        Initialize PostgreSQL advisory lock.
        
        Args:
            key: Lock key (int or string converted to int hash)
            session: Database session
            shared: Use shared lock instead of exclusive
        """
        self.key = self._normalize_key(key)
        self.session = session
        self.shared = shared
        self.acquired = False
        
        # Function names based on lock type
        self.acquire_func = "pg_try_advisory_lock_shared" if shared else "pg_try_advisory_lock"
        self.release_func = "pg_advisory_unlock_shared" if shared else "pg_advisory_unlock"
    
    def _normalize_key(self, key: Union[int, str]) -> int:
        """Convert key to integer for PostgreSQL advisory locks."""
        if isinstance(key, int):
            return key
        elif isinstance(key, str):
            # Use hash of string as integer key
            hash_obj = hashlib.md5(key.encode('utf-8'))
            # Convert first 8 bytes to signed 64-bit integer
            return int.from_bytes(hash_obj.digest()[:8], byteorder='big', signed=True)
        else:
            raise ValueError(f"Invalid key type: {type(key)}. Must be int or str.")
    
    async def acquire(self, timeout: Optional[float] = None, blocking: bool = True) -> bool:
        """
        Acquire the advisory lock.
        
        Args:
            timeout: Maximum time to wait (None = no timeout)
            blocking: Whether to block waiting for the lock
            
        Returns:
            True if lock was acquired, False if not (non-blocking mode)
            
        Raises:
            LockTimeout: If timeout expires
            LockError: If acquisition fails
        """
        if self.acquired:
            return True
        
        if not self.session:
            raise LockError("No database session provided")
        
        start_time = time.time()
        
        while True:
            try:
                # Try to acquire the lock
                result = await self.session.execute(
                    text(f"SELECT {self.acquire_func}(:key)"),
                    {"key": self.key}
                )
                
                acquired = result.scalar()
                
                if acquired:
                    self.acquired = True
                    logger.debug(f"Acquired PG advisory lock {self.key} ({'shared' if self.shared else 'exclusive'})")
                    return True
                
                # Lock not acquired
                if not blocking:
                    return False
                
                # Check timeout
                if timeout is not None:
                    elapsed = time.time() - start_time
                    if elapsed >= timeout:
                        raise LockTimeout(
                            f"Timeout waiting for PG advisory lock {self.key} after {elapsed:.2f}s"
                        )
                
                # Wait before retrying
                await asyncio.sleep(0.1)
                
            except Exception as e:
                if isinstance(e, LockTimeout):
                    raise
                logger.error(f"Error acquiring PG advisory lock {self.key}: {e}")
                raise LockError(f"Failed to acquire PG advisory lock {self.key}: {e}") from e
    
    async def release(self) -> bool:
        """
        Release the advisory lock.
        
        Returns:
            True if lock was released, False if lock was not held
            
        Raises:
            LockError: If release operation fails
        """
        if not self.acquired:
            return True
        
        if not self.session:
            raise LockError("No database session provided")
        
        try:
            result = await self.session.execute(
                text(f"SELECT {self.release_func}(:key)"),
                {"key": self.key}
            )
            
            released = result.scalar()
            
            if released:
                self.acquired = False
                logger.debug(f"Released PG advisory lock {self.key}")
                return True
            else:
                logger.warning(f"PG advisory lock {self.key} was not held")
                self.acquired = False
                return False
                
        except Exception as e:
            logger.error(f"Error releasing PG advisory lock {self.key}: {e}")
            raise LockError(f"Failed to release PG advisory lock {self.key}: {e}") from e
    
    async def is_locked(self) -> bool:
        """
        Check if the lock is currently held by this session.
        
        Note: This only checks if THIS session holds the lock,
        not if the lock is held by any session.
        
        Returns:
            True if this session holds the lock
        """
        return self.acquired
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.release()


@asynccontextmanager
async def redis_lock(
    name: str,
    ttl: int = 30,
    timeout: Optional[float] = None,
    redis_client: Optional[Redis] = None,
    **kwargs: Any,
):
    """
    Async context manager for Redis distributed locks.
    
    Args:
        name: Lock name
        ttl: Lock TTL in seconds
        timeout: Acquisition timeout
        redis_client: Redis client
        **kwargs: Additional RedisLock arguments
        
    Example:
        async with redis_lock("import-data", ttl=60) as lock:
            if lock.acquired:
                # Perform exclusive operation
                await import_data()
            else:
                raise Exception("Could not acquire lock")
    """
    lock = RedisLock(name, ttl=ttl, redis_client=redis_client, **kwargs)
    
    try:
        await lock.acquire(timeout=timeout)
        yield lock
    finally:
        if lock.acquired:
            await lock.release()


@asynccontextmanager
async def pg_advisory_lock(
    key: Union[int, str],
    session: AsyncSession,
    timeout: Optional[float] = None,
    shared: bool = False,
):
    """
    Async context manager for PostgreSQL advisory locks.
    
    Args:
        key: Lock key
        session: Database session
        timeout: Acquisition timeout
        shared: Use shared lock
        
    Example:
        async with pg_advisory_lock(12345, session) as lock:
            if lock.acquired:
                # Perform database operation requiring coordination
                await update_global_counters(session)
    """
    lock = PgAdvisoryLock(key, session=session, shared=shared)
    
    try:
        await lock.acquire(timeout=timeout)
        yield lock
    finally:
        if lock.acquired:
            await lock.release()