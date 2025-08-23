"""
Verification-related models for SDKs.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4
from dataclasses import dataclass


class VerificationStatus(str, Enum):
    """Verification status enumeration."""
    
    PENDING = "pending"
    VERIFIED = "verified"
    EXPIRED = "expired"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DeliverabilityStatus(str, Enum):
    """Email deliverability status enumeration."""
    
    DELIVERED = "delivered"
    BOUNCED = "bounced"
    REJECTED = "rejected"
    DEFERRED = "deferred"
    UNKNOWN = "unknown"


@dataclass 
class EmailVerification:
    """Email verification model."""
    
    id: UUID
    email: str
    verification_token: str
    status: VerificationStatus
    deliverability_status: DeliverabilityStatus
    created_at: datetime
    verified_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    attempts: int = 0
    max_attempts: int = 3
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', uuid4())
        self.email = kwargs.get('email')
        self.verification_token = kwargs.get('verification_token')
        self.status = kwargs.get('status', VerificationStatus.PENDING)
        self.deliverability_status = kwargs.get('deliverability_status', DeliverabilityStatus.UNKNOWN)
        self.created_at = kwargs.get('created_at', datetime.utcnow())
        self.verified_at = kwargs.get('verified_at')
        # Default expiry: 24 hours from creation
        self.expires_at = kwargs.get('expires_at', self.created_at + timedelta(hours=24))
        self.attempts = kwargs.get('attempts', 0)
        self.max_attempts = kwargs.get('max_attempts', 3)
    
    def is_expired(self) -> bool:
        """Check if verification has expired."""
        return self.expires_at and datetime.utcnow() > self.expires_at
    
    def can_retry(self) -> bool:
        """Check if verification can be retried."""
        return self.attempts < self.max_attempts and not self.is_expired()
    
    def mark_verified(self) -> None:
        """Mark verification as verified."""
        self.status = VerificationStatus.VERIFIED
        self.verified_at = datetime.utcnow()
    
    def mark_failed(self) -> None:
        """Mark verification as failed."""
        self.status = VerificationStatus.FAILED
        self.attempts += 1


@dataclass
class PhoneVerification:
    """Phone verification model."""
    
    id: UUID
    phone_number: str
    verification_code: str
    status: VerificationStatus
    created_at: datetime
    verified_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    attempts: int = 0
    max_attempts: int = 3
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', uuid4())
        self.phone_number = kwargs.get('phone_number')
        self.verification_code = kwargs.get('verification_code')
        self.status = kwargs.get('status', VerificationStatus.PENDING)
        self.created_at = kwargs.get('created_at', datetime.utcnow())
        self.verified_at = kwargs.get('verified_at')
        # Default expiry: 15 minutes from creation
        self.expires_at = kwargs.get('expires_at', self.created_at + timedelta(minutes=15))
        self.attempts = kwargs.get('attempts', 0)
        self.max_attempts = kwargs.get('max_attempts', 3)
    
    def is_expired(self) -> bool:
        """Check if verification has expired."""
        return self.expires_at and datetime.utcnow() > self.expires_at
    
    def can_retry(self) -> bool:
        """Check if verification can be retried."""
        return self.attempts < self.max_attempts and not self.is_expired()
    
    def mark_verified(self) -> None:
        """Mark verification as verified."""
        self.status = VerificationStatus.VERIFIED
        self.verified_at = datetime.utcnow()
    
    def mark_failed(self) -> None:
        """Mark verification as failed."""
        self.status = VerificationStatus.FAILED
        self.attempts += 1