"""
Customer model definitions
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class CustomerTier(Enum):
    """Customer tier levels"""

    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class CustomerStatus(Enum):
    """Customer account status"""

    PENDING_VERIFICATION = "pending_verification"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"


class Customer(BaseModel):
    """Customer model"""

    id: str = Field(..., description="Unique customer identifier")
    email: str = Field(..., description="Customer email address")
    first_name: str = Field(..., description="Customer first name")
    last_name: str = Field(..., description="Customer last name")
    phone: Optional[str] = Field(None, description="Customer phone number")
    tier: CustomerTier = Field(CustomerTier.BASIC, description="Customer service tier")
    status: CustomerStatus = Field(CustomerStatus.PENDING_VERIFICATION, description="Customer account status")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional customer metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Customer creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = ConfigDict(use_enum_values=True)
