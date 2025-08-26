"""Network Integration database models."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
import json

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    Enum as SQLEnum,
    BigInteger,
    Numeric,
)
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property

from dotmac_isp.shared.database.base import TenantModel
from dotmac_isp.shared.database.base import StatusMixin, AuditMixin
from dotmac_isp.shared.models import AddressMixin


class DeviceType(str, Enum):
    """Network device types."""

    ROUTER = "router"
    SWITCH = "switch"
    ACCESS_POINT = "access_point"
    FIREWALL = "firewall"
    LOAD_BALANCER = "load_balancer"
    OLT = "olt"
    ONU = "onu"
    MODEM = "modem"
    CPE = "cpe"
    SERVER = "server"
    UPS = "ups"
    PDU = "pdu"
    OPTICAL_AMPLIFIER = "optical_amplifier"
    SPLITTER = "splitter"
    PATCH_PANEL = "patch_panel"


class DeviceStatus(str, Enum):
    """Device operational status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    FAILED = "failed"
    PROVISIONING = "provisioning"
    DECOMMISSIONED = "decommissioned"
    UNKNOWN = "unknown"


class InterfaceType(str, Enum):
    """Network interface types."""

    ETHERNET = "ethernet"
    FIBER = "fiber"
    WIRELESS = "wireless"
    SERIAL = "serial"
    LOOPBACK = "loopback"
    VLAN = "vlan"
    TUNNEL = "tunnel"
    GPON = "gpon"


class InterfaceStatus(str, Enum):
    """Interface operational status."""

    UP = "up"
    DOWN = "down"
    ADMIN_DOWN = "admin_down"
    TESTING = "testing"
    DORMANT = "dormant"
    NOT_PRESENT = "not_present"
    LOWER_LAYER_DOWN = "lower_layer_down"


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertType(str, Enum):
    """Alert types."""

    DEVICE_DOWN = "device_down"
    INTERFACE_DOWN = "interface_down"
    HIGH_CPU = "high_cpu"
    HIGH_MEMORY = "high_memory"
    HIGH_TEMPERATURE = "high_temperature"
    HIGH_TRAFFIC = "high_traffic"
    POWER_FAILURE = "power_failure"
    CONFIGURATION_CHANGE = "configuration_change"
    SECURITY_BREACH = "security_breach"
    BACKUP_FAILURE = "backup_failure"


