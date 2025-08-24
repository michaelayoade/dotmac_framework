"""
Organization-related models for SDKs.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
from dataclasses import dataclass


class OrganizationType(str, Enum):
    """Organization type enumeration."""
    
    COMPANY = "company"
    NONPROFIT = "nonprofit"
    GOVERNMENT = "government"
    EDUCATIONAL = "educational"
    HEALTHCARE = "healthcare"
    PARTNERSHIP = "partnership"
    OTHER = "other"


class MemberRole(str, Enum):
    """Organization member role enumeration."""
    
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    MEMBER = "member"
    VIEWER = "viewer"
    GUEST = "guest"


class OrganizationStatus(str, Enum):
    """Organization status enumeration."""
    
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"
    ARCHIVED = "archived"


@dataclass
class Organization:
    """Organization model."""
    
    id: UUID
    name: str
    display_name: Optional[str]
    organization_type: OrganizationType
    status: OrganizationStatus
    description: Optional[str]
    website: Optional[str]
    industry: Optional[str]
    size: Optional[str]
    founded_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    metadata: Optional[Dict[str, Any]] = None
    
    def __init__(self, **kwargs):
        """  Init   operation."""
        self.id = kwargs.get('id', uuid4())
        self.name = kwargs.get('name')
        self.display_name = kwargs.get('display_name') or self.name
        self.organization_type = kwargs.get('organization_type', OrganizationType.COMPANY)
        self.status = kwargs.get('status', OrganizationStatus.ACTIVE)
        self.description = kwargs.get('description')
        self.website = kwargs.get('website')
        self.industry = kwargs.get('industry')
        self.size = kwargs.get('size')
        self.founded_date = kwargs.get('founded_date')
        self.created_at = kwargs.get('created_at', datetime.utcnow())
        self.updated_at = kwargs.get('updated_at', datetime.utcnow())
        self.metadata = kwargs.get('metadata') or {}
    
    def is_active(self) -> bool:
        """Check if organization is active."""
        return self.status == OrganizationStatus.ACTIVE
    
    def suspend(self) -> None:
        """Suspend the organization."""
        self.status = OrganizationStatus.SUSPENDED
        self.updated_at = datetime.utcnow()
    
    def activate(self) -> None:
        """Activate the organization."""
        self.status = OrganizationStatus.ACTIVE
        self.updated_at = datetime.utcnow()


@dataclass
class OrganizationMember:
    """Organization member model."""
    
    id: UUID
    organization_id: UUID
    user_id: UUID
    role: MemberRole
    is_active: bool
    joined_at: datetime
    invited_at: Optional[datetime]
    invited_by: Optional[UUID]
    title: Optional[str]
    department: Optional[str]
    metadata: Optional[Dict[str, Any]] = None
    
    def __init__(self, **kwargs):
        """  Init   operation."""
        self.id = kwargs.get('id', uuid4())
        self.organization_id = kwargs.get('organization_id')
        self.user_id = kwargs.get('user_id')
        self.role = kwargs.get('role', MemberRole.MEMBER)
        self.is_active = kwargs.get('is_active', True)
        self.joined_at = kwargs.get('joined_at', datetime.utcnow())
        self.invited_at = kwargs.get('invited_at')
        self.invited_by = kwargs.get('invited_by')
        self.title = kwargs.get('title')
        self.department = kwargs.get('department')
        self.metadata = kwargs.get('metadata') or {}
    
    def has_role(self, role: MemberRole) -> bool:
        """Check if member has specific role."""
        return self.role == role
    
    def can_manage_members(self) -> bool:
        """Check if member can manage other members."""
        return self.role in [MemberRole.OWNER, MemberRole.ADMIN, MemberRole.MANAGER]
    
    def can_admin(self) -> bool:
        """Check if member has admin privileges."""
        return self.role in [MemberRole.OWNER, MemberRole.ADMIN]
    
    def promote_to_role(self, new_role: MemberRole) -> None:
        """Promote member to new role."""
        self.role = new_role
    
    def deactivate(self) -> None:
        """Deactivate member."""
        self.is_active = False