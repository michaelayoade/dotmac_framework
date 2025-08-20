"""
Portal models for portal management, customer portals, and reseller access.
"""

from dataclasses import dataclass, field
from datetime import datetime
from ..core.datetime_utils import utc_now, is_expired, expires_in_hours, expires_in_minutes
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class PortalType(Enum):
    """Portal type enumeration."""
    CUSTOMER = "customer"
    RESELLER = "reseller"
    ADMIN = "admin"
    SUPPORT = "support"


class PortalStatus(Enum):
    """Portal status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    SUSPENDED = "suspended"


class BindingStatus(Enum):
    """Portal binding status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"


class AccessLevel(Enum):
    """Access level enumeration."""
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    ADMIN = "admin"
    FULL = "full"


@dataclass
class Portal:
    """Portal model for managing portal instances."""
    id: UUID = field(default_factory=uuid4)
    tenant_id: str = ""

    # Portal identification
    portal_id: str = ""  # The "portal_id" referenced in requirements
    name: str = ""
    display_name: str = ""
    description: Optional[str] = None

    # Portal configuration
    portal_type: PortalType = PortalType.CUSTOMER
    status: PortalStatus = PortalStatus.ACTIVE

    # URLs and domains
    base_url: Optional[str] = None
    custom_domain: Optional[str] = None

    # Branding
    logo_url: Optional[str] = None
    theme_config: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_active(self) -> bool:
        """Check if portal is active."""
        return self.status == PortalStatus.ACTIVE


@dataclass
class PortalSettings:
    """Portal settings model for per-tenant portal configuration."""
    id: UUID = field(default_factory=uuid4)
    portal_id: UUID = field(default_factory=uuid4)
    tenant_id: str = ""

    # Authentication settings
    session_timeout: int = 3600  # seconds
    max_login_attempts: int = 5
    lockout_duration: int = 900  # seconds
    require_mfa: bool = False

    # Password policy
    password_min_length: int = 8
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_numbers: bool = True
    password_require_symbols: bool = False
    password_expiry_days: Optional[int] = None

    # Features
    enabled_features: List[str] = field(default_factory=list)
    disabled_features: List[str] = field(default_factory=list)

    # Customization
    custom_css: Optional[str] = None
    custom_javascript: Optional[str] = None
    custom_footer: Optional[str] = None

    # Metadata
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    # Additional settings
    settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CustomerPortalBinding:
    """Customer portal binding model for linking customers/contacts to portal accounts."""
    id: UUID = field(default_factory=uuid4)
    portal_id: UUID = field(default_factory=uuid4)
    tenant_id: str = ""

    # Binding targets
    customer_id: Optional[UUID] = None
    contact_id: Optional[UUID] = None
    account_id: Optional[UUID] = None

    # Portal account details
    portal_username: str = ""
    portal_email: str = ""

    # Status and permissions
    status: BindingStatus = BindingStatus.ACTIVE
    access_level: AccessLevel = AccessLevel.READ_WRITE
    permissions: List[str] = field(default_factory=list)

    # Login policies
    login_policies: Dict[str, Any] = field(default_factory=dict)

    # ISP-specific: credentials/attributes for Networking consumption
    published_credentials: Dict[str, Any] = field(default_factory=dict)
    published_attributes: Dict[str, Any] = field(default_factory=dict)

    # Tracking
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    last_login_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None

    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_active(self) -> bool:
        """Check if binding is active."""
        return self.status == BindingStatus.ACTIVE

    def has_permission(self, permission: str) -> bool:
        """Check if binding has specific permission."""
        return permission in self.permissions


@dataclass
class ResellerPortalAccess:
    """Reseller portal access model for supporting reseller access."""
    id: UUID = field(default_factory=uuid4)
    portal_id: UUID = field(default_factory=uuid4)
    tenant_id: str = ""

    # Reseller information
    reseller_organization_id: UUID = field(default_factory=uuid4)
    reseller_contact_id: Optional[UUID] = None
    reseller_account_id: Optional[UUID] = None

    # Access configuration
    status: BindingStatus = BindingStatus.ACTIVE
    access_level: AccessLevel = AccessLevel.READ_WRITE

    # Permissions and scope
    permissions: List[str] = field(default_factory=list)
    accessible_customers: List[UUID] = field(default_factory=list)  # Customer IDs reseller can access
    accessible_organizations: List[UUID] = field(default_factory=list)  # Org IDs reseller can access

    # Restrictions
    ip_restrictions: List[str] = field(default_factory=list)
    time_restrictions: Dict[str, Any] = field(default_factory=dict)

    # Commission and business
    commission_rate: Optional[float] = None
    territory: Optional[str] = None

    # Tracking
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    last_access_at: Optional[datetime] = None

    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_active(self) -> bool:
        """Check if reseller access is active."""
        return self.status == BindingStatus.ACTIVE

    def has_permission(self, permission: str) -> bool:
        """Check if reseller has specific permission."""
        return permission in self.permissions

    def can_access_customer(self, customer_id: UUID) -> bool:
        """Check if reseller can access specific customer."""
        return not self.accessible_customers or customer_id in self.accessible_customers
