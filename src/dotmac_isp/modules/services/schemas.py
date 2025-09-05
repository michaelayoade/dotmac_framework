"""Services schemas for API requests and responses."""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from dotmac_isp.shared.schemas import TenantModelSchema
from pydantic import BaseModel, Field


class ServiceType(str, Enum):
    """Service type enumeration."""

    INTERNET = "internet"
    PHONE = "phone"
    TV = "tv"
    BUNDLE = "bundle"
    HOSTING = "hosting"
    CLOUD = "cloud"
    MANAGED_SERVICES = "managed_services"


class ServiceStatus(str, Enum):
    """Service status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    MAINTENANCE = "maintenance"


class ProvisioningStatus(str, Enum):
    """Provisioning status enumeration."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BandwidthUnit(str, Enum):
    """Bandwidth unit enumeration."""

    KBPS = "kbps"
    MBPS = "mbps"
    GBPS = "gbps"


# Service Plan Schemas
class ServicePlanBase(BaseModel):
    """Base service plan schema."""

    plan_code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    service_type: ServiceType
    monthly_price: Decimal = Field(..., gt=0, decimal_places=2)
    setup_fee: Decimal = Field(0, ge=0, decimal_places=2)
    cancellation_fee: Decimal = Field(0, ge=0, decimal_places=2)
    download_speed: Optional[int] = Field(None, gt=0)
    upload_speed: Optional[int] = Field(None, gt=0)
    bandwidth_unit: BandwidthUnit = BandwidthUnit.MBPS
    data_allowance: Optional[int] = Field(None, gt=0)
    features: dict[str, Any] = Field(default_factory=dict)
    technical_specs: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    is_public: bool = True
    requires_approval: bool = False
    min_contract_months: int = Field(0, ge=0)
    max_contract_months: Optional[int] = Field(None, gt=0)


class ServicePlanCreate(ServicePlanBase):
    """Schema for creating service plans."""

    pass


