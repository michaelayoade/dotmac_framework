"""
Gateway Analytics SDK - Request metrics, performance monitoring, API usage tracking.
"""

from datetime import datetime, timedelta
from ..core.datetime_utils import (
    utc_now_iso,
    utc_now,
    expires_in_days,
    expires_in_hours,
    time_ago_minutes,
    time_ago_hours,
    is_expired_iso,
)
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4


class GatewayAnalyticsService:
    """In-memory service for gateway analytics operations."""

    def __init__(self):
        self._metrics: Dict[str, List[Dict[str, Any]]] = {}
        self._usage_stats: Dict[str, Dict[str, Any]] = {}
        self._error_logs: Dict[str, List[Dict[str, Any]]] = {}
        self._performance_metrics: Dict[str, List[Dict[str, Any]]] = {}
        self._real_time_monitors: Dict[str, Dict[str, Any]] = {}

    async def record_request_metric(self, **kwargs) -> None:
        """Record request metric."""
        gateway_id = kwargs["gateway_id"]

        if gateway_id not in self._metrics:
            self._metrics[gateway_id] = []

        metric = {
            "timestamp": utc_now_iso(),
            "gateway_id": gateway_id,
            "route_id": kwargs.get("route_id"),
            "method": kwargs.get("method"),
            "path": kwargs.get("path"),
            "status_code": kwargs.get("status_code"),
            "response_time_ms": kwargs.get("response_time_ms"),
            "request_size_bytes": kwargs.get("request_size_bytes"),
            "response_size_bytes": kwargs.get("response_size_bytes"),
            "user_id": kwargs.get("user_id"),
            "api_key": kwargs.get("api_key"),
            "ip_address": kwargs.get("ip_address"),
            "user_agent": kwargs.get("user_agent"),
            "error_message": kwargs.get("error_message"),
        }

        self._metrics[gateway_id].append(metric)

    async def get_request_metrics(self, gateway_id: str, **filters) -> Dict[str, Any]:
        """Get request metrics."""
        if gateway_id not in self._metrics:
            return {"total_requests": 0, "metrics": []}

        metrics = self._metrics[gateway_id]

        # Apply time range filter
        time_range = filters.get("time_range", "24h")
        if time_range:
            cutoff = self._parse_time_range(time_range)
            metrics = [
                m for m in metrics if datetime.fromisoformat(m["timestamp"]) >= cutoff
            ]

        # Apply other filters
        if filters.get("route_id"):
            metrics = [m for m in metrics if m.get("route_id") == filters["route_id"]]

        if filters.get("status_code"):
            metrics = [
                m for m in metrics if m.get("status_code") == filters["status_code"]
            ]

        # Calculate aggregated metrics
        total_requests = len(metrics)
        successful_requests = len([m for m in metrics if m.get("status_code", 0) < 400])
        error_requests = total_requests - successful_requests

        response_times = [
            m.get("response_time_ms", 0) for m in metrics if m.get("response_time_ms")
        ]
        avg_latency = sum(response_times) / len(response_times) if response_times else 0

        return {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "error_requests": error_requests,
            "error_rate": (
                (error_requests / total_requests * 100) if total_requests > 0 else 0
            ),
            "avg_latency_ms": round(avg_latency, 2),
            "metrics": metrics,
        }

    async def get_usage_analytics(self, gateway_id: str, **filters) -> Dict[str, Any]:
        """Get API usage analytics."""
        if gateway_id not in self._metrics:
            return {}

        metrics = self._metrics[gateway_id]

        # Apply time range filter
        time_range = filters.get("time_range", "7d")
        if time_range:
            cutoff = self._parse_time_range(time_range)
            metrics = [
                m for m in metrics if datetime.fromisoformat(m["timestamp"]) >= cutoff
            ]

        # Group by specified field
        group_by = filters.get("group_by", ["api_key"])
        usage = {}

        for metric in metrics:
            key = self._build_group_key(metric, group_by)

            if key not in usage:
                usage[key] = {
                    "requests": 0,
                    "bytes_transferred": 0,
                    "errors": 0,
                    "avg_response_time": 0,
                }

            usage[key]["requests"] += 1
            usage[key]["bytes_transferred"] += metric.get("response_size_bytes", 0)

            if metric.get("status_code", 0) >= 400:
                usage[key]["errors"] += 1

            # Update average response time
            current_avg = usage[key]["avg_response_time"]
            current_count = usage[key]["requests"]
            new_response_time = metric.get("response_time_ms", 0)
            usage[key]["avg_response_time"] = (
                current_avg * (current_count - 1) + new_response_time
            ) / current_count

        return usage

    async def start_monitoring(self, gateway_id: str, **config) -> str:
        """Start real-time monitoring."""
        monitor_id = str(uuid4())

        monitor = {
            "monitor_id": monitor_id,
            "gateway_id": gateway_id,
            "metrics": config.get("metrics", ["requests", "latency", "errors"]),
            "interval_seconds": config.get("interval_seconds", 60),
            "started_at": utc_now_iso(),
            "status": "active",
        }

        self._real_time_monitors[monitor_id] = monitor
        return monitor_id

    async def start_real_time_monitoring(
        self,
        gateway_id: str,
        on_request: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
        **config,
    ) -> str:
        """Start real-time monitoring with callbacks."""
        monitor_id = await self.start_monitoring(gateway_id, **config)

        # In a real implementation, this would set up WebSocket connections
        # or Server-Sent Events for real-time streaming

        monitor = self._real_time_monitors[monitor_id]
        monitor["on_request"] = on_request
        monitor["on_error"] = on_error

        return monitor_id

    def _parse_time_range(self, time_range: str) -> datetime:
        """Parse time range string to datetime."""
        now = utc_now()

        if time_range.endswith("h"):
            hours = int(time_range[:-1])
            return now - timedelta(hours=hours)
        elif time_range.endswith("d"):
            days = int(time_range[:-1])
            return now - timedelta(days=days)
        elif time_range.endswith("w"):
            weeks = int(time_range[:-1])
            return now - timedelta(weeks=weeks)
        else:
            return now - timedelta(hours=24)  # Default to 24 hours

    def _build_group_key(self, metric: Dict[str, Any], group_by: List[str]) -> str:
        """Build grouping key from metric."""
        key_parts = []
        for field in group_by:
            value = metric.get(field, "unknown")
            key_parts.append(f"{field}:{value}")
        return "|".join(key_parts)


