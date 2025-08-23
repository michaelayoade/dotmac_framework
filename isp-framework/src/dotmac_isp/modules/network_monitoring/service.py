"""Network Monitoring service layer for business logic."""

import asyncio
import json
import socket
import time
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session

from .repository import (
    MonitoringProfileRepository,
    SnmpDeviceRepository,
    SnmpMetricRepository,
    MonitoringAlertRepository,
    AlertRuleRepository,
    MonitoringScheduleRepository,
)
from .models import (
    MonitoringProfile,
    SnmpDevice,
    SnmpMetric,
    MonitoringAlert,
    AlertRule,
    MonitoringSchedule,
    MonitoringStatus,
    AlertSeverity,
    AlertStatus,
    MetricType,
    DeviceStatus,
    ScheduleType,
)
from . import schemas
from dotmac_isp.shared.exceptions import NotFoundError, ValidationError, ServiceError


class MonitoringProfileService:
    """Service for monitoring profile management."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = UUID(tenant_id)
        self.profile_repo = MonitoringProfileRepository(db, self.tenant_id)

    async def create_profile(self, profile_data: Dict[str, Any]) -> MonitoringProfile:
        """Create a new monitoring profile."""
        # Validate OIDs
        if "oids_to_monitor" in profile_data:
            self._validate_oids(profile_data["oids_to_monitor"])

        # Set default OIDs if not provided
        if not profile_data.get("oids_to_monitor"):
            profile_data["oids_to_monitor"] = self._get_default_oids(
                profile_data.get("profile_type", "system")
            )

        return self.profile_repo.create(profile_data)

    async def get_profile(self, profile_id: UUID) -> MonitoringProfile:
        """Get monitoring profile by ID."""
        profile = self.profile_repo.get_by_id(profile_id)
        if not profile:
            raise NotFoundError(f"Monitoring profile with ID {profile_id} not found")
        return profile

    async def list_profiles(
        self,
        profile_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[MonitoringProfile]:
        """List monitoring profiles with filtering."""
        return self.profile_repo.list_profiles(profile_type, is_active, skip, limit)

    async def update_profile(
        self, profile_id: UUID, update_data: Dict[str, Any]
    ) -> MonitoringProfile:
        """Update monitoring profile."""
        if "oids_to_monitor" in update_data:
            self._validate_oids(update_data["oids_to_monitor"])

        profile = self.profile_repo.update(profile_id, update_data)
        if not profile:
            raise NotFoundError(f"Monitoring profile with ID {profile_id} not found")
        return profile

    def _validate_oids(self, oids: List[Dict[str, Any]]) -> None:
        """Validate SNMP OIDs."""
        for oid_config in oids:
            if not isinstance(oid_config, dict):
                raise ValidationError("OID configuration must be a dictionary")

            if "oid" not in oid_config:
                raise ValidationError("OID configuration must include 'oid' field")

            oid = oid_config["oid"]
            if not oid.startswith(".") and not oid.startswith("1."):
                raise ValidationError(f"Invalid OID format: {oid}")

    def _get_default_oids(self, profile_type: str) -> List[Dict[str, Any]]:
        """Get default OIDs for profile type."""
        default_oids = {
            "system": [
                {"oid": "1.3.6.1.2.1.1.3.0", "name": "sysUpTime", "type": "gauge"},
                {"oid": "1.3.6.1.2.1.1.5.0", "name": "sysName", "type": "string"},
                {"oid": "1.3.6.1.2.1.25.1.1.0", "name": "hostUptime", "type": "gauge"},
                {"oid": "1.3.6.1.2.1.25.3.3.1.2", "name": "cpuLoad", "type": "gauge"},
                {"oid": "1.3.6.1.2.1.25.2.2.0", "name": "memorySize", "type": "gauge"},
            ],
            "interface": [
                {
                    "oid": "1.3.6.1.2.1.2.2.1.10",
                    "name": "ifInOctets",
                    "type": "counter",
                },
                {
                    "oid": "1.3.6.1.2.1.2.2.1.16",
                    "name": "ifOutOctets",
                    "type": "counter",
                },
                {"oid": "1.3.6.1.2.1.2.2.1.8", "name": "ifOperStatus", "type": "gauge"},
                {
                    "oid": "1.3.6.1.2.1.2.2.1.7",
                    "name": "ifAdminStatus",
                    "type": "gauge",
                },
            ],
            "custom": [],
        }
        return default_oids.get(profile_type, default_oids["system"])


class SnmpDeviceService:
    """Service for SNMP device management."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = UUID(tenant_id)
        self.device_repo = SnmpDeviceRepository(db, self.tenant_id)
        self.profile_repo = MonitoringProfileRepository(db, self.tenant_id)
        self.metric_repo = SnmpMetricRepository(db, self.tenant_id)

    async def add_device(self, device_data: Dict[str, Any]) -> SnmpDevice:
        """Add a new SNMP device for monitoring."""
        # Validate monitoring profile exists
        profile = self.profile_repo.get_by_id(device_data["monitoring_profile_id"])
        if not profile:
            raise ValidationError("Monitoring profile not found")

        # Validate IP address
        try:
            socket.inet_aton(device_data["device_ip"])
        except socket.error:
            raise ValidationError("Invalid IP address format")

        # Test SNMP connectivity
        if await self._test_snmp_connectivity(device_data["device_ip"], profile):
            device_data["availability_status"] = DeviceStatus.UP
        else:
            device_data["availability_status"] = DeviceStatus.DOWN

        device = self.device_repo.create(device_data)

        # Auto-discover device information
        try:
            await self._discover_device_info(device.id)
        except Exception as e:
            # Log error but don't fail device creation
            pass

        return device

    async def get_device(self, device_id: UUID) -> SnmpDevice:
        """Get SNMP device by ID."""
        device = self.device_repo.get_by_id(device_id)
        if not device:
            raise NotFoundError(f"SNMP device with ID {device_id} not found")
        return device

    async def list_devices(
        self,
        monitoring_profile_id: Optional[UUID] = None,
        monitoring_status: Optional[MonitoringStatus] = None,
        availability_status: Optional[DeviceStatus] = None,
        monitoring_enabled: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[SnmpDevice]:
        """List SNMP devices with filtering."""
        return self.device_repo.list_devices(
            monitoring_profile_id,
            monitoring_status,
            availability_status,
            monitoring_enabled,
            skip,
            limit,
        )

    async def enable_monitoring(self, device_id: UUID) -> SnmpDevice:
        """Enable monitoring for a device."""
        device = await self.get_device(device_id)
        device.monitoring_enabled = True
        device.monitoring_status = MonitoringStatus.ACTIVE

        self.db.commit()
        self.db.refresh(device)
        return device

    async def disable_monitoring(self, device_id: UUID) -> SnmpDevice:
        """Disable monitoring for a device."""
        device = await self.get_device(device_id)
        device.monitoring_enabled = False
        device.monitoring_status = MonitoringStatus.DISABLED

        self.db.commit()
        self.db.refresh(device)
        return device

    async def _test_snmp_connectivity(
        self, device_ip: str, profile: MonitoringProfile
    ) -> bool:
        """Test SNMP connectivity to device."""
        try:
            # Simple SNMP get for sysUpTime
            # In production, would use pysnmp or similar library
            import subprocess

            result = subprocess.run(
                [
                    "snmpget",
                    "-v2c",
                    "-c",
                    profile.snmp_community or "public",
                    device_ip,
                    "1.3.6.1.2.1.1.3.0",
                ],
                capture_output=True,
                timeout=profile.snmp_timeout or 5,
            )
            return result.returncode == 0
        except Exception:
            return False

    async def _discover_device_info(self, device_id: UUID) -> None:
        """Auto-discover device information via SNMP."""
        device = await self.get_device(device_id)
        profile = self.profile_repo.get_by_id(device.monitoring_profile_id)

        if not profile:
            return

        # Discover system information
        sys_info = await self._get_system_info(device, profile)
        if sys_info:
            self.device_repo.update_system_info(device_id, sys_info)

    async def _get_system_info(
        self, device: SnmpDevice, profile: MonitoringProfile
    ) -> Dict[str, Any]:
        """Get system information via SNMP."""
        # In production, would use proper SNMP library
        # For now, return mock data
        return {
            "sys_description": f"Mock device description for {device.device_name}",
            "sys_location": "Unknown location",
            "sys_contact": "admin@example.com",
        }


class NetworkMonitoringService:
    """Service for network monitoring operations."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = UUID(tenant_id)
        self.device_repo = SnmpDeviceRepository(db, self.tenant_id)
        self.metric_repo = SnmpMetricRepository(db, self.tenant_id)
        self.alert_repo = MonitoringAlertRepository(db, self.tenant_id)
        self.rule_repo = AlertRuleRepository(db, self.tenant_id)
        self.profile_repo = MonitoringProfileRepository(db, self.tenant_id)

    async def collect_device_metrics(self, device_id: UUID) -> List[SnmpMetric]:
        """Collect metrics from a specific device."""
        device = self.device_repo.get_by_id(device_id)
        if not device or not device.monitoring_enabled:
            raise ValidationError("Device not found or monitoring not enabled")

        profile = self.profile_repo.get_by_id(device.monitoring_profile_id)
        if not profile:
            raise ValidationError("Monitoring profile not found")

        start_time = time.time()
        metrics_data = []

        try:
            # Test device availability
            is_available = await self._test_device_availability(device)

            if is_available:
                # Collect configured metrics
                for oid_config in profile.oids_to_monitor:
                    try:
                        value = await self._get_snmp_value(device, profile, oid_config)
                        if value is not None:
                            metrics_data.append(
                                {
                                    "device_id": device_id,
                                    "metric_name": oid_config["name"],
                                    "metric_oid": oid_config["oid"],
                                    "metric_type": oid_config.get("type", "gauge"),
                                    "value": value,
                                    "collection_time_ms": (time.time() - start_time)
                                    * 1000,
                                }
                            )
                    except Exception as e:
                        # Log error and continue with other metrics
                        continue

                # Update device status
                self.device_repo.update_availability_status(
                    device_id, DeviceStatus.UP, (time.time() - start_time) * 1000
                )
                self.device_repo.update_monitoring_status(
                    device_id, MonitoringStatus.ACTIVE
                )
            else:
                # Device is down
                self.device_repo.update_availability_status(
                    device_id, DeviceStatus.DOWN
                )

                # Create availability alert
                await self._create_availability_alert(device)

            # Store metrics in bulk
            if metrics_data:
                metrics = self.metric_repo.create_bulk(metrics_data)

                # Check alert rules
                await self._evaluate_alert_rules(device_id, metrics)

                return metrics

        except Exception as e:
            # Update monitoring status to failed
            self.device_repo.update_monitoring_status(
                device_id, MonitoringStatus.FAILED, str(e)
            )
            raise ServiceError(
                f"Metric collection failed for device {device.device_name}: {str(e)}"
            )

        return []

    async def collect_all_metrics(self) -> Dict[str, Any]:
        """Collect metrics from all monitored devices."""
        devices = self.device_repo.get_devices_for_monitoring()

        results = {
            "total_devices": len(devices),
            "successful_collections": 0,
            "failed_collections": 0,
            "total_metrics_collected": 0,
            "collection_errors": [],
        }

        for device in devices:
            try:
                metrics = await self.collect_device_metrics(device.id)
                results["successful_collections"] += 1
                results["total_metrics_collected"] += len(metrics)
            except Exception as e:
                results["failed_collections"] += 1
                results["collection_errors"].append(
                    {
                        "device_id": str(device.id),
                        "device_name": device.device_name,
                        "error": str(e),
                    }
                )

        return results

    async def get_device_metrics(
        self,
        device_id: UUID,
        metric_names: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        aggregation: Optional[str] = None,
        interval_minutes: int = 5,
    ) -> List[Dict[str, Any]]:
        """Get device metrics with optional filtering and aggregation."""
        if not start_time:
            start_time = datetime.utcnow() - timedelta(hours=24)
        if not end_time:
            end_time = datetime.utcnow()

        device = self.device_repo.get_by_id(device_id)
        if not device:
            raise NotFoundError(f"Device with ID {device_id} not found")

        results = {}

        if metric_names:
            for metric_name in metric_names:
                timeseries = self.metric_repo.get_metric_timeseries(
                    device_id,
                    metric_name,
                    start_time,
                    end_time,
                    aggregation,
                    interval_minutes,
                )
                results[metric_name] = timeseries
        else:
            # Get all metrics
            metrics = self.metric_repo.get_latest_metrics(device_id, None, 24)
            unique_metrics = list(set(m.metric_name for m in metrics))

            for metric_name in unique_metrics:
                timeseries = self.metric_repo.get_metric_timeseries(
                    device_id,
                    metric_name,
                    start_time,
                    end_time,
                    aggregation,
                    interval_minutes,
                )
                results[metric_name] = timeseries

        return results

    async def _test_device_availability(self, device: SnmpDevice) -> bool:
        """Test if device is available via ping and SNMP."""
        # Ping test
        import subprocess

        try:
            ping_result = subprocess.run(
                ["ping", "-c", "1", "-W", "5", str(device.device_ip)],
                capture_output=True,
                timeout=10,
            )

            if ping_result.returncode != 0:
                return False
        except Exception:
            return False

        # SNMP test
        profile = self.profile_repo.get_by_id(device.monitoring_profile_id)
        if profile:
            try:
                # Simple SNMP get for sysUpTime
                snmp_result = subprocess.run(
                    [
                        "snmpget",
                        "-v2c",
                        "-c",
                        profile.snmp_community or "public",
                        str(device.device_ip),
                        "1.3.6.1.2.1.1.3.0",
                    ],
                    capture_output=True,
                    timeout=profile.snmp_timeout or 5,
                )
                return snmp_result.returncode == 0
            except Exception:
                return False

        return True

    async def _get_snmp_value(
        self, device: SnmpDevice, profile: MonitoringProfile, oid_config: Dict[str, Any]
    ) -> Optional[float]:
        """Get SNMP value for specific OID."""
        # In production, would use proper SNMP library like pysnmp
        # For now, return mock values based on OID
        import random

        oid = oid_config["oid"]
        metric_type = oid_config.get("type", "gauge")

        # Mock values based on common OIDs
        if "cpu" in oid_config["name"].lower():
            return random.uniform(10, 90)
        elif "memory" in oid_config["name"].lower():
            return random.uniform(1000000, 8000000)  # bytes
        elif "uptime" in oid_config["name"].lower():
            return random.uniform(100000, 10000000)  # timeticks
        elif "octets" in oid_config["name"].lower():
            return random.uniform(1000000, 100000000)  # bytes
        elif "status" in oid_config["name"].lower():
            return random.choice([1, 2])  # up/down
        else:
            return random.uniform(0, 100)

    async def _create_availability_alert(self, device: SnmpDevice) -> MonitoringAlert:
        """Create device availability alert."""
        return self.alert_repo.create(
            {
                "device_id": device.id,
                "alert_name": f"Device {device.device_name} Unavailable",
                "alert_type": "device_down",
                "title": f"Device {device.device_name} is unreachable",
                "description": f"Device {device.device_name} ({device.device_ip}) is not responding to ping or SNMP requests",
                "severity": AlertSeverity.CRITICAL,
                "status": AlertStatus.ACTIVE,
            }
        )

    async def _evaluate_alert_rules(
        self, device_id: UUID, metrics: List[SnmpMetric]
    ) -> None:
        """Evaluate alert rules against collected metrics."""
        # Get alert rules for this device's profile
        device = self.device_repo.get_by_id(device_id)
        if not device:
            return

        rules = self.rule_repo.list_rules(
            monitoring_profile_id=device.monitoring_profile_id, enabled=True
        )

        for rule in rules:
            # Find metrics that match this rule
            matching_metrics = [m for m in metrics if m.metric_name == rule.metric_name]

            for metric in matching_metrics:
                if await self._check_threshold_violation(rule, metric):
                    await self._create_threshold_alert(rule, device, metric)
                    self.rule_repo.increment_alert_count(rule.id)

            # Update rule evaluation
            self.rule_repo.update_rule_evaluation(rule.id)

    async def _check_threshold_violation(
        self, rule: AlertRule, metric: SnmpMetric
    ) -> bool:
        """Check if metric violates alert rule threshold."""
        metric_value = float(metric.value)
        threshold_value = float(rule.threshold_value)

        if rule.condition_operator == ">":
            return metric_value > threshold_value
        elif rule.condition_operator == "<":
            return metric_value < threshold_value
        elif rule.condition_operator == ">=":
            return metric_value >= threshold_value
        elif rule.condition_operator == "<=":
            return metric_value <= threshold_value
        elif rule.condition_operator == "=":
            return metric_value == threshold_value
        elif rule.condition_operator == "!=":
            return metric_value != threshold_value

        return False

    async def _create_threshold_alert(
        self, rule: AlertRule, device: SnmpDevice, metric: SnmpMetric
    ) -> MonitoringAlert:
        """Create threshold violation alert."""
        return self.alert_repo.create(
            {
                "device_id": device.id,
                "alert_rule_id": rule.id,
                "alert_name": rule.rule_name,
                "alert_type": rule.rule_type,
                "title": f"{rule.rule_name} - {device.device_name}",
                "description": f"Metric {rule.metric_name} value {metric.value} {rule.condition_operator} threshold {rule.threshold_value}",
                "severity": rule.alert_severity,
                "status": AlertStatus.ACTIVE,
                "metric_name": rule.metric_name,
                "metric_value": metric.value,
                "threshold_value": rule.threshold_value,
                "threshold_operator": rule.condition_operator,
            }
        )


class AlertManagementService:
    """Service for alert management operations."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = UUID(tenant_id)
        self.alert_repo = MonitoringAlertRepository(db, self.tenant_id)
        self.rule_repo = AlertRuleRepository(db, self.tenant_id)

    async def get_alert(self, alert_id: UUID) -> MonitoringAlert:
        """Get alert by ID."""
        alert = self.alert_repo.get_by_id(alert_id)
        if not alert:
            raise NotFoundError(f"Alert with ID {alert_id} not found")
        return alert

    async def list_alerts(
        self,
        device_id: Optional[UUID] = None,
        status: Optional[AlertStatus] = None,
        severity: Optional[AlertSeverity] = None,
        alert_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[MonitoringAlert]:
        """List alerts with filtering."""
        return self.alert_repo.list_alerts(
            device_id, status, severity, alert_type, start_time, end_time, skip, limit
        )

    async def acknowledge_alert(
        self, alert_id: UUID, user_id: UUID, comment: Optional[str] = None
    ) -> MonitoringAlert:
        """Acknowledge an alert."""
        alert = self.alert_repo.acknowledge_alert(alert_id, user_id, comment)
        if not alert:
            raise NotFoundError(f"Alert with ID {alert_id} not found")
        return alert

    async def resolve_alert(
        self, alert_id: UUID, user_id: UUID, comment: Optional[str] = None
    ) -> MonitoringAlert:
        """Resolve an alert."""
        alert = self.alert_repo.resolve_alert(alert_id, user_id, comment)
        if not alert:
            raise NotFoundError(f"Alert with ID {alert_id} not found")
        return alert

    async def create_alert_rule(self, rule_data: Dict[str, Any]) -> AlertRule:
        """Create new alert rule."""
        # Validate monitoring profile exists
        profile_repo = MonitoringProfileRepository(self.db, self.tenant_id)
        profile = profile_repo.get_by_id(rule_data["monitoring_profile_id"])
        if not profile:
            raise ValidationError("Monitoring profile not found")

        # Validate threshold operator
        valid_operators = [">", "<", ">=", "<=", "=", "!="]
        if rule_data["condition_operator"] not in valid_operators:
            raise ValidationError(
                f"Invalid condition operator. Must be one of: {valid_operators}"
            )

        return self.rule_repo.create(rule_data)

    async def get_alert_summary(self) -> Dict[str, Any]:
        """Get alert summary statistics."""
        # Get counts by status
        status_counts = {}
        for status in AlertStatus:
            count = len(self.alert_repo.list_alerts(status=status, limit=10000))
            status_counts[status.value] = count

        # Get counts by severity
        severity_counts = {}
        for severity in AlertSeverity:
            count = len(self.alert_repo.list_alerts(severity=severity, limit=10000))
            severity_counts[severity.value] = count

        # Get recent alerts
        recent_alerts = self.alert_repo.list_alerts(limit=10)

        # Get active critical alerts
        critical_alerts = self.alert_repo.list_alerts(
            status=AlertStatus.ACTIVE, severity=AlertSeverity.CRITICAL, limit=100
        )

        return {
            "status_counts": status_counts,
            "severity_counts": severity_counts,
            "total_active_alerts": status_counts.get("active", 0),
            "critical_alerts_count": len(critical_alerts),
            "recent_alerts": [
                {
                    "id": str(alert.id),
                    "alert_name": alert.alert_name,
                    "severity": alert.severity.value,
                    "status": alert.status.value,
                    "created_at": alert.created_at.isoformat(),
                    "device_name": alert.device.device_name if alert.device else None,
                }
                for alert in recent_alerts
            ],
            "last_updated": datetime.utcnow().isoformat(),
        }


class NetworkMonitoringMainService:
    """Main service orchestrating all network monitoring operations."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.profile_service = MonitoringProfileService(db, tenant_id)
        self.device_service = SnmpDeviceService(db, tenant_id)
        self.monitoring_service = NetworkMonitoringService(db, tenant_id)
        self.alert_service = AlertManagementService(db, tenant_id)
        self.metric_repo = SnmpMetricRepository(db, UUID(tenant_id))

    async def setup_device_monitoring(
        self,
        device_data: schemas.SnmpDeviceCreate,
        profile_data: Optional[schemas.MonitoringProfileCreate] = None,
    ) -> SnmpDevice:
        """Setup complete monitoring for a device."""
        # Create monitoring profile if provided
        if profile_data:
            profile = await self.profile_service.create_profile(profile_data.dict())
            device_data.monitoring_profile_id = profile.id

        # Add device to monitoring
        device = await self.device_service.add_device(device_data.dict())

        # Create default alert rules
        await self._create_default_alert_rules(device.monitoring_profile_id)

        return device

    async def get_monitoring_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive monitoring dashboard data."""
        # Get device statistics
        devices = await self.device_service.list_devices(limit=1000)
        device_stats = {
            "total_devices": len(devices),
            "up_devices": len(
                [d for d in devices if d.availability_status == DeviceStatus.UP]
            ),
            "down_devices": len(
                [d for d in devices if d.availability_status == DeviceStatus.DOWN]
            ),
            "monitoring_enabled": len([d for d in devices if d.monitoring_enabled]),
        }

        # Get alert summary
        alert_summary = await self.alert_service.get_alert_summary()

        # Get recent metrics count
        recent_metrics_count = (
            len(
                self.metric_repo.get_latest_metrics(
                    devices[0].id if devices else uuid4(), hours=1
                )
            )
            if devices
            else 0
        )

        # Calculate uptime percentage
        uptime_percentage = (
            (device_stats["up_devices"] / device_stats["total_devices"] * 100)
            if device_stats["total_devices"] > 0
            else 0
        )

        return {
            "device_statistics": device_stats,
            "alert_summary": alert_summary,
            "network_uptime_percentage": round(uptime_percentage, 2),
            "recent_metrics_collected": recent_metrics_count,
            "monitoring_status": (
                "healthy"
                if uptime_percentage > 95
                else "degraded" if uptime_percentage > 80 else "critical"
            ),
            "last_updated": datetime.utcnow().isoformat(),
        }

    async def _create_default_alert_rules(self, profile_id: UUID) -> List[AlertRule]:
        """Create default alert rules for monitoring profile."""
        default_rules = [
            {
                "monitoring_profile_id": profile_id,
                "rule_name": "High CPU Usage",
                "rule_type": "threshold",
                "metric_name": "cpuLoad",
                "condition_operator": ">",
                "threshold_value": 80,
                "alert_severity": AlertSeverity.HIGH,
                "evaluation_window": 300,
                "consecutive_violations": 2,
            },
            {
                "monitoring_profile_id": profile_id,
                "rule_name": "Device Unreachable",
                "rule_type": "availability",
                "metric_name": "sysUpTime",
                "condition_operator": "=",
                "threshold_value": 0,
                "alert_severity": AlertSeverity.CRITICAL,
                "evaluation_window": 60,
                "consecutive_violations": 1,
            },
        ]

        rules = []
        for rule_data in default_rules:
            try:
                rule = await self.alert_service.create_alert_rule(rule_data)
                rules.append(rule)
            except Exception:
                # Skip if rule creation fails
                continue

        return rules
