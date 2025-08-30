"""Address models for SDK operations."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class AddressType(str, Enum):
    """Address type enumeration."""

    BILLING = "billing"
    SHIPPING = "shipping"
    SERVICE = "service"
    MAILING = "mailing"


@dataclass
class AddressModel:
    """Address model for customer and service locations."""

    id: Optional[str] = None
    address_type: Optional[AddressType] = None
    street_address: str = ""
    street_address_2: Optional[str] = None
    city: str = ""
    state_province: str = ""
    postal_code: str = ""
    country: str = "US"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_primary: bool = False
    is_verified: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# Alias for backward compatibility
Address = AddressModel
