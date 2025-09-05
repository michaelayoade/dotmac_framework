"""
Service plan model definitions
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class BandwidthTier(Enum):
    """Bandwidth tier levels"""

    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class ServicePlanStatus(Enum):
    """Service plan status"""

    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DISCONTINUED = "discontinued"


class ServicePlan(BaseModel):
    """Service plan model"""

    id: str = Field(..., description="Unique service plan identifier")
    name: str = Field(..., description="Service plan name")
    description: Optional[str] = Field(None, description="Service plan description")
    bandwidth_down: int = Field(..., description="Download bandwidth in Mbps")
    bandwidth_up: int = Field(..., description="Upload bandwidth in Mbps")
    monthly_price: Decimal = Field(..., description="Monthly price in USD")
    setup_fee: Optional[Decimal] = Field(
        Decimal("0.00"), description="One-time setup fee"
    )
    tier: BandwidthTier = Field(..., description="Service tier level")
    features: list[str] = Field(
        default_factory=list, description="List of included features"
    )
    status: ServicePlanStatus = Field(
        ServicePlanStatus.DRAFT, description="Plan status"
    )
    data_cap: Optional[int] = Field(
        None, description="Monthly data cap in GB (None for unlimited)"
    )
    contract_length: int = Field(1, description="Contract length in months")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional plan metadata"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Plan creation timestamp"
    )
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = ConfigDict(use_enum_values=True)