class NetworkDevice(TenantModel, StatusMixin, AuditMixin, AddressMixin):
    """Network device model."""

    __tablename__ = "network_devices"

    # Device identification
    name = Column(String(255), nullable=False, index=True)
    hostname = Column(String(255), nullable=True, unique=True, index=True)
    device_type = Column(SQLEnum(DeviceType), nullable=False, index=True)
    model = Column(String(100), nullable=True)
    vendor = Column(String(100), nullable=True)
    serial_number = Column(String(100), nullable=True, unique=True)
    asset_tag = Column(String(100), nullable=True, unique=True)

    # Network configuration
    management_ip = Column(INET, nullable=True, unique=True, index=True)
    subnet_mask = Column(String(18), nullable=True)  # e.g., 255.255.255.0
    gateway = Column(INET, nullable=True)
    dns_servers = Column(JSON, nullable=True)  # List of DNS server IPs

    # SNMP configuration
    snmp_community = Column(String(100), nullable=True)
    snmp_version = Column(String(10), default="v2c", nullable=False)
    snmp_port = Column(Integer, default=161, nullable=False)
    snmp_enabled = Column(Boolean, default=True, nullable=False)

    # Device specifications
    cpu_count = Column(Integer, nullable=True)
    memory_total_mb = Column(BigInteger, nullable=True)
    storage_total_gb = Column(Integer, nullable=True)
    power_consumption_watts = Column(Integer, nullable=True)

    # Software information
    os_version = Column(String(100), nullable=True)
    firmware_version = Column(String(100), nullable=True)
    last_config_backup = Column(DateTime(timezone=True), nullable=True)

    # Monitoring settings
    monitoring_enabled = Column(Boolean, default=True, nullable=False)
    monitoring_interval = Column(Integer, default=300, nullable=False)  # seconds

    # Location and physical details
    location_id = Column(
        UUID(as_uuid=True),
        ForeignKey("network_locations.id"),
        nullable=True,
        index=True,
    )
    rack_location = Column(String(100), nullable=True)
    rack_unit = Column(String(10), nullable=True)
    datacenter = Column(String(100), nullable=True)

    # Maintenance information
    warranty_expires = Column(DateTime(timezone=True), nullable=True)
    last_maintenance = Column(DateTime(timezone=True), nullable=True)
    next_maintenance = Column(DateTime(timezone=True), nullable=True)

    # Additional metadata
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)  # List of tags
    custom_fields = Column(JSON, nullable=True)  # Custom key-value pairs

    # Relationships
    interfaces = relationship(
        "NetworkInterface", back_populates="device", cascade="all, delete-orphan"
    )
    metrics = relationship(
        "NetworkMetric", back_populates="device", cascade="all, delete-orphan"
    )
    configurations = relationship(
        "DeviceConfiguration", back_populates="device", cascade="all, delete-orphan"
    )
    alerts = relationship(
        "NetworkAlert", back_populates="device", cascade="all, delete-orphan"
    )
    location = relationship("NetworkLocation", back_populates="devices")

    @validates("management_ip")
    def validate_management_ip(self, key, value):
        """Validate management IP address."""
        if value and not isinstance(value, str):
            raise ValueError("Management IP must be a valid IP address string")
        return value

    @hybrid_property
    def is_online(self):
        """Check if device is online based on recent metrics."""
        return self.status == DeviceStatus.ACTIVE

    @property
    def uptime_percentage(self) -> Optional[float]:
        """Calculate uptime percentage based on recent metrics."""
        # This would be calculated from monitoring data
        return None

    def __repr__(self):
        """  Repr   operation."""
        return f"<NetworkDevice(name='{self.name}', type='{self.device_type}', ip='{self.management_ip}')>"