class ServicePlanUpdate(BaseModel):
    """Schema for updating service plans."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    monthly_price: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    setup_fee: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    cancellation_fee: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    download_speed: Optional[int] = Field(None, gt=0)
    upload_speed: Optional[int] = Field(None, gt=0)
    data_allowance: Optional[int] = Field(None, gt=0)
    features: Optional[dict[str, Any]] = None
    technical_specs: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None
    requires_approval: Optional[bool] = None
    min_contract_months: Optional[int] = Field(None, ge=0)
    max_contract_months: Optional[int] = Field(None, gt=0)


class ServicePlanResponse(TenantModelSchema, ServicePlanBase):
    """Schema for service plan responses."""

    pass


# Service Instance Schemas
class ServiceInstanceBase(BaseModel):
    """Base service instance schema."""

    service_number: str = Field(..., min_length=1, max_length=50)
    customer_id: UUID
    service_plan_id: UUID
    status: ServiceStatus = ServiceStatus.PENDING
    activation_date: Optional[datetime] = None
    suspension_date: Optional[datetime] = None
    cancellation_date: Optional[datetime] = None
    service_address: Optional[str] = Field(None, max_length=500)
    service_coordinates: Optional[str] = Field(None, max_length=50)
    assigned_ip: Optional[str] = Field(None, max_length=45)
    assigned_vlan: Optional[int] = Field(None, gt=0)
    router_config: dict[str, Any] = Field(default_factory=dict)
    contract_start_date: Optional[date] = None
    contract_end_date: Optional[date] = None
    monthly_price: Decimal = Field(..., gt=0, decimal_places=2)
    notes: Optional[str] = Field(None, max_length=1000)
    custom_config: dict[str, Any] = Field(default_factory=dict)


class ServiceInstanceCreate(ServiceInstanceBase):
    """Schema for creating service instances."""

    pass


class ServiceInstanceUpdate(BaseModel):
    """Schema for updating service instances."""

    status: Optional[ServiceStatus] = None
    service_address: Optional[str] = Field(None, max_length=500)
    service_coordinates: Optional[str] = Field(None, max_length=50)
    assigned_ip: Optional[str] = Field(None, max_length=45)
    assigned_vlan: Optional[int] = Field(None, gt=0)
    router_config: Optional[dict[str, Any]] = None
    monthly_price: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    notes: Optional[str] = Field(None, max_length=1000)
    custom_config: Optional[dict[str, Any]] = None


class ServiceStatusUpdate(BaseModel):
    """Schema for updating service status."""

    status: ServiceStatus
    reason: Optional[str] = Field(None, max_length=500)
    effective_date: Optional[datetime] = None
    notify_customer: bool = True
    internal_notes: Optional[str] = Field(None, max_length=1000)


class ServiceInstanceResponse(TenantModelSchema, ServiceInstanceBase):
    """Schema for service instance responses."""

    pass


# Provisioning Task Schemas
class ProvisioningTaskBase(BaseModel):
    """Base provisioning task schema."""

    service_instance_id: UUID
    task_type: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=1000)
    status: ProvisioningStatus = ProvisioningStatus.PENDING
    scheduled_date: Optional[datetime] = None
    assigned_technician_id: Optional[UUID] = None
    task_data: dict[str, Any] = Field(default_factory=dict)


class ProvisioningTaskCreate(ProvisioningTaskBase):
    """Schema for creating provisioning tasks."""

    pass


class ProvisioningTaskUpdate(BaseModel):
    """Schema for updating provisioning tasks."""

    status: Optional[ProvisioningStatus] = None
    scheduled_date: Optional[datetime] = None
    assigned_technician_id: Optional[UUID] = None
    task_data: Optional[dict[str, Any]] = None
    result_data: Optional[dict[str, Any]] = None
    error_message: Optional[str] = Field(None, max_length=1000)


class ProvisioningTaskStatusUpdate(BaseModel):
    """Schema for updating provisioning task status."""

    status: ProvisioningStatus
    result_data: Optional[dict[str, Any]] = Field(default_factory=dict)
    error_message: Optional[str] = Field(None, max_length=1000)
    completion_notes: Optional[str] = Field(None, max_length=1000)


class ProvisioningTaskResponse(TenantModelSchema, ProvisioningTaskBase):
    """Schema for provisioning task responses."""

    started_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    result_data: dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None


# Service Add-on Schemas
class ServiceAddonBase(BaseModel):
    """Base service add-on schema."""

    addon_code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    monthly_price: Decimal = Field(..., gt=0, decimal_places=2)
    setup_fee: Decimal = Field(0, ge=0, decimal_places=2)
    is_active: bool = True


class ServiceAddonCreate(ServiceAddonBase):
    """Schema for creating service add-ons."""

    pass


class ServiceAddonResponse(TenantModelSchema, ServiceAddonBase):
    """Schema for service add-on responses."""

    pass


# Service Usage Schemas
class ServiceUsageBase(BaseModel):
    """Base service usage schema."""

    service_instance_id: UUID
    usage_date: date
    usage_period: str = Field("daily", pattern="^(daily|weekly|monthly)$")
    data_downloaded: Decimal = Field(0, ge=0, decimal_places=2)
    data_uploaded: Decimal = Field(0, ge=0, decimal_places=2)
    total_data: Decimal = Field(0, ge=0, decimal_places=2)
    avg_download_speed: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    avg_upload_speed: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    peak_download_speed: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    peak_upload_speed: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    uptime_percentage: Optional[Decimal] = Field(None, ge=0, le=100, decimal_places=2)
    downtime_minutes: Optional[int] = Field(None, ge=0)
    additional_metrics: dict[str, Any] = Field(default_factory=dict)


class ServiceUsageCreate(ServiceUsageBase):
    """Schema for creating service usage records."""

    pass


class ServiceUsageResponse(TenantModelSchema, ServiceUsageBase):
    """Schema for service usage responses."""

    pass


# Service Activation Request
class ServiceActivationRequest(BaseModel):
    """Schema for service activation requests."""

    customer_id: UUID
    service_plan_id: UUID
    service_address: str = Field(..., min_length=1, max_length=500)
    service_coordinates: Optional[str] = Field(None, max_length=50)
    contract_months: Optional[int] = Field(None, gt=0)
    requested_addons: list[UUID] = Field(default_factory=list)
    installation_notes: Optional[str] = Field(None, max_length=1000)
    preferred_installation_date: Optional[datetime] = None


class ServiceActivationResponse(BaseModel):
    """Schema for service activation responses."""

    service_instance: ServiceInstanceResponse
    provisioning_task: ProvisioningTaskResponse
    estimated_activation: Optional[datetime] = None
    total_setup_cost: Decimal
    monthly_recurring_cost: Decimal


# Service Modification Request
class ServiceModificationRequest(BaseModel):
    """Schema for service modification requests."""

    new_service_plan_id: Optional[UUID] = None
    add_addons: list[UUID] = Field(default_factory=list)
    remove_addons: list[UUID] = Field(default_factory=list)
    change_address: Optional[str] = Field(None, max_length=500)
    modification_notes: Optional[str] = Field(None, max_length=1000)
    effective_date: Optional[datetime] = None


class ServiceProvisioningRequest(BaseModel):
    """Service provisioning request schema."""

    customer_id: UUID
    service_plan_id: UUID
    service_address: str = Field(..., max_length=500)
    installation_date: Optional[date] = None
    service_addons: list[UUID] = Field(default_factory=list)
    custom_configuration: Optional[dict[str, Any]] = Field(default_factory=dict)
    billing_start_date: Optional[date] = None
    provisioning_notes: Optional[str] = Field(None, max_length=1000)
    priority: str = Field("normal", pattern="^(low|normal|high|urgent)$")


# Dashboard and Analytics Schemas
class ServiceDashboard(BaseModel):
    """Service dashboard metrics."""

    total_services: int = Field(..., ge=0)
    active_services: int = Field(..., ge=0)
    pending_activations: int = Field(..., ge=0)
    suspended_services: int = Field(..., ge=0)
    cancelled_services: int = Field(..., ge=0)
    monthly_revenue: Decimal = Field(..., ge=0, decimal_places=2)
    avg_service_value: Decimal = Field(..., ge=0, decimal_places=2)
    churn_rate: Decimal = Field(..., ge=0, le=100, decimal_places=2)
    most_popular_plans: list[dict[str, Any]] = Field(default_factory=list)


class ServicePerformanceMetrics(BaseModel):
    """Service performance metrics."""

    service_instance_id: UUID
    avg_uptime: Decimal = Field(..., ge=0, le=100, decimal_places=2)
    avg_download_speed: Decimal = Field(..., ge=0, decimal_places=2)
    avg_upload_speed: Decimal = Field(..., ge=0, decimal_places=2)
    total_data_usage: Decimal = Field(..., ge=0, decimal_places=2)
    recent_alerts: int = Field(..., ge=0)
    last_outage: Optional[datetime] = None
    customer_satisfaction: Optional[Decimal] = Field(None, ge=0, le=10, decimal_places=1)


class BulkServiceOperation(BaseModel):
    """Schema for bulk service operations."""

    service_instance_ids: list[UUID] = Field(..., min_length=1)
    operation: str = Field(..., pattern="^(suspend|reactivate|cancel|maintenance)$")
    reason: str = Field(..., min_length=1, max_length=500)
    effective_date: Optional[datetime] = None
    notify_customers: bool = True


class BulkServiceOperationResponse(BaseModel):
    """Schema for bulk service operation responses."""

    total_requested: int
    successful: int
    failed: int
    results: list[dict[str, Any]]
    operation_id: UUID
