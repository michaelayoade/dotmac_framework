"""
Audit API endpoints for DotMac monitoring system.

Provides FastAPI endpoints for audit event management including:
- Event querying and filtering
- Real-time event streaming
- Audit statistics and reporting
- Compliance reporting
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from fastapi import APIRouter, Depends, HTTPException, Query, Request
    from fastapi.responses import StreamingResponse
    from pydantic import BaseModel, Field

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    APIRouter = BaseModel = Field = None

from .utils import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, get_current_timestamp, get_logger

logger = get_logger(__name__)

from .audit import (
    AuditEvent,
    AuditEventType,
    AuditLogger,
    AuditOutcome,
    AuditSeverity,
    get_audit_logger,
)

# Pydantic models for API
if FASTAPI_AVAILABLE:

    class AuditEventQuery(BaseModel):
        """Query parameters for audit events."""

        start_time: Optional[float] = Field(
            None, description="Start timestamp (Unix epoch)"
        )
        end_time: Optional[float] = Field(
            None, description="End timestamp (Unix epoch)"
        )
        event_types: Optional[List[str]] = Field(
            None, description="Filter by event types"
        )
        actor_ids: Optional[List[str]] = Field(None, description="Filter by actor IDs")
        resource_types: Optional[List[str]] = Field(
            None, description="Filter by resource types"
        )
        resource_ids: Optional[List[str]] = Field(
            None, description="Filter by resource IDs"
        )
        severities: Optional[List[str]] = Field(
            None, description="Filter by severities"
        )
        outcomes: Optional[List[str]] = Field(None, description="Filter by outcomes")
        tenant_id: Optional[str] = Field(None, description="Filter by tenant ID")
        search: Optional[str] = Field(
            None, description="Text search in message/description"
        )
        limit: int = Field(
            DEFAULT_PAGE_SIZE,
            ge=1,
            le=MAX_PAGE_SIZE,
            description="Maximum number of events to return",
        )
        offset: int = Field(0, ge=0, description="Number of events to skip")

    class AuditEventResponse(BaseModel):
        """Response model for audit events."""

        event_id: str
        event_type: str
        event_name: str
        timestamp: float
        duration_ms: Optional[float]
        severity: str
        outcome: str
        message: str
        description: Optional[str]

        # Simplified actor information
        actor_id: Optional[str]
        actor_type: Optional[str]
        actor_name: Optional[str]
        username: Optional[str]

        # Simplified resource information
        resource_id: Optional[str]
        resource_type: Optional[str]
        resource_name: Optional[str]

        # Context information
        client_ip: Optional[str]
        user_agent: Optional[str]
        service_name: Optional[str]
        environment: Optional[str]

        # Additional data
        tags: Dict[str, str] = Field(default_factory=dict)
        risk_score: Optional[int]
        compliance_frameworks: List[str] = Field(default_factory=list)

        @classmethod
        def from_audit_event(cls, event: AuditEvent) -> "AuditEventResponse":
            """Convert AuditEvent to API response model."""
            return cls(
                event_id=event.event_id,
                event_type=event.event_type.value,
                event_name=event.event_name or event.event_type.value,
                timestamp=event.timestamp,
                duration_ms=event.duration_ms,
                severity=event.severity.value,
                outcome=event.outcome.value,
                message=event.message,
                description=event.description,
                # Actor information
                actor_id=event.actor.actor_id if event.actor else None,
                actor_type=event.actor.actor_type if event.actor else None,
                actor_name=event.actor.actor_name if event.actor else None,
                username=event.actor.username if event.actor else None,
                # Resource information
                resource_id=event.resource.resource_id if event.resource else None,
                resource_type=event.resource.resource_type if event.resource else None,
                resource_name=event.resource.resource_name if event.resource else None,
                # Context information
                client_ip=event.context.client_ip if event.context else None,
                user_agent=event.context.user_agent if event.context else None,
                service_name=event.context.service_name if event.context else None,
                environment=event.context.environment if event.context else None,
                # Additional data
                tags=event.tags,
                risk_score=event.risk_score,
                compliance_frameworks=event.compliance_frameworks,
            )

    class AuditEventListResponse(BaseModel):
        """Response model for audit event lists."""

        events: List[AuditEventResponse]
        total_count: int
        offset: int
        limit: int
        has_more: bool

    class AuditStatsResponse(BaseModel):
        """Response model for audit statistics."""

        total_events: int
        time_range: Dict[str, Optional[float]]
        events_by_type: Dict[str, int]
        events_by_severity: Dict[str, int]
        events_by_outcome: Dict[str, int]
        unique_actors: int
        unique_resources: int
        high_risk_events: int
        failed_events: int

    class AuditComplianceReport(BaseModel):
        """Response model for compliance reporting."""

        framework: str
        total_events: int
        compliant_events: int
        non_compliant_events: int
        compliance_percentage: float
        critical_violations: int
        report_period: Dict[str, Optional[float]]
        violations_by_type: Dict[str, int]


def get_current_audit_logger() -> AuditLogger:
    """Dependency to get the current audit logger."""
    logger_instance = get_audit_logger()
    if not logger_instance:
        raise HTTPException(status_code=500, detail="Audit logger not initialized")
    return logger_instance


def create_audit_api_router(
    prefix: str = "/audit", tags: List[str] = None, dependencies: List[Any] = None
) -> "APIRouter":
    """
    Create FastAPI router for audit endpoints.

    Args:
        prefix: URL prefix for all audit endpoints
        tags: OpenAPI tags for documentation
        dependencies: FastAPI dependencies to apply to all routes

    Returns:
        Configured FastAPI router
    """
    if not FASTAPI_AVAILABLE:
        raise ImportError("FastAPI is required for audit API endpoints")

    if tags is None:
        tags = ["audit"]

    router = APIRouter(prefix=prefix, tags=tags, dependencies=dependencies or [])

    @router.get("/events", response_model=AuditEventListResponse)
    async def query_audit_events(
        request: Request,
        start_time: Optional[float] = Query(None, description="Start timestamp"),
        end_time: Optional[float] = Query(None, description="End timestamp"),
        event_types: Optional[List[str]] = Query(None, description="Event types"),
        actor_ids: Optional[List[str]] = Query(None, description="Actor IDs"),
        resource_types: Optional[List[str]] = Query(None, description="Resource types"),
        severities: Optional[List[str]] = Query(None, description="Severity levels"),
        outcomes: Optional[List[str]] = Query(None, description="Event outcomes"),
        tenant_id: Optional[str] = Query(None, description="Tenant ID"),
        search: Optional[str] = Query(None, description="Text search"),
        limit: int = Query(
            DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Result limit"
        ),
        offset: int = Query(0, ge=0, description="Result offset"),
        audit_logger: AuditLogger = Depends(get_current_audit_logger),
    ):
        """Query audit events with filtering and pagination."""

        # Convert string enum values to enum objects
        parsed_event_types = None
        if event_types:
            parsed_event_types = []
            for event_type_str in event_types:
                try:
                    parsed_event_types.append(AuditEventType(event_type_str))
                except ValueError:
                    raise HTTPException(
                        status_code=400, detail=f"Invalid event type: {event_type_str}"
                    )

        # Query events
        try:
            events = audit_logger.query_events(
                start_time=start_time,
                end_time=end_time,
                event_types=parsed_event_types,
                actor_ids=actor_ids,
                resource_types=resource_types,
                tenant_id=tenant_id,
                limit=limit + 1,  # Get one extra to check if there are more
                offset=offset,
            )

            # Filter by search term if provided
            if search:
                search_lower = search.lower()
                events = [
                    e
                    for e in events
                    if search_lower in e.message.lower()
                    or (e.description and search_lower in e.description.lower())
                ]

            # Filter by severity if provided
            if severities:
                severity_enums = [AuditSeverity(s) for s in severities]
                events = [e for e in events if e.severity in severity_enums]

            # Filter by outcome if provided
            if outcomes:
                outcome_enums = [AuditOutcome(o) for o in outcomes]
                events = [e for e in events if e.outcome in outcome_enums]

            # Check if there are more results
            has_more = len(events) > limit
            if has_more:
                events = events[:-1]

            # Convert to response models
            response_events = [
                AuditEventResponse.from_audit_event(event) for event in events
            ]

            return AuditEventListResponse(
                events=response_events,
                total_count=len(
                    response_events
                ),  # This is not the true total, just current page
                offset=offset,
                limit=limit,
                has_more=has_more,
            )

        except Exception as e:
            logger.error(f"Failed to query audit events: {e}")
            raise HTTPException(status_code=500, detail="Failed to query audit events")

    @router.get("/events/{event_id}", response_model=AuditEventResponse)
    async def get_audit_event(
        event_id: str, audit_logger: AuditLogger = Depends(get_current_audit_logger)
    ):
        """Get a specific audit event by ID."""

        try:
            # Query for the specific event (inefficient but works with current interface)
            events = audit_logger.query_events(limit=10000)
            event = next((e for e in events if e.event_id == event_id), None)

            if not event:
                raise HTTPException(status_code=404, detail="Audit event not found")

            return AuditEventResponse.from_audit_event(event)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get audit event {event_id}: {e}")
            raise HTTPException(
                status_code=500, detail="Failed to retrieve audit event"
            )

    @router.get("/stats", response_model=AuditStatsResponse)
    async def get_audit_stats(
        start_time: Optional[float] = Query(None, description="Start timestamp"),
        end_time: Optional[float] = Query(None, description="End timestamp"),
        tenant_id: Optional[str] = Query(None, description="Tenant ID"),
        audit_logger: AuditLogger = Depends(get_current_audit_logger),
    ):
        """Get audit statistics for the specified time period."""

        try:
            stats = audit_logger.get_event_stats(
                start_time=start_time, end_time=end_time
            )

            # Calculate additional metrics
            events = audit_logger.query_events(
                start_time=start_time,
                end_time=end_time,
                tenant_id=tenant_id,
                limit=10000,
            )

            high_risk_events = len(
                [e for e in events if e.risk_score and e.risk_score >= 70]
            )
            failed_events = len(
                [e for e in events if e.outcome == AuditOutcome.FAILURE]
            )

            return AuditStatsResponse(
                total_events=stats["total_events"],
                time_range={"start_time": start_time, "end_time": end_time},
                events_by_type=stats["events_by_type"],
                events_by_severity=stats["events_by_severity"],
                events_by_outcome=stats["events_by_outcome"],
                unique_actors=stats["unique_actors"],
                unique_resources=stats["unique_resources"],
                high_risk_events=high_risk_events,
                failed_events=failed_events,
            )

        except Exception as e:
            logger.error(f"Failed to get audit stats: {e}")
            raise HTTPException(
                status_code=500, detail="Failed to retrieve audit statistics"
            )

    @router.get("/compliance/{framework}", response_model=AuditComplianceReport)
    async def get_compliance_report(
        framework: str,
        start_time: Optional[float] = Query(None, description="Start timestamp"),
        end_time: Optional[float] = Query(None, description="End timestamp"),
        tenant_id: Optional[str] = Query(None, description="Tenant ID"),
        audit_logger: AuditLogger = Depends(get_current_audit_logger),
    ):
        """Generate compliance report for a specific framework."""

        try:
            events = audit_logger.query_events(
                start_time=start_time,
                end_time=end_time,
                tenant_id=tenant_id,
                limit=10000,
            )

            # Filter events relevant to the compliance framework
            framework_events = [
                e
                for e in events
                if framework.lower() in [f.lower() for f in e.compliance_frameworks]
            ]

            total_events = len(framework_events)
            compliant_events = len(
                [e for e in framework_events if e.outcome == AuditOutcome.SUCCESS]
            )
            non_compliant_events = total_events - compliant_events
            compliance_percentage = (
                (compliant_events / total_events * 100) if total_events > 0 else 100.0
            )

            critical_violations = len(
                [
                    e
                    for e in framework_events
                    if e.severity == AuditSeverity.CRITICAL
                    and e.outcome == AuditOutcome.FAILURE
                ]
            )

            # Count violations by event type
            violations_by_type = {}
            for event in framework_events:
                if event.outcome == AuditOutcome.FAILURE:
                    event_type = event.event_type.value
                    violations_by_type[event_type] = (
                        violations_by_type.get(event_type, 0) + 1
                    )

            return AuditComplianceReport(
                framework=framework,
                total_events=total_events,
                compliant_events=compliant_events,
                non_compliant_events=non_compliant_events,
                compliance_percentage=compliance_percentage,
                critical_violations=critical_violations,
                report_period={"start_time": start_time, "end_time": end_time},
                violations_by_type=violations_by_type,
            )

        except Exception as e:
            logger.error(f"Failed to generate compliance report for {framework}: {e}")
            raise HTTPException(
                status_code=500, detail="Failed to generate compliance report"
            )

    @router.get("/events/stream")
    async def stream_audit_events(
        request: Request,
        event_types: Optional[List[str]] = Query(
            None, description="Event types to stream"
        ),
        severities: Optional[List[str]] = Query(
            None, description="Severity levels to stream"
        ),
        tenant_id: Optional[str] = Query(None, description="Tenant ID filter"),
        audit_logger: AuditLogger = Depends(get_current_audit_logger),
    ):
        """Stream audit events in real-time (Server-Sent Events)."""

        async def event_stream():
            """Generate server-sent events for audit stream."""
            last_check = get_current_timestamp()

            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break

                try:
                    # Get recent events (simple polling approach)
                    events = audit_logger.query_events(
                        start_time=last_check, tenant_id=tenant_id, limit=100
                    )

                    # Filter by event types if specified
                    if event_types:
                        try:
                            type_enums = [AuditEventType(t) for t in event_types]
                            events = [e for e in events if e.event_type in type_enums]
                        except ValueError as e:
                            logger.warning(f"Invalid event type in stream filter: {e}")

                    # Filter by severities if specified
                    if severities:
                        try:
                            severity_enums = [AuditSeverity(s) for s in severities]
                            events = [e for e in events if e.severity in severity_enums]
                        except ValueError as e:
                            logger.warning(f"Invalid severity in stream filter: {e}")

                    # Send events
                    for event in events:
                        response_event = AuditEventResponse.from_audit_event(event)
                        yield f"data: {response_event.model_dump_json()}\n\n"

                    last_check = get_current_timestamp()

                    # Wait before next check
                    import asyncio

                    await asyncio.sleep(1)

                except Exception as e:
                    logger.error(f"Error in audit event stream: {e}")
                    yield f"event: error\ndata: {{'error': 'Stream error occurred'}}\n\n"
                    break

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control",
            },
        )

    @router.post("/events/export")
    async def export_audit_events(
        query: AuditEventQuery,
        format: str = Query("json", description="Export format (json, csv)"),
        audit_logger: AuditLogger = Depends(get_current_audit_logger),
    ):
        """Export audit events in the specified format."""

        try:
            # Convert string enum values
            parsed_event_types = None
            if query.event_types:
                parsed_event_types = [AuditEventType(t) for t in query.event_types]

            # Query all matching events (no pagination for export)
            events = audit_logger.query_events(
                start_time=query.start_time,
                end_time=query.end_time,
                event_types=parsed_event_types,
                actor_ids=query.actor_ids,
                resource_types=query.resource_types,
                tenant_id=query.tenant_id,
                limit=10000,  # Large limit for export
            )

            if format.lower() == "csv":
                # Generate CSV
                import csv
                import io

                output = io.StringIO()
                writer = csv.writer(output)

                # Write header
                writer.writerow(
                    [
                        "event_id",
                        "timestamp",
                        "event_type",
                        "severity",
                        "outcome",
                        "message",
                        "actor_id",
                        "actor_type",
                        "resource_type",
                        "resource_id",
                        "client_ip",
                        "service_name",
                    ]
                )

                # Write events
                for event in events:
                    writer.writerow(
                        [
                            event.event_id,
                            datetime.fromtimestamp(event.timestamp).isoformat(),
                            event.event_type.value,
                            event.severity.value,
                            event.outcome.value,
                            event.message,
                            event.actor.actor_id if event.actor else "",
                            event.actor.actor_type if event.actor else "",
                            event.resource.resource_type if event.resource else "",
                            event.resource.resource_id if event.resource else "",
                            event.context.client_ip if event.context else "",
                            event.context.service_name if event.context else "",
                        ]
                    )

                return StreamingResponse(
                    io.BytesIO(output.getvalue().encode()),
                    media_type="text/csv",
                    headers={
                        "Content-Disposition": "attachment; filename=audit_events.csv"
                    },
                )

            else:
                # Default to JSON
                response_events = [
                    AuditEventResponse.from_audit_event(event) for event in events
                ]
                export_data = {
                    "export_timestamp": get_current_timestamp(),
                    "total_events": len(response_events),
                    "query_parameters": query.model_dump(),
                    "events": [event.model_dump() for event in response_events],
                }

                import json

                return StreamingResponse(
                    io.BytesIO(json.dumps(export_data, indent=2).encode()),
                    media_type="application/json",
                    headers={
                        "Content-Disposition": "attachment; filename=audit_events.json"
                    },
                )

        except Exception as e:
            logger.error(f"Failed to export audit events: {e}")
            raise HTTPException(status_code=500, detail="Failed to export audit events")

    return router


def create_audit_health_router(prefix: str = "/audit/health") -> "APIRouter":
    """Create a simple health check router for audit system."""
    if not FASTAPI_AVAILABLE:
        raise ImportError("FastAPI is required for audit health endpoints")

    router = APIRouter(prefix=prefix, tags=["audit-health"])

    @router.get("/")
    async def audit_health():
        """Check audit system health."""
        audit_logger = get_audit_logger()

        return {
            "status": "healthy" if audit_logger else "unhealthy",
            "audit_logger_initialized": audit_logger is not None,
            "timestamp": get_current_timestamp(),
        }

    return router


__all__ = [
    "AuditEventQuery",
    "AuditEventResponse",
    "AuditEventListResponse",
    "AuditStatsResponse",
    "AuditComplianceReport",
    "create_audit_api_router",
    "create_audit_health_router",
    "get_current_audit_logger",
    "FASTAPI_AVAILABLE",
]
