"""Network monitoring schemas for API requests and responses."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, IPvAnyAddress
from decimal import Decimal

from .models import (
    MonitoringStatus,
    AlertSeverity,
    AlertStatus,
    MetricType,
    DeviceStatus,
    ScheduleType,
)


# Base schemas
class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = {"from_attributes": True}


# Monitoring Profile schemas
class MonitoringProfileBase(BaseSchema):
    """Base monitoring profile schema."""

    profile_name: str = Field(
        ..., min_length=1, max_length=255, description="Profile name"
    )
    profile_type: str = Field(..., max_length=100, description="Profile type")
    description: Optional[str] = Field(None, description="Profile description")


class MonitoringProfileCreate(MonitoringProfileBase):
    """Schema for creating monitoring profiles."""

    # SNMP configuration
    snmp_version: str = Field(default="v2c", description="SNMP version")
    snmp_community: Optional[str] = Field(
        None, max_length=100, description="SNMP community string"
    )
    snmp_port: int = Field(default=161, ge=1, le=65535, description="SNMP port")
    snmp_timeout: int = Field(
        default=5, ge=1, le=60, description="SNMP timeout in seconds"
    )
    snmp_retries: int = Field(default=3, ge=1, le=10, description="SNMP retry count")

    # SNMPv3 configuration
    snmp_v3_username: Optional[str] = Field(
        None, max_length=100, description="SNMPv3 username"
    )
    snmp_v3_auth_protocol: Optional[str] = Field(
        None, description="SNMPv3 auth protocol"
    )
    snmp_v3_auth_key: Optional[str] = Field(None, description="SNMPv3 auth key")
    snmp_v3_priv_protocol: Optional[str] = Field(
        None, description="SNMPv3 privacy protocol"
    )
    snmp_v3_priv_key: Optional[str] = Field(None, description="SNMPv3 privacy key")

    # Monitoring configuration
    monitoring_interval: int = Field(
        default=300, ge=30, le=3600, description="Monitoring interval in seconds"
    )
    collection_timeout: int = Field(
        default=30, ge=5, le=300, description="Collection timeout in seconds"
    )

    # OID configuration
    oids_to_monitor: List[Dict[str, Any]] = Field(
        ..., description="List of OIDs to monitor"
    )
    custom_oids: Optional[List[Dict[str, Any]]] = Field(None, description="Custom OIDs")

    # Data retention
    data_retention_days: int = Field(
        default=30, ge=1, le=365, description="Data retention period"
    )
    aggregation_rules: Optional[Dict[str, Any]] = Field(
        None, description="Data aggregation rules"
    )

    # Device targeting
    device_types: Optional[List[str]] = Field(
        None, description="Applicable device types"
    )
    device_vendors: Optional[List[str]] = Field(None, description="Applicable vendors")
    device_models: Optional[List[str]] = Field(None, description="Applicable models")

    # Metadata
    tags: Optional[List[str]] = Field(None, description="Profile tags")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="Custom fields")


class MonitoringProfileUpdate(BaseSchema):
    """Schema for updating monitoring profiles."""

    profile_name: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Profile name"
    )
    description: Optional[str] = Field(None, description="Profile description")
    monitoring_interval: Optional[int] = Field(
        None, ge=30, le=3600, description="Monitoring interval"
    )
    collection_timeout: Optional[int] = Field(
        None, ge=5, le=300, description="Collection timeout"
    )
    data_retention_days: Optional[int] = Field(
        None, ge=1, le=365, description="Data retention period"
    )
    tags: Optional[List[str]] = Field(None, description="Profile tags")


class MonitoringProfileResponse(MonitoringProfileBase):
    """Schema for monitoring profile responses."""

    id: str = Field(..., description="Profile ID")
    tenant_id: str = Field(..., description="Tenant ID")
    status: str = Field(..., description="Profile status")
    snmp_version: str = Field(..., description="SNMP version")
    snmp_port: int = Field(..., description="SNMP port")
    monitoring_interval: int = Field(..., description="Monitoring interval in seconds")
    data_retention_days: int = Field(..., description="Data retention period")
    device_count: int = Field(
        0, ge=0, description="Number of devices using this profile"
    )
    alert_rule_count: int = Field(0, ge=0, description="Number of alert rules")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# SNMP Device schemas
class SnmpDeviceBase(BaseSchema):
    """Base SNMP device schema."""

    device_name: str = Field(
        ..., min_length=1, max_length=255, description="Device name"
    )
    device_ip: IPvAnyAddress = Field(..., description="Device IP address")
    device_type: Optional[str] = Field(None, max_length=100, description="Device type")
    device_vendor: Optional[str] = Field(
        None, max_length=100, description="Device vendor"
    )
    device_model: Optional[str] = Field(
        None, max_length=100, description="Device model"
    )


class SnmpDeviceCreate(SnmpDeviceBase):
    """Schema for creating SNMP devices."""

    monitoring_profile_id: str = Field(..., description="Monitoring profile ID")
    network_device_id: Optional[str] = Field(None, description="Network device ID")

    # SNMP overrides
    snmp_version_override: Optional[str] = Field(
        None, description="SNMP version override"
    )
    snmp_community_override: Optional[str] = Field(
        None, description="SNMP community override"
    )
    snmp_port_override: Optional[int] = Field(
        None, ge=1, le=65535, description="SNMP port override"
    )

    # Monitoring settings
    monitoring_enabled: bool = Field(default=True, description="Enable monitoring")

    # Device information
    sys_description: Optional[str] = Field(None, description="System description")
    sys_location: Optional[str] = Field(
        None, max_length=255, description="System location"
    )
    sys_contact: Optional[str] = Field(
        None, max_length=255, description="System contact"
    )

    # Metadata
    tags: Optional[List[str]] = Field(None, description="Device tags")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="Custom fields")


class SnmpDeviceUpdate(BaseSchema):
    """Schema for updating SNMP devices."""

    device_name: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Device name"
    )
    monitoring_enabled: Optional[bool] = Field(None, description="Enable monitoring")
    snmp_community_override: Optional[str] = Field(
        None, description="SNMP community override"
    )
    sys_location: Optional[str] = Field(None, description="System location")
    sys_contact: Optional[str] = Field(None, description="System contact")
    tags: Optional[List[str]] = Field(None, description="Device tags")


class SnmpDeviceResponse(SnmpDeviceBase):
    """Schema for SNMP device responses."""

    id: str = Field(..., description="Device ID")
    tenant_id: str = Field(..., description="Tenant ID")
    monitoring_profile_id: str = Field(..., description="Monitoring profile ID")
    network_device_id: Optional[str] = Field(None, description="Network device ID")

    # Monitoring status
    monitoring_enabled: bool = Field(..., description="Monitoring enabled")
    monitoring_status: MonitoringStatus = Field(..., description="Monitoring status")
    last_monitored: Optional[datetime] = Field(
        None, description="Last monitoring timestamp"
    )

    # Device availability
    availability_status: DeviceStatus = Field(
        ..., description="Device availability status"
    )
    last_seen: Optional[datetime] = Field(None, description="Last seen timestamp")
    response_time_ms: Optional[float] = Field(
        None, description="Response time in milliseconds"
    )
    uptime_seconds: Optional[int] = Field(None, description="Device uptime in seconds")

    # Error tracking
    consecutive_failures: int = Field(..., description="Consecutive failure count")
    last_error: Optional[str] = Field(None, description="Last error message")
    last_error_time: Optional[datetime] = Field(
        None, description="Last error timestamp"
    )

    # Performance metrics
    cpu_usage_percent: Optional[float] = Field(None, description="CPU usage percentage")
    memory_usage_percent: Optional[float] = Field(
        None, description="Memory usage percentage"
    )
    temperature_celsius: Optional[float] = Field(
        None, description="Temperature in Celsius"
    )

    # System information
    sys_description: Optional[str] = Field(None, description="System description")
    sys_location: Optional[str] = Field(None, description="System location")
    sys_contact: Optional[str] = Field(None, description="System contact")

    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# SNMP Metric schemas
class SnmpMetricResponse(BaseSchema):
    """Schema for SNMP metric responses."""

    id: str = Field(..., description="Metric ID")
    device_id: str = Field(..., description="Device ID")
    metric_name: str = Field(..., description="Metric name")
    metric_oid: str = Field(..., description="Metric OID")
    metric_type: MetricType = Field(..., description="Metric type")
    metric_instance: Optional[str] = Field(None, description="Metric instance")
    value: Decimal = Field(..., description="Metric value")
    raw_value: Optional[str] = Field(None, description="Raw SNMP value")
    unit: Optional[str] = Field(None, description="Metric unit")
    timestamp: datetime = Field(..., description="Metric timestamp")
    collection_time_ms: Optional[float] = Field(
        None, description="Collection time in milliseconds"
    )
    labels: Optional[Dict[str, str]] = Field(None, description="Metric labels")


# Network Alert schemas
class NetworkAlertCreate(BaseSchema):
    """Schema for creating network alerts."""

    alert_name: str = Field(..., min_length=1, max_length=255, description="Alert name")
    alert_type: str = Field(..., max_length=100, description="Alert type")
    title: str = Field(..., min_length=1, max_length=255, description="Alert title")
    description: str = Field(..., min_length=1, description="Alert description")
    severity: AlertSeverity = Field(..., description="Alert severity")
    device_id: Optional[str] = Field(None, description="Device ID")
    alert_rule_id: Optional[str] = Field(None, description="Alert rule ID")

    # Alert context
    metric_name: Optional[str] = Field(None, description="Metric name")
    metric_value: Optional[Decimal] = Field(None, description="Metric value")
    threshold_value: Optional[Decimal] = Field(None, description="Threshold value")
    threshold_operator: Optional[str] = Field(None, description="Threshold operator")

    # Additional data
    alert_data: Optional[Dict[str, Any]] = Field(
        None, description="Additional alert data"
    )
    tags: Optional[List[str]] = Field(None, description="Alert tags")


class NetworkAlertResponse(BaseSchema):
    """Schema for network alert responses."""

    id: str = Field(..., description="Alert ID")
    tenant_id: str = Field(..., description="Tenant ID")
    device_id: Optional[str] = Field(None, description="Device ID")
    alert_rule_id: Optional[str] = Field(None, description="Alert rule ID")
    alert_id: str = Field(..., description="Alert identifier")
    alert_name: str = Field(..., description="Alert name")
    alert_type: str = Field(..., description="Alert type")
    title: str = Field(..., description="Alert title")
    description: str = Field(..., description="Alert description")
    severity: AlertSeverity = Field(..., description="Alert severity")
    status: AlertStatus = Field(..., description="Alert status")

    # Alert context
    metric_name: Optional[str] = Field(None, description="Metric name")
    metric_value: Optional[Decimal] = Field(None, description="Metric value")
    threshold_value: Optional[Decimal] = Field(None, description="Threshold value")
    threshold_operator: Optional[str] = Field(None, description="Threshold operator")

    # Lifecycle timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    acknowledged_at: Optional[datetime] = Field(
        None, description="Acknowledgment timestamp"
    )
    resolved_at: Optional[datetime] = Field(None, description="Resolution timestamp")

    # Assignment
    assigned_to: Optional[str] = Field(None, description="Assigned user ID")
    acknowledged_by: Optional[str] = Field(None, description="Acknowledged by user ID")
    resolved_by: Optional[str] = Field(None, description="Resolved by user ID")

    # Notification tracking
    escalation_level: int = Field(..., description="Escalation level")


# Alert Rule schemas
class AlertRuleBase(BaseSchema):
    """Base alert rule schema."""

    rule_name: str = Field(..., min_length=1, max_length=255, description="Rule name")
    rule_type: str = Field(..., max_length=100, description="Rule type")
    metric_name: str = Field(..., max_length=255, description="Metric name")
    condition_operator: str = Field(..., description="Condition operator")
    threshold_value: Decimal = Field(..., description="Threshold value")
    alert_severity: AlertSeverity = Field(..., description="Alert severity")
    description: Optional[str] = Field(None, description="Rule description")


class AlertRuleCreate(AlertRuleBase):
    """Schema for creating alert rules."""

    monitoring_profile_id: str = Field(..., description="Monitoring profile ID")
    threshold_unit: Optional[str] = Field(None, description="Threshold unit")

    # Time-based conditions
    evaluation_window: int = Field(
        default=300, ge=60, le=3600, description="Evaluation window in seconds"
    )
    evaluation_frequency: int = Field(
        default=60, ge=30, le=600, description="Evaluation frequency in seconds"
    )
    consecutive_violations: int = Field(
        default=1, ge=1, le=10, description="Consecutive violations required"
    )

    # Alert configuration
    alert_template: Optional[str] = Field(None, description="Alert message template")

    # Notification settings
    notification_channels: Optional[List[str]] = Field(
        None, description="Notification channels"
    )
    notification_cooldown: int = Field(
        default=3600, ge=300, le=86400, description="Notification cooldown in seconds"
    )
    escalation_rules: Optional[Dict[str, Any]] = Field(
        None, description="Escalation configuration"
    )

    # Rule application
    device_filters: Optional[Dict[str, Any]] = Field(
        None, description="Device selection criteria"
    )
    time_restrictions: Optional[Dict[str, Any]] = Field(
        None, description="Time-based restrictions"
    )

    # Metadata
    enabled: bool = Field(default=True, description="Rule enabled")
    tags: Optional[List[str]] = Field(None, description="Rule tags")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="Custom fields")


class AlertRuleUpdate(BaseSchema):
    """Schema for updating alert rules."""

    rule_name: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Rule name"
    )
    threshold_value: Optional[Decimal] = Field(None, description="Threshold value")
    alert_severity: Optional[AlertSeverity] = Field(None, description="Alert severity")
    enabled: Optional[bool] = Field(None, description="Rule enabled")
    evaluation_window: Optional[int] = Field(
        None, ge=60, le=3600, description="Evaluation window"
    )
    consecutive_violations: Optional[int] = Field(
        None, ge=1, le=10, description="Consecutive violations"
    )
    notification_cooldown: Optional[int] = Field(
        None, ge=300, le=86400, description="Notification cooldown"
    )
    description: Optional[str] = Field(None, description="Rule description")


class AlertRuleResponse(AlertRuleBase):
    """Schema for alert rule responses."""

    id: str = Field(..., description="Rule ID")
    tenant_id: str = Field(..., description="Tenant ID")
    monitoring_profile_id: str = Field(..., description="Monitoring profile ID")
    threshold_unit: Optional[str] = Field(None, description="Threshold unit")
    evaluation_window: int = Field(..., description="Evaluation window in seconds")
    evaluation_frequency: int = Field(
        ..., description="Evaluation frequency in seconds"
    )
    consecutive_violations: int = Field(
        ..., description="Consecutive violations required"
    )
    notification_cooldown: int = Field(
        ..., description="Notification cooldown in seconds"
    )

    # Rule state
    enabled: bool = Field(..., description="Rule enabled")
    last_evaluation: Optional[datetime] = Field(
        None, description="Last evaluation timestamp"
    )
    evaluation_count: int = Field(..., description="Evaluation count")
    alert_count: int = Field(..., description="Alert count")

    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# Device Availability schemas
class DeviceAvailabilityResponse(BaseSchema):
    """Schema for device availability responses."""

    id: str = Field(..., description="Availability record ID")
    device_id: str = Field(..., description="Device ID")
    timestamp: datetime = Field(..., description="Check timestamp")
    status: DeviceStatus = Field(..., description="Device status")
    response_time_ms: Optional[float] = Field(
        None, description="Response time in milliseconds"
    )
    check_method: str = Field(..., description="Check method")
    check_details: Optional[Dict[str, Any]] = Field(None, description="Check details")
    error_message: Optional[str] = Field(None, description="Error message")
    error_code: Optional[str] = Field(None, description="Error code")


# Dashboard and Analytics schemas
class MonitoringDashboard(BaseSchema):
    """Monitoring dashboard metrics."""

    total_devices: int = Field(..., ge=0, description="Total monitored devices")
    active_devices: int = Field(..., ge=0, description="Active devices")
    failed_devices: int = Field(..., ge=0, description="Failed devices")
    warning_devices: int = Field(..., ge=0, description="Warning devices")
    total_profiles: int = Field(..., ge=0, description="Total monitoring profiles")
    total_alerts: int = Field(..., ge=0, description="Total active alerts")
    critical_alerts: int = Field(..., ge=0, description="Critical alerts")
    high_alerts: int = Field(..., ge=0, description="High severity alerts")
    avg_response_time: float = Field(..., ge=0, description="Average response time")
    network_availability: float = Field(
        ..., ge=0, le=100, description="Network availability percentage"
    )


class DeviceHealthSummary(BaseSchema):
    """Device health summary."""

    device_id: str = Field(..., description="Device ID")
    device_name: str = Field(..., description="Device name")
    device_ip: str = Field(..., description="Device IP")
    availability_status: DeviceStatus = Field(..., description="Availability status")
    monitoring_status: MonitoringStatus = Field(..., description="Monitoring status")
    cpu_usage: Optional[float] = Field(None, description="CPU usage percentage")
    memory_usage: Optional[float] = Field(None, description="Memory usage percentage")
    temperature: Optional[float] = Field(None, description="Temperature")
    uptime_seconds: Optional[int] = Field(None, description="Uptime in seconds")
    response_time_ms: Optional[float] = Field(None, description="Response time")
    alert_count: int = Field(..., ge=0, description="Active alert count")
    last_seen: Optional[datetime] = Field(None, description="Last seen timestamp")


class MetricsQuery(BaseSchema):
    """Metrics query schema."""

    device_ids: Optional[List[str]] = Field(None, description="Device IDs to query")
    metric_names: Optional[List[str]] = Field(
        None, description="Metric names to retrieve"
    )
    start_time: datetime = Field(..., description="Query start time")
    end_time: datetime = Field(..., description="Query end time")
    aggregation: Optional[str] = Field("raw", description="Aggregation method")
    interval: Optional[int] = Field(None, description="Aggregation interval in seconds")


class BulkDeviceOperation(BaseSchema):
    """Bulk device operation schema."""

    device_ids: List[str] = Field(..., min_items=1, description="Device IDs")
    operation: str = Field(
        ...,
        pattern="^(enable|disable|restart_monitoring|reset_counters)$",
        description="Operation",
    )
    parameters: Optional[Dict[str, Any]] = Field(
        None, description="Operation parameters"
    )


class BulkOperationResponse(BaseSchema):
    """Bulk operation response."""

    operation_id: str = Field(..., description="Operation ID")
    total_devices: int = Field(..., ge=0, description="Total devices")
    successful: int = Field(..., ge=0, description="Successful operations")
    failed: int = Field(..., ge=0, description="Failed operations")
    results: List[Dict[str, Any]] = Field(..., description="Operation results")


# Re-export commonly used schemas
__all__ = [
    # Base
    "BaseSchema",
    # Monitoring Profile schemas
    "MonitoringProfileBase",
    "MonitoringProfileCreate",
    "MonitoringProfileUpdate",
    "MonitoringProfileResponse",
    # SNMP Device schemas
    "SnmpDeviceBase",
    "SnmpDeviceCreate",
    "SnmpDeviceUpdate",
    "SnmpDeviceResponse",
    # Metric schemas
    "SnmpMetricResponse",
    "MetricsQuery",
    # Alert schemas
    "NetworkAlertCreate",
    "NetworkAlertResponse",
    "AlertRuleBase",
    "AlertRuleCreate",
    "AlertRuleUpdate",
    "AlertRuleResponse",
    # Availability schemas
    "DeviceAvailabilityResponse",
    # Dashboard schemas
    "MonitoringDashboard",
    "DeviceHealthSummary",
    # Bulk operations
    "BulkDeviceOperation",
    "BulkOperationResponse",
    # Enums
    "MonitoringStatus",
    "AlertSeverity",
    "AlertStatus",
    "MetricType",
    "DeviceStatus",
    "ScheduleType",
]
