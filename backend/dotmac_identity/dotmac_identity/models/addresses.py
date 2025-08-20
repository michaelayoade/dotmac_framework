"""
Address models for postal and geographic information.
"""

from dataclasses import dataclass, field
from datetime import datetime
from ..core.datetime_utils import utc_now, is_expired, expires_in_hours, expires_in_minutes
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4


class AddressType(Enum):
    """Address type enumeration."""
    BILLING = "billing"
    SHIPPING = "shipping"
    SERVICE = "service"
    MAILING = "mailing"
    HOME = "home"
    WORK = "work"
    OTHER = "other"


class AddressStatus(Enum):
    """Address status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


@dataclass
class Address:
    """Address model for postal and geographic information."""
    id: UUID = field(default_factory=uuid4)
    tenant_id: str = ""

    # Linked entities
    contact_id: Optional[UUID] = None
    organization_id: Optional[UUID] = None
    customer_id: Optional[UUID] = None

    # Address type and status
    address_type: AddressType = AddressType.BILLING
    status: AddressStatus = AddressStatus.ACTIVE

    # Address components
    line1: str = ""
    line2: Optional[str] = None
    line3: Optional[str] = None
    city: str = ""
    state_province: str = ""
    postal_code: str = ""
    country: str = ""

    # Geographic coordinates
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # Validation and verification
    is_verified: bool = False
    is_deliverable: Optional[bool] = None
    verified_at: Optional[datetime] = None

    # Metadata
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    # Additional data
    notes: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_formatted_address(self) -> str:
        """Get formatted address string."""
        lines = [self.line1]
        if self.line2:
            lines.append(self.line2)
        if self.line3:
            lines.append(self.line3)

        city_state_zip = f"{self.city}, {self.state_province} {self.postal_code}".strip()
        if city_state_zip != ", ":
            lines.append(city_state_zip)

        if self.country:
            lines.append(self.country)

        return "\n".join(line for line in lines if line.strip())

    def get_single_line_address(self) -> str:
        """Get single line formatted address."""
        return self.get_formatted_address().replace("\n", ", ")

    def is_active(self) -> bool:
        """Check if address is active."""
        return self.status == AddressStatus.ACTIVE

    def has_coordinates(self) -> bool:
        """Check if address has geographic coordinates."""
        return self.latitude is not None and self.longitude is not None
