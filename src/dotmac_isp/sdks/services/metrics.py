"""Metrics service for Services SDK.

This module provides metrics-related service operations for analytics integration.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from dotmac_isp.sdks.core.exceptions import SDKError


class MetricService:
    """Service for handling metrics operations in the Services SDK."""

    def __init__(self, db: Session, timezone):
        """Initialize metrics service with database session."""
        self.db = db
        self._metrics_cache: dict[str, Any] = {}

    async def create_metric(
        self,
        name: str,
        value: Decimal,
        metric_type: str = "gauge",
        tags: Optional[dict[str, str]] = None,
        timestamp: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """Create a new metric entry."""
        try:
            metric_data = {
                "id": str(UUID()),
                "name": name,
                "value": float(value),
                "metric_type": metric_type,
                "tags": tags or {},
                "timestamp": timestamp or datetime.now(timezone.utc),
                "created_at": datetime.now(timezone.utc),
            }

            # Store in cache for now (in real implementation, this would go to database)
            metric_id = metric_data["id"]
            self._metrics_cache[metric_id] = metric_data

            return metric_data
        except Exception as e:
            raise SDKError(f"Failed to create metric: {str(e)}") from e

    async def get_metric(self, metric_id: str) -> Optional[dict[str, Any]]:
        """Get metric by ID."""
        try:
            return self._metrics_cache.get(metric_id)
        except Exception as e:
            raise SDKError(f"Failed to get metric: {str(e)}") from e

    async def query_metrics(
        self,
        name_pattern: Optional[str] = None,
        tags: Optional[dict[str, str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Query metrics with filters."""
        try:
            results = []

            for metric_data in self._metrics_cache.values():
                # Apply filters
                if name_pattern and name_pattern not in metric_data.get("name", ""):
                    continue

                if tags:
                    metric_tags = metric_data.get("tags", {})
                    if not all(metric_tags.get(k) == v for k, v in tags.items()):
                        continue

                metric_time = metric_data.get("timestamp")
                if start_time and metric_time < start_time:
                    continue
                if end_time and metric_time > end_time:
                    continue

                results.append(metric_data)

                if len(results) >= limit:
                    break

            return results
        except Exception as e:
            raise SDKError(f"Failed to query metrics: {str(e)}") from e

    async def aggregate_metrics(
        self,
        name: str,
        aggregation: str = "sum",  # sum, avg, min, max, count
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        group_by: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Aggregate metrics data."""
        try:
            metrics = await self.query_metrics(
                name_pattern=name,
                start_time=start_time,
                end_time=end_time,
                limit=10000,  # Large limit for aggregation
            )
            if not metrics:
                return {"result": 0, "count": 0}

            values = [float(m.get("value", 0)) for m in metrics]

            if aggregation == "sum":
                result = sum(values)
            elif aggregation == "avg":
                result = sum(values) / len(values) if values else 0
            elif aggregation == "min":
                result = min(values) if values else 0
            elif aggregation == "max":
                result = max(values) if values else 0
            elif aggregation == "count":
                result = len(values)
            else:
                raise SDKError(f"Unsupported aggregation type: {aggregation}")

            return {
                "result": result,
                "count": len(values),
                "aggregation": aggregation,
                "start_time": start_time,
                "end_time": end_time,
            }
        except Exception as e:
            raise SDKError(f"Failed to aggregate metrics: {str(e)}") from e

    async def delete_metric(self, metric_id: str) -> bool:
        """Delete metric by ID."""
        try:
            if metric_id in self._metrics_cache:
                del self._metrics_cache[metric_id]
                return True
            return False
        except Exception as e:
            raise SDKError(f"Failed to delete metric: {str(e)}") from e

    async def get_metrics_summary(
        self, time_window: Optional[timedelta] = None
    ) -> dict[str, Any]:
        """Get         if time_window is None:
                    time_window = timedelta(hours=24)
        summary of metrics within time window."""
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - time_window

            metrics = await self.query_metrics(
                start_time=start_time, end_time=end_time, limit=10000
            )
            summary = {
                "total_metrics": len(metrics),
                "time_window": str(time_window),
                "start_time": start_time,
                "end_time": end_time,
                "metric_types": {},
                "unique_names": set(),
            }

            for metric in metrics:
                metric_type = metric.get("metric_type", "unknown")
                metric_name = metric.get("name", "unknown")

                summary["metric_types"][metric_type] = (
                    summary["metric_types"].get(metric_type, 0) + 1
                )
                summary["unique_names"].add(metric_name)

            summary["unique_names"] = list(summary["unique_names"])
            summary["unique_name_count"] = len(summary["unique_names"])

            return summary
        except Exception as e:
            raise SDKError(f"Failed to get metrics summary: {str(e)}") from e
