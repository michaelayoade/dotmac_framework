"""
Tenant Super Admin schemas for multi-app platform user management.
Provides specialized schemas for tenant-level administration across multiple applications.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, field_validator, ConfigDict

from dotmac_shared.common.schemas import BaseCreateSchema, BaseUpdateSchema, BaseResponseSchema, PaginatedResponseSchema

# Multi-App Enums
class ApplicationType(str, Enum):
    """Available applications in the platform."""
    ISP = "isp"
    CRM = "crm"
    ECOMMERCE = "ecommerce"
    PROJECTS = "projects"
    ANALYTICS = "analytics"
    LMS = "lms"
    BUSINESS_INTELLIGENCE = "bi"

class UserType(str, Enum):
    """User types that can span multiple applications."""
    SUPER_ADMIN = "super_admin"  # Access to all subscribed apps
    APP_ADMIN = "app_admin"      # Admin within specific apps
    CROSS_APP_USER = "cross_app_user"  # Access to multiple apps
    APP_USER = "app_user"        # Access to single app
    CUSTOMER = "customer"        # Customer across apps
    VENDOR = "vendor"           # Vendor/supplier role
    PARTNER = "partner"         # Partner/reseller role

# Tenant Super Admin Schemas
class TenantSubscriptionSchema(BaseModel):
    """Schema for tenant application subscriptions."""
    app: ApplicationType
    plan: str = Field(..., description="Subscription plan (basic, standard, professional, enterprise)")
    features: List[str] = Field(default_factory=list, description="Enabled features for this app")
    usage_limits: Dict[str, int] = Field(default_factory=dict, description="Usage limits (users, API calls, storage)")
    is_active: bool = True
    expires_at: Optional[datetime] = None

class CrossAppRoleCreateSchema(BaseCreateSchema):
    """Schema for creating roles that span multiple applications."""
    name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = Field(None, max_length=1000)
    
    # Cross-app permissions mapping
    app_permissions: Dict[ApplicationType, List[str]] = Field(
        default_factory=dict,
        description="Permissions per app: {'isp': ['customers:read'], 'crm': ['leads:write']}"
    )
    
    # Role scope
    is_tenant_wide: bool = Field(
        default=False,
        description="Whether this role applies tenant-wide or is app-specific"
    )
    
    # Metadata
    custom_metadata: Optional[Dict[str, Any]] = None
    
    @field_validator("app_permissions")
    @classmethod
    def validate_app_permissions(cls, v: Dict[ApplicationType, List[str]]) -> Dict[ApplicationType, List[str]]:
        """Validate app permissions format."""
        for app, permissions in v.items():
            if not isinstance(permissions, list):
                raise ValueError(f"Permissions for app '{app}' must be a list")
            
            for perm in permissions:
                if not isinstance(perm, str) or ':' not in perm:
                    raise ValueError(f"Permission '{perm}' must be in format 'resource:action'")
        
        return v

class CrossAppUserCreateSchema(BaseCreateSchema):
    """Schema for creating users with cross-app access."""
    # Basic user info
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., description="User's email address")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    
    # User type and apps
    user_type: UserType = Field(default=UserType.CROSS_APP_USER)
    app_access: List[ApplicationType] = Field(
        default_factory=list,
        description="Applications this user should have access to"
    )
    
    # Cross-app role assignments
    app_roles: Dict[ApplicationType, List[str]] = Field(
        default_factory=dict,
        description="Role assignments per app: {'isp': ['customer_service'], 'crm': ['sales_rep']}"
    )
    
    # User preferences
    preferred_app: Optional[ApplicationType] = Field(
        None,
        description="Default app to show after login"
    )
    
    # Security settings
    require_mfa: bool = Field(default=False)
    force_password_change: bool = Field(default=False)
    
    @field_validator("app_access")
    @classmethod
    def validate_app_access(cls, v: List[ApplicationType]) -> List[ApplicationType]:
        """Ensure unique app access."""
        return list(set(v))

class TenantUserManagementSchema(BaseModel):
    """Comprehensive tenant user management schema."""
    tenant_id: UUID
    
    # Subscription info
    subscriptions: List[TenantSubscriptionSchema] = Field(default_factory=list)
    
    # User statistics
    user_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="User counts per app: {'isp': 150, 'crm': 45, 'total': 180}"
    )
    
    # Available permissions per app
    available_permissions: Dict[ApplicationType, List[str]] = Field(
        default_factory=dict,
        description="All available permissions per subscribed app"
    )
    
    # Tenant-wide roles
    tenant_roles: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Roles that apply across all tenant apps"
    )

class AppNavigationSchema(BaseModel):
    """Schema for app navigation and switching."""
    app: ApplicationType
    display_name: str
    url: str
    icon: str
    is_active: bool
    user_permissions: List[str] = Field(default_factory=list)
    quick_actions: List[Dict[str, str]] = Field(default_factory=list)

class CrossAppSearchSchema(BaseModel):
    """Schema for cross-app search functionality."""
    query: str = Field(..., min_length=1, max_length=500)
    apps: List[ApplicationType] = Field(default_factory=list, description="Apps to search in")
    resource_types: List[str] = Field(default_factory=list, description="Resource types to search for")
    limit: int = Field(default=20, ge=1, le=100)
    include_archived: bool = Field(default=False)

class CrossAppSearchResultSchema(BaseModel):
    """Schema for cross-app search results."""
    app: ApplicationType
    resource_type: str
    resource_id: str
    title: str
    description: Optional[str] = None
    url: str
    context: Optional[str] = None  # Additional context about the result
    relevance_score: float = Field(ge=0.0, le=1.0)
    created_at: datetime
    updated_at: Optional[datetime] = None

class TenantAnalyticsSchema(BaseModel):
    """Schema for tenant-wide analytics across apps."""
    tenant_id: UUID
    period_start: datetime
    period_end: datetime
    
    # User activity across apps
    app_usage: Dict[ApplicationType, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Usage metrics per app"
    )
    
    # Cross-app workflows
    cross_app_activities: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Activities that span multiple apps"
    )
    
    # Feature utilization
    feature_usage: Dict[str, int] = Field(
        default_factory=dict,
        description="Feature usage counts across all apps"
    )

class BulkUserOperationSchema(BaseModel):
    """Schema for bulk user operations across apps."""
    user_ids: List[UUID] = Field(..., min_length=1, max_length=1000)
    operation: str = Field(..., description="Operation to perform: assign_role, remove_role, add_app_access, etc.")
    
    # Operation parameters
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters for the operation"
    )
    
    # Scope
    target_apps: List[ApplicationType] = Field(
        default_factory=list,
        description="Apps to apply the operation to"
    )
    
    # Options
    send_notifications: bool = Field(default=True)
    apply_immediately: bool = Field(default=True)

class TenantSecurityPolicySchema(BaseModel):
    """Schema for tenant-wide security policies."""
    # Password policies
    password_min_length: int = Field(default=8, ge=8, le=128)
    password_require_uppercase: bool = Field(default=True)
    password_require_lowercase: bool = Field(default=True)
    password_require_numbers: bool = Field(default=True)
    password_require_symbols: bool = Field(default=False)
    password_history_count: int = Field(default=5, ge=0, le=20)
    
    # MFA policies
    require_mfa: bool = Field(default=False)
    mfa_apps: List[ApplicationType] = Field(
        default_factory=list,
        description="Apps that require MFA"
    )
    
    # Session policies
    session_timeout_minutes: int = Field(default=480, ge=15, le=1440)  # 8 hours default
    concurrent_sessions_limit: int = Field(default=3, ge=1, le=10)
    
    # Access policies
    ip_whitelist: List[str] = Field(default_factory=list)
    allowed_countries: List[str] = Field(default_factory=list)
    
    # Audit policies
    audit_login_attempts: bool = Field(default=True)
    audit_permission_changes: bool = Field(default=True)
    audit_cross_app_access: bool = Field(default=True)

# Response schemas
class CrossAppUserResponseSchema(BaseResponseSchema):
    """Response schema for cross-app user data."""
    username: str
    email: str
    first_name: str
    last_name: str
    user_type: UserType
    is_active: bool
    
    # App access info
    app_access: List[ApplicationType]
    app_roles: Dict[ApplicationType, List[str]]
    preferred_app: Optional[ApplicationType]
    
    # Status info
    last_login: Optional[datetime]
    mfa_enabled: bool
    
class TenantDashboardSchema(BaseModel):
    """Schema for tenant super admin dashboard."""
    tenant_info: Dict[str, Any]
    
    # Quick stats
    total_users: int
    active_sessions: int
    subscribed_apps: List[ApplicationType]
    
    # Recent activity
    recent_logins: List[Dict[str, Any]] = Field(default_factory=list)
    recent_user_changes: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Alerts and notifications
    security_alerts: List[Dict[str, Any]] = Field(default_factory=list)
    billing_alerts: List[Dict[str, Any]] = Field(default_factory=list)
    
    # App-specific dashboards
    app_dashboards: Dict[ApplicationType, Dict[str, Any]] = Field(default_factory=dict)

class AppPermissionTemplateSchema(BaseModel):
    """Schema for application permission templates."""
    app: ApplicationType
    template_name: str
    description: str
    permissions: List[str]
    is_default: bool = Field(default=False)
    role_category: str = Field(default="custom")  # system, admin, user, custom

# Audit and compliance schemas
class CrossAppAuditLogSchema(BaseModel):
    """Schema for cross-app audit logging."""
    user_id: UUID
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    source_app: Optional[ApplicationType] = None
    target_app: Optional[ApplicationType] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime