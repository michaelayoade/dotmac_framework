"""
Unified Portal Authentication System

Provides consistent authentication flow across all portals with proper
portal type detection and routing.
"""

import logging
from enum import Enum
from typing import Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from pydantic import BaseModel
import jwt

from dotmac_isp.core.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class PortalType(str, Enum):
    """Portal types for authentication routing."""
    ADMIN = "admin"
    CUSTOMER = "customer" 
    RESELLER = "reseller"
    TECHNICIAN = "technician"


class AuthenticationMode(str, Enum):
    """Authentication modes supported by portals."""
    USERNAME_PASSWORD = "username_password"
    PORTAL_ID_PASSWORD = "portal_id_password"
    EMAIL_PASSWORD = "email_password"
    MFA_REQUIRED = "mfa_required"
    SSO = "sso"


class PortalAuthConfig(BaseModel):
    """Portal authentication configuration."""
    portal_type: PortalType
    auth_modes: list[AuthenticationMode]
    require_mfa: bool = False
    session_timeout_minutes: int = 480  # 8 hours
    allow_remember_device: bool = True
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15


class AuthenticationRequest(BaseModel):
    """Unified authentication request."""
    portal_type: PortalType
    auth_mode: AuthenticationMode
    
    # Credentials (one set required based on auth_mode)
    username: Optional[str] = None
    email: Optional[str] = None
    portal_id: Optional[str] = None
    password: str
    
    # MFA
    mfa_code: Optional[str] = None
    
    # Session preferences
    remember_device: bool = False
    session_timeout_override: Optional[int] = None


class AuthenticationResponse(BaseModel):
    """Unified authentication response."""
    success: bool
    portal_type: PortalType
    user_id: UUID
    user_type: str
    access_token: str
    refresh_token: str
    session_id: str
    expires_at: datetime
    
    # User info
    user_info: Dict[str, Any]
    permissions: list[str]
    tenant_id: Optional[UUID] = None
    
    # Portal routing
    portal_url: str
    redirect_url: Optional[str] = None
    
    # MFA/Security
    requires_password_change: bool = False
    mfa_enabled: bool = False
    device_remembered: bool = False


