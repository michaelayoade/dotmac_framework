"""
Outbox SDK - Simplified transactional outbox API.

Provides a high-level interface for the transactional outbox pattern
with automatic background processing and simplified usage patterns.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog

from ..core.event_bus import EventBus
from ..core.models import EventBusError, EventMetadata, EventRecord
from ..core.outbox import OutboxEvent, OutboxEventStatus, OutboxManager

logger = structlog.get_logger(__name__)


class OutboxSDK:
    """
    High-level Outbox SDK.

    Provides simplified transactional outbox operations with:
    - Automatic event processing and publishing
    - Background worker for reliable event delivery
    - Simple APIs for common patterns
    - Built-in retry logic and error handling
    """

    def __init__(
        self,
        outbox_manager: OutboxManager,
        event_bus: EventBus,
        *,
        process_interval_seconds: int = 5,
        batch_size: int = 50,
        auto_start: bool = True,
    ):
        """
        Initialize Outbox SDK.

        Args:
            outbox_manager: Outbox manager instance
            event_bus: Event bus for publishing events
            process_interval_seconds: How often to process pending events
            batch_size: Number of events to process per batch
            auto_start: Whether to automatically start background processing
        """
        self.outbox_manager = outbox_manager
        self.event_bus = event_bus
        self.process_interval_seconds = process_interval_seconds
        self.batch_size = batch_size

        self._processing_task: Optional[asyncio.Task] = None
        self._running = False

        if auto_start:
            asyncio.create_task(self.start_processing())

        logger.info(
            "Outbox SDK initialized",
            process_interval=process_interval_seconds,
            batch_size=batch_size,
        )

    async def start_processing(self) -> None:
        """Start background event processing."""
        try:
            if self._running:
                logger.warning("Outbox processing already running")
                return

            self._running = True
            self._processing_task = asyncio.create_task(self._processing_loop())

            logger.info("Outbox processing started")

        except Exception as e:
            logger.error("Failed to start outbox processing", error=str(e))
            raise EventBusError(f"Failed to start outbox processing: {e}") from e

    async def stop_processing(self) -> None:
        """Stop background event processing."""
        try:
            self._running = False

            if self._processing_task:
                self._processing_task.cancel()
                try:
                    await self._processing_task
                except asyncio.CancelledError:
                    pass

            logger.info("Outbox processing stopped")

        except Exception as e:
            logger.error("Error stopping outbox processing", error=str(e))

    async def store_event(
        self,
        session,  # SQLAlchemy async session
        event_type: str,
        data: Dict[str, Any],
        *,
        tenant_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        source: Optional[str] = None,
        topic: Optional[str] = None,
        scheduled_at: Optional[datetime] = None,
    ) -> str:
        """
        Store an event in the outbox within a transaction.

        Args:
            session: Database session (within transaction)
            event_type: Type of event
            data: Event payload
            tenant_id: Tenant ID
            correlation_id: Correlation ID for tracing
            user_id: User who triggered the event
            source: Source service
            topic: Target topic
            scheduled_at: Schedule for future publishing

        Returns:
            Outbox event ID
        """
        try:
            # Create metadata
            metadata = EventMetadata(
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                user_id=user_id,
                source=source,
            )

            # Create event record
            event = EventRecord(
                event_type=event_type, data=data, metadata=metadata, topic=topic
            )

            # Store in outbox
            outbox_id = await self.outbox_manager.store_event(
                session=session,
                event=event,
                tenant_id=tenant_id,
                scheduled_at=scheduled_at,
            )

            logger.debug(
                "Event stored in outbox via SDK",
                outbox_id=outbox_id,
                event_type=event_type,
                event_id=event.event_id,
            )

            return outbox_id

        except Exception as e:
            logger.error(
                "Failed to store event in outbox via SDK",
                event_type=event_type,
                error=str(e),
            )
            raise EventBusError(f"Failed to store event in outbox: {e}") from e

    async def store_events_batch(
        self,
        session,  # SQLAlchemy async session
        events: List[Dict[str, Any]],
        *,
        tenant_id: Optional[str] = None,
    ) -> List[str]:
        """
        Store multiple events in the outbox within a transaction.

        Args:
            session: Database session (within transaction)
            events: List of event dictionaries with 'event_type' and 'data'
            tenant_id: Tenant ID for all events

        Returns:
            List of outbox event IDs
        """
        try:
            # Convert to EventRecord objects
            event_records = []
            for event_dict in events:
                metadata = EventMetadata(tenant_id=tenant_id)

                event_record = EventRecord(
                    event_type=event_dict["event_type"],
                    data=event_dict["data"],
                    metadata=metadata,
                    topic=event_dict.get("topic"),
                )
                event_records.append(event_record)

            # Store batch in outbox
            outbox_ids = await self.outbox_manager.store_events_batch(
                session=session, events=event_records, tenant_id=tenant_id
            )

            logger.debug(
                "Event batch stored in outbox via SDK",
                batch_size=len(events),
                tenant_id=tenant_id,
            )

            return outbox_ids

        except Exception as e:
            logger.error(
                "Failed to store event batch in outbox via SDK",
                batch_size=len(events),
                error=str(e),
            )
            raise EventBusError(f"Failed to store event batch in outbox: {e}") from e

    async def process_pending_events(
        self, limit: Optional[int] = None, tenant_id: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Manually process pending events.

        Args:
            limit: Maximum number of events to process
            tenant_id: Filter by tenant ID

        Returns:
            Dictionary with processing statistics
        """
        try:
            # Get pending events
            pending_events = await self.outbox_manager.get_pending_events(
                limit=limit or self.batch_size, tenant_id=tenant_id
            )

            if not pending_events:
                return {"processed": 0, "failed": 0, "skipped": 0}

            # Mark as processing
            event_ids = [event.id for event in pending_events]
            await self.outbox_manager.mark_processing(event_ids)

            processed = 0
            failed = 0

            # Process each event
            for outbox_event in pending_events:
                try:
                    # Convert to event record
                    event_record = outbox_event.to_event_record()

                    # Publish via event bus
                    await self.event_bus.publish(
                        event_type=event_record.event_type,
                        data=event_record.data,
                        metadata=event_record.metadata,
                        topic=event_record.topic,
                    )

                    # Mark as published
                    await self.outbox_manager.mark_published([outbox_event.id])
                    processed += 1

                    logger.debug(
                        "Outbox event processed successfully",
                        outbox_id=outbox_event.id,
                        event_id=event_record.event_id,
                    )

                except Exception as e:
                    # Mark as failed
                    await self.outbox_manager.mark_failed(
                        outbox_event.id, str(e), increment_retry=True
                    )
                    failed += 1

                    logger.error(
                        "Failed to process outbox event",
                        outbox_id=outbox_event.id,
                        event_id=outbox_event.event_id,
                        error=str(e),
                    )

            stats = {"processed": processed, "failed": failed, "skipped": 0}

            logger.info(
                "Processed pending outbox events",
                **stats,
                total_events=len(pending_events),
            )

            return stats

        except Exception as e:
            logger.error(
                "Failed to process pending outbox events",
                limit=limit,
                tenant_id=tenant_id,
                error=str(e),
            )
            raise EventBusError(f"Failed to process pending events: {e}") from e

    async def get_stats(self) -> Dict[str, Any]:
        """Get outbox statistics."""
        try:
            return await self.outbox_manager.get_stats()
        except Exception as e:
            logger.error("Failed to get outbox stats", error=str(e))
            return {"error": str(e)}

    async def cleanup_old_events(
        self, older_than_days: int = 7, keep_failed: bool = True
    ) -> int:
        """
        Clean up old processed events.

        Args:
            older_than_days: Delete events older than this many days
            keep_failed: Whether to keep failed/dead letter events

        Returns:
            Number of events deleted
        """
        try:
            deleted_count = await self.outbox_manager.cleanup_old_events(
                older_than_days=older_than_days, keep_failed=keep_failed
            )

            logger.info(
                "Cleaned up old outbox events",
                deleted_count=deleted_count,
                older_than_days=older_than_days,
            )

            return deleted_count

        except Exception as e:
            logger.error(
                "Failed to cleanup old outbox events",
                older_than_days=older_than_days,
                error=str(e),
            )
            raise EventBusError(f"Failed to cleanup old events: {e}") from e

    async def reset_stuck_events(self, timeout_minutes: int = 30) -> int:
        """
        Reset events stuck in processing status.

        Args:
            timeout_minutes: Minutes after which processing events are considered stuck

        Returns:
            Number of events reset
        """
        try:
            reset_count = await self.outbox_manager.reset_stuck_events(timeout_minutes)

            if reset_count > 0:
                logger.info(
                    "Reset stuck outbox events",
                    reset_count=reset_count,
                    timeout_minutes=timeout_minutes,
                )

            return reset_count

        except Exception as e:
            logger.error(
                "Failed to reset stuck outbox events",
                timeout_minutes=timeout_minutes,
                error=str(e),
            )
            raise EventBusError(f"Failed to reset stuck events: {e}") from e

    async def _processing_loop(self) -> None:
        """Background processing loop."""
        while self._running:
            try:
                # Reset stuck events periodically
                await self.reset_stuck_events()

                # Process pending events
                stats = await self.process_pending_events()

                if stats["processed"] > 0:
                    logger.debug("Outbox processing iteration completed", **stats)

                # Sleep until next iteration
                await asyncio.sleep(self.process_interval_seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in outbox processing loop", error=str(e))

                # Back off on error to prevent tight error loops
                await asyncio.sleep(min(self.process_interval_seconds * 2, 60))

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start_processing()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop_processing()
