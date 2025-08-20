"""
REST API for DotMac Core Events management.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import structlog
from fastapi import Depends, FastAPI, HTTPException, Path, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, validator

from ..models.envelope import EventEnvelope
from ..persistence.outbox import OutboxStatus, OutboxStore
from ..sdks.event_bus import EventBusSDK
from ..security.tenant_auth import TenantAuthorizer

logger = structlog.get_logger(__name__)

# Security
security = HTTPBearer()

# Request/Response Models
class PublishEventRequest(BaseModel):
    """Request to publish an event."""

    event_type: str = Field(..., description="Event type identifier")
    data: Dict[str, Any] = Field(..., description="Event payload data")
    partition_key: Optional[str] = Field(None, description="Partition key for ordering")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracing")
    causation_id: Optional[str] = Field(None, description="Causation ID for event sourcing")
    source: Optional[str] = Field(None, description="Event source identifier")
    idempotency_key: Optional[str] = Field(None, description="Idempotency key")

    @validator("event_type")
    def validate_event_type(cls, v):
        if not v or not v.strip():
            raise ValueError("Event type cannot be empty")
        return v.strip()


class PublishEventResponse(BaseModel):
    """Response from publishing an event."""

    event_id: str = Field(..., description="Generated event ID")
    status: str = Field(..., description="Publish status")
    outbox_entry_id: Optional[str] = Field(None, description="Outbox entry ID if using outbox pattern")
    topic: str = Field(..., description="Target topic")


class EventEnvelopeResponse(BaseModel):
    """Event envelope response."""

    id: str
    type: str
    schema_version: str
    tenant_id: str
    occurred_at: datetime
    trace_id: str
    data: Dict[str, Any]
    source: Optional[str] = None
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    version: Optional[int] = None


class TopicInfo(BaseModel):
    """Topic information."""

    name: str
    partition_count: int
    message_count: int
    consumer_groups: List[str]
    retention_hours: Optional[int] = None


class ConsumerGroupInfo(BaseModel):
    """Consumer group information."""

    name: str
    topic: str
    lag: int
    last_consumed_at: Optional[datetime] = None
    members: List[str]


class OutboxEntryResponse(BaseModel):
    """Outbox entry response."""

    id: str
    tenant_id: str
    envelope_id: str
    topic: str
    status: str
    created_at: datetime
    published_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    retry_count: int
    last_error: Optional[str] = None


class ReplayRequest(BaseModel):
    """Request to replay events."""

    topic: str = Field(..., description="Topic to replay from")
    from_timestamp: Optional[datetime] = Field(None, description="Start timestamp for replay")
    to_timestamp: Optional[datetime] = Field(None, description="End timestamp for replay")
    consumer_group: str = Field(..., description="Target consumer group")
    filter_tenant_id: Optional[str] = Field(None, description="Filter by tenant ID")
    max_events: Optional[int] = Field(1000, description="Maximum events to replay")


class ReplayResponse(BaseModel):
    """Response from replay operation."""

    replay_id: str = Field(..., description="Replay operation ID")
    status: str = Field(..., description="Replay status")
    events_count: int = Field(..., description="Number of events to replay")
    estimated_duration_seconds: Optional[int] = Field(None, description="Estimated duration")


# API Dependencies
async def get_current_tenant(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    authorizer: TenantAuthorizer = Depends()
) -> str:
    """Extract tenant ID from authorization token."""
    try:
        # Verify token and extract tenant
        identity = await authorizer.verify_producer_token(credentials.credentials)
        return identity.tenant_id
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid authorization token")


async def get_event_bus() -> EventBusSDK:
    """Get event bus SDK instance."""
    # This would be injected via dependency injection in real implementation
    raise HTTPException(status_code=500, detail="Event bus not configured")


async def get_outbox_store() -> OutboxStore:
    """Get outbox store instance."""
    # This would be injected via dependency injection in real implementation
    raise HTTPException(status_code=500, detail="Outbox store not configured")


# Import the refactored version
from .rest_refactored import create_events_api as create_events_api_refactored  # noqa: C901, PLR0915

# API Router - Using refactored version to reduce complexity
def create_events_api(
    event_bus: EventBusSDK,
    outbox_store: Optional[OutboxStore] = None,
    tenant_authorizer: Optional[TenantAuthorizer] = None
) -> FastAPI:
    """Create FastAPI app for events management - now using composition to reduce complexity."""
    # Delegate to refactored version that uses composition pattern
    return create_events_api_refactored(event_bus, outbox_store, tenant_authorizer)


# Old implementation removed - using refactored version above
# The refactored implementation is in rest_refactored.py
"""
def create_events_api_old(  # noqa: C901, PLR0915
    event_bus: EventBusSDK,
    outbox_store: Optional[OutboxStore] = None,
    tenant_authorizer: Optional[TenantAuthorizer] = None
) -> FastAPI:
    """Old implementation - kept for reference."""  # noqa: C901
    app = FastAPI(
        title="DotMac Core Events API",
        description="REST API for event publishing, topic management, and monitoring",
        version="1.0.0"
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.post("/events/publish", response_model=PublishEventResponse)
    async def publish_event(
        request: PublishEventRequest,
        tenant_id: str = Depends(get_current_tenant)
    ):
        """Publish an event."""  # noqa: C901
        try:
            # Create event envelope
            envelope = EventEnvelope.create(
                event_type=request.event_type,
                data=request.data,
                tenant_id=tenant_id,
                source=request.source,
                correlation_id=request.correlation_id,
                causation_id=request.causation_id
            )

            # Publish event
            result = await event_bus.publish(
                event_type=request.event_type,
                data=request.data,
                partition_key=request.partition_key,
                idempotency_key=request.idempotency_key
            )

            return PublishEventResponse(
                event_id=envelope.id,
                status="published",
                topic=envelope.get_topic_name()
            )

        except Exception as e:
            logger.error("Failed to publish event", error=str(e), tenant_id=tenant_id)
            raise HTTPException(status_code=500, detail=f"Failed to publish event: {str(e)}")

    @app.get("/topics", response_model=List[TopicInfo])
    async def list_topics(
        tenant_id: str = Depends(get_current_tenant)
    ):
        """List available topics for tenant."""  # noqa: C901
        try:
            topics = await event_bus.list_topics(tenant_id=tenant_id)

            topic_infos = []
            for topic_name in topics:
                info = await event_bus.get_topic_info(topic_name)
                topic_infos.append(TopicInfo(
                    name=topic_name,
                    partition_count=info.get("partition_count", 1),
                    message_count=info.get("message_count", 0),
                    consumer_groups=info.get("consumer_groups", []),
                    retention_hours=info.get("retention_hours")
                ))

            return topic_infos

        except Exception as e:
            logger.error("Failed to list topics", error=str(e), tenant_id=tenant_id)
            raise HTTPException(status_code=500, detail=f"Failed to list topics: {str(e)}")

    @app.get("/topics/{topic_name}", response_model=TopicInfo)
    async def get_topic(
        topic_name: str = Path(..., description="Topic name"),
        tenant_id: str = Depends(get_current_tenant)
    ):
        """Get topic information."""  # noqa: C901
        try:
            # Verify tenant has access to topic
            if not topic_name.startswith(f"tenant.{tenant_id}."):
                raise HTTPException(status_code=403, detail="Access denied to topic")

            info = await event_bus.get_topic_info(topic_name)

            return TopicInfo(
                name=topic_name,
                partition_count=info.get("partition_count", 1),
                message_count=info.get("message_count", 0),
                consumer_groups=info.get("consumer_groups", []),
                retention_hours=info.get("retention_hours")
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to get topic info", error=str(e), topic=topic_name)
            raise HTTPException(status_code=500, detail=f"Failed to get topic info: {str(e)}")

    @app.get("/consumer-groups", response_model=List[ConsumerGroupInfo])
    async def list_consumer_groups(
        topic: Optional[str] = Query(None, description="Filter by topic"),
        tenant_id: str = Depends(get_current_tenant)
    ):
        """List consumer groups."""  # noqa: C901
        try:
            groups = await event_bus.list_consumer_groups(tenant_id=tenant_id, topic=topic)

            group_infos = []
            for group_name in groups:
                info = await event_bus.get_consumer_group_info(group_name)
                group_infos.append(ConsumerGroupInfo(
                    name=group_name,
                    topic=info.get("topic", ""),
                    lag=info.get("lag", 0),
                    last_consumed_at=info.get("last_consumed_at"),
                    members=info.get("members", [])
                ))

            return group_infos

        except Exception as e:
            logger.error("Failed to list consumer groups", error=str(e), tenant_id=tenant_id)
            raise HTTPException(status_code=500, detail=f"Failed to list consumer groups: {str(e)}")

    @app.get("/consumer-groups/{group_name}/lag")
    async def get_consumer_lag(
        group_name: str = Path(..., description="Consumer group name"),
        tenant_id: str = Depends(get_current_tenant)
    ):
        """Get consumer group lag."""  # noqa: C901
        try:
            # Verify tenant has access to consumer group
            if not group_name.startswith(f"tenant.{tenant_id}."):
                raise HTTPException(status_code=403, detail="Access denied to consumer group")

            lag_info = await event_bus.get_consumer_lag(group_name)

            return {
                "consumer_group": group_name,
                "total_lag": lag_info.get("total_lag", 0),
                "partition_lags": lag_info.get("partition_lags", {}),
                "last_updated": lag_info.get("last_updated")
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to get consumer lag", error=str(e), group=group_name)
            raise HTTPException(status_code=500, detail=f"Failed to get consumer lag: {str(e)}")

    @app.post("/replay", response_model=ReplayResponse)
    async def replay_events(
        request: ReplayRequest,
        tenant_id: str = Depends(get_current_tenant)
    ):
        """Replay events from a topic."""  # noqa: C901
        try:
            # Verify tenant has access to topic
            if not request.topic.startswith(f"tenant.{tenant_id}."):
                raise HTTPException(status_code=403, detail="Access denied to topic")

            # Start replay operation
            replay_result = await event_bus.replay_events(
                topic=request.topic,
                consumer_group=request.consumer_group,
                from_timestamp=request.from_timestamp,
                to_timestamp=request.to_timestamp,
                max_events=request.max_events,
                tenant_id=tenant_id
            )

            return ReplayResponse(
                replay_id=replay_result["replay_id"],
                status=replay_result["status"],
                events_count=replay_result["events_count"],
                estimated_duration_seconds=replay_result.get("estimated_duration_seconds")
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to start replay", error=str(e), tenant_id=tenant_id)
            raise HTTPException(status_code=500, detail=f"Failed to start replay: {str(e)}")

    @app.get("/replay/{replay_id}/status")
    async def get_replay_status(
        replay_id: str = Path(..., description="Replay operation ID"),
        tenant_id: str = Depends(get_current_tenant)
    ):
        """Get replay operation status."""  # noqa: C901
        try:
            status = await event_bus.get_replay_status(replay_id, tenant_id=tenant_id)

            return {
                "replay_id": replay_id,
                "status": status.get("status"),
                "progress": status.get("progress", {}),
                "events_replayed": status.get("events_replayed", 0),
                "errors": status.get("errors", []),
                "started_at": status.get("started_at"),
                "completed_at": status.get("completed_at")
            }

        except Exception as e:
            logger.error("Failed to get replay status", error=str(e), replay_id=replay_id)
            raise HTTPException(status_code=500, detail=f"Failed to get replay status: {str(e)}")

    # Outbox endpoints (if outbox store is available)
    if outbox_store:

        @app.get("/outbox/entries", response_model=List[OutboxEntryResponse])
        async def list_outbox_entries(
            status: Optional[OutboxStatus] = Query(None, description="Filter by status"),
            limit: int = Query(100, description="Maximum entries to return"),
            tenant_id: str = Depends(get_current_tenant)
        ):
            """List outbox entries."""  # noqa: C901
            try:
                if status == OutboxStatus.PENDING:
                    entries = await outbox_store.get_pending_entries(limit, tenant_id)
                elif status == OutboxStatus.FAILED:
                    entries = await outbox_store.get_failed_entries(limit)
                    # Filter by tenant
                    entries = [e for e in entries if e.tenant_id == tenant_id]
                else:
                    # Get all entries for tenant (would need additional method)
                    entries = await outbox_store.get_pending_entries(limit, tenant_id)

                return [
                    OutboxEntryResponse(
                        id=entry.id,
                        tenant_id=entry.tenant_id,
                        envelope_id=entry.envelope_id,
                        topic=entry.topic,
                        status=entry.status.value,
                        created_at=entry.created_at,
                        published_at=entry.published_at,
                        failed_at=entry.failed_at,
                        retry_count=entry.retry_count,
                        last_error=entry.last_error
                    )
                    for entry in entries
                ]

            except Exception as e:
                logger.error("Failed to list outbox entries", error=str(e), tenant_id=tenant_id)
                raise HTTPException(status_code=500, detail=f"Failed to list outbox entries: {str(e)}")

        @app.get("/outbox/stats")
        async def get_outbox_stats(
            tenant_id: str = Depends(get_current_tenant)
        ):
            """Get outbox statistics."""  # noqa: C901
            try:
                stats = await outbox_store.get_stats()

                # Filter stats for tenant (would need tenant-specific stats method)
                return {
                    "total_entries": stats.get("total_entries", 0),
                    "by_status": stats.get("by_status", {}),
                    "avg_publish_time_seconds": stats.get("avg_publish_time_seconds", 0)
                }

            except Exception as e:
                logger.error("Failed to get outbox stats", error=str(e), tenant_id=tenant_id)
                raise HTTPException(status_code=500, detail=f"Failed to get outbox stats: {str(e)}")

        @app.post("/outbox/entries/{entry_id}/retry")
        async def retry_outbox_entry(
            entry_id: str = Path(..., description="Outbox entry ID"),
            tenant_id: str = Depends(get_current_tenant)
        ):
            """Retry failed outbox entry."""  # noqa: C901
            try:
                # Get entry and verify tenant access
                entry = await outbox_store.get_entry(entry_id)
                if not entry:
                    raise HTTPException(status_code=404, detail="Outbox entry not found")

                if entry.tenant_id != tenant_id:
                    raise HTTPException(status_code=403, detail="Access denied to outbox entry")

                if entry.status != OutboxStatus.FAILED:
                    raise HTTPException(status_code=400, detail="Entry is not in failed status")

                # Reset to pending for retry
                success = await outbox_store.update_status(entry_id, OutboxStatus.PENDING)

                return {
                    "entry_id": entry_id,
                    "status": "queued_for_retry" if success else "failed_to_queue"
                }

            except HTTPException:
                raise
            except Exception as e:
                logger.error("Failed to retry outbox entry", error=str(e), entry_id=entry_id)
                raise HTTPException(status_code=500, detail=f"Failed to retry outbox entry: {str(e)}")

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""  # noqa: C901
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0.0"
        }

    @app.get("/metrics")
    async def get_metrics(
        tenant_id: str = Depends(get_current_tenant)
    ):
        """Get events metrics for tenant."""  # noqa: C901
        try:
            metrics = await event_bus.get_metrics(tenant_id=tenant_id)

            return {
                "tenant_id": tenant_id,
                "events_published_total": metrics.get("events_published_total", 0),
                "events_consumed_total": metrics.get("events_consumed_total", 0),
                "publish_errors_total": metrics.get("publish_errors_total", 0),
                "consumer_lag_total": metrics.get("consumer_lag_total", 0),
                "last_updated": metrics.get("last_updated")
            }

        except Exception as e:
            logger.error("Failed to get metrics", error=str(e), tenant_id=tenant_id)
            raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")

    return app
"""  # noqa: C901


# Factory function for production use
def create_production_events_api(  # noqa: C901
    event_bus: EventBusSDK,
    outbox_store: Optional[OutboxStore] = None,
    tenant_authorizer: Optional[TenantAuthorizer] = None,
    cors_origins: List[str] = None
) -> FastAPI:
    """Create production-ready events API."""

    app = create_events_api(event_bus, outbox_store, tenant_authorizer)

    # Update CORS for production
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST"],
            allow_headers=["Authorization", "Content-Type"],
        )

    # Add additional middleware for production
    @app.middleware("http")
    async def add_security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response

    return app
