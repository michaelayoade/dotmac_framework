"""
Operations API Schemas

Pydantic schemas for operations automation API endpoints.
Follows existing DRY patterns and base schema inheritance.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from dotmac.core.schemas.base_schemas import (
    BaseCreateSchema,
    BaseResponseSchema,
    BaseUpdateSchema,
)


# Enums for operations
class NetworkHealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    OFFLINE = "offline"


class CustomerLifecycleStage(str, Enum):
    REGISTRATION = "registration"
    VERIFICATION = "verification"
    ONBOARDING = "onboarding"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CHURNING = "churning"
    INACTIVE = "inactive"
    DELETED = "deleted"


class MaintenanceType(str, Enum):
    DATABASE_CLEANUP = "database_cleanup"
    LOG_ROTATION = "log_rotation"
    CACHE_CLEANUP = "cache_cleanup"
    BACKUP_MANAGEMENT = "backup_management"
    SECURITY_UPDATES = "security_updates"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    DISK_CLEANUP = "disk_cleanup"
    SYSTEM_MONITORING = "system_monitoring"


class MaintenanceStatus(str, Enum):
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# Network Health Monitoring Schemas
class NetworkEndpointCreate(BaseCreateSchema):
    """Schema for creating network endpoint monitoring"""

    name: str = Field(..., description="Endpoint name")
    host: str = Field(..., description="Endpoint host")
    port: int = Field(..., ge=1, le=65535, description="Endpoint port")
    service_type: str = Field(..., description="Service type")
    tenant_id: Optional[UUID] = Field(None, description="Tenant ID")
    check_interval: int = Field(30, ge=5, le=3600, description="Check interval in seconds")
    timeout: int = Field(5, ge=1, le=60, description="Timeout in seconds")
    retry_count: int = Field(3, ge=1, le=10, description="Retry count")
    expected_response_time: float = Field(1.0, ge=0.1, le=30.0, description="Expected response time")


class NetworkEndpointUpdate(BaseUpdateSchema):
    """Schema for updating network endpoint monitoring"""

    name: Optional[str] = Field(None, description="Endpoint name")
    host: Optional[str] = Field(None, description="Endpoint host")
    port: Optional[int] = Field(None, ge=1, le=65535, description="Endpoint port")
    service_type: Optional[str] = Field(None, description="Service type")
    check_interval: Optional[int] = Field(None, ge=5, le=3600, description="Check interval in seconds")
    timeout: Optional[int] = Field(None, ge=1, le=60, description="Timeout in seconds")
    retry_count: Optional[int] = Field(None, ge=1, le=10, description="Retry count")
    expected_response_time: Optional[float] = Field(None, ge=0.1, le=30.0, description="Expected response time")


class NetworkEndpointResponse(BaseResponseSchema):
    """Schema for network endpoint response"""

    name: str
    host: str
    port: int
    service_type: str
    tenant_id: Optional[UUID]
    check_interval: int
    timeout: int
    retry_count: int
    expected_response_time: float
    last_check: Optional[datetime]
    last_status: Optional[NetworkHealthStatus]


class HealthCheckResult(BaseModel):
    """Health check result schema"""

    endpoint_id: UUID
    status: NetworkHealthStatus
    response_time: float
    message: str
    timestamp: datetime
    details: dict[str, Any]


class NetworkHealthSummary(BaseModel):
    """Network health summary schema"""

    overall_status: NetworkHealthStatus
    total_endpoints: int
    healthy_count: int
    degraded_count: int
    critical_count: int
    offline_count: int
    average_response_time: float
    timestamp: str
    details: list[dict[str, Any]]


# Customer Lifecycle Management Schemas
class CustomerRegistrationRequest(BaseCreateSchema):
    """Schema for customer registration request"""

    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: str = Field(..., description="Email address")
    first_name: str = Field(..., min_length=1, max_length=100, description="First name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Last name")
    user_type: str = Field(..., description="User type")
    tenant_id: Optional[UUID] = Field(None, description="Tenant ID")
    requires_approval: bool = Field(False, description="Requires approval")
    registration_source: str = Field("api", description="Registration source")
    referral_code: Optional[str] = Field(None, description="Referral code")
    terms_accepted: bool = Field(True, description="Terms accepted")
    privacy_policy_accepted: bool = Field(True, description="Privacy policy accepted")
    marketing_consent: bool = Field(False, description="Marketing consent")


class CustomerVerificationRequest(BaseModel):
    """Schema for customer verification request"""

    verification_token: str = Field(..., description="Verification token")
    verification_type: str = Field("email", description="Verification type")
    additional_data: Optional[dict[str, Any]] = Field(None, description="Additional verification data")


class CustomerLifecycleAction(BaseModel):
    """Schema for customer lifecycle action"""

    action_type: str = Field(..., description="Action type")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Action parameters")
    reason: Optional[str] = Field(None, description="Action reason")


class CustomerLifecycleResponse(BaseResponseSchema):
    """Schema for customer lifecycle response"""

    user_id: UUID
    status: str
    lifecycle_stage: CustomerLifecycleStage
    next_actions: list[dict[str, str]]
    timestamp: str


# Service Provisioning Schemas
class ServiceProvisioningRequest(BaseCreateSchema):
    """Schema for service provisioning request"""

    customer_id: UUID = Field(..., description="Customer ID")
    service_name: str = Field(..., description="Service name")
    custom_config: Optional[dict[str, Any]] = Field(None, description="Custom configuration")


class ServiceProvisioningResponse(BaseResponseSchema):
    """Schema for service provisioning response"""

    request_id: UUID
    customer_id: UUID
    service_name: str
    status: str
    message: str
    created_at: Optional[str] = None
    provisioned_at: Optional[str] = None


# Infrastructure Maintenance Schemas
class MaintenanceTaskCreate(BaseCreateSchema):
    """Schema for creating maintenance task"""

    task_name: str = Field(..., description="Task name")
    maintenance_type: MaintenanceType = Field(..., description="Maintenance type")
    schedule_cron: str = Field(..., description="Cron schedule")
    enabled: bool = Field(True, description="Task enabled")
    timeout_minutes: int = Field(60, ge=1, le=1440, description="Timeout in minutes")
    retry_count: int = Field(3, ge=1, le=10, description="Retry count")
    parameters: Optional[dict[str, Any]] = Field(None, description="Task parameters")


class MaintenanceTaskUpdate(BaseUpdateSchema):
    """Schema for updating maintenance task"""

    task_name: Optional[str] = Field(None, description="Task name")
    schedule_cron: Optional[str] = Field(None, description="Cron schedule")
    enabled: Optional[bool] = Field(None, description="Task enabled")
    timeout_minutes: Optional[int] = Field(None, ge=1, le=1440, description="Timeout in minutes")
    retry_count: Optional[int] = Field(None, ge=1, le=10, description="Retry count")
    parameters: Optional[dict[str, Any]] = Field(None, description="Task parameters")


class MaintenanceTaskResponse(BaseResponseSchema):
    """Schema for maintenance task response"""

    task_name: str
    maintenance_type: MaintenanceType
    schedule_cron: str
    enabled: bool
    timeout_minutes: int
    retry_count: int
    parameters: Optional[dict[str, Any]]
    last_run: Optional[datetime]
    last_status: Optional[MaintenanceStatus]
    next_run: Optional[datetime]


class MaintenanceResult(BaseModel):
    """Schema for maintenance result"""

    task_id: UUID
    task_name: str
    status: MaintenanceStatus
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    items_processed: int = 0
    items_cleaned: int = 0
    space_freed_mb: float = 0.0
    error_message: Optional[str] = None
    details: Optional[dict[str, Any]] = None


class MaintenanceExecutionRequest(BaseModel):
    """Schema for manual maintenance execution request"""

    maintenance_type: MaintenanceType = Field(..., description="Maintenance type")
    parameters: Optional[dict[str, Any]] = Field(None, description="Execution parameters")


# Operations Status Schemas
class OperationsStatus(BaseModel):
    """Schema for operations status"""

    scheduler_running: bool
    active_tasks: int
    recent_results: list[dict[str, Any]]
    maintenance_tasks: list[dict[str, Any]]
    timestamp: str


# Service Health Check Schemas
class ServiceHealthCheckRequest(BaseModel):
    """Schema for service health check request"""

    service_type: str = Field(..., description="Service type (database, redis, container)")
    connection_string: Optional[str] = Field(None, description="Connection string")
    container_id: Optional[str] = Field(None, description="Container ID")
    timeout: int = Field(5, ge=1, le=60, description="Timeout in seconds")


class ServiceHealthCheckResponse(BaseModel):
    """Schema for service health check response"""

    status: NetworkHealthStatus
    response_time: float
    message: str
    details: dict[str, Any]


# Endpoint Trends Schema
class EndpointTrendsResponse(BaseModel):
    """Schema for endpoint trends response"""

    endpoint_id: UUID
    endpoint_name: Optional[str]
    period_hours: int
    total_checks: int
    availability_percentage: float
    average_response_time: float
    status_distribution: dict[str, dict[str, Any]]
    recent_issues: list[dict[str, Any]]
