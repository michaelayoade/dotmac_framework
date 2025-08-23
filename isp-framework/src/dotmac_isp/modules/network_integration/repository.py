"""Repository pattern for network integration database operations."""

from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, func, desc

from .models import (
    NetworkDevice,
    NetworkInterface,
    NetworkLocation,
    NetworkMetric,
    NetworkTopology,
    DeviceConfiguration,
    NetworkAlert,
    DeviceGroup,
    NetworkService,
    MaintenanceWindow,
    DeviceStatus,
    InterfaceStatus,
    AlertSeverity,
    AlertType,
)
from dotmac_isp.shared.exceptions import NotFoundError, ConflictError, ValidationError


class NetworkDeviceRepository:
    """Repository for network device database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def create(self, device_data: Dict[str, Any]) -> NetworkDevice:
        """Create new network device."""
        try:
            device = NetworkDevice(
                id=uuid4(),
                tenant_id=self.tenant_id,
                status=DeviceStatus.PROVISIONING,
                **device_data,
            )

            self.db.add(device)
            self.db.commit()
            self.db.refresh(device)
            return device

        except IntegrityError as e:
            self.db.rollback()
            if "hostname" in str(e):
                raise ConflictError(
                    f"Hostname {device_data.get('hostname')} already exists"
                )
            if "management_ip" in str(e):
                raise ConflictError(
                    f"Management IP {device_data.get('management_ip')} already exists"
                )
            if "serial_number" in str(e):
                raise ConflictError(
                    f"Serial number {device_data.get('serial_number')} already exists"
                )
            raise ConflictError("Device creation failed due to data conflict")

    def get_by_id(self, device_id: UUID) -> Optional[NetworkDevice]:
        """Get device by ID."""
        return (
            self.db.query(NetworkDevice)
            .filter(
                and_(
                    NetworkDevice.id == device_id,
                    NetworkDevice.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    def get_by_hostname(self, hostname: str) -> Optional[NetworkDevice]:
        """Get device by hostname."""
        return (
            self.db.query(NetworkDevice)
            .filter(
                and_(
                    NetworkDevice.hostname == hostname,
                    NetworkDevice.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    def get_by_management_ip(self, management_ip: str) -> Optional[NetworkDevice]:
        """Get device by management IP."""
        return (
            self.db.query(NetworkDevice)
            .filter(
                and_(
                    NetworkDevice.management_ip == management_ip,
                    NetworkDevice.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    def list_devices(
        self,
        device_type: Optional[str] = None,
        status: Optional[DeviceStatus] = None,
        location_id: Optional[UUID] = None,
        monitoring_enabled: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[NetworkDevice]:
        """List devices with filtering."""
        query = self.db.query(NetworkDevice).filter(
            NetworkDevice.tenant_id == self.tenant_id
        )

        if device_type:
            query = query.filter(NetworkDevice.device_type == device_type)
        if status:
            query = query.filter(NetworkDevice.status == status)
        if location_id:
            query = query.filter(NetworkDevice.location_id == location_id)
        if monitoring_enabled is not None:
            query = query.filter(NetworkDevice.monitoring_enabled == monitoring_enabled)

        return query.order_by(NetworkDevice.name).offset(skip).limit(limit).all()

    def update_status(
        self, device_id: UUID, status: DeviceStatus, notes: Optional[str] = None
    ) -> Optional[NetworkDevice]:
        """Update device status."""
        device = self.get_by_id(device_id)
        if not device:
            return None

        device.status = status
        device.updated_at = datetime.utcnow()

        if notes and hasattr(device, "notes"):
            current_notes = getattr(device, "notes", "") or ""
            device.notes = (
                f"{current_notes}\n{datetime.utcnow().isoformat()}: {notes}".strip()
            )

        self.db.commit()
        self.db.refresh(device)
        return device

    def backup_configuration(self, device_id: UUID) -> Optional[NetworkDevice]:
        """Update last configuration backup timestamp."""
        device = self.get_by_id(device_id)
        if not device:
            return None

        device.last_config_backup = datetime.utcnow()
        device.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(device)
        return device


class NetworkInterfaceRepository:
    """Repository for network interface database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def create(self, interface_data: Dict[str, Any]) -> NetworkInterface:
        """Create new network interface."""
        try:
            interface = NetworkInterface(
                id=uuid4(),
                tenant_id=self.tenant_id,
                admin_status=InterfaceStatus.UP,
                operational_status=InterfaceStatus.DOWN,
                **interface_data,
            )

            self.db.add(interface)
            self.db.commit()
            self.db.refresh(interface)
            return interface

        except IntegrityError as e:
            self.db.rollback()
            if "mac_address" in str(e):
                raise ConflictError(
                    f"MAC address {interface_data.get('mac_address')} already exists"
                )
            raise ConflictError("Interface creation failed due to data conflict")

    def get_by_id(self, interface_id: UUID) -> Optional[NetworkInterface]:
        """Get interface by ID."""
        return (
            self.db.query(NetworkInterface)
            .filter(
                and_(
                    NetworkInterface.id == interface_id,
                    NetworkInterface.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    def list_by_device(self, device_id: UUID) -> List[NetworkInterface]:
        """List interfaces for a device."""
        return (
            self.db.query(NetworkInterface)
            .filter(
                and_(
                    NetworkInterface.device_id == device_id,
                    NetworkInterface.tenant_id == self.tenant_id,
                )
            )
            .order_by(NetworkInterface.name)
            .all()
        )

    def update_status(
        self,
        interface_id: UUID,
        admin_status: InterfaceStatus,
        operational_status: InterfaceStatus,
    ) -> Optional[NetworkInterface]:
        """Update interface status."""
        interface = self.get_by_id(interface_id)
        if not interface:
            return None

        interface.admin_status = admin_status
        interface.operational_status = operational_status
        interface.last_change = datetime.utcnow()

        self.db.commit()
        self.db.refresh(interface)
        return interface

    def update_traffic_counters(
        self, interface_id: UUID, counters: Dict[str, int]
    ) -> Optional[NetworkInterface]:
        """Update traffic counters."""
        interface = self.get_by_id(interface_id)
        if not interface:
            return None

        for key, value in counters.items():
            if hasattr(interface, key):
                setattr(interface, key, value)

        self.db.commit()
        self.db.refresh(interface)
        return interface


class NetworkLocationRepository:
    """Repository for network location database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def create(self, location_data: Dict[str, Any]) -> NetworkLocation:
        """Create new network location."""
        try:
            location = NetworkLocation(
                id=uuid4(), tenant_id=self.tenant_id, **location_data
            )

            self.db.add(location)
            self.db.commit()
            self.db.refresh(location)
            return location

        except IntegrityError as e:
            self.db.rollback()
            if "code" in str(e):
                raise ConflictError(
                    f"Location code {location_data.get('code')} already exists"
                )
            raise ConflictError("Location creation failed due to data conflict")

    def get_by_id(self, location_id: UUID) -> Optional[NetworkLocation]:
        """Get location by ID."""
        return (
            self.db.query(NetworkLocation)
            .filter(
                and_(
                    NetworkLocation.id == location_id,
                    NetworkLocation.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    def get_by_code(self, code: str) -> Optional[NetworkLocation]:
        """Get location by code."""
        return (
            self.db.query(NetworkLocation)
            .filter(
                and_(
                    NetworkLocation.code == code,
                    NetworkLocation.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    def list_locations(
        self, location_type: Optional[str] = None, skip: int = 0, limit: int = 100
    ) -> List[NetworkLocation]:
        """List locations with filtering."""
        query = self.db.query(NetworkLocation).filter(
            NetworkLocation.tenant_id == self.tenant_id
        )

        if location_type:
            query = query.filter(NetworkLocation.location_type == location_type)

        return query.order_by(NetworkLocation.name).offset(skip).limit(limit).all()


class NetworkMetricRepository:
    """Repository for network metric database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def create(self, metric_data: Dict[str, Any]) -> NetworkMetric:
        """Create new network metric."""
        metric = NetworkMetric(
            id=uuid4(),
            tenant_id=self.tenant_id,
            timestamp=datetime.utcnow(),
            **metric_data,
        )

        self.db.add(metric)
        self.db.commit()
        self.db.refresh(metric)
        return metric

    def create_bulk(self, metrics_data: List[Dict[str, Any]]) -> List[NetworkMetric]:
        """Create multiple metrics in bulk."""
        metrics = []
        for metric_data in metrics_data:
            metric = NetworkMetric(
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
    ) -> List[NetworkMetric]:
        """Get latest metrics for a device."""
        cutoff_time = datetime.utcnow() - datetime.timedelta(hours=hours)

        query = self.db.query(NetworkMetric).filter(
            and_(
                NetworkMetric.device_id == device_id,
                NetworkMetric.tenant_id == self.tenant_id,
                NetworkMetric.timestamp >= cutoff_time,
            )
        )

        if metric_names:
            query = query.filter(NetworkMetric.metric_name.in_(metric_names))

        return query.order_by(desc(NetworkMetric.timestamp)).all()


class NetworkAlertRepository:
    """Repository for network alert database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def create(self, alert_data: Dict[str, Any]) -> NetworkAlert:
        """Create new network alert."""
        alert = NetworkAlert(id=uuid4(), tenant_id=self.tenant_id, **alert_data)

        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert

    def get_by_id(self, alert_id: UUID) -> Optional[NetworkAlert]:
        """Get alert by ID."""
        return (
            self.db.query(NetworkAlert)
            .filter(
                and_(
                    NetworkAlert.id == alert_id,
                    NetworkAlert.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    def list_active_alerts(
        self,
        device_id: Optional[UUID] = None,
        severity: Optional[AlertSeverity] = None,
        alert_type: Optional[AlertType] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[NetworkAlert]:
        """List active alerts with filtering."""
        query = self.db.query(NetworkAlert).filter(
            and_(
                NetworkAlert.tenant_id == self.tenant_id, NetworkAlert.is_active == True
            )
        )

        if device_id:
            query = query.filter(NetworkAlert.device_id == device_id)
        if severity:
            query = query.filter(NetworkAlert.severity == severity)
        if alert_type:
            query = query.filter(NetworkAlert.alert_type == alert_type)

        return (
            query.order_by(desc(NetworkAlert.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def acknowledge_alert(
        self, alert_id: UUID, user_id: UUID
    ) -> Optional[NetworkAlert]:
        """Acknowledge an alert."""
        alert = self.get_by_id(alert_id)
        if not alert:
            return None

        alert.acknowledge(str(user_id))
        self.db.commit()
        self.db.refresh(alert)
        return alert

    def resolve_alert(self, alert_id: UUID) -> Optional[NetworkAlert]:
        """Resolve an alert."""
        alert = self.get_by_id(alert_id)
        if not alert:
            return None

        alert.resolve()
        self.db.commit()
        self.db.refresh(alert)
        return alert


class DeviceConfigurationRepository:
    """Repository for device configuration database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def create(self, config_data: Dict[str, Any]) -> DeviceConfiguration:
        """Create new device configuration."""
        config = DeviceConfiguration(
            id=uuid4(), tenant_id=self.tenant_id, **config_data
        )

        self.db.add(config)
        self.db.commit()
        self.db.refresh(config)
        return config

    def get_by_id(self, config_id: UUID) -> Optional[DeviceConfiguration]:
        """Get configuration by ID."""
        return (
            self.db.query(DeviceConfiguration)
            .filter(
                and_(
                    DeviceConfiguration.id == config_id,
                    DeviceConfiguration.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    def get_active_config(self, device_id: UUID) -> Optional[DeviceConfiguration]:
        """Get active configuration for device."""
        return (
            self.db.query(DeviceConfiguration)
            .filter(
                and_(
                    DeviceConfiguration.device_id == device_id,
                    DeviceConfiguration.tenant_id == self.tenant_id,
                    DeviceConfiguration.is_active == True,
                )
            )
            .first()
        )

    def list_by_device(self, device_id: UUID) -> List[DeviceConfiguration]:
        """List configurations for a device."""
        return (
            self.db.query(DeviceConfiguration)
            .filter(
                and_(
                    DeviceConfiguration.device_id == device_id,
                    DeviceConfiguration.tenant_id == self.tenant_id,
                )
            )
            .order_by(desc(DeviceConfiguration.created_at))
            .all()
        )

    def set_active_config(self, config_id: UUID) -> Optional[DeviceConfiguration]:
        """Set configuration as active and deactivate others."""
        config = self.get_by_id(config_id)
        if not config:
            return None

        # Deactivate all other configs for this device
        self.db.query(DeviceConfiguration).filter(
            and_(
                DeviceConfiguration.device_id == config.device_id,
                DeviceConfiguration.tenant_id == self.tenant_id,
                DeviceConfiguration.id != config_id,
            )
        ).update({"is_active": False})

        # Activate this config
        config.is_active = True
        config.deployment_time = datetime.utcnow()
        config.deployment_status = "deployed"

        self.db.commit()
        self.db.refresh(config)
        return config


class NetworkTopologyRepository:
    """Repository for network topology database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def create(self, topology_data: Dict[str, Any]) -> NetworkTopology:
        """Create new topology connection."""
        topology = NetworkTopology(
            id=uuid4(), tenant_id=self.tenant_id, **topology_data
        )

        self.db.add(topology)
        self.db.commit()
        self.db.refresh(topology)
        return topology

    def get_device_connections(self, device_id: UUID) -> List[NetworkTopology]:
        """Get all connections for a device."""
        return (
            self.db.query(NetworkTopology)
            .filter(
                and_(
                    or_(
                        NetworkTopology.parent_device_id == device_id,
                        NetworkTopology.child_device_id == device_id,
                    ),
                    NetworkTopology.tenant_id == self.tenant_id,
                )
            )
            .all()
        )

    def get_topology_map(self) -> List[NetworkTopology]:
        """Get complete network topology."""
        return (
            self.db.query(NetworkTopology)
            .filter(NetworkTopology.tenant_id == self.tenant_id)
            .all()
        )
