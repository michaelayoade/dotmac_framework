"""
Portal-related models for SDKs.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from uuid import UUID, uuid4
from dataclasses import dataclass


class AccessLevel(str, Enum):
    """Portal access levels."""
    
    READ_ONLY = "read_only"
    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"
    ADMIN = "admin"


class BindingStatus(str, Enum):
    """Portal binding status."""
    
    ACTIVE = "active"
    SUSPENDED = "suspended" 
    INACTIVE = "inactive"
    PENDING = "pending"


@dataclass
class CustomerPortalBinding:
    """Customer portal binding model."""
    
    id: UUID
    customer_id: UUID
    portal_id: UUID
    portal_username: str
    access_level: AccessLevel
    status: BindingStatus
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    
    def __init__(self, **kwargs):
        """  Init   operation."""
        self.id = kwargs.get('id', uuid4())
        self.customer_id = kwargs.get('customer_id')
        self.portal_id = kwargs.get('portal_id')
        self.portal_username = kwargs.get('portal_username')
        self.access_level = kwargs.get('access_level', AccessLevel.BASIC)
        self.status = kwargs.get('status', BindingStatus.ACTIVE)
        self.created_at = kwargs.get('created_at', datetime.utcnow())
        self.updated_at = kwargs.get('updated_at', datetime.utcnow())
        self.last_login = kwargs.get('last_login')


class PortalType(str, Enum):
    """Portal type enumeration."""
    
    CUSTOMER = "customer"
    ADMIN = "admin"
    RESELLER = "reseller"
    SUPPORT = "support"
    BILLING = "billing"
    API = "api"


class PortalStatus(str, Enum):
    """Portal status enumeration."""
    
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    SUSPENDED = "suspended"
    DEPRECATED = "deprecated"


@dataclass
class PortalSettings:
    """Portal settings model."""
    
    theme: str = "default"
    branding_logo_url: Optional[str] = None
    branding_color: str = "#007bff"
    custom_css: Optional[str] = None
    session_timeout_minutes: int = 30
    max_login_attempts: int = 5
    require_mfa: bool = False
    allowed_domains: Optional[List[str]] = None
    maintenance_message: Optional[str] = None
    custom_footer: Optional[str] = None
    
    def __init__(self, **kwargs):
        """  Init   operation."""
        self.theme = kwargs.get('theme', 'default')
        self.branding_logo_url = kwargs.get('branding_logo_url')
        self.branding_color = kwargs.get('branding_color', '#007bff')
        self.custom_css = kwargs.get('custom_css')
        self.session_timeout_minutes = kwargs.get('session_timeout_minutes', 30)
        self.max_login_attempts = kwargs.get('max_login_attempts', 5)
        self.require_mfa = kwargs.get('require_mfa', False)
        self.allowed_domains = kwargs.get('allowed_domains')
        self.maintenance_message = kwargs.get('maintenance_message')
        self.custom_footer = kwargs.get('custom_footer')


@dataclass
class Portal:
    """Portal model."""
    
    id: UUID
    name: str
    portal_type: PortalType
    status: PortalStatus
    url: str
    description: Optional[str]
    settings: PortalSettings
    created_at: datetime
    updated_at: datetime
    last_accessed_at: Optional[datetime] = None
    access_count: int = 0
    
    def __init__(self, **kwargs):
        """  Init   operation."""
        self.id = kwargs.get('id', uuid4())
        self.name = kwargs.get('name')
        self.portal_type = kwargs.get('portal_type', PortalType.CUSTOMER)
        self.status = kwargs.get('status', PortalStatus.ACTIVE)
        self.url = kwargs.get('url')
        self.description = kwargs.get('description')
        self.settings = kwargs.get('settings', PortalSettings())
        self.created_at = kwargs.get('created_at', datetime.utcnow())
        self.updated_at = kwargs.get('updated_at', datetime.utcnow())
        self.last_accessed_at = kwargs.get('last_accessed_at')
        self.access_count = kwargs.get('access_count', 0)
    
    def is_active(self) -> bool:
        """Check if portal is active."""
        return self.status == PortalStatus.ACTIVE
    
    def is_maintenance_mode(self) -> bool:
        """Check if portal is in maintenance mode."""
        return self.status == PortalStatus.MAINTENANCE
    
    def activate(self) -> None:
        """Activate the portal."""
        self.status = PortalStatus.ACTIVE
        self.updated_at = datetime.utcnow()
    
    def deactivate(self) -> None:
        """Deactivate the portal."""
        self.status = PortalStatus.INACTIVE
        self.updated_at = datetime.utcnow()
    
    def enter_maintenance(self, message: Optional[str] = None) -> None:
        """Put portal in maintenance mode."""
        self.status = PortalStatus.MAINTENANCE
        if message:
            self.settings.maintenance_message = message
        self.updated_at = datetime.utcnow()
    
    def record_access(self) -> None:
        """Record portal access."""
        self.last_accessed_at = datetime.utcnow()
        self.access_count += 1


@dataclass
class ResellerPortalAccess:
    """Reseller portal access model."""
    
    id: UUID
    reseller_id: UUID
    portal_id: UUID
    access_level: AccessLevel
    is_active: bool
    granted_at: datetime
    granted_by: UUID
    expires_at: Optional[datetime] = None
    last_accessed_at: Optional[datetime] = None
    access_count: int = 0
    
    def __init__(self, **kwargs):
        """  Init   operation."""
        self.id = kwargs.get('id', uuid4())
        self.reseller_id = kwargs.get('reseller_id')
        self.portal_id = kwargs.get('portal_id')
        self.access_level = kwargs.get('access_level', AccessLevel.BASIC)
        self.is_active = kwargs.get('is_active', True)
        self.granted_at = kwargs.get('granted_at', datetime.utcnow())
        self.granted_by = kwargs.get('granted_by')
        self.expires_at = kwargs.get('expires_at')
        self.last_accessed_at = kwargs.get('last_accessed_at')
        self.access_count = kwargs.get('access_count', 0)
    
    def is_expired(self) -> bool:
        """Check if access has expired."""
        return self.expires_at and datetime.utcnow() > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if access is valid."""
        return self.is_active and not self.is_expired()
    
    def revoke(self) -> None:
        """Revoke access."""
        self.is_active = False
    
    def record_access(self) -> None:
        """Record access."""
        self.last_accessed_at = datetime.utcnow()
        self.access_count += 1