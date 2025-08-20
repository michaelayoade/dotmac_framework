"""
Consent and preferences models for GDPR/CCPA compliance and communication preferences.
"""

from dataclasses import dataclass, field
from datetime import datetime
from ..core.datetime_utils import utc_now, is_expired, expires_in_hours, expires_in_minutes
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class ConsentType(Enum):
    """Consent type enumeration."""
    MARKETING_EMAIL = "marketing_email"
    MARKETING_SMS = "marketing_sms"
    MARKETING_WHATSAPP = "marketing_whatsapp"
    TRANSACTIONAL_EMAIL = "transactional_email"
    TRANSACTIONAL_SMS = "transactional_sms"
    DATA_PROCESSING = "data_processing"
    COOKIES = "cookies"
    ANALYTICS = "analytics"
    THIRD_PARTY_SHARING = "third_party_sharing"


class ConsentStatus(Enum):
    """Consent status enumeration."""
    GRANTED = "granted"
    DENIED = "denied"
    WITHDRAWN = "withdrawn"
    PENDING = "pending"


class ConsentMethod(Enum):
    """Consent collection method enumeration."""
    EXPLICIT_OPT_IN = "explicit_opt_in"
    IMPLIED_CONSENT = "implied_consent"
    PRE_CHECKED_BOX = "pre_checked_box"
    UNCHECKED_BOX = "unchecked_box"
    VERBAL = "verbal"
    WRITTEN = "written"


class ComplianceRegion(Enum):
    """Compliance region enumeration."""
    GDPR = "gdpr"  # EU General Data Protection Regulation
    CCPA = "ccpa"  # California Consumer Privacy Act
    PIPEDA = "pipeda"  # Personal Information Protection and Electronic Documents Act (Canada)
    LGPD = "lgpd"  # Lei Geral de Proteção de Dados (Brazil)


@dataclass
class ConsentPreference:
    """Consent preference model for communication preferences and compliance."""
    id: UUID = field(default_factory=uuid4)
    tenant_id: str = ""

    # Target entity
    contact_id: Optional[UUID] = None
    account_id: Optional[UUID] = None
    customer_id: Optional[UUID] = None

    # Consent details
    consent_type: ConsentType = ConsentType.MARKETING_EMAIL
    status: ConsentStatus = ConsentStatus.PENDING

    # Collection details
    consent_method: ConsentMethod = ConsentMethod.EXPLICIT_OPT_IN
    collected_at: datetime = field(default_factory=utc_now)
    collected_from: Optional[str] = None  # Source: website, app, phone, etc.

    # Legal basis and compliance
    legal_basis: Optional[str] = None
    compliance_regions: List[ComplianceRegion] = field(default_factory=list)

    # Timing
    granted_at: Optional[datetime] = None
    withdrawn_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    # Tracking
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    # Additional data
    notes: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_active(self) -> bool:
        """Check if consent is currently active."""
        if self.status != ConsentStatus.GRANTED:
            return False
        if self.expires_at and self.expires_at < utc_now():
            return False
        return True

    def is_expired(self) -> bool:
        """Check if consent has expired."""
        return self.expires_at is not None and self.expires_at < utc_now()


@dataclass
class ConsentAudit:
    """Consent audit log for compliance tracking."""
    id: UUID = field(default_factory=uuid4)
    tenant_id: str = ""

    # Related consent
    consent_preference_id: UUID = field(default_factory=uuid4)

    # Audit details
    action: str = ""  # granted, withdrawn, updated, expired
    previous_status: Optional[ConsentStatus] = None
    new_status: ConsentStatus = ConsentStatus.PENDING

    # Context
    performed_by: Optional[UUID] = None  # Account ID who performed the action
    performed_at: datetime = field(default_factory=utc_now)
    source: Optional[str] = None  # Source of the change

    # Legal and compliance
    legal_basis: Optional[str] = None
    compliance_regions: List[ComplianceRegion] = field(default_factory=list)

    # Evidence
    evidence_data: Dict[str, Any] = field(default_factory=dict)  # IP address, user agent, etc.

    # Additional data
    notes: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
