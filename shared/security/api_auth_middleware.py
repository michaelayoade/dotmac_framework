"""
Comprehensive API Authentication and Authorization Middleware
Provides JWT validation, role-based access control, and permission enforcement

SECURITY: This middleware ensures all API requests are properly authenticated
and authorized before reaching application endpoints
"""

import logging
import jwt
import time
from typing import Optional, List, Dict, Any, Callable, Set
from datetime import datetime, timezone, timedelta
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class AuthenticationError(HTTPException):
    """Custom authentication error"""
    def __init__(self, detail: str = "Authentication required"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

class AuthorizationError(HTTPException):
    """Custom authorization error"""  
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

class UserRole(str, Enum):
    """User roles for role-based access control"""
    SUPER_ADMIN = "super_admin"
    TENANT_ADMIN = "tenant_admin"
    MANAGER = "manager"
    TECHNICIAN = "technician"
    SUPPORT = "support"
    SALES = "sales"
    CUSTOMER = "customer"
    API_CLIENT = "api_client"
    READONLY = "readonly"

@dataclass
class AuthUser:
    """Authenticated user information"""
    user_id: str
    email: str
    tenant_id: Optional[str]
    roles: List[str]
    permissions: List[str]
    is_active: bool
    is_verified: bool
    expires_at: Optional[datetime] = None
    session_id: Optional[str] = None
    client_type: Optional[str] = None

@dataclass
class APIPermission:
    """API permission definition"""
    resource: str  # e.g., "customers", "billing", "analytics"
    action: str   # e.g., "read", "write", "delete", "admin"
    scope: Optional[str] = None  # e.g., "own", "tenant", "global"

class JWTTokenValidator:
    """
    JWT token validation with comprehensive security checks
    """
    
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        verify_exp: bool = True,
        verify_iat: bool = True,
        verify_nbf: bool = True,
        leeway: int = 10,  # seconds
        max_token_age: int = 3600,  # 1 hour
        require_tenant_context: bool = True
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.verify_exp = verify_exp
        self.verify_iat = verify_iat
        self.verify_nbf = verify_nbf
        self.leeway = leeway
        self.max_token_age = max_token_age
        self.require_tenant_context = require_tenant_context
        
        # Token blacklist (in production, use Redis)
        self.blacklisted_tokens: Set[str] = set()
    
    async def validate_token(self, token: str) -> AuthUser:
        """
        Validate JWT token and extract user information
        """
        try:
            # Check if token is blacklisted
            if self.is_token_blacklisted(token):
                raise AuthenticationError("Token has been revoked")
            
            # Decode and validate JWT
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={
                    "verify_exp": self.verify_exp,
                    "verify_iat": self.verify_iat,
                    "verify_nbf": self.verify_nbf,
                },
                leeway=self.leeway
            )
            
            # Extract required claims
            user_id = payload.get("sub")
            if not user_id:
                raise AuthenticationError("Invalid token: missing user ID")
            
            email = payload.get("email")
            if not email:
                raise AuthenticationError("Invalid token: missing email")
            
            # Extract optional claims
            tenant_id = payload.get("tenant_id")
            if self.require_tenant_context and not tenant_id:
                raise AuthenticationError("Invalid token: missing tenant context")
            
            roles = payload.get("roles", [])
            permissions = payload.get("permissions", [])
            is_active = payload.get("is_active", True)
            is_verified = payload.get("is_verified", True)
            session_id = payload.get("session_id")
            client_type = payload.get("client_type")
            
            # Check token age
            issued_at = payload.get("iat")
            if issued_at and self.max_token_age:
                token_age = time.time() - issued_at
                if token_age > self.max_token_age:
                    raise AuthenticationError("Token has expired")
            
            # Check if user is active
            if not is_active:
                raise AuthenticationError("User account is inactive")
            
            # Check if email is verified (for certain operations)
            if not is_verified:
                logger.warning(f"Unverified user accessing API: {email}")
            
            # Extract expiration
            expires_at = None
            if payload.get("exp"):
                expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
            
            return AuthUser(
                user_id=user_id,
                email=email,
                tenant_id=tenant_id,
                roles=roles,
                permissions=permissions,
                is_active=is_active,
                is_verified=is_verified,
                expires_at=expires_at,
                session_id=session_id,
                client_type=client_type
            )
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {str(e)}")
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise AuthenticationError("Token validation failed")
    
    def is_token_blacklisted(self, token: str) -> bool:
        """Check if token is in blacklist"""
        # In production, this would check Redis
        return token in self.blacklisted_tokens
    
    def blacklist_token(self, token: str) -> None:
        """Add token to blacklist"""
        # In production, this would use Redis with TTL
        self.blacklisted_tokens.add(token)

