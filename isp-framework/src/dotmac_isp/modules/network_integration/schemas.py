"""Network Integration Pydantic schemas."""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict, IPvAnyAddress
from decimal import Decimal

from .models import (
    DeviceType,
    DeviceStatus,
    InterfaceType,
    InterfaceStatus,
    AlertSeverity,
    AlertType,
)


# Base schemas
class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(from_attributes=True)


# Network Device schemas
class NetworkDeviceBase(BaseSchema):
    """Base network device schema."""

    name: str = Field(..., min_length=1, max_length=255, description="Device name")
    hostname: Optional[str] = Field(None, max_length=255, description="Device hostname")
    device_type: DeviceType = Field(..., description="Device type")
    model: Optional[str] = Field(None, max_length=100, description="Device model")
    vendor: Optional[str] = Field(None, max_length=100, description="Device vendor")
    serial_number: Optional[str] = Field(
        None, max_length=100, description="Serial number"
    )
    asset_tag: Optional[str] = Field(None, max_length=100, description="Asset tag")
    description: Optional[str] = Field(None, description="Device description")


class NetworkDeviceCreate(NetworkDeviceBase):
    """Schema for creating a network device."""

    management_ip: Optional[IPvAnyAddress] = Field(
        None, description="Management IP address"
    )
    subnet_mask: Optional[str] = Field(None, max_length=18, description="Subnet mask")
    gateway: Optional[IPvAnyAddress] = Field(None, description="Default gateway")
    dns_servers: Optional[List[str]] = Field(None, description="DNS servers")

    # SNMP configuration
    snmp_community: Optional[str] = Field(
        None, max_length=100, description="SNMP community string"
    )
    snmp_version: str = Field(default="v2c", description="SNMP version")
    snmp_port: int = Field(default=161, ge=1, le=65535, description="SNMP port")
    snmp_enabled: bool = Field(default=True, description="SNMP monitoring enabled")

    # Device specifications
    cpu_count: Optional[int] = Field(None, ge=1, description="Number of CPUs")
    memory_total_mb: Optional[int] = Field(None, ge=1, description="Total memory in MB")
    storage_total_gb: Optional[int] = Field(
        None, ge=1, description="Total storage in GB"
    )
    power_consumption_watts: Optional[int] = Field(
        None, ge=1, description="Power consumption in watts"
    )

    # Software information
    os_version: Optional[str] = Field(
        None, max_length=100, description="Operating system version"
    )
    firmware_version: Optional[str] = Field(
        None, max_length=100, description="Firmware version"
    )

    # Location details
    street_address: Optional[str] = Field(
        None, max_length=255, description="Street address"
    )
    city: Optional[str] = Field(None, max_length=100, description="City")
    state_province: Optional[str] = Field(
        None, max_length=100, description="State/Province"
    )
    postal_code: Optional[str] = Field(None, max_length=20, description="Postal code")
    country_code: str = Field(default="US", max_length=2, description="Country code")

    rack_location: Optional[str] = Field(
        None, max_length=100, description="Rack location"
    )
    rack_unit: Optional[str] = Field(None, max_length=10, description="Rack unit")
    datacenter: Optional[str] = Field(None, max_length=100, description="Datacenter")

    # Monitoring settings
    monitoring_enabled: bool = Field(default=True, description="Monitoring enabled")
    monitoring_interval: int = Field(
        default=300, ge=30, le=3600, description="Monitoring interval in seconds"
    )

    # Maintenance information
    warranty_expires: Optional[datetime] = Field(
        None, description="Warranty expiration date"
    )
    next_maintenance: Optional[datetime] = Field(
        None, description="Next maintenance date"
    )

    # Metadata
    tags: Optional[List[str]] = Field(None, description="Device tags")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="Custom fields")


class NetworkDeviceUpdate(BaseSchema):
    """Schema for updating a network device."""

    name: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Device name"
    )
    hostname: Optional[str] = Field(None, max_length=255, description="Device hostname")
    device_type: Optional[DeviceType] = Field(None, description="Device type")
    model: Optional[str] = Field(None, max_length=100, description="Device model")
    vendor: Optional[str] = Field(None, max_length=100, description="Device vendor")
    management_ip: Optional[IPvAnyAddress] = Field(
        None, description="Management IP address"
    )
    snmp_community: Optional[str] = Field(
        None, max_length=100, description="SNMP community string"
    )
    monitoring_enabled: Optional[bool] = Field(None, description="Monitoring enabled")
    monitoring_interval: Optional[int] = Field(
        None, ge=30, le=3600, description="Monitoring interval in seconds"
    )
    description: Optional[str] = Field(None, description="Device description")
    tags: Optional[List[str]] = Field(None, description="Device tags")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="Custom fields")


