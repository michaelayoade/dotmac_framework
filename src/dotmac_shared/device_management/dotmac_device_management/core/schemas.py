"""
Device Management Framework Schemas.

Pydantic schemas for API serialization and validation.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class DeviceCreateRequest(BaseModel):
    """Schema for device creation request."""

    device_id: str = Field(..., description="Unique device identifier")
    hostname: str = Field(..., description="Device hostname")
    device_type: str = Field(default="unknown", description="Device type")
    vendor: Optional[str] = Field(None, description="Device vendor")
    model: Optional[str] = Field(None, description="Device model")
    serial_number: Optional[str] = Field(None, description="Serial number")
    firmware_version: Optional[str] = Field(None, description="Firmware version")
    management_ip: Optional[str] = Field(None, description="Management IP address")
    mac_address: Optional[str] = Field(None, description="Management MAC address")
    site_id: Optional[str] = Field(None, description="Site identifier")
    rack_id: Optional[str] = Field(None, description="Rack identifier")
    rack_unit: Optional[int] = Field(None, description="Rack unit position")
    location_description: Optional[str] = Field(
        None, description="Location description"
    )
    status: str = Field(default="active", description="Device status")
    install_date: Optional[datetime] = Field(None, description="Installation date")
    warranty_end: Optional[datetime] = Field(None, description="Warranty end date")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    properties: Dict[str, Any] = Field(
        default_factory=dict, description="Device properties"
    )

    @validator("device_id")
    def validate_device_id(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Device ID cannot be empty")
        return v.strip()

    @validator("management_ip")
    def validate_management_ip(cls, v):
        if v is None:
            return v
        # Basic IP validation (IPv4/IPv6)
        if not re.match(r"^[\d\.\:a-fA-F]+$", v):
            raise ValueError("Invalid IP address format")
        return v


class DeviceResponse(BaseModel):
    """Schema for device response."""

    id: str
    tenant_id: str
    device_id: str
    hostname: str
    device_type: str
    vendor: Optional[str]
    model: Optional[str]
    serial_number: Optional[str]
    firmware_version: Optional[str]
    management_ip: Optional[str]
    mac_address: Optional[str]
    site_id: Optional[str]
    rack_id: Optional[str]
    rack_unit: Optional[int]
    location_description: Optional[str]
    status: str
    install_date: Optional[datetime]
    warranty_end: Optional[datetime]
    metadata: Dict[str, Any]
    properties: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    updated_by: Optional[str]

    class Config:
        """Config implementation."""

        from_attributes = True


class DeviceModuleResponse(BaseModel):
    """Schema for device module response."""

    id: str
    tenant_id: str
    module_id: str
    device_id: str
    slot: str
    module_type: Optional[str]
    part_number: Optional[str]
    serial_number: Optional[str]
    firmware_version: Optional[str]
    status: str
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        """Config implementation."""

        from_attributes = True


class DeviceInterfaceResponse(BaseModel):
    """Schema for device interface response."""

    id: str
    tenant_id: str
    interface_id: str
    device_id: str
    port_id: str
    interface_name: str
    interface_type: str
    speed: Optional[str]
    duplex: str
    mtu: int
    admin_status: str
    oper_status: str
    description: Optional[str]
    vlan_id: Optional[int]
    ip_address: Optional[str]
    subnet_mask: Optional[str]
    mac_address: Optional[str]
    last_input: Optional[datetime]
    last_output: Optional[datetime]
    input_rate: float
    output_rate: float
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        """Config implementation."""

        from_attributes = True


class MacAddressResponse(BaseModel):
    """Schema for MAC address response."""

    id: str
    tenant_id: str
    mac_address: str
    oui: str
    vendor: str
    device_id: Optional[str]
    interface_name: Optional[str]
    port_id: Optional[str]
    device_type: str
    description: Optional[str]
    first_seen: datetime
    last_seen: datetime
    seen_count: int
    status: str
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        """Config implementation."""

        from_attributes = True


class MonitoringRecordResponse(BaseModel):
    """Schema for monitoring record response."""

    id: str
    tenant_id: str
    record_id: str
    device_id: str
    monitor_id: str
    monitor_type: str
    metrics: Dict[str, Any]
    collection_timestamp: datetime
    collection_status: str
    collection_duration_ms: Optional[float]
    error_message: Optional[str]
    error_code: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime

    class Config:
        """Config implementation."""

        from_attributes = True


class NetworkNodeResponse(BaseModel):
    """Schema for network node response."""

    id: str
    tenant_id: str
    node_id: str
    node_type: str
    name: str
    description: Optional[str]
    device_id: Optional[str]
    site_id: Optional[str]
    x_coordinate: Optional[float]
    y_coordinate: Optional[float]
    z_coordinate: Optional[float]
    status: str
    properties: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        """Config implementation."""

        from_attributes = True


class NetworkLinkResponse(BaseModel):
    """Schema for network link response."""

    id: str
    tenant_id: str
    link_id: str
    source_node_id: str
    target_node_id: str
    source_port: Optional[str]
    target_port: Optional[str]
    link_type: str
    bandwidth: Optional[str]
    latency_ms: Optional[float]
    cost: int
    status: str
    properties: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        """Config implementation."""

        from_attributes = True


class ConfigTemplateResponse(BaseModel):
    """Schema for configuration template response."""

    id: str
    tenant_id: str
    template_id: str
    template_name: str
    description: Optional[str]
    version: str
    device_type: Optional[str]
    vendor: Optional[str]
    model: Optional[str]
    template_content: str
    variables: List[str]
    status: str
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    updated_by: Optional[str]

    class Config:
        """Config implementation."""

        from_attributes = True


class ConfigIntentResponse(BaseModel):
    """Schema for configuration intent response."""

    id: str
    tenant_id: str
    intent_id: str
    device_id: str
    template_id: Optional[str]
    intent_type: str
    parameters: Dict[str, Any]
    rendered_config: Optional[str]
    priority: str
    requires_approval: bool
    maintenance_window_id: Optional[str]
    status: str
    applied_at: Optional[datetime]
    error_message: Optional[str]
    error_code: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    updated_by: Optional[str]

    class Config:
        """Config implementation."""

        from_attributes = True


class TopologyResponse(BaseModel):
    """Schema for topology response."""

    nodes: List[NetworkNodeResponse]
    links: List[NetworkLinkResponse]
    node_count: int
    link_count: int
    site_id: Optional[str] = None

    class Config:
        """Config implementation."""

        from_attributes = True


class DeviceHealthSummary(BaseModel):
    """Schema for device health summary."""

    device_id: str
    hostname: str
    device_type: str
    status: str
    site_id: Optional[str]
    interfaces: Dict[str, int]
    modules: Dict[str, int]
    last_updated: datetime
    uptime_days: Optional[int]


class MonitoringOverview(BaseModel):
    """Schema for monitoring overview."""

    device_id: str
    health_status: Dict[str, Any]
    active_monitors: List[Dict[str, Any]]
    total_records: int
    monitoring_active: bool


class NetworkPathResponse(BaseModel):
    """Schema for network path response."""

    source_device: str
    target_device: str
    path_found: bool
    hop_count: int
    path_details: List[Dict[str, Any]]
    metrics: Dict[str, Any]


class DeviceConnectivityResponse(BaseModel):
    """Schema for device connectivity response."""

    device_id: str
    node_info: Dict[str, Any]
    connectivity_summary: Dict[str, Any]
    neighbors: List[Dict[str, Any]]
    links: List[Dict[str, Any]]


class MacAddressCreateRequest(BaseModel):
    """Schema for MAC address registration request."""

    mac_address: str = Field(..., description="MAC address in any format")
    device_id: Optional[str] = Field(None, description="Associated device ID")
    interface_name: Optional[str] = Field(None, description="Interface name")
    device_type: str = Field(default="unknown", description="Device type")
    description: Optional[str] = Field(None, description="Description")
    status: str = Field(default="active", description="Status")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    @validator("mac_address")
    def validate_mac_address(cls, v):
        # Basic MAC address validation
        mac_clean = re.sub(r"[:-]", "", v.lower())
        if len(mac_clean) != 12 or not re.match(r"^[0-9a-f]{12}$", mac_clean):
            raise ValueError("Invalid MAC address format")
        return v


class NetworkNodeCreateRequest(BaseModel):
    """Schema for network node creation request."""

    node_id: str = Field(..., description="Unique node identifier")
    node_type: str = Field(default="device", description="Node type")
    name: str = Field(..., description="Node name")
    description: Optional[str] = Field(None, description="Node description")
    device_id: Optional[str] = Field(None, description="Associated device ID")
    site_id: Optional[str] = Field(None, description="Site identifier")
    x_coordinate: Optional[float] = Field(
        None, description="X coordinate for visualization"
    )
    y_coordinate: Optional[float] = Field(
        None, description="Y coordinate for visualization"
    )
    z_coordinate: Optional[float] = Field(
        None, description="Z coordinate for visualization"
    )
    status: str = Field(default="active", description="Node status")
    properties: Dict[str, Any] = Field(
        default_factory=dict, description="Node properties"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class NetworkLinkCreateRequest(BaseModel):
    """Schema for network link creation request."""

    link_id: Optional[str] = Field(
        None, description="Unique link identifier (auto-generated if not provided)"
    )
    source_node_id: str = Field(..., description="Source node identifier")
    target_node_id: str = Field(..., description="Target node identifier")
    source_port: Optional[str] = Field(None, description="Source port identifier")
    target_port: Optional[str] = Field(None, description="Target port identifier")
    link_type: str = Field(default="physical", description="Link type")
    bandwidth: Optional[str] = Field(None, description="Link bandwidth")
    latency_ms: Optional[float] = Field(
        None, description="Link latency in milliseconds"
    )
    cost: int = Field(default=1, description="Link cost for routing algorithms")
    status: str = Field(default="active", description="Link status")
    properties: Dict[str, Any] = Field(
        default_factory=dict, description="Link properties"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
