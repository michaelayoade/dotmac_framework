"""
Events API endpoints for analytics data ingestion.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..core.database import get_session
from ..core.exceptions import AnalyticsError, ValidationError
from ..models.enums import EventType, TimeGranularity
from ..services.events import EventService

events_router = APIRouter(prefix="/events", tags=["events"])


class EventTrackRequest(BaseModel):
    """Request model for tracking an event."""
    event_type: EventType
    event_name: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    customer_id: Optional[str] = None
    properties: Optional[Dict[str, Any]] = Field(default_factory=dict)
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    source: Optional[str] = None
    timestamp: Optional[datetime] = None


class EventBatchRequest(BaseModel):
    """Request model for batch event tracking."""
    events: List[Dict[str, Any]]
    source: Optional[str] = None


class EventQueryRequest(BaseModel):
    """Request model for querying events."""
    event_type: Optional[EventType] = None
    event_name: Optional[str] = None
    user_id: Optional[str] = None
    customer_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = Field(default=100, le=1000)
    offset: int = Field(default=0, ge=0)


class EventAggregateRequest(BaseModel):
    """Request model for event aggregation."""
    granularity: TimeGranularity
    start_time: datetime
    end_time: datetime
    event_type: Optional[EventType] = None
    event_name: Optional[str] = None
    dimensions: Optional[List[str]] = Field(default_factory=list)


class EventFunnelRequest(BaseModel):
    """Request model for funnel analysis."""
    funnel_steps: List[str]
    start_time: datetime
    end_time: datetime
    user_id_field: str = "user_id"


class EventSchemaRequest(BaseModel):
    """Request model for creating event schema."""
    event_type: EventType
    event_name: str
    schema_definition: Dict[str, Any]
    version: str = "1.0"


def get_tenant_id(request) -> str:
    """Extract tenant ID from request headers."""
    # In a real implementation, this would extract from JWT token or headers
    return "default_tenant"


@events_router.post("/track")
async def track_event(
    request: EventTrackRequest,
    db: Session = Depends(get_session)
):
    """Track a single analytics event."""
    try:
        tenant_id = get_tenant_id(request)
        service = EventService(db)

        event = await service.track_event(
            tenant_id=tenant_id,
            event_type=request.event_type,
            event_name=request.event_name,
            properties=request.properties,
            context=request.context,
            user_id=request.user_id,
            session_id=request.session_id,
            customer_id=request.customer_id,
            source=request.source
        )

        return {
            "event_id": str(event.id),
            "status": "tracked",
            "timestamp": event.timestamp
        }

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AnalyticsError as e:
        raise HTTPException(status_code=500, detail=str(e))


@events_router.post("/track/batch")
async def track_events_batch(
    request: EventBatchRequest,
    db: Session = Depends(get_session)
):
    """Track multiple events in a batch."""
    try:
        tenant_id = get_tenant_id(request)
        service = EventService(db)

        batch = await service.track_events_batch(
            tenant_id=tenant_id,
            events=request.events,
            source=request.source
        )

        return {
            "batch_id": str(batch.id),
            "status": batch.status,
            "success_count": batch.success_count,
            "error_count": batch.error_count,
            "processed_at": batch.processed_at
        }

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AnalyticsError as e:
        raise HTTPException(status_code=500, detail=str(e))


@events_router.post("/query")
async def query_events(
    request: EventQueryRequest,
    db: Session = Depends(get_session)
):
    """Query events with filtering options."""
    try:
        tenant_id = get_tenant_id(request)
        service = EventService(db)

        events = await service.get_events(
            tenant_id=tenant_id,
            event_type=request.event_type,
            event_name=request.event_name,
            user_id=request.user_id,
            customer_id=request.customer_id,
            start_time=request.start_time,
            end_time=request.end_time,
            limit=request.limit,
            offset=request.offset
        )

        return {
            "events": [
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
                    "source": event.source
                }
                for event in events
            ],
            "count": len(events),
            "limit": request.limit,
            "offset": request.offset
        }

    except AnalyticsError as e:
        raise HTTPException(status_code=500, detail=str(e))


@events_router.post("/aggregate")
async def aggregate_events(
    request: EventAggregateRequest,
    db: Session = Depends(get_session)
):
    """Aggregate events by time and dimensions."""
    try:
        tenant_id = get_tenant_id(request)
        service = EventService(db)

        aggregates = await service.aggregate_events(
            tenant_id=tenant_id,
            granularity=request.granularity,
            start_time=request.start_time,
            end_time=request.end_time,
            event_type=request.event_type,
            event_name=request.event_name,
            dimensions=request.dimensions
        )

        return {
            "aggregates": [
                {
                    "time_bucket": aggregate.time_bucket,
                    "granularity": aggregate.granularity,
                    "event_count": aggregate.event_count,
                    "unique_users": aggregate.unique_users,
                    "unique_sessions": aggregate.unique_sessions,
                    "unique_customers": aggregate.unique_customers,
                    "dimensions": aggregate.dimensions
                }
                for aggregate in aggregates
            ],
            "count": len(aggregates)
        }

    except AnalyticsError as e:
        raise HTTPException(status_code=500, detail=str(e))


@events_router.post("/funnel")
async def analyze_funnel(
    request: EventFunnelRequest,
    db: Session = Depends(get_session)
):
    """Analyze event funnel conversion rates."""
    try:
        tenant_id = get_tenant_id(request)
        service = EventService(db)

        funnel_data = await service.get_event_funnel(
            tenant_id=tenant_id,
            funnel_steps=request.funnel_steps,
            start_time=request.start_time,
            end_time=request.end_time,
            user_id_field=request.user_id_field
        )

        return {
            "funnel_steps": request.funnel_steps,
            "analysis_period": {
                "start_time": request.start_time,
                "end_time": request.end_time
            },
            "funnel_data": funnel_data
        }

    except AnalyticsError as e:
        raise HTTPException(status_code=500, detail=str(e))


@events_router.post("/schema")
async def create_event_schema(
    request: EventSchemaRequest,
    db: Session = Depends(get_session)
):
    """Create event schema for validation."""
    try:
        tenant_id = get_tenant_id(request)
        service = EventService(db)

        schema = await service.create_event_schema(
            tenant_id=tenant_id,
            event_type=request.event_type,
            event_name=request.event_name,
            schema_definition=request.schema_definition,
            version=request.version
        )

        return {
            "schema_id": str(schema.id),
            "event_type": schema.event_type,
            "event_name": schema.event_name,
            "version": schema.version,
            "created_at": schema.created_at
        }

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AnalyticsError as e:
        raise HTTPException(status_code=500, detail=str(e))


@events_router.get("/schemas")
async def list_event_schemas(
    event_type: Optional[EventType] = Query(None),
    event_name: Optional[str] = Query(None),
    db: Session = Depends(get_session)
):
    """List event schemas."""
    try:
        tenant_id = get_tenant_id(None)

        # Query schemas from database
        from ..models.events import EventSchema
        query = db.query(EventSchema).filter(
            EventSchema.tenant_id == tenant_id,
            EventSchema.is_active == True
        )

        if event_type:
            query = query.filter(EventSchema.event_type == event_type.value)

        if event_name:
            query = query.filter(EventSchema.event_name == event_name)

        schemas = query.all()

        return {
            "schemas": [
                {
                    "id": str(schema.id),
                    "event_type": schema.event_type,
                    "event_name": schema.event_name,
                    "version": schema.version,
                    "schema_definition": schema.schema_definition,
                    "created_at": schema.created_at
                }
                for schema in schemas
            ],
            "count": len(schemas)
        }

    except AnalyticsError as e:
        raise HTTPException(status_code=500, detail=str(e))
