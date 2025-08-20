"""
Events API endpoints for dotmac_core_events.

Provides REST API for:
- Event publishing
- Event subscription management
- Event history and replay
- Topic information
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from ..core.dependencies import get_event_bus, get_tenant_id
from ..sdks.event_bus import EventBusSDK, EventMetadata
from ..utils.validation import (
    SecureRequestModel,
    ValidationError,
    validate_consumer_group,
    validate_event_type,
    validate_pagination_params,
    validate_partition_key,
    validate_subscription_id,
)


class PublishEventRequest(SecureRequestModel):
    """Request model for event publishing."""

    event_type: str = Field(..., description="Event type identifier")
    data: Dict[str, Any] = Field(..., description="Event payload")
    partition_key: Optional[str] = Field(None, description="Partition key for routing")
    event_metadata: Optional[Dict[str, Any]] = Field(None, description="Event metadata")
    idempotency_key: Optional[str] = Field(None, description="Idempotency key")

    @validator("event_type")
    def validate_event_type_field(cls, v):
        validate_event_type(v)
        return v

    @validator("partition_key")
    def validate_partition_key_field(cls, v):
        if v is not None:
            validate_partition_key(v)
        return v


class PublishEventResponse(BaseModel):
    """Response model for event publishing."""

    event_id: str = Field(..., description="Generated event ID")
    partition: int = Field(..., description="Assigned partition")
    offset: int = Field(..., description="Message offset")
    timestamp: datetime = Field(..., description="Event timestamp")


class SubscribeRequest(SecureRequestModel):
    """Request model for event subscription."""

    event_types: List[str] = Field(..., description="Event types to subscribe to")
    consumer_group: str = Field(..., description="Consumer group ID")
    auto_commit: bool = Field(True, description="Auto-commit offsets")
    max_poll_records: int = Field(100, ge=1, le=1000, description="Max records per poll")

    @validator("event_types")
    def validate_event_types_field(cls, v):
        for event_type in v:
            validate_event_type(event_type)
        return v

    @validator("consumer_group")
    def validate_consumer_group_field(cls, v):
        validate_consumer_group(v)
        return v


class SubscribeResponse(BaseModel):
    """Response model for event subscription."""

    subscription_id: str = Field(..., description="Subscription identifier")
    consumer_group: str = Field(..., description="Consumer group ID")
    event_types: List[str] = Field(..., description="Subscribed event types")


class UnsubscribeRequest(BaseModel):
    """Request model for unsubscribing."""

    subscription_id: str = Field(..., description="Subscription to cancel")


class EventHistoryResponse(BaseModel):
    """Response model for event history."""

    events: List[Dict[str, Any]] = Field(..., description="List of events")
    total: int = Field(..., description="Total number of events")
    has_more: bool = Field(..., description="More events available")


class ReplayRequest(BaseModel):
    """Request model for event replay."""

    event_type: str = Field(..., description="Event type to replay")
    start_time: datetime = Field(..., description="Replay start time")
    end_time: datetime = Field(..., description="Replay end time")
    target_topic: Optional[str] = Field(None, description="Target topic for replayed events")
    speed_multiplier: float = Field(1.0, ge=0.1, le=100, description="Replay speed multiplier")


class ReplayResponse(BaseModel):
    """Response model for event replay."""

    replay_id: str = Field(..., description="Replay job identifier")
    status: str = Field(..., description="Replay status")
    estimated_events: int = Field(..., description="Estimated number of events")


class TopicInfoResponse(BaseModel):
    """Response model for topic information."""

    topic: str = Field(..., description="Topic name")
    event_type: str = Field(..., description="Event type")
    partitions: int = Field(..., description="Number of partitions")
    replication_factor: Optional[int] = Field(None, description="Replication factor")
    message_count: Optional[int] = Field(None, description="Total message count")
    size_bytes: Optional[int] = Field(None, description="Topic size in bytes")


class EventsAPI:
    """Events API endpoints."""

    def __init__(self):
        self.router = APIRouter(prefix="/events", tags=["events"])
        self._setup_routes()

    def _setup_routes(self):  # noqa: PLR0915, C901
        """Set up API routes."""

        @self.router.post(
            "/publish",
            response_model=PublishEventResponse,
            status_code=status.HTTP_201_CREATED,
            summary="Publish event",
            description="Publish a new event to the event stream"
        )
        async def publish_event(
            request: PublishEventRequest,
            event_bus: EventBusSDK = Depends(get_event_bus),
            tenant_id: str = Depends(get_tenant_id)
        ) -> PublishEventResponse:
            """Publish an event."""
            try:
                # Convert metadata dict to EventMetadata if provided
                event_metadata = None
                if request.event_metadata:
                    event_metadata = EventMetadata.from_dict(request.event_metadata)

                result = await event_bus.publish(
                    event_type=request.event_type,
                    data=request.data,
                    partition_key=request.partition_key,
                    event_metadata=event_metadata,
                    idempotency_key=request.idempotency_key,
                )

                return PublishEventResponse(
                    event_id=result.event_id,
                    partition=result.partition,
                    offset=result.offset,
                    timestamp=result.timestamp,
                )

            except ValidationError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Validation error: {str(e)}"
                )
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to publish event"
                )

        @self.router.post(
            "/subscribe",
            response_model=SubscribeResponse,
            status_code=status.HTTP_201_CREATED,
            summary="Subscribe to events",
            description="Subscribe to events of specific types"
        )
        async def subscribe_to_events(
            request: SubscribeRequest,
            event_bus: EventBusSDK = Depends(get_event_bus),
            tenant_id: str = Depends(get_tenant_id)
        ) -> SubscribeResponse:
            """Subscribe to events."""
            try:
                # For HTTP API, we return subscription info but don't start streaming
                # Actual streaming would be handled via WebSocket or SSE endpoints
                subscription_id = f"{tenant_id}:{request.consumer_group}:{':'.join(request.event_types)}"

                return SubscribeResponse(
                    subscription_id=subscription_id,
                    consumer_group=request.consumer_group,
                    event_types=request.event_types,
                )

            except ValidationError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Validation error: {str(e)}"
                )
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create subscription"
                )

        @self.router.post(
            "/unsubscribe",
            status_code=status.HTTP_204_NO_CONTENT,
            summary="Unsubscribe from events",
            description="Cancel event subscription"
        )
        async def unsubscribe_from_events(
            request: UnsubscribeRequest,
            event_bus: EventBusSDK = Depends(get_event_bus),
            tenant_id: str = Depends(get_tenant_id)
        ):
            """Unsubscribe from events."""
            try:
                # Extract consumer group from subscription ID
                try:
                    validate_subscription_id(request.subscription_id, tenant_id)
                    parts = request.subscription_id.split(":")
                except ValidationError as e:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid subscription ID: {str(e)}"
                    )

                consumer_group = parts[1]
                await event_bus.unsubscribe(consumer_group)

            except HTTPException:
                raise
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to unsubscribe"
                )

        @self.router.get(
            "/history",
            response_model=EventHistoryResponse,
            summary="Get event history",
            description="Retrieve historical events"
        )
        async def get_event_history(
            event_type: str = Query(..., description="Event type to retrieve"),
            limit: int = Query(100, ge=1, le=1000, description="Maximum number of events"),
            offset: int = Query(0, ge=0, description="Offset for pagination"),
            start_time: Optional[datetime] = Query(None, description="Start time filter"),
            end_time: Optional[datetime] = Query(None, description="End time filter"),
            event_bus: EventBusSDK = Depends(get_event_bus),
            tenant_id: str = Depends(get_tenant_id)
        ) -> EventHistoryResponse:
            """Get event history."""
            try:
                # Validate inputs
                validate_event_type(event_type)
                validate_pagination_params(limit, offset)

                # This is a placeholder implementation
                # In a real implementation, you would query the event store
                return EventHistoryResponse(
                    events=[],
                    total=0,
                    has_more=False,
                )

            except ValidationError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Validation error: {str(e)}"
                )
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to retrieve event history"
                )

        @self.router.post(
            "/replay",
            response_model=ReplayResponse,
            status_code=status.HTTP_202_ACCEPTED,
            summary="Replay events",
            description="Replay historical events"
        )
        async def replay_events(
            request: ReplayRequest,
            event_bus: EventBusSDK = Depends(get_event_bus),
            tenant_id: str = Depends(get_tenant_id)
        ) -> ReplayResponse:
            """Replay events."""
            try:
                # This is a placeholder implementation
                # In a real implementation, you would start a replay job
                import uuid
                replay_id = str(uuid.uuid4())

                return ReplayResponse(
                    replay_id=replay_id,
                    status="started",
                    estimated_events=0,
                )

            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to start replay"
                )

        @self.router.get(
            "/topics/{event_type}/info",
            response_model=TopicInfoResponse,
            summary="Get topic information",
            description="Get information about a topic"
        )
        async def get_topic_info(
            event_type: str,
            event_bus: EventBusSDK = Depends(get_event_bus),
            tenant_id: str = Depends(get_tenant_id)
        ) -> TopicInfoResponse:
            """Get topic information."""
            try:
                info = await event_bus.get_topic_info(event_type)

                return TopicInfoResponse(
                    topic=info.get("topic", f"tenant-{tenant_id}.{event_type}"),
                    event_type=event_type,
                    partitions=info.get("partitions", 0),
                    replication_factor=info.get("replication_factor"),
                    message_count=info.get("message_count"),
                    size_bytes=info.get("size_bytes"),
                )

            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to get topic information"
                )
