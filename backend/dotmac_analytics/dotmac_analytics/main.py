"""
DotMac Analytics Service - Main Application
Provides business intelligence, reporting, and analytics services.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .core.config import config
from .core.exceptions import AnalyticsError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OpenAPI tags metadata
tags_metadata = [
    {
        "name": "Health",
        "description": "Service health and status monitoring",
    },
    {
        "name": "Dashboards",
        "description": "Analytics dashboards and visualizations",
    },
    {
        "name": "Reports",
        "description": "Business reports generation and management",
    },
    {
        "name": "Metrics",
        "description": "Real-time metrics and KPIs",
    },
    {
        "name": "Analytics",
        "description": "Data analysis and insights",
    },
    {
        "name": "Alerts",
        "description": "Analytics alerts and thresholds",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting DotMac Analytics Service...")
    logger.info(f"Service initialized with tenant: {config.tenant_id}")
    
    yield
    
    logger.info("Shutting down DotMac Analytics Service...")


# Create FastAPI application
app = FastAPI(
    title="DotMac Analytics Service",
    description="""
    **Business Intelligence and Analytics Platform**

    The DotMac Analytics Service provides comprehensive analytics capabilities for ISPs:

    ## 📊 Core Features

    ### Dashboards
    - Real-time operational dashboards
    - Executive dashboards
    - Custom dashboard builder
    - Widget library
    - Interactive visualizations

    ### Reporting
    - Scheduled reports
    - Ad-hoc reporting
    - Report templates
    - Export formats (PDF, Excel, CSV)
    - Report distribution

    ### Metrics & KPIs
    - Revenue metrics (MRR, ARR, ARPU)
    - Customer metrics (Churn, LTV, CAC)
    - Network metrics (Utilization, Performance)
    - Service metrics (SLA, Uptime)
    - Custom metrics

    ### Analytics
    - Predictive analytics
    - Churn prediction
    - Revenue forecasting
    - Capacity planning
    - Trend analysis

    ### Data Processing
    - ETL pipelines
    - Data aggregation
    - Time-series analysis
    - Anomaly detection
    - Data warehousing

    ## 🚀 Integration

    - **Database**: PostgreSQL for data warehouse
    - **Cache**: Redis for real-time metrics
    - **Events**: Event streaming for real-time data
    - **Multi-tenant**: Full tenant isolation

    **Base URL**: `/api/v1`
    **Version**: 1.0.0
    """,
    version="1.0.0",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
    docs_url="/docs" if config.debug else None,
    redoc_url="/redoc" if config.debug else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class MetricRequest(BaseModel):
    """Request model for metric queries."""
    metric_name: str = Field(..., description="Name of the metric")
    start_date: datetime = Field(..., description="Start date for metric")
    end_date: datetime = Field(..., description="End date for metric")
    granularity: str = Field(default="daily", description="Data granularity (hourly, daily, weekly, monthly)")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Optional filters")


class DashboardResponse(BaseModel):
    """Response model for dashboard data."""
    dashboard_id: str = Field(..., description="Dashboard unique identifier")
    name: str = Field(..., description="Dashboard name")
    widgets: List[Dict[str, Any]] = Field(..., description="Dashboard widgets")
    last_updated: datetime = Field(..., description="Last update timestamp")


class ReportResponse(BaseModel):
    """Response model for reports."""
    report_id: str = Field(..., description="Report unique identifier")
    name: str = Field(..., description="Report name")
    status: str = Field(..., description="Report status")
    download_url: Optional[str] = Field(default=None, description="Download URL if ready")
    created_at: datetime = Field(..., description="Creation timestamp")


# Health check endpoint
@app.get(
    "/health",
    tags=["Health"],
    summary="Health check",
    description="Check service health and dependencies",
    responses={
        200: {
            "description": "Service is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "service": "dotmac_analytics",
                        "version": "1.0.0",
                        "timestamp": "2024-01-15T10:30:00Z",
                    }
                }
            }
        }
    }
)
async def health_check() -> Dict[str, Any]:
    """Check service health status."""
    return {
        "status": "healthy",
        "service": "dotmac_analytics",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


# Dashboard endpoints
@app.get(
    "/api/v1/dashboards",
    tags=["Dashboards"],
    summary="List dashboards",
    description="Get list of available dashboards",
)
async def list_dashboards() -> List[DashboardResponse]:
    """List all available dashboards."""
    # Mock implementation
    return [
        DashboardResponse(
            dashboard_id="dash_001",
            name="Executive Overview",
            widgets=[
                {"type": "metric", "title": "MRR", "value": 125000},
                {"type": "chart", "title": "Customer Growth", "data": []},
            ],
            last_updated=datetime.utcnow(),
        )
    ]


@app.get(
    "/api/v1/dashboards/{dashboard_id}",
    tags=["Dashboards"],
    summary="Get dashboard",
    description="Get specific dashboard data",
)
async def get_dashboard(dashboard_id: str) -> DashboardResponse:
    """Get dashboard by ID."""
    return DashboardResponse(
        dashboard_id=dashboard_id,
        name="Executive Overview",
        widgets=[
            {"type": "metric", "title": "MRR", "value": 125000},
            {"type": "metric", "title": "Active Customers", "value": 5420},
            {"type": "metric", "title": "Churn Rate", "value": 2.3},
            {"type": "chart", "title": "Revenue Trend", "data": []},
        ],
        last_updated=datetime.utcnow(),
    )


# Metrics endpoints
@app.post(
    "/api/v1/metrics/query",
    tags=["Metrics"],
    summary="Query metrics",
    description="Query metrics with filters",
)
async def query_metrics(request: MetricRequest) -> Dict[str, Any]:
    """Query metrics based on criteria."""
    # Mock implementation
    return {
        "metric": request.metric_name,
        "period": {
            "start": request.start_date.isoformat(),
            "end": request.end_date.isoformat(),
        },
        "granularity": request.granularity,
        "data": [
            {"timestamp": datetime.utcnow().isoformat(), "value": 100},
            {"timestamp": (datetime.utcnow() - timedelta(days=1)).isoformat(), "value": 95},
        ],
    }


@app.get(
    "/api/v1/metrics/realtime",
    tags=["Metrics"],
    summary="Real-time metrics",
    description="Get real-time metrics stream",
)
async def realtime_metrics() -> Dict[str, Any]:
    """Get real-time metrics."""
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": {
            "active_users": 1250,
            "requests_per_second": 450,
            "average_response_time": 125,
            "error_rate": 0.02,
            "bandwidth_usage_gbps": 2.5,
        },
    }


# Reports endpoints
@app.get(
    "/api/v1/reports",
    tags=["Reports"],
    summary="List reports",
    description="Get list of available reports",
)
async def list_reports() -> List[ReportResponse]:
    """List all reports."""
    return [
        ReportResponse(
            report_id="rpt_001",
            name="Monthly Revenue Report",
            status="completed",
            download_url="/api/v1/reports/rpt_001/download",
            created_at=datetime.utcnow(),
        )
    ]


@app.post(
    "/api/v1/reports/generate",
    tags=["Reports"],
    summary="Generate report",
    description="Generate a new report",
)
async def generate_report(
    report_type: str = Query(..., description="Type of report to generate"),
    start_date: datetime = Query(..., description="Report start date"),
    end_date: datetime = Query(..., description="Report end date"),
) -> ReportResponse:
    """Generate a new report."""
    report_id = f"rpt_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    return ReportResponse(
        report_id=report_id,
        name=f"{report_type} Report",
        status="processing",
        download_url=None,
        created_at=datetime.utcnow(),
    )


# Analytics endpoints
@app.get(
    "/api/v1/analytics/churn-prediction",
    tags=["Analytics"],
    summary="Churn prediction",
    description="Get customer churn predictions",
)
async def churn_prediction() -> Dict[str, Any]:
    """Get churn prediction analytics."""
    return {
        "prediction_date": datetime.utcnow().isoformat(),
        "high_risk_customers": 45,
        "medium_risk_customers": 120,
        "low_risk_customers": 5255,
        "predicted_churn_rate": 2.8,
        "confidence": 0.85,
    }


@app.get(
    "/api/v1/analytics/revenue-forecast",
    tags=["Analytics"],
    summary="Revenue forecast",
    description="Get revenue forecasting",
)
async def revenue_forecast() -> Dict[str, Any]:
    """Get revenue forecast."""
    return {
        "forecast_date": datetime.utcnow().isoformat(),
        "current_mrr": 125000,
        "forecast_30d": 128500,
        "forecast_60d": 132000,
        "forecast_90d": 135500,
        "confidence_interval": {
            "lower": 130000,
            "upper": 141000,
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "dotmac_analytics.main:app",
        host="0.0.0.0",
        port=8005,
        reload=config.debug,
        log_level="info" if not config.debug else "debug",
    )