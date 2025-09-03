"""Analytics API router with comprehensive endpoints for metrics, reports, dashboards and alerts."""

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import \1, Dependsndsses import StreamingResponse

from dotmac_shared.api.dependencies import (
    StandardDependencies,
    PaginatedDependencies,
    SearchParams,
    get_standard_deps,
    get_paginated_deps,
    get_admin_deps

from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.api.router_factory import RouterFactory

from .schemas import (
    AlertCreate,
    AlertResponse,
    AlertTestRequest,
    AlertTestResponse,
    AlertUpdate,
    AnalyticsOverviewResponse,
    CustomerAnalyticsResponse,
    DashboardCreate,
    DashboardMetricsResponse,
    DashboardOverviewResponse,
    DashboardResponse,
    DashboardUpdate,
    DataSourceCreate,
    DataSourceResponse,
    DataSourceUpdate,
    ExecutiveReportResponse,
    MetricAggregationRequest,
    MetricAggregationResponse,
    MetricCreate,
    MetricResponse,
    MetricUpdate,
    MetricValueCreate,
    MetricValueResponse,
    RealTimeMetricsResponse,
    ReportCreate,
    ReportExportRequest,
    ReportExportResponse,
    ReportResponse,
    ReportUpdate,
    RevenueAnalyticsResponse,
    ServiceAnalyticsResponse,
    WidgetCreate,
    WidgetResponse,
    WidgetUpdate,
)
from .service import (
    AlertService,
    AnalyticsService,
    DashboardService,
    MetricService,
    ReportService,
    WidgetService,
)

# === MAIN ANALYTICS ROUTER ===
router = RouterFactory.create_readonly_router(
    service_class=AnalyticsService,
    response_schema=AnalyticsOverviewResponse,
    prefix="",
    tags=["analytics"],
    enable_search=False,
)

# === METRICS MANAGEMENT ===
metrics_router = RouterFactory.create_crud_router(
    service_class=MetricService,
    create_schema=MetricCreate,
    update_schema=MetricUpdate,
    response_schema=MetricResponse,
    prefix="/metrics",
    tags=["analytics", "metrics"],
    enable_search=True,
    enable_bulk_operations=True,
)

# === REPORTS MANAGEMENT ===
reports_router = RouterFactory.create_crud_router(
    service_class=ReportService,
    create_schema=ReportCreate,
    update_schema=ReportUpdate,
    response_schema=ReportResponse,
    prefix="/reports",
    tags=["analytics", "reports"],
    enable_search=True,
    enable_bulk_operations=True,
)

# === DASHBOARDS MANAGEMENT ===
dashboards_router = RouterFactory.create_crud_router(
    service_class=DashboardService,
    create_schema=DashboardCreate,
    update_schema=DashboardUpdate,
    response_schema=DashboardResponse,
    prefix="/dashboards",
    tags=["analytics", "dashboards"],
    enable_search=True,
    enable_bulk_operations=True,
)

# === WIDGETS MANAGEMENT ===
widgets_router = RouterFactory.create_crud_router(
    service_class=WidgetService,
    create_schema=WidgetCreate,
    update_schema=WidgetUpdate,
    response_schema=WidgetResponse,
    prefix="/widgets",
    tags=["analytics", "widgets"],
    enable_search=True,
    enable_bulk_operations=True,
)

# === ALERTS MANAGEMENT ===
alerts_router = RouterFactory.create_crud_router(
    service_class=AlertService,
    create_schema=AlertCreate,
    update_schema=AlertUpdate,
    response_schema=AlertResponse,
    prefix="/alerts",
    tags=["analytics", "alerts"],
    enable_search=True,
    enable_bulk_operations=True,
)

# Include all sub-routers
router.include_router(metrics_router)
router.include_router(reports_router)
router.include_router(dashboards_router)
router.include_router(widgets_router)
router.include_router(alerts_router)

# === ANALYTICS OVERVIEW AND DASHBOARD ===

@router.get("/overview", response_model=AnalyticsOverviewResponse)
@standard_exception_handler
async def get_analytics_overview(deps: StandardDependencies = Depends(get_standard_deps)) -> AnalyticsOverviewResponse:
    """Get comprehensive analytics overview with key metrics and activity."""
    service = AnalyticsService(deps.db, deps.tenant_id)
    return await service.get_analytics_overview(deps.user_id)

@router.get("/dashboard", response_model=DashboardOverviewResponse)
@standard_exception_handler
async def get_dashboard_overview(deps: StandardDependencies = Depends(get_standard_deps)) -> DashboardOverviewResponse:
    """Get main dashboard overview with key business metrics."""
    service = DashboardService(deps.db, deps.tenant_id)
    return await service.get_dashboard_overview(deps.user_id)

@router.get("/realtime", response_model=RealTimeMetricsResponse)
@standard_exception_handler
async def get_real_time_metrics(deps: StandardDependencies = Depends(get_standard_deps)) -> RealTimeMetricsResponse:
    """Get real-time system metrics and performance data."""
    service = AnalyticsService(deps.db, deps.tenant_id)
    return await service.get_real_time_metrics(deps.user_id)

# === METRIC VALUE OPERATIONS ===

@router.post("/metrics/{metric_id}/values", response_model=MetricValueResponse)
@standard_exception_handler
async def record_metric_value(
    metric_id: UUID, 
    data: MetricValueCreate, 
    deps: StandardDependencies = Depends(get_standard_deps)
) -> MetricValueResponse:
    """Record a new value for a specific metric."""
    service = MetricService(deps.db, deps.tenant_id)
    return await service.record_metric_value(metric_id, data, deps.user_id)

@router.get("/metrics/{metric_id}/values", response_model=List[MetricValueResponse])
@standard_exception_handler
async def get_metric_values(
    metric_id: UUID,
    deps: StandardDependencies = Depends(get_standard_deps),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum values to return")
) -> List[MetricValueResponse]:
    """Get values for a specific metric within date range."""
    from datetime import datetime
    
    start_dt = datetime.fromisoformat(start_date, timezone) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None
    
    service = MetricService(deps.db, deps.tenant_id)
    return await service.get_metric_values(metric_id, start_dt, end_dt, limit)

@router.get("/metrics/{metric_id}/statistics")
@standard_exception_handler
async def get_metric_statistics(
    metric_id: UUID,
    deps: StandardDependencies = Depends(get_standard_deps),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)")
) -> Dict[str, Any]:
    """Get statistical summary for a metric."""
    from datetime import datetime
    
    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None
    
    service = MetricService(deps.db, deps.tenant_id)
    return await service.get_metric_statistics(metric_id, start_dt, end_dt)

