"""
Exactly-once delivery semantics with dedupe store.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Optional, Tuple

import structlog

from ..models.envelope import EventEnvelope

logger = structlog.get_logger(__name__)


class DedupeStatus(str, Enum):
    """Status of dedupe record."""

    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DedupeRecord:
    """Dedupe record for exactly-once processing."""

    key: str
    envelope_id: str
    tenant_id: str
    consumer_group: str
    status: DedupeStatus
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    attempt_count: int = 0
    last_error: Optional[str] = None
    processing_node: Optional[str] = None

    def is_expired(self) -> bool:
        """Check if record is expired."""
        return datetime.now(timezone.utc) > self.expires_at

    def can_retry(self, max_attempts: int = 3) -> bool:
        """Check if processing can be retried."""
        return self.attempt_count < max_attempts and self.status == DedupeStatus.FAILED


class DedupeStore:
    """Abstract base class for dedupe storage."""

    async def get_record(self, key: str) -> Optional[DedupeRecord]:
        """Get dedupe record by key."""
        raise NotImplementedError

    async def create_record(
        self,
        key: str,
        envelope_id: str,
        tenant_id: str,
        consumer_group: str,
        ttl_seconds: int = 3600
    ) -> DedupeRecord:
        """Create new dedupe record."""
        raise NotImplementedError

    async def update_status(
        self,
        key: str,
        status: DedupeStatus,
        error: Optional[str] = None,
        processing_node: Optional[str] = None
    ) -> bool:
        """Update record status."""
        raise NotImplementedError

    async def cleanup_expired(self) -> int:
        """Clean up expired records."""
        raise NotImplementedError

    async def get_stats(self) -> Dict[str, Any]:
        """Get dedupe store statistics."""
        raise NotImplementedError


class RedisDedupeStore(DedupeStore):
    """Redis-based dedupe store implementation."""

    def __init__(self, redis_client, key_prefix: str = "dedupe:"):
        self.redis = redis_client
        self.key_prefix = key_prefix
        self._cleanup_interval = 300  # 5 minutes
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """Start background cleanup task."""
        if self._running:
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Redis dedupe store started")

    async def stop(self):
        """Stop background cleanup task."""
        self._running = False

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        logger.info("Redis dedupe store stopped")

    def _make_key(self, key: str) -> str:
        """Create Redis key with prefix."""
        return f"{self.key_prefix}{key}"

    async def get_record(self, key: str) -> Optional[DedupeRecord]:
        """Get dedupe record by key."""
        redis_key = self._make_key(key)

        try:
            data = await self.redis.hgetall(redis_key)
            if not data:
                return None

            return DedupeRecord(
                key=key,
                envelope_id=data[b"envelope_id"].decode(),
                tenant_id=data[b"tenant_id"].decode(),
                consumer_group=data[b"consumer_group"].decode(),
                status=DedupeStatus(data[b"status"].decode()),
                created_at=datetime.fromisoformat(data[b"created_at"].decode()),
                updated_at=datetime.fromisoformat(data[b"updated_at"].decode()),
                expires_at=datetime.fromisoformat(data[b"expires_at"].decode()),
                attempt_count=int(data[b"attempt_count"]),
                last_error=data.get(b"last_error", b"").decode() or None,
                processing_node=data.get(b"processing_node", b"").decode() or None
            )

        except Exception as e:
            logger.error("Failed to get dedupe record", key=key, error=str(e))
            return None

    async def create_record(
        self,
        key: str,
        envelope_id: str,
        tenant_id: str,
        consumer_group: str,
        ttl_seconds: int = 3600
    ) -> DedupeRecord:
        """Create new dedupe record."""
        redis_key = self._make_key(key)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=ttl_seconds)

        record = DedupeRecord(
            key=key,
            envelope_id=envelope_id,
            tenant_id=tenant_id,
            consumer_group=consumer_group,
            status=DedupeStatus.PROCESSING,
            created_at=now,
            updated_at=now,
            expires_at=expires_at,
            attempt_count=1
        )

        try:
            # Use Redis transaction to ensure atomicity
            async with self.redis.pipeline(transaction=True) as pipe:
                await pipe.hset(redis_key, mapping={
                    "envelope_id": envelope_id,
                    "tenant_id": tenant_id,
                    "consumer_group": consumer_group,
                    "status": record.status.value,
                    "created_at": record.created_at.isoformat(),
                    "updated_at": record.updated_at.isoformat(),
                    "expires_at": record.expires_at.isoformat(),
                    "attempt_count": record.attempt_count,
                    "last_error": "",
                    "processing_node": ""
                })
                await pipe.expire(redis_key, ttl_seconds)
                await pipe.execute()

            logger.debug("Created dedupe record", key=key, envelope_id=envelope_id)
            return record

        except Exception as e:
            logger.error("Failed to create dedupe record", key=key, error=str(e))
            raise

    async def update_status(
        self,
        key: str,
        status: DedupeStatus,
        error: Optional[str] = None,
        processing_node: Optional[str] = None
    ) -> bool:
        """Update record status."""
        redis_key = self._make_key(key)
        now = datetime.now(timezone.utc)

        try:
            # Get current record to increment attempt count
            current = await self.get_record(key)
            if not current:
                logger.warning("Dedupe record not found for status update", key=key)
                return False

            attempt_count = current.attempt_count
            if status == DedupeStatus.FAILED:
                attempt_count += 1

            update_data = {
                "status": status.value,
                "updated_at": now.isoformat(),
                "attempt_count": attempt_count
            }

            if error:
                update_data["last_error"] = error

            if processing_node:
                update_data["processing_node"] = processing_node

            await self.redis.hset(redis_key, mapping=update_data)

            logger.debug(
                "Updated dedupe record status",
                key=key,
                status=status.value,
                attempt_count=attempt_count
            )
            return True

        except Exception as e:
            logger.error("Failed to update dedupe record", key=key, error=str(e))
            return False

    async def cleanup_expired(self) -> int:
        """Clean up expired records."""
        try:
            pattern = f"{self.key_prefix}*"
            cursor = 0
            cleaned_count = 0

            while True:
                cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)

                if keys:
                    # Check each key for expiration
                    for key in keys:
                        try:
                            ttl = await self.redis.ttl(key)
                            if ttl == -1:  # Key exists but has no expiration
                                await self.redis.delete(key)
                                cleaned_count += 1
                        except Exception as e:
                            logger.warning("Error checking key TTL", key=key.decode(), error=str(e))

                if cursor == 0:
                    break

            if cleaned_count > 0:
                logger.info("Cleaned up expired dedupe records", count=cleaned_count)

            return cleaned_count

        except Exception as e:
            logger.error("Failed to cleanup expired records", error=str(e))
            return 0

    async def get_stats(self) -> Dict[str, Any]:  # noqa: C901
        """Get dedupe store statistics."""
        try:
            pattern = f"{self.key_prefix}*"
            cursor = 0
            stats = {
                "total_records": 0,
                "by_status": {status.value: 0 for status in DedupeStatus},
                "by_consumer_group": {},
                "expired_records": 0
            }

            while True:
                cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)

                for key in keys:
                    try:
                        data = await self.redis.hgetall(key)
                        if data:
                            stats["total_records"] += 1

                            status = data.get(b"status", b"").decode()
                            if status in stats["by_status"]:
                                stats["by_status"][status] += 1

                            consumer_group = data.get(b"consumer_group", b"").decode()
                            if consumer_group:
                                stats["by_consumer_group"][consumer_group] = \
                                    stats["by_consumer_group"].get(consumer_group, 0) + 1

                            # Check if expired
                            expires_at_str = data.get(b"expires_at", b"").decode()
                            if expires_at_str:
                                expires_at = datetime.fromisoformat(expires_at_str)
                                if expires_at < datetime.now(timezone.utc):
                                    stats["expired_records"] += 1

                    except Exception as e:
                        logger.warning("Error reading dedupe record for stats", error=str(e))

                if cursor == 0:
                    break

            return stats

        except Exception as e:
            logger.error("Failed to get dedupe store stats", error=str(e))
            return {}

    async def _cleanup_loop(self):
        """Background cleanup loop."""
        while self._running:
            try:
                await self.cleanup_expired()
                await asyncio.sleep(self._cleanup_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Cleanup loop error", error=str(e))
                await asyncio.sleep(self._cleanup_interval)


class ExactlyOnceProcessor:
    """Exactly-once event processor using dedupe store."""

    def __init__(
        self,
        dedupe_store: DedupeStore,
        consumer_group: str,
        ttl_seconds: int = 3600,
        max_attempts: int = 3
    ):
        self.dedupe_store = dedupe_store
        self.consumer_group = consumer_group
        self.ttl_seconds = ttl_seconds
        self.max_attempts = max_attempts
        self.processing_node = f"node_{id(self)}"

    def _make_dedupe_key(self, envelope: EventEnvelope) -> str:
        """Create dedupe key from envelope."""
        return f"{envelope.tenant_id}:{self.consumer_group}:{envelope.id}"

    async def should_process(self, envelope: EventEnvelope) -> Tuple[bool, Optional[DedupeRecord]]:
        """
        Check if event should be processed based on dedupe logic.

        Returns:
            Tuple of (should_process, existing_record)
        """
        dedupe_key = self._make_dedupe_key(envelope)

        try:
            existing_record = await self.dedupe_store.get_record(dedupe_key)

            if not existing_record:
                # First time seeing this event
                record = await self.dedupe_store.create_record(
                    key=dedupe_key,
                    envelope_id=envelope.id,
                    tenant_id=envelope.tenant_id,
                    consumer_group=self.consumer_group,
                    ttl_seconds=self.ttl_seconds
                )
                return True, record

            # Check if record is expired
            if existing_record.is_expired():
                logger.info("Dedupe record expired, allowing reprocessing",
                           envelope_id=envelope.id, key=dedupe_key)

                # Create new record
                record = await self.dedupe_store.create_record(
                    key=dedupe_key,
                    envelope_id=envelope.id,
                    tenant_id=envelope.tenant_id,
                    consumer_group=self.consumer_group,
                    ttl_seconds=self.ttl_seconds
                )
                return True, record

            # Check status
            if existing_record.status == DedupeStatus.COMPLETED:
                logger.debug("Event already processed successfully",
                           envelope_id=envelope.id, key=dedupe_key)
                return False, existing_record

            if existing_record.status == DedupeStatus.PROCESSING:
                logger.debug("Event currently being processed",
                           envelope_id=envelope.id, key=dedupe_key)
                return False, existing_record

            if existing_record.status == DedupeStatus.FAILED:
                if existing_record.can_retry(self.max_attempts):
                    logger.info("Retrying failed event",
                              envelope_id=envelope.id,
                              key=dedupe_key,
                              attempt=existing_record.attempt_count + 1)

                    # Update to processing status
                    await self.dedupe_store.update_status(
                        key=dedupe_key,
                        status=DedupeStatus.PROCESSING,
                        processing_node=self.processing_node
                    )
                    return True, existing_record
                else:
                    logger.warning("Event exceeded max retry attempts",
                                 envelope_id=envelope.id,
                                 key=dedupe_key,
                                 attempts=existing_record.attempt_count)
                    return False, existing_record

            return False, existing_record

        except Exception as e:
            logger.error("Error checking dedupe status",
                        envelope_id=envelope.id, error=str(e))
            # In case of error, allow processing to avoid blocking
            return True, None

    async def mark_completed(self, envelope: EventEnvelope) -> bool:
        """Mark event processing as completed."""
        dedupe_key = self._make_dedupe_key(envelope)

        try:
            success = await self.dedupe_store.update_status(
                key=dedupe_key,
                status=DedupeStatus.COMPLETED,
                processing_node=self.processing_node
            )

            if success:
                logger.debug("Marked event as completed",
                           envelope_id=envelope.id, key=dedupe_key)
            else:
                logger.warning("Failed to mark event as completed",
                             envelope_id=envelope.id, key=dedupe_key)

            return success

        except Exception as e:
            logger.error("Error marking event as completed",
                        envelope_id=envelope.id, error=str(e))
            return False

    async def mark_failed(self, envelope: EventEnvelope, error: str) -> bool:
        """Mark event processing as failed."""
        dedupe_key = self._make_dedupe_key(envelope)

        try:
            success = await self.dedupe_store.update_status(
                key=dedupe_key,
                status=DedupeStatus.FAILED,
                error=error,
                processing_node=self.processing_node
            )

            if success:
                logger.debug("Marked event as failed",
                           envelope_id=envelope.id, key=dedupe_key, error=error)
            else:
                logger.warning("Failed to mark event as failed",
                             envelope_id=envelope.id, key=dedupe_key)

            return success

        except Exception as e:
            logger.error("Error marking event as failed",
                        envelope_id=envelope.id, error=str(e))
            return False

    async def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        try:
            store_stats = await self.dedupe_store.get_stats()

            # Filter by consumer group
            consumer_group_stats = {
                "consumer_group": self.consumer_group,
                "processing_node": self.processing_node,
                "total_records": store_stats.get("by_consumer_group", {}).get(self.consumer_group, 0),
                "by_status": store_stats.get("by_status", {}),
                "expired_records": store_stats.get("expired_records", 0)
            }

            return consumer_group_stats

        except Exception as e:
            logger.error("Error getting processing stats", error=str(e))
            return {}


class ExactlyOnceDecorator:
    """Decorator for exactly-once event processing."""

    def __init__(self, processor: ExactlyOnceProcessor):
        self.processor = processor

    def __call__(self, handler_func):
        """Decorate event handler function."""

        async def wrapper(envelope: EventEnvelope, *args, **kwargs):
            # Check if should process
            should_process, record = await self.processor.should_process(envelope)

            if not should_process:
                logger.debug("Skipping duplicate event", envelope_id=envelope.id)
                return {"status": "duplicate", "record": record}

            try:
                # Call original handler
                result = await handler_func(envelope, *args, **kwargs)

                # Mark as completed
                await self.processor.mark_completed(envelope)

                return {"status": "completed", "result": result}

            except Exception as e:
                # Mark as failed
                await self.processor.mark_failed(envelope, str(e))

                logger.error("Event processing failed",
                           envelope_id=envelope.id, error=str(e))
                raise

        return wrapper


# Convenience function for creating exactly-once processor
async def create_exactly_once_processor(
    redis_client,
    consumer_group: str,
    ttl_seconds: int = 3600,
    max_attempts: int = 3
) -> ExactlyOnceProcessor:
    """Create and start exactly-once processor with Redis dedupe store."""

    dedupe_store = RedisDedupeStore(redis_client)
    await dedupe_store.start()

    processor = ExactlyOnceProcessor(
        dedupe_store=dedupe_store,
        consumer_group=consumer_group,
        ttl_seconds=ttl_seconds,
        max_attempts=max_attempts
    )

    return processor
