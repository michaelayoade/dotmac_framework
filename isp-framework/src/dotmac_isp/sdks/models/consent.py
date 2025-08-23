"""Consent management models for GDPR and privacy compliance."""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum


class ConsentType(str, Enum):
    """Types of consent that can be granted or revoked."""

    ESSENTIAL = "essential"  # Required for service operation
    ANALYTICS = "analytics"  # Data analytics and metrics
    MARKETING = "marketing"  # Marketing communications
    PERSONALIZATION = "personalization"  # Personalized experience
    THIRD_PARTY = "third_party"  # Third-party integrations
    COOKIES = "cookies"  # Cookie tracking
    LOCATION = "location"  # Location data
    COMMUNICATIONS = "communications"  # Email/SMS communications


class ConsentStatus(str, Enum):
    """Status of consent."""

    GRANTED = "granted"
    REVOKED = "revoked"
    PENDING = "pending"
    EXPIRED = "expired"


class ConsentSource(str, Enum):
    """Source of consent collection."""

    REGISTRATION = "registration"  # During account registration
    WEBSITE = "website"  # Website consent banner
    MOBILE_APP = "mobile_app"  # Mobile application
    EMAIL = "email"  # Email consent link
    PHONE = "phone"  # Phone conversation
    IN_PERSON = "in_person"  # In-person interaction
    API = "api"  # API call
    ADMIN = "admin"  # Admin portal


class ConsentMethod(str, Enum):
    """Method of consent collection."""

    OPT_IN = "opt_in"  # Explicit opt-in
    OPT_OUT = "opt_out"  # Opt-out with notice
    IMPLIED = "implied"  # Implied consent
    LEGITIMATE_INTEREST = "legitimate_interest"  # Legitimate business interest


class ComplianceRegion(str, Enum):
    """GDPR compliance regions."""

    EU = "eu"  # European Union
    UK = "uk"  # United Kingdom
    CALIFORNIA = "california"  # California (CCPA)
    CANADA = "canada"  # Canada (PIPEDA)
    BRAZIL = "brazil"  # Brazil (LGPD)
    GLOBAL = "global"  # Global compliance


@dataclass
class ConsentPreference:
    """Individual consent preference."""

    consent_type: ConsentType
    status: ConsentStatus
    granted_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    source: Optional[ConsentSource] = None
    version: str = "1.0"  # Consent policy version
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    notes: Optional[str] = None

    def __post_init__(self):
        """Validate consent preference after initialization."""
        if self.status == ConsentStatus.GRANTED and self.granted_at is None:
            self.granted_at = datetime.now(timezone.utc)
        elif self.status == ConsentStatus.REVOKED and self.revoked_at is None:
            self.revoked_at = datetime.now(timezone.utc)

    def is_valid(self) -> bool:
        """Check if consent is currently valid."""
        if self.status != ConsentStatus.GRANTED:
            return False

        if self.expires_at and self.expires_at < datetime.now(timezone.utc):
            return False

        return True

    def is_expired(self) -> bool:
        """Check if consent has expired."""
        if not self.expires_at:
            return False
        return self.expires_at < datetime.now(timezone.utc)

    def revoke(
        self, source: Optional[ConsentSource] = None, notes: Optional[str] = None
    ):
        """Revoke the consent."""
        self.status = ConsentStatus.REVOKED
        self.revoked_at = datetime.now(timezone.utc)
        if source:
            self.source = source
        if notes:
            self.notes = notes