@router.post("/metrics/aggregate", response_model=MetricAggregationResponse)
@standard_exception_handler
async def aggregate_metrics(
    request: MetricAggregationRequest,
    deps: StandardDependencies = Depends(get_standard_deps)
) -> MetricAggregationResponse:
    """Aggregate metric data for analysis and reporting."""
    service = MetricService(deps.db, deps.tenant_id)
    return await service.aggregate_metrics(request)

# === REPORT OPERATIONS ===

@router.post("/reports/{report_id}/generate", response_model=ReportResponse)
@standard_exception_handler
async def generate_report(
    report_id: UUID,
    deps: StandardDependencies = Depends(get_standard_deps)
) -> ReportResponse:
    """Generate data for an existing report definition."""
    service = ReportService(deps.db, deps.tenant_id)
    return await service.generate_report_data(report_id, deps.user_id)

@router.post("/reports/export", response_model=ReportExportResponse)
@standard_exception_handler
async def export_report(
    request: ReportExportRequest,
    deps: StandardDependencies = Depends(get_standard_deps)
) -> ReportExportResponse:
    """Export a report in the specified format (JSON, CSV, PDF, Excel)."""
    service = ReportService(deps.db, deps.tenant_id)
    return await service.export_report(request, deps.user_id)

@router.get("/reports/executive", response_model=ExecutiveReportResponse)
@standard_exception_handler
async def generate_executive_report(deps: StandardDependencies = Depends(get_standard_deps)) -> ExecutiveReportResponse:
    """Generate comprehensive executive report with strategic insights."""
    service = AnalyticsService(deps.db, deps.tenant_id)
    return await service.generate_executive_report(deps.user_id)

# === DASHBOARD OPERATIONS ===

