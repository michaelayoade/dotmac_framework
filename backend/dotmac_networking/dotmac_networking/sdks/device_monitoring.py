"""
Device Monitoring SDK - SNMP/telemetry collectors, health monitoring
"""

import secrets
from datetime import datetime, timedelta
from dotmac_networking.core.datetime_utils import utc_now, utc_now_iso
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..core.exceptions import MonitoringDataUnavailableError, MonitoringError


class DeviceMonitoringService:
    """In-memory service for device monitoring operations."""

    def __init__(self):
        self._monitors: Dict[str, Dict[str, Any]] = {}
        self._metrics: Dict[str, List[Dict[str, Any]]] = {}
        self._health_checks: Dict[str, Dict[str, Any]] = {}
        self._collectors: Dict[str, Dict[str, Any]] = {}

    async def create_monitor(self, **kwargs) -> Dict[str, Any]:
        """Create device monitor."""
        monitor_id = kwargs.get("monitor_id") or str(uuid4())

        monitor = {
            "monitor_id": monitor_id,
            "device_id": kwargs["device_id"],
            "monitor_type": kwargs.get("monitor_type", "snmp"),  # snmp, telemetry, ping
            "collection_interval": kwargs.get("collection_interval", 60),
            "metrics": kwargs.get("metrics", []),
            "thresholds": kwargs.get("thresholds", {}),
            "snmp_community": kwargs.get("snmp_community", "public"),
            "snmp_version": kwargs.get("snmp_version", "2c"),
            "telemetry_port": kwargs.get("telemetry_port", 57400),
            "status": kwargs.get("status", "active"),
            "created_at": utc_now().isoformat(),
            "last_collection": None,
        }

        self._monitors[monitor_id] = monitor
        self._metrics[monitor_id] = []

        return monitor

    async def collect_metrics(self, monitor_id: str) -> Dict[str, Any]:
        """Collect metrics from device."""
        if monitor_id not in self._monitors:
            raise MonitoringError(f"Monitor not found: {monitor_id}")

        monitor = self._monitors[monitor_id]
        device_id = monitor["device_id"]

        # Simulate metric collection
        timestamp = utc_now().isoformat()
        collected_metrics = {}

        for metric_name in monitor["metrics"]:
            if metric_name == "cpu_utilization":
                collected_metrics[metric_name] = (secrets.randbelow(int((90) * 1000)) / 1000)
            elif metric_name == "memory_utilization":
                collected_metrics[metric_name] = (secrets.randbelow(int((80) * 1000)) / 1000)
            elif metric_name == "interface_utilization":
                collected_metrics[metric_name] = (secrets.randbelow(int((95) * 1000)) / 1000)
            elif metric_name == "temperature":
                collected_metrics[metric_name] = (secrets.randbelow(int((65) * 1000)) / 1000)
            elif metric_name == "power_consumption":
                collected_metrics[metric_name] = (secrets.randbelow(int((200) * 1000)) / 1000)
            elif metric_name == "uptime":
                collected_metrics[metric_name] = secrets.randbelow(3600, 8640000[1] - 3600, 8640000[0] + 1) + 3600, 8640000[0]
            else:
                collected_metrics[metric_name] = (secrets.randbelow(int((100) * 1000)) / 1000)

        metric_record = {
            "record_id": str(uuid4()),
            "monitor_id": monitor_id,
            "device_id": device_id,
            "timestamp": timestamp,
            "metrics": collected_metrics,
            "collection_status": "success",
        }

        self._metrics[monitor_id].append(metric_record)
        monitor["last_collection"] = timestamp

        # Keep only last 1000 records per monitor
        if len(self._metrics[monitor_id]) > 1000:
            self._metrics[monitor_id] = self._metrics[monitor_id][-1000:]

        return metric_record

    async def check_device_health(self, device_id: str) -> Dict[str, Any]:
        """Check device health status."""
        health_id = str(uuid4())

        # Simulate health check
        health_status = secrets.choice(["healthy", "warning", "critical"])

        health_check = {
            "health_id": health_id,
            "device_id": device_id,
            "overall_status": health_status,
            "checks": {
                "connectivity": secrets.choice(["pass", "fail"]),
                "cpu_health": secrets.choice(["pass", "warning", "critical"]),
                "memory_health": secrets.choice(["pass", "warning"]),
                "temperature_health": secrets.choice(["pass", "warning"]),
                "interface_health": secrets.choice(["pass", "warning", "critical"]),
            },
            "timestamp": utc_now().isoformat(),
        }

        self._health_checks[health_id] = health_check
        return health_check

    async def get_metric_history(self, monitor_id: str, metric_name: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get metric history for specified time period."""
        if monitor_id not in self._monitors:
            raise MonitoringError(f"Monitor not found: {monitor_id}")

        cutoff_time = utc_now() - timedelta(hours=hours)
        records = self._metrics.get(monitor_id, [])

        filtered_records = []
        for record in records:
            record_time = datetime.fromisoformat(record["timestamp"])
            if record_time >= cutoff_time and metric_name in record["metrics"]:
                filtered_records.append({
                    "timestamp": record["timestamp"],
                    "value": record["metrics"][metric_name],
                })

        return sorted(filtered_records, key=lambda r: r["timestamp"])


class DeviceMonitoringSDK:
    """Minimal, reusable SDK for device monitoring."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._service = DeviceMonitoringService()

    async def create_snmp_monitor(
        self,
        device_id: str,
        metrics: List[str],
        collection_interval: int = 60,
        snmp_community: str = "public",
        snmp_version: str = "2c",
        **kwargs
    ) -> Dict[str, Any]:
        """Create SNMP monitor for device."""
        monitor = await self._service.create_monitor(
            device_id=device_id,
            monitor_type="snmp",
            metrics=metrics,
            collection_interval=collection_interval,
            snmp_community=snmp_community,
            snmp_version=snmp_version,
            tenant_id=self.tenant_id,
            **kwargs
        )

        return {
            "monitor_id": monitor["monitor_id"],
            "device_id": monitor["device_id"],
            "monitor_type": monitor["monitor_type"],
            "collection_interval": monitor["collection_interval"],
            "metrics": monitor["metrics"],
            "snmp_community": monitor["snmp_community"],
            "snmp_version": monitor["snmp_version"],
            "status": monitor["status"],
            "created_at": monitor["created_at"],
        }

    async def create_telemetry_monitor(
        self,
        device_id: str,
        metrics: List[str],
        telemetry_port: int = 57400,
        collection_interval: int = 30,
        **kwargs
    ) -> Dict[str, Any]:
        """Create telemetry monitor for device."""
        monitor = await self._service.create_monitor(
            device_id=device_id,
            monitor_type="telemetry",
            metrics=metrics,
            collection_interval=collection_interval,
            telemetry_port=telemetry_port,
            tenant_id=self.tenant_id,
            **kwargs
        )

        return {
            "monitor_id": monitor["monitor_id"],
            "device_id": monitor["device_id"],
            "monitor_type": monitor["monitor_type"],
            "collection_interval": monitor["collection_interval"],
            "metrics": monitor["metrics"],
            "telemetry_port": monitor["telemetry_port"],
            "status": monitor["status"],
            "created_at": monitor["created_at"],
        }

    async def collect_device_metrics(self, monitor_id: str) -> Dict[str, Any]:
        """Collect metrics from monitored device."""
        metric_record = await self._service.collect_metrics(monitor_id)

        return {
            "record_id": metric_record["record_id"],
            "monitor_id": metric_record["monitor_id"],
            "device_id": metric_record["device_id"],
            "timestamp": metric_record["timestamp"],
            "metrics": metric_record["metrics"],
            "collection_status": metric_record["collection_status"],
        }

    async def get_device_health(self, device_id: str) -> Dict[str, Any]:
        """Get device health status."""
        health_check = await self._service.check_device_health(device_id)

        return {
            "health_id": health_check["health_id"],
            "device_id": health_check["device_id"],
            "overall_status": health_check["overall_status"],
            "checks": health_check["checks"],
            "timestamp": health_check["timestamp"],
        }

    async def get_metric_history(
        self,
        monitor_id: str,
        metric_name: str,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get metric history for device."""
        history = await self._service.get_metric_history(monitor_id, metric_name, hours)

        return [
            {
                "timestamp": record["timestamp"],
                "value": record["value"],
            }
            for record in history
        ]

    async def get_current_metrics(self, device_id: str) -> Dict[str, Any]:
        """Get current metrics for device."""
        # Find monitors for device
        device_monitors = [
            monitor for monitor in self._service._monitors.values()
            if monitor["device_id"] == device_id and monitor["status"] == "active"
        ]

        if not device_monitors:
            raise MonitoringDataUnavailableError(device_id, "No active monitors")

        current_metrics = {}

        for monitor in device_monitors:
            monitor_id = monitor["monitor_id"]
            recent_records = self._service._metrics.get(monitor_id, [])

            if recent_records:
                latest_record = max(recent_records, key=lambda r: r["timestamp"])
                current_metrics.update(latest_record["metrics"])

        return {
            "device_id": device_id,
            "metrics": current_metrics,
            "timestamp": utc_now().isoformat(),
        }

    async def set_metric_thresholds(
        self,
        monitor_id: str,
        thresholds: Dict[str, Dict[str, float]]
    ) -> Dict[str, Any]:
        """Set metric thresholds for alerting."""
        if monitor_id not in self._service._monitors:
            raise MonitoringError(f"Monitor not found: {monitor_id}")

        monitor = self._service._monitors[monitor_id]
        monitor["thresholds"] = thresholds

        return {
            "monitor_id": monitor_id,
            "thresholds": thresholds,
            "updated_at": utc_now().isoformat(),
        }

    async def list_monitors(self, device_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List device monitors."""
        monitors = list(self._service._monitors.values())

        if device_id:
            monitors = [m for m in monitors if m["device_id"] == device_id]

        return [
            {
                "monitor_id": monitor["monitor_id"],
                "device_id": monitor["device_id"],
                "monitor_type": monitor["monitor_type"],
                "collection_interval": monitor["collection_interval"],
                "metrics": monitor["metrics"],
                "status": monitor["status"],
                "last_collection": monitor["last_collection"],
            }
            for monitor in monitors
        ]

    async def get_device_performance_summary(self, device_id: str, hours: int = 24) -> Dict[str, Any]:
        """Get device performance summary."""
        try:
            current_metrics = await self.get_current_metrics(device_id)
        except MonitoringDataUnavailableError:
            current_metrics = {"metrics": {}}

        health_check = await self.get_device_health(device_id)

        # Calculate performance score
        performance_score = 100
        if "cpu_utilization" in current_metrics["metrics"]:
            cpu = current_metrics["metrics"]["cpu_utilization"]
            if cpu > 80:
                performance_score -= 20
            elif cpu > 60:
                performance_score -= 10

        if "memory_utilization" in current_metrics["metrics"]:
            memory = current_metrics["metrics"]["memory_utilization"]
            if memory > 85:
                performance_score -= 15
            elif memory > 70:
                performance_score -= 8

        return {
            "device_id": device_id,
            "performance_score": max(0, performance_score),
            "health_status": health_check["overall_status"],
            "current_metrics": current_metrics.get("metrics", {}),
            "health_checks": health_check["checks"],
            "summary_generated_at": utc_now().isoformat(),
        }