class NetworkDeviceResponse(NetworkDeviceBase):
    """Schema for network device response."""

    id: str = Field(..., description="Device ID")
    tenant_id: str = Field(..., description="Tenant ID")
    status: str = Field(..., description="Device status")
    management_ip: Optional[str] = Field(None, description="Management IP address")
    subnet_mask: Optional[str] = Field(None, description="Subnet mask")
    gateway: Optional[str] = Field(None, description="Default gateway")

    # SNMP configuration
    snmp_version: str = Field(..., description="SNMP version")
    snmp_port: int = Field(..., description="SNMP port")
    snmp_enabled: bool = Field(..., description="SNMP monitoring enabled")

    # Device specifications
    cpu_count: Optional[int] = Field(None, description="Number of CPUs")
    memory_total_mb: Optional[int] = Field(None, description="Total memory in MB")
    storage_total_gb: Optional[int] = Field(None, description="Total storage in GB")

    # Software information
    os_version: Optional[str] = Field(None, description="Operating system version")
    firmware_version: Optional[str] = Field(None, description="Firmware version")
    last_config_backup: Optional[datetime] = Field(
        None, description="Last configuration backup"
    )

    # Location
    street_address: Optional[str] = Field(None, description="Street address")
    city: Optional[str] = Field(None, description="City")
    full_address: Optional[str] = Field(None, description="Full formatted address")

    # Monitoring
    monitoring_enabled: bool = Field(..., description="Monitoring enabled")
    monitoring_interval: int = Field(..., description="Monitoring interval in seconds")

    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    # Metadata
    tags: Optional[List[str]] = Field(None, description="Device tags")


# Network Interface schemas
class NetworkInterfaceBase(BaseSchema):
    """Base network interface schema."""

    name: str = Field(..., min_length=1, max_length=100, description="Interface name")
    description: Optional[str] = Field(None, description="Interface description")
    interface_type: InterfaceType = Field(..., description="Interface type")


class NetworkInterfaceCreate(NetworkInterfaceBase):
    """Schema for creating a network interface."""

    device_id: str = Field(..., description="Parent device ID")
    interface_index: Optional[int] = Field(None, description="SNMP interface index")
    ip_address: Optional[IPvAnyAddress] = Field(None, description="IP address")
    subnet_mask: Optional[str] = Field(None, max_length=18, description="Subnet mask")
    vlan_id: Optional[int] = Field(None, ge=1, le=4094, description="VLAN ID")
    mac_address: Optional[str] = Field(None, description="MAC address")
    speed_mbps: Optional[int] = Field(None, ge=1, description="Interface speed in Mbps")
    duplex: Optional[str] = Field(None, description="Duplex mode")
    mtu: int = Field(default=1500, ge=68, le=9000, description="MTU size")
    admin_status: InterfaceStatus = Field(
        default=InterfaceStatus.UP, description="Administrative status"
    )
    tags: Optional[List[str]] = Field(None, description="Interface tags")


class NetworkInterfaceUpdate(BaseSchema):
    """Schema for updating a network interface."""

    name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Interface name"
    )
    description: Optional[str] = Field(None, description="Interface description")
    ip_address: Optional[IPvAnyAddress] = Field(None, description="IP address")
    vlan_id: Optional[int] = Field(None, ge=1, le=4094, description="VLAN ID")
    admin_status: Optional[InterfaceStatus] = Field(
        None, description="Administrative status"
    )
    tags: Optional[List[str]] = Field(None, description="Interface tags")


