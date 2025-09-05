"""Service management models for ISP platform."""

from enum import Enum

from dotmac_isp.shared.database.base import BaseModel
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


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


class ServicePlan(BaseModel):
    """Service plan model for ISP service offerings."""

    __tablename__ = "service_plans"

    # Basic plan information
    plan_code = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    service_type = Column(String(50), nullable=False, index=True)

    # Pricing information
    monthly_price = Column(Numeric(10, 2), nullable=False)
    setup_fee = Column(Numeric(10, 2), default=0, nullable=False)
    cancellation_fee = Column(Numeric(10, 2), default=0, nullable=False)

    # Technical specifications
    download_speed = Column(Integer, nullable=True)
    upload_speed = Column(Integer, nullable=True)
    bandwidth_unit = Column(String(10), default="mbps", nullable=False)
    data_allowance = Column(Integer, nullable=True)  # GB per month, null = unlimited

    # Plan configuration
    features = Column(JSONB, nullable=True, default=dict)
    technical_specs = Column(JSONB, nullable=True, default=dict)

    # Plan status and visibility
    is_active = Column(Boolean, default=True, nullable=False)
    is_public = Column(Boolean, default=True, nullable=False)
    requires_approval = Column(Boolean, default=False, nullable=False)

    # Contract terms
    min_contract_months = Column(Integer, default=0, nullable=False)
    max_contract_months = Column(Integer, nullable=True)

    # Relationships
    service_instances = relationship("ServiceInstance", back_populates="service_plan")

    def __repr__(self):
        return f"<ServicePlan(code={self.plan_code}, name={self.name})>"


class ServiceInstance(BaseModel):
    """Service instance model for customer services."""

    __tablename__ = "service_instances"

    # Service identification
    service_number = Column(String(50), nullable=False, unique=True, index=True)

    # Relationships
    customer_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    service_plan_id = Column(
        UUID(as_uuid=True), ForeignKey("service_plans.id"), nullable=False
    )
    service_plan = relationship("ServicePlan", back_populates="service_instances")

    # Service status and lifecycle
    status = Column(String(20), default="pending", nullable=False, index=True)
    activation_date = Column(DateTime(timezone=True), nullable=True)
    suspension_date = Column(DateTime(timezone=True), nullable=True)
    cancellation_date = Column(DateTime(timezone=True), nullable=True)

    # Service location and technical details
    service_address = Column(String(500), nullable=True)
    service_coordinates = Column(String(50), nullable=True)
    assigned_ip = Column(String(45), nullable=True)  # IPv4 or IPv6
    assigned_vlan = Column(Integer, nullable=True)
    router_config = Column(JSONB, nullable=True, default=dict)

    # Contract and pricing
    contract_start_date = Column(Date, nullable=True)
    contract_end_date = Column(Date, nullable=True)
    monthly_price = Column(Numeric(10, 2), nullable=False)

    # Additional information
    notes = Column(Text, nullable=True)
    custom_config = Column(JSONB, nullable=True, default=dict)

    def __repr__(self):
        return f"<ServiceInstance(number={self.service_number}, status={self.status})>"


class ServiceProvisioning(BaseModel):
    """Service provisioning tracking model."""

    __tablename__ = "service_provisioning"

    # Service reference
    service_instance_id = Column(
        UUID(as_uuid=True), ForeignKey("service_instances.id"), nullable=False
    )
    service_instance = relationship("ServiceInstance")

    # Provisioning details
    provisioning_status = Column(
        String(20), default="pending", nullable=False, index=True
    )
    scheduled_date = Column(DateTime(timezone=True), nullable=True)
    started_date = Column(DateTime(timezone=True), nullable=True)
    completed_date = Column(DateTime(timezone=True), nullable=True)

    # Assignment and tracking
    assigned_technician_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    work_order_number = Column(String(50), nullable=True, index=True)

    # Provisioning details
    equipment_required = Column(JSONB, nullable=True, default=list)
    installation_notes = Column(Text, nullable=True)
    completion_notes = Column(Text, nullable=True)

    # Quality assurance
    tested = Column(Boolean, default=False, nullable=False)
    test_results = Column(JSONB, nullable=True, default=dict)
    customer_signature = Column(String(500), nullable=True)  # Base64 or path

    # Failure tracking
    failure_reason = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)

    def __repr__(self):
        return f"<ServiceProvisioning(service_id={self.service_instance_id}, status={self.provisioning_status})>"


class ServiceStatusHistory(BaseModel):
    """Service status change history."""

    __tablename__ = "service_status_history"

    # Service reference
    service_instance_id = Column(
        UUID(as_uuid=True), ForeignKey("service_instances.id"), nullable=False
    )
    service_instance = relationship("ServiceInstance")

    # Status change details
    old_status = Column(String(20), nullable=True)
    new_status = Column(String(20), nullable=False)
    change_reason = Column(String(500), nullable=True)
    changed_by_user_id = Column(UUID(as_uuid=True), nullable=True)

    # Effective dates
    effective_date = Column(DateTime(timezone=True), default=func.now(), nullable=False)

    # Additional context
    notes = Column(Text, nullable=True)
    change_metadata = Column(JSONB, nullable=True, default=dict)

    def __repr__(self):
        return f"<ServiceStatusHistory(service_id={self.service_instance_id}, {self.old_status} -> {self.new_status})>"


class ServiceUsageMetric(BaseModel):
    """Service usage tracking for billing and analytics."""

    __tablename__ = "service_usage_metrics"

    # Service reference
    service_instance_id = Column(
        UUID(as_uuid=True), ForeignKey("service_instances.id"), nullable=False
    )
    service_instance = relationship("ServiceInstance")

    # Usage period
    usage_date = Column(Date, nullable=False, index=True)
    usage_hour = Column(Integer, nullable=True)  # 0-23 for hourly metrics

    # Usage metrics
    data_downloaded_mb = Column(Numeric(15, 2), default=0, nullable=False)
    data_uploaded_mb = Column(Numeric(15, 2), default=0, nullable=False)
    peak_download_speed_mbps = Column(Numeric(10, 2), nullable=True)
    peak_upload_speed_mbps = Column(Numeric(10, 2), nullable=True)

    # Connection quality
    uptime_minutes = Column(Integer, default=0, nullable=False)
    downtime_minutes = Column(Integer, default=0, nullable=False)
    connection_drops = Column(Integer, default=0, nullable=False)

    # Additional metrics
    custom_metrics = Column(JSONB, nullable=True, default=dict)

    def __repr__(self):
        return f"<ServiceUsageMetric(service_id={self.service_instance_id}, date={self.usage_date})>"