@router.get("/dashboards/{dashboard_id}/full")
@standard_exception_handler
async def get_dashboard_with_widgets(
    dashboard_id: UUID,
    deps: StandardDependencies = Depends(get_standard_deps)
) -> Dict[str, Any]:
    """Get complete dashboard with all widgets and data."""
    service = DashboardService(deps.db, deps.tenant_id)
    return await service.get_dashboard_with_widgets(dashboard_id)

@router.get("/dashboards/{dashboard_id}/metrics", response_model=DashboardMetricsResponse)
@standard_exception_handler
async def get_dashboard_metrics(
    dashboard_id: UUID,
    deps: StandardDependencies = Depends(get_standard_deps)
) -> DashboardMetricsResponse:
    """Get usage metrics and analytics for a specific dashboard."""
    service = DashboardService(deps.db, deps.tenant_id)
    return await service.get_dashboard_metrics(dashboard_id)

# === WIDGET OPERATIONS ===

@router.get("/dashboards/{dashboard_id}/widgets", response_model=List[WidgetResponse])
@standard_exception_handler
async def get_dashboard_widgets(
    dashboard_id: UUID,
    deps: StandardDependencies = Depends(get_standard_deps)
) -> List[WidgetResponse]:
    """Get all widgets for a specific dashboard."""
    service = WidgetService(deps.db, deps.tenant_id)
    return await service.get_widgets_by_dashboard(dashboard_id)

@router.post("/dashboards/{dashboard_id}/widgets/reorder")
@standard_exception_handler
async def reorder_dashboard_widgets(
    dashboard_id: UUID,
    widget_positions: Dict[str, int],
    deps: StandardDependencies = Depends(get_standard_deps)
) -> Dict[str, bool]:
    """Reorder widgets within a dashboard."""
    service = WidgetService(deps.db, deps.tenant_id)
    success = await service.reorder_widgets(dashboard_id, widget_positions, deps.user_id)
    return {"success": success}

# === ALERT OPERATIONS ===

@router.post("/alerts/{alert_id}/test", response_model=AlertTestResponse)
@standard_exception_handler
async def test_alert_condition(
    alert_id: UUID,
    request: AlertTestRequest,
    deps: StandardDependencies = Depends(get_standard_deps)
) -> AlertTestResponse:
    """Test an alert condition with a specific value."""
    service = AlertService(deps.db, deps.tenant_id)
    return await service.test_alert(alert_id, request.test_value)

@router.post("/alerts/check")
@standard_exception_handler
async def check_all_alert_conditions(deps: StandardDependencies = Depends(get_standard_deps)) -> Dict[str, Any]:
    """Check all active alerts against current metric values."""
    service = AlertService(deps.db, deps.tenant_id)
    triggered_alerts = await service.check_alert_conditions(deps.user_id)
    
    return {
        "timestamp": deps.current_time.isoformat(),
        "total_alerts_checked": len(triggered_alerts),
        "triggered_alerts": triggered_alerts
    }

# === ANALYTICS ENDPOINTS ===

@router.get("/analytics/customer/{customer_id}", response_model=CustomerAnalyticsResponse)
@standard_exception_handler
async def get_customer_analytics(
    customer_id: UUID,
    deps: StandardDependencies = Depends(get_standard_deps),
    months: int = Query(12, ge=1, le=36, description="Number of months to analyze")
) -> CustomerAnalyticsResponse:
    """Get comprehensive analytics for a specific customer."""
    from datetime import datetime, timedelta
    
    # Mock implementation - replace with actual service call
    return CustomerAnalyticsResponse(
        customer_id=str(customer_id),
        total_revenue=1250.00,
        monthly_recurring_revenue=125.00,
        lifetime_value=2400.00,
        service_count=3,
        support_tickets=2,
        payment_history={
            "total_payments": 12,
            "late_payments": 0,
            "average_payment_time": 5.2
        },
        usage_metrics={
            "data_usage_gb": 450.5,
            "bandwidth_avg_mbps": 50.2,
            "uptime_percentage": 99.5
        },
        churn_risk_score=15.3,
        satisfaction_score=4.2,
        acquisition_date=datetime.now(timezone.utc) - timedelta(days=365),
        last_activity=datetime.now(timezone.utc) - timedelta(hours=6)
    )

