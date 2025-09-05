"""
Device Monitoring Management for DotMac Device Management Framework.

Provides SNMP monitoring, telemetry collection, and device health tracking.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from ..exceptions import DeviceMonitoringError
from .models import Device, MonitoringRecord, MonitorType


class DeviceMonitoringManager:
    """Device monitoring manager for database operations."""

    def __init__(self, session: Session, tenant_id: str, timezone):
        self.session = session
        self.tenant_id = tenant_id

    async def create_monitoring_record(
        self,
        device_id: str,
        monitor_id: str,
        monitor_type: str,
        metrics: dict[str, Any],
        collection_status: str = "success",
        **kwargs,
    ) -> MonitoringRecord:
        """Create new monitoring record."""
        # Verify device exists
        device = (
            self.session.query(Device)
            .filter(and_(Device.device_id == device_id, Device.tenant_id == self.tenant_id))
            .first()
        )

        if not device:
            raise DeviceMonitoringError(f"Device not found: {device_id}")

        record = MonitoringRecord(
            tenant_id=self.tenant_id,
            record_id=str(uuid.uuid4()),
            device_id=device_id,
            monitor_id=monitor_id,
            monitor_type=monitor_type,
            metrics=metrics,
            collection_timestamp=kwargs.get("collection_timestamp", datetime.now(timezone.utc)),
            collection_status=collection_status,
            collection_duration_ms=kwargs.get("collection_duration_ms"),
            error_message=kwargs.get("error_message"),
            error_code=kwargs.get("error_code"),
            device_device_metadata=kwargs.get("metadata", {}),
        )

        self.session.add(record)
        self.session.commit()
        return record

    async def get_latest_metrics(self, device_id: str, monitor_type: Optional[str] = None) -> list[MonitoringRecord]:
        """Get latest monitoring records for device."""
        query = self.session.query(MonitoringRecord).filter(
            and_(
                MonitoringRecord.device_id == device_id,
                MonitoringRecord.tenant_id == self.tenant_id,
            )
        )

        if monitor_type:
            query = query.filter(MonitoringRecord.monitor_type == monitor_type)

        return query.order_by(desc(MonitoringRecord.collection_timestamp)).limit(10).all()

    async def get_metrics_history(
        self,
        device_id: str,
        monitor_type: Optional[str] = None,
        hours: int = 24,
        limit: int = 100,
    ) -> list[MonitoringRecord]:
        """Get historical monitoring records."""
        since = datetime.now(timezone.utc) - timedelta(hours=hours)

        query = self.session.query(MonitoringRecord).filter(
            and_(
                MonitoringRecord.device_id == device_id,
                MonitoringRecord.tenant_id == self.tenant_id,
                MonitoringRecord.collection_timestamp >= since,
            )
        )

        if monitor_type:
            query = query.filter(MonitoringRecord.monitor_type == monitor_type)

        return query.order_by(desc(MonitoringRecord.collection_timestamp)).limit(limit).all()

    async def get_device_health_status(self, device_id: str) -> dict[str, Any]:
        """Get current device health status from latest metrics."""
        # Get latest SNMP metrics
        latest_records = await self.get_latest_metrics(device_id, MonitorType.SNMP)

        if not latest_records:
            return {
                "device_id": device_id,
                "health_status": "unknown",
                "last_check": None,
                "message": "No monitoring data available",
            }

        latest_record = latest_records[0]
        metrics = latest_record.metrics

        # Calculate health score based on common SNMP metrics
        health_score = 100
        issues = []

        # Check CPU utilization
        cpu_usage = metrics.get("cpu_usage")
        if cpu_usage is not None:
            if cpu_usage > 90:
                health_score -= 30
                issues.append(f"High CPU usage: {cpu_usage}%")
            elif cpu_usage > 70:
                health_score -= 15
                issues.append(f"Elevated CPU usage: {cpu_usage}%")

        # Check memory utilization
        memory_usage = metrics.get("memory_usage")
        if memory_usage is not None:
            if memory_usage > 90:
                health_score -= 25
                issues.append(f"High memory usage: {memory_usage}%")
            elif memory_usage > 80:
                health_score -= 10
                issues.append(f"Elevated memory usage: {memory_usage}%")

        # Check interface errors
        interface_errors = metrics.get("interface_errors", 0)
        if interface_errors > 100:
            health_score -= 20
            issues.append(f"High interface errors: {interface_errors}")

        # Check system uptime (low uptime might indicate recent restart)
        uptime = metrics.get("system_uptime")
        if uptime is not None and uptime < 3600:  # Less than 1 hour
            health_score -= 10
            issues.append(f"Recent restart: uptime {uptime}s")

        # Determine health status
        if health_score >= 80:
            status = "healthy"
        elif health_score >= 60:
            status = "warning"
        elif health_score >= 40:
            status = "degraded"
        else:
            status = "critical"

        return {
            "device_id": device_id,
            "health_status": status,
            "health_score": health_score,
            "last_check": latest_record.collection_timestamp.isoformat(),
            "collection_status": latest_record.collection_status,
            "issues": issues,
            "metrics_summary": {
                "cpu_usage": cpu_usage,
                "memory_usage": memory_usage,
                "interface_errors": interface_errors,
                "system_uptime": uptime,
            },
        }

    async def get_monitoring_statistics(self, device_id: str, metric_name: str, hours: int = 24) -> dict[str, Any]:
        """Get statistics for a specific metric."""
        records = await self.get_metrics_history(device_id, hours=hours)

        values = []
        for record in records:
            if metric_name in record.metrics:
                values.append(float(record.metrics[metric_name]))

        if not values:
            return {
                "device_id": device_id,
                "metric_name": metric_name,
                "data_points": 0,
                "message": "No data available",
            }

        return {
            "device_id": device_id,
            "metric_name": metric_name,
            "data_points": len(values),
            "min_value": min(values),
            "max_value": max(values),
            "avg_value": sum(values) / len(values),
            "latest_value": values[0] if values else None,
            "time_range_hours": hours,
        }

    async def cleanup_old_records(self, days_to_keep: int = 30) -> int:
        """Clean up old monitoring records."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)

        deleted_count = (
            self.session.query(MonitoringRecord)
            .filter(
                and_(
                    MonitoringRecord.tenant_id == self.tenant_id,
                    MonitoringRecord.collection_timestamp < cutoff_date,
                )
            )
            .delete()
        )

        self.session.commit()
        return deleted_count


