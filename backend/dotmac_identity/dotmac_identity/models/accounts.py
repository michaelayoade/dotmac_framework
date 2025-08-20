"""
Account models for identity management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from ..core.datetime_utils import utc_now, is_expired


class AccountStatus(Enum):
    """Account status enumeration."""
    ACTIVE = "active"
    DISABLED = "disabled"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"
    LOCKED = "locked"


class CredentialType(Enum):
    """Credential type enumeration."""
    PASSWORD = "password"
    API_KEY = "api_key"
    OAUTH_TOKEN = "oauth_token"
    CERTIFICATE = "certificate"


class MFAFactorType(Enum):
    """MFA factor type enumeration."""
    TOTP = "totp"
    SMS = "sms"
    EMAIL = "email"
    BACKUP_CODES = "backup_codes"
    HARDWARE_TOKEN = "hardware_token"


@dataclass
class Account:
    """User account model."""
    id: UUID = field(default_factory=uuid4)
    tenant_id: str = ""
    username: str = ""
    email: str = ""
    status: AccountStatus = AccountStatus.PENDING_VERIFICATION

    # Metadata
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    last_login_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None

    # Security
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    password_changed_at: Optional[datetime] = None

    # Profile links
    profile_id: Optional[UUID] = None
    organization_id: Optional[UUID] = None

    # Settings
    settings: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_active(self) -> bool:
        """Check if account is active."""
        return self.status == AccountStatus.ACTIVE

    def is_locked(self) -> bool:
        """Check if account is locked."""
        if self.status == AccountStatus.LOCKED:
            return True
        if self.locked_until and self.locked_until > utc_now():
            return True
        return False

    def can_login(self) -> bool:
        """Check if account can login."""
        return self.is_active() and not self.is_locked()


@dataclass
class Credential:
    """User credential model."""
    id: UUID = field(default_factory=uuid4)
    account_id: UUID = field(default_factory=uuid4)
    tenant_id: str = ""

    credential_type: CredentialType = CredentialType.PASSWORD
    credential_data: str = ""  # Hashed password, API key, etc.

    # Metadata
    name: Optional[str] = None
    description: Optional[str] = None

    # Status
    is_active: bool = True
    expires_at: Optional[datetime] = None

    # Tracking
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    last_used_at: Optional[datetime] = None

    # Security
    usage_count: int = 0
    max_usage_count: Optional[int] = None

    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if credential is expired."""
        if self.expires_at and self.expires_at < datetime.utcnow():
            return True
        if self.max_usage_count and self.usage_count >= self.max_usage_count:
            return True
        return False

    def is_valid(self) -> bool:
        """Check if credential is valid."""
        return self.is_active and not self.is_expired()


@dataclass
class MFAFactor:
    """Multi-factor authentication factor model."""
    id: UUID = field(default_factory=uuid4)
    account_id: UUID = field(default_factory=uuid4)
    tenant_id: str = ""

    factor_type: MFAFactorType = MFAFactorType.TOTP
    factor_data: Dict[str, Any] = field(default_factory=dict)  # TOTP secret, phone number, etc.

    # Status
    is_active: bool = True
    is_verified: bool = False

    # Metadata
    name: Optional[str] = None
    description: Optional[str] = None

    # Tracking
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    verified_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None

    # Usage tracking
    usage_count: int = 0
    failed_attempts: int = 0

    # Backup codes (for BACKUP_CODES type)
    backup_codes: List[str] = field(default_factory=list)
    used_backup_codes: List[str] = field(default_factory=list)

    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_valid(self) -> bool:
        """Check if MFA factor is valid."""
        return self.is_active and self.is_verified

    def has_unused_backup_codes(self) -> bool:
        """Check if there are unused backup codes."""
        if self.factor_type != MFAFactorType.BACKUP_CODES:
            return False
        return len(set(self.backup_codes) - set(self.used_backup_codes)) > 0