class RoleBasedAccessControl:
    """
    Role-based access control system
    """
    
    def __init__(self):
        # Define role hierarchy (higher roles inherit permissions from lower roles)
        self.role_hierarchy = {
            UserRole.SUPER_ADMIN: [
                UserRole.TENANT_ADMIN, UserRole.MANAGER, UserRole.TECHNICIAN,
                UserRole.SUPPORT, UserRole.SALES, UserRole.API_CLIENT, UserRole.READONLY
            ],
            UserRole.TENANT_ADMIN: [
                UserRole.MANAGER, UserRole.TECHNICIAN, UserRole.SUPPORT,
                UserRole.SALES, UserRole.API_CLIENT, UserRole.READONLY
            ],
            UserRole.MANAGER: [UserRole.TECHNICIAN, UserRole.SUPPORT, UserRole.SALES, UserRole.READONLY],
            UserRole.TECHNICIAN: [UserRole.READONLY],
            UserRole.SUPPORT: [UserRole.READONLY],
            UserRole.SALES: [UserRole.READONLY],
            UserRole.API_CLIENT: [UserRole.READONLY],
            UserRole.READONLY: []
        }
        
        # Define permissions for each role
        self.role_permissions = {
            UserRole.SUPER_ADMIN: ["*"],  # All permissions
            UserRole.TENANT_ADMIN: [
                "tenant.admin", "users.manage", "billing.manage", "services.manage",
                "support.manage", "analytics.view", "system.configure"
            ],
            UserRole.MANAGER: [
                "users.view", "billing.view", "services.view", "support.manage",
                "analytics.view", "reports.generate"
            ],
            UserRole.TECHNICIAN: [
                "services.manage", "tickets.manage", "customers.view",
                "inventory.manage", "field_ops.manage"
            ],
            UserRole.SUPPORT: [
                "tickets.manage", "customers.view", "services.view", "billing.view"
            ],
            UserRole.SALES: [
                "customers.manage", "services.view", "billing.view", "analytics.view"
            ],
            UserRole.API_CLIENT: [
                "api.read", "api.write"  # Controlled API access
            ],
            UserRole.READONLY: [
                "dashboard.view", "profile.view"
            ]
        }
    
    def get_effective_permissions(self, roles: List[str]) -> Set[str]:
        """Get all effective permissions for given roles"""
        permissions = set()
        
        for role_str in roles:
            try:
                role = UserRole(role_str)
                
                # Add direct permissions
                role_perms = self.role_permissions.get(role, [])
                permissions.update(role_perms)
                
                # Add inherited permissions
                inherited_roles = self.role_hierarchy.get(role, [])
                for inherited_role in inherited_roles:
                    inherited_perms = self.role_permissions.get(inherited_role, [])
                    permissions.update(inherited_perms)
                    
            except ValueError:
                logger.warning(f"Unknown role: {role_str}")
        
        return permissions
    
    def has_permission(self, user: AuthUser, required_permission: str) -> bool:
        """Check if user has required permission"""
        if not user.is_active:
            return False
        
        # Super admin has all permissions
        if "*" in user.permissions:
            return True
        
        # Get effective permissions from roles
        effective_permissions = self.get_effective_permissions(user.roles)
        
        # Combine with explicit permissions
        all_permissions = effective_permissions.union(set(user.permissions))
        
        # Check for wildcard or exact match
        return "*" in all_permissions or required_permission in all_permissions
    
    def has_role(self, user: AuthUser, required_role: str) -> bool:
        """Check if user has required role"""
        if not user.is_active:
            return False
        
        return required_role in user.roles or UserRole.SUPER_ADMIN.value in user.roles

