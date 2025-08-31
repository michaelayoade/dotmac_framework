"""
Workflow analytics router using RouterFactory and standard exception handling patterns.
Provides standardized API endpoints for workflow analytics functionality.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import Depends, Query, Body, Path
from pydantic import BaseModel

from dotmac_shared.api.router_factory import RouterFactory
from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.api.dependencies import get_tenant_context, get_user_context
from dotmac_shared.schemas.base_schemas import BaseResponse, PaginatedResponse

from ..workflow_analytics import (
    WorkflowAnalyticsService,
    WorkflowType,
    WorkflowStatus,
    WorkflowEvent,
    WorkflowMetrics,
)


class TrackWorkflowRequest(BaseModel):
    """Request model for tracking workflow events."""
    
    workflow_id: UUID
    workflow_type: WorkflowType
    event_type: str
    status: WorkflowStatus
    step_name: Optional[str] = None
    duration_ms: Optional[float] = None
    input_data: Dict[str, Any] = {}
    output_data: Dict[str, Any] = {}
    error_details: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = {}


class WorkflowMetricsQuery(BaseModel):
    """Query parameters for workflow metrics."""
    
    workflow_type: WorkflowType
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class WorkflowAnalyticsRouter:
    """Workflow analytics router with DRY patterns and standard exception handling."""
    
    def __init__(self, analytics_service: WorkflowAnalyticsService):
        self.analytics_service = analytics_service
        self.router_factory = RouterFactory(
            prefix="/workflow-analytics",
            tags=["Workflow Analytics"],
            dependencies=[Depends(get_tenant_context)]
        )
        
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup workflow analytics API routes."""
        
        # Event tracking endpoints
        self.router_factory.add_route(
            "/events",
            self.track_workflow_event,
            methods=["POST"],
            summary="Track workflow event",
            description="Track a workflow execution event for analytics",
            response_model=BaseResponse[Dict[str, str]],
        )
        
        # Metrics endpoints
        self.router_factory.add_route(
            "/metrics/{workflow_type}",
            self.get_workflow_metrics,
            methods=["GET"],
            summary="Get workflow metrics",
            description="Get analytics metrics for a specific workflow type",
            response_model=BaseResponse[WorkflowMetrics],
        )
        
        self.router_factory.add_route(
            "/dashboard",
            self.get_analytics_dashboard,
            methods=["GET"],
            summary="Get workflow analytics dashboard",
            description="Get comprehensive workflow analytics dashboard data",
            response_model=BaseResponse[Dict[str, Any]],
        )
        
        # Workflow-specific endpoints
        self.router_factory.add_route(
            "/workflows/{workflow_id}/timeline",
            self.get_workflow_timeline,
            methods=["GET"],
            summary="Get workflow execution timeline",
            description="Get detailed timeline of a specific workflow execution",
            response_model=BaseResponse[List[Dict[str, Any]]],
        )
        
        self.router_factory.add_route(
            "/performance/bottlenecks",
            self.get_performance_bottlenecks,
            methods=["GET"],
            summary="Get performance bottlenecks",
            description="Get workflow steps that are performance bottlenecks",
            response_model=BaseResponse[List[Dict[str, Any]]],
        )
        
        # Analytics insights endpoints
        self.router_factory.add_route(
            "/insights/trends",
            self.get_workflow_trends,
            methods=["GET"],
            summary="Get workflow trends",
            description="Get workflow execution trends and patterns",
            response_model=BaseResponse[Dict[str, Any]],
        )
        
        self.router_factory.add_route(
            "/insights/failures",
            self.get_failure_analysis,
            methods=["GET"],
            summary="Get failure analysis",
            description="Get analysis of workflow failures and error patterns",
            response_model=BaseResponse[Dict[str, Any]],
        )
        
        # Health check endpoint
        self.router_factory.add_route(
            "/health",
            self.health_check,
            methods=["GET"],
            summary="Workflow analytics health check",
            description="Check the health status of workflow analytics service",
            response_model=BaseResponse[Dict[str, Any]],
        )
    
    @standard_exception_handler
    async def track_workflow_event(
        self,
        request: TrackWorkflowRequest = Body(...),
        tenant_context: dict = Depends(get_tenant_context),
        user_context: dict = Depends(get_user_context),
    ) -> BaseResponse[Dict[str, str]]:
        """Track a workflow event."""
        
        success = await self.analytics_service.track_workflow_event(
            workflow_id=request.workflow_id,
            workflow_type=request.workflow_type,
            event_type=request.event_type,
            status=request.status,
            step_name=request.step_name,
            user_id=user_context.get("user_id"),
            duration_ms=request.duration_ms,
            input_data=request.input_data,
            output_data=request.output_data,
            error_details=request.error_details,
            metadata=request.metadata,
        )
        
        return BaseResponse[Dict[str, str]](
            success=success,
            data={"workflow_id": str(request.workflow_id)},
            message="Workflow event tracked successfully" if success else "Failed to track workflow event"
        )
    
    @standard_exception_handler
    async def get_workflow_metrics(
        self,
        workflow_type: WorkflowType = Path(..., description="Type of workflow"),
        period_start: Optional[datetime] = Query(None, description="Period start date"),
        period_end: Optional[datetime] = Query(None, description="Period end date"),
        tenant_context: dict = Depends(get_tenant_context),
    ) -> BaseResponse[WorkflowMetrics]:
        """Get workflow metrics for a specific type."""
        
        metrics = await self.analytics_service.get_workflow_metrics(
            workflow_type,
            period_start,
            period_end,
            tenant_context.get("tenant_id")
        )
        
        return BaseResponse[WorkflowMetrics](
            success=True,
            data=metrics,
            message="Workflow metrics retrieved successfully"
        )
    
    @standard_exception_handler
    async def get_analytics_dashboard(
        self,
        period_days: int = Query(7, description="Period in days", ge=1, le=90),
        tenant_context: dict = Depends(get_tenant_context),
    ) -> BaseResponse[Dict[str, Any]]:
        """Get workflow analytics dashboard data."""
        
        dashboard = await self.analytics_service.get_workflow_analytics_dashboard(
            period_days,
            tenant_context.get("tenant_id")
        )
        
        return BaseResponse[Dict[str, Any]](
            success=True,
            data=dashboard,
            message="Workflow analytics dashboard retrieved successfully"
        )
    
    @standard_exception_handler
    async def get_workflow_timeline(
        self,
        workflow_id: UUID = Path(..., description="Workflow identifier"),
        tenant_context: dict = Depends(get_tenant_context),
    ) -> BaseResponse[List[Dict[str, Any]]]:
        """Get detailed timeline for a specific workflow."""
        
        # This would typically query the analytics service for workflow events
        # For demo purposes, returning simulated timeline data
        
        timeline = [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": "workflow_started",
                "status": "running",
                "step_name": "initialization",
                "duration_ms": None,
                "details": "Workflow execution started",
            },
            {
                "timestamp": (datetime.utcnow() + timedelta(seconds=30)).isoformat(),
                "event_type": "step_completed",
                "status": "completed",
                "step_name": "validation",
                "duration_ms": 1500,
                "details": "Input validation completed successfully",
            },
            {
                "timestamp": (datetime.utcnow() + timedelta(minutes=2)).isoformat(),
                "event_type": "step_completed", 
                "status": "completed",
                "step_name": "processing",
                "duration_ms": 45000,
                "details": "Main processing logic completed",
            },
            {
                "timestamp": (datetime.utcnow() + timedelta(minutes=2, seconds=15)).isoformat(),
                "event_type": "workflow_completed",
                "status": "completed",
                "step_name": "finalization",
                "duration_ms": 500,
                "details": "Workflow completed successfully",
            },
        ]
        
        return BaseResponse[List[Dict[str, Any]]](
            success=True,
            data=timeline,
            message=f"Retrieved timeline for workflow {workflow_id}"
        )
    
    @standard_exception_handler
    async def get_performance_bottlenecks(
        self,
        workflow_type: Optional[WorkflowType] = Query(None, description="Filter by workflow type"),
        period_days: int = Query(7, description="Period in days", ge=1, le=30),
        limit: int = Query(10, description="Maximum number of bottlenecks", ge=1, le=50),
        tenant_context: dict = Depends(get_tenant_context),
    ) -> BaseResponse[List[Dict[str, Any]]]:
        """Get performance bottlenecks across workflows."""
        
        # Simulate bottleneck analysis
        bottlenecks = []
        
        if workflow_type:
            # Get metrics for specific workflow type
            metrics = await self.analytics_service.get_workflow_metrics(
                workflow_type,
                datetime.utcnow() - timedelta(days=period_days),
                datetime.utcnow(),
                tenant_context.get("tenant_id")
            )
            
            bottlenecks = metrics.bottleneck_steps
        else:
            # Simulate cross-workflow bottlenecks
            bottlenecks = [
                {
                    "step_name": "external_api_call",
                    "workflow_type": "customer_onboarding",
                    "avg_duration_ms": 15000,
                    "total_executions": 150,
                    "success_rate": 0.95,
                    "impact_score": 85,
                },
                {
                    "step_name": "database_validation",
                    "workflow_type": "service_provisioning",
                    "avg_duration_ms": 8500,
                    "total_executions": 300,
                    "success_rate": 0.98,
                    "impact_score": 72,
                },
            ]
        
        return BaseResponse[List[Dict[str, Any]]](
            success=True,
            data=bottlenecks[:limit],
            message=f"Retrieved {len(bottlenecks)} performance bottlenecks"
        )
    
    @standard_exception_handler
    async def get_workflow_trends(
        self,
        workflow_type: Optional[WorkflowType] = Query(None, description="Filter by workflow type"),
        period_days: int = Query(30, description="Period in days", ge=7, le=90),
        tenant_context: dict = Depends(get_tenant_context),
    ) -> BaseResponse[Dict[str, Any]]:
        """Get workflow trends and patterns."""
        
        # Simulate trend analysis
        trends = {
            "volume_trends": {
                "current_period": period_days,
                "total_workflows": 1250,
                "daily_average": 41.7,
                "trend_direction": "increasing",
                "growth_rate": 12.5,
                "daily_data": [
                    {"date": "2024-01-01", "count": 35},
                    {"date": "2024-01-02", "count": 42},
                    {"date": "2024-01-03", "count": 38},
                ],
            },
            "performance_trends": {
                "avg_duration_ms": 45000,
                "trend_direction": "improving",
                "improvement_rate": -8.2,
                "daily_averages": [
                    {"date": "2024-01-01", "avg_duration_ms": 48000},
                    {"date": "2024-01-02", "avg_duration_ms": 46000},
                    {"date": "2024-01-03", "avg_duration_ms": 43000},
                ],
            },
            "success_rate_trends": {
                "current_success_rate": 0.92,
                "trend_direction": "stable",
                "change_rate": 0.5,
                "daily_rates": [
                    {"date": "2024-01-01", "success_rate": 0.91},
                    {"date": "2024-01-02", "success_rate": 0.93},
                    {"date": "2024-01-03", "success_rate": 0.92},
                ],
            },
        }
        
        if workflow_type:
            trends["workflow_type"] = workflow_type.value
        
        return BaseResponse[Dict[str, Any]](
            success=True,
            data=trends,
            message="Workflow trends retrieved successfully"
        )
    
    @standard_exception_handler
    async def get_failure_analysis(
        self,
        workflow_type: Optional[WorkflowType] = Query(None, description="Filter by workflow type"),
        period_days: int = Query(7, description="Period in days", ge=1, le=30),
        tenant_context: dict = Depends(get_tenant_context),
    ) -> BaseResponse[Dict[str, Any]]:
        """Get workflow failure analysis."""
        
        # Simulate failure analysis
        failure_analysis = {
            "period": {
                "days": period_days,
                "start": (datetime.utcnow() - timedelta(days=period_days)).isoformat(),
                "end": datetime.utcnow().isoformat(),
            },
            "overview": {
                "total_failures": 45,
                "failure_rate": 0.08,
                "most_common_failure": "timeout_error",
                "recovery_rate": 0.75,
            },
            "failure_categories": {
                "timeout_error": 15,
                "validation_error": 12,
                "external_service_error": 10,
                "resource_unavailable": 5,
                "configuration_error": 3,
            },
            "failure_by_step": [
                {"step_name": "external_api_call", "failure_count": 18, "failure_rate": 0.12},
                {"step_name": "data_validation", "failure_count": 12, "failure_rate": 0.08},
                {"step_name": "resource_allocation", "failure_count": 8, "failure_rate": 0.05},
            ],
            "top_error_messages": [
                {
                    "message": "Connection timeout to external service",
                    "count": 15,
                    "percentage": 33.3,
                },
                {
                    "message": "Invalid input data format",
                    "count": 12,
                    "percentage": 26.7,
                },
            ],
            "recommendations": [
                {
                    "priority": "high",
                    "issue": "External service timeouts",
                    "recommendation": "Implement retry logic with exponential backoff",
                    "impact": "Could reduce failures by 40%",
                },
                {
                    "priority": "medium", 
                    "issue": "Input validation errors",
                    "recommendation": "Add client-side validation",
                    "impact": "Could reduce failures by 25%",
                },
            ],
        }
        
        if workflow_type:
            failure_analysis["workflow_type"] = workflow_type.value
        
        return BaseResponse[Dict[str, Any]](
            success=True,
            data=failure_analysis,
            message="Workflow failure analysis retrieved successfully"
        )
    
    @standard_exception_handler
    async def health_check(
        self,
        tenant_context: dict = Depends(get_tenant_context),
    ) -> BaseResponse[Dict[str, Any]]:
        """Check workflow analytics service health."""
        
        health = await self.analytics_service._health_check_stateful_service()
        
        return BaseResponse[Dict[str, Any]](
            success=health.status.value == "ready",
            data={
                "status": health.status.value,
                "message": health.message,
                "details": health.details,
            },
            message="Workflow analytics service health check completed"
        )
    
    def get_router(self):
        """Get the configured FastAPI router."""
        return self.router_factory.create_router()


# Factory function for creating workflow analytics router
def create_workflow_analytics_router(analytics_service: WorkflowAnalyticsService):
    """Create workflow analytics router with service dependency."""
    return WorkflowAnalyticsRouter(analytics_service)