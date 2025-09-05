"""Customer models for SDK."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID


class CustomerStatus(str, Enum):
    """Customer status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class CustomerType(str, Enum):
    """Customer type enumeration."""

    RESIDENTIAL = "residential"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


# Alias for CustomerState
CustomerState = CustomerStatus


@dataclass
class Customer:
    """Customer model."""

    customer_id: UUID
    customer_number: str
    customer_type: CustomerType
    status: CustomerStatus
    company_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    billing_address: Optional[dict] = None
    service_address: Optional[dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class CustomerProfile:
    """Customer profile model."""

    profile_id: UUID
    customer_id: UUID
    preferences: dict
    communication_settings: dict
    billing_preferences: dict
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class CustomerNote:
    """Customer note model."""

    note_id: UUID
    customer_id: UUID
    note_text: str
    created_by: str
    created_at: datetime
    note_type: Optional[str] = None
