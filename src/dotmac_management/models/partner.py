"""
Partner and Customer database models
"""

import uuid
from datetime import datetime
from typing import Optional

from app.database import Base
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
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship


class Partner(Base):
    """Partner/Reseller model"""

    __tablename__ = "partners"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    company_name = Column(String(100), nullable=False, index=True)
    partner_code = Column(String(10), unique=True, nullable=False, index=True)

    # Contact Information
    contact_name = Column(String(100), nullable=False)
    contact_email = Column(String(255), nullable=False, index=True)
    contact_phone = Column(String(20), nullable=False)

    # Address
    address_street = Column(String(200))
    address_city = Column(String(100))
    address_state = Column(String(2))
    address_zip = Column(String(10))
    address_country = Column(String(2), default="US")

    # Business Details
    territory = Column(String(100), nullable=False, index=True)
    tier = Column(
        String(20), nullable=False, default="bronze", index=True
    )  # bronze, silver, gold, platinum
    status = Column(
        String(20), nullable=False, default="active", index=True
    )  # active, suspended, inactive

    # Targets and Goals
    monthly_customer_target = Column(Integer, default=25)
    monthly_revenue_target = Column(Float, default=50000.0)
    growth_target = Column(Float, default=10.0)  # Percentage

    # Commission and Payout Info
    commission_tier = Column(String(20), nullable=False, default="bronze")
    last_payout_amount = Column(Float, default=0.0)
    next_payout_date = Column(DateTime)
    total_lifetime_revenue = Column(Float, default=0.0)

    # Authentication
    user_id = Column(String, ForeignKey("users.id"), nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customers = relationship("PartnerCustomer", back_populates="partner")
    commissions = relationship("Commission", back_populates="partner")
    user = relationship("User", back_populates="partner")


class PartnerCustomer(Base):
    """Customer managed by a partner"""

    __tablename__ = "partner_customers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    partner_id = Column(String, ForeignKey("partners.id"), nullable=False, index=True)

    # Customer Information
    name = Column(String(100), nullable=False, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    phone = Column(String(20), nullable=False)

    # Address
    address = Column(Text, nullable=False)
    address_validated = Column(Boolean, default=False)
    territory_validated = Column(Boolean, default=False)

    # Service Information
    service_plan = Column(
        String(50), nullable=False, index=True
    )  # residential_basic, etc.
    mrr = Column(Float, nullable=False)  # Monthly Recurring Revenue
    contract_length = Column(Integer, default=12)  # Contract length in months

    # Status
    status = Column(
        String(20), nullable=False, default="pending", index=True
    )  # active, pending, suspended, cancelled
    connection_status = Column(String(20), default="offline")  # online, offline
    usage_percentage = Column(Float, default=0.0)

    # Dates
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    activated_at = Column(DateTime)
    cancelled_at = Column(DateTime)
    last_payment_date = Column(DateTime)
    next_billing_date = Column(DateTime)

    # Additional Data
    notes = Column(Text)
    customer_metadata = Column(JSON, default=dict)

    # Relationships
    partner = relationship("Partner", back_populates="customers")
    commissions = relationship("Commission", back_populates="customer")


class Commission(Base):
    """Commission records for partners"""

    __tablename__ = "commissions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    partner_id = Column(String, ForeignKey("partners.id"), nullable=False, index=True)
    customer_id = Column(
        String, ForeignKey("partner_customers.id"), nullable=False, index=True
    )

    # Commission Details
    amount = Column(Float, nullable=False)
    base_amount = Column(Float, nullable=False)
    bonus_amount = Column(Float, default=0.0)
    effective_rate = Column(Float, nullable=False)  # Commission rate applied

    # Commission Breakdown
    tier_multiplier = Column(Float, default=1.0)
    product_multiplier = Column(Float, default=1.0)
    new_customer_bonus = Column(Float, default=0.0)
    territory_bonus = Column(Float, default=0.0)
    contract_length_bonus = Column(Float, default=0.0)
    promotional_adjustment = Column(Float, default=0.0)

    # Commission Type and Period
    commission_type = Column(
        String(20), default="monthly"
    )  # monthly, one-time, renewal
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # Status and Processing
    status = Column(
        String(20), nullable=False, default="pending", index=True
    )  # pending, approved, paid, disputed
    approved_at = Column(DateTime)
    paid_at = Column(DateTime)
    payout_batch_id = Column(String)

    # Audit Trail
    calculation_method = Column(String(50))  # Method used for calculation
    calculation_details = Column(JSON)  # Full calculation breakdown
    created_by = Column(String)  # System or user ID

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    partner = relationship("Partner", back_populates="commissions")
    customer = relationship("PartnerCustomer", back_populates="commissions")


class Territory(Base):
    """Partner territory definitions"""

    __tablename__ = "territories"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    name = Column(String(100), nullable=False)
    partner_id = Column(String, ForeignKey("partners.id"), nullable=False, index=True)

    # Boundary Definitions
    zip_codes = Column(JSON, default=list)  # List of ZIP codes
    cities = Column(JSON, default=list)  # List of cities
    counties = Column(JSON, default=list)  # List of counties
    states = Column(JSON, default=list)  # List of state codes

    # Geographic Coordinates (for complex boundaries)
    coordinates_polygon = Column(JSON)  # GeoJSON polygon

    # Exclusions
    excluded_zip_codes = Column(JSON, default=list)
    excluded_addresses = Column(JSON, default=list)

    # Territory Management
    priority = Column(Integer, default=5)  # 1-10, higher = higher priority
    is_active = Column(Boolean, default=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    partner = relationship("Partner")


class PartnerPerformanceMetrics(Base):
    """Historical partner performance metrics"""

    __tablename__ = "partner_performance_metrics"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    partner_id = Column(String, ForeignKey("partners.id"), nullable=False, index=True)

    # Time Period
    period_type = Column(
        String(20), nullable=False
    )  # daily, weekly, monthly, quarterly, yearly
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # Customer Metrics
    customers_added = Column(Integer, default=0)
    customers_churned = Column(Integer, default=0)
    customers_total = Column(Integer, default=0)
    customers_active = Column(Integer, default=0)

    # Revenue Metrics
    revenue_total = Column(Float, default=0.0)
    revenue_new = Column(Float, default=0.0)
    revenue_churn = Column(Float, default=0.0)
    revenue_growth_rate = Column(Float, default=0.0)

    # Commission Metrics
    commissions_earned = Column(Float, default=0.0)
    commissions_paid = Column(Float, default=0.0)
    commission_rate_average = Column(Float, default=0.0)

    # Goals Achievement
    customer_goal_achievement = Column(Float, default=0.0)  # Percentage
    revenue_goal_achievement = Column(Float, default=0.0)  # Percentage

    # Additional Metrics
    average_deal_size = Column(Float, default=0.0)
    conversion_rate = Column(Float, default=0.0)
    customer_satisfaction = Column(Float, default=0.0)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    calculated_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    partner = relationship("Partner")
