"""
DotMac Unified User Management Service

Consolidates user lifecycle management across ISP Framework and Management Platform,
eliminating 8-10 duplicate user service implementations.

Key Components:
- UserLifecycleService: Core user operations (register, activate, update, deactivate)
- Platform Adapters: ISP and Management platform integration
- Profile Manager: User profile and preference management
- Permission Manager: User role and permission assignment
- Auth Integration: Seamless integration with dotmac_shared/auth/

Usage:
    from dotmac_shared.user_management import UserLifecycleService
    from dotmac_shared.user_management.adapters import ISPUserAdapter

    user_service = UserLifecycleService()
    isp_adapter = ISPUserAdapter(db_session, tenant_id)

    # Register new user
    user = await isp_adapter.register_user({
        "email": "user@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "user_type": "customer"
    })
"""

from .core.permission_manager import PermissionManager
from .core.profile_manager import ProfileManager
from .core.user_lifecycle_service import UserLifecycleService
from .schemas.lifecycle_schemas import (
    UserActivation,
    UserDeactivation,
    UserDeletion,
    UserLifecycleEvent,
    UserRegistration,
)
from .schemas.user_schemas import (
    UserBase,
    UserCreate,
    UserPreferences,
    UserProfile,
    UserResponse,
    UserUpdate,
)

# Version information
__version__ = "1.0.0"
__author__ = "DotMac Framework Team"

# Public API
__all__ = [
    # Core Services
    "UserLifecycleService",
    "ProfileManager",
    "PermissionManager",
    # User Schemas
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserProfile",
    "UserPreferences",
    # Lifecycle Schemas
    "UserRegistration",
    "UserActivation",
    "UserDeactivation",
    "UserDeletion",
    "UserLifecycleEvent",
    # Metadata
    "__version__",
    "__author__",
]