class NetworkInterface(TenantModel, StatusMixin, AuditMixin):
    """Network interface model."""

    __tablename__ = "network_interfaces"

    device_id = Column(
        UUID(as_uuid=True), ForeignKey("network_devices.id"), nullable=False, index=True
    )

    # Interface identification
    name = Column(
        String(100), nullable=False, index=True
    )  # e.g., eth0, GigabitEthernet1/0/1
    description = Column(Text, nullable=True)
    interface_type = Column(SQLEnum(InterfaceType), nullable=False)
    interface_index = Column(Integer, nullable=True)  # SNMP ifIndex

    # Network configuration
    ip_address = Column(INET, nullable=True)
    subnet_mask = Column(String(18), nullable=True)
    vlan_id = Column(Integer, nullable=True)

    # Physical properties
    mac_address = Column(
        String(17), nullable=True, index=True
    )  # Format: XX:XX:XX:XX:XX:XX
    speed_mbps = Column(BigInteger, nullable=True)  # Interface speed in Mbps
    duplex = Column(String(10), nullable=True)  # full, half, auto
    mtu = Column(Integer, default=1500, nullable=False)

    # Status and monitoring
    admin_status = Column(
        SQLEnum(InterfaceStatus), default=InterfaceStatus.UP, nullable=False
    )
    operational_status = Column(
        SQLEnum(InterfaceStatus), default=InterfaceStatus.DOWN, nullable=False
    )
    last_change = Column(DateTime(timezone=True), nullable=True)

    # Traffic counters (updated by monitoring)
    bytes_in = Column(BigInteger, default=0, nullable=False)
    bytes_out = Column(BigInteger, default=0, nullable=False)
    packets_in = Column(BigInteger, default=0, nullable=False)
    packets_out = Column(BigInteger, default=0, nullable=False)
    errors_in = Column(BigInteger, default=0, nullable=False)
    errors_out = Column(BigInteger, default=0, nullable=False)
    discards_in = Column(BigInteger, default=0, nullable=False)
    discards_out = Column(BigInteger, default=0, nullable=False)

    # Additional metadata
    tags = Column(JSON, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    device = relationship("NetworkDevice", back_populates="interfaces")

    @validates("mac_address")
    def validate_mac_address(self, key, value):
        """Validate MAC address format."""
        if value:
            # Basic MAC address format validation
            if not value.replace(":", "").replace("-", "").isalnum():
                raise ValueError("Invalid MAC address format")
        return value

    @hybrid_property
    def utilization_percentage(self) -> Optional[float]:
        """Calculate interface utilization percentage."""
        if not self.speed_mbps:
            return None
        # This would be calculated from recent traffic metrics
        return None

    def __repr__(self):
        """  Repr   operation."""
        return f"<NetworkInterface(name='{self.name}', device='{self.device.name if self.device else 'Unknown'}')>"


class NetworkLocation(TenantModel, AddressMixin, AuditMixin):
    """Physical location model for network devices and infrastructure."""

    __tablename__ = "network_locations"

    # Location identification
    name = Column(String(255), nullable=False, index=True)
    location_type = Column(
        String(50), nullable=False, index=True
    )  # datacenter, pop, customer_premise, etc.
    code = Column(
        String(20), nullable=True, unique=True, index=True
    )  # Short location code

    # Geographic coordinates
    latitude = Column(Numeric(precision=10, scale=8), nullable=True, index=True)
    longitude = Column(Numeric(precision=11, scale=8), nullable=True, index=True)
    elevation_meters = Column(Float, nullable=True)

    # Facility details
    facility_size_sqm = Column(Float, nullable=True)
    power_capacity_kw = Column(Float, nullable=True)
    cooling_capacity_tons = Column(Float, nullable=True)
    rack_count = Column(Integer, nullable=True)

    # Contact and access information
    contact_person = Column(String(255), nullable=True)
    contact_phone = Column(String(20), nullable=True)
    contact_email = Column(String(255), nullable=True)
    access_hours = Column(String(255), nullable=True)
    access_instructions = Column(Text, nullable=True)

    # Service area coverage
    service_area_radius_km = Column(Float, nullable=True)
    population_served = Column(Integer, nullable=True)

    # Additional metadata
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    devices = relationship("NetworkDevice", back_populates="location")

    @hybrid_property
    def coordinates(self) -> Optional[Dict[str, float]]:
        """Get coordinates as dictionary."""
        if self.latitude and self.longitude:
            return {"lat": float(self.latitude), "lon": float(self.longitude)}
        return None

    def __repr__(self):
        """  Repr   operation."""
        return f"<NetworkLocation(name='{self.name}', type='{self.location_type}')>"


class NetworkMetric(TenantModel):
    """Network device metrics and performance data."""

    __tablename__ = "network_metrics"

    device_id = Column(
        UUID(as_uuid=True), ForeignKey("network_devices.id"), nullable=False, index=True
    )
    interface_id = Column(
        UUID(as_uuid=True),
        ForeignKey("network_interfaces.id"),
        nullable=True,
        index=True,
    )

    # Metric identification
    metric_name = Column(String(100), nullable=False, index=True)
    metric_type = Column(
        String(50), nullable=False, index=True
    )  # gauge, counter, histogram

    # Metric data
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    # Additional context
    tags = Column(JSON, nullable=True)  # Additional metric tags
    labels = Column(JSON, nullable=True)  # Prometheus-style labels

    # Relationships
    device = relationship("NetworkDevice", back_populates="metrics")
    interface = relationship("NetworkInterface")

    def __repr__(self):
        """  Repr   operation."""
        return f"<NetworkMetric(device='{self.device.name if self.device else 'Unknown'}', metric='{self.metric_name}', value='{self.value}')>"


class NetworkTopology(TenantModel, AuditMixin):
    """Network topology and device relationships."""

    __tablename__ = "network_topology"

    # Device relationship
    parent_device_id = Column(
        UUID(as_uuid=True), ForeignKey("network_devices.id"), nullable=False, index=True
    )
    child_device_id = Column(
        UUID(as_uuid=True), ForeignKey("network_devices.id"), nullable=False, index=True
    )

    # Connection details
    connection_type = Column(
        String(50), nullable=False, index=True
    )  # physical, logical, wireless
    parent_interface_id = Column(
        UUID(as_uuid=True), ForeignKey("network_interfaces.id"), nullable=True
    )
    child_interface_id = Column(
        UUID(as_uuid=True), ForeignKey("network_interfaces.id"), nullable=True
    )

    # Connection properties
    bandwidth_mbps = Column(Integer, nullable=True)
    distance_meters = Column(Float, nullable=True)
    cable_type = Column(String(50), nullable=True)

    # Additional metadata
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)

    # Relationships
    parent_device = relationship("NetworkDevice", foreign_keys=[parent_device_id])
    child_device = relationship("NetworkDevice", foreign_keys=[child_device_id])
    parent_interface = relationship(
        "NetworkInterface", foreign_keys=[parent_interface_id]
    )
    child_interface = relationship(
        "NetworkInterface", foreign_keys=[child_interface_id]
    )

    def __repr__(self):
        """  Repr   operation."""
        return f"<NetworkTopology(parent='{self.parent_device.name if self.parent_device else 'Unknown'}', child='{self.child_device.name if self.child_device else 'Unknown'}')>"


