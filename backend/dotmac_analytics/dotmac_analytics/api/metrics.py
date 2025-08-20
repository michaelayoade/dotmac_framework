"""
Metrics API endpoints for analytics KPI management.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..core.database import get_session
from ..core.exceptions import AnalyticsError, NotFoundError, ValidationError
from ..models.enums import AggregationMethod, AlertSeverity, MetricType, TimeGranularity
from ..services.metrics import MetricService

metrics_router = APIRouter(prefix="/metrics", tags=["metrics"])


class MetricCreateRequest(BaseModel):
    """Request model for creating a metric."""
    name: str
    display_name: str
    metric_type: MetricType
    description: Optional[str] = None
    unit: Optional[str] = None
    calculation_config: Optional[Dict[str, Any]] = Field(default_factory=dict)
    dimensions: Optional[List[str]] = Field(default_factory=list)
    tags: Optional[Dict[str, str]] = Field(default_factory=dict)


class MetricValueRequest(BaseModel):
    """Request model for recording metric values."""
    metric_id: str
    value: Union[int, float]
    timestamp: Optional[datetime] = None
    dimensions: Optional[Dict[str, str]] = Field(default_factory=dict)
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)


class MetricQueryRequest(BaseModel):
    """Request model for querying metric values."""
    metric_id: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    dimensions: Optional[Dict[str, str]] = Field(default_factory=dict)
    limit: int = Field(default=1000, le=10000)
    offset: int = Field(default=0, ge=0)


class MetricAggregateRequest(BaseModel):
    """Request model for metric aggregation."""
    metric_id: str
    aggregation_method: AggregationMethod
    granularity: TimeGranularity
    start_time: datetime
    end_time: datetime
    dimensions: Optional[List[str]] = Field(default_factory=list)


class MetricAlertRequest(BaseModel):
    """Request model for creating metric alerts."""
    metric_id: str
    name: str
    condition_config: Dict[str, Any]
    severity: AlertSeverity = AlertSeverity.MEDIUM
    notification_channels: Optional[List[str]] = Field(default_factory=list)


class MetricAnnotationRequest(BaseModel):
    """Request model for creating metric annotations."""
    metric_id: str
    timestamp: datetime
    title: str
    description: Optional[str] = None
    annotation_type: str = "event"
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class MetricTrendRequest(BaseModel):
    """Request model for metric trend analysis."""
    metric_id: str
    current_period_start: datetime
    current_period_end: datetime
    comparison_period_start: datetime
    comparison_period_end: datetime


def get_tenant_id(request) -> str:
    """Extract tenant ID from request headers."""
    return "default_tenant"


@metrics_router.post("/")
async def create_metric(
    request: MetricCreateRequest,
    db: Session = Depends(get_session)
):
    """Create a new metric definition."""
    try:
        tenant_id = get_tenant_id(request)
        service = MetricService(db)

        metric = await service.create_metric(
            tenant_id=tenant_id,
            name=request.name,
            display_name=request.display_name,
            metric_type=request.metric_type,
            description=request.description,
            unit=request.unit,
            calculation_config=request.calculation_config,
            dimensions=request.dimensions,
            tags=request.tags
        )

        return {
            "metric_id": str(metric.id),
            "name": metric.name,
            "display_name": metric.display_name,
            "metric_type": metric.metric_type,
            "created_at": metric.created_at
        }

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AnalyticsError as e:
        raise HTTPException(status_code=500, detail=str(e))


@metrics_router.get("/")
async def list_metrics(
    metric_type: Optional[MetricType] = Query(None),
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_session)
):
    """List metrics with filtering options."""
    try:
        tenant_id = get_tenant_id(None)
        service = MetricService(db)

        metrics = await service.get_metrics(
            tenant_id=tenant_id,
            metric_type=metric_type,
            limit=limit,
            offset=offset
        )

        return {
            "metrics": [
                {
                    "id": str(metric.id),
                    "name": metric.name,
                    "display_name": metric.display_name,
                    "metric_type": metric.metric_type,
                    "description": metric.description,
                    "unit": metric.unit,
                    "dimensions": metric.dimensions,
                    "tags": metric.tags,
                    "created_at": metric.created_at
                }
                for metric in metrics
            ],
            "count": len(metrics),
            "limit": limit,
            "offset": offset
        }

    except AnalyticsError as e:
        raise HTTPException(status_code=500, detail=str(e))


@metrics_router.get("/{metric_id}")
async def get_metric(
    metric_id: str,
    db: Session = Depends(get_session)
):
    """Get metric by ID."""
    try:
        tenant_id = get_tenant_id(None)
        service = MetricService(db)

        metric = await service.get_metric(tenant_id, metric_id)
        if not metric:
            raise HTTPException(status_code=404, detail="Metric not found")

        return {
            "id": str(metric.id),
            "name": metric.name,
            "display_name": metric.display_name,
            "metric_type": metric.metric_type,
            "description": metric.description,
            "unit": metric.unit,
            "calculation_config": metric.calculation_config,
            "dimensions": metric.dimensions,
            "tags": metric.tags,
            "created_at": metric.created_at,
            "updated_at": metric.updated_at
        }

    except AnalyticsError as e:
        raise HTTPException(status_code=500, detail=str(e))


@metrics_router.post("/values")
async def record_metric_value(
    request: MetricValueRequest,
    db: Session = Depends(get_session)
):
    """Record a metric value."""
    try:
        tenant_id = get_tenant_id(request)
        service = MetricService(db)

        metric_value = await service.record_metric_value(
            tenant_id=tenant_id,
            metric_id=request.metric_id,
            value=request.value,
            timestamp=request.timestamp,
            dimensions=request.dimensions,
            context=request.context
        )

        return {
            "value_id": str(metric_value.id),
            "metric_id": request.metric_id,
            "value": metric_value.value,
            "timestamp": metric_value.timestamp,
            "recorded_at": metric_value.created_at
        }

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AnalyticsError as e:
        raise HTTPException(status_code=500, detail=str(e))


@metrics_router.post("/values/query")
async def query_metric_values(
    request: MetricQueryRequest,
    db: Session = Depends(get_session)
):
    """Query metric values with filtering."""
    try:
        tenant_id = get_tenant_id(request)
        service = MetricService(db)

        values = await service.get_metric_values(
            tenant_id=tenant_id,
            metric_id=request.metric_id,
            start_time=request.start_time,
            end_time=request.end_time,
            dimensions=request.dimensions,
            limit=request.limit,
            offset=request.offset
        )

        return {
            "metric_id": request.metric_id,
            "values": [
                {
                    "id": str(value.id),
                    "value": value.value,
                    "timestamp": value.timestamp,
                    "dimensions": value.dimensions,
                    "context": value.context
                }
                for value in values
            ],
            "count": len(values),
            "limit": request.limit,
            "offset": request.offset
        }

    except AnalyticsError as e:
        raise HTTPException(status_code=500, detail=str(e))


@metrics_router.post("/aggregate")
async def aggregate_metric(
    request: MetricAggregateRequest,
    db: Session = Depends(get_session)
):
    """Aggregate metric values by time and dimensions."""
    try:
        tenant_id = get_tenant_id(request)
        service = MetricService(db)

        aggregates = await service.aggregate_metric(
            tenant_id=tenant_id,
            metric_id=request.metric_id,
            aggregation_method=request.aggregation_method,
            granularity=request.granularity,
            start_time=request.start_time,
            end_time=request.end_time,
            dimensions=request.dimensions
        )

        return {
            "metric_id": request.metric_id,
            "aggregation_method": request.aggregation_method.value,
            "granularity": request.granularity.value,
            "aggregates": [
                {
                    "time_bucket": aggregate.time_bucket,
                    "value": aggregate.value,
                    "sample_count": aggregate.sample_count,
                    "dimensions": aggregate.dimensions
                }
                for aggregate in aggregates
            ],
            "count": len(aggregates)
        }

    except AnalyticsError as e:
        raise HTTPException(status_code=500, detail=str(e))


@metrics_router.post("/trend")
async def analyze_metric_trend(
    request: MetricTrendRequest,
    db: Session = Depends(get_session)
):
    """Analyze metric trend between two periods."""
    try:
        tenant_id = get_tenant_id(request)
        service = MetricService(db)

        trend_data = await service.calculate_metric_trend(
            tenant_id=tenant_id,
            metric_id=request.metric_id,
            current_period_start=request.current_period_start,
            current_period_end=request.current_period_end,
            comparison_period_start=request.comparison_period_start,
            comparison_period_end=request.comparison_period_end
        )

        return trend_data

    except AnalyticsError as e:
        raise HTTPException(status_code=500, detail=str(e))


@metrics_router.post("/alerts")
async def create_metric_alert(
    request: MetricAlertRequest,
    db: Session = Depends(get_session)
):
    """Create a metric alert."""
    try:
        tenant_id = get_tenant_id(request)
        service = MetricService(db)

        alert = await service.create_metric_alert(
            tenant_id=tenant_id,
            metric_id=request.metric_id,
            name=request.name,
            condition_config=request.condition_config,
            severity=request.severity,
            notification_channels=request.notification_channels
        )

        return {
            "alert_id": str(alert.id),
            "metric_id": request.metric_id,
            "name": alert.name,
            "severity": alert.severity,
            "created_at": alert.created_at
        }

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AnalyticsError as e:
        raise HTTPException(status_code=500, detail=str(e))


@metrics_router.post("/annotations")
async def create_metric_annotation(
    request: MetricAnnotationRequest,
    db: Session = Depends(get_session)
):
    """Create a metric annotation."""
    try:
        tenant_id = get_tenant_id(request)
        service = MetricService(db)

        annotation = await service.create_metric_annotation(
            tenant_id=tenant_id,
            metric_id=request.metric_id,
            timestamp=request.timestamp,
            title=request.title,
            description=request.description,
            annotation_type=request.annotation_type,
            metadata=request.metadata
        )

        return {
            "annotation_id": str(annotation.id),
            "metric_id": request.metric_id,
            "title": annotation.title,
            "timestamp": annotation.timestamp,
            "created_at": annotation.created_at
        }

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AnalyticsError as e:
        raise HTTPException(status_code=500, detail=str(e))