class AuthenticationError(HTTPException):
    """Custom authentication error with portal context."""
    
    def __init__(
        self, 
        detail: str, 
        portal_type: PortalType,
        error_code: str = "AUTH_FAILED",
        status_code: int = status.HTTP_401_UNAUTHORIZED
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.portal_type = portal_type
        self.error_code = error_code


class PortalAuthManager:
    """Unified portal authentication manager."""
    
    # Portal configurations
    PORTAL_CONFIGS = {
        PortalType.ADMIN: PortalAuthConfig(
            portal_type=PortalType.ADMIN,
            auth_modes=[AuthenticationMode.USERNAME_PASSWORD, AuthenticationMode.EMAIL_PASSWORD],
            require_mfa=True,
            session_timeout_minutes=240,  # 4 hours for admins
            max_login_attempts=3
        ),
        PortalType.CUSTOMER: PortalAuthConfig(
            portal_type=PortalType.CUSTOMER,
            auth_modes=[AuthenticationMode.PORTAL_ID_PASSWORD, AuthenticationMode.EMAIL_PASSWORD],
            require_mfa=False,
            session_timeout_minutes=720,  # 12 hours for customers
            allow_remember_device=True
        ),
        PortalType.RESELLER: PortalAuthConfig(
            portal_type=PortalType.RESELLER,
            auth_modes=[AuthenticationMode.EMAIL_PASSWORD, AuthenticationMode.USERNAME_PASSWORD],
            require_mfa=False,
            session_timeout_minutes=480,  # 8 hours for resellers
        ),
        PortalType.TECHNICIAN: PortalAuthConfig(
            portal_type=PortalType.TECHNICIAN,
            auth_modes=[AuthenticationMode.USERNAME_PASSWORD],
            require_mfa=False,
            session_timeout_minutes=600,  # 10 hours for field work
            allow_remember_device=True
        )
    }
    
    # Portal URLs
    PORTAL_URLS = {
        PortalType.ADMIN: "https://admin.dotmac-isp.local:3000",
        PortalType.CUSTOMER: "https://customer.dotmac-isp.local:3001", 
        PortalType.RESELLER: "https://reseller.dotmac-isp.local:3003",
        PortalType.TECHNICIAN: "https://technician.dotmac-isp.local:3004"
    }
    
    def __init__(self):
        """  Init   operation."""
        self.failed_attempts: Dict[str, Dict[str, Any]] = {}
    
    def detect_portal_type_from_request(self, request) -> Optional[PortalType]:
        """Detect portal type from request headers, host, or cookies."""
        try:
            # Check Host header first
            host = request.headers.get('host', '').lower()
            if 'admin.' in host or host.endswith(':3000'):
                return PortalType.ADMIN
            elif 'customer.' in host or host.endswith(':3001'):
                return PortalType.CUSTOMER
            elif 'reseller.' in host or host.endswith(':3003'):
                return PortalType.RESELLER
            elif 'technician.' in host or host.endswith(':3004'):
                return PortalType.TECHNICIAN
            
            # Check for portal type in cookies
            portal_cookie = request.cookies.get('portal-type')
            if portal_cookie:
                try:
                    return PortalType(portal_cookie)
                except ValueError:
                    pass
            
            # Check User-Agent for mobile (technician app)
            user_agent = request.headers.get('user-agent', '').lower()
            if 'mobile' in user_agent or 'app' in user_agent:
                return PortalType.TECHNICIAN
                
            return None
            
        except Exception as e:
            logger.warning(f"Failed to detect portal type: {e}")
            return None
    
    def validate_auth_request(
        self, 
        auth_request: AuthenticationRequest
    ) -> Tuple[bool, Optional[str]]:
        """Validate authentication request for portal type."""
        try:
            config = self.PORTAL_CONFIGS.get(auth_request.portal_type)
            if not config:
                return False, f"Invalid portal type: {auth_request.portal_type}"
            
            # Check if auth mode is supported
            if auth_request.auth_mode not in config.auth_modes:
                return False, f"Authentication mode {auth_request.auth_mode} not supported for {auth_request.portal_type} portal"
            
            # Validate credentials based on auth mode
            if auth_request.auth_mode == AuthenticationMode.USERNAME_PASSWORD:
                if not auth_request.username:
                    return False, "Username is required"
            elif auth_request.auth_mode == AuthenticationMode.EMAIL_PASSWORD:
                if not auth_request.email:
                    return False, "Email is required"
            elif auth_request.auth_mode == AuthenticationMode.PORTAL_ID_PASSWORD:
                if not auth_request.portal_id:
                    return False, "Portal ID is required"
                if auth_request.portal_type != PortalType.CUSTOMER:
                    return False, "Portal ID authentication only available for customer portal"
            
            if not auth_request.password:
                return False, "Password is required"
            
            # Check for rate limiting
            identifier = auth_request.username or auth_request.email or auth_request.portal_id
            if self._is_rate_limited(identifier, auth_request.portal_type):
                return False, f"Too many failed attempts. Please try again in {config.lockout_duration_minutes} minutes."
            
            return True, None
            
        except Exception as e:
            logger.error(f"Auth request validation error: {e}")
            return False, "Authentication validation failed"
    
    def _is_rate_limited(self, identifier: str, portal_type: PortalType) -> bool:
        """Check if user is rate limited due to failed attempts."""
        if not identifier:
            return False
        
        key = f"{portal_type}:{identifier}"
        attempts = self.failed_attempts.get(key, {})
        
        if not attempts:
            return False
        
        config = self.PORTAL_CONFIGS[portal_type]
        
        # Check if lockout period has expired
        last_attempt = attempts.get('last_attempt')
        if last_attempt:
            lockout_expires = last_attempt + timedelta(minutes=config.lockout_duration_minutes)
            if datetime.utcnow() > lockout_expires:
                # Clear expired lockout
                self.failed_attempts.pop(key, None)
                return False
        
        # Check attempt count
        return attempts.get('count', 0) >= config.max_login_attempts
    
    def record_failed_attempt(self, identifier: str, portal_type: PortalType):
        """Record a failed login attempt."""
        if not identifier:
            return
        
        key = f"{portal_type}:{identifier}"
        attempts = self.failed_attempts.get(key, {'count': 0})
        attempts['count'] += 1
        attempts['last_attempt'] = datetime.utcnow()
        self.failed_attempts[key] = attempts
    
    def clear_failed_attempts(self, identifier: str, portal_type: PortalType):
        """Clear failed attempts after successful login."""
        if not identifier:
            return
        
        key = f"{portal_type}:{identifier}"
        self.failed_attempts.pop(key, None)
    
    def generate_session_token(
        self, 
        user_id: UUID,
        portal_type: PortalType,
        user_info: Dict[str, Any],
        session_timeout_override: Optional[int] = None
    ) -> Tuple[str, str, datetime]:
        """Generate access and refresh tokens for session."""
        config = self.PORTAL_CONFIGS[portal_type]
        timeout_minutes = session_timeout_override or config.session_timeout_minutes
        
        expires_at = datetime.utcnow() + timedelta(minutes=timeout_minutes)
        
        # Access token payload
        access_payload = {
            'user_id': str(user_id),
            'portal_type': portal_type.value,
            'user_type': user_info.get('user_type', 'unknown'),
            'tenant_id': str(user_info.get('tenant_id')) if user_info.get('tenant_id') else None,
            'exp': expires_at.timestamp(),
            'iat': datetime.utcnow().timestamp(),
            'session_id': f"{portal_type.value}_{user_id}_{datetime.utcnow().timestamp()}"
        }
        
        # Refresh token (longer lived)
        refresh_expires = datetime.utcnow() + timedelta(days=7)
        refresh_payload = {
            'user_id': str(user_id),
            'portal_type': portal_type.value,
            'exp': refresh_expires.timestamp(),
            'iat': datetime.utcnow().timestamp(),
            'type': 'refresh'
        }
        
        access_token = jwt.encode(access_payload, settings.SECRET_KEY, algorithm="HS256")
        refresh_token = jwt.encode(refresh_payload, settings.SECRET_KEY, algorithm="HS256")
        
        return access_token, refresh_token, expires_at
    
    def get_portal_url(self, portal_type: PortalType, redirect_path: Optional[str] = None) -> str:
        """Get portal URL with optional redirect path."""
        base_url = self.PORTAL_URLS.get(portal_type, "")
        if redirect_path:
            return f"{base_url}{redirect_path}"
        return base_url
    
    async def authenticate_user(
        self, 
        auth_request: AuthenticationRequest
    ) -> AuthenticationResponse:
        """Main authentication method - integrates with existing auth systems."""
        try:
            # Validate request
            is_valid, error_msg = self.validate_auth_request(auth_request)
            if not is_valid:
                raise AuthenticationError(
                    detail=error_msg, 
                    portal_type=auth_request.portal_type,
                    error_code="VALIDATION_FAILED"
                )
            
            # Delegate to portal-specific authentication
            user_info = await self._authenticate_by_portal_type(auth_request)
            
            if not user_info:
                # Record failed attempt
                identifier = auth_request.username or auth_request.email or auth_request.portal_id
                self.record_failed_attempt(identifier, auth_request.portal_type)
                
                raise AuthenticationError(
                    detail="Invalid credentials",
                    portal_type=auth_request.portal_type,
                    error_code="INVALID_CREDENTIALS"
                )
            
            # Clear failed attempts on success
            identifier = auth_request.username or auth_request.email or auth_request.portal_id
            self.clear_failed_attempts(identifier, auth_request.portal_type)
            
            # Generate tokens
            access_token, refresh_token, expires_at = self.generate_session_token(
                user_id=user_info['user_id'],
                portal_type=auth_request.portal_type,
                user_info=user_info,
                session_timeout_override=auth_request.session_timeout_override
            )
            
            # Build response
            return AuthenticationResponse(
                success=True,
                portal_type=auth_request.portal_type,
                user_id=user_info['user_id'],
                user_type=user_info['user_type'],
                access_token=access_token,
                refresh_token=refresh_token,
                session_id=f"{auth_request.portal_type.value}_{user_info['user_id']}_{datetime.utcnow().timestamp()}",
                expires_at=expires_at,
                user_info=user_info,
                permissions=user_info.get('permissions', []),
                tenant_id=user_info.get('tenant_id'),
                portal_url=self.get_portal_url(auth_request.portal_type),
                requires_password_change=user_info.get('requires_password_change', False),
                mfa_enabled=user_info.get('mfa_enabled', False),
                device_remembered=auth_request.remember_device
            )
            
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise AuthenticationError(
                detail="Authentication system error",
                portal_type=auth_request.portal_type,
                error_code="SYSTEM_ERROR"
            )
    
    async def _authenticate_by_portal_type(
        self, 
        auth_request: AuthenticationRequest
    ) -> Optional[Dict[str, Any]]:
        """Delegate to portal-specific authentication systems."""
        # Import here to avoid circular dependencies
        from dotmac_isp.shared.auth import (
            authenticate_admin_user,
            authenticate_customer_by_portal_id,
            authenticate_customer_by_email,
            authenticate_reseller_user,
            authenticate_technician_user
        )
        
        try:
            if auth_request.portal_type == PortalType.ADMIN:
                if auth_request.auth_mode == AuthenticationMode.USERNAME_PASSWORD:
                    return await authenticate_admin_user(auth_request.username, auth_request.password)
                elif auth_request.auth_mode == AuthenticationMode.EMAIL_PASSWORD:
                    return await authenticate_admin_user(auth_request.email, auth_request.password, use_email=True)
            
            elif auth_request.portal_type == PortalType.CUSTOMER:
                if auth_request.auth_mode == AuthenticationMode.PORTAL_ID_PASSWORD:
                    return await authenticate_customer_by_portal_id(auth_request.portal_id, auth_request.password)
                elif auth_request.auth_mode == AuthenticationMode.EMAIL_PASSWORD:
                    return await authenticate_customer_by_email(auth_request.email, auth_request.password)
            
            elif auth_request.portal_type == PortalType.RESELLER:
                if auth_request.auth_mode == AuthenticationMode.EMAIL_PASSWORD:
                    return await authenticate_reseller_user(auth_request.email, auth_request.password)
                elif auth_request.auth_mode == AuthenticationMode.USERNAME_PASSWORD:
                    return await authenticate_reseller_user(auth_request.username, auth_request.password, use_username=True)
            
            elif auth_request.portal_type == PortalType.TECHNICIAN:
                if auth_request.auth_mode == AuthenticationMode.USERNAME_PASSWORD:
                    return await authenticate_technician_user(auth_request.username, auth_request.password)
            
            return None
            
        except Exception as e:
            logger.error(f"Portal-specific authentication failed: {e}")
            return None


# Global instance
portal_auth_manager = PortalAuthManager()