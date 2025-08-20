"""
Security monitoring API endpoints.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from ..core.dependencies import get_tenant_id
from ..runtime.security_monitoring import (
    SecurityEventType,
    get_security_monitor,
)


class SecurityEventResponse(BaseModel):
    """Response model for security events."""

    event_type: str = Field(..., description="Type of security event")
    timestamp: datetime = Field(..., description="Event timestamp")
    client_ip: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="User agent string")
    tenant_id: Optional[str] = Field(None, description="Tenant ID")
    user_id: Optional[str] = Field(None, description="User ID")
    endpoint: Optional[str] = Field(None, description="API endpoint")
    request_id: Optional[str] = Field(None, description="Request ID")
    details: Dict[str, Any] = Field(default_factory=dict, description="Event details")
    severity: str = Field(..., description="Event severity")


class SecurityStatsResponse(BaseModel):
    """Response model for security statistics."""

    total_events: int = Field(..., description="Total number of security events")
    event_types: Dict[str, int] = Field(..., description="Events by type")
    recent_events_1h: int = Field(..., description="Events in last hour")
    recent_by_type: Dict[str, int] = Field(..., description="Recent events by type")
    recent_by_severity: Dict[str, int] = Field(..., description="Recent events by severity")
    top_clients: Dict[str, int] = Field(..., description="Top clients by event count")
    monitored_clients: int = Field(..., description="Number of monitored clients")


class SecurityAPI:
    """Security monitoring API endpoints."""

    def __init__(self):
        self.router = APIRouter(prefix="/security", tags=["security"])
        self._setup_routes()

    def _setup_routes(self):
        """Set up API routes."""

        @self.router.get(
            "/events",
            response_model=List[SecurityEventResponse],
            summary="Get security events",
            description="Retrieve recent security events"
        )
        async def get_security_events(
            limit: int = Query(100, ge=1, le=1000, description="Maximum number of events"),
            event_type: Optional[str] = Query(None, description="Filter by event type"),
            client_ip: Optional[str] = Query(None, description="Filter by client IP"),
            severity: Optional[str] = Query(None, description="Filter by severity"),
            tenant_id: str = Depends(get_tenant_id)
        ) -> List[SecurityEventResponse]:
            """Get security events."""
            try:
                monitor = get_security_monitor()

                # Convert string to enum if provided
                event_type_enum = None
                if event_type:
                    try:
                        event_type_enum = SecurityEventType(event_type)
                    except ValueError:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid event type: {event_type}"
                        )

                events = await monitor.get_recent_events(
                    limit=limit,
                    event_type=event_type_enum,
                    client_ip=client_ip,
                    severity=severity
                )

                return [
                    SecurityEventResponse(
                        event_type=event.event_type,
                        timestamp=event.timestamp,
                        client_ip=event.client_ip,
                        user_agent=event.user_agent,
                        tenant_id=event.tenant_id,
                        user_id=event.user_id,
                        endpoint=event.endpoint,
                        request_id=event.request_id,
                        details=event.details,
                        severity=event.severity
                    )
                    for event in events
                ]

            except HTTPException:
                raise
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to retrieve security events"
                )

        @self.router.get(
            "/stats",
            response_model=SecurityStatsResponse,
            summary="Get security statistics",
            description="Get security monitoring statistics"
        )
        async def get_security_stats(
            tenant_id: str = Depends(get_tenant_id)
        ) -> SecurityStatsResponse:
            """Get security statistics."""
            try:
                monitor = get_security_monitor()
                stats = await monitor.get_statistics()

                return SecurityStatsResponse(**stats)

            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to retrieve security statistics"
                )

        @self.router.get(
            "/event-types",
            response_model=List[str],
            summary="Get event types",
            description="Get list of available security event types"
        )
        async def get_event_types(
            tenant_id: str = Depends(get_tenant_id)
        ) -> List[str]:
            """Get available security event types."""
            return [event_type.value for event_type in SecurityEventType]
