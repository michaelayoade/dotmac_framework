"""
Device management models for DotMac Device Management Framework.
"""

import uuid
from enum import Enum

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


class DeviceStatus(str, Enum):
    """Device status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    FAILED = "failed"
    PROVISIONING = "provisioning"
    DECOMMISSIONED = "decommissioned"


class DeviceType(str, Enum):
    """Device type enumeration."""

    SWITCH = "switch"
    ROUTER = "router"
    FIREWALL = "firewall"
    ACCESS_POINT = "access_point"
    SERVER = "server"
    OPTICAL = "optical"
    CABLE_MODEM = "cable_modem"
    ONT = "ont"
    OLT = "olt"
    UNKNOWN = "unknown"


class InterfaceType(str, Enum):
    """Interface type enumeration."""

    ETHERNET = "ethernet"
    FIBER = "fiber"
    WIRELESS = "wireless"
    SERIAL = "serial"
    MANAGEMENT = "management"
    LOOPBACK = "loopback"
    VLAN = "vlan"


class InterfaceStatus(str, Enum):
    """Interface status enumeration."""

    UP = "up"
    DOWN = "down"
    ADMIN_DOWN = "admin_down"
    TESTING = "testing"


class MonitorType(str, Enum):
    """Monitoring type enumeration."""

    SNMP = "snmp"
    TELEMETRY = "telemetry"
    PING = "ping"
    HTTP = "http"
    CUSTOM = "custom"


class NodeType(str, Enum):
    """Network node type enumeration."""

    DEVICE = "device"
    SITE = "site"
    LOGICAL = "logical"
    VIRTUAL = "virtual"


class LinkType(str, Enum):
    """Network link type enumeration."""

    PHYSICAL = "physical"
    LOGICAL = "logical"
    VIRTUAL = "virtual"
    WIRELESS = "wireless"


class Device(Base):
    """Device model for network equipment tracking."""

    __tablename__ = "device_inventory"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    device_id = Column(String(100), nullable=False, unique=True, index=True)

    # Basic device information
    hostname = Column(String(255), nullable=False)
    device_type = Column(String(50), nullable=False, default=DeviceType.UNKNOWN)
    vendor = Column(String(100))
    model = Column(String(100))
    serial_number = Column(String(100))
    firmware_version = Column(String(100))

    # Network information
    management_ip = Column(String(45))  # IPv4/IPv6
    mac_address = Column(String(17))

    # Location information
    site_id = Column(String(100), index=True)
    rack_id = Column(String(100))
    rack_unit = Column(Integer)
    location_description = Column(Text)

    # Status and lifecycle
    status = Column(String(50), nullable=False, default=DeviceStatus.ACTIVE, index=True)
    install_date = Column(DateTime)
    warranty_end = Column(DateTime)

    # Metadata
    device_metadata = Column(JSON, default=dict)
    properties = Column(JSON, default=dict)

    # Audit fields
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    created_by = Column(String(100))
    updated_by = Column(String(100))

    # Relationships
    modules = relationship(
        "DeviceModule", back_populates="device", cascade="all, delete-orphan"
    )
    interfaces = relationship(
        "DeviceInterface", back_populates="device", cascade="all, delete-orphan"
    )
    mac_addresses = relationship("MacAddress", back_populates="device")
    monitoring_records = relationship("MonitoringRecord", back_populates="device")


class DeviceModule(Base):
    """Device module/card model."""

    __tablename__ = "device_modules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    module_id = Column(String(100), nullable=False, unique=True, index=True)

    # Device relationship
    device_id = Column(
        String(100), ForeignKey("device_inventory.device_id"), nullable=False
    )

    # Module information
    slot = Column(String(50), nullable=False)
    module_type = Column(String(100))
    part_number = Column(String(100))
    serial_number = Column(String(100))
    firmware_version = Column(String(100))

    # Status
    status = Column(String(50), nullable=False, default="active")

    # Metadata
    device_metadata = Column(JSON, default=dict)

    # Audit fields
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    device = relationship("Device", back_populates="modules")


class DeviceInterface(Base):
    """Device interface/port model."""

    __tablename__ = "device_interfaces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    interface_id = Column(String(100), nullable=False, unique=True, index=True)

    # Device relationship
    device_id = Column(
        String(100), ForeignKey("device_inventory.device_id"), nullable=False
    )

    # Stable port identifier: {device_id}:{interface_name}
    port_id = Column(String(255), nullable=False, unique=True, index=True)

    # Interface information
    interface_name = Column(String(100), nullable=False)
    interface_type = Column(String(50), nullable=False, default=InterfaceType.ETHERNET)
    speed = Column(String(50))  # "1G", "10G", etc.
    duplex = Column(String(20), default="full")
    mtu = Column(Integer, default=1500)

    # Status
    admin_status = Column(String(20), nullable=False, default=InterfaceStatus.UP)
    oper_status = Column(String(20), nullable=False, default=InterfaceStatus.DOWN)

    # Network configuration
    description = Column(Text)
    vlan_id = Column(Integer)
    ip_address = Column(String(45))  # IPv4/IPv6
    subnet_mask = Column(String(45))
    mac_address = Column(String(17))

    # Statistics tracking
    last_input = Column(DateTime)
    last_output = Column(DateTime)
    input_rate = Column(Float, default=0.0)
    output_rate = Column(Float, default=0.0)

    # Metadata
    device_metadata = Column(JSON, default=dict)

    # Audit fields
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    device = relationship("Device", back_populates="interfaces")


class MacAddress(Base):
    """MAC address registry model."""

    __tablename__ = "mac_registry"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)

    # MAC address information
    mac_address = Column(
        String(17), nullable=False, unique=True, index=True
    )  # xx:xx:xx:xx:xx:xx
    oui = Column(String(8), nullable=False, index=True)  # First 3 octets
    vendor = Column(String(255))

    # Association information
    device_id = Column(String(100), ForeignKey("device_inventory.device_id"))
    interface_name = Column(String(100))
    port_id = Column(String(255))  # Stable port identifier

    # Device type and description
    device_type = Column(String(100), default="unknown")
    description = Column(Text)

    # Tracking information
    first_seen = Column(DateTime, nullable=False, server_default=func.now())
    last_seen = Column(DateTime, nullable=False, server_default=func.now())
    seen_count = Column(Integer, default=1)

    # Status
    status = Column(String(50), nullable=False, default="active", index=True)

    # Metadata
    device_metadata = Column(JSON, default=dict)

    # Audit fields
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    device = relationship("Device", back_populates="mac_addresses")


class MonitoringRecord(Base):
    """Device monitoring record model."""

    __tablename__ = "device_monitoring_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    record_id = Column(String(100), nullable=False, unique=True, index=True)

    # Device and monitor information
    device_id = Column(
        String(100),
        ForeignKey("device_inventory.device_id"),
        nullable=False,
        index=True,
    )
    monitor_id = Column(String(100), nullable=False, index=True)
    monitor_type = Column(String(50), nullable=False, default=MonitorType.SNMP)

    # Collected metrics
    metrics = Column(JSON, nullable=False, default=dict)

    # Collection information
    collection_timestamp = Column(DateTime, nullable=False, index=True)
    collection_status = Column(String(50), nullable=False, default="success")
    collection_duration_ms = Column(Float)

    # Error information
    error_message = Column(Text)
    error_code = Column(String(50))

    # Metadata
    device_metadata = Column(JSON, default=dict)

    # Audit fields
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    device = relationship("Device", back_populates="monitoring_records")


class NetworkNode(Base):
    """Network topology node model."""

    __tablename__ = "network_nodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    node_id = Column(String(100), nullable=False, unique=True, index=True)

    # Node information
    node_type = Column(String(50), nullable=False, default=NodeType.DEVICE)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Associations
    device_id = Column(String(100), ForeignKey("device_inventory.device_id"))
    site_id = Column(String(100))

    # Visualization coordinates
    x_coordinate = Column(Float)
    y_coordinate = Column(Float)
    z_coordinate = Column(Float)

    # Status and properties
    status = Column(String(50), nullable=False, default="active", index=True)
    properties = Column(JSON, default=dict)

    # Metadata
    device_metadata = Column(JSON, default=dict)

    # Audit fields
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    source_links = relationship(
        "NetworkLink",
        foreign_keys="NetworkLink.source_node_id",
        back_populates="source_node",
    )
    target_links = relationship(
        "NetworkLink",
        foreign_keys="NetworkLink.target_node_id",
        back_populates="target_node",
    )


class NetworkLink(Base):
    """Network topology link model."""

    __tablename__ = "network_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    link_id = Column(String(100), nullable=False, unique=True, index=True)

    # Link endpoints
    source_node_id = Column(
        String(100), ForeignKey("network_nodes.node_id"), nullable=False
    )
    target_node_id = Column(
        String(100), ForeignKey("network_nodes.node_id"), nullable=False
    )

    # Port/interface information
    source_port = Column(String(255))  # Port ID from source device
    target_port = Column(String(255))  # Port ID from target device

    # Link information
    link_type = Column(String(50), nullable=False, default=LinkType.PHYSICAL)
    bandwidth = Column(String(50))  # "1G", "10G", etc.
    latency_ms = Column(Float)
    cost = Column(Integer, default=1)  # For routing algorithms

    # Status
    status = Column(String(50), nullable=False, default="active", index=True)

    # Properties and metadata
    properties = Column(JSON, default=dict)
    device_metadata = Column(JSON, default=dict)

    # Audit fields
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    source_node = relationship(
        "NetworkNode", foreign_keys=[source_node_id], back_populates="source_links"
    )
    target_node = relationship(
        "NetworkNode", foreign_keys=[target_node_id], back_populates="target_links"
    )


class ConfigTemplate(Base):
    """Device configuration template model."""

    __tablename__ = "device_config_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    template_id = Column(String(100), nullable=False, unique=True, index=True)

    # Template information
    template_name = Column(String(255), nullable=False)
    description = Column(Text)
    version = Column(String(50), nullable=False, default="1.0")

    # Device targeting
    device_type = Column(String(50))
    vendor = Column(String(100))
    model = Column(String(100))

    # Template content
    template_content = Column(Text, nullable=False)
    variables = Column(JSON, default=list)  # List of variable definitions

    # Status
    status = Column(String(50), nullable=False, default="active", index=True)

    # Metadata
    device_metadata = Column(JSON, default=dict)

    # Audit fields
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    created_by = Column(String(100))
    updated_by = Column(String(100))

    # Relationships
    config_intents = relationship("ConfigIntent", back_populates="template")


class ConfigIntent(Base):
    """Device configuration intent model."""

    __tablename__ = "device_config_intents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    intent_id = Column(String(100), nullable=False, unique=True, index=True)

    # Target device
    device_id = Column(
        String(100), ForeignKey("device_inventory.device_id"), nullable=False
    )

    # Template reference
    template_id = Column(String(100), ForeignKey("device_config_templates.template_id"))

    # Intent information
    intent_type = Column(String(50), nullable=False, default="configuration")
    parameters = Column(JSON, nullable=False, default=dict)
    rendered_config = Column(Text)

    # Workflow information
    priority = Column(
        String(20), nullable=False, default="normal"
    )  # low, normal, high, urgent
    requires_approval = Column(Boolean, nullable=False, default=False)
    maintenance_window_id = Column(String(100))

    # Status tracking
    status = Column(
        String(50), nullable=False, default="pending", index=True
    )  # pending, approved, applied, failed
    applied_at = Column(DateTime)

    # Error information
    error_message = Column(Text)
    error_code = Column(String(50))

    # Metadata
    device_metadata = Column(JSON, default=dict)

    # Audit fields
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    created_by = Column(String(100))
    updated_by = Column(String(100))

    # Relationships
    template = relationship("ConfigTemplate", back_populates="config_intents")