class DeviceConfiguration(TenantModel, AuditMixin):
    """Device configuration management."""

    __tablename__ = "device_configurations"

    device_id = Column(
        UUID(as_uuid=True), ForeignKey("network_devices.id"), nullable=False, index=True
    )

    # Configuration identification
    name = Column(String(255), nullable=False, index=True)
    version = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=False, nullable=False)
    is_backup = Column(Boolean, default=False, nullable=False)

    # Configuration data
    configuration_data = Column(Text, nullable=False)  # Full device configuration
    configuration_hash = Column(String(64), nullable=True, index=True)  # SHA-256 hash

    # Metadata
    source = Column(String(50), nullable=True)  # manual, automatic, ansible, etc.
    deployment_status = Column(String(50), default="draft", nullable=False)
    deployment_time = Column(DateTime(timezone=True), nullable=True)

    # Validation
    syntax_validated = Column(Boolean, default=False, nullable=False)
    validation_errors = Column(JSON, nullable=True)

    # Additional metadata
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)

    # Relationships
    device = relationship("NetworkDevice", back_populates="configurations")

    def __repr__(self):
        """  Repr   operation."""
        return f"<DeviceConfiguration(device='{self.device.name if self.device else 'Unknown'}', name='{self.name}', version='{self.version}')>"


