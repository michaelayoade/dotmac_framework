"""
Security utilities for authentication and authorization.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

from jose import jwt
from jose.exceptions import JWTError
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext

from config import settings

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token handler
security = HTTPBearer()


class UserRole:
    """User role constants."""
    MASTER_ADMIN = "master_admin"
    TENANT_ADMIN = "tenant_admin"
    TENANT_USER = "tenant_user"
    RESELLER = "reseller"
    SUPPORT = "support"


class Permission:
    """Permission constants."""
    # Tenant permissions
    CREATE_TENANT = "create_tenant"
    READ_TENANT = "read_tenant"
    UPDATE_TENANT = "update_tenant"
    DELETE_TENANT = "delete_tenant"
    MANAGE_ALL_TENANTS = "manage_all_tenants"
    
    # Billing permissions
    CREATE_SUBSCRIPTION = "create_subscription"
    READ_BILLING = "read_billing"
    UPDATE_BILLING = "update_billing"
    MANAGE_ALL_BILLING = "manage_all_billing"
    BILLING_READ = "billing:read"
    BILLING_WRITE = "billing:write"
    
    # Deployment permissions
    CREATE_DEPLOYMENT = "create_deployment"
    READ_DEPLOYMENT = "read_deployment"
    UPDATE_DEPLOYMENT = "update_deployment"
    DELETE_DEPLOYMENT = "delete_deployment"
    DEPLOYMENT_READ = "deployment:read"
    DEPLOYMENT_WRITE = "deployment:write"
    
    # Plugin permissions
    MANAGE_PLUGINS = "manage_plugins"
    READ_PLUGIN_ANALYTICS = "read_plugin_analytics"
    PLUGIN_READ = "plugin:read"
    PLUGIN_WRITE = "plugin:write"
    PLUGIN_INSTALL = "plugin:install"
    PLUGIN_REVIEW = "plugin:review"
    
    # Analytics permissions
    READ_TENANT_ANALYTICS = "read_tenant_analytics"
    READ_CROSS_TENANT_ANALYTICS = "read_cross_tenant_analytics"
    
    # System permissions
    MANAGE_USERS = "manage_users"
    SYSTEM_ADMIN = "system_admin"
    MONITORING_READ = "monitoring:read"
    MONITORING_WRITE = "monitoring:write"


# Role-based permissions mapping
ROLE_PERMISSIONS = {
    UserRole.MASTER_ADMIN: [
        # Full access to everything
        Permission.CREATE_TENANT,
        Permission.READ_TENANT,
        Permission.UPDATE_TENANT,
        Permission.DELETE_TENANT,
        Permission.MANAGE_ALL_TENANTS,
        Permission.MANAGE_ALL_BILLING,
        Permission.CREATE_DEPLOYMENT,
        Permission.READ_DEPLOYMENT,
        Permission.UPDATE_DEPLOYMENT,
        Permission.DELETE_DEPLOYMENT,
        Permission.MANAGE_PLUGINS,
        Permission.READ_PLUGIN_ANALYTICS,
        Permission.READ_CROSS_TENANT_ANALYTICS,
        Permission.MANAGE_USERS,
        Permission.SYSTEM_ADMIN,
        Permission.BILLING_READ,
        Permission.BILLING_WRITE,
        Permission.DEPLOYMENT_READ,
        Permission.DEPLOYMENT_WRITE,
        Permission.PLUGIN_READ,
        Permission.PLUGIN_WRITE,
        Permission.PLUGIN_INSTALL,
        Permission.PLUGIN_REVIEW,
        Permission.MONITORING_READ,
        Permission.MONITORING_WRITE,
    ],
    UserRole.TENANT_ADMIN: [
        # Own tenant management
        Permission.READ_TENANT,
        Permission.UPDATE_TENANT,
        Permission.READ_BILLING,
        Permission.UPDATE_BILLING,
        Permission.READ_DEPLOYMENT,
        Permission.UPDATE_DEPLOYMENT,
        Permission.READ_TENANT_ANALYTICS,
        Permission.MANAGE_USERS,  # Within their tenant
        Permission.BILLING_READ,
        Permission.BILLING_WRITE,
        Permission.DEPLOYMENT_READ,
        Permission.DEPLOYMENT_WRITE,
        Permission.PLUGIN_READ,
        Permission.PLUGIN_INSTALL,
        Permission.PLUGIN_REVIEW,
        Permission.MONITORING_READ,
        Permission.MONITORING_WRITE,
    ],
    UserRole.TENANT_USER: [
        # Limited tenant access
        Permission.READ_TENANT,
        Permission.READ_BILLING,
        Permission.READ_DEPLOYMENT,
        Permission.BILLING_READ,
        Permission.DEPLOYMENT_READ,
        Permission.PLUGIN_READ,
        Permission.MONITORING_READ,
    ],
    UserRole.RESELLER: [
        # Reseller-specific permissions
        Permission.CREATE_TENANT,
        Permission.READ_TENANT,
        Permission.CREATE_SUBSCRIPTION,
        Permission.READ_BILLING,
        Permission.READ_TENANT_ANALYTICS,
    ],
    UserRole.SUPPORT: [
        # Support access
        Permission.READ_TENANT,
        Permission.READ_BILLING,
        Permission.READ_DEPLOYMENT,
        Permission.READ_TENANT_ANALYTICS,
        Permission.BILLING_READ,
        Permission.DEPLOYMENT_READ,
        Permission.PLUGIN_READ,
        Permission.MONITORING_READ,
    ],
}


def get_role_permissions(role: str) -> List[str]:
    """Get permissions for a role."""
    return ROLE_PERMISSIONS.get(role, [])


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(
    data: Dict[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token."""
    to_encode = data.copy() if isinstance(data, dict) else dict(data)
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire, "type": "access"})
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.jwt_secret_key, 
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT refresh token."""
    to_encode = data.copy() if isinstance(data, dict) else dict(data)
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    
    to_encode.update({"exp": expire, "type": "refresh"})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def check_permission(user_role: str, required_permission: str) -> bool:
    """Check if user role has required permission."""
    role_permissions = ROLE_PERMISSIONS.get(user_role, [])
    return required_permission in role_permissions


def check_tenant_access(user_tenant_id: Optional[str], target_tenant_id: str, user_role: str) -> bool:
    """Check if user can access target tenant."""
    # Master admins can access all tenants
    if user_role == UserRole.MASTER_ADMIN:
        return True
    
    # Users can only access their own tenant
    return user_tenant_id == target_tenant_id


class CurrentUser:
    """Current user context."""
    
    def __init__(
        self,
        user_id: str,
        email: str,
        role: str,
        tenant_id: Optional[str] = None,
        is_active: bool = True,
        permissions: Optional[list] = None,
    ):
        self.user_id = user_id
        self.email = email
        self.role = role
        self.tenant_id = tenant_id
        self.is_active = is_active
        self.permissions = permissions or ROLE_PERMISSIONS.get(role, [])
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission."""
        return permission in self.permissions
    
    def can_access_tenant(self, tenant_id: str) -> bool:
        """Check if user can access specific tenant."""
        return check_tenant_access(self.tenant_id, tenant_id, self.role)
    
    def is_master_admin(self) -> bool:
        """Check if user is master admin."""
        return self.role == UserRole.MASTER_ADMIN
    
    def is_tenant_admin(self) -> bool:
        """Check if user is tenant admin."""
        return self.role == UserRole.TENANT_ADMIN
    
    def is_reseller(self) -> bool:
        """Check if user is reseller."""
        return self.role == UserRole.RESELLER