"""
Account-related models for SDKs.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from dataclasses import dataclass


class MFAFactorType(str, Enum):
    """Multi-factor authentication factor types."""
    
    TOTP = "totp"  # Time-based One-Time Password
    SMS = "sms"    # SMS verification
    EMAIL = "email"  # Email verification
    BACKUP_CODES = "backup_codes"  # Recovery codes
    PUSH = "push"  # Push notification
    HARDWARE_KEY = "hardware_key"  # Hardware security key


class AccountStatus(str, Enum):
    """Account status enumeration."""
    
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    LOCKED = "locked"
    PENDING_VERIFICATION = "pending_verification"


@dataclass
class MFAFactor:
    """MFA factor model."""
    
    id: UUID
    account_id: UUID
    factor_type: MFAFactorType
    name: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', uuid4())
        self.account_id = kwargs.get('account_id')
        self.factor_type = kwargs.get('factor_type')
        self.name = kwargs.get('name')
        self.is_active = kwargs.get('is_active', True)
        self.is_verified = kwargs.get('is_verified', False)
        self.created_at = kwargs.get('created_at', datetime.utcnow())
        self.last_used_at = kwargs.get('last_used_at')
        self.metadata = kwargs.get('metadata') or {}


@dataclass
class Account:
    """Account model."""
    
    id: UUID
    username: str
    email: str
    status: AccountStatus
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', uuid4())
        self.username = kwargs.get('username')
        self.email = kwargs.get('email')
        self.status = kwargs.get('status', AccountStatus.PENDING_VERIFICATION)
        self.is_verified = kwargs.get('is_verified', False)
        self.created_at = kwargs.get('created_at', datetime.utcnow())
        self.updated_at = kwargs.get('updated_at', datetime.utcnow())
        self.last_login_at = kwargs.get('last_login_at')
        self.failed_login_attempts = kwargs.get('failed_login_attempts', 0)
        self.locked_until = kwargs.get('locked_until')
    
    def is_locked(self) -> bool:
        """Check if account is currently locked."""
        if self.locked_until:
            return datetime.utcnow() < self.locked_until
        return self.status == AccountStatus.LOCKED
    
    def lock_account(self, duration_minutes: int = 30) -> None:
        """Lock account for specified duration."""
        self.status = AccountStatus.LOCKED
        self.locked_until = datetime.utcnow() + datetime.timedelta(minutes=duration_minutes)
    
    def unlock_account(self) -> None:
        """Unlock account."""
        self.status = AccountStatus.ACTIVE
        self.locked_until = None
        self.failed_login_attempts = 0