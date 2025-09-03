"""
NOC Dashboard Service.

Provides real-time network monitoring dashboards, metrics aggregation,
and operational status views for network operations center.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from dotmac_isp.shared.base_service import BaseTenantService
from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.device_management.dotmac_device_management.services.device_service import DeviceService
from dotmac_shared.device_management.dotmac_device_management.core.models import Device, MonitoringRecord

from ..models.alarms import Alarm, AlarmSeverity, AlarmStatus
from ..models.events import NetworkEvent, EventSeverity

logger = logging.getLogger(__name__)


class NOCDashboardService(BaseTenantService):
    """Service for NOC dashboard operations and real-time monitoring."""

    def __init__(self, db: Session, tenant_id: str):
        super().__init__(
            db=db,
            model_class=Device,
            create_schema=None,
            update_schema=None,
            response_schema=None,
            tenant_id=tenant_id
        )
        self.device_service = DeviceService(db, tenant_id)

    @standard_exception_handler
    async def get_network_status_overview(self) -> Dict[str, Any]:
        """Get high-level network status overview."""
        # Get device statistics
        total_devices = self.db.query(Device).filter(
            Device.tenant_id == self.tenant_id
        ).count()
        
        online_devices = self.db.query(Device).filter(
            and_(
                Device.tenant_id == self.tenant_id,
                Device.status == "active"
            )
        ).count()
        
        offline_devices = total_devices - online_devices

        # Get active alarms by severity
        alarm_counts = {}
        for severity in AlarmSeverity:
            count = self.db.query(Alarm).filter(
                and_(
                    Alarm.tenant_id == self.tenant_id,
                    Alarm.severity == severity.value,
                    Alarm.status == AlarmStatus.ACTIVE
                )
            ).count()
            alarm_counts[severity.value] = count

        total_active_alarms = sum(alarm_counts.values())

        # Calculate network health score
        health_score = self._calculate_network_health_score(
            online_devices, total_devices, total_active_alarms
        )

        # Get recent events count
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        recent_events = self.db.query(NetworkEvent).filter(
            and_(
                NetworkEvent.tenant_id == self.tenant_id,
                NetworkEvent.event_timestamp >= one_hour_ago
            )
        ).count()

        return {
            "network_health": {
                "overall_score": health_score,
                "status": self._get_health_status(health_score)
            },
            "device_summary": {
                "total_devices": total_devices,
                "online_devices": online_devices,
                "offline_devices": offline_devices,
                "availability_percentage": round((online_devices / max(total_devices, 1)) * 100, 2)
            },
            "alarm_summary": {
                "total_active": total_active_alarms,
                "by_severity": alarm_counts,
                "critical_count": alarm_counts.get("critical", 0),
                "major_count": alarm_counts.get("major", 0)
            },
            "activity_summary": {
                "recent_events_1h": recent_events,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }

    @standard_exception_handler
    async def get_device_status_summary(
        self, 
        limit: int = 50,
        include_metrics: bool = True
    ) -> Dict[str, Any]:
        """Get summary of device statuses with latest metrics."""
        devices = self.db.query(Device).filter(
            Device.tenant_id == self.tenant_id
        ).order_by(Device.hostname).limit(limit).all()

        device_summaries = []
        
        for device in devices:
            device_data = {
                "device_id": device.device_id,
                "hostname": device.hostname,
                "device_type": device.device_type,
                "status": device.status,
                "site_id": device.site_id,
                "management_ip": device.management_ip,
                "last_seen": device.updated_at.isoformat() if device.updated_at else None
            }

            if include_metrics:
                # Get latest monitoring data
                latest_metrics = await self._get_device_latest_metrics(device.device_id)
                device_data["metrics"] = latest_metrics
                
                # Get active alarms for device
                device_alarms = self.db.query(Alarm).filter(
                    and_(
                        Alarm.tenant_id == self.tenant_id,
                        Alarm.device_id == device.device_id,
                        Alarm.status == AlarmStatus.ACTIVE
                    )
                ).count()
                
                device_data["active_alarms"] = device_alarms

            device_summaries.append(device_data)

        return {
            "devices": device_summaries,
            "total_count": len(device_summaries),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    @standard_exception_handler
    async def get_active_alarms_dashboard(
        self, 
        severity_filter: Optional[List[str]] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Get active alarms for dashboard display."""
        query = self.db.query(Alarm).filter(
            and_(
                Alarm.tenant_id == self.tenant_id,
                Alarm.status == AlarmStatus.ACTIVE
            )
        )

        if severity_filter:
            query = query.filter(Alarm.severity.in_(severity_filter))

        alarms = query.order_by(
            desc(Alarm.severity),
            desc(Alarm.last_occurrence)
        ).limit(limit).all()

        # Group by severity for dashboard display
        alarms_by_severity = {}
        for severity in AlarmSeverity:
            alarms_by_severity[severity.value] = []

        alarm_summaries = []
        for alarm in alarms:
            alarm_data = {
                "alarm_id": alarm.alarm_id,
                "alarm_type": alarm.alarm_type,
                "severity": alarm.severity,
                "title": alarm.title,
                "device_id": alarm.device_id,
                "customer_id": alarm.customer_id,
                "first_occurrence": alarm.first_occurrence.isoformat(),
                "last_occurrence": alarm.last_occurrence.isoformat(),
                "occurrence_count": alarm.occurrence_count,
                "acknowledged": alarm.acknowledged_at is not None,
                "acknowledged_by": alarm.acknowledged_by,
                "context_data": alarm.context_data,
                "age_minutes": int((datetime.now(timezone.utc) - alarm.first_occurrence).total_seconds() / 60)
            }
            
            alarm_summaries.append(alarm_data)
            alarms_by_severity[alarm.severity].append(alarm_data)

        return {
            "alarms": alarm_summaries,
            "alarms_by_severity": alarms_by_severity,
            "total_count": len(alarm_summaries),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    @standard_exception_handler
    async def get_network_performance_metrics(self) -> Dict[str, Any]:
        """Get network-wide performance metrics."""
        # Get metrics from last 24 hours
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        
        # Aggregate CPU usage across all devices
        cpu_metrics = self.db.query(
            func.avg(func.cast(func.json_extract(MonitoringRecord.metrics, '$.cpu_usage'), float)).label('avg_cpu'),
            func.max(func.cast(func.json_extract(MonitoringRecord.metrics, '$.cpu_usage'), float)).label('max_cpu'),
            func.count(MonitoringRecord.id).label('sample_count')
        ).filter(
            and_(
                MonitoringRecord.tenant_id == self.tenant_id,
                MonitoringRecord.collection_timestamp >= since,
                MonitoringRecord.collection_status == 'success',
                func.json_extract(MonitoringRecord.metrics, '$.cpu_usage').isnot(None)
            )
        ).first()

        # Aggregate memory usage
        memory_metrics = self.db.query(
            func.avg(func.cast(func.json_extract(MonitoringRecord.metrics, '$.memory_usage'), float)).label('avg_memory'),
            func.max(func.cast(func.json_extract(MonitoringRecord.metrics, '$.memory_usage'), float)).label('max_memory')
        ).filter(
            and_(
                MonitoringRecord.tenant_id == self.tenant_id,
                MonitoringRecord.collection_timestamp >= since,
                MonitoringRecord.collection_status == 'success',
                func.json_extract(MonitoringRecord.metrics, '$.memory_usage').isnot(None)
            )
        ).first()

        # Get interface statistics
        interface_stats = self.db.query(
            func.count(func.distinct(MonitoringRecord.device_id)).label('monitored_devices'),
            func.sum(
                func.cast(
                    func.json_extract(MonitoringRecord.metrics, '$.interfaces_up'), 
                    int
                )
            ).label('total_interfaces_up'),
            func.sum(
                func.cast(
                    func.json_extract(MonitoringRecord.metrics, '$.interfaces_down'),
                    int
                )
            ).label('total_interfaces_down')
        ).filter(
            and_(
                MonitoringRecord.tenant_id == self.tenant_id,
                MonitoringRecord.collection_timestamp >= since,
                MonitoringRecord.collection_status == 'success'
            )
        ).first()

        return {
            "cpu_utilization": {
                "average_percent": round(float(cpu_metrics.avg_cpu or 0), 2),
                "peak_percent": round(float(cpu_metrics.max_cpu or 0), 2),
                "sample_count": cpu_metrics.sample_count or 0
            },
            "memory_utilization": {
                "average_percent": round(float(memory_metrics.avg_memory or 0), 2),
                "peak_percent": round(float(memory_metrics.max_memory or 0), 2)
            },
            "interface_summary": {
                "monitored_devices": interface_stats.monitored_devices or 0,
                "total_interfaces_up": interface_stats.total_interfaces_up or 0,
                "total_interfaces_down": interface_stats.total_interfaces_down or 0,
                "availability_percentage": round(
                    ((interface_stats.total_interfaces_up or 0) / 
                     max(((interface_stats.total_interfaces_up or 0) + (interface_stats.total_interfaces_down or 0)), 1)) * 100, 
                    2
                )
            },
            "measurement_period": "24_hours",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    @standard_exception_handler
    async def get_recent_events(
        self, 
        hours: int = 24,
        severity_filter: Optional[List[str]] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Get recent network events for timeline view."""
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        query = self.db.query(NetworkEvent).filter(
            and_(
                NetworkEvent.tenant_id == self.tenant_id,
                NetworkEvent.event_timestamp >= since
            )
        )

        if severity_filter:
            query = query.filter(NetworkEvent.severity.in_(severity_filter))

        events = query.order_by(
            desc(NetworkEvent.event_timestamp)
        ).limit(limit).all()

        event_summaries = []
        for event in events:
            event_data = {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "severity": event.severity,
                "title": event.title,
                "device_id": event.device_id,
                "customer_id": event.customer_id,
                "event_timestamp": event.event_timestamp.isoformat(),
                "age_minutes": int((datetime.now(timezone.utc) - event.event_timestamp).total_seconds() / 60),
                "category": event.category,
                "source_system": event.source_system
            }
            event_summaries.append(event_data)

        # Group events by hour for timeline
        events_by_hour = {}
        for event in event_summaries:
            hour_key = event["event_timestamp"][:13]  # YYYY-MM-DDTHH
            if hour_key not in events_by_hour:
                events_by_hour[hour_key] = []
            events_by_hour[hour_key].append(event)

        return {
            "events": event_summaries,
            "events_by_hour": events_by_hour,
            "total_count": len(event_summaries),
            "time_range_hours": hours,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    @standard_exception_handler  
    async def get_dashboard_widgets_data(self) -> Dict[str, Any]:
        """Get all dashboard widget data in single call for efficiency."""
        # Run multiple queries concurrently using the database
        network_overview = await self.get_network_status_overview()
        performance_metrics = await self.get_network_performance_metrics()
        active_alarms = await self.get_active_alarms_dashboard(limit=20)
        recent_events = await self.get_recent_events(hours=6, limit=50)

        return {
            "network_overview": network_overview,
            "performance_metrics": performance_metrics,
            "active_alarms": {
                "total_count": active_alarms["total_count"],
                "by_severity": active_alarms["alarms_by_severity"],
                "recent_alarms": active_alarms["alarms"][:10]  # Top 10 for widget
            },
            "recent_activity": {
                "event_count": recent_events["total_count"],
                "recent_events": recent_events["events"][:15]  # Top 15 for widget
            },
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

    # Private helper methods
    
    def _calculate_network_health_score(
        self, online_devices: int, total_devices: int, active_alarms: int
    ) -> float:
        """Calculate overall network health score (0-100)."""
        if total_devices == 0:
            return 100.0

        # Device availability contributes 60% to health score
        availability_score = (online_devices / total_devices) * 60

        # Alarm impact contributes 40% to health score (fewer alarms = better score)
        if active_alarms == 0:
            alarm_score = 40.0
        else:
            # Logarithmic penalty for alarms
            import math
            alarm_penalty = min(40, math.log(active_alarms + 1) * 10)
            alarm_score = max(0, 40 - alarm_penalty)

        total_score = availability_score + alarm_score
        return round(min(100.0, max(0.0, total_score)), 1)

    def _get_health_status(self, health_score: float) -> str:
        """Convert health score to status label."""
        if health_score >= 90:
            return "excellent"
        elif health_score >= 75:
            return "good"
        elif health_score >= 60:
            return "fair"
        elif health_score >= 40:
            return "poor"
        else:
            return "critical"

    async def _get_device_latest_metrics(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get latest metrics for a specific device."""
        latest_record = self.db.query(MonitoringRecord).filter(
            and_(
                MonitoringRecord.device_id == device_id,
                MonitoringRecord.tenant_id == self.tenant_id,
                MonitoringRecord.collection_status == 'success'
            )
        ).order_by(desc(MonitoringRecord.collection_timestamp)).first()

        if not latest_record:
            return None

        metrics = latest_record.metrics or {}
        return {
            "cpu_usage": metrics.get("cpu_usage"),
            "memory_usage": metrics.get("memory_usage"),
            "interfaces_up": metrics.get("interfaces_up"),
            "interfaces_down": metrics.get("interfaces_down"),
            "system_uptime": metrics.get("system_uptime"),
            "last_collection": latest_record.collection_timestamp.isoformat(),
            "collection_status": latest_record.collection_status
        }