# Configuration defaults - Now leverages existing shared services
DEFAULT_CONFIG = {
    # Core user management settings
    "registration": {
        "email_verification_required": True,
        "phone_verification_required": False,
        "approval_required": False,
        "password_requirements": {
            "min_length": 8,
            "require_uppercase": True,
            "require_numbers": True,
            "require_symbols": True,
        },
    },
    "activation": {
        "verification_code_length": 6,
        "verification_code_expiry": 900,  # 15 minutes
        "max_verification_attempts": 5,
        "resend_cooldown": 60,  # 1 minute
    },
    "profiles": {
        "avatar_max_size": 5242880,  # 5MB
        "avatar_formats": ["jpg", "png", "webp"],
        "extended_profiles_enabled": True,
    },
    "cleanup": {"inactive_user_days": 365, "deleted_user_retention_days": 90},
    # Integration with existing shared services
    "events": {
        "enabled": True,
        "base_topic": "user_management",
        "adapter": "redis",  # Use existing event bus
        "publish_lifecycle_events": True,
    },
    "cache": {
        "enabled": True,
        "prefix": "um",  # user_management
        "default_ttl": 3600,  # 1 hour
        "adapter": "redis",  # Use existing cache service
        "tenant_isolation": True,
    },
    "notifications": {
        "enabled": True,
        "adapter": "omnichannel",  # Use existing notification service
        "templates": {
            "welcome_email": "user_welcome",
            "email_verification": "email_verify",
            "phone_verification": "phone_verify",
            "password_reset": "password_reset",
            "password_changed": "password_changed",
            "profile_updated": "profile_updated",
            "account_activated": "account_activated",
            "account_deactivated": "account_deactivated",
            "permission_granted": "permission_granted",
            "admin_welcome": "admin_welcome",
            "tenant_admin_welcome": "tenant_admin_welcome",
            "invitation": "user_invitation",
        },
    },
    "audit": {
        "enabled": True,
        "adapter": "database",  # Use existing audit logger
        "log_level": "info",
        "include_sensitive_data": False,
    },
    "health": {
        "enabled": True,
        "adapter": "prometheus",  # Use existing health reporter
        "check_interval": 30,
        "report_metrics": True,
    },
    "metrics": {
        "enabled": True,
        "adapter": "prometheus",  # Use existing metrics service
        "namespace": "user_management",
        "track_operations": True,
        "track_cache_hits": True,
    },
    # Rate limiting configuration
    "rate_limits": {
        "registration": {
            "enabled": True,
            "requests_per_minute": 5,
            "requests_per_hour": 20,
            "burst_limit": 2,
        },
        "login": {
            "enabled": True,
            "requests_per_minute": 10,
            "requests_per_hour": 100,
            "burst_limit": 3,
        },
        "password_reset": {
            "enabled": True,
            "requests_per_minute": 2,
            "requests_per_hour": 5,
            "burst_limit": 1,
        },
    },
    # Timeout configuration
    "timeouts": {
        "database": {
            "connect_timeout": 5.0,
            "read_timeout": 30.0,
            "total_timeout": 60.0,
        },
        "cache": {"connect_timeout": 2.0, "read_timeout": 5.0, "total_timeout": 10.0},
        "notifications": {
            "connect_timeout": 5.0,
            "read_timeout": 15.0,
            "total_timeout": 30.0,
        },
    },
    # Default permissions configuration (eliminates hardcoding)
    "default_permissions": {
        "universal": {
            "user_management": [
                {
                    "name": "user:read",
                    "description": "View user information",
                    "scope": "resource",
                },
                {
                    "name": "user:update",
                    "description": "Update user information",
                    "scope": "resource",
                },
                {
                    "name": "user:delete",
                    "description": "Delete user",
                    "scope": "resource",
                },
                {
                    "name": "user:create",
                    "description": "Create new user",
                    "scope": "tenant",
                },
                {"name": "user:list", "description": "List users", "scope": "tenant"},
                {
                    "name": "user:search",
                    "description": "Search users",
                    "scope": "tenant",
                },
            ],
            "profile": [
                {
                    "name": "profile:read",
                    "description": "View profile",
                    "scope": "user",
                },
                {
                    "name": "profile:update",
                    "description": "Update profile",
                    "scope": "user",
                },
                {
                    "name": "profile:avatar",
                    "description": "Manage avatar",
                    "scope": "user",
                },
            ],
            "system": [
                {
                    "name": "system:admin",
                    "description": "System administration",
                    "scope": "global",
                },
                {
                    "name": "system:config",
                    "description": "System configuration",
                    "scope": "global",
                },
                {
                    "name": "system:audit",
                    "description": "View audit logs",
                    "scope": "global",
                },
                {
                    "name": "system:monitor",
                    "description": "System monitoring",
                    "scope": "global",
                },
            ],
            "api": [
                {
                    "name": "api:read",
                    "description": "API read access",
                    "scope": "tenant",
                },
                {
                    "name": "api:write",
                    "description": "API write access",
                    "scope": "tenant",
                },
                {
                    "name": "api:admin",
                    "description": "API administration",
                    "scope": "tenant",
                },
            ],
        },
        "isp_framework": {
            "customer_management": [
                {
                    "name": "customer:create",
                    "description": "Create customer",
                    "scope": "tenant",
                },
                {
                    "name": "customer:read",
                    "description": "View customer",
                    "scope": "resource",
                },
                {
                    "name": "customer:update",
                    "description": "Update customer",
                    "scope": "resource",
                },
                {
                    "name": "customer:delete",
                    "description": "Delete customer",
                    "scope": "resource",
                },
                {
                    "name": "customer:list",
                    "description": "List customers",
                    "scope": "tenant",
                },
            ],
            "service_management": [
                {
                    "name": "service:create",
                    "description": "Create service",
                    "scope": "tenant",
                },
                {
                    "name": "service:read",
                    "description": "View service",
                    "scope": "resource",
                },
                {
                    "name": "service:update",
                    "description": "Update service",
                    "scope": "resource",
                },
                {
                    "name": "service:activate",
                    "description": "Activate service",
                    "scope": "resource",
                },
                {
                    "name": "service:deactivate",
                    "description": "Deactivate service",
                    "scope": "resource",
                },
            ],
        },
        "management_platform": {
            "tenant_management": [
                {
                    "name": "tenant:create",
                    "description": "Create tenant",
                    "scope": "global",
                },
                {
                    "name": "tenant:read",
                    "description": "View tenant",
                    "scope": "resource",
                },
                {
                    "name": "tenant:update",
                    "description": "Update tenant",
                    "scope": "resource",
                },
                {
                    "name": "tenant:delete",
                    "description": "Delete tenant",
                    "scope": "resource",
                },
                {
                    "name": "tenant:list",
                    "description": "List tenants",
                    "scope": "global",
                },
            ]
        },
    },
    # Default roles configuration (eliminates hardcoding)
    "default_roles": {
        "universal": [
            {
                "name": "super_admin",
                "description": "Super Administrator",
                "permissions": ["system:*", "user:*", "profile:*", "api:*"],
                "is_system_role": True,
            },
            {
                "name": "api_user",
                "description": "API User",
                "permissions": ["api:read", "profile:read"],
                "is_system_role": True,
            },
        ],
        "isp_framework": [
            {
                "name": "isp_admin",
                "description": "ISP Administrator",
                "permissions": [
                    "user:*",
                    "customer:*",
                    "service:*",
                    "billing:*",
                    "network:*",
                ],
                "platform": "isp_framework",
                "is_system_role": True,
            },
            {
                "name": "customer",
                "description": "Customer",
                "permissions": ["profile:*", "service:read", "billing:read"],
                "platform": "isp_framework",
                "is_system_role": True,
            },
        ],
        "management_platform": [
            {
                "name": "platform_admin",
                "description": "Platform Administrator",
                "permissions": ["platform:*", "tenant:*", "user:*"],
                "platform": "management_platform",
                "is_system_role": True,
            },
            {
                "name": "tenant_admin",
                "description": "Tenant Administrator",
                "permissions": ["user:*", "api:*", "plugin:*"],
                "platform": "management_platform",
                "is_system_role": True,
            },
        ],
    },
}


def get_config():
    """Get the default user management configuration."""
    return DEFAULT_CONFIG.copy()


def create_user_service(db_session, config: dict = None) -> UserLifecycleService:
    """
    Factory function to create a configured UserLifecycleService.

    Args:
        db_session: Database session
        config: Optional configuration override

    Returns:
        Configured UserLifecycleService instance
    """
    service_config = DEFAULT_CONFIG.copy()
    if config:
        service_config.update(config)

    return UserLifecycleService(db_session, config=service_config)
