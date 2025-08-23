"""Authentication contracts and schemas for the DotMac ISP Framework."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from .transport import RequestContext


class AuthenticationMethod(str, Enum):
    """Authentication method types."""

    PASSWORD = "password"
    JWT = "jwt"
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    LDAP = "ldap"
    SAML = "saml"
    MULTI_FACTOR = "multi_factor"


class TokenType(str, Enum):
    """Token types for authentication."""

    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"
    RESET = "reset"
    VERIFICATION = "verification"


class AuthenticationStatus(str, Enum):
    """Authentication status values."""

    SUCCESS = "success"
    FAILED = "failed"
    LOCKED = "locked"
    EXPIRED = "expired"
    PENDING = "pending"
    REQUIRES_MFA = "requires_mfa"


@dataclass
class AuthRequest:
    """Basic auth request schema."""

    username: str
    password: str
    tenant_id: Optional[str] = None
    remember_me: bool = False


@dataclass
class AuthenticationRequest:
    """Authentication request data."""

    username: str
    password: Optional[str] = None
    token: Optional[str] = None
    method: AuthenticationMethod = AuthenticationMethod.PASSWORD
    client_info: Optional[Dict[str, Any]] = None
    mfa_code: Optional[str] = None
    context: Optional[RequestContext] = None


@dataclass
class AuthenticationResponse:
    """Authentication response data."""

    status: AuthenticationStatus
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    permissions: Optional[List[str]] = None
    roles: Optional[List[str]] = None
    session_id: Optional[str] = None
    mfa_required: bool = False
    error_message: Optional[str] = None


@dataclass
class TokenValidationRequest:
    """Token validation request."""

    token: str
    token_type: TokenType = TokenType.ACCESS
    required_permissions: Optional[List[str]] = None
    context: Optional[RequestContext] = None


@dataclass
class TokenValidationResponse:
    """Token validation response."""

    valid: bool
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    permissions: Optional[List[str]] = None
    roles: Optional[List[str]] = None
    expires_at: Optional[datetime] = None
    error_message: Optional[str] = None


@dataclass
class SessionInfo:
    """Session information."""

    session_id: str
    user_id: str
    tenant_id: str
    created_at: datetime
    last_activity: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    permissions: Optional[List[str]] = None
    roles: Optional[List[str]] = None


@dataclass
class PasswordChangeRequest:
    """Password change request."""

    user_id: str
    current_password: str
    new_password: str
    context: Optional[RequestContext] = None


@dataclass
class PasswordResetRequest:
    """Password reset request."""

    email: str
    reset_url_template: Optional[str] = None
    context: Optional[RequestContext] = None


@dataclass
class MFASetupRequest:
    """Multi-factor authentication setup request."""

    user_id: str
    method: str  # "totp", "sms", "email"
    phone_number: Optional[str] = None
    context: Optional[RequestContext] = None


@dataclass
class MFAVerificationRequest:
    """Multi-factor authentication verification request."""

    user_id: str
    code: str
    method: str
    context: Optional[RequestContext] = None


@dataclass
class AuthenticationLog:
    """Authentication log entry."""

    user_id: Optional[str]
    username: str
    method: AuthenticationMethod
    status: AuthenticationStatus
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: Optional[datetime] = None
    error_details: Optional[str] = None
    tenant_id: Optional[str] = None


@dataclass
class RolePermission:
    """Role and permission mapping."""

    role: str
    permissions: List[str]
    description: Optional[str] = None
    scope: Optional[str] = None  # "tenant", "global", "resource"


@dataclass
class UserAuthProfile:
    """User authentication profile."""

    user_id: str
    username: str
    email: str
    tenant_id: str
    roles: List[str]
    permissions: List[str]
    mfa_enabled: bool = False
    mfa_methods: Optional[List[str]] = None
    last_login: Optional[datetime] = None
    password_changed_at: Optional[datetime] = None
    account_locked: bool = False
    login_attempts: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class AuthResponse:
    """Authentication response (alias for AuthenticationResponse)."""

    status: AuthenticationStatus
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    permissions: Optional[List[str]] = None
    roles: Optional[List[str]] = None
    session_id: Optional[str] = None
    mfa_required: bool = False
    error_message: Optional[str] = None


@dataclass
class AuthToken:
    """Authentication token data."""

    token: str
    token_type: TokenType
    expires_at: Optional[datetime] = None
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    permissions: Optional[List[str]] = None


@dataclass
class LogoutRequest:
    """Logout request data."""

    token: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    context: Optional[RequestContext] = None


@dataclass
class LogoutResponse:
    """Logout response data."""

    success: bool
    message: Optional[str] = None


@dataclass
class TokenRefreshRequest:
    """Token refresh request."""

    refresh_token: str
    context: Optional[RequestContext] = None


@dataclass
class TokenRefreshResponse:
    """Token refresh response."""

    access_token: str
    expires_at: datetime
    refresh_token: Optional[str] = None