class GatewayAnalyticsSDK:
    """SDK for gateway analytics and monitoring."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._service = GatewayAnalyticsService()

    async def record_request_metric(
        self,
        gateway_id: str,
        method: str,
        path: str,
        status_code: int,
        response_time_ms: float,
        **kwargs,
    ) -> None:
        """Record request metric."""
        await self._service.record_request_metric(
            gateway_id=gateway_id,
            method=method,
            path=path,
            status_code=status_code,
            response_time_ms=response_time_ms,
            **kwargs,
        )

    async def get_request_metrics(
        self, gateway_id: str, time_range: str = "24h", **filters
    ) -> Dict[str, Any]:
        """Get request metrics."""
        return await self._service.get_request_metrics(
            gateway_id, time_range=time_range, **filters
        )

    async def get_usage_analytics(
        self,
        gateway_id: str,
        time_range: str = "7d",
        group_by: List[str] = None,
        **filters,
    ) -> Dict[str, Any]:
        """Get usage analytics."""
        return await self._service.get_usage_analytics(
            gateway_id,
            time_range=time_range,
            group_by=group_by or ["api_key"],
            **filters,
        )

    async def start_monitoring(
        self, gateway_id: str, metrics: List[str] = None, **config
    ) -> str:
        """Start monitoring."""
        return await self._service.start_monitoring(
            gateway_id, metrics=metrics or ["requests", "latency", "errors"], **config
        )

    async def start_real_time_monitoring(
        self,
        gateway_id: str,
        on_request: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
        **config,
    ) -> str:
        """Start real-time monitoring."""
        return await self._service.start_real_time_monitoring(
            gateway_id, on_request, on_error, **config
        )
