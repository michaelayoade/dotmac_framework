"""
Events SDK for analytics data collection and tracking.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ..core.exceptions import AnalyticsError
from ..models.enums import EventType, TimeGranularity
from ..services.events import EventService

logger = logging.getLogger(__name__)


class EventsSDK:
    """SDK for analytics events operations."""

    def __init__(self, tenant_id: str, db: Session):
        """  Init   operation."""
        self.tenant_id = tenant_id
        self.db = db
        self.service = EventService(db)

    async def track(
        self,
        event_type: EventType,
        event_name: str,
        properties: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        source: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Track a single analytics event.

        Args:
            event_type: Type of event (page_view, click, etc.)
            event_name: Name of the event
            properties: Event properties/attributes
            context: Additional context information
            user_id: User identifier
            session_id: Session identifier
            customer_id: Customer identifier
            source: Event source

        Returns:
            Dict with event tracking result
        """
        try:
            event = await self.service.track_event(
                tenant_id=self.tenant_id,
                event_type=event_type,
                event_name=event_name,
                properties=properties,
                context=context,
                user_id=user_id,
                session_id=session_id,
                customer_id=customer_id,
                source=source,
            )

            return {
                "event_id": str(event.id),
                "status": "tracked",
                "timestamp": event.timestamp,
            }

        except Exception as e:
            logger.error(f"Failed to track event: {e}")
            raise AnalyticsError(f"Event tracking failed: {str(e)}")

    async def track_batch(
        self, events: List[Dict[str, Any]], source: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Track multiple events in a batch.

        Args:
            events: List of event dictionaries
            source: Batch source identifier

        Returns:
            Dict with batch tracking result
        """
        try:
            batch = await self.service.track_events_batch(
                tenant_id=self.tenant_id, events=events, source=source
            )

            return {
                "batch_id": str(batch.id),
                "status": batch.status,
                "success_count": batch.success_count,
                "error_count": batch.error_count,
                "processed_at": batch.processed_at,
            }

        except Exception as e:
            logger.error(f"Failed to track event batch: {e}")
            raise AnalyticsError(f"Batch tracking failed: {str(e)}")

    async def get_events(
        self,
        event_type: Optional[EventType] = None,
        event_name: Optional[str] = None,
        user_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Get events with filtering options.

        Args:
            event_type: Filter by event type
            event_name: Filter by event name
            user_id: Filter by user ID
            customer_id: Filter by customer ID
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum number of results
            offset: Result offset for pagination

        Returns:
            List of event dictionaries
        """
        try:
            events = await self.service.get_events(
                tenant_id=self.tenant_id,
                event_type=event_type,
                event_name=event_name,
                user_id=user_id,
                customer_id=customer_id,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
                offset=offset,
            )

            return [
                {
                    "id": str(event.id),
                    "event_type": event.event_type,
                    "event_name": event.event_name,
                    "user_id": event.user_id,
                    "session_id": event.session_id,
                    "customer_id": event.customer_id,
                    "properties": event.properties,
                    "context": event.context,
                    "timestamp": event.timestamp,
                    "source": event.source,
                }
                for event in events
            ]

        except Exception as e:
            logger.error(f"Failed to get events: {e}")
            raise AnalyticsError(f"Event retrieval failed: {str(e)}")

    async def aggregate(
        self,
        granularity: TimeGranularity,
        start_time: datetime,
        end_time: datetime,
        event_type: Optional[EventType] = None,
        event_name: Optional[str] = None,
        dimensions: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Aggregate events by time and dimensions.

        Args:
            granularity: Time granularity for aggregation
            start_time: Aggregation start time
            end_time: Aggregation end time
            event_type: Filter by event type
            event_name: Filter by event name
            dimensions: Dimensions to group by

        Returns:
            List of aggregated event data
        """
        try:
            aggregates = await self.service.aggregate_events(
                tenant_id=self.tenant_id,
                granularity=granularity,
                start_time=start_time,
                end_time=end_time,
                event_type=event_type,
                event_name=event_name,
                dimensions=dimensions,
            )

            return [
                {
                    "time_bucket": aggregate.time_bucket,
                    "granularity": aggregate.granularity,
                    "event_count": aggregate.event_count,
                    "unique_users": aggregate.unique_users,
                    "unique_sessions": aggregate.unique_sessions,
                    "unique_customers": aggregate.unique_customers,
                    "dimensions": aggregate.dimensions,
                }
                for aggregate in aggregates
            ]

        except Exception as e:
            logger.error(f"Failed to aggregate events: {e}")
            raise AnalyticsError(f"Event aggregation failed: {str(e)}")

    async def funnel_analysis(
        self,
        funnel_steps: List[str],
        start_time: datetime,
        end_time: datetime,
        user_id_field: str = "user_id",
    ) -> Dict[str, Any]:
        """
        Analyze event funnel conversion rates.

        Args:
            funnel_steps: List of event names representing funnel steps
            start_time: Analysis start time
            end_time: Analysis end time
            user_id_field: Field to use for user identification

        Returns:
            Dict with funnel analysis results
        """
        try:
            funnel_data = await self.service.get_event_funnel(
                tenant_id=self.tenant_id,
                funnel_steps=funnel_steps,
                start_time=start_time,
                end_time=end_time,
                user_id_field=user_id_field,
            )

            return {
                "funnel_steps": funnel_steps,
                "analysis_period": {"start_time": start_time, "end_time": end_time},
                "funnel_data": funnel_data,
            }

        except Exception as e:
            logger.error(f"Failed to analyze funnel: {e}")
            raise AnalyticsError(f"Funnel analysis failed: {str(e)}")

    async def create_schema(
        self,
        event_type: EventType,
        event_name: str,
        schema_definition: Dict[str, Any],
        version: str = "1.0",
    ) -> Dict[str, Any]:
        """
        Create event schema for validation.

        Args:
            event_type: Type of event
            event_name: Name of the event
            schema_definition: JSON schema definition
            version: Schema version

        Returns:
            Dict with schema creation result
        """
        try:
            schema = await self.service.create_event_schema(
                tenant_id=self.tenant_id,
                event_type=event_type,
                event_name=event_name,
                schema_definition=schema_definition,
                version=version,
            )

            return {
                "schema_id": str(schema.id),
                "event_type": schema.event_type,
                "event_name": schema.event_name,
                "version": schema.version,
                "created_at": schema.created_at,
            }

        except Exception as e:
            logger.error(f"Failed to create event schema: {e}")
            raise AnalyticsError(f"Schema creation failed: {str(e)}")

    # Convenience methods for common event types
    async def track_page_view(
        self,
        page_url: str,
        page_title: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Track a page view event."""
        event_properties = {
            "page_url": page_url,
            "page_title": page_title,
            **(properties or {}),
        }

        return await self.track(
            event_type=EventType.PAGE_VIEW,
            event_name="page_view",
            properties=event_properties,
            user_id=user_id,
            session_id=session_id,
        )

    async def track_click(
        self,
        element_id: str,
        element_text: Optional[str] = None,
        page_url: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Track a click event."""
        event_properties = {
            "element_id": element_id,
            "element_text": element_text,
            "page_url": page_url,
            **(properties or {}),
        }

        return await self.track(
            event_type=EventType.CLICK,
            event_name="click",
            properties=event_properties,
            user_id=user_id,
            session_id=session_id,
        )

    async def track_conversion(
        self,
        conversion_type: str,
        conversion_value: Optional[float] = None,
        user_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Track a conversion event."""
        event_properties = {
            "conversion_type": conversion_type,
            "conversion_value": conversion_value,
            **(properties or {}),
        }

        return await self.track(
            event_type=EventType.CONVERSION,
            event_name="conversion",
            properties=event_properties,
            user_id=user_id,
            customer_id=customer_id,
        )
