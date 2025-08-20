"""
Outbox pattern implementation for exactly-once event publishing.
"""

import asyncio
import json
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import structlog

from ..models.envelope import EventEnvelope

logger = structlog.get_logger(__name__)


class OutboxStatus(str, Enum):
    """Outbox entry status."""

    PENDING = "pending"
    PUBLISHED = "published"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class OutboxEntry:
    """Outbox table entry."""

    id: str
    tenant_id: str
    envelope_id: str
    topic: str
    envelope_data: Dict[str, Any]
    status: OutboxStatus
    created_at: datetime
    published_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    retry_count: int = 0
    last_error: Optional[str] = None
    expires_at: Optional[datetime] = None

    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    def can_retry(self, max_retries: int = 3) -> bool:
        """Check if entry can be retried."""
        return (self.status == OutboxStatus.FAILED and
                self.retry_count < max_retries and
                not self.is_expired())


class OutboxStore:
    """Abstract base class for outbox storage."""

    async def create_entry(
        self,
        envelope: EventEnvelope,
        ttl_hours: int = 24
    ) -> OutboxEntry:
        """Create new outbox entry."""
        raise NotImplementedError

    async def get_entry(self, entry_id: str) -> Optional[OutboxEntry]:
        """Get outbox entry by ID."""
        raise NotImplementedError

    async def update_status(
        self,
        entry_id: str,
        status: OutboxStatus,
        error: Optional[str] = None
    ) -> bool:
        """Update entry status."""
        raise NotImplementedError

    async def get_pending_entries(
        self,
        limit: int = 100,
        tenant_id: Optional[str] = None
    ) -> List[OutboxEntry]:
        """Get pending entries for processing."""
        raise NotImplementedError

    async def get_failed_entries(
        self,
        limit: int = 100,
        max_retries: int = 3
    ) -> List[OutboxEntry]:
        """Get failed entries that can be retried."""
        raise NotImplementedError

    async def cleanup_expired(self) -> int:
        """Clean up expired entries."""
        raise NotImplementedError

    async def get_stats(self) -> Dict[str, Any]:
        """Get outbox statistics."""
        raise NotImplementedError


