"""Service models - Service catalog, instances, and provisioning."""

from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import (
    Column,
    String,
    Text,
    ForeignKey,
    DateTime,
    Numeric,
    Boolean,
    Enum,
    Integer,
    Date,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import enum

from dotmac_isp.shared.database.base import TenantModel


class ServiceType(enum.Enum):
    """Service type enumeration."""

    INTERNET = "internet"
    PHONE = "phone"
    TV = "tv"
    BUNDLE = "bundle"
    HOSTING = "hosting"
    CLOUD = "cloud"
    MANAGED_SERVICES = "managed_services"


class ServiceStatus(enum.Enum):
    """Service status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    MAINTENANCE = "maintenance"


class ProvisioningStatus(enum.Enum):
    """Provisioning status enumeration."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BandwidthUnit(enum.Enum):
    """Bandwidth unit enumeration."""

    KBPS = "kbps"
    MBPS = "mbps"
    GBPS = "gbps"


class ServicePlan(TenantModel):
    """Service plan model for ISP service offerings."""

    __tablename__ = "service_plans"

    # Plan identification
    plan_code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    service_type = Column(Enum(ServiceType), nullable=False)

    # Pricing
    monthly_price = Column(Numeric(10, 2), nullable=False)
    setup_fee = Column(Numeric(10, 2), nullable=False, default=0)
    cancellation_fee = Column(Numeric(10, 2), nullable=False, default=0)

    # Technical specifications
    download_speed = Column(Integer, nullable=True)  # in Mbps
    upload_speed = Column(Integer, nullable=True)  # in Mbps
    bandwidth_unit = Column(
        Enum(BandwidthUnit), default=BandwidthUnit.MBPS, nullable=False
    )
    data_allowance = Column(Integer, nullable=True)  # in GB, NULL for unlimited

    # Service features (stored as JSON)
    features = Column(JSONB, nullable=True)  # e.g., {"static_ip": true, "vpn": false}
    technical_specs = Column(
        JSONB, nullable=True
    )  # Additional technical specifications

    # Availability
    is_active = Column(Boolean, default=True, nullable=False)
    is_public = Column(
        Boolean, default=True, nullable=False
    )  # Available for public purchase
    requires_approval = Column(Boolean, default=False, nullable=False)

    # Contract terms
    min_contract_months = Column(Integer, default=0, nullable=False)
    max_contract_months = Column(Integer, nullable=True)

    # Relationships
    service_instances = relationship("ServiceInstance", back_populates="service_plan")
    add_ons = relationship(
        "ServiceAddon",
        secondary="service_plan_addons",
        back_populates="compatible_plans",
    )


class ServiceAddon(TenantModel):
    """Service add-on model for additional features."""

    __tablename__ = "service_addons"

    # Add-on identification
    addon_code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Pricing
    monthly_price = Column(Numeric(10, 2), nullable=False)
    setup_fee = Column(Numeric(10, 2), nullable=False, default=0)

    # Availability
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    compatible_plans = relationship(
        "ServicePlan", secondary="service_plan_addons", back_populates="add_ons"
    )


# Association table for service plan and add-on compatibility
from sqlalchemy import Table

service_plan_addons = Table(
    "service_plan_addons",
    TenantModel.metadata,
    Column(
        "service_plan_id",
        UUID(as_uuid=True),
        ForeignKey("service_plans.id"),
        primary_key=True,
    ),
    Column(
        "service_addon_id",
        UUID(as_uuid=True),
        ForeignKey("service_addons.id"),
        primary_key=True,
    ),
)


class ServiceInstance(TenantModel):
    """Service instance model for active customer services."""

    __tablename__ = "service_instances"

    # Service identification
    service_number = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    service_plan_id = Column(
        UUID(as_uuid=True), ForeignKey("service_plans.id"), nullable=False
    )

    # Service details
    status = Column(Enum(ServiceStatus), default=ServiceStatus.PENDING, nullable=False)
    activation_date = Column(DateTime(timezone=True), nullable=True)
    suspension_date = Column(DateTime(timezone=True), nullable=True)
    cancellation_date = Column(DateTime(timezone=True), nullable=True)

    # Service address (installation location)
    service_address = Column(Text, nullable=True)
    service_coordinates = Column(String(50), nullable=True)  # lat,lng

    # Technical configuration
    assigned_ip = Column(String(45), nullable=True)  # IPv4 or IPv6
    assigned_vlan = Column(Integer, nullable=True)
    router_config = Column(JSONB, nullable=True)

    # Contract information
    contract_start_date = Column(Date, nullable=True)
    contract_end_date = Column(Date, nullable=True)
    monthly_price = Column(Numeric(10, 2), nullable=False)  # Can differ from plan price

    # Notes and custom configuration
    notes = Column(Text, nullable=True)
    custom_config = Column(JSONB, nullable=True)

    # Relationships
    customer = relationship("Customer", back_populates="services")
    service_plan = relationship("ServicePlan", back_populates="service_instances")
    provisioning_tasks = relationship(
        "ProvisioningTask", back_populates="service_instance"
    )
    active_addons = relationship(
        "ServiceInstanceAddon", back_populates="service_instance"
    )


class ServiceInstanceAddon(TenantModel):
    """Active add-ons for service instances."""

    __tablename__ = "service_instance_addons"

    service_instance_id = Column(
        UUID(as_uuid=True), ForeignKey("service_instances.id"), nullable=False
    )
    service_addon_id = Column(
        UUID(as_uuid=True), ForeignKey("service_addons.id"), nullable=False
    )

    # Add-on details
    activation_date = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    deactivation_date = Column(DateTime(timezone=True), nullable=True)
    monthly_price = Column(
        Numeric(10, 2), nullable=False
    )  # Can differ from addon price
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    service_instance = relationship("ServiceInstance", back_populates="active_addons")
    service_addon = relationship("ServiceAddon")


class ProvisioningTask(TenantModel):
    """Provisioning task model for service activation."""

    __tablename__ = "provisioning_tasks"

    service_instance_id = Column(
        UUID(as_uuid=True), ForeignKey("service_instances.id"), nullable=False
    )

    # Task details
    task_type = Column(
        String(100), nullable=False
    )  # e.g., 'activate', 'suspend', 'modify'
    description = Column(Text, nullable=False)
    status = Column(
        Enum(ProvisioningStatus), default=ProvisioningStatus.PENDING, nullable=False
    )

    # Scheduling
    scheduled_date = Column(DateTime(timezone=True), nullable=True)
    started_date = Column(DateTime(timezone=True), nullable=True)
    completed_date = Column(DateTime(timezone=True), nullable=True)

    # Assignment
    assigned_technician_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # Task data and results
    task_data = Column(JSONB, nullable=True)  # Input data for the task
    result_data = Column(JSONB, nullable=True)  # Results and outputs
    error_message = Column(Text, nullable=True)

    # Relationships
    service_instance = relationship(
        "ServiceInstance", back_populates="provisioning_tasks"
    )
    assigned_technician = relationship("User")


class ServiceUsage(TenantModel):
    """Service usage tracking model."""

    __tablename__ = "service_usage"

    service_instance_id = Column(
        UUID(as_uuid=True), ForeignKey("service_instances.id"), nullable=False
    )

    # Usage period
    usage_date = Column(Date, nullable=False)
    usage_period = Column(
        String(20), default="daily", nullable=False
    )  # daily, weekly, monthly

    # Usage metrics
    data_downloaded = Column(Numeric(15, 2), nullable=False, default=0)  # in MB
    data_uploaded = Column(Numeric(15, 2), nullable=False, default=0)  # in MB
    total_data = Column(Numeric(15, 2), nullable=False, default=0)  # in MB

    # Performance metrics
    avg_download_speed = Column(Numeric(10, 2), nullable=True)  # in Mbps
    avg_upload_speed = Column(Numeric(10, 2), nullable=True)  # in Mbps
    peak_download_speed = Column(Numeric(10, 2), nullable=True)  # in Mbps
    peak_upload_speed = Column(Numeric(10, 2), nullable=True)  # in Mbps

    # Connection metrics
    uptime_percentage = Column(Numeric(5, 2), nullable=True)  # 0-100
    downtime_minutes = Column(Integer, nullable=True)

    # Additional metrics (stored as JSON)
    additional_metrics = Column(JSONB, nullable=True)

    # Relationships
    service_instance = relationship("ServiceInstance")


class ServiceAlert(TenantModel):
    """Service alert model for monitoring and notifications."""

    __tablename__ = "service_alerts"

    service_instance_id = Column(
        UUID(as_uuid=True), ForeignKey("service_instances.id"), nullable=False
    )

    # Alert details
    alert_type = Column(
        String(100), nullable=False
    )  # e.g., 'outage', 'performance', 'usage'
    severity = Column(
        String(20), default="medium", nullable=False
    )  # low, medium, high, critical
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)

    # Alert timing
    alert_time = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    resolved_time = Column(DateTime(timezone=True), nullable=True)
    acknowledged_time = Column(DateTime(timezone=True), nullable=True)

    # Status
    is_resolved = Column(Boolean, default=False, nullable=False)
    is_acknowledged = Column(Boolean, default=False, nullable=False)

    # Assignment
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Additional data
    alert_data = Column(JSONB, nullable=True)

    # Relationships
    service_instance = relationship("ServiceInstance")
    assigned_user = relationship("User")