@router.get("/analytics/revenue", response_model=RevenueAnalyticsResponse)
@standard_exception_handler
async def get_revenue_analytics(
    deps: StandardDependencies = Depends(get_standard_deps),
    months: int = Query(12, ge=1, le=36, description="Number of months to analyze")
) -> RevenueAnalyticsResponse:
    """Get comprehensive revenue analytics and forecasting."""
    from datetime import datetime, timedelta
    
    current_time = datetime.now(timezone.utc)
    start_time = current_time - timedelta(days=30 * months)
    
    # Mock implementation - replace with actual service call
    return RevenueAnalyticsResponse(
        period_start=start_time,
        period_end=current_time,
        total_revenue=125670.50,
        recurring_revenue=98450.00,
        one_time_revenue=27220.50,
        growth_rate=12.5,
        average_revenue_per_user=78.90,
        revenue_by_service={
            "internet": 75000.00,
            "phone": 35000.00,
            "tv": 15670.50
        },
        revenue_by_region={
            "north": 45000.00,
            "south": 38000.00,
            "east": 25670.50,
            "west": 17000.00
        },
        top_customers=[
            {
                "customer_id": "cust-001",
                "name": "Business Corp",
                "revenue": 5670.00,
                "percentage": 4.5
            }
        ],
        churn_impact=-2450.00,
        forecasted_revenue=135000.00
    )

@router.get("/analytics/services/{service_id}", response_model=ServiceAnalyticsResponse)
@standard_exception_handler
async def get_service_analytics(
    service_id: str,
    deps: StandardDependencies = Depends(get_standard_deps),
    period: str = Query("monthly", pattern=r"^(daily|weekly|monthly|quarterly)$"),
    months: int = Query(3, ge=1, le=12, description="Number of months to analyze")
) -> ServiceAnalyticsResponse:
    """Get detailed analytics for a specific service offering."""
    from datetime import datetime, timedelta
    
    current_time = datetime.now(timezone.utc)
    start_time = current_time - timedelta(days=30 * months)
    
    # Mock implementation - replace with actual service call
    return ServiceAnalyticsResponse(
        service_id=service_id,
        service_name=f"Service {service_id}",
        metrics={
            "active_customers": 450,
            "usage_metrics": {
                "data_consumption_gb": 12450.5,
                "peak_usage_hour": 20,
                "avg_session_duration": 145.2
            },
            "performance_metrics": {
                "uptime_percentage": 99.7,
                "response_time_ms": 125.4,
                "error_rate": 0.02
            }
        },
        period=period,
        period_start=start_time,
        period_end=current_time,
        total_customers=450,
        revenue=45670.00,
        uptime_percentage=99.7
    )

# === DATA SOURCE MANAGEMENT ===

data_sources_router = RouterFactory.create_crud_router(
    service_class=None,
    create_schema=DataSourceCreate,
    update_schema=DataSourceUpdate,
    response_schema=DataSourceResponse,
    prefix="/data-sources",
    tags=["analytics", "data-sources"],
    enable_search=True,
    enable_bulk_operations=True,
)

router.include_router(data_sources_router)

@router.post("/data-sources/{source_id}/sync")
@standard_exception_handler
async def sync_data_source(
    source_id: UUID,
    deps: StandardDependencies = Depends(get_standard_deps)
) -> Dict[str, Any]:
    """Trigger manual sync for a data source."""
    from datetime import datetime
    
    # Mock implementation - replace with actual service call
    return {
        "source_id": str(source_id),
        "sync_started": datetime.now(timezone.utc).isoformat(),
        "status": "processing",
        "estimated_duration": "5-10 minutes"
    }

@router.get("/data-sources/{source_id}/status")
@standard_exception_handler
async def get_data_source_status(
    source_id: UUID,
    deps: StandardDependencies = Depends(get_standard_deps)
) -> Dict[str, Any]:
    """Get current status and health of a data source."""
    from datetime import datetime
    
    # Mock implementation - replace with actual service call
    return {
        "source_id": str(source_id),
        "status": "connected",
        "last_sync": datetime.now(timezone.utc).isoformat(),
        "health_score": 95.5,
        "records_synced": 12450,
        "errors": []
    }

# Export main router
analytics_router = router