class APIAuthenticationMiddleware:
    """
    FastAPI middleware for API authentication and authorization
    """
    
    def __init__(
        self,
        app,
        jwt_validator: JWTTokenValidator,
        rbac: RoleBasedAccessControl,
        exempt_paths: Optional[List[str]] = None,
        require_auth: bool = True,
        extract_from_cookie: bool = True,
        cookie_name: str = "access_token"
    ):
        self.app = app
        self.jwt_validator = jwt_validator
        self.rbac = rbac
        self.exempt_paths = exempt_paths or [
            '/docs', '/redoc', '/openapi.json', '/health', '/api/auth/login'
        ]
        self.require_auth = require_auth
        self.extract_from_cookie = extract_from_cookie
        self.cookie_name = cookie_name
        
        # Bearer token security
        self.bearer_security = HTTPBearer(auto_error=False)
    
    def is_exempt(self, path: str) -> bool:
        """Check if path is exempt from authentication"""
        return any(path.startswith(exempt_path) for exempt_path in self.exempt_paths)
    
    async def extract_token(self, request: Request) -> Optional[str]:
        """Extract token from request (header or cookie)"""
        token = None
        
        # Try Authorization header first
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
        
        # Fall back to cookie if enabled
        elif self.extract_from_cookie:
            token = request.cookies.get(self.cookie_name)
        
        return token
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)
            
            # Skip exempt paths
            if self.is_exempt(request.url.path):
                await self.app(scope, receive, send)
                return
            
            try:
                # Extract token
                token = await self.extract_token(request)
                
                if not token:
                    if self.require_auth:
                        error_response = JSONResponse(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            content={"error": "Authentication required", "message": "No token provided"},
                            headers={"WWW-Authenticate": "Bearer"}
                        )
                        await error_response(scope, receive, send)
                        return
                    else:
                        # Allow unauthenticated access
                        await self.app(scope, receive, send)
                        return
                
                # Validate token
                auth_user = await self.jwt_validator.validate_token(token)
                
                # Add user to request state
                request.state.auth_user = auth_user
                request.state.authenticated = True
                
                # Add tenant context
                if auth_user.tenant_id:
                    request.state.tenant_id = auth_user.tenant_id
                
                logger.debug(f"Authenticated user: {auth_user.email} (tenant: {auth_user.tenant_id})")
                
                await self.app(scope, receive, send)
                
            except AuthenticationError as e:
                error_response = JSONResponse(
                    status_code=e.status_code,
                    content={"error": "Authentication failed", "message": e.detail},
                    headers={"WWW-Authenticate": "Bearer"}
                )
                await error_response(scope, receive, send)
            except Exception as e:
                logger.error(f"Authentication middleware error: {e}")
                error_response = JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={"error": "Internal server error", "message": "Authentication system unavailable"}
                )
                await error_response(scope, receive, send)
        else:
            await self.app(scope, receive, send)

# Dependency functions for FastAPI
def get_current_user(request: Request) -> AuthUser:
    """Get current authenticated user from request state"""
    if not hasattr(request.state, "auth_user"):
        raise AuthenticationError("No authenticated user found")
    
    return request.state.auth_user

def get_current_active_user(current_user: AuthUser = Depends(get_current_user)) -> AuthUser:
    """Get current active user"""
    if not current_user.is_active:
        raise AuthenticationError("User account is inactive")
    
    return current_user

def get_current_verified_user(current_user: AuthUser = Depends(get_current_user)) -> AuthUser:
    """Get current verified user"""
    if not current_user.is_verified:
        raise AuthenticationError("User email not verified")
    
    return current_user

# Permission checking functions
def require_permission(permission: str):
    """Dependency to require specific permission"""
    def permission_checker(
        current_user: AuthUser = Depends(get_current_active_user),
        rbac: RoleBasedAccessControl = Depends()
    ) -> AuthUser:
        if not rbac.has_permission(current_user, permission):
            raise AuthorizationError(f"Permission required: {permission}")
        return current_user
    
    return permission_checker

def require_role(role: str):
    """Dependency to require specific role"""
    def role_checker(
        current_user: AuthUser = Depends(get_current_active_user),
        rbac: RoleBasedAccessControl = Depends()
    ) -> AuthUser:
        if not rbac.has_role(current_user, role):
            raise AuthorizationError(f"Role required: {role}")
        return current_user
    
    return role_checker

# Factory functions
def create_jwt_validator(
    secret_key: str,
    **kwargs
) -> JWTTokenValidator:
    """Create JWT token validator"""
    return JWTTokenValidator(secret_key=secret_key, **kwargs)

def create_api_auth_middleware(
    jwt_validator: JWTTokenValidator,
    rbac: Optional[RoleBasedAccessControl] = None,
    **kwargs
) -> Callable:
    """Factory for creating API authentication middleware"""
    rbac = rbac or RoleBasedAccessControl()
    
    def middleware_factory(app):
        return APIAuthenticationMiddleware(
            app=app,
            jwt_validator=jwt_validator,
            rbac=rbac,
            **kwargs
        )
    
    return middleware_factory