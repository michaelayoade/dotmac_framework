"""Contact models for SDK."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from uuid import UUID


class ContactType(str, Enum):
    """Contact type enumeration."""

    PRIMARY = "primary"
    BILLING = "billing"
    TECHNICAL = "technical"
    EMERGENCY = "emergency"


class EmailType(str, Enum):
    """Email type enumeration."""

    PERSONAL = "personal"
    BUSINESS = "business"
    BILLING = "billing"
    SUPPORT = "support"


class PhoneType(str, Enum):
    """Phone type enumeration."""

    MOBILE = "mobile"
    HOME = "home"
    OFFICE = "office"
    FAX = "fax"
    EMERGENCY = "emergency"


@dataclass
class Contact:
    """Contact model."""

    contact_id: UUID
    first_name: str
    last_name: str
    contact_type: ContactType
    customer_id: Optional[UUID] = None
    company: Optional[str] = None
    title: Optional[str] = None
    preferred_language: Optional[str] = None


@dataclass
class ContactEmail:
    """Contact email model."""

    email_id: UUID
    contact_id: UUID
    email_address: str
    email_type: EmailType
    is_primary: bool = False
    is_verified: bool = False


@dataclass
class ContactPhone:
    """Contact phone model."""

    phone_id: UUID
    contact_id: UUID
    phone_number: str
    phone_type: PhoneType
    is_primary: bool = False
    is_verified: bool = False
    country_code: Optional[str] = None
