"""
Device management schemas for API serialization and validation.

Pydantic schemas for API serialization and validation.
"""

import re
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DeviceCreateRequest(BaseModel):
    """Schema for device creation request."""

    device_id: str = Field(..., description="Unique device identifier")
    hostname: str = Field(..., description="Device hostname")
    device_type: str = Field(default="unknown", description="Device type")
    model: Optional[str] = Field(None, description="Device model")
    vendor: Optional[str] = Field(None, description="Device vendor")
    firmware_version: Optional[str] = Field(None, description="Firmware version")
    ip_address: Optional[str] = Field(None, description="Primary IP address")
    mac_address: Optional[str] = Field(None, description="Primary MAC address")
    site_id: Optional[str] = Field(None, description="Site identifier")
    location: Optional[str] = Field(None, description="Physical location")
    description: Optional[str] = Field(None, description="Device description")
    status: str = Field(default="active", description="Device status")
    properties: dict[str, Any] = Field(default_factory=dict, description="Additional properties")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    model_config = ConfigDict(from_attributes=True)

    @field_validator("device_id")
    @classmethod
    def validate_device_id(cls, v):
        if not v or not v.strip():
            raise ValueError("device_id cannot be empty")
        # Allow alphanumeric, hyphens, underscores, dots
        if not re.match(r"^[a-zA-Z0-9._-]+$", v):
            raise ValueError("device_id contains invalid characters")
        return v.strip()

    @field_validator("hostname")
    @classmethod
    def validate_hostname(cls, v):
        if not v or not v.strip():
            raise ValueError("hostname cannot be empty")
        # Basic hostname validation
        if not re.match(r"^[a-zA-Z0-9.-]+$", v):
            raise ValueError("Invalid hostname format")
        return v.strip()


class DeviceResponse(BaseModel):
    """Schema for device response."""

    id: str
    tenant_id: str
    device_id: str
    hostname: str
    device_type: str
    model: Optional[str]
    vendor: Optional[str]
    firmware_version: Optional[str]
    ip_address: Optional[str]
    mac_address: Optional[str]
    site_id: Optional[str]
    location: Optional[str]
    description: Optional[str]
    status: str
    properties: dict[str, Any]
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    updated_by: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class ConfigIntentRequest(BaseModel):
    """Schema for configuration intent request."""

    device_id: str = Field(..., description="Target device identifier")
    intent_type: str = Field(..., description="Type of configuration intent")
    config_data: dict[str, Any] = Field(..., description="Configuration data")
    apply_immediately: bool = Field(default=False, description="Apply configuration immediately")
    validate_only: bool = Field(default=False, description="Only validate configuration")

    model_config = ConfigDict(from_attributes=True)


class ConfigIntentResponse(BaseModel):
    """Schema for configuration intent response."""

    intent_id: str = Field(..., description="Configuration intent identifier")
    device_id: str = Field(..., description="Target device identifier")
    intent_type: str = Field(..., description="Type of configuration intent")
    status: str = Field(..., description="Intent processing status")
    result: Optional[dict[str, Any]] = Field(None, description="Processing result")
    errors: list[str] = Field(default_factory=list, description="Processing errors")
    warnings: list[str] = Field(default_factory=list, description="Processing warnings")
    applied_at: Optional[datetime] = Field(None, description="When configuration was applied")

    model_config = ConfigDict(from_attributes=True)


class ConfigTemplateResponse(BaseModel):
    """Schema for configuration template response."""

    template_id: str = Field(..., description="Configuration template identifier")
    device_type: str = Field(..., description="Target device type")
    template_name: str = Field(..., description="Template name")
    template_content: str = Field(..., description="Template content")
    version: str = Field(..., description="Template version")
    created_at: datetime = Field(..., description="When template was created")
    updated_at: datetime = Field(..., description="When template was last updated")
    is_active: bool = Field(True, description="Whether template is active")

    model_config = ConfigDict(from_attributes=True)


class DeviceInterfaceResponse(BaseModel):
    """Schema for device interface response."""

    interface_id: str = Field(..., description="Interface identifier")
    device_id: str = Field(..., description="Parent device identifier")
    interface_name: str = Field(..., description="Interface name (e.g., eth0, gi0/0/1)")
    interface_type: str = Field(..., description="Interface type (ethernet, serial, etc.)")
    mac_address: Optional[str] = Field(None, description="Interface MAC address")
    ip_address: Optional[str] = Field(None, description="Interface IP address")
    subnet_mask: Optional[str] = Field(None, description="Interface subnet mask")
    status: str = Field(default="unknown", description="Interface operational status")
    admin_status: str = Field(default="up", description="Interface administrative status")
    speed: Optional[int] = Field(None, description="Interface speed in Mbps")
    duplex: Optional[str] = Field(None, description="Interface duplex mode")
    description: Optional[str] = Field(None, description="Interface description")
    vlan_id: Optional[int] = Field(None, description="VLAN ID if applicable")
    created_at: datetime = Field(..., description="When interface was discovered")
    updated_at: datetime = Field(..., description="When interface was last updated")

    model_config = ConfigDict(from_attributes=True)


