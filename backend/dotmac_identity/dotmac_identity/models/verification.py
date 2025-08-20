"""
Verification models for email and phone verification with OTP.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from ..core.datetime_utils import utc_now, is_expired, expires_in_hours, expires_in_minutes
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4


class VerificationType(Enum):
    """Verification type enumeration."""
    EMAIL = "email"
    PHONE = "phone"


class VerificationStatus(Enum):
    """Verification status enumeration."""
    PENDING = "pending"
    VERIFIED = "verified"
    EXPIRED = "expired"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DeliverabilityStatus(Enum):
    """Email deliverability status enumeration."""
    DELIVERED = "delivered"
    BOUNCED = "bounced"
    REJECTED = "rejected"
    SPAM = "spam"
    UNKNOWN = "unknown"


@dataclass
class EmailVerification:
    """Email verification model with OTP and deliverability tracking."""
    id: UUID = field(default_factory=uuid4)
    tenant_id: str = ""

    # Target information
    email: str = ""
    contact_id: Optional[UUID] = None
    account_id: Optional[UUID] = None

    # Verification details
    verification_code: str = ""
    status: VerificationStatus = VerificationStatus.PENDING

    # Timing
    created_at: datetime = field(default_factory=utc_now)
    expires_at: datetime = field(default_factory=lambda: utc_now() + timedelta(hours=1))
    verified_at: Optional[datetime] = None

    # Attempts tracking
    attempts_count: int = 0
    max_attempts: int = 3
    last_attempt_at: Optional[datetime] = None

    # Deliverability results
    deliverability_status: Optional[DeliverabilityStatus] = None
    delivery_attempted_at: Optional[datetime] = None
    delivery_confirmed_at: Optional[datetime] = None
    bounce_reason: Optional[str] = None

    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if verification is expired."""
        return utc_now() > self.expires_at

    def is_valid(self) -> bool:
        """Check if verification is valid for use."""
        return (
            self.status == VerificationStatus.PENDING and
            not self.is_expired() and
            self.attempts_count < self.max_attempts
        )

    def can_retry(self) -> bool:
        """Check if verification can be retried."""
        return self.attempts_count < self.max_attempts and not self.is_expired()


@dataclass
class PhoneVerification:
    """Phone verification model with OTP."""
    id: UUID = field(default_factory=uuid4)
    tenant_id: str = ""

    # Target information
    phone_number: str = ""
    country_code: Optional[str] = None
    contact_id: Optional[UUID] = None
    account_id: Optional[UUID] = None

    # Verification details
    verification_code: str = ""
    status: VerificationStatus = VerificationStatus.PENDING

    # Timing
    created_at: datetime = field(default_factory=utc_now)
    expires_at: datetime = field(default_factory=lambda: utc_now() + timedelta(minutes=5))
    verified_at: Optional[datetime] = None

    # Attempts tracking
    attempts_count: int = 0
    max_attempts: int = 3
    last_attempt_at: Optional[datetime] = None

    # SMS delivery tracking
    sms_sent_at: Optional[datetime] = None
    sms_delivered_at: Optional[datetime] = None
    sms_failed_at: Optional[datetime] = None
    sms_failure_reason: Optional[str] = None

    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_formatted_number(self) -> str:
        """Get formatted phone number."""
        if self.country_code and not self.phone_number.startswith("+"):
            return f"+{self.country_code}{self.phone_number}"
        return self.phone_number

    def is_expired(self) -> bool:
        """Check if verification is expired."""
        return utc_now() > self.expires_at

    def is_valid(self) -> bool:
        """Check if verification is valid for use."""
        return (
            self.status == VerificationStatus.PENDING and
            not self.is_expired() and
            self.attempts_count < self.max_attempts
        )

    def can_retry(self) -> bool:
        """Check if verification can be retried."""
        return self.attempts_count < self.max_attempts and not self.is_expired()
