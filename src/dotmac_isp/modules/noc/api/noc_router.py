"""
NOC API Router.

REST API endpoints for Network Operations Center functionality including
dashboards, alarms, events, and operational monitoring.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from dotmac_isp.core.auth import require_permissions
from dotmac_isp.core.database import get_db
from dotmac_shared.api.router_factory import RouterFactory
from dotmac_shared.api.exception_handlers import standard_exception_handler

from ..services.noc_dashboard_service import NOCDashboardService
from ..services.alarm_management_service import AlarmManagementService
from ..services.event_correlation_service import EventCorrelationService

# Pydantic models for API requests/responses

class AlarmCreateRequest(BaseModel):
    """Request model for creating alarms."""
    alarm_type: str = Field(..., description="Type of alarm")
    severity: str = Field(..., description="Alarm severity")
    title: str = Field(..., description="Alarm title")
    description: Optional[str] = Field(None, description="Detailed description")
    device_id: Optional[str] = Field(None, description="Associated device ID")
    interface_id: Optional[str] = Field(None, description="Associated interface ID")
    service_id: Optional[str] = Field(None, description="Associated service ID")
    customer_id: Optional[str] = Field(None, description="Associated customer ID")
    source_system: Optional[str] = Field(None, description="Source system")
    context_data: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    tags: Optional[List[str]] = Field(None, description="Alarm tags")


class AlarmUpdateRequest(BaseModel):
    """Request model for updating alarms."""
    acknowledged_by: Optional[str] = Field(None, description="User acknowledging alarm")
    notes: Optional[str] = Field(None, description="Acknowledgment notes")
    clear_reason: Optional[str] = Field(None, description="Reason for clearing")


class AlarmRuleCreateRequest(BaseModel):
    """Request model for creating alarm rules."""
    name: str = Field(..., description="Rule name")
    description: Optional[str] = Field(None, description="Rule description")
    metric_name: str = Field(..., description="Metric to monitor")
    threshold_value: float = Field(..., description="Threshold value")
    threshold_operator: str = Field(..., description="Comparison operator")
    alarm_type: str = Field(..., description="Alarm type to generate")
    alarm_severity: str = Field(..., description="Alarm severity to generate")
    device_type: Optional[str] = Field(None, description="Target device type")
    evaluation_window_minutes: Optional[int] = Field(5, description="Evaluation window")


class EventProcessRequest(BaseModel):
    """Request model for processing events."""
    event_type: str = Field(..., description="Type of event")
    severity: str = Field(..., description="Event severity")
    title: str = Field(..., description="Event title")
    description: Optional[str] = Field(None, description="Event description")
    device_id: Optional[str] = Field(None, description="Associated device ID")
    service_id: Optional[str] = Field(None, description="Associated service ID")
    customer_id: Optional[str] = Field(None, description="Associated customer ID")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="Raw event data")


class NOCRouterFactory(RouterFactory):
    """Factory for creating NOC API router."""

    @classmethod
    def create_noc_router(cls) -> APIRouter:
        """Create NOC API router with all endpoints."""
        router = APIRouter(prefix="/api/noc", tags=["noc"])
        
        # Dashboard endpoints
        @router.get("/dashboard/overview")
        @require_permissions("noc:read")
        async def get_network_overview(
            db: Session = Depends(get_db),
            tenant_id: str = Depends(cls.get_tenant_id)
        ):
            """Get network status overview for dashboard."""
            service = NOCDashboardService(db, tenant_id)
            return await service.get_network_status_overview()

        @router.get("/dashboard/performance")
        @require_permissions("noc:read")
        async def get_performance_metrics(
            db: Session = Depends(get_db),
            tenant_id: str = Depends(cls.get_tenant_id)
        ):
            """Get network performance metrics."""
            service = NOCDashboardService(db, tenant_id)
            return await service.get_network_performance_metrics()

        @router.get("/dashboard/devices")
        @require_permissions("noc:read")
        async def get_device_status_summary(
            limit: int = Query(50, description="Maximum devices to return"),
            include_metrics: bool = Query(True, description="Include device metrics"),
            db: Session = Depends(get_db),
            tenant_id: str = Depends(cls.get_tenant_id)
        ):
            """Get device status summary."""
            service = NOCDashboardService(db, tenant_id)
            return await service.get_device_status_summary(limit, include_metrics)

        @router.get("/dashboard/widgets")
        @require_permissions("noc:read")
        async def get_dashboard_widgets_data(
            db: Session = Depends(get_db),
            tenant_id: str = Depends(cls.get_tenant_id)
        ):
            """Get all dashboard widget data in single call."""
            service = NOCDashboardService(db, tenant_id)
            return await service.get_dashboard_widgets_data()

        # Alarm management endpoints
        @router.get("/alarms")
        @require_permissions("noc:read")
        async def get_alarms(
            status_filter: Optional[List[str]] = Query(None, description="Filter by status"),
            severity_filter: Optional[List[str]] = Query(None, description="Filter by severity"),
            device_filter: Optional[str] = Query(None, description="Filter by device"),
            customer_filter: Optional[str] = Query(None, description="Filter by customer"),
            alarm_type_filter: Optional[str] = Query(None, description="Filter by alarm type"),
            since_hours: Optional[int] = Query(None, description="Show alarms from last N hours"),
            limit: int = Query(100, description="Maximum alarms to return"),
            offset: int = Query(0, description="Pagination offset"),
            db: Session = Depends(get_db),
            tenant_id: str = Depends(cls.get_tenant_id)
        ):
            """Get filtered list of alarms."""
            service = AlarmManagementService(db, tenant_id)
            return await service.get_alarms_list(
                status_filter, severity_filter, device_filter,
                customer_filter, alarm_type_filter, since_hours, limit, offset
            )

        @router.get("/alarms/active")
        @require_permissions("noc:read")
        async def get_active_alarms(
            severity_filter: Optional[List[str]] = Query(None, description="Filter by severity"),
            limit: int = Query(100, description="Maximum alarms to return"),
            db: Session = Depends(get_db),
            tenant_id: str = Depends(cls.get_tenant_id)
        ):
            """Get active alarms for dashboard."""
            service = NOCDashboardService(db, tenant_id)
            return await service.get_active_alarms_dashboard(severity_filter, limit)

        @router.post("/alarms")
        @require_permissions("noc:write")
        async def create_alarm(
            alarm_data: AlarmCreateRequest,
            db: Session = Depends(get_db),
            tenant_id: str = Depends(cls.get_tenant_id)
        ):
            """Create new alarm."""
            service = AlarmManagementService(db, tenant_id)
            return await service.create_alarm(alarm_data.dict())

        @router.post("/alarms/{alarm_id}/acknowledge")
        @require_permissions("noc:write")
        async def acknowledge_alarm(
            alarm_id: str,
            request: AlarmUpdateRequest,
            db: Session = Depends(get_db),
            tenant_id: str = Depends(cls.get_tenant_id)
        ):
            """Acknowledge an alarm."""
            if not request.acknowledged_by:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="acknowledged_by is required"
                )
            service = AlarmManagementService(db, tenant_id)
            return await service.acknowledge_alarm(
                alarm_id, request.acknowledged_by, request.notes
            )

        @router.post("/alarms/{alarm_id}/clear")
        @require_permissions("noc:write")
        async def clear_alarm(
            alarm_id: str,
            cleared_by: str = Query(..., description="User clearing the alarm"),
            clear_reason: Optional[str] = Query(None, description="Reason for clearing"),
            db: Session = Depends(get_db),
            tenant_id: str = Depends(cls.get_tenant_id)
        ):
            """Clear an alarm."""
            service = AlarmManagementService(db, tenant_id)
            return await service.clear_alarm(alarm_id, cleared_by, clear_reason)

        @router.post("/alarms/{alarm_id}/escalate")
        @require_permissions("noc:write")
        async def escalate_alarm(
            alarm_id: str,
            new_severity: str = Query(..., description="New severity level"),
            escalated_by: str = Query(..., description="User escalating the alarm"),
            escalation_reason: Optional[str] = Query(None, description="Reason for escalation"),
            db: Session = Depends(get_db),
            tenant_id: str = Depends(cls.get_tenant_id)
        ):
            """Escalate an alarm to higher severity."""
            service = AlarmManagementService(db, tenant_id)
            return await service.escalate_alarm(
                alarm_id, new_severity, escalated_by, escalation_reason
            )

        @router.post("/alarms/{alarm_id}/suppress")
        @require_permissions("noc:write")
        async def suppress_alarm(
            alarm_id: str,
            suppressed_by: str = Query(..., description="User suppressing the alarm"),
            suppression_duration_hours: Optional[int] = Query(None, description="Suppression duration"),
            suppression_reason: Optional[str] = Query(None, description="Reason for suppression"),
            db: Session = Depends(get_db),
            tenant_id: str = Depends(cls.get_tenant_id)
        ):
            """Suppress an alarm."""
            service = AlarmManagementService(db, tenant_id)
            return await service.suppress_alarm(
                alarm_id, suppressed_by, suppression_duration_hours, suppression_reason
            )

        # Alarm rules endpoints
        @router.post("/alarm-rules")
        @require_permissions("noc:admin")
        async def create_alarm_rule(
            rule_data: AlarmRuleCreateRequest,
            db: Session = Depends(get_db),
            tenant_id: str = Depends(cls.get_tenant_id)
        ):
            """Create alarm generation rule."""
            service = AlarmManagementService(db, tenant_id)
            return await service.create_alarm_rule(rule_data.dict())

        # Event correlation endpoints
        @router.post("/events")
        @require_permissions("noc:write")
        async def process_event(
            event_data: EventProcessRequest,
            db: Session = Depends(get_db),
            tenant_id: str = Depends(cls.get_tenant_id)
        ):
            """Process incoming network event."""
            service = EventCorrelationService(db, tenant_id)
            return await service.process_incoming_event(event_data.dict())

        @router.get("/events/recent")
        @require_permissions("noc:read")
        async def get_recent_events(
            hours: int = Query(24, description="Time range in hours"),
            severity_filter: Optional[List[str]] = Query(None, description="Filter by severity"),
            limit: int = Query(100, description="Maximum events to return"),
            db: Session = Depends(get_db),
            tenant_id: str = Depends(cls.get_tenant_id)
        ):
            """Get recent network events."""
            service = NOCDashboardService(db, tenant_id)
            return await service.get_recent_events(hours, severity_filter, limit)

        @router.get("/events/patterns")
        @require_permissions("noc:read")
        async def analyze_event_patterns(
            time_window_hours: int = Query(24, description="Analysis time window"),
            min_event_count: int = Query(5, description="Minimum events for pattern analysis"),
            db: Session = Depends(get_db),
            tenant_id: str = Depends(cls.get_tenant_id)
        ):
            """Analyze event patterns and anomalies."""
            service = EventCorrelationService(db, tenant_id)
            return await service.analyze_event_patterns(time_window_hours, min_event_count)

        @router.get("/events/correlations/{correlation_id}")
        @require_permissions("noc:read")
        async def get_correlated_events(
            correlation_id: str,
            include_children: bool = Query(True, description="Include child events"),
            db: Session = Depends(get_db),
            tenant_id: str = Depends(cls.get_tenant_id)
        ):
            """Get all events in a correlation group."""
            service = EventCorrelationService(db, tenant_id)
            return await service.get_correlated_events(correlation_id, include_children)

        @router.post("/events/correlations/{correlation_id}/incident")
        @require_permissions("noc:write")
        async def create_incident_from_correlation(
            correlation_id: str,
            incident_title: str = Query(..., description="Incident title"),
            incident_description: str = Query(..., description="Incident description"),
            assigned_to: Optional[str] = Query(None, description="Assigned user"),
            db: Session = Depends(get_db),
            tenant_id: str = Depends(cls.get_tenant_id)
        ):
            """Create incident from correlated events."""
            service = EventCorrelationService(db, tenant_id)
            return await service.create_incident_from_correlation(
                correlation_id, incident_title, incident_description, assigned_to
            )

        return router


# Create the NOC router instance
noc_router = NOCRouterFactory.create_noc_router()