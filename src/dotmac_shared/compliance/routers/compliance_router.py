"""
Compliance router using RouterFactory and standard exception handling patterns.
Provides standardized API endpoints for compliance functionality.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import Depends, Query, Body
from pydantic import BaseModel

from dotmac_shared.api.router_factory import RouterFactory
from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.api.dependencies import get_tenant_context, get_user_context
from dotmac_shared.schemas.base_schemas import BaseResponse, PaginatedResponse

from ..services.compliance_service import ComplianceService
from ..schemas.compliance_schemas import (
    ComplianceFramework,
    ComplianceEvent,
    ComplianceReportRequest,
    RegulatoryReport,
    ComplianceMetrics,
    ComplianceAlert,
    ComplianceStatus,
    AuditEventType,
    RiskLevel,
)


class ComplianceEventRequest(BaseModel):
    """Request model for compliance event tracking."""
    
    event_type: AuditEventType
    framework: ComplianceFramework
    resource_id: Optional[str] = None
    resource_type: Optional[str] = None
    user_id: Optional[UUID] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    risk_level: RiskLevel = RiskLevel.LOW
    details: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}


class ComplianceCheckRequest(BaseModel):
    """Request model for compliance checks."""
    
    framework: ComplianceFramework
    resource_id: str
    resource_type: str
    context: Dict[str, Any] = {}


class ScheduleReportRequest(BaseModel):
    """Request model for scheduling reports."""
    
    framework: ComplianceFramework
    report_type: str
    frequency: str
    recipients: List[str]


class ComplianceRouter:
    """Compliance router with DRY patterns and standard exception handling."""
    
    def __init__(self, compliance_service: ComplianceService):
        self.compliance_service = compliance_service
        self.router_factory = RouterFactory(
            prefix="/compliance",
            tags=["Compliance"],
            dependencies=[Depends(get_tenant_context)]
        )
        
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup compliance API routes."""
        
        # Event tracking endpoints
        self.router_factory.add_route(
            "/events",
            self.track_compliance_event,
            methods=["POST"],
            summary="Track compliance event",
            description="Record a compliance event for audit and monitoring",
            response_model=BaseResponse[Dict[str, str]],
        )
        
        # Report generation endpoints
        self.router_factory.add_route(
            "/reports/generate",
            self.generate_report,
            methods=["POST"],
            summary="Generate compliance report",
            description="Generate a regulatory compliance report",
            response_model=BaseResponse[Dict[str, Any]],
        )
        
        self.router_factory.add_route(
            "/reports/schedule",
            self.schedule_report,
            methods=["POST"],
            summary="Schedule compliance report",
            description="Schedule automatic compliance report generation",
            response_model=BaseResponse[Dict[str, str]],
        )
        
        # Metrics and analytics endpoints
        self.router_factory.add_route(
            "/metrics/{framework}",
            self.get_compliance_metrics,
            methods=["GET"],
            summary="Get compliance metrics",
            description="Get compliance metrics for a specific framework",
            response_model=BaseResponse[ComplianceMetrics],
        )
        
        self.router_factory.add_route(
            "/dashboard",
            self.get_compliance_dashboard,
            methods=["GET"],
            summary="Get compliance dashboard",
            description="Get comprehensive compliance dashboard data",
            response_model=BaseResponse[Dict[str, Any]],
        )
        
        # Alert management endpoints
        self.router_factory.add_route(
            "/alerts",
            self.get_active_alerts,
            methods=["GET"],
            summary="Get active compliance alerts",
            description="Get list of active compliance alerts",
            response_model=BaseResponse[List[Dict[str, Any]]],
        )
        
        # Compliance checks endpoints
        self.router_factory.add_route(
            "/checks",
            self.perform_compliance_check,
            methods=["POST"],
            summary="Perform compliance check",
            description="Perform compliance checks for a resource",
            response_model=BaseResponse[List[Dict[str, Any]]],
        )
        
        # Health check endpoint
        self.router_factory.add_route(
            "/health",
            self.health_check,
            methods=["GET"],
            summary="Compliance service health check",
            description="Check the health status of compliance service",
            response_model=BaseResponse[Dict[str, Any]],
        )
    
    @standard_exception_handler
    async def track_compliance_event(
        self,
        request: ComplianceEventRequest = Body(...),
        tenant_context: dict = Depends(get_tenant_context),
        user_context: dict = Depends(get_user_context),
    ) -> BaseResponse[Dict[str, str]]:
        """Track a compliance event."""
        
        # Create compliance event from request
        compliance_event = ComplianceEvent(
            event_id=UUID("00000000-0000-0000-0000-000000000000"),  # Will be generated
            event_type=request.event_type,
            framework=request.framework,
            resource_id=request.resource_id,
            resource_type=request.resource_type,
            user_id=request.user_id or user_context.get("user_id"),
            session_id=request.session_id or user_context.get("session_id"),
            ip_address=request.ip_address or user_context.get("ip_address"),
            user_agent=request.user_agent or user_context.get("user_agent"),
            risk_level=request.risk_level,
            details=request.details,
            metadata=request.metadata,
            tenant_id=tenant_context.get("tenant_id"),
        )
        
        # Track the event
        success = await self.compliance_service.record_compliance_event(compliance_event)
        
        return BaseResponse[Dict[str, str]](
            success=success,
            data={"event_id": str(compliance_event.event_id)},
            message="Compliance event tracked successfully" if success else "Failed to track compliance event"
        )
    
    @standard_exception_handler
    async def generate_report(
        self,
        request: ComplianceReportRequest = Body(...),
        tenant_context: dict = Depends(get_tenant_context),
        user_context: dict = Depends(get_user_context),
    ) -> BaseResponse[Dict[str, Any]]:
        """Generate a compliance report."""
        
        # Set tenant ID if not provided
        if not request.tenant_id and tenant_context.get("tenant_id"):
            request.tenant_id = UUID(tenant_context["tenant_id"])
        
        # Generate the report
        report = await self.compliance_service.generate_compliance_report(
            request,
            user_context.get("user_id")
        )
        
        return BaseResponse[Dict[str, Any]](
            success=True,
            data={
                "report_id": str(report.report_id),
                "name": report.name,
                "framework": report.framework.value,
                "status": report.compliance_status.value,
                "score": report.compliance_score,
                "generated_at": report.generated_at.isoformat(),
                "executive_summary": report.executive_summary,
                "findings_count": len(report.findings),
                "recommendations_count": len(report.recommendations),
            },
            message="Compliance report generated successfully"
        )
    
    @standard_exception_handler
    async def schedule_report(
        self,
        request: ScheduleReportRequest = Body(...),
        tenant_context: dict = Depends(get_tenant_context),
        user_context: dict = Depends(get_user_context),
    ) -> BaseResponse[Dict[str, str]]:
        """Schedule automatic report generation."""
        
        schedule_id = await self.compliance_service.schedule_report(
            request.framework,
            request.report_type,
            request.frequency,
            request.recipients,
            user_context.get("user_id")
        )
        
        return BaseResponse[Dict[str, str]](
            success=True,
            data={"schedule_id": schedule_id},
            message="Report scheduled successfully"
        )
    
    @standard_exception_handler
    async def get_compliance_metrics(
        self,
        framework: ComplianceFramework,
        period_start: Optional[datetime] = Query(None, description="Period start date"),
        period_end: Optional[datetime] = Query(None, description="Period end date"),
        tenant_context: dict = Depends(get_tenant_context),
    ) -> BaseResponse[ComplianceMetrics]:
        """Get compliance metrics for a framework."""
        
        metrics = await self.compliance_service.get_compliance_metrics(
            framework,
            period_start,
            period_end
        )
        
        return BaseResponse[ComplianceMetrics](
            success=True,
            data=metrics,
            message="Compliance metrics retrieved successfully"
        )
    
    @standard_exception_handler
    async def get_compliance_dashboard(
        self,
        frameworks: Optional[List[ComplianceFramework]] = Query(None, description="Frameworks to include"),
        period_days: int = Query(30, description="Period in days", ge=1, le=365),
        tenant_context: dict = Depends(get_tenant_context),
    ) -> BaseResponse[Dict[str, Any]]:
        """Get compliance dashboard data."""
        
        dashboard = await self.compliance_service.get_compliance_dashboard(
            frameworks,
            period_days
        )
        
        return BaseResponse[Dict[str, Any]](
            success=True,
            data=dashboard,
            message="Compliance dashboard data retrieved successfully"
        )
    
    @standard_exception_handler
    async def get_active_alerts(
        self,
        framework: Optional[ComplianceFramework] = Query(None, description="Filter by framework"),
        tenant_context: dict = Depends(get_tenant_context),
    ) -> BaseResponse[List[Dict[str, Any]]]:
        """Get active compliance alerts."""
        
        alerts = await self.compliance_service.get_active_alerts(framework)
        
        # Format alerts for API response
        formatted_alerts = []
        for alert in alerts:
            formatted_alerts.append({
                "alert_id": str(alert.alert_id),
                "framework": alert.framework.value,
                "severity": alert.severity.value,
                "title": alert.title,
                "description": alert.description,
                "resource_affected": alert.resource_affected,
                "status": alert.status,
                "triggered_at": alert.triggered_at.isoformat(),
                "remediation": alert.remediation,
            })
        
        return BaseResponse[List[Dict[str, Any]]](
            success=True,
            data=formatted_alerts,
            message=f"Retrieved {len(formatted_alerts)} active compliance alerts"
        )
    
    @standard_exception_handler
    async def perform_compliance_check(
        self,
        request: ComplianceCheckRequest = Body(...),
        tenant_context: dict = Depends(get_tenant_context),
        user_context: dict = Depends(get_user_context),
    ) -> BaseResponse[List[Dict[str, Any]]]:
        """Perform compliance checks for a resource."""
        
        results = await self.compliance_service.perform_compliance_check(
            request.framework,
            request.resource_id,
            request.resource_type,
            request.context
        )
        
        return BaseResponse[List[Dict[str, Any]]](
            success=True,
            data=results,
            message=f"Performed {len(results)} compliance checks"
        )
    
    @standard_exception_handler
    async def health_check(
        self,
        tenant_context: dict = Depends(get_tenant_context),
    ) -> BaseResponse[Dict[str, Any]]:
        """Check compliance service health."""
        
        health = await self.compliance_service._health_check_stateful_service()
        
        return BaseResponse[Dict[str, Any]](
            success=health.status.value == "ready",
            data={
                "status": health.status.value,
                "message": health.message,
                "details": health.details,
            },
            message="Compliance service health check completed"
        )
    
    def get_router(self):
        """Get the configured FastAPI router."""
        return self.router_factory.create_router()


# Factory function for creating compliance router
def create_compliance_router(compliance_service: ComplianceService):
    """Create compliance router with service dependency."""
    return ComplianceRouter(compliance_service)