class NetworkInterfaceResponse(NetworkInterfaceBase):
    """Schema for network interface response."""

    id: str = Field(..., description="Interface ID")
    device_id: str = Field(..., description="Parent device ID")
    tenant_id: str = Field(..., description="Tenant ID")
    interface_index: Optional[int] = Field(None, description="SNMP interface index")
    ip_address: Optional[str] = Field(None, description="IP address")
    mac_address: Optional[str] = Field(None, description="MAC address")
    speed_mbps: Optional[int] = Field(None, description="Interface speed in Mbps")
    admin_status: InterfaceStatus = Field(..., description="Administrative status")
    operational_status: InterfaceStatus = Field(..., description="Operational status")
    last_change: Optional[datetime] = Field(None, description="Last status change")

    # Traffic counters
    bytes_in: int = Field(..., description="Bytes received")
    bytes_out: int = Field(..., description="Bytes transmitted")
    packets_in: int = Field(..., description="Packets received")
    packets_out: int = Field(..., description="Packets transmitted")
    errors_in: int = Field(..., description="Input errors")
    errors_out: int = Field(..., description="Output errors")

    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# Network Location schemas
class NetworkLocationBase(BaseSchema):
    """Base network location schema."""

    name: str = Field(..., min_length=1, max_length=255, description="Location name")
    location_type: str = Field(..., max_length=50, description="Location type")
    code: Optional[str] = Field(None, max_length=20, description="Location code")


class NetworkLocationCreate(NetworkLocationBase):
    """Schema for creating a network location."""

    # Geographic coordinates
    latitude: Optional[Decimal] = Field(None, description="Latitude")
    longitude: Optional[Decimal] = Field(None, description="Longitude")
    elevation_meters: Optional[float] = Field(None, description="Elevation in meters")

    # Address
    street_address: Optional[str] = Field(
        None, max_length=255, description="Street address"
    )
    city: Optional[str] = Field(None, max_length=100, description="City")
    state_province: Optional[str] = Field(
        None, max_length=100, description="State/Province"
    )
    postal_code: Optional[str] = Field(None, max_length=20, description="Postal code")
    country_code: str = Field(default="US", max_length=2, description="Country code")

    # Facility details
    facility_size_sqm: Optional[float] = Field(
        None, ge=0, description="Facility size in square meters"
    )
    power_capacity_kw: Optional[float] = Field(
        None, ge=0, description="Power capacity in kW"
    )
    cooling_capacity_tons: Optional[float] = Field(
        None, ge=0, description="Cooling capacity in tons"
    )
    rack_count: Optional[int] = Field(None, ge=0, description="Number of racks")

    # Contact information
    contact_person: Optional[str] = Field(
        None, max_length=255, description="Contact person"
    )
    contact_phone: Optional[str] = Field(
        None, max_length=20, description="Contact phone"
    )
    contact_email: Optional[str] = Field(
        None, max_length=255, description="Contact email"
    )

    # Service area
    service_area_radius_km: Optional[float] = Field(
        None, ge=0, description="Service area radius in km"
    )
    population_served: Optional[int] = Field(
        None, ge=0, description="Population served"
    )

    description: Optional[str] = Field(None, description="Location description")
    tags: Optional[List[str]] = Field(None, description="Location tags")


class NetworkLocationUpdate(BaseSchema):
    """Schema for updating a network location."""

    name: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Location name"
    )
    location_type: Optional[str] = Field(
        None, max_length=50, description="Location type"
    )
    latitude: Optional[Decimal] = Field(None, description="Latitude")
    longitude: Optional[Decimal] = Field(None, description="Longitude")
    contact_person: Optional[str] = Field(
        None, max_length=255, description="Contact person"
    )
    contact_phone: Optional[str] = Field(
        None, max_length=20, description="Contact phone"
    )
    description: Optional[str] = Field(None, description="Location description")
    tags: Optional[List[str]] = Field(None, description="Location tags")


class NetworkLocationResponse(NetworkLocationBase):
    """Schema for network location response."""

    id: str = Field(..., description="Location ID")
    tenant_id: str = Field(..., description="Tenant ID")
    latitude: Optional[str] = Field(None, description="Latitude")
    longitude: Optional[str] = Field(None, description="Longitude")
    coordinates: Optional[Dict[str, float]] = Field(
        None, description="Coordinates as lat/lon dict"
    )

    # Address
    street_address: Optional[str] = Field(None, description="Street address")
    city: Optional[str] = Field(None, description="City")
    full_address: Optional[str] = Field(None, description="Full formatted address")

    # Facility details
    facility_size_sqm: Optional[float] = Field(
        None, description="Facility size in square meters"
    )
    rack_count: Optional[int] = Field(None, description="Number of racks")

    # Contact information
    contact_person: Optional[str] = Field(None, description="Contact person")
    contact_phone: Optional[str] = Field(None, description="Contact phone")

    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# Network Metric schemas
class NetworkMetricResponse(BaseSchema):
    """Schema for network metric response."""

    id: str = Field(..., description="Metric ID")
    device_id: str = Field(..., description="Device ID")
    interface_id: Optional[str] = Field(None, description="Interface ID")
    metric_name: str = Field(..., description="Metric name")
    metric_type: str = Field(..., description="Metric type")
    value: float = Field(..., description="Metric value")
    unit: Optional[str] = Field(None, description="Metric unit")
    timestamp: datetime = Field(..., description="Metric timestamp")
    tags: Optional[Dict[str, str]] = Field(None, description="Metric tags")


# Network Topology schemas
class NetworkTopologyResponse(BaseSchema):
    """Schema for network topology response."""

    id: str = Field(..., description="Topology ID")
    parent_device_id: str = Field(..., description="Parent device ID")
    child_device_id: str = Field(..., description="Child device ID")
    connection_type: str = Field(..., description="Connection type")
    parent_interface_id: Optional[str] = Field(None, description="Parent interface ID")
    child_interface_id: Optional[str] = Field(None, description="Child interface ID")
    bandwidth_mbps: Optional[int] = Field(
        None, description="Connection bandwidth in Mbps"
    )
    distance_meters: Optional[float] = Field(
        None, description="Connection distance in meters"
    )
    description: Optional[str] = Field(None, description="Connection description")


# Device Configuration schemas
class DeviceConfigurationCreate(BaseSchema):
    """Schema for creating a device configuration."""

    device_id: str = Field(..., description="Device ID")
    name: str = Field(
        ..., min_length=1, max_length=255, description="Configuration name"
    )
    version: str = Field(..., max_length=50, description="Configuration version")
    configuration_data: str = Field(..., description="Configuration data")
    source: Optional[str] = Field(
        None, max_length=50, description="Configuration source"
    )
    description: Optional[str] = Field(None, description="Configuration description")
    tags: Optional[List[str]] = Field(None, description="Configuration tags")