class PostgresOutboxStore(OutboxStore):
    """PostgreSQL-based outbox store."""

    def __init__(self, db_pool):
        self.db_pool = db_pool
        self._initialized = False

    async def initialize(self):
        """Initialize database schema."""
        if self._initialized:
            return

        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS event_outbox (
                    id VARCHAR(255) PRIMARY KEY,
                    tenant_id VARCHAR(255) NOT NULL,
                    envelope_id VARCHAR(255) NOT NULL,
                    topic VARCHAR(255) NOT NULL,
                    envelope_data JSONB NOT NULL,
                    status VARCHAR(50) NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    published_at TIMESTAMP WITH TIME ZONE,
                    failed_at TIMESTAMP WITH TIME ZONE,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    expires_at TIMESTAMP WITH TIME ZONE,

                    CONSTRAINT outbox_status_check CHECK (status IN ('pending', 'published', 'failed', 'expired'))
                );

                CREATE INDEX IF NOT EXISTS idx_outbox_status_created
                ON event_outbox (status, created_at);

                CREATE INDEX IF NOT EXISTS idx_outbox_tenant_status
                ON event_outbox (tenant_id, status);

                CREATE INDEX IF NOT EXISTS idx_outbox_expires_at
                ON event_outbox (expires_at) WHERE expires_at IS NOT NULL;

                CREATE UNIQUE INDEX IF NOT EXISTS idx_outbox_envelope_id
                ON event_outbox (envelope_id);
            """)

        self._initialized = True
        logger.info("PostgreSQL outbox store initialized")

    async def create_entry(
        self,
        envelope: EventEnvelope,
        ttl_hours: int = 24
    ) -> OutboxEntry:
        """Create new outbox entry."""
        await self.initialize()

        entry_id = f"outbox_{envelope.id}_{int(time.time())}"
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=ttl_hours)

        entry = OutboxEntry(
            id=entry_id,
            tenant_id=envelope.tenant_id,
            envelope_id=envelope.id,
            topic=envelope.get_topic_name(),
            envelope_data=envelope.to_dict(),
            status=OutboxStatus.PENDING,
            created_at=now,
            expires_at=expires_at
        )

        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO event_outbox (
                    id, tenant_id, envelope_id, topic, envelope_data,
                    status, created_at, expires_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
                entry.id, entry.tenant_id, entry.envelope_id, entry.topic,
                json.dumps(entry.envelope_data), entry.status.value,
                entry.created_at, entry.expires_at
            )

        logger.debug("Created outbox entry", entry_id=entry_id, envelope_id=envelope.id)
        return entry

    async def get_entry(self, entry_id: str) -> Optional[OutboxEntry]:
        """Get outbox entry by ID."""
        await self.initialize()

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM event_outbox WHERE id = $1
            """, entry_id)

            if not row:
                return None

            return self._row_to_entry(row)

    async def update_status(
        self,
        entry_id: str,
        status: OutboxStatus,
        error: Optional[str] = None
    ) -> bool:
        """Update entry status."""
        await self.initialize()

        now = datetime.now(timezone.utc)

        async with self.db_pool.acquire() as conn:
            if status == OutboxStatus.PUBLISHED:
                result = await conn.execute("""
                    UPDATE event_outbox
                    SET status = $1, published_at = $2, last_error = NULL
                    WHERE id = $3
                """, status.value, now, entry_id)

            elif status == OutboxStatus.FAILED:
                result = await conn.execute("""
                    UPDATE event_outbox
                    SET status = $1, failed_at = $2, retry_count = retry_count + 1, last_error = $3
                    WHERE id = $4
                """, status.value, now, error, entry_id)

            else:
                result = await conn.execute("""
                    UPDATE event_outbox
                    SET status = $1, last_error = $2
                    WHERE id = $3
                """, status.value, error, entry_id)

            return result == "UPDATE 1"

    async def get_pending_entries(
        self,
        limit: int = 100,
        tenant_id: Optional[str] = None
    ) -> List[OutboxEntry]:
        """Get pending entries for processing."""
        await self.initialize()

        async with self.db_pool.acquire() as conn:
            if tenant_id:
                rows = await conn.fetch("""
                    SELECT * FROM event_outbox
                    WHERE status = 'pending' AND tenant_id = $1
                    ORDER BY created_at ASC
                    LIMIT $2
                """, tenant_id, limit)
            else:
                rows = await conn.fetch("""
                    SELECT * FROM event_outbox
                    WHERE status = 'pending'
                    ORDER BY created_at ASC
                    LIMIT $1
                """, limit)

            return [self._row_to_entry(row) for row in rows]

    async def get_failed_entries(
        self,
        limit: int = 100,
        max_retries: int = 3
    ) -> List[OutboxEntry]:
        """Get failed entries that can be retried."""
        await self.initialize()

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM event_outbox
                WHERE status = 'failed'
                AND retry_count < $1
                AND (expires_at IS NULL OR expires_at > NOW())
                ORDER BY failed_at ASC
                LIMIT $2
            """, max_retries, limit)

            return [self._row_to_entry(row) for row in rows]

    async def cleanup_expired(self) -> int:
        """Clean up expired entries."""
        await self.initialize()

        async with self.db_pool.acquire() as conn:
            # Mark expired entries
            await conn.execute("""
                UPDATE event_outbox
                SET status = 'expired'
                WHERE expires_at IS NOT NULL
                AND expires_at <= NOW()
                AND status != 'expired'
            """)

            # Delete old expired entries (older than 7 days)
            result = await conn.execute("""
                DELETE FROM event_outbox
                WHERE status = 'expired'
                AND created_at < NOW() - INTERVAL '7 days'
            """)

            # Extract count from result
            deleted_count = int(result.split()[-1]) if result.startswith("DELETE") else 0

            if deleted_count > 0:
                logger.info("Cleaned up expired outbox entries", count=deleted_count)

            return deleted_count

    async def get_stats(self) -> Dict[str, Any]:
        """Get outbox statistics."""
        await self.initialize()

        async with self.db_pool.acquire() as conn:
            stats_row = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_entries,
                    COUNT(*) FILTER (WHERE status = 'pending') as pending_count,
                    COUNT(*) FILTER (WHERE status = 'published') as published_count,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed_count,
                    COUNT(*) FILTER (WHERE status = 'expired') as expired_count,
                    AVG(EXTRACT(EPOCH FROM (published_at - created_at))) as avg_publish_time_seconds
                FROM event_outbox
            """)

            tenant_stats = await conn.fetch("""
                SELECT tenant_id, COUNT(*) as entry_count
                FROM event_outbox
                WHERE status = 'pending'
                GROUP BY tenant_id
                ORDER BY entry_count DESC
                LIMIT 10
            """)

            return {
                "total_entries": stats_row["total_entries"],
                "by_status": {
                    "pending": stats_row["pending_count"],
                    "published": stats_row["published_count"],
                    "failed": stats_row["failed_count"],
                    "expired": stats_row["expired_count"]
                },
                "avg_publish_time_seconds": float(stats_row["avg_publish_time_seconds"] or 0),
                "top_tenants_by_pending": [
                    {"tenant_id": row["tenant_id"], "count": row["entry_count"]}
                    for row in tenant_stats
                ]
            }

    def _row_to_entry(self, row) -> OutboxEntry:
        """Convert database row to OutboxEntry."""
        return OutboxEntry(
            id=row["id"],
            tenant_id=row["tenant_id"],
            envelope_id=row["envelope_id"],
            topic=row["topic"],
            envelope_data=json.loads(row["envelope_data"]),
            status=OutboxStatus(row["status"]),
            created_at=row["created_at"],
            published_at=row["published_at"],
            failed_at=row["failed_at"],
            retry_count=row["retry_count"],
            last_error=row["last_error"],
            expires_at=row["expires_at"]
        )


