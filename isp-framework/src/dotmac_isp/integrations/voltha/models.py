"""VOLTHA integration database models."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

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
)
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property

from dotmac_isp.shared.database.base import TenantModel
from dotmac_isp.shared.database.base import StatusMixin, AuditMixin


class DeviceType(str, Enum):
    """VOLTHA device types."""

    OLT = "olt"
    ONU = "onu"
    ADAPTER = "adapter"


class DeviceConnectionStatus(str, Enum):
    """Device connection status."""

    REACHABLE = "reachable"
    UNREACHABLE = "unreachable"
    DISCOVERED = "discovered"
    DISABLED = "disabled"
    UNKNOWN = "unknown"


class DeviceOperationalStatus(str, Enum):
    """Device operational status."""

    ACTIVE = "active"
    ACTIVATING = "activating"
    INACTIVE = "inactive"
    FAILED = "failed"
    TESTING = "testing"
    UNKNOWN = "unknown"


class DeviceAdminState(str, Enum):
    """Device administrative state."""

    ENABLED = "enabled"
    DISABLED = "disabled"
    PREPROVISIONED = "preprovisioned"
    DOWNLOADING_IMAGE = "downloading_image"
    DELETED = "deleted"


class GponPortType(str, Enum):
    """GPON port types."""

    PON_PORT = "pon_port"
    ETHERNET_NNI = "ethernet_nni"
    ETHERNET_UNI = "ethernet_uni"
    VIRTUAL_PON = "virtual_pon"


class GponPortState(str, Enum):
    """GPON port states."""

    ENABLED = "enabled"
    DISABLED = "disabled"
    UNKNOWN = "unknown"


class OnuState(str, Enum):
    """ONU states."""

    DISCOVERED = "discovered"
    ACTIVATING = "activating"
    ACTIVE = "active"
    DISABLED = "disabled"
    FAILED = "failed"
    REBOOTING = "rebooting"
    DELETING = "deleting"


class ServiceType(str, Enum):
    """Service types."""

    INTERNET = "internet"
    VOICE = "voice"
    VIDEO = "video"
    ENTERPRISE = "enterprise"
    MULTICAST = "multicast"


class ServiceStatus(str, Enum):
    """Service status."""

    PROVISIONED = "provisioned"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    FAILED = "failed"


class VolthaOlt(TenantModel, StatusMixin, AuditMixin):
    """VOLTHA OLT (Optical Line Terminal) model."""

    __tablename__ = "voltha_olts"

    # Device identification
    voltha_device_id = Column(String(100), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    device_type = Column(String(100), nullable=False)
    vendor = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    hardware_version = Column(String(100), nullable=True)
    firmware_version = Column(String(100), nullable=True)
    software_version = Column(String(100), nullable=True)
    serial_number = Column(String(100), nullable=True, unique=True)

    # Network configuration
    management_ip = Column(INET, nullable=True, index=True)
    management_port = Column(Integer, nullable=True)
    mac_address = Column(String(17), nullable=True, index=True)

    # VOLTHA-specific configuration
    adapter_type = Column(String(100), nullable=True)
    parent_device_id = Column(String(100), nullable=True)
    root_device = Column(Boolean, default=True, nullable=False)

    # Device states
    connection_status = Column(
        SQLEnum(DeviceConnectionStatus), nullable=False, index=True
    )
    operational_status = Column(
        SQLEnum(DeviceOperationalStatus), nullable=False, index=True
    )
    admin_state = Column(SQLEnum(DeviceAdminState), nullable=False, index=True)

    # Physical location and rack information
    location_id = Column(
        UUID(as_uuid=True), ForeignKey("network_locations.id"), nullable=True
    )
    rack_position = Column(String(20), nullable=True)

    # Capacity and performance
    max_pon_ports = Column(Integer, nullable=True)
    active_pon_ports = Column(Integer, default=0, nullable=False)
    max_onus_per_port = Column(Integer, nullable=True)
    total_active_onus = Column(Integer, default=0, nullable=False)

    # Monitoring and health
    last_reboot = Column(DateTime(timezone=True), nullable=True)
    uptime_seconds = Column(BigInteger, nullable=True)
    cpu_usage = Column(Float, nullable=True)  # Percentage
    memory_usage = Column(Float, nullable=True)  # Percentage
    temperature = Column(Float, nullable=True)  # Celsius

    # Additional metadata
    custom_fields = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)

    # Relationships
    pon_ports = relationship(
        "GponPort", back_populates="olt", cascade="all, delete-orphan"
    )
    onus = relationship("VolthaOnu", back_populates="olt")
    services = relationship("GponService", back_populates="olt")
    metrics = relationship("VolthaMetric", back_populates="olt")
    alerts = relationship("VolthaAlert", back_populates="olt")

    @validates("mac_address")
    def validate_mac_address(self, key, value):
        """Validate MAC address format."""
        if value:
            if not value.replace(":", "").replace("-", "").isalnum():
                raise ValueError("Invalid MAC address format")
        return value

    @hybrid_property
    def utilization_percentage(self) -> Optional[float]:
        """Calculate OLT utilization percentage."""
        if self.max_pon_ports and self.max_pon_ports > 0:
            return (self.active_pon_ports / self.max_pon_ports) * 100
        return None

    def __repr__(self):
        """  Repr   operation."""
        return f"<VolthaOlt(name='{self.name}', device_id='{self.voltha_device_id}', status='{self.operational_status}')>"


class VolthaOnu(TenantModel, StatusMixin, AuditMixin):
    """VOLTHA ONU (Optical Network Unit) model."""

    __tablename__ = "voltha_onus"

    olt_id = Column(
        UUID(as_uuid=True), ForeignKey("voltha_olts.id"), nullable=False, index=True
    )
    pon_port_id = Column(
        UUID(as_uuid=True), ForeignKey("gpon_ports.id"), nullable=True, index=True
    )

    # Device identification
    voltha_device_id = Column(String(100), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    vendor = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    hardware_version = Column(String(100), nullable=True)
    firmware_version = Column(String(100), nullable=True)
    software_version = Column(String(100), nullable=True)
    serial_number = Column(String(100), nullable=True, unique=True, index=True)

    # GPON-specific identifiers
    onu_id = Column(Integer, nullable=True, index=True)  # ONU ID on PON port
    alloc_id = Column(Integer, nullable=True)  # Allocation ID
    gem_port_ids = Column(JSON, nullable=True)  # List of GEM port IDs

    # Network configuration
    mac_address = Column(String(17), nullable=True, index=True)
    ip_address = Column(INET, nullable=True)

    # Device states
    connection_status = Column(
        SQLEnum(DeviceConnectionStatus), nullable=False, index=True
    )
    operational_status = Column(
        SQLEnum(DeviceOperationalStatus), nullable=False, index=True
    )
    admin_state = Column(SQLEnum(DeviceAdminState), nullable=False, index=True)
    onu_state = Column(SQLEnum(OnuState), nullable=False, index=True)

    # Customer and service information
    customer_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    service_profile_id = Column(
        UUID(as_uuid=True), ForeignKey("service_profiles.id"), nullable=True
    )

    # Performance metrics
    rx_power_dbm = Column(Float, nullable=True)  # Received optical power in dBm
    tx_power_dbm = Column(Float, nullable=True)  # Transmitted optical power in dBm
    voltage = Column(Float, nullable=True)  # Supply voltage
    temperature = Column(Float, nullable=True)  # Temperature in Celsius
    current = Column(Float, nullable=True)  # Current in mA

    # Traffic statistics (updated periodically)
    bytes_upstream = Column(BigInteger, default=0, nullable=False)
    bytes_downstream = Column(BigInteger, default=0, nullable=False)
    packets_upstream = Column(BigInteger, default=0, nullable=False)
    packets_downstream = Column(BigInteger, default=0, nullable=False)

    # Provisioning information
    discovered_at = Column(DateTime(timezone=True), nullable=True)
    activated_at = Column(DateTime(timezone=True), nullable=True)
    last_seen = Column(DateTime(timezone=True), nullable=True)

    # Additional metadata
    custom_fields = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)

    # Relationships
    olt = relationship("VolthaOlt", back_populates="onus")
    pon_port = relationship("GponPort", back_populates="onus")
    services = relationship("GponService", back_populates="onu")
    service_profile = relationship("ServiceProfile")
    metrics = relationship("VolthaMetric", back_populates="onu")
    alerts = relationship("VolthaAlert", back_populates="onu")

    @hybrid_property
    def signal_quality(self) -> Optional[str]:
        """Determine signal quality based on RX power."""
        if self.rx_power_dbm is None:
            return None

        if self.rx_power_dbm >= -8:
            return "excellent"
        elif self.rx_power_dbm >= -12:
            return "good"
        elif self.rx_power_dbm >= -15:
            return "fair"
        elif self.rx_power_dbm >= -20:
            return "poor"
        else:
            return "critical"

    def __repr__(self):
        """  Repr   operation."""
        return f"<VolthaOnu(name='{self.name}', onu_id={self.onu_id}, serial='{self.serial_number}')>"


class GponPort(TenantModel, StatusMixin, AuditMixin):
    """GPON port model."""

    __tablename__ = "gpon_ports"

    olt_id = Column(
        UUID(as_uuid=True), ForeignKey("voltha_olts.id"), nullable=False, index=True
    )

    # Port identification
    port_number = Column(Integer, nullable=False, index=True)
    port_label = Column(String(50), nullable=True)
    port_type = Column(SQLEnum(GponPortType), nullable=False, index=True)

    # Port configuration
    admin_state = Column(
        SQLEnum(GponPortState), default=GponPortState.ENABLED, nullable=False
    )
    operational_state = Column(
        SQLEnum(GponPortState), default=GponPortState.DISABLED, nullable=False
    )

    # PON-specific configuration
    downstream_fec_enabled = Column(Boolean, default=True, nullable=False)
    upstream_fec_enabled = Column(Boolean, default=True, nullable=False)

    # Capacity and utilization
    max_onus = Column(Integer, default=64, nullable=False)
    active_onus = Column(Integer, default=0, nullable=False)

    # Performance metrics
    rx_power_dbm = Column(Float, nullable=True)
    tx_power_dbm = Column(Float, nullable=True)
    temperature = Column(Float, nullable=True)
    voltage = Column(Float, nullable=True)
    bias_current = Column(Float, nullable=True)

    # Traffic statistics
    bytes_upstream = Column(BigInteger, default=0, nullable=False)
    bytes_downstream = Column(BigInteger, default=0, nullable=False)
    packets_upstream = Column(BigInteger, default=0, nullable=False)
    packets_downstream = Column(BigInteger, default=0, nullable=False)

    # Additional metadata
    custom_fields = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)

    # Relationships
    olt = relationship("VolthaOlt", back_populates="pon_ports")
    onus = relationship("VolthaOnu", back_populates="pon_port")

    @hybrid_property
    def utilization_percentage(self) -> float:
        """Calculate port utilization percentage."""
        if self.max_onus > 0:
            return (self.active_onus / self.max_onus) * 100
        return 0.0

    def __repr__(self):
        """  Repr   operation."""
        return f"<GponPort(olt='{self.olt.name if self.olt else 'Unknown'}', port={self.port_number}, type='{self.port_type}')>"


class GponService(TenantModel, StatusMixin, AuditMixin):
    """GPON service provisioning model."""

    __tablename__ = "gpon_services"

    olt_id = Column(
        UUID(as_uuid=True), ForeignKey("voltha_olts.id"), nullable=False, index=True
    )
    onu_id = Column(
        UUID(as_uuid=True), ForeignKey("voltha_onus.id"), nullable=False, index=True
    )
    service_profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey("service_profiles.id"),
        nullable=False,
        index=True,
    )

    # Service identification
    service_name = Column(String(255), nullable=False, index=True)
    service_type = Column(SQLEnum(ServiceType), nullable=False, index=True)

    # VLAN configuration
    c_tag = Column(Integer, nullable=True)  # Customer VLAN tag
    s_tag = Column(Integer, nullable=True)  # Service VLAN tag

    # GEM port configuration
    gem_port_id = Column(Integer, nullable=False, index=True)
    alloc_id = Column(Integer, nullable=False, index=True)

    # Service configuration
    upstream_bandwidth_kbps = Column(Integer, nullable=True)
    downstream_bandwidth_kbps = Column(Integer, nullable=True)
    priority = Column(Integer, default=0, nullable=False)

    # Service state
    service_status = Column(
        SQLEnum(ServiceStatus),
        default=ServiceStatus.PROVISIONED,
        nullable=False,
        index=True,
    )
    provisioned_at = Column(DateTime(timezone=True), nullable=True)
    activated_at = Column(DateTime(timezone=True), nullable=True)
    suspended_at = Column(DateTime(timezone=True), nullable=True)
    terminated_at = Column(DateTime(timezone=True), nullable=True)

    # Customer information
    customer_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    service_instance_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Traffic statistics
    bytes_upstream = Column(BigInteger, default=0, nullable=False)
    bytes_downstream = Column(BigInteger, default=0, nullable=False)
    packets_upstream = Column(BigInteger, default=0, nullable=False)
    packets_downstream = Column(BigInteger, default=0, nullable=False)

    # Additional metadata
    custom_fields = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)

    # Relationships
    olt = relationship("VolthaOlt", back_populates="services")
    onu = relationship("VolthaOnu", back_populates="services")
    service_profile = relationship("ServiceProfile", back_populates="services")

    def __repr__(self):
        """  Repr   operation."""
        return f"<GponService(name='{self.service_name}', type='{self.service_type}', gem_port={self.gem_port_id})>"


class VolthaDevice(TenantModel, AuditMixin):
    """Generic VOLTHA device model for device hierarchy."""

    __tablename__ = "voltha_devices"

    # Device identification
    voltha_device_id = Column(String(100), nullable=False, unique=True, index=True)
    device_type = Column(SQLEnum(DeviceType), nullable=False, index=True)
    parent_device_id = Column(String(100), nullable=True, index=True)
    parent_port_number = Column(Integer, nullable=True)

    # Device hierarchy
    root = Column(Boolean, default=False, nullable=False)
    depth = Column(Integer, default=0, nullable=False)

    # Device information
    device_data = Column(JSON, nullable=True)  # Full device information from VOLTHA

    # Additional metadata
    custom_fields = Column(JSON, nullable=True)

    def __repr__(self):
        """  Repr   operation."""
        return f"<VolthaDevice(device_id='{self.voltha_device_id}', type='{self.device_type}')>"


class VolthaMetric(TenantModel):
    """VOLTHA device metrics model."""

    __tablename__ = "voltha_metrics"

    olt_id = Column(
        UUID(as_uuid=True), ForeignKey("voltha_olts.id"), nullable=True, index=True
    )
    onu_id = Column(
        UUID(as_uuid=True), ForeignKey("voltha_onus.id"), nullable=True, index=True
    )
    port_id = Column(
        UUID(as_uuid=True), ForeignKey("gpon_ports.id"), nullable=True, index=True
    )

    # Metric identification
    metric_name = Column(String(100), nullable=False, index=True)
    metric_type = Column(
        String(50), nullable=False, index=True
    )  # counter, gauge, histogram
    device_id = Column(String(100), nullable=False, index=True)

    # Metric data
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    # Context information
    labels = Column(JSON, nullable=True)  # Additional metric labels
    context = Column(JSON, nullable=True)  # Metric context

    # Relationships
    olt = relationship("VolthaOlt", back_populates="metrics")
    onu = relationship("VolthaOnu", back_populates="metrics")
    port = relationship("GponPort")

    def __repr__(self):
        """  Repr   operation."""
        return f"<VolthaMetric(device='{self.device_id}', metric='{self.metric_name}', value={self.value})>"


class VolthaAlert(TenantModel, AuditMixin):
    """VOLTHA alerts and alarms model."""

    __tablename__ = "voltha_alerts"

    olt_id = Column(
        UUID(as_uuid=True), ForeignKey("voltha_olts.id"), nullable=True, index=True
    )
    onu_id = Column(
        UUID(as_uuid=True), ForeignKey("voltha_onus.id"), nullable=True, index=True
    )

    # Alert identification
    alert_id = Column(String(100), nullable=False, unique=True, index=True)
    device_id = Column(String(100), nullable=False, index=True)

    # Alert information
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(
        String(20), nullable=False, index=True
    )  # critical, major, minor, warning, info
    category = Column(
        String(50), nullable=False, index=True
    )  # equipment, processing, environment, etc.
    type = Column(
        String(50), nullable=False, index=True
    )  # communication, quality, processing, equipment, environment

    # Alert state
    state = Column(
        String(20), default="active", nullable=False, index=True
    )  # active, cleared, acknowledged
    acknowledged = Column(Boolean, default=False, nullable=False)
    acknowledged_by = Column(UUID(as_uuid=True), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    cleared_at = Column(DateTime(timezone=True), nullable=True)

    # Alert context
    raised_at = Column(DateTime(timezone=True), nullable=False, index=True)
    context = Column(JSON, nullable=True)  # Additional alert context

    # Relationships
    olt = relationship("VolthaOlt", back_populates="alerts")
    onu = relationship("VolthaOnu", back_populates="alerts")

    def acknowledge(self, user_id: str):
        """Acknowledge the alert."""
        self.acknowledged = True
        self.acknowledged_by = user_id
        self.acknowledged_at = datetime.utcnow()

    def clear(self):
        """Clear the alert."""
        self.state = "cleared"
        self.cleared_at = datetime.utcnow()

    def __repr__(self):
        """  Repr   operation."""
        return f"<VolthaAlert(id='{self.alert_id}', device='{self.device_id}', severity='{self.severity}')>"


class ServiceProfile(TenantModel, StatusMixin, AuditMixin):
    """Service profile for GPON service provisioning."""

    __tablename__ = "service_profiles"

    # Profile identification
    name = Column(String(255), nullable=False, index=True)
    profile_type = Column(
        String(50), nullable=False, index=True
    )  # residential, business, enterprise

    # Bandwidth configuration
    upstream_bandwidth_kbps = Column(Integer, nullable=False)
    downstream_bandwidth_kbps = Column(Integer, nullable=False)
    burst_upstream_kbps = Column(Integer, nullable=True)
    burst_downstream_kbps = Column(Integer, nullable=True)

    # QoS configuration
    priority = Column(Integer, default=0, nullable=False)
    guaranteed_bandwidth_kbps = Column(Integer, nullable=True)
    maximum_bandwidth_kbps = Column(Integer, nullable=True)

    # Traffic shaping
    traffic_shaping_enabled = Column(Boolean, default=False, nullable=False)
    traffic_shaping_config = Column(JSON, nullable=True)

    # Service configuration
    vlan_tag_mode = Column(
        String(20), default="transparent", nullable=False
    )  # transparent, tag, untag
    default_c_tag = Column(Integer, nullable=True)
    default_s_tag = Column(Integer, nullable=True)

    # Additional features
    multicast_enabled = Column(Boolean, default=False, nullable=False)
    igmp_enabled = Column(Boolean, default=False, nullable=False)
    dhcp_relay_enabled = Column(Boolean, default=False, nullable=False)

    # Additional metadata
    description = Column(Text, nullable=True)
    custom_fields = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)

    # Relationships
    services = relationship("GponService", back_populates="service_profile")
    bandwidth_profiles = relationship(
        "BandwidthProfile", back_populates="service_profile"
    )

    def __repr__(self):
        """  Repr   operation."""
        return f"<ServiceProfile(name='{self.name}', down={self.downstream_bandwidth_kbps}kbps, up={self.upstream_bandwidth_kbps}kbps)>"


class BandwidthProfile(TenantModel, StatusMixin, AuditMixin):
    """Bandwidth profile for traffic management."""

    __tablename__ = "bandwidth_profiles"

    service_profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey("service_profiles.id"),
        nullable=False,
        index=True,
    )

    # Profile identification
    name = Column(String(255), nullable=False, index=True)
    direction = Column(String(20), nullable=False, index=True)  # upstream, downstream

    # Bandwidth parameters
    committed_information_rate = Column(Integer, nullable=False)  # CIR in kbps
    committed_burst_size = Column(Integer, nullable=False)  # CBS in bytes
    excess_information_rate = Column(Integer, nullable=True)  # EIR in kbps
    excess_burst_size = Column(Integer, nullable=True)  # EBS in bytes

    # Traffic conditioning
    peak_information_rate = Column(Integer, nullable=True)  # PIR in kbps
    peak_burst_size = Column(Integer, nullable=True)  # PBS in bytes

    # Additional metadata
    description = Column(Text, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    service_profile = relationship(
        "ServiceProfile", back_populates="bandwidth_profiles"
    )

    def __repr__(self):
        """  Repr   operation."""
        return f"<BandwidthProfile(name='{self.name}', direction='{self.direction}', cir={self.committed_information_rate}kbps)>"