class DeviceConfigurationResponse(BaseSchema):
    """Schema for device configuration response."""

    id: str = Field(..., description="Configuration ID")
    device_id: str = Field(..., description="Device ID")
    name: str = Field(..., description="Configuration name")
    version: str = Field(..., description="Configuration version")
    is_active: bool = Field(..., description="Is active configuration")
    is_backup: bool = Field(..., description="Is backup configuration")
    configuration_hash: Optional[str] = Field(None, description="Configuration hash")
    source: Optional[str] = Field(None, description="Configuration source")
    deployment_status: str = Field(..., description="Deployment status")
    deployment_time: Optional[datetime] = Field(None, description="Deployment time")
    syntax_validated: bool = Field(..., description="Syntax validation status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# Network Alert schemas
class NetworkAlertResponse(BaseSchema):
    """Schema for network alert response."""

    id: str = Field(..., description="Alert ID")
    device_id: Optional[str] = Field(None, description="Device ID")
    interface_id: Optional[str] = Field(None, description="Interface ID")
    alert_type: AlertType = Field(..., description="Alert type")
    severity: AlertSeverity = Field(..., description="Alert severity")
    title: str = Field(..., description="Alert title")
    message: str = Field(..., description="Alert message")
    is_active: bool = Field(..., description="Is alert active")
    is_acknowledged: bool = Field(..., description="Is alert acknowledged")
    acknowledged_at: Optional[datetime] = Field(
        None, description="Acknowledgment timestamp"
    )
    resolved_at: Optional[datetime] = Field(None, description="Resolution timestamp")
    metric_name: Optional[str] = Field(None, description="Related metric name")
    threshold_value: Optional[float] = Field(None, description="Threshold value")
    current_value: Optional[float] = Field(None, description="Current metric value")
    created_at: datetime = Field(..., description="Creation timestamp")


# Device Group schemas
class DeviceGroupCreate(BaseSchema):
    """Schema for creating a device group."""

    name: str = Field(..., min_length=1, max_length=255, description="Group name")
    group_type: str = Field(..., max_length=50, description="Group type")
    monitoring_template: Optional[str] = Field(
        None, max_length=255, description="Monitoring template"
    )
    alert_rules: Optional[Dict[str, Any]] = Field(None, description="Alert rules")
    description: Optional[str] = Field(None, description="Group description")
    tags: Optional[List[str]] = Field(None, description="Group tags")


class DeviceGroupResponse(BaseSchema):
    """Schema for device group response."""

    id: str = Field(..., description="Group ID")
    tenant_id: str = Field(..., description="Tenant ID")
    name: str = Field(..., description="Group name")
    group_type: str = Field(..., description="Group type")
    monitoring_template: Optional[str] = Field(None, description="Monitoring template")
    description: Optional[str] = Field(None, description="Group description")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# Network Service schemas
class NetworkServiceCreate(BaseSchema):
    """Schema for creating a network service."""

    name: str = Field(..., min_length=1, max_length=255, description="Service name")
    service_type: str = Field(..., max_length=100, description="Service type")
    protocol: str = Field(..., max_length=20, description="Protocol")
    port: Optional[int] = Field(None, ge=1, le=65535, description="Port number")
    listen_address: Optional[IPvAnyAddress] = Field(None, description="Listen address")
    configuration: Optional[Dict[str, Any]] = Field(
        None, description="Service configuration"
    )
    health_check_enabled: bool = Field(default=True, description="Health check enabled")
    description: Optional[str] = Field(None, description="Service description")
    tags: Optional[List[str]] = Field(None, description="Service tags")


class NetworkServiceResponse(BaseSchema):
    """Schema for network service response."""

    id: str = Field(..., description="Service ID")
    tenant_id: str = Field(..., description="Tenant ID")
    name: str = Field(..., description="Service name")
    service_type: str = Field(..., description="Service type")
    protocol: str = Field(..., description="Protocol")
    port: Optional[int] = Field(None, description="Port number")
    listen_address: Optional[str] = Field(None, description="Listen address")
    status: str = Field(..., description="Service status")
    health_check_enabled: bool = Field(..., description="Health check enabled")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# Maintenance Window schemas
class MaintenanceWindowCreate(BaseSchema):
    """Schema for creating a maintenance window."""

    name: str = Field(
        ..., min_length=1, max_length=255, description="Maintenance window name"
    )
    maintenance_type: str = Field(..., max_length=50, description="Maintenance type")
    start_time: datetime = Field(..., description="Start time")
    end_time: datetime = Field(..., description="End time")
    timezone: str = Field(default="UTC", max_length=50, description="Timezone")
    impact_level: str = Field(..., max_length=20, description="Impact level")
    description: str = Field(..., description="Maintenance description")
    work_instructions: Optional[str] = Field(None, description="Work instructions")
    rollback_plan: Optional[str] = Field(None, description="Rollback plan")
    affected_services: Optional[List[str]] = Field(
        None, description="Affected services"
    )
    notifications_enabled: bool = Field(
        default=True, description="Notifications enabled"
    )
    tags: Optional[List[str]] = Field(None, description="Maintenance tags")


class MaintenanceWindowResponse(BaseSchema):
    """Schema for maintenance window response."""

    id: str = Field(..., description="Maintenance window ID")
    tenant_id: str = Field(..., description="Tenant ID")
    name: str = Field(..., description="Maintenance window name")
    maintenance_type: str = Field(..., description="Maintenance type")
    start_time: datetime = Field(..., description="Start time")
    end_time: datetime = Field(..., description="End time")
    timezone: str = Field(..., description="Timezone")
    impact_level: str = Field(..., description="Impact level")
    approval_status: str = Field(..., description="Approval status")
    execution_status: str = Field(..., description="Execution status")
    description: str = Field(..., description="Maintenance description")
    notifications_enabled: bool = Field(..., description="Notifications enabled")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# Pagination schemas
class PaginatedResponse(BaseSchema):
    """Base paginated response schema."""

    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")


class PaginatedNetworkDeviceResponse(PaginatedResponse):
    """Paginated network device response."""

    items: List[NetworkDeviceResponse] = Field(..., description="Network devices")


class PaginatedNetworkInterfaceResponse(PaginatedResponse):
    """Paginated network interface response."""

    items: List[NetworkInterfaceResponse] = Field(..., description="Network interfaces")


class PaginatedNetworkLocationResponse(PaginatedResponse):
    """Paginated network location response."""

    items: List[NetworkLocationResponse] = Field(..., description="Network locations")


class PaginatedNetworkAlertResponse(PaginatedResponse):
    """Paginated network alert response."""

    items: List[NetworkAlertResponse] = Field(..., description="Network alerts")