@dataclass
class ConsentAudit:
    """Audit record for consent changes."""

    audit_id: str
    user_id: str
    tenant_id: str
    consent_type: ConsentType
    old_status: ConsentStatus
    new_status: ConsentStatus
    timestamp: datetime
    source: ConsentSource
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ConsentProfile:
    """Complete consent profile for a customer."""

    customer_id: str
    tenant_id: str
    preferences: List[ConsentPreference]
    created_at: datetime
    updated_at: datetime
    profile_version: str = "1.0"
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Initialize consent profile."""
        if self.metadata is None:
            self.metadata = {}

    def get_consent(self, consent_type: ConsentType) -> Optional[ConsentPreference]:
        """Get consent preference for a specific type."""
        for pref in self.preferences:
            if pref.consent_type == consent_type:
                return pref
        return None

    def has_valid_consent(self, consent_type: ConsentType) -> bool:
        """Check if customer has valid consent for a specific type."""
        consent = self.get_consent(consent_type)
        return consent is not None and consent.is_valid()

    def grant_consent(
        self,
        consent_type: ConsentType,
        source: ConsentSource,
        expires_at: Optional[datetime] = None,
        version: str = "1.0",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        notes: Optional[str] = None,
    ):
        """Grant consent for a specific type."""
        # Remove existing consent for this type
        self.preferences = [
            p for p in self.preferences if p.consent_type != consent_type
        ]

        # Add new consent
        new_consent = ConsentPreference(
            consent_type=consent_type,
            status=ConsentStatus.GRANTED,
            granted_at=datetime.now(timezone.utc),
            expires_at=expires_at,
            source=source,
            version=version,
            ip_address=ip_address,
            user_agent=user_agent,
            notes=notes,
        )

        self.preferences.append(new_consent)
        self.updated_at = datetime.now(timezone.utc)

    def revoke_consent(
        self,
        consent_type: ConsentType,
        source: Optional[ConsentSource] = None,
        notes: Optional[str] = None,
    ):
        """Revoke consent for a specific type."""
        consent = self.get_consent(consent_type)
        if consent:
            consent.revoke(source, notes)
            self.updated_at = datetime.now(timezone.utc)

    def get_valid_consents(self) -> List[ConsentType]:
        """Get list of all valid consent types."""
        return [pref.consent_type for pref in self.preferences if pref.is_valid()]

    def get_expired_consents(self) -> List[ConsentType]:
        """Get list of expired consent types."""
        return [pref.consent_type for pref in self.preferences if pref.is_expired()]

    def to_dict(self) -> Dict[str, Any]:
        """Convert consent profile to dictionary."""
        return {
            "customer_id": self.customer_id,
            "tenant_id": self.tenant_id,
            "profile_version": self.profile_version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
            "preferences": [
                {
                    "consent_type": pref.consent_type.value,
                    "status": pref.status.value,
                    "granted_at": (
                        pref.granted_at.isoformat() if pref.granted_at else None
                    ),
                    "revoked_at": (
                        pref.revoked_at.isoformat() if pref.revoked_at else None
                    ),
                    "expires_at": (
                        pref.expires_at.isoformat() if pref.expires_at else None
                    ),
                    "source": pref.source.value if pref.source else None,
                    "version": pref.version,
                    "ip_address": pref.ip_address,
                    "user_agent": pref.user_agent,
                    "notes": pref.notes,
                    "is_valid": pref.is_valid(),
                    "is_expired": pref.is_expired(),
                }
                for pref in self.preferences
            ],
        }


# Helper functions for common consent operations
def create_default_consent_profile(customer_id: str, tenant_id: str) -> ConsentProfile:
    """Create a default consent profile with essential consent only."""
    essential_consent = ConsentPreference(
        consent_type=ConsentType.ESSENTIAL,
        status=ConsentStatus.GRANTED,
        source=ConsentSource.REGISTRATION,
        notes="Essential consent for service operation",
    )

    return ConsentProfile(
        customer_id=customer_id,
        tenant_id=tenant_id,
        preferences=[essential_consent],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def validate_gdpr_compliance(consent_profile: ConsentProfile) -> Dict[str, Any]:
    """Validate GDPR compliance for a consent profile."""
    issues = []

    # Check for essential consent
    if not consent_profile.has_valid_consent(ConsentType.ESSENTIAL):
        issues.append("Missing essential consent required for service operation")

    # Check for expired consents
    expired = consent_profile.get_expired_consents()
    if expired:
        issues.append(
            f"Expired consents found: {', '.join([c.value for c in expired])}"
        )

    # Check for proper documentation
    for pref in consent_profile.preferences:
        if pref.status == ConsentStatus.GRANTED and not pref.source:
            issues.append(
                f"Missing source documentation for {pref.consent_type.value} consent"
            )

    return {
        "is_compliant": len(issues) == 0,
        "issues": issues,
        "valid_consents": consent_profile.get_valid_consents(),
        "expired_consents": expired,
        "last_updated": consent_profile.updated_at.isoformat(),
    }
