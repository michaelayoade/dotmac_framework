"""
Outbox SDK for dotmac_core_events.

Provides transactional outbox pattern implementation with:
- Database integration for reliable event storage
- Background event dispatch with retry logic
- Dead letter queue for failed events
- Multi-tenant isolation
- SQLAlchemy async support
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker

logger = structlog.get_logger(__name__)

Base = declarative_base()


class OutboxEventStatus(Enum):
    """Status of outbox events."""

    PENDING = "pending"
    PROCESSING = "processing"
    PUBLISHED = "published"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class OutboxEvent(Base):
    """Outbox event model for database storage."""

    __tablename__ = "outbox_events"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False)
    event_data = Column(Text, nullable=False)
    partition_key = Column(String, nullable=True)
    event_metadata = Column(Text, nullable=True)
    status = Column(String, nullable=False, default=OutboxEventStatus.PENDING.value)
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    next_retry_at = Column(DateTime, nullable=True)
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    published_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "event_type": self.event_type,
            "event_data": json.loads(self.event_data) if self.event_data else {},
            "partition_key": self.partition_key,
            "metadata": json.loads(self.event_metadata) if self.event_metadata else {},
            "status": self.status,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "next_retry_at": (
                self.next_retry_at.isoformat() if self.next_retry_at else None
            ),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "published_at": (
                self.published_at.isoformat() if self.published_at else None
            ),
            "error_message": self.error_message,
        }


class OutboxSDK:
    """
    Outbox SDK for transactional outbox pattern implementation.

    Provides:
    - Transactional event storage within database transactions
    - Background event dispatch with retry logic
    - Dead letter queue for failed events
    - Multi-tenant isolation
    - Metrics and monitoring
    """

    def __init__(
        self,
        tenant_id: str,
        event_bus_sdk: Optional[Any] = None,
        session_factory: Optional[sessionmaker] = None,
        dispatch_interval: int = 5,
        max_retries: int = 3,
        retry_backoff_multiplier: float = 2.0,
    ):
        """
        Initialize the Outbox SDK.

        Args:
            tenant_id: Tenant identifier for isolation
            event_bus_sdk: EventBusSDK instance for publishing events
            session_factory: SQLAlchemy async session factory
            dispatch_interval: Interval between dispatch attempts (seconds)
            max_retries: Maximum retry attempts for failed events
            retry_backoff_multiplier: Backoff multiplier for retries
        """
        self.tenant_id = tenant_id
        self.event_bus_sdk = event_bus_sdk
        self.session_factory = session_factory
        self.dispatch_interval = dispatch_interval
        self.max_retries = max_retries
        self.retry_backoff_multiplier = retry_backoff_multiplier

        # Background task management
        self._dispatch_task: Optional[asyncio.Task] = None
        self._running = False

        # Metrics
        self._stored_count = 0
        self._published_count = 0
        self._failed_count = 0
        self._retry_count = 0

    async def start_background_dispatch(self) -> None:
        """Start the background dispatch task."""
        if self._running:
            return

        self._running = True
        self._dispatch_task = asyncio.create_task(self._dispatch_loop())

        logger.info(
            "Outbox background dispatch started",
            tenant_id=self.tenant_id,
            dispatch_interval=self.dispatch_interval,
        )

    async def stop_background_dispatch(self) -> None:
        """Stop the background dispatch task."""
        if not self._running:
            return

        self._running = False

        if self._dispatch_task:
            self._dispatch_task.cancel()
            try:
                await self._dispatch_task
            except asyncio.CancelledError:
                pass

        logger.info("Outbox background dispatch stopped", tenant_id=self.tenant_id)

    async def store_event(
        self,
        session: AsyncSession,
        event_type: str,
        data: Dict[str, Any],
        partition_key: Optional[str] = None,
        event_metadata: Optional[Dict[str, Any]] = None,
        max_retries: Optional[int] = None,
    ) -> str:
        """
        Store an event in the outbox within a database transaction.

        Args:
            session: Database session (part of larger transaction)
            event_type: Event type identifier
            data: Event payload data
            partition_key: Optional partition key
            event_metadata: Optional event metadata
            max_retries: Optional override for max retries

        Returns:
            Event ID
        """
        try:
            event_id = str(uuid.uuid4())

            outbox_event = OutboxEvent(
                id=event_id,
                tenant_id=self.tenant_id,
                event_type=event_type,
                event_data=json.dumps(data),
                partition_key=partition_key,
                event_metadata=(
                    json.dumps(event_metadata or {}) if event_metadata else None
                ),
                max_retries=max_retries or self.max_retries,
            )

            session.add(outbox_event)

            # Update metrics
            self._stored_count += 1

            logger.debug(
                "Event stored in outbox",
                event_id=event_id,
                event_type=event_type,
                tenant_id=self.tenant_id,
            )

            return event_id

        except Exception as e:
            logger.error(
                "Failed to store event in outbox",
                event_type=event_type,
                tenant_id=self.tenant_id,
                error=str(e),
            )
            raise

    async def dispatch_pending_events(self) -> Dict[str, int]:
        """
        Dispatch all pending events for this tenant.

        Returns:
            Dictionary with dispatch statistics
        """
        if not self.session_factory or not self.event_bus_sdk:
            logger.warning("Session factory or event bus not configured")
            return {"processed": 0, "published": 0, "failed": 0}

        processed = 0
        published = 0
        failed = 0

        try:
            async with self.session_factory() as session:
                # Get pending events for this tenant
                stmt = (
                    select(OutboxEvent)
                    .where(
                        OutboxEvent.tenant_id == self.tenant_id,
                        OutboxEvent.status.in_(
                            [
                                OutboxEventStatus.PENDING.value,
                                OutboxEventStatus.FAILED.value,
                            ]
                        ),
                        OutboxEvent.retry_count < OutboxEvent.max_retries,
                    )
                    .order_by(OutboxEvent.created_at)
                )

                result = await session.execute(stmt)
                events = result.scalars().all()

                for event in events:
                    processed += 1

                    # Check if it's time to retry
                    if event.next_retry_at and event.next_retry_at > datetime.now(
                        timezone.utc
                    ):
                        continue

                    # Mark as processing
                    event.status = OutboxEventStatus.PROCESSING.value
                    event.updated_at = datetime.now(timezone.utc)

                    try:
                        # Parse event data
                        event_data = json.loads(event.event_data)
                        metadata_dict = (
                            json.loads(event.event_metadata)
                            if event.event_metadata
                            else {}
                        )

                        # Convert to EventMetadata if available
                        event_metadata = None
                        if hasattr(self.event_bus_sdk, "EventMetadata"):
                            event_metadata = self.event_bus_sdk.EventMetadata.from_dict(
                                metadata_dict
                            )

                        # Publish via event bus
                        await self.event_bus_sdk.publish(
                            event_type=event.event_type,
                            data=event_data,
                            partition_key=event.partition_key,
                            metadata=event_metadata,
                        )

                        # Mark as published
                        event.status = OutboxEventStatus.PUBLISHED.value
                        event.published_at = datetime.now(timezone.utc)
                        event.error_message = None

                        published += 1
                        self._published_count += 1

                        logger.debug(
                            "Event published from outbox",
                            event_id=event.id,
                            event_type=event.event_type,
                        )

                    except Exception as e:
                        # Handle failure
                        event.retry_count += 1
                        event.error_message = str(e)
                        event.updated_at = datetime.now(timezone.utc)

                        if event.retry_count >= event.max_retries:
                            # Move to dead letter
                            event.status = OutboxEventStatus.DEAD_LETTER.value
                            logger.error(
                                "Event moved to dead letter queue",
                                event_id=event.id,
                                event_type=event.event_type,
                                retry_count=event.retry_count,
                                error=str(e),
                            )
                        else:
                            # Schedule retry with backoff
                            event.status = OutboxEventStatus.FAILED.value
                            backoff_seconds = (
                                self.retry_backoff_multiplier**event.retry_count
                            )
                            event.next_retry_at = datetime.now(
                                timezone.utc
                            ) + timedelta(seconds=backoff_seconds)

                            self._retry_count += 1

                            logger.warning(
                                "Event dispatch failed, will retry",
                                event_id=event.id,
                                event_type=event.event_type,
                                retry_count=event.retry_count,
                                next_retry_at=event.next_retry_at,
                                error=str(e),
                            )

                        failed += 1
                        self._failed_count += 1

                # Commit all changes
                await session.commit()

        except Exception as e:
            logger.error(
                "Failed to dispatch pending events",
                tenant_id=self.tenant_id,
                error=str(e),
            )

        return {
            "processed": processed,
            "published": published,
            "failed": failed,
        }

    async def get_pending_events(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Get pending events for this tenant.

        Args:
            limit: Maximum number of events to return
            offset: Offset for pagination

        Returns:
            List of event dictionaries
        """
        if not self.session_factory:
            return []

        try:
            async with self.session_factory() as session:
                stmt = (
                    select(OutboxEvent)
                    .where(
                        OutboxEvent.tenant_id == self.tenant_id,
                        OutboxEvent.status.in_(
                            [
                                OutboxEventStatus.PENDING.value,
                                OutboxEventStatus.PROCESSING.value,
                                OutboxEventStatus.FAILED.value,
                            ]
                        ),
                    )
                    .order_by(OutboxEvent.created_at)
                    .offset(offset)
                    .limit(limit)
                )

                result = await session.execute(stmt)
                events = result.scalars().all()

                return [event.to_dict() for event in events]

        except Exception as e:
            logger.error(
                "Failed to get pending events",
                tenant_id=self.tenant_id,
                error=str(e),
            )
            return []

    async def get_dead_letter_events(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Get dead letter events for this tenant.

        Args:
            limit: Maximum number of events to return
            offset: Offset for pagination

        Returns:
            List of event dictionaries
        """
        if not self.session_factory:
            return []

        try:
            async with self.session_factory() as session:
                stmt = (
                    select(OutboxEvent)
                    .where(
                        OutboxEvent.tenant_id == self.tenant_id,
                        OutboxEvent.status == OutboxEventStatus.DEAD_LETTER.value,
                    )
                    .order_by(OutboxEvent.updated_at.desc())
                    .offset(offset)
                    .limit(limit)
                )

                result = await session.execute(stmt)
                events = result.scalars().all()

                return [event.to_dict() for event in events]

        except Exception as e:
            logger.error(
                "Failed to get dead letter events",
                tenant_id=self.tenant_id,
                error=str(e),
            )
            return []

    async def retry_event(self, event_id: str) -> bool:
        """
        Retry a specific event.

        Args:
            event_id: Event ID to retry

        Returns:
            True if event was reset for retry, False otherwise
        """
        if not self.session_factory:
            return False

        try:
            async with self.session_factory() as session:
                stmt = select(OutboxEvent).where(
                    OutboxEvent.id == event_id,
                    OutboxEvent.tenant_id == self.tenant_id,
                )

                result = await session.execute(stmt)
                event = result.scalar_one_or_none()

                if not event:
                    return False

                # Reset for retry
                event.status = OutboxEventStatus.PENDING.value
                event.retry_count = 0
                event.next_retry_at = None
                event.error_message = None
                event.updated_at = datetime.now(timezone.utc)

                await session.commit()

                logger.info(
                    "Event reset for retry",
                    event_id=event_id,
                    event_type=event.event_type,
                )

                return True

        except Exception as e:
            logger.error(
                "Failed to retry event",
                event_id=event_id,
                error=str(e),
            )
            return False

    async def cleanup_expired_events(
        self,
        retention_days: int = 30,
    ) -> Dict[str, int]:
        """
        Clean up old published and dead letter events.

        Args:
            retention_days: Number of days to retain events

        Returns:
            Dictionary with cleanup statistics
        """
        if not self.session_factory:
            return {"cleaned_count": 0}

        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)

            async with self.session_factory() as session:
                # Delete old published events
                stmt = select(OutboxEvent).where(
                    OutboxEvent.tenant_id == self.tenant_id,
                    OutboxEvent.status.in_(
                        [
                            OutboxEventStatus.PUBLISHED.value,
                            OutboxEventStatus.DEAD_LETTER.value,
                        ]
                    ),
                    OutboxEvent.updated_at < cutoff_date,
                )

                result = await session.execute(stmt)
                events_to_delete = result.scalars().all()

                for event in events_to_delete:
                    await session.delete(event)

                await session.commit()

                cleaned_count = len(events_to_delete)

                logger.info(
                    "Cleaned up expired outbox events",
                    tenant_id=self.tenant_id,
                    cleaned_count=cleaned_count,
                    retention_days=retention_days,
                )

                return {"cleaned_count": cleaned_count}

        except Exception as e:
            logger.error(
                "Failed to cleanup expired events",
                tenant_id=self.tenant_id,
                error=str(e),
            )
            return {"cleaned_count": 0}

    async def _dispatch_loop(self) -> None:
        """Background dispatch loop."""
        while self._running:
            try:
                await self.dispatch_pending_events()
                await asyncio.sleep(self.dispatch_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    "Error in dispatch loop",
                    tenant_id=self.tenant_id,
                    error=str(e),
                )
                await asyncio.sleep(self.dispatch_interval)

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get SDK metrics.

        Returns:
            Dictionary of metrics
        """
        return {
            "tenant_id": self.tenant_id,
            "stored_count": self._stored_count,
            "published_count": self._published_count,
            "failed_count": self._failed_count,
            "retry_count": self._retry_count,
            "running": self._running,
        }
