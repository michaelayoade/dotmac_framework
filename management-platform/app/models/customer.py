"""
Customer models for tenant customer management.
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any

from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import JSON
from .base import UUID
from sqlalchemy.orm import relationship
from sqlalchemy import Enum as SQLEnum

from .base import BaseModel


class CustomerStatus(str, Enum):
    """Customer status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive" 
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class ServiceStatus(str, Enum):
    """Service status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PROVISIONING = "provisioning"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    MAINTENANCE = "maintenance"


class Customer(BaseModel):
    """Customer model for tenant customers."""
    
    __tablename__ = "customers"
    
    # Tenant relationship
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Customer information
    email = Column(String(255), nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    company_name = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    
    # Status
    status = Column(SQLEnum(CustomerStatus), default=CustomerStatus.ACTIVE, nullable=False, index=True)
    
    # Address information
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), nullable=True)
    
    # Account information
    account_number = Column(String(50), nullable=True, index=True)
    customer_since = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_login = Column(DateTime, nullable=True)
    
    # Payment information
    payment_status = Column(String(50), default="current", nullable=False, index=True)
    last_payment_date = Column(DateTime, nullable=True)
    next_billing_date = Column(DateTime, nullable=True)
    
    # Customer metadata
    notes = Column(Text, nullable=True)
    tags = Column(JSON, default=list, nullable=False)
    preferences = Column(JSON, default=dict, nullable=False)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="customers")
    services = relationship("CustomerService", back_populates="customer", cascade="all, delete-orphan")
    usage_records = relationship("CustomerUsageRecord", back_populates="customer")
    
    def __repr__(self) -> str:
        return f"<Customer(email='{self.email}', name='{self.first_name} {self.last_name}')>"
    
    @property
    def full_name(self) -> str:
        """Get customer's full name."""
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def display_name(self) -> str:
        """Get customer's display name (company or full name)."""
        return self.company_name or self.full_name
    
    @property
    def address(self) -> Dict[str, Optional[str]]:
        """Get customer address as dict."""
        return {
            "line1": self.address_line1,
            "line2": self.address_line2,
            "city": self.city,
            "state": self.state,
            "postal_code": self.postal_code,
            "country": self.country
        }


class CustomerService(BaseModel):
    """Customer service model for services provided to customers."""
    
    __tablename__ = "customer_services"
    
    # Relationships
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False, index=True)
    
    # Service information
    service_name = Column(String(255), nullable=False)
    service_type = Column(String(100), nullable=False, index=True)  # internet, phone, tv, etc.
    service_plan = Column(String(255), nullable=True)
    
    # Status and lifecycle
    status = Column(SQLEnum(ServiceStatus), default=ServiceStatus.PROVISIONING, nullable=False, index=True)
    activation_date = Column(DateTime, nullable=True)
    suspension_date = Column(DateTime, nullable=True)
    cancellation_date = Column(DateTime, nullable=True)
    
    # Service configuration
    configuration = Column(JSON, default=dict, nullable=False)
    technical_details = Column(JSON, default=dict, nullable=False)
    
    # Billing information
    monthly_cost = Column(Numeric(10, 2), nullable=False, default=0.00)
    setup_fee = Column(Numeric(10, 2), nullable=False, default=0.00)
    
    # Service metadata
    notes = Column(Text, nullable=True)
    tags = Column(JSON, default=list, nullable=False)
    
    # Relationships
    tenant = relationship("Tenant")
    customer = relationship("Customer", back_populates="services")
    usage_records = relationship("ServiceUsageRecord", back_populates="service")
    
    def __repr__(self) -> str:
        return f"<CustomerService(name='{self.service_name}', type='{self.service_type}', status='{self.status}')>"
    
    @property
    def is_active(self) -> bool:
        """Check if service is active."""
        return self.status == ServiceStatus.ACTIVE


class CustomerUsageRecord(BaseModel):
    """Customer usage tracking."""
    
    __tablename__ = "customer_usage_records"
    
    # Relationships
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False, index=True)
    
    # Usage period
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False, index=True)
    
    # Usage metrics
    data_usage_gb = Column(Numeric(15, 6), nullable=False, default=0)
    api_requests = Column(Integer, nullable=False, default=0)
    login_sessions = Column(Integer, nullable=False, default=0)
    support_tickets = Column(Integer, nullable=False, default=0)
    
    # Performance metrics
    uptime_percentage = Column(Numeric(5, 2), nullable=False, default=100.00)
    avg_response_time_ms = Column(Numeric(8, 2), nullable=False, default=0.00)
    peak_concurrent_users = Column(Integer, nullable=False, default=0)
    
    # Cost breakdown
    base_cost = Column(Numeric(10, 2), nullable=False, default=0.00)
    usage_charges = Column(Numeric(10, 2), nullable=False, default=0.00)
    overage_charges = Column(Numeric(10, 2), nullable=False, default=0.00)
    total_cost = Column(Numeric(10, 2), nullable=False, default=0.00)
    
    # Usage by service (JSON structure)
    usage_by_service = Column(JSON, default=dict, nullable=False)
    daily_breakdown = Column(JSON, default=list, nullable=False)
    
    # Relationships
    tenant = relationship("Tenant")
    customer = relationship("Customer", back_populates="usage_records")
    
    def __repr__(self) -> str:
        return f"<CustomerUsageRecord(customer_id='{self.customer_id}', period='{self.period_start.date()}')>"


class ServiceUsageRecord(BaseModel):
    """Service-level usage tracking."""
    
    __tablename__ = "service_usage_records"
    
    # Relationships
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    service_id = Column(UUID(as_uuid=True), ForeignKey("customer_services.id"), nullable=False, index=True)
    
    # Usage timestamp
    recorded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    
    # Usage metrics specific to service type
    data_usage_gb = Column(Numeric(15, 6), nullable=False, default=0)
    monthly_usage_gb = Column(Numeric(15, 6), nullable=False, default=0)
    peak_usage_date = Column(DateTime, nullable=True)
    uptime_percentage = Column(Numeric(5, 2), nullable=False, default=100.00)
    last_usage = Column(DateTime, nullable=True)
    
    # Performance metrics
    response_time_ms = Column(Numeric(8, 2), nullable=False, default=0.00)
    error_count = Column(Integer, nullable=False, default=0)
    success_count = Column(Integer, nullable=False, default=0)
    
    # Service-specific metrics (JSON structure)
    service_metrics = Column(JSON, default=dict, nullable=False)
    
    # Relationships
    tenant = relationship("Tenant")
    service = relationship("CustomerService", back_populates="usage_records")
    
    def __repr__(self) -> str:
        return f"<ServiceUsageRecord(service_id='{self.service_id}', recorded_at='{self.recorded_at}')>"