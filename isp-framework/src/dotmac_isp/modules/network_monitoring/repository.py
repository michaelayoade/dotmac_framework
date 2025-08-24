"""Repository pattern for network monitoring database operations."""

from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, func, desc, asc, text

from .models import (
    MonitoringProfile,
    SnmpDevice,
    SnmpMetric,
    MonitoringAlert,
    AlertRule,
    MonitoringSchedule,
    DeviceAvailability,
    InterfaceMetric,
    SystemMetric,
    MonitoringStatus,
    AlertSeverity,
    AlertStatus,
    MetricType,
    DeviceStatus,
    ScheduleType,
)
from dotmac_isp.shared.exceptions import NotFoundError, ConflictError, ValidationError


class MonitoringProfileRepository:
    """Repository for monitoring profile database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        """  Init   operation."""
        self.db = db
        self.tenant_id = tenant_id

    def create(self, profile_data: Dict[str, Any]) -> MonitoringProfile:
        """Create new monitoring profile."""
        try:
            profile = MonitoringProfile(
                id=uuid4(), tenant_id=self.tenant_id, **profile_data
            )

            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)
            return profile

        except IntegrityError as e:
            self.db.rollback()
            if "profile_name" in str(e):
                raise ConflictError(
                    f"Monitoring profile name {profile_data.get('profile_name')} already exists"
                )
            raise ConflictError(
                "Monitoring profile creation failed due to data conflict"
            )

    def get_by_id(self, profile_id: UUID) -> Optional[MonitoringProfile]:
        """Get monitoring profile by ID."""
        return (
            self.db.query(MonitoringProfile)
            .filter(
                and_(
                    MonitoringProfile.id == profile_id,
                    MonitoringProfile.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    def get_by_name(self, profile_name: str) -> Optional[MonitoringProfile]:
        """Get monitoring profile by name."""
        return (
            self.db.query(MonitoringProfile)
            .filter(
                and_(
                    MonitoringProfile.profile_name == profile_name,
                    MonitoringProfile.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    def list_profiles(
        self,
        profile_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[MonitoringProfile]:
        """List monitoring profiles with filtering."""
        query = self.db.query(MonitoringProfile).filter(
            MonitoringProfile.tenant_id == self.tenant_id
        )

        if profile_type:
            query = query.filter(MonitoringProfile.profile_type == profile_type)
        if is_active is not None:
            query = query.filter(MonitoringProfile.is_active == is_active)

        return (
            query.order_by(MonitoringProfile.profile_name)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update(
        self, profile_id: UUID, update_data: Dict[str, Any]
    ) -> Optional[MonitoringProfile]:
        """Update monitoring profile."""
        profile = self.get_by_id(profile_id)
        if not profile:
            return None

        for key, value in update_data.items():
            if hasattr(profile, key):
                setattr(profile, key, value)

        profile.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(profile)
        return profile


class SnmpDeviceRepository:
    """Repository for SNMP device database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        """  Init   operation."""
        self.db = db
        self.tenant_id = tenant_id

    def create(self, device_data: Dict[str, Any]) -> SnmpDevice:
        """Create new SNMP device."""
        try:
            device = SnmpDevice(
                id=uuid4(),
                tenant_id=self.tenant_id,
                monitoring_status=MonitoringStatus.ACTIVE,
                availability_status=DeviceStatus.UNKNOWN,
                **device_data,
            )

            self.db.add(device)
            self.db.commit()
            self.db.refresh(device)
            return device

        except IntegrityError as e:
            self.db.rollback()
            if "device_ip" in str(e):
                raise ConflictError(
                    f"Device IP {device_data.get('device_ip')} already exists"
                )
            raise ConflictError("SNMP device creation failed due to data conflict")

    def get_by_id(self, device_id: UUID) -> Optional[SnmpDevice]:
        """Get SNMP device by ID."""
        return (
            self.db.query(SnmpDevice)
            .filter(
                and_(SnmpDevice.id == device_id, SnmpDevice.tenant_id == self.tenant_id)
            )
            .first()
        )

    def get_by_ip(self, device_ip: str) -> Optional[SnmpDevice]:
        """Get SNMP device by IP address."""
        return (
            self.db.query(SnmpDevice)
            .filter(
                and_(
                    SnmpDevice.device_ip == device_ip,
                    SnmpDevice.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    def get_by_name(self, device_name: str) -> Optional[SnmpDevice]:
        """Get SNMP device by name."""
        return (
            self.db.query(SnmpDevice)
            .filter(
                and_(
                    SnmpDevice.device_name == device_name,
                    SnmpDevice.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    def list_devices(
        self,
        monitoring_profile_id: Optional[UUID] = None,
        monitoring_status: Optional[MonitoringStatus] = None,
        availability_status: Optional[DeviceStatus] = None,
        monitoring_enabled: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[SnmpDevice]:
        """List SNMP devices with filtering."""
        query = self.db.query(SnmpDevice).filter(SnmpDevice.tenant_id == self.tenant_id)

        if monitoring_profile_id:
            query = query.filter(
                SnmpDevice.monitoring_profile_id == monitoring_profile_id
            )
        if monitoring_status:
            query = query.filter(SnmpDevice.monitoring_status == monitoring_status)
        if availability_status:
            query = query.filter(SnmpDevice.availability_status == availability_status)
        if monitoring_enabled is not None:
            query = query.filter(SnmpDevice.monitoring_enabled == monitoring_enabled)

        return query.order_by(SnmpDevice.device_name).offset(skip).limit(limit).all()

    def get_devices_for_monitoring(self) -> List[SnmpDevice]:
        """Get devices that need monitoring."""
        return (
            self.db.query(SnmpDevice)
            .filter(
                and_(
                    SnmpDevice.tenant_id == self.tenant_id,
                    SnmpDevice.monitoring_enabled == True,
                    SnmpDevice.monitoring_status == MonitoringStatus.ACTIVE,
                )
            )
            .all()
        )

    def update_monitoring_status(
        self, device_id: UUID, status: MonitoringStatus, error: Optional[str] = None
    ) -> Optional[SnmpDevice]:
        """Update device monitoring status."""
        device = self.get_by_id(device_id)
        if not device:
            return None

        device.monitoring_status = status
        device.last_monitored = datetime.utcnow()

        if status == MonitoringStatus.FAILED:
            device.consecutive_failures += 1
            if error:
                device.last_error = error
                device.last_error_time = datetime.utcnow()
        else:
            device.consecutive_failures = 0
            device.last_error = None

        self.db.commit()
        self.db.refresh(device)
        return device

    def update_availability_status(
        self,
        device_id: UUID,
        status: DeviceStatus,
        response_time_ms: Optional[float] = None,
    ) -> Optional[SnmpDevice]:
        """Update device availability status."""
        device = self.get_by_id(device_id)
        if not device:
            return None

        device.availability_status = status
        device.last_seen = (
            datetime.utcnow() if status == DeviceStatus.UP else device.last_seen
        )
        if response_time_ms is not None:
            device.response_time_ms = response_time_ms

        self.db.commit()
        self.db.refresh(device)
        return device

    def update_system_info(
        self, device_id: UUID, sys_info: Dict[str, Any]
    ) -> Optional[SnmpDevice]:
        """Update device system information."""
        device = self.get_by_id(device_id)
        if not device:
            return None

        for key, value in sys_info.items():
            if hasattr(device, key):
                setattr(device, key, value)

        self.db.commit()
        self.db.refresh(device)
        return device


class SnmpMetricRepository:
    """Repository for SNMP metric database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        """  Init   operation."""
        self.db = db
        self.tenant_id = tenant_id

    def create(self, metric_data: Dict[str, Any]) -> SnmpMetric:
        """Create new SNMP metric."""
        metric = SnmpMetric(
            id=uuid4(),
            tenant_id=self.tenant_id,
            timestamp=datetime.utcnow(),
            **metric_data,
        )

        self.db.add(metric)
        self.db.commit()
        self.db.refresh(metric)
        return metric

    def create_bulk(self, metrics_data: List[Dict[str, Any]]) -> List[SnmpMetric]:
        """Create multiple metrics in bulk."""
        metrics = []
        for metric_data in metrics_data:
            metric = SnmpMetric(
                id=uuid4(),
                tenant_id=self.tenant_id,
                timestamp=datetime.utcnow(),
                **metric_data,
            )
            metrics.append(metric)

        self.db.add_all(metrics)
        self.db.commit()
        return metrics

    def get_latest_metrics(
        self, device_id: UUID, metric_names: Optional[List[str]] = None, hours: int = 24
    ) -> List[SnmpMetric]:
        """Get latest metrics for a device."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        query = self.db.query(SnmpMetric).filter(
            and_(
                SnmpMetric.device_id == device_id,
                SnmpMetric.tenant_id == self.tenant_id,
                SnmpMetric.timestamp >= cutoff_time,
            )
        )

        if metric_names:
            query = query.filter(SnmpMetric.metric_name.in_(metric_names))

        return query.order_by(desc(SnmpMetric.timestamp)).all()

    def get_metric_timeseries(
        self,
        device_id: UUID,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
        aggregation: Optional[str] = None,
        interval_minutes: int = 5,
    ) -> List[Dict[str, Any]]:
        """Get metric timeseries data with optional aggregation."""
        query = self.db.query(SnmpMetric).filter(
            and_(
                SnmpMetric.device_id == device_id,
                SnmpMetric.metric_name == metric_name,
                SnmpMetric.tenant_id == self.tenant_id,
                SnmpMetric.timestamp >= start_time,
                SnmpMetric.timestamp <= end_time,
            )
        )

        if aggregation:
            # Group by time intervals and aggregate
            interval_seconds = interval_minutes * 60
            time_bucket = (
                func.floor(
                    func.extract("epoch", SnmpMetric.timestamp) / interval_seconds
                )
                * interval_seconds
            )

            if aggregation == "avg":
                agg_func = func.avg(SnmpMetric.value)
            elif aggregation == "max":
                agg_func = func.max(SnmpMetric.value)
            elif aggregation == "min":
                agg_func = func.min(SnmpMetric.value)
            elif aggregation == "sum":
                agg_func = func.sum(SnmpMetric.value)
            else:
                agg_func = func.avg(SnmpMetric.value)

            query = (
                self.db.query(
                    func.to_timestamp(time_bucket).label("timestamp"),
                    agg_func.label("value"),
                )
                .filter(
                    and_(
                        SnmpMetric.device_id == device_id,
                        SnmpMetric.metric_name == metric_name,
                        SnmpMetric.tenant_id == self.tenant_id,
                        SnmpMetric.timestamp >= start_time,
                        SnmpMetric.timestamp <= end_time,
                    )
                )
                .group_by(time_bucket)
                .order_by(time_bucket)
            )

            results = query.all()
            return [
                {"timestamp": r.timestamp, "value": float(r.value)} for r in results
            ]
        else:
            results = query.order_by(SnmpMetric.timestamp).all()
            return [
                {"timestamp": r.timestamp, "value": float(r.value)} for r in results
            ]

    def cleanup_old_metrics(self, retention_days: int = 30) -> int:
        """Clean up metrics older than retention period."""
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

        deleted_count = (
            self.db.query(SnmpMetric)
            .filter(
                and_(
                    SnmpMetric.tenant_id == self.tenant_id,
                    SnmpMetric.timestamp < cutoff_date,
                )
            )
            .delete()
        )

        self.db.commit()
        return deleted_count


class MonitoringAlertRepository:
    """Repository for network alert database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        """  Init   operation."""
        self.db = db
        self.tenant_id = tenant_id

    def create(self, alert_data: Dict[str, Any]) -> MonitoringAlert:
        """Create new network alert."""
        # Generate unique alert ID
        alert_id = f"alert_{int(datetime.utcnow().timestamp())}_{uuid4().hex[:8]}"

        alert = MonitoringAlert(
            id=uuid4(),
            tenant_id=self.tenant_id,
            alert_id=alert_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            **alert_data,
        )

        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert

    def get_by_id(self, alert_id: UUID) -> Optional[MonitoringAlert]:
        """Get alert by ID."""
        return (
            self.db.query(MonitoringAlert)
            .filter(
                and_(
                    MonitoringAlert.id == alert_id,
                    MonitoringAlert.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    def get_by_alert_id(self, alert_id: str) -> Optional[MonitoringAlert]:
        """Get alert by alert ID string."""
        return (
            self.db.query(MonitoringAlert)
            .filter(
                and_(
                    MonitoringAlert.alert_id == alert_id,
                    MonitoringAlert.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    def list_alerts(
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
        query = self.db.query(MonitoringAlert).filter(
            MonitoringAlert.tenant_id == self.tenant_id
        )

        if device_id:
            query = query.filter(MonitoringAlert.device_id == device_id)
        if status:
            query = query.filter(MonitoringAlert.status == status)
        if severity:
            query = query.filter(MonitoringAlert.severity == severity)
        if alert_type:
            query = query.filter(MonitoringAlert.alert_type == alert_type)
        if start_time:
            query = query.filter(MonitoringAlert.created_at >= start_time)
        if end_time:
            query = query.filter(MonitoringAlert.created_at <= end_time)

        return (
            query.order_by(desc(MonitoringAlert.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_active_alerts(self, device_id: Optional[UUID] = None) -> List[MonitoringAlert]:
        """Get active alerts."""
        query = self.db.query(MonitoringAlert).filter(
            and_(
                MonitoringAlert.tenant_id == self.tenant_id,
                MonitoringAlert.status == AlertStatus.ACTIVE,
            )
        )

        if device_id:
            query = query.filter(MonitoringAlert.device_id == device_id)

        return query.order_by(desc(MonitoringAlert.created_at)).all()

    def acknowledge_alert(
        self, alert_id: UUID, user_id: UUID, comment: Optional[str] = None
    ) -> Optional[MonitoringAlert]:
        """Acknowledge an alert."""
        alert = self.get_by_id(alert_id)
        if not alert:
            return None

        alert.acknowledge(str(user_id), comment)
        alert.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(alert)
        return alert

    def resolve_alert(
        self, alert_id: UUID, user_id: UUID, comment: Optional[str] = None
    ) -> Optional[MonitoringAlert]:
        """Resolve an alert."""
        alert = self.get_by_id(alert_id)
        if not alert:
            return None

        alert.resolve(str(user_id), comment)
        alert.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(alert)
        return alert


class AlertRuleRepository:
    """Repository for alert rule database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        """  Init   operation."""
        self.db = db
        self.tenant_id = tenant_id

    def create(self, rule_data: Dict[str, Any]) -> AlertRule:
        """Create new alert rule."""
        try:
            rule = AlertRule(id=uuid4(), tenant_id=self.tenant_id, **rule_data)

            self.db.add(rule)
            self.db.commit()
            self.db.refresh(rule)
            return rule

        except IntegrityError as e:
            self.db.rollback()
            if "rule_name" in str(e):
                raise ConflictError(
                    f"Alert rule name {rule_data.get('rule_name')} already exists"
                )
            raise ConflictError("Alert rule creation failed due to data conflict")

    def get_by_id(self, rule_id: UUID) -> Optional[AlertRule]:
        """Get alert rule by ID."""
        return (
            self.db.query(AlertRule)
            .filter(
                and_(AlertRule.id == rule_id, AlertRule.tenant_id == self.tenant_id)
            )
            .first()
        )

    def list_rules(
        self,
        monitoring_profile_id: Optional[UUID] = None,
        enabled: Optional[bool] = None,
        metric_name: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[AlertRule]:
        """List alert rules with filtering."""
        query = self.db.query(AlertRule).filter(AlertRule.tenant_id == self.tenant_id)

        if monitoring_profile_id:
            query = query.filter(
                AlertRule.monitoring_profile_id == monitoring_profile_id
            )
        if enabled is not None:
            query = query.filter(AlertRule.enabled == enabled)
        if metric_name:
            query = query.filter(AlertRule.metric_name == metric_name)

        return query.order_by(AlertRule.rule_name).offset(skip).limit(limit).all()

    def get_active_rules(self) -> List[AlertRule]:
        """Get all active alert rules."""
        return (
            self.db.query(AlertRule)
            .filter(
                and_(
                    AlertRule.tenant_id == self.tenant_id,
                    AlertRule.enabled == True,
                    AlertRule.is_active == True,
                )
            )
            .all()
        )

    def update_rule_evaluation(self, rule_id: UUID) -> Optional[AlertRule]:
        """Update rule evaluation timestamp and count."""
        rule = self.get_by_id(rule_id)
        if not rule:
            return None

        rule.last_evaluation = datetime.utcnow()
        rule.evaluation_count += 1

        self.db.commit()
        self.db.refresh(rule)
        return rule

    def increment_alert_count(self, rule_id: UUID) -> Optional[AlertRule]:
        """Increment alert count for rule."""
        rule = self.get_by_id(rule_id)
        if not rule:
            return None

        rule.alert_count += 1

        self.db.commit()
        self.db.refresh(rule)
        return rule


class MonitoringScheduleRepository:
    """Repository for monitoring schedule database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        """  Init   operation."""
        self.db = db
        self.tenant_id = tenant_id

    def create(self, schedule_data: Dict[str, Any]) -> MonitoringSchedule:
        """Create new monitoring schedule."""
        schedule = MonitoringSchedule(
            id=uuid4(), tenant_id=self.tenant_id, **schedule_data
        )

        self.db.add(schedule)
        self.db.commit()
        self.db.refresh(schedule)
        return schedule

    def get_by_id(self, schedule_id: UUID) -> Optional[MonitoringSchedule]:
        """Get monitoring schedule by ID."""
        return (
            self.db.query(MonitoringSchedule)
            .filter(
                and_(
                    MonitoringSchedule.id == schedule_id,
                    MonitoringSchedule.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    def get_active_schedules(
        self, device_id: Optional[UUID] = None
    ) -> List[MonitoringSchedule]:
        """Get active monitoring schedules."""
        query = self.db.query(MonitoringSchedule).filter(
            and_(
                MonitoringSchedule.tenant_id == self.tenant_id,
                MonitoringSchedule.enabled == True,
                MonitoringSchedule.is_active == True,
            )
        )

        if device_id:
            query = query.filter(MonitoringSchedule.device_id == device_id)

        return query.all()

    def update_execution_time(self, schedule_id: UUID) -> Optional[MonitoringSchedule]:
        """Update schedule last execution time."""
        schedule = self.get_by_id(schedule_id)
        if not schedule:
            return None

        schedule.last_execution = datetime.utcnow()
        schedule.execution_count += 1

        self.db.commit()
        self.db.refresh(schedule)
        return schedule