class OutboxDispatcher:
    """Dispatcher for processing outbox entries."""

    def __init__(
        self,
        outbox_store: OutboxStore,
        event_publisher: Callable[[EventEnvelope], Any],
        batch_size: int = 50,
        dispatch_interval: float = 1.0,
        max_retries: int = 3
    ):
        self.outbox_store = outbox_store
        self.event_publisher = event_publisher
        self.batch_size = batch_size
        self.dispatch_interval = dispatch_interval
        self.max_retries = max_retries
        self.running = False
        self._dispatch_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._retry_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start outbox dispatcher."""
        if self.running:
            return

        self.running = True

        # Start dispatch loop
        self._dispatch_task = asyncio.create_task(self._dispatch_loop())

        # Start cleanup loop
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        # Start retry loop
        self._retry_task = asyncio.create_task(self._retry_loop())

        logger.info("Outbox dispatcher started")

    async def stop(self):
        """Stop outbox dispatcher."""
        self.running = False

        # Cancel tasks
        for task in [self._dispatch_task, self._cleanup_task, self._retry_task]:
            if task:
                task.cancel()

        # Wait for tasks to complete
        tasks = [t for t in [self._dispatch_task, self._cleanup_task, self._retry_task] if t]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        logger.info("Outbox dispatcher stopped")

    async def _dispatch_loop(self):
        """Main dispatch loop for pending entries."""
        while self.running:
            try:
                # Get pending entries
                entries = await self.outbox_store.get_pending_entries(self.batch_size)

                if entries:
                    await self._process_entries(entries)

                await asyncio.sleep(self.dispatch_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Dispatch loop error", error=str(e))
                await asyncio.sleep(self.dispatch_interval)

    async def _retry_loop(self):
        """Retry loop for failed entries."""
        while self.running:
            try:
                # Get failed entries that can be retried
                entries = await self.outbox_store.get_failed_entries(
                    self.batch_size, self.max_retries
                )

                if entries:
                    logger.info("Retrying failed outbox entries", count=len(entries))
                    await self._process_entries(entries)

                # Retry less frequently than dispatch
                await asyncio.sleep(self.dispatch_interval * 10)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Retry loop error", error=str(e))
                await asyncio.sleep(self.dispatch_interval * 10)

    async def _cleanup_loop(self):
        """Cleanup loop for expired entries."""
        while self.running:
            try:
                await self.outbox_store.cleanup_expired()

                # Cleanup less frequently
                await asyncio.sleep(300)  # 5 minutes

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Cleanup loop error", error=str(e))
                await asyncio.sleep(300)

    async def _process_entries(self, entries: List[OutboxEntry]):
        """Process a batch of outbox entries."""
        for entry in entries:
            try:
                # Reconstruct envelope
                envelope = EventEnvelope(**entry.envelope_data)

                # Publish event
                await self.event_publisher(envelope)

                # Mark as published
                await self.outbox_store.update_status(entry.id, OutboxStatus.PUBLISHED)

                logger.debug(
                    "Outbox entry published",
                    entry_id=entry.id,
                    envelope_id=entry.envelope_id,
                    topic=entry.topic
                )

            except Exception as e:
                # Mark as failed
                await self.outbox_store.update_status(
                    entry.id,
                    OutboxStatus.FAILED,
                    str(e)
                )

                logger.error(
                    "Failed to publish outbox entry",
                    entry_id=entry.id,
                    envelope_id=entry.envelope_id,
                    error=str(e)
                )


class TransactionalOutbox:
    """Transactional outbox for exactly-once publishing."""

    def __init__(self, outbox_store: OutboxStore):
        self.outbox_store = outbox_store

    @asynccontextmanager
    async def transaction(self, db_connection):
        """Context manager for transactional outbox operations."""
        # Start database transaction
        async with db_connection.transaction():
            # Create outbox context
            outbox_context = OutboxTransactionContext(self.outbox_store, db_connection)
            yield outbox_context

            # Transaction will commit automatically if no exceptions


class OutboxTransactionContext:
    """Context for outbox operations within a transaction."""

    def __init__(self, outbox_store: OutboxStore, db_connection):
        self.outbox_store = outbox_store
        self.db_connection = db_connection
        self.pending_events: List[EventEnvelope] = []

    async def add_event(self, envelope: EventEnvelope):
        """Add event to be published after transaction commits."""
        self.pending_events.append(envelope)

    async def commit_events(self):
        """Commit events to outbox (called automatically by transaction context)."""
        for envelope in self.pending_events:
            await self.outbox_store.create_entry(envelope)

        logger.debug("Committed events to outbox", count=len(self.pending_events))


class OutboxPublisher:
    """High-level publisher with outbox pattern."""

    def __init__(
        self,
        outbox_store: OutboxStore,
        dispatcher: OutboxDispatcher
    ):
        self.outbox_store = outbox_store
        self.dispatcher = dispatcher

    async def start(self):
        """Start outbox publisher."""
        await self.dispatcher.start()

    async def stop(self):
        """Stop outbox publisher."""
        await self.dispatcher.stop()

    async def publish_event(self, envelope: EventEnvelope) -> OutboxEntry:
        """Publish event via outbox pattern."""
        # Create outbox entry
        entry = await self.outbox_store.create_entry(envelope)

        logger.debug(
            "Event added to outbox",
            entry_id=entry.id,
            envelope_id=envelope.id,
            topic=entry.topic
        )

        return entry

    @asynccontextmanager
    async def transaction(self, db_connection):
        """Create transactional context for atomic publishing."""
        transactional_outbox = TransactionalOutbox(self.outbox_store)
        async with transactional_outbox.transaction(db_connection) as context:
            yield OutboxPublisherContext(context)


class OutboxPublisherContext:
    """Publisher context within a transaction."""

    def __init__(self, outbox_context: OutboxTransactionContext):
        self.outbox_context = outbox_context

    async def publish_event(self, envelope: EventEnvelope):
        """Publish event within transaction."""
        await self.outbox_context.add_event(envelope)


# Factory functions
async def create_postgres_outbox_publisher(
    db_pool,
    event_publisher: Callable[[EventEnvelope], Any],
    batch_size: int = 50,
    dispatch_interval: float = 1.0
) -> OutboxPublisher:
    """Create PostgreSQL-based outbox publisher."""

    outbox_store = PostgresOutboxStore(db_pool)
    await outbox_store.initialize()

    dispatcher = OutboxDispatcher(
        outbox_store=outbox_store,
        event_publisher=event_publisher,
        batch_size=batch_size,
        dispatch_interval=dispatch_interval
    )

    publisher = OutboxPublisher(outbox_store, dispatcher)
    await publisher.start()

    return publisher


def create_outbox_middleware(outbox_publisher: OutboxPublisher):
    """Create middleware for outbox publishing."""

    async def middleware(envelope: EventEnvelope, handler, next_middleware):
        """Middleware function."""
        # Add to outbox instead of direct publishing
        entry = await outbox_publisher.publish_event(envelope)

        # Continue with next middleware
        result = await next_middleware(envelope, handler)

        return {
            "status": "added_to_outbox",
            "outbox_entry_id": entry.id,
            "result": result
        }

    return middleware
