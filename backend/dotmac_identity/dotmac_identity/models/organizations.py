"""
Organization models for tenant and company management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from ..core.datetime_utils import utc_now, is_expired, expires_in_hours, expires_in_minutes
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class OrganizationType(Enum):
    """Organization type enumeration."""
    TENANT = "tenant"
    COMPANY = "company"
    DEPARTMENT = "department"
    TEAM = "team"
    RESELLER = "reseller"


class OrganizationStatus(Enum):
    """Organization status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class MemberRole(Enum):
    """Organization member role enumeration."""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"
    BILLING_ADMIN = "billing_admin"


class MemberStatus(Enum):
    """Organization member status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"


@dataclass
class Organization:
    """Organization model for tenants and companies."""
    id: UUID = field(default_factory=uuid4)
    tenant_id: str = ""

    # Basic information
    name: str = ""
    display_name: str = ""
    description: Optional[str] = None
    organization_type: OrganizationType = OrganizationType.COMPANY

    # Status
    status: OrganizationStatus = OrganizationStatus.ACTIVE

    # Hierarchy
    parent_organization_id: Optional[UUID] = None

    # Contact information
    primary_contact_id: Optional[UUID] = None
    billing_contact_id: Optional[UUID] = None

    # Settings
    settings: Dict[str, Any] = field(default_factory=dict)

    # Billing
    billing_owner_id: Optional[UUID] = None
    billing_account_id: Optional[str] = None

    # Metadata
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    # Additional data
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_active(self) -> bool:
        """Check if organization is active."""
        return self.status == OrganizationStatus.ACTIVE


@dataclass
class OrganizationMember:
    """Organization member model."""
    id: UUID = field(default_factory=uuid4)
    organization_id: UUID = field(default_factory=uuid4)
    account_id: UUID = field(default_factory=uuid4)
    tenant_id: str = ""

    # Role and permissions
    role: MemberRole = MemberRole.MEMBER
    permissions: List[str] = field(default_factory=list)

    # Status
    status: MemberStatus = MemberStatus.ACTIVE

    # Membership details
    joined_at: datetime = field(default_factory=utc_now)
    invited_at: Optional[datetime] = None
    invited_by: Optional[UUID] = None

    # Tracking
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    last_activity_at: Optional[datetime] = None

    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_active(self) -> bool:
        """Check if member is active."""
        return self.status == MemberStatus.ACTIVE

    def has_permission(self, permission: str) -> bool:
        """Check if member has specific permission."""
        return permission in self.permissions

    def is_admin(self) -> bool:
        """Check if member has admin role."""
        return self.role in [MemberRole.OWNER, MemberRole.ADMIN]