class NetworkAlert(TenantModel, AuditMixin):
    """Network alerts and notifications."""

    __tablename__ = "network_alerts"

    device_id = Column(
        UUID(as_uuid=True), ForeignKey("network_devices.id"), nullable=True, index=True
    )
    interface_id = Column(
        UUID(as_uuid=True),
        ForeignKey("network_interfaces.id"),
        nullable=True,
        index=True,
    )

    # Alert identification
    alert_type = Column(SQLEnum(AlertType), nullable=False, index=True)
    severity = Column(SQLEnum(AlertSeverity), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    # Alert status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_acknowledged = Column(Boolean, default=False, nullable=False)
    acknowledged_by = Column(UUID(as_uuid=True), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Alert context
    metric_name = Column(String(100), nullable=True)
    threshold_value = Column(Float, nullable=True)
    current_value = Column(Float, nullable=True)

    # Additional metadata
    tags = Column(JSON, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    device = relationship("NetworkDevice", back_populates="alerts")
    interface = relationship("NetworkInterface")

    def acknowledge(self, user_id: str):
        """Acknowledge the alert."""
        self.is_acknowledged = True
        self.acknowledged_by = user_id
        self.acknowledged_at = datetime.now(timezone.utc)

    def resolve(self):
        """Resolve the alert."""
        self.is_active = False
        self.resolved_at = datetime.now(timezone.utc)

    def __repr__(self):
        """  Repr   operation."""
        return f"<NetworkAlert(type='{self.alert_type}', severity='{self.severity}', device='{self.device.name if self.device else 'System'}')>"


class DeviceGroup(TenantModel, AuditMixin):
    """Device grouping for management and monitoring."""

    __tablename__ = "device_groups"

    # Group identification
    name = Column(String(255), nullable=False, index=True)
    group_type = Column(
        String(50), nullable=False, index=True
    )  # location, function, vendor, etc.

    # Group configuration
    monitoring_template = Column(String(255), nullable=True)
    alert_rules = Column(JSON, nullable=True)
    maintenance_schedule = Column(JSON, nullable=True)

    # Additional metadata
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Many-to-many relationship with devices would be implemented via association table

    def __repr__(self):
        """  Repr   operation."""
        return f"<DeviceGroup(name='{self.name}', type='{self.group_type}')>"


class NetworkService(TenantModel, StatusMixin, AuditMixin):
    """Network services and applications."""

    __tablename__ = "network_services"

    # Service identification
    name = Column(String(255), nullable=False, index=True)
    service_type = Column(
        String(100), nullable=False, index=True
    )  # DHCP, DNS, HTTP, SNMP, etc.
    protocol = Column(String(20), nullable=False)  # TCP, UDP, ICMP
    port = Column(Integer, nullable=True)

    # Service configuration
    listen_address = Column(INET, nullable=True)
    configuration = Column(JSON, nullable=True)

    # Health monitoring
    health_check_enabled = Column(Boolean, default=True, nullable=False)
    health_check_interval = Column(Integer, default=60, nullable=False)  # seconds
    health_check_timeout = Column(Integer, default=10, nullable=False)  # seconds

    # Dependencies
    dependencies = Column(JSON, nullable=True)  # List of dependent services

    # Additional metadata
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    def __repr__(self):
        """  Repr   operation."""
        return f"<NetworkService(name='{self.name}', type='{self.service_type}', port='{self.port}')>"


class MaintenanceWindow(TenantModel, AuditMixin):
    """Scheduled maintenance windows."""

    __tablename__ = "maintenance_windows"

    # Maintenance identification
    name = Column(String(255), nullable=False, index=True)
    maintenance_type = Column(
        String(50), nullable=False, index=True
    )  # planned, emergency, routine

    # Schedule
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=False, index=True)
    timezone = Column(String(50), default="UTC", nullable=False)

    # Impact assessment
    impact_level = Column(
        String(20), nullable=False, index=True
    )  # low, medium, high, critical
    affected_services = Column(JSON, nullable=True)  # List of affected services

    # Status tracking
    approval_status = Column(String(20), default="pending", nullable=False)
    execution_status = Column(String(20), default="scheduled", nullable=False)

    # Additional details
    description = Column(Text, nullable=False)
    work_instructions = Column(Text, nullable=True)
    rollback_plan = Column(Text, nullable=True)

    # Notification settings
    notifications_enabled = Column(Boolean, default=True, nullable=False)
    notification_channels = Column(JSON, nullable=True)

    # Additional metadata
    tags = Column(JSON, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    def __repr__(self):
        """  Repr   operation."""
        return f"<MaintenanceWindow(name='{self.name}', type='{self.maintenance_type}', start='{self.start_time}')>"
