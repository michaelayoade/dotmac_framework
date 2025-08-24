"""Analytics API router for metrics, reports, dashboards and alerts."""

from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from decimal import Decimal

from dotmac_isp.core.database import get_db
from dotmac_isp.core.middleware import get_tenant_id_dependency
from sqlalchemy.orm import Session
from .service import MetricService, ReportService, DashboardService, AlertService, AnalyticsService
from . import schemas
from dotmac_isp.shared.exceptions import (
    EntityNotFoundError,
    ValidationError,
    BusinessRuleError,
    ServiceError
)

router = APIRouter(tags=["analytics"])
analytics_router = router  # Standard export alias


# Metric endpoints
@router.post("/metrics", response_model=schemas.MetricResponse)
async def create_metric(
    data: schemas.MetricCreate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Create new metric."""
    try:
        service = MetricService(db, tenant_id)
        return await service.create(data)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except BusinessRuleError as e:
        raise HTTPException(status_code=422, detail=e.message)
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.get("/metrics", response_model=List[schemas.MetricResponse])
async def list_metrics(
    metric_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """List metrics with optional filtering."""
    try:
        service = MetricService(db, tenant_id)
        filters = {}
        if metric_type:
            filters['metric_type'] = metric_type
        if is_active is not None:
            filters['is_active'] = is_active
        
        return await service.list(
            filters=filters,
            limit=limit,
            offset=skip
        )
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.get("/metrics/{metric_id}", response_model=schemas.MetricResponse)
async def get_metric(
    metric_id: UUID,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Get metric by ID."""
    try:
        service = MetricService(db, tenant_id)
        return await service.get_by_id_or_raise(metric_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=e.message)


# Report endpoints
@router.post("/reports", response_model=schemas.ReportResponse)
async def create_report(
    data: schemas.ReportCreate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Create new report."""
    try:
        service = ReportService(db, tenant_id)
        return await service.create(data)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except BusinessRuleError as e:
        raise HTTPException(status_code=422, detail=e.message)
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.get("/reports", response_model=List[schemas.ReportResponse])
async def list_reports(
    report_type: Optional[str] = Query(None),
    is_scheduled: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """List reports with optional filtering."""
    try:
        service = ReportService(db, tenant_id)
        filters = {}
        if report_type:
            filters['report_type'] = report_type
        if is_scheduled is not None:
            filters['is_scheduled'] = is_scheduled
        
        return await service.list(
            filters=filters,
            limit=limit,
            offset=skip
        )
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=e.message)


# Dashboard endpoints
@router.post("/dashboards", response_model=schemas.DashboardResponse)
async def create_dashboard(
    data: schemas.DashboardCreate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Create new dashboard."""
    try:
        service = DashboardService(db, tenant_id)
        return await service.create(data)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except BusinessRuleError as e:
        raise HTTPException(status_code=422, detail=e.message)
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.get("/dashboards", response_model=List[schemas.DashboardResponse])
async def list_dashboards(
    is_default: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """List dashboards with optional filtering."""
    try:
        service = DashboardService(db, tenant_id)
        filters = {}
        if is_default is not None:
            filters['is_default'] = is_default
        
        return await service.list(
            filters=filters,
            limit=limit,
            offset=skip
        )
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=e.message)


# Alert endpoints
@router.post("/alerts", response_model=schemas.AlertResponse)
async def create_alert(
    data: schemas.AlertCreate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Create new alert."""
    try:
        service = AlertService(db, tenant_id)
        return await service.create(data)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except BusinessRuleError as e:
        raise HTTPException(status_code=422, detail=e.message)
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=e.message)


# Legacy overview endpoint
@router.get("/overview")
async def get_analytics_overview(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Get analytics overview with key metrics and stats."""
    try:
        service = AnalyticsService(db, tenant_id)
        overview = await service.get_dashboard_overview(start_date, end_date)
        return overview
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


# Metrics endpoints
@router.get("/metrics")
async def list_metrics(
    metric_type: Optional[MetricType] = None, limit: int = Query(50, le=200)
):
    """List available metrics."""
    metrics = [
        {
            "id": str(uuid4()),
            "name": "bandwidth_utilization",
            "display_name": "Bandwidth Utilization",
            "metric_type": "bandwidth",
            "latest_value": 85.5,
            "unit": "percentage",
            "trend": "increasing",
            "last_updated": datetime.now(),
        },
        {
            "id": str(uuid4()),
            "name": "monthly_revenue",
            "display_name": "Monthly Revenue",
            "metric_type": "revenue",
            "latest_value": 45000.0,
            "unit": "USD",
            "trend": "increasing",
            "last_updated": datetime.now(),
        },
        {
            "id": str(uuid4()),
            "name": "customer_count",
            "display_name": "Total Customers",
            "metric_type": "customer_count",
            "latest_value": 1250,
            "unit": "count",
            "trend": "stable",
            "last_updated": datetime.now(),
        },
        {
            "id": str(uuid4()),
            "name": "service_uptime",
            "display_name": "Service Uptime",
            "metric_type": "service_uptime",
            "latest_value": 99.8,
            "unit": "percentage",
            "trend": "stable",
            "last_updated": datetime.now(),
        },
    ]

    if metric_type:
        metrics = [m for m in metrics if m["metric_type"] == metric_type.value]

    return {
        "metrics": metrics[:limit],
        "total": len(metrics),
        "metric_types": [t.value for t in MetricType],
    }


@router.get("/metrics/{metric_id}")
async def get_metric_details(metric_id: str):
    """Get detailed metric information."""
    # Generate sample historical data
    now = datetime.now()
    historical_data = []
    for i in range(24):  # Last 24 hours
        timestamp = now - timedelta(hours=i)
        value = 85.5 + (i * 0.5) - 12  # Sample trending data
        historical_data.append(
            {
                "timestamp": timestamp,
                "value": max(0, value),
                "dimensions": {"region": "us-west", "service_type": "residential"},
            }
        )

    return {
        "id": metric_id,
        "name": "bandwidth_utilization",
        "display_name": "Bandwidth Utilization",
        "description": "Real-time bandwidth utilization across all service regions",
        "metric_type": "bandwidth",
        "current_value": 85.5,
        "unit": "percentage",
        "historical_data": historical_data[::-1],  # Reverse to show oldest first
        "statistics": {
            "min": min(d["value"] for d in historical_data),
            "max": max(d["value"] for d in historical_data),
            "avg": sum(d["value"] for d in historical_data) / len(historical_data),
            "trend": "increasing",
        },
    }


@router.post("/metrics/{metric_id}/values")
async def record_metric_value(
    metric_id: str,
    value: float,
    timestamp: Optional[datetime] = None,
    dimensions: Optional[Dict[str, Any]] = None,
):
    """Record a new metric value."""
    record_time = timestamp or datetime.now()

    return {
        "message": "Metric value recorded successfully",
        "metric_id": metric_id,
        "value": value,
        "timestamp": record_time,
        "dimensions": dimensions or {},
        "status": "recorded",
    }


# Reports endpoints
@router.get("/reports")
async def list_reports(
    report_type: Optional[ReportType] = None, limit: int = Query(20, le=100)
):
    """List available reports."""
    reports = [
        {
            "id": str(uuid4()),
            "title": "Monthly Revenue Report",
            "report_type": "monthly",
            "generated_at": datetime.now() - timedelta(days=1),
            "period": "2024-08",
            "status": "completed",
            "size_mb": 2.5,
        },
        {
            "id": str(uuid4()),
            "title": "Customer Growth Analysis",
            "report_type": "quarterly",
            "generated_at": datetime.now() - timedelta(days=7),
            "period": "Q3-2024",
            "status": "completed",
            "size_mb": 5.2,
        },
        {
            "id": str(uuid4()),
            "title": "Network Performance Summary",
            "report_type": "weekly",
            "generated_at": datetime.now() - timedelta(hours=12),
            "period": "Week 34",
            "status": "completed",
            "size_mb": 1.8,
        },
    ]

    if report_type:
        reports = [r for r in reports if r["report_type"] == report_type.value]

    return {
        "reports": reports[:limit],
        "total": len(reports),
        "report_types": [t.value for t in ReportType],
    }


@router.post("/reports")
async def create_report(
    title: str,
    report_type: ReportType,
    start_date: datetime,
    end_date: datetime,
    filters: Optional[Dict[str, Any]] = None,
):
    """Create a new analytics report."""
    report_id = str(uuid4())

    # Generate sample report data based on type
    sample_data = {
        "summary": {
            "period": f"{start_date.date()} to {end_date.date()}",
            "total_customers": 1250,
            "total_revenue": 45000.0,
            "avg_bandwidth": 85.5,
            "uptime_percentage": 99.8,
        },
        "trends": {
            "customer_growth": 5.2,
            "revenue_growth": 8.1,
            "bandwidth_growth": 12.3,
        },
        "regional_breakdown": {
            "us-west": {"customers": 450, "revenue": 18000.0},
            "us-east": {"customers": 380, "revenue": 15200.0},
            "us-central": {"customers": 420, "revenue": 11800.0},
        },
    }

    if filters:
        sample_data["filters_applied"] = filters

    return {
        "id": report_id,
        "title": title,
        "report_type": report_type.value,
        "start_date": start_date,
        "end_date": end_date,
        "status": "generated",
        "generated_at": datetime.now(),
        "data": sample_data,
        "download_url": f"/api/v1/analytics/reports/{report_id}/download",
    }


@router.get("/reports/{report_id}")
async def get_report(report_id: str):
    """Get detailed report information."""
    return {
        "id": report_id,
        "title": "Monthly Revenue Report",
        "report_type": "monthly",
        "generated_at": datetime.now() - timedelta(days=1),
        "status": "completed",
        "data": {
            "executive_summary": {
                "total_revenue": 45000.0,
                "customer_count": 1250,
                "growth_rate": 8.1,
                "key_insights": [
                    "Revenue increased 8.1% compared to previous month",
                    "Customer acquisition up 12% with reduced churn",
                    "Network utilization optimized, reduced costs by 5%",
                ],
            },
            "financial_metrics": {
                "gross_revenue": 45000.0,
                "net_revenue": 42750.0,
                "operating_costs": 28000.0,
                "profit_margin": 34.4,
            },
            "customer_metrics": {
                "total_customers": 1250,
                "new_customers": 45,
                "churned_customers": 12,
                "avg_revenue_per_customer": 36.0,
            },
        },
    }


@router.get("/reports/{report_id}/download")
async def download_report(
    report_id: str, format: str = Query("json", pattern="^(json|csv|pdf)$")
):
    """Download report in specified format."""
    return {
        "report_id": report_id,
        "format": format,
        "download_url": f"https://api.dotmac.com/downloads/reports/{report_id}.{format}",
        "expires_at": datetime.now() + timedelta(hours=24),
        "size_mb": 2.5 if format == "json" else 1.8 if format == "csv" else 5.2,
    }


# Dashboard endpoints
@router.get("/dashboards")
async def list_dashboards():
    """List available dashboards."""
    return {
        "dashboards": [
            {
                "id": str(uuid4()),
                "name": "Executive Overview",
                "description": "High-level metrics for executive team",
                "widget_count": 8,
                "last_updated": datetime.now() - timedelta(hours=2),
                "is_public": False,
            },
            {
                "id": str(uuid4()),
                "name": "Network Operations",
                "description": "Real-time network monitoring and alerts",
                "widget_count": 12,
                "last_updated": datetime.now() - timedelta(minutes=15),
                "is_public": True,
            },
            {
                "id": str(uuid4()),
                "name": "Customer Analytics",
                "description": "Customer behavior and satisfaction metrics",
                "widget_count": 6,
                "last_updated": datetime.now() - timedelta(hours=1),
                "is_public": False,
            },
        ],
        "total": 3,
    }


@router.get("/dashboards/{dashboard_id}")
async def get_dashboard(dashboard_id: str):
    """Get dashboard with widgets."""
    return {
        "id": dashboard_id,
        "name": "Executive Overview",
        "description": "High-level metrics for executive team",
        "widgets": [
            {
                "id": str(uuid4()),
                "type": "metric_card",
                "title": "Total Revenue",
                "config": {"metric": "revenue", "period": "month"},
                "position": {"x": 0, "y": 0, "width": 3, "height": 2},
                "data": {"value": 45000.0, "change": 8.1},
            },
            {
                "id": str(uuid4()),
                "type": "line_chart",
                "title": "Customer Growth",
                "config": {"metric": "customer_count", "period": "6_months"},
                "position": {"x": 3, "y": 0, "width": 6, "height": 4},
                "data": {
                    "trend": "increasing",
                    "values": [1100, 1150, 1180, 1220, 1240, 1250],
                },
            },
            {
                "id": str(uuid4()),
                "type": "gauge",
                "title": "Network Uptime",
                "config": {"metric": "uptime", "threshold": 99.5},
                "position": {"x": 9, "y": 0, "width": 3, "height": 2},
                "data": {"value": 99.8, "status": "excellent"},
            },
        ],
        "last_updated": datetime.now() - timedelta(hours=2),
    }


@router.post("/dashboards")
async def create_dashboard(
    name: str, description: Optional[str] = None, is_public: bool = False
):
    """Create a new dashboard."""
    dashboard_id = str(uuid4())

    return {
        "id": dashboard_id,
        "name": name,
        "description": description,
        "is_public": is_public,
        "widgets": [],
        "created_at": datetime.now(),
        "share_url": f"/dashboards/{dashboard_id}" if is_public else None,
    }


# Alerts endpoints
@router.get("/alerts")
async def list_alerts(
    severity: Optional[AlertSeverity] = None, is_active: Optional[bool] = None
):
    """List analytics alerts."""
    alerts = [
        {
            "id": str(uuid4()),
            "name": "High Bandwidth Usage",
            "metric_type": "bandwidth",
            "condition": "greater_than",
            "threshold": 90.0,
            "severity": "high",
            "is_active": True,
            "last_triggered": datetime.now() - timedelta(hours=2),
            "trigger_count": 3,
        },
        {
            "id": str(uuid4()),
            "name": "Revenue Drop Alert",
            "metric_type": "revenue",
            "condition": "less_than",
            "threshold": 40000.0,
            "severity": "critical",
            "is_active": True,
            "last_triggered": None,
            "trigger_count": 0,
        },
        {
            "id": str(uuid4()),
            "name": "Customer Churn Warning",
            "metric_type": "customer_count",
            "condition": "decrease_rate",
            "threshold": 5.0,
            "severity": "medium",
            "is_active": True,
            "last_triggered": datetime.now() - timedelta(days=3),
            "trigger_count": 1,
        },
    ]

    filtered_alerts = alerts
    if severity:
        filtered_alerts = [
            a for a in filtered_alerts if a["severity"] == severity.value
        ]
    if is_active is not None:
        filtered_alerts = [a for a in filtered_alerts if a["is_active"] == is_active]

    return {
        "alerts": filtered_alerts,
        "total": len(filtered_alerts),
        "active_count": len([a for a in alerts if a["is_active"]]),
        "triggered_today": len(
            [
                a
                for a in alerts
                if a["last_triggered"]
                and (datetime.now() - a["last_triggered"]).days == 0
            ]
        ),
    }


@router.post("/alerts")
async def create_alert(
    name: str,
    metric_type: MetricType,
    condition: str,
    threshold: float,
    severity: AlertSeverity,
    notification_channels: Optional[List[str]] = None,
):
    """Create a new analytics alert."""
    alert_id = str(uuid4())

    return {
        "id": alert_id,
        "name": name,
        "metric_type": metric_type.value,
        "condition": condition,
        "threshold": threshold,
        "severity": severity.value,
        "notification_channels": notification_channels or ["email"],
        "is_active": True,
        "created_at": datetime.now(),
        "last_triggered": None,
        "trigger_count": 0,
    }


@router.get("/alerts/active")
async def get_active_alerts():
    """Get all currently active alerts."""
    return {
        "active_alerts": [
            {
                "id": str(uuid4()),
                "name": "High Bandwidth Usage",
                "severity": "high",
                "metric_type": "bandwidth",
                "current_value": 92.5,
                "threshold": 90.0,
                "triggered_at": datetime.now() - timedelta(hours=2),
                "priority_score": 8.5,
            },
            {
                "id": str(uuid4()),
                "name": "Network Latency Spike",
                "severity": "medium",
                "metric_type": "network_latency",
                "current_value": 45.2,
                "threshold": 40.0,
                "triggered_at": datetime.now() - timedelta(minutes=30),
                "priority_score": 6.2,
            },
        ],
        "total_count": 2,
        "critical_count": 0,
        "high_count": 1,
        "medium_count": 1,
        "low_count": 0,
    }


# Real-time data endpoints
@router.get("/realtime/metrics")
async def get_realtime_metrics():
    """Get real-time metric values."""
    return {
        "timestamp": datetime.now(),
        "metrics": {
            "bandwidth_utilization": {
                "value": 85.5,
                "unit": "percentage",
                "trend": "stable",
            },
            "active_connections": {
                "value": 2847,
                "unit": "count",
                "trend": "increasing",
            },
            "network_latency": {
                "value": 12.3,
                "unit": "milliseconds",
                "trend": "stable",
            },
            "error_rate": {"value": 0.02, "unit": "percentage", "trend": "decreasing"},
        },
        "refresh_interval": 30,
    }


@router.get("/export")
async def export_analytics_data(
    start_date: datetime,
    end_date: datetime,
    metrics: Optional[List[str]] = None,
    format: str = Query("json", pattern="^(json|csv|excel)$"),
):
    """Export analytics data for specified date range."""
    return {
        "export_id": str(uuid4()),
        "start_date": start_date,
        "end_date": end_date,
        "metrics": metrics or ["all"],
        "format": format,
        "status": "processing",
        "estimated_completion": datetime.now() + timedelta(minutes=5),
        "download_url": None,  # Will be provided when ready
        "estimated_size_mb": 15.2,
    }