class DeviceModuleResponse(BaseModel):
    """Schema for device module response."""

    module_id: str = Field(..., description="Module identifier")
    device_id: str = Field(..., description="Parent device identifier")
    module_name: str = Field(..., description="Module name")
    module_type: str = Field(..., description="Module type (linecard, supervisor, etc.)")
    slot_number: Optional[int] = Field(None, description="Physical slot number")
    serial_number: Optional[str] = Field(None, description="Module serial number")
    part_number: Optional[str] = Field(None, description="Module part number")
    firmware_version: Optional[str] = Field(None, description="Module firmware version")
    status: str = Field(default="unknown", description="Module operational status")
    description: Optional[str] = Field(None, description="Module description")
    created_at: datetime = Field(..., description="When module was discovered")
    updated_at: datetime = Field(..., description="When module was last updated")

    model_config = ConfigDict(from_attributes=True)


class MonitoringRecordResponse(BaseModel):
    """Schema for monitoring record response."""

    record_id: str = Field(..., description="Monitoring record identifier")
    device_id: str = Field(..., description="Target device identifier")
    metric_name: str = Field(..., description="Metric name (cpu, memory, interface_util)")
    metric_value: float = Field(..., description="Metric value")
    metric_unit: str = Field(..., description="Metric unit (%, bytes, pps)")
    threshold_warning: Optional[float] = Field(None, description="Warning threshold")
    threshold_critical: Optional[float] = Field(None, description="Critical threshold")
    status: str = Field(default="normal", description="Current status based on thresholds")
    timestamp: datetime = Field(..., description="When metric was collected")
    additional_data: dict[str, Any] = Field(default_factory=dict, description="Additional metric data")

    model_config = ConfigDict(from_attributes=True)


class MacAddressResponse(BaseModel):
    """Schema for MAC address response."""

    mac_id: str = Field(..., description="MAC address record identifier")
    mac_address: str = Field(..., description="MAC address")
    device_id: Optional[str] = Field(None, description="Associated device identifier")
    interface_name: Optional[str] = Field(None, description="Associated interface name")
    vlan_id: Optional[int] = Field(None, description="VLAN ID")
    learned_from: str = Field(..., description="How MAC was learned (static, dynamic)")
    first_seen: datetime = Field(..., description="When MAC was first seen")
    last_seen: datetime = Field(..., description="When MAC was last seen")
    is_static: bool = Field(default=False, description="Whether MAC is statically configured")

    model_config = ConfigDict(from_attributes=True)


class NetworkNodeResponse(BaseModel):
    """Schema for network node response."""

    node_id: str = Field(..., description="Network node identifier")
    device_id: Optional[str] = Field(None, description="Associated device identifier")
    node_name: str = Field(..., description="Node name")
    node_type: str = Field(..., description="Node type (switch, router, host)")
    ip_address: Optional[str] = Field(None, description="Primary IP address")
    location: Optional[str] = Field(None, description="Physical location")
    coordinates: Optional[dict[str, float]] = Field(None, description="Geographic coordinates")
    properties: dict[str, Any] = Field(default_factory=dict, description="Additional node properties")
    created_at: datetime = Field(..., description="When node was created")
    updated_at: datetime = Field(..., description="When node was last updated")

    model_config = ConfigDict(from_attributes=True)


class NetworkLinkResponse(BaseModel):
    """Schema for network link response."""

    link_id: str = Field(..., description="Network link identifier")
    source_node_id: str = Field(..., description="Source node identifier")
    target_node_id: str = Field(..., description="Target node identifier")
    source_interface: Optional[str] = Field(None, description="Source interface name")
    target_interface: Optional[str] = Field(None, description="Target interface name")
    link_type: str = Field(..., description="Link type (ethernet, fiber, wireless)")
    bandwidth: Optional[int] = Field(None, description="Link bandwidth in Mbps")
    utilization: Optional[float] = Field(None, description="Current utilization percentage")
    status: str = Field(default="up", description="Link operational status")
    properties: dict[str, Any] = Field(default_factory=dict, description="Additional link properties")
    created_at: datetime = Field(..., description="When link was discovered")
    updated_at: datetime = Field(..., description="When link was last updated")

    model_config = ConfigDict(from_attributes=True)


class TopologyResponse(BaseModel):
    """Schema for network topology response."""

    topology_id: str = Field(..., description="Topology identifier")
    topology_name: str = Field(..., description="Topology name")
    description: Optional[str] = Field(None, description="Topology description")
    nodes: list[NetworkNodeResponse] = Field(default_factory=list, description="Network nodes")
    links: list[NetworkLinkResponse] = Field(default_factory=list, description="Network links")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional topology metadata")
    created_at: datetime = Field(..., description="When topology was created")
    updated_at: datetime = Field(..., description="When topology was last updated")

    model_config = ConfigDict(from_attributes=True)
