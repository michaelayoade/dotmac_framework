"""
Contact models for people management across CRM, orders, and support.
"""

from dataclasses import dataclass, field
from datetime import datetime
from ..core.datetime_utils import utc_now, is_expired, expires_in_hours, expires_in_minutes
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class ContactType(Enum):
    """Contact type enumeration."""
    PERSON = "person"
    BUSINESS = "business"
    TECHNICAL = "technical"
    BILLING = "billing"
    SUPPORT = "support"


class ContactStatus(Enum):
    """Contact status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class EmailType(Enum):
    """Email type enumeration."""
    PRIMARY = "primary"
    WORK = "work"
    PERSONAL = "personal"
    BILLING = "billing"
    SUPPORT = "support"
    OTHER = "other"


class PhoneType(Enum):
    """Phone type enumeration."""
    PRIMARY = "primary"
    MOBILE = "mobile"
    WORK = "work"
    HOME = "home"
    FAX = "fax"
    OTHER = "other"


@dataclass
class Contact:
    """Contact model for people used across CRM, orders, and support."""
    id: UUID = field(default_factory=uuid4)
    tenant_id: str = ""

    # Basic information
    first_name: str = ""
    last_name: str = ""
    middle_name: Optional[str] = None
    display_name: Optional[str] = None

    # Contact type and status
    contact_type: ContactType = ContactType.PERSON
    status: ContactStatus = ContactStatus.ACTIVE

    # Business information
    company: Optional[str] = None
    job_title: Optional[str] = None
    department: Optional[str] = None

    # Relationships
    organization_id: Optional[UUID] = None
    account_id: Optional[UUID] = None

    # Metadata
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    # Additional data
    notes: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_full_name(self) -> str:
        """Get full name from components."""
        parts = []
        if self.first_name:
            parts.append(self.first_name)
        if self.middle_name:
            parts.append(self.middle_name)
        if self.last_name:
            parts.append(self.last_name)
        return " ".join(parts)

    def get_display_name(self) -> str:
        """Get the best display name."""
        if self.display_name:
            return self.display_name
        return self.get_full_name() or "Unknown Contact"

    def is_active(self) -> bool:
        """Check if contact is active."""
        return self.status == ContactStatus.ACTIVE


@dataclass
class ContactEmail:
    """Contact email model."""
    id: UUID = field(default_factory=uuid4)
    contact_id: UUID = field(default_factory=uuid4)
    tenant_id: str = ""

    # Email information
    email: str = ""
    email_type: EmailType = EmailType.PRIMARY

    # Status
    is_primary: bool = False
    is_verified: bool = False
    is_active: bool = True

    # Verification
    verified_at: Optional[datetime] = None
    verification_token: Optional[str] = None

    # Deliverability
    is_deliverable: Optional[bool] = None
    bounce_count: int = 0
    last_bounce_at: Optional[datetime] = None

    # Metadata
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_valid(self) -> bool:
        """Check if email is valid for use."""
        return self.is_active and (self.is_deliverable is not False)


@dataclass
class ContactPhone:
    """Contact phone model."""
    id: UUID = field(default_factory=uuid4)
    contact_id: UUID = field(default_factory=uuid4)
    tenant_id: str = ""

    # Phone information
    phone_number: str = ""
    country_code: Optional[str] = None
    phone_type: PhoneType = PhoneType.PRIMARY

    # Status
    is_primary: bool = False
    is_verified: bool = False
    is_active: bool = True

    # Verification
    verified_at: Optional[datetime] = None
    verification_token: Optional[str] = None

    # Metadata
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_formatted_number(self) -> str:
        """Get formatted phone number."""
        if self.country_code and not self.phone_number.startswith("+"):
            return f"+{self.country_code}{self.phone_number}"
        return self.phone_number

    def is_valid(self) -> bool:
        """Check if phone is valid for use."""
        return self.is_active