class DeviceMonitoringService:
    """High-level service for device monitoring operations."""

    def __init__(self, session: Session, tenant_id: str):
        self.manager = DeviceMonitoringManager(session, tenant_id)
        self.tenant_id = tenant_id

    async def create_snmp_monitor(
        self,
        device_id: str,
        metrics: list[str],
        collection_interval: int = 60,
        snmp_community: str = "public",
        snmp_version: str = "2c",
    ) -> dict[str, Any]:
        """Create SNMP monitoring configuration for device."""
        monitor_id = f"snmp_{device_id}_{uuid.uuid4().hex[:8]}"

        # This would typically configure the actual SNMP monitoring system
        # For now, we'll create a monitoring record to track the configuration
        config_metrics = {
            "monitor_type": "snmp",
            "metrics_list": metrics,
            "collection_interval": collection_interval,
            "snmp_community": snmp_community,
            "snmp_version": snmp_version,
            "status": "configured",
        }

        record = await self.manager.create_monitoring_record(
            device_id=device_id,
            monitor_id=monitor_id,
            monitor_type=MonitorType.SNMP,
            metrics=config_metrics,
            collection_status="configured",
        )

        return {
            "monitor_id": monitor_id,
            "device_id": device_id,
            "monitor_type": "snmp",
            "metrics": metrics,
            "collection_interval": collection_interval,
            "configured_at": record.collection_timestamp.isoformat(),
        }

    async def collect_snmp_metrics(
        self, device_id: str, monitor_id: str, metrics_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Store collected SNMP metrics."""
        start_time = datetime.now(timezone.utc)

        try:
            record = await self.manager.create_monitoring_record(
                device_id=device_id,
                monitor_id=monitor_id,
                monitor_type=MonitorType.SNMP,
                metrics=metrics_data,
                collection_status="success",
                collection_timestamp=start_time,
                collection_duration_ms=0,  # Would be calculated from actual collection
            )

            return {
                "record_id": record.record_id,
                "device_id": device_id,
                "monitor_id": monitor_id,
                "collection_status": "success",
                "metrics_count": len(metrics_data),
                "collected_at": record.collection_timestamp.isoformat(),
            }

        except Exception as e:
            # Store error record
            error_record = await self.manager.create_monitoring_record(
                device_id=device_id,
                monitor_id=monitor_id,
                monitor_type=MonitorType.SNMP,
                metrics={},
                collection_status="error",
                collection_timestamp=start_time,
                error_message=str(e),
                error_code="COLLECTION_FAILED",
            )

            return {
                "record_id": error_record.record_id,
                "device_id": device_id,
                "monitor_id": monitor_id,
                "collection_status": "error",
                "error_message": str(e),
                "collected_at": error_record.collection_timestamp.isoformat(),
            }

    async def create_telemetry_monitor(
        self, device_id: str, telemetry_paths: list[str], collection_interval: int = 30
    ) -> dict[str, Any]:
        """Create telemetry monitoring configuration."""
        monitor_id = f"telemetry_{device_id}_{uuid.uuid4().hex[:8]}"

        config_metrics = {
            "monitor_type": "telemetry",
            "telemetry_paths": telemetry_paths,
            "collection_interval": collection_interval,
            "status": "configured",
        }

        record = await self.manager.create_monitoring_record(
            device_id=device_id,
            monitor_id=monitor_id,
            monitor_type=MonitorType.TELEMETRY,
            metrics=config_metrics,
            collection_status="configured",
        )

        return {
            "monitor_id": monitor_id,
            "device_id": device_id,
            "monitor_type": "telemetry",
            "telemetry_paths": telemetry_paths,
            "collection_interval": collection_interval,
            "configured_at": record.collection_timestamp.isoformat(),
        }

    async def get_device_monitoring_overview(self, device_id: str) -> dict[str, Any]:
        """Get comprehensive monitoring overview for device."""
        health_status = await self.manager.get_device_health_status(device_id)
        latest_records = await self.manager.get_latest_metrics(device_id)

        # Group records by monitor type
        monitors_summary = {}
        for record in latest_records:
            monitor_type = record.monitor_type
            if monitor_type not in monitors_summary:
                monitors_summary[monitor_type] = {
                    "type": monitor_type,
                    "last_collection": record.collection_timestamp.isoformat(),
                    "status": record.collection_status,
                    "records_count": 0,
                }
            monitors_summary[monitor_type]["records_count"] += 1

        return {
            "device_id": device_id,
            "health_status": health_status,
            "active_monitors": list(monitors_summary.values()),
            "total_records": len(latest_records),
            "monitoring_active": len(latest_records) > 0,
        }

    async def create_health_check(
        self, device_id: str, check_type: str = "ping", target: Optional[str] = None
    ) -> dict[str, Any]:
        """Create basic health check monitor."""
        monitor_id = f"health_{check_type}_{device_id}_{uuid.uuid4().hex[:8]}"

        config_metrics = {
            "monitor_type": "health_check",
            "check_type": check_type,
            "target": target or device_id,
            "status": "configured",
        }

        record = await self.manager.create_monitoring_record(
            device_id=device_id,
            monitor_id=monitor_id,
            monitor_type=(MonitorType.PING if check_type == "ping" else MonitorType.CUSTOM),
            metrics=config_metrics,
            collection_status="configured",
        )

        return {
            "monitor_id": monitor_id,
            "device_id": device_id,
            "check_type": check_type,
            "target": target,
            "configured_at": record.collection_timestamp.isoformat(),
        }

    async def get_trending_metrics(self, device_id: str, metric_names: list[str], hours: int = 24) -> dict[str, Any]:
        """Get trending data for specific metrics."""
        trending_data = {}

        for metric_name in metric_names:
            stats = await self.manager.get_monitoring_statistics(device_id, metric_name, hours)
            trending_data[metric_name] = stats

        return {
            "device_id": device_id,
            "time_range_hours": hours,
            "metrics": trending_data,
        }
