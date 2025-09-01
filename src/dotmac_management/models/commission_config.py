"""
Commission configuration models for flexible reseller management.
All commission rates and structures are configurable via management portal.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any, Optional, List
from uuid import uuid4

from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey, Integer, 
    Numeric, String, Text, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy import Enum as SQLEnum
from pydantic import BaseModel, Field, ConfigDict

from .base import BaseModel as DBBaseModel
from dotmac_shared.sales.core.reseller_models import (
    ResellerType, ResellerTier, CommissionStructure
)


class CommissionConfig(DBBaseModel):
    """
    Configurable commission structure for resellers.
    Allows management portal to define all rates and rules.
    """
    __tablename__ = "commission_configs"
    
    # Basic configuration
    name = Column(String(200), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    
    # Applicable contexts
    reseller_type = Column(SQLEnum(ResellerType), nullable=True)  # Null = applies to all
    reseller_tier = Column(SQLEnum(ResellerTier), nullable=True)  # Null = applies to all
    territory = Column(String(100), nullable=True)  # Null = applies to all
    
    # Commission structure
    commission_structure = Column(SQLEnum(CommissionStructure), nullable=False)
    
    # Flexible rate configuration (JSON for complex structures)
    rate_config = Column(JSON, nullable=False)
    # Examples:
    # Flat rate: {"amount": "100.00"}
    # Percentage: {"percentage": "10.5"}
    # Tiered: {"tiers": [{"min_amount": 0, "max_amount": 1000, "rate": "5.0"}, ...]}
    # Performance: {"base_rate": "5.0", "performance_multipliers": {...}}
    
    # Effective period
    effective_from = Column(Date, nullable=False, default=date.today)
    effective_until = Column(Date, nullable=True)
    
    # Calculation settings
    calculate_on = Column(String(50), default="revenue")  # revenue, signup, both
    payment_frequency = Column(String(20), default="monthly")  # monthly, quarterly, annual
    minimum_payout = Column(Numeric(10, 2), default=Decimal("50.00"))
    
    # Additional settings
    settings = Column(JSON, default={})
    # Examples: auto_tier_upgrades, performance_bonuses, geographic_multipliers


class RevenueModel(DBBaseModel):
    """
    Configurable revenue models for different service types.
    Management portal defines all pricing structures.
    """
    __tablename__ = "revenue_models"
    
    # Service identification
    service_type = Column(String(100), nullable=False)  # e.g., "internet", "hosting"
    service_tier = Column(String(50), nullable=True)    # e.g., "basic", "premium"
    
    # Pricing structure
    base_price = Column(Numeric(10, 2), nullable=False)
    setup_fee = Column(Numeric(10, 2), default=Decimal("0.00"))
    recurring_fee = Column(Numeric(10, 2), default=Decimal("0.00"))
    recurring_period = Column(String(20), default="monthly")
    
    # Geographic pricing
    territory = Column(String(100), nullable=True)
    currency = Column(String(3), default="USD")
    
    # Flexible pricing options
    pricing_config = Column(JSON, default={})
    # Examples: volume_discounts, promotional_rates, seasonal_adjustments
    
    # Effective period
    effective_from = Column(Date, nullable=False, default=date.today)
    effective_until = Column(Date, nullable=True)
    
    is_active = Column(Boolean, default=True)


# Pydantic models for API
class CommissionConfigBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)
    
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    is_active: bool = True
    is_default: bool = False
    reseller_type: Optional[ResellerType] = None
    reseller_tier: Optional[ResellerTier] = None
    territory: Optional[str] = None
    commission_structure: CommissionStructure
    rate_config: Dict[str, Any]
    effective_from: date
    effective_until: Optional[date] = None
    calculate_on: str = "revenue"
    payment_frequency: str = "monthly"
    minimum_payout: Decimal = Field(default=Decimal("50.00"), ge=0)
    settings: Dict[str, Any] = Field(default_factory=dict)


class CommissionConfigCreate(CommissionConfigBase):
    pass


class CommissionConfigUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)
    
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    rate_config: Optional[Dict[str, Any]] = None
    effective_until: Optional[date] = None
    calculate_on: Optional[str] = None
    payment_frequency: Optional[str] = None
    minimum_payout: Optional[Decimal] = None
    settings: Optional[Dict[str, Any]] = None


class CommissionConfigResponse(CommissionConfigBase):
    id: UUID
    created_at: datetime
    updated_at: datetime


class RevenueModelBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)
    
    service_type: str = Field(..., min_length=1, max_length=100)
    service_tier: Optional[str] = None
    base_price: Decimal = Field(..., ge=0)
    setup_fee: Decimal = Field(default=Decimal("0.00"), ge=0)
    recurring_fee: Decimal = Field(default=Decimal("0.00"), ge=0)
    recurring_period: str = "monthly"
    territory: Optional[str] = None
    currency: str = "USD"
    pricing_config: Dict[str, Any] = Field(default_factory=dict)
    effective_from: date
    effective_until: Optional[date] = None
    is_active: bool = True


class RevenueModelCreate(RevenueModelBase):
    pass


class RevenueModelUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)
    
    base_price: Optional[Decimal] = None
    setup_fee: Optional[Decimal] = None
    recurring_fee: Optional[Decimal] = None
    pricing_config: Optional[Dict[str, Any]] = None
    effective_until: Optional[date] = None
    is_active: Optional[bool] = None


class RevenueModelResponse(RevenueModelBase):
    id: UUID
    created_at: datetime
    updated_at: datetime