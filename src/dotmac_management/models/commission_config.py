"""
Commission configuration models for flexible reseller management.
All commission rates and structures are configurable via management portal.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import JSON, Boolean, Column, Date, Numeric, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID

from dotmac_shared.sales.core.reseller_models import (
    CommissionStructure,
    ResellerTier,
    ResellerType,
)
from dotmac_shared.validation.common_validators import (
    CommonValidators,
    ValidationPatterns,
)

from .base import BaseModel as DBBaseModel


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
    service_tier = Column(String(50), nullable=True)  # e.g., "basic", "premium"

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
    territory: Optional[str] = Field(None, max_length=100)
    commission_structure: CommissionStructure
    rate_config: dict[str, Any]
    effective_from: date
    effective_until: Optional[date] = None
    calculate_on: str = Field(default="revenue", pattern=r"^(revenue|signup|both)$")
    payment_frequency: str = Field(default="monthly", pattern=r"^(monthly|quarterly|annual)$")
    minimum_payout: Decimal = Field(default=Decimal("50.00"), ge=Decimal("0.00"), le=Decimal("10000.00"))
    settings: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate commission config name with sanitization"""
        return CommonValidators.validate_required_string(v, "Commission config name", 2, 200)

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate optional description"""
        return CommonValidators.validate_description(v, 500)

    @field_validator("territory")
    @classmethod
    def validate_territory(cls, v: Optional[str]) -> Optional[str]:
        """Validate territory code"""
        if v is None:
            return None
        clean_territory = v.strip().upper()
        if not ValidationPatterns.ALPHANUMERIC.match(clean_territory.replace("-", "")):
            raise ValueError("Territory must contain only alphanumeric characters and hyphens")
        if len(clean_territory) < 2 or len(clean_territory) > 10:
            raise ValueError("Territory must be between 2 and 10 characters")
        return clean_territory

    @field_validator("rate_config")
    @classmethod
    def validate_rate_config(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate commission rate configuration structure"""
        if not v:
            raise ValueError("Rate configuration is required")

        # Validate based on common patterns
        if "percentage" in v:
            percentage = v["percentage"]
            if isinstance(percentage, str):
                try:
                    percentage = Decimal(percentage)
                except Exception as e:
                    raise ValueError("Invalid percentage format") from e
            if not isinstance(percentage, (int, float, Decimal)):
                raise ValueError("Percentage must be numeric")
            if percentage < 0 or percentage > 100:
                raise ValueError("Percentage must be between 0 and 100")

        if "amount" in v:
            amount = v["amount"]
            if isinstance(amount, str):
                try:
                    amount = Decimal(amount)
                except Exception as e:
                    raise ValueError("Invalid amount format") from e
            if not isinstance(amount, (int, float, Decimal)):
                raise ValueError("Amount must be numeric")
            if amount < 0:
                raise ValueError("Amount must be non-negative")
            if amount > Decimal("999999.99"):
                raise ValueError("Amount cannot exceed $999,999.99")

        if "tiers" in v:
            tiers = v["tiers"]
            if not isinstance(tiers, list) or len(tiers) == 0:
                raise ValueError("Tiers must be a non-empty list")

            for i, tier in enumerate(tiers):
                if not isinstance(tier, dict):
                    raise ValueError(f"Tier {i+1} must be an object")

                # Validate tier structure
                required_fields = ["min_amount", "rate"]
                for field in required_fields:
                    if field not in tier:
                        raise ValueError(f"Tier {i+1} missing required field: {field}")

                # Validate tier amounts
                min_amount = tier.get("min_amount", 0)
                if isinstance(min_amount, str):
                    try:
                        min_amount = Decimal(min_amount)
                    except Exception as e:
                        raise ValueError(f"Tier {i+1} min_amount must be numeric") from e

                if min_amount < 0:
                    raise ValueError(f"Tier {i+1} min_amount must be non-negative")

                # Validate tier rate
                rate = tier.get("rate")
                if isinstance(rate, str):
                    try:
                        rate = Decimal(rate)
                    except Exception as e:
                        raise ValueError(f"Tier {i+1} rate must be numeric") from e

                if rate < 0 or rate > 100:
                    raise ValueError(f"Tier {i+1} rate must be between 0 and 100")

        return v

    @field_validator("effective_until")
    @classmethod
    def validate_effective_dates(cls, v: Optional[date], info) -> Optional[date]:
        """Validate effective date range"""
        if v is None:
            return None

        # Check if effective_from is available
        effective_from = info.data.get("effective_from")
        if effective_from and v <= effective_from:
            raise ValueError("Effective until date must be after effective from date")

        return v

    @field_validator("minimum_payout")
    @classmethod
    def validate_minimum_payout(cls, v: Decimal) -> Decimal:
        """Validate minimum payout amount"""
        if v < Decimal("0.00"):
            raise ValueError("Minimum payout cannot be negative")
        if v > Decimal("10000.00"):
            raise ValueError("Minimum payout cannot exceed $10,000.00")

        # Round to 2 decimal places for currency
        return v.quantize(Decimal("0.01"))

    @field_validator("settings")
    @classmethod
    def validate_settings(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate commission settings structure"""
        if not isinstance(v, dict):
            raise ValueError("Settings must be a dictionary")

        # Validate specific settings if present
        if "performance_multipliers" in v:
            multipliers = v["performance_multipliers"]
            if not isinstance(multipliers, dict):
                raise ValueError("Performance multipliers must be a dictionary")

            for key, multiplier in multipliers.items():
                if not isinstance(multiplier, (int, float, Decimal)):
                    raise ValueError(f"Performance multiplier {key} must be numeric")
                if multiplier < 0.1 or multiplier > 10.0:
                    raise ValueError(f"Performance multiplier {key} must be between 0.1 and 10.0")

        return v


class CommissionConfigCreate(CommissionConfigBase):
    pass


class CommissionConfigUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    rate_config: Optional[dict[str, Any]] = None
    effective_until: Optional[date] = None
    calculate_on: Optional[str] = None
    payment_frequency: Optional[str] = None
    minimum_payout: Optional[Decimal] = None
    settings: Optional[dict[str, Any]] = None


class CommissionConfigResponse(CommissionConfigBase):
    id: UUID
    created_at: datetime
    updated_at: datetime


class RevenueModelBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

    service_type: str = Field(..., min_length=1, max_length=100)
    service_tier: Optional[str] = Field(None, max_length=50)
    base_price: Decimal = Field(..., ge=Decimal("0.00"), le=Decimal("999999.99"))
    setup_fee: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), le=Decimal("99999.99"))
    recurring_fee: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), le=Decimal("99999.99"))
    recurring_period: str = Field(default="monthly", pattern=r"^(monthly|quarterly|annual|one-time)$")
    territory: Optional[str] = Field(None, max_length=100)
    currency: str = Field(default="USD", min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    pricing_config: dict[str, Any] = Field(default_factory=dict)
    effective_from: date
    effective_until: Optional[date] = None
    is_active: bool = True

    @field_validator("service_type")
    @classmethod
    def validate_service_type(cls, v: str) -> str:
        """Validate service type with sanitization"""
        return CommonValidators.validate_required_string(v, "Service type", 2, 100)

    @field_validator("service_tier")
    @classmethod
    def validate_service_tier(cls, v: Optional[str]) -> Optional[str]:
        """Validate service tier"""
        if v is None:
            return None
        clean_tier = v.strip().lower()
        allowed_tiers = ["basic", "standard", "premium", "enterprise", "custom"]
        if clean_tier not in allowed_tiers:
            raise ValueError(f"Service tier must be one of: {allowed_tiers}")
        return clean_tier

    @field_validator("base_price", "setup_fee", "recurring_fee")
    @classmethod
    def validate_currency_amounts(cls, v: Decimal, info) -> Decimal:
        """Validate currency amounts with proper decimal places"""
        if v < Decimal("0.00"):
            raise ValueError(f"{info.field_name} cannot be negative")

        # Round to 2 decimal places for currency
        rounded = v.quantize(Decimal("0.01"))

        # Check maximum limits based on field
        max_amounts = {
            "base_price": Decimal("999999.99"),
            "setup_fee": Decimal("99999.99"),
            "recurring_fee": Decimal("99999.99"),
        }

        max_amount = max_amounts.get(info.field_name, Decimal("999999.99"))
        if rounded > max_amount:
            raise ValueError(f"{info.field_name} cannot exceed ${max_amount}")

        return rounded

    @field_validator("territory")
    @classmethod
    def validate_territory(cls, v: Optional[str]) -> Optional[str]:
        """Validate territory code"""
        if v is None:
            return None
        clean_territory = v.strip().upper()
        if not ValidationPatterns.ALPHANUMERIC.match(clean_territory.replace("-", "")):
            raise ValueError("Territory must contain only alphanumeric characters and hyphens")
        if len(clean_territory) < 2 or len(clean_territory) > 10:
            raise ValueError("Territory must be between 2 and 10 characters")
        return clean_territory

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate ISO currency code"""
        clean_currency = v.strip().upper()

        # Basic ISO 4217 validation - should be 3 letter code
        if not clean_currency.isalpha() or len(clean_currency) != 3:
            raise ValueError("Currency must be a valid 3-letter ISO code")

        # Common currency codes validation
        valid_currencies = {
            "USD",
            "EUR",
            "GBP",
            "CAD",
            "AUD",
            "JPY",
            "CHF",
            "CNY",
            "INR",
            "BRL",
            "MXN",
            "ZAR",
            "KRW",
            "SGD",
            "HKD",
            "NOK",
            "SEK",
            "DKK",
            "PLN",
            "CZK",
        }

        if clean_currency not in valid_currencies:
            raise ValueError(f"Currency {clean_currency} is not supported")

        return clean_currency

    @field_validator("pricing_config")
    @classmethod
    def validate_pricing_config(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate pricing configuration structure"""
        if not isinstance(v, dict):
            raise ValueError("Pricing config must be a dictionary")

        # Validate volume discounts if present
        if "volume_discounts" in v:
            discounts = v["volume_discounts"]
            if not isinstance(discounts, list):
                raise ValueError("Volume discounts must be a list")

            for i, discount in enumerate(discounts):
                if not isinstance(discount, dict):
                    raise ValueError(f"Volume discount {i+1} must be an object")

                required_fields = ["min_quantity", "discount_percentage"]
                for field in required_fields:
                    if field not in discount:
                        raise ValueError(f"Volume discount {i+1} missing required field: {field}")

                # Validate quantities and percentages
                min_qty = discount.get("min_quantity", 0)
                if not isinstance(min_qty, (int, float)) or min_qty <= 0:
                    raise ValueError(f"Volume discount {i+1} min_quantity must be positive")

                discount_pct = discount.get("discount_percentage", 0)
                if not isinstance(discount_pct, (int, float, Decimal)) or discount_pct < 0 or discount_pct > 100:
                    raise ValueError(f"Volume discount {i+1} discount_percentage must be between 0 and 100")

        # Validate promotional rates if present
        if "promotional_rates" in v:
            promo = v["promotional_rates"]
            if not isinstance(promo, dict):
                raise ValueError("Promotional rates must be a dictionary")

            if "discount_percentage" in promo:
                discount = promo["discount_percentage"]
                if not isinstance(discount, (int, float, Decimal)) or discount < 0 or discount > 100:
                    raise ValueError("Promotional discount percentage must be between 0 and 100")

        return v

    @field_validator("effective_until")
    @classmethod
    def validate_effective_dates(cls, v: Optional[date], info) -> Optional[date]:
        """Validate effective date range"""
        if v is None:
            return None

        # Check if effective_from is available
        effective_from = info.data.get("effective_from")
        if effective_from and v <= effective_from:
            raise ValueError("Effective until date must be after effective from date")

        return v


class RevenueModelCreate(RevenueModelBase):
    pass


class RevenueModelUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

    base_price: Optional[Decimal] = None
    setup_fee: Optional[Decimal] = None
    recurring_fee: Optional[Decimal] = None
    pricing_config: Optional[dict[str, Any]] = None
    effective_until: Optional[date] = None
    is_active: Optional[bool] = None


class RevenueModelResponse(RevenueModelBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
