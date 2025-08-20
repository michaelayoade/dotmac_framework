"""
Event service for analytics data collection and processing.
"""

import logging
from datetime import datetime, timedelta
from dotmac_analytics.core.datetime_utils import utc_now, utc_now_iso
from typing import Any, Dict, List, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from ..core.exceptions import AnalyticsError, ValidationError
from ..models.enums import EventType, TimeGranularity
from ..models.events import AnalyticsEvent, EventAggregate, EventBatch, EventSchema

logger = logging.getLogger(__name__)


class EventService:
    """Service for managing analytics events."""

    def __init__(self, db: Session):
        self.db = db

    async def track_event(  # noqa: PLR0913
        self,
        tenant_id: str,
        event_type: EventType,
        event_name: str,
        properties: Dict[str, Any] = None,
        context: Dict[str, Any] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        source: Optional[str] = None
    ) -> AnalyticsEvent:
        """Track a single analytics event."""
        try:
            # Validate event schema if exists
            await self._validate_event_schema(tenant_id, event_type, event_name, properties)

            event = AnalyticsEvent(
                tenant_id=tenant_id,
                event_type=event_type.value,
                event_name=event_name,
                user_id=user_id,
                session_id=session_id,
                customer_id=customer_id,
                properties=properties or {},
                context=context or {},
                source=source,
                timestamp=utc_now()
            )

            self.db.add(event)
            self.db.commit()
            self.db.refresh(event)

            # Trigger real-time processing
            await self._process_event_real_time(event)

            logger.info(f"Tracked event: {event_name} for tenant {tenant_id}")
            return event

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to track event: {e}")
            raise AnalyticsError(f"Event tracking failed: {str(e)}")

    async def track_events_batch(
        self,
        tenant_id: str,
        events: List[Dict[str, Any]],
        source: Optional[str] = None
    ) -> EventBatch:
        """Track multiple events in a batch for efficiency."""
        try:
            batch = EventBatch(
                tenant_id=tenant_id,
                batch_size=len(events),
                source=source,
                status="processing"
            )

            self.db.add(batch)
            self.db.flush()

            success_count = 0
            error_count = 0

            for event_data in events:
                try:
                    event = AnalyticsEvent(
                        tenant_id=tenant_id,
                        event_type=event_data.get("event_type"),
                        event_name=event_data.get("event_name"),
                        user_id=event_data.get("user_id"),
                        session_id=event_data.get("session_id"),
                        customer_id=event_data.get("customer_id"),
                        properties=event_data.get("properties", {}),
                        context=event_data.get("context", {}),
                        source=source,
                        timestamp=datetime.fromisoformat(event_data.get("timestamp", utc_now().isoformat()))
                    )

                    self.db.add(event)
                    success_count += 1

                except Exception as e:
                    logger.warning(f"Failed to process event in batch: {e}")
                    error_count += 1

            batch.success_count = success_count
            batch.error_count = error_count
            batch.status = "completed" if error_count == 0 else "partial_success"
            batch.processed_at = utc_now()

            self.db.commit()

            logger.info(f"Processed batch: {success_count} success, {error_count} errors")
            return batch

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to process event batch: {e}")
            raise AnalyticsError(f"Batch processing failed: {str(e)}")

    async def get_events(  # noqa: PLR0913
        self,
        tenant_id: str,
        event_type: Optional[EventType] = None,
        event_name: Optional[str] = None,
        user_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AnalyticsEvent]:
        """Get events with filtering options."""
        try:
            query = self.db.query(AnalyticsEvent).filter(
                AnalyticsEvent.tenant_id == tenant_id
            )

            if event_type:
                query = query.filter(AnalyticsEvent.event_type == event_type.value)

            if event_name:
                query = query.filter(AnalyticsEvent.event_name == event_name)

            if user_id:
                query = query.filter(AnalyticsEvent.user_id == user_id)

            if customer_id:
                query = query.filter(AnalyticsEvent.customer_id == customer_id)

            if start_time:
                query = query.filter(AnalyticsEvent.timestamp >= start_time)

            if end_time:
                query = query.filter(AnalyticsEvent.timestamp <= end_time)

            return query.order_by(AnalyticsEvent.timestamp.desc()).offset(offset).limit(limit).all()

        except Exception as e:
            logger.error(f"Failed to get events: {e}")
            raise AnalyticsError(f"Event retrieval failed: {str(e)}")

    async def aggregate_events(
        self,
        tenant_id: str,
        granularity: TimeGranularity,
        start_time: datetime,
        end_time: datetime,
        event_type: Optional[EventType] = None,
        event_name: Optional[str] = None,
        dimensions: Optional[List[str]] = None
    ) -> List[EventAggregate]:
        """Aggregate events by time and dimensions."""
        try:
            # Check if aggregates already exist
            existing_aggregates = self.db.query(EventAggregate).filter(
                and_(
                    EventAggregate.tenant_id == tenant_id,
                    EventAggregate.granularity == granularity.value,
                    EventAggregate.time_bucket >= start_time,
                    EventAggregate.time_bucket <= end_time
                )
            ).all()

            if existing_aggregates:
                return existing_aggregates

            # Generate aggregates
            time_buckets = self._generate_time_buckets(start_time, end_time, granularity)
            aggregates = []

            for time_bucket in time_buckets:
                bucket_end = self._get_bucket_end(time_bucket, granularity)

                # Query events in this time bucket
                query = self.db.query(AnalyticsEvent).filter(
                    and_(
                        AnalyticsEvent.tenant_id == tenant_id,
                        AnalyticsEvent.timestamp >= time_bucket,
                        AnalyticsEvent.timestamp < bucket_end
                    )
                )

                if event_type:
                    query = query.filter(AnalyticsEvent.event_type == event_type.value)

                if event_name:
                    query = query.filter(AnalyticsEvent.event_name == event_name)

                events = query.all()

                if events:
                    aggregate = EventAggregate(
                        tenant_id=tenant_id,
                        event_type=event_type.value if event_type else "all",
                        event_name=event_name or "all",
                        time_bucket=time_bucket,
                        granularity=granularity.value,
                        event_count=len(events),
                        unique_users=len(set(e.user_id for e in events if e.user_id)),
                        unique_sessions=len(set(e.session_id for e in events if e.session_id)),
                        unique_customers=len(set(e.customer_id for e in events if e.customer_id))
                    )

                    self.db.add(aggregate)
                    aggregates.append(aggregate)

            self.db.commit()
            return aggregates

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to aggregate events: {e}")
            raise AnalyticsError(f"Event aggregation failed: {str(e)}")

    async def create_event_schema(
        self,
        tenant_id: str,
        event_type: EventType,
        event_name: str,
        schema_definition: Dict[str, Any],
        version: str = "1.0"
    ) -> EventSchema:
        """Create event schema for validation."""
        try:
            schema = EventSchema(
                tenant_id=tenant_id,
                event_type=event_type.value,
                event_name=event_name,
                version=version,
                schema_definition=schema_definition,
                required_properties=schema_definition.get("required", []),
                optional_properties=schema_definition.get("optional", [])
            )

            self.db.add(schema)
            self.db.commit()
            self.db.refresh(schema)

            logger.info(f"Created event schema: {event_name} v{version}")
            return schema

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create event schema: {e}")
            raise AnalyticsError(f"Schema creation failed: {str(e)}")

    async def get_event_funnel(
        self,
        tenant_id: str,
        funnel_steps: List[str],
        start_time: datetime,
        end_time: datetime,
        user_id_field: str = "user_id"
    ) -> Dict[str, Any]:
        """Analyze event funnel conversion rates."""
        try:
            funnel_data = {}

            for i, step in enumerate(funnel_steps):
                # Get users who completed this step
                users_query = self.db.query(AnalyticsEvent.user_id).filter(
                    and_(
                        AnalyticsEvent.tenant_id == tenant_id,
                        AnalyticsEvent.event_name == step,
                        AnalyticsEvent.timestamp >= start_time,
                        AnalyticsEvent.timestamp <= end_time,
                        AnalyticsEvent.user_id.isnot(None)
                    )
                ).distinct()

                if i > 0:
                    # Filter users who completed previous steps
                    previous_users = funnel_data[funnel_steps[i-1]]["users"]
                    users_query = users_query.filter(AnalyticsEvent.user_id.in_(previous_users))

                users = [row[0] for row in users_query.all()]

                funnel_data[step] = {
                    "users": users,
                    "count": len(users),
                    "conversion_rate": len(users) / funnel_data[funnel_steps[0]]["count"] if i > 0 and funnel_data[funnel_steps[0]]["count"] > 0 else 1.0
                }

            return funnel_data

        except Exception as e:
            logger.error(f"Failed to analyze event funnel: {e}")
            raise AnalyticsError(f"Funnel analysis failed: {str(e)}")

    async def _validate_event_schema(
        self,
        tenant_id: str,
        event_type: EventType,
        event_name: str,
        properties: Dict[str, Any]
    ):
        """Validate event against schema if exists."""
        schema = self.db.query(EventSchema).filter(
            and_(
                EventSchema.tenant_id == tenant_id,
                EventSchema.event_type == event_type.value,
                EventSchema.event_name == event_name,
                EventSchema.is_active == True
            )
        ).first()

        if schema and properties:
            required_props = schema.required_properties or []
            for prop in required_props:
                if prop not in properties:
                    raise ValidationError(f"Required property '{prop}' missing from event")

    async def _process_event_real_time(self, event: AnalyticsEvent):
        """Process event for real-time analytics."""
        # This would trigger real-time processing pipelines
        # For now, just log the event
        logger.debug(f"Real-time processing event: {event.event_name}")

    def _generate_time_buckets(
        self,
        start_time: datetime,
        end_time: datetime,
        granularity: TimeGranularity
    ) -> List[datetime]:
        """Generate time buckets for aggregation."""
        buckets = []
        current = start_time

        if granularity == TimeGranularity.HOUR:
            delta = timedelta(hours=1)
        elif granularity == TimeGranularity.DAY:
            delta = timedelta(days=1)
        elif granularity == TimeGranularity.WEEK:
            delta = timedelta(weeks=1)
        elif granularity == TimeGranularity.MONTH:
            delta = timedelta(days=30)  # Approximate
        else:
            delta = timedelta(minutes=1)

        while current < end_time:
            buckets.append(current)
            current += delta

        return buckets

    def _get_bucket_end(self, bucket_start: datetime, granularity: TimeGranularity) -> datetime:
        """Get the end time for a time bucket."""
        if granularity == TimeGranularity.HOUR:
            return bucket_start + timedelta(hours=1)
        elif granularity == TimeGranularity.DAY:
            return bucket_start + timedelta(days=1)
        elif granularity == TimeGranularity.WEEK:
            return bucket_start + timedelta(weeks=1)
        elif granularity == TimeGranularity.MONTH:
            return bucket_start + timedelta(days=30)
        else:
            return bucket_start + timedelta(minutes=1)
