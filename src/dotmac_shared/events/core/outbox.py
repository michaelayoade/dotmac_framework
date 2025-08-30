"""
Transactional Outbox Pattern Implementation.

Provides reliable event publishing with database transaction guarantees:
- Store events in database table within same transaction
- Background processor publishes events to event bus
- Handles failures with retry logic and dead letter queue
- Supports multi-tenant isolation
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

import structlog
from sqlalchemy import Column, DateTime, Integer, String, Text, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base

from .models import EventBusError, EventMetadata, EventRecord

logger = structlog.get_logger(__name__)

# SQLAlchemy Base
Base = declarative_base()


class OutboxEventStatus(str, Enum):
    """Status enumeration for outbox events."""

    PENDING = "pending"
    PROCESSING = "processing"
    PUBLISHED = "published"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class OutboxEvent(Base):
    """
    Database model for outbox events.

    Stores events that need to be published reliably with transaction guarantees.
    """

    __tablename__ = "outbox_events"

    # Primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))

    # Event identification
    event_id = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)

    # Multi-tenancy
    tenant_id = Column(String, nullable=True, index=True)

    # Event data (JSON serialized)
    event_data = Column(Text, nullable=False)
    metadata_data = Column(Text, nullable=False)

    # Routing
    topic = Column(String, nullable=True)
    partition_key = Column(String, nullable=True)

    # Status tracking
    status = Column(
        String, nullable=False, default=OutboxEventStatus.PENDING, index=True
    )
    retry_count = Column(Integer, nullable=False, default=0)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    scheduled_at = Column(
        DateTime(timezone=True), nullable=True
    )  # For delayed publishing
    published_at = Column(DateTime(timezone=True), nullable=True)

    # Error tracking
    last_error = Column(Text, nullable=True)

    def to_event_record(self) -> EventRecord:
        """Convert outbox event to EventRecord for publishing."""
        try:
            data = json.loads(self.event_data)
            metadata_dict = json.loads(self.metadata_data)

            # Reconstruct metadata
            metadata = EventMetadata(
                event_id=self.event_id, tenant_id=self.tenant_id, **metadata_dict
            )

            return EventRecord(
                event_type=self.event_type,
                data=data,
                metadata=metadata,
                topic=self.topic,
                partition_key=self.partition_key,
            )

        except Exception as e:
            logger.error(
                "Failed to convert outbox event to EventRecord",
                outbox_id=self.id,
                event_id=self.event_id,
                error=str(e),
            )
            raise

    @classmethod
    def from_event_record(
        cls,
        event: EventRecord,
        tenant_id: Optional[str] = None,
        scheduled_at: Optional[datetime] = None,
    ) -> "OutboxEvent":
        """Create outbox event from EventRecord."""
        try:
            # Extract tenant_id from event metadata if not provided
            if tenant_id is None:
                tenant_id = event.metadata.tenant_id

            # Serialize event data and metadata
            event_data = json.dumps(event.data, default=str, ensure_ascii=False)

            # Prepare metadata dict (exclude event_id to avoid duplication)
            metadata_dict = event.metadata.model_dump(exclude={"event_id"})
            metadata_data = json.dumps(metadata_dict, default=str, ensure_ascii=False)

            return cls(
                event_id=event.metadata.event_id,
                event_type=event.event_type,
                tenant_id=tenant_id,
                event_data=event_data,
                metadata_data=metadata_data,
                topic=event.topic,
                partition_key=event.partition_key or event.metadata.partition_key,
                scheduled_at=scheduled_at,
            )

        except Exception as e:
            logger.error(
                "Failed to create outbox event from EventRecord",
                event_id=event.metadata.event_id,
                event_type=event.event_type,
                error=str(e),
            )
            raise


class OutboxManager:
    """
    Manages transactional outbox operations.

    Provides methods to store events in database and process them reliably.
    """

    def __init__(
        self,
        session_factory,
        max_retries: int = 5,
        retry_delay_seconds: int = 30,
        batch_size: int = 50,
        dead_letter_threshold: int = 10,
    ):
        """
        Initialize outbox manager.

        Args:
            session_factory: SQLAlchemy async session factory
            max_retries: Maximum retry attempts before marking as failed
            retry_delay_seconds: Delay between retries
            batch_size: Number of events to process in each batch
            dead_letter_threshold: Retry count threshold for dead letter
        """
        self.session_factory = session_factory
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.batch_size = batch_size
        self.dead_letter_threshold = dead_letter_threshold

        logger.info(
            "Outbox manager initialized", max_retries=max_retries, batch_size=batch_size
        )

    async def store_event(
        self,
        session: AsyncSession,
        event: EventRecord,
        *,
        tenant_id: Optional[str] = None,
        scheduled_at: Optional[datetime] = None,
    ) -> str:
        """
        Store an event in the outbox table within a transaction.

        Args:
            session: Database session (should be within a transaction)
            event: Event to store
            tenant_id: Override tenant ID
            scheduled_at: Schedule event for future publishing

        Returns:
            Outbox event ID
        """
        try:
            outbox_event = OutboxEvent.from_event_record(
                event=event, tenant_id=tenant_id, scheduled_at=scheduled_at
            )

            session.add(outbox_event)
            await session.flush()  # Get the ID without committing

            logger.debug(
                "Event stored in outbox",
                outbox_id=outbox_event.id,
                event_id=event.metadata.event_id,
                event_type=event.event_type,
                tenant_id=tenant_id,
            )

            return outbox_event.id

        except Exception as e:
            logger.error(
                "Failed to store event in outbox",
                event_id=event.metadata.event_id,
                event_type=event.event_type,
                error=str(e),
            )
            raise EventBusError(f"Failed to store event in outbox: {e}") from e

    async def store_events_batch(
        self,
        session: AsyncSession,
        events: List[EventRecord],
        *,
        tenant_id: Optional[str] = None,
    ) -> List[str]:
        """
        Store multiple events in the outbox table within a transaction.

        Args:
            session: Database session (should be within a transaction)
            events: Events to store
            tenant_id: Override tenant ID for all events

        Returns:
            List of outbox event IDs
        """
        try:
            outbox_events = []
            for event in events:
                outbox_event = OutboxEvent.from_event_record(
                    event=event, tenant_id=tenant_id
                )
                outbox_events.append(outbox_event)

            session.add_all(outbox_events)
            await session.flush()

            ids = [oe.id for oe in outbox_events]

            logger.debug(
                "Event batch stored in outbox",
                batch_size=len(events),
                tenant_id=tenant_id,
            )

            return ids

        except Exception as e:
            logger.error(
                "Failed to store event batch in outbox",
                batch_size=len(events),
                error=str(e),
            )
            raise EventBusError(f"Failed to store event batch in outbox: {e}") from e

    async def get_pending_events(
        self,
        limit: Optional[int] = None,
        tenant_id: Optional[str] = None,
        include_scheduled: bool = True,
    ) -> List[OutboxEvent]:
        """
        Get pending events ready for publishing.

        Args:
            limit: Maximum number of events to return
            tenant_id: Filter by tenant ID
            include_scheduled: Include scheduled events that are due

        Returns:
            List of pending OutboxEvent objects
        """
        try:
            async with self.session_factory() as session:
                # Base query for pending events
                query = select(OutboxEvent).where(
                    OutboxEvent.status == OutboxEventStatus.PENDING
                )

                # Add tenant filter
                if tenant_id:
                    query = query.where(OutboxEvent.tenant_id == tenant_id)

                # Handle scheduled events
                if include_scheduled:
                    now = datetime.now(timezone.utc)
                    query = query.where(
                        (OutboxEvent.scheduled_at.is_(None))
                        | (OutboxEvent.scheduled_at <= now)
                    )
                else:
                    query = query.where(OutboxEvent.scheduled_at.is_(None))

                # Order by creation time and limit
                query = query.order_by(OutboxEvent.created_at)
                if limit:
                    query = query.limit(limit)

                result = await session.execute(query)
                events = result.scalars().all()

                return list(events)

        except Exception as e:
            logger.error(
                "Failed to get pending events",
                limit=limit,
                tenant_id=tenant_id,
                error=str(e),
            )
            raise

    async def mark_processing(self, event_ids: List[str]) -> None:
        """Mark events as currently being processed."""
        try:
            async with self.session_factory() as session:
                await session.execute(
                    update(OutboxEvent)
                    .where(OutboxEvent.id.in_(event_ids))
                    .values(
                        status=OutboxEventStatus.PROCESSING,
                        updated_at=datetime.now(timezone.utc),
                    )
                )
                await session.commit()

                logger.debug("Events marked as processing", event_count=len(event_ids))

        except Exception as e:
            logger.error(
                "Failed to mark events as processing",
                event_count=len(event_ids),
                error=str(e),
            )
            raise

    async def mark_published(self, event_ids: List[str]) -> None:
        """Mark events as successfully published."""
        try:
            async with self.session_factory() as session:
                now = datetime.now(timezone.utc)
                await session.execute(
                    update(OutboxEvent)
                    .where(OutboxEvent.id.in_(event_ids))
                    .values(
                        status=OutboxEventStatus.PUBLISHED,
                        published_at=now,
                        updated_at=now,
                        last_error=None,
                    )
                )
                await session.commit()

                logger.debug("Events marked as published", event_count=len(event_ids))

        except Exception as e:
            logger.error(
                "Failed to mark events as published",
                event_count=len(event_ids),
                error=str(e),
            )
            raise

    async def mark_failed(
        self, event_id: str, error: str, increment_retry: bool = True
    ) -> None:
        """Mark event as failed and optionally increment retry count."""
        try:
            async with self.session_factory() as session:
                # Get current event to check retry count
                result = await session.execute(
                    select(OutboxEvent).where(OutboxEvent.id == event_id)
                )
                event = result.scalar_one_or_none()

                if not event:
                    logger.warning(
                        "Event not found for failure marking", event_id=event_id
                    )
                    return

                # Determine new status based on retry count
                new_retry_count = (
                    event.retry_count + 1 if increment_retry else event.retry_count
                )

                if new_retry_count >= self.dead_letter_threshold:
                    new_status = OutboxEventStatus.DEAD_LETTER
                    logger.warning(
                        "Event moved to dead letter",
                        event_id=event_id,
                        retry_count=new_retry_count,
                    )
                else:
                    new_status = OutboxEventStatus.FAILED

                # Calculate next retry time
                next_retry = datetime.now(timezone.utc) + timedelta(
                    seconds=self.retry_delay_seconds
                    * (2 ** min(new_retry_count, 5))  # Exponential backoff
                )

                await session.execute(
                    update(OutboxEvent)
                    .where(OutboxEvent.id == event_id)
                    .values(
                        status=new_status,
                        retry_count=new_retry_count,
                        last_error=error,
                        updated_at=datetime.now(timezone.utc),
                        scheduled_at=(
                            next_retry
                            if new_status == OutboxEventStatus.FAILED
                            else None
                        ),
                    )
                )
                await session.commit()

                logger.debug(
                    "Event marked as failed",
                    event_id=event_id,
                    retry_count=new_retry_count,
                    status=new_status,
                )

        except Exception as e:
            logger.error(
                "Failed to mark event as failed", event_id=event_id, error=str(e)
            )
            raise

    async def reset_stuck_events(self, timeout_minutes: int = 30) -> int:
        """
        Reset events stuck in processing status.

        Args:
            timeout_minutes: Minutes after which processing events are considered stuck

        Returns:
            Number of events reset
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(
                minutes=timeout_minutes
            )

            async with self.session_factory() as session:
                result = await session.execute(
                    update(OutboxEvent)
                    .where(
                        (OutboxEvent.status == OutboxEventStatus.PROCESSING)
                        & (OutboxEvent.updated_at < cutoff_time)
                    )
                    .values(
                        status=OutboxEventStatus.PENDING,
                        updated_at=datetime.now(timezone.utc),
                    )
                )

                reset_count = result.rowcount
                await session.commit()

                if reset_count > 0:
                    logger.info(
                        "Reset stuck processing events",
                        reset_count=reset_count,
                        timeout_minutes=timeout_minutes,
                    )

                return reset_count

        except Exception as e:
            logger.error(
                "Failed to reset stuck events",
                timeout_minutes=timeout_minutes,
                error=str(e),
            )
            raise

    async def cleanup_old_events(
        self, older_than_days: int = 7, keep_failed: bool = True
    ) -> int:
        """
        Clean up old published events.

        Args:
            older_than_days: Delete events older than this many days
            keep_failed: Whether to keep failed/dead letter events

        Returns:
            Number of events deleted
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=older_than_days)

            async with self.session_factory() as session:
                query = delete(OutboxEvent).where(
                    (OutboxEvent.status == OutboxEventStatus.PUBLISHED)
                    & (OutboxEvent.published_at < cutoff_date)
                )

                result = await session.execute(query)
                deleted_count = result.rowcount
                await session.commit()

                if deleted_count > 0:
                    logger.info(
                        "Cleaned up old events",
                        deleted_count=deleted_count,
                        older_than_days=older_than_days,
                    )

                return deleted_count

        except Exception as e:
            logger.error(
                "Failed to cleanup old events",
                older_than_days=older_than_days,
                error=str(e),
            )
            raise

    async def get_stats(self) -> Dict[str, Any]:
        """Get outbox statistics."""
        try:
            async with self.session_factory() as session:
                # Count by status
                stats_query = """
                SELECT status, COUNT(*) as count
                FROM outbox_events
                GROUP BY status
                """

                result = await session.execute(stats_query)
                status_counts = {row.status: row.count for row in result}

                # Total events
                total = sum(status_counts.values())

                # Failed events in last hour
                one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
                recent_failures_query = select(OutboxEvent).where(
                    (
                        OutboxEvent.status.in_(
                            [OutboxEventStatus.FAILED, OutboxEventStatus.DEAD_LETTER]
                        )
                    )
                    & (OutboxEvent.updated_at >= one_hour_ago)
                )

                recent_failures_result = await session.execute(recent_failures_query)
                recent_failures = len(recent_failures_result.scalars().all())

                return {
                    "total_events": total,
                    "by_status": status_counts,
                    "recent_failures": recent_failures,
                    "config": {
                        "max_retries": self.max_retries,
                        "batch_size": self.batch_size,
                        "dead_letter_threshold": self.dead_letter_threshold,
                    },
                }

        except Exception as e:
            logger.error("Failed to get outbox stats", error=str(e))
            return {"error": str(e)}
