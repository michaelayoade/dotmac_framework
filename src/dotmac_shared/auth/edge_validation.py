"""
Edge JWT Validation System
Validates JWT tokens at the edge for sensitive routes with tenant-aware claims
"""

import jwt
import time
from typing import Optional, Dict, Any, List, Set
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta

from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..core.logging import get_logger
from ..tenant.identity import TenantContext
from ..api.exception_handlers import standard_exception_handler

logger = get_logger(__name__)


class RoutesSensitivity(str, Enum):
    """Route sensitivity levels for JWT validation"""
    PUBLIC = "public"          # No authentication required
    AUTHENTICATED = "authenticated"  # Valid JWT required
    SENSITIVE = "sensitive"    # Valid JWT + additional claims required
    ADMIN = "admin"           # Admin-level JWT required
    INTERNAL = "internal"     # Service-to-service tokens only


@dataclass
class JWTClaims:
    """Standardized JWT claims structure"""
    user_id: str
    tenant_id: Optional[str] = None
    email: Optional[str] = None
    roles: List[str] = None
    permissions: List[str] = None
    scopes: List[str] = None
    issued_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    issuer: str = "dotmac"
    audience: str = "dotmac-api"
    token_type: str = "access"  # access, refresh, internal
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.roles is None:
            self.roles = []
        if self.permissions is None:
            self.permissions = []
        if self.scopes is None:
            self.scopes = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ValidationResult:
    """Result of JWT validation"""
    valid: bool
    claims: Optional[JWTClaims] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    tenant_match: bool = False


class EdgeJWTValidator:
    """
    JWT validator for edge authentication with tenant-aware validation.
    
    Features:
    - Multi-tenant JWT validation
    - Route sensitivity-based requirements
    - Tenant-scoped claim validation
    - Token type differentiation (user vs service tokens)
    - Comprehensive security logging
    """
    
    def __init__(
        self,
        jwt_secret: str,
        jwt_algorithm: str = "HS256",
        token_expiry: int = 3600,  # 1 hour
        require_tenant_match: bool = True
    ):
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = jwt_algorithm
        self.token_expiry = token_expiry
        self.require_tenant_match = require_tenant_match
        
        # Route sensitivity configuration
        self.route_sensitivity = {}
        self.sensitive_path_patterns = [
            "/api/v1/admin/*",
            "/api/v1/tenants/*/sensitive/*",
            "/api/v1/billing/*",
            "/api/v1/users/*/admin/*"
        ]
        
        self.admin_path_patterns = [
            "/api/v1/admin/*",
            "/api/v1/management/*",
            "/api/v1/system/*"
        ]
        
        # HTTP Bearer security scheme
        self.bearer_scheme = HTTPBearer(auto_error=False)
    
    @standard_exception_handler
    async def validate_token(
        self, 
        token: str, 
        tenant_context: Optional[TenantContext] = None,
        required_scopes: List[str] = None
    ) -> ValidationResult:
        """
        Validate JWT token with optional tenant context validation.
        
        Args:
            token: JWT token string
            tenant_context: Current tenant context from middleware
            required_scopes: Required scopes for the operation
            
        Returns:
            ValidationResult with validation status and claims
        """
        try:
            if not token:
                return ValidationResult(
                    valid=False,
                    error="Token missing",
                    error_code="TOKEN_MISSING"
                )
            
            # Decode and validate JWT
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm],
                audience="dotmac-api",
                issuer="dotmac"
            )
            
            # Extract claims
            claims = self._extract_claims(payload)
            
            # Validate token expiry
            if claims.expires_at and claims.expires_at < datetime.utcnow():
                return ValidationResult(
                    valid=False,
                    error="Token expired",
                    error_code="TOKEN_EXPIRED"
                )
            
            # Validate tenant match if required
            tenant_match = True
            if self.require_tenant_match and tenant_context and not tenant_context.is_management:
                tenant_match = claims.tenant_id == tenant_context.tenant_id
                
                if not tenant_match:
                    logger.warning("JWT tenant mismatch", extra={
                        "token_tenant": claims.tenant_id,
                        "context_tenant": tenant_context.tenant_id,
                        "user_id": claims.user_id
                    })
            
            # Validate required scopes
            if required_scopes:
                missing_scopes = set(required_scopes) - set(claims.scopes)
                if missing_scopes:
                    return ValidationResult(
                        valid=False,
                        error=f"Missing required scopes: {list(missing_scopes)}",
                        error_code="INSUFFICIENT_SCOPES"
                    )
            
            return ValidationResult(
                valid=True,
                claims=claims,
                tenant_match=tenant_match
            )
            
        except jwt.ExpiredSignatureError:
            return ValidationResult(
                valid=False,
                error="Token expired",
                error_code="TOKEN_EXPIRED"
            )
        except jwt.InvalidTokenError as e:
            return ValidationResult(
                valid=False,
                error=f"Invalid token: {str(e)}",
                error_code="TOKEN_INVALID"
            )
        except Exception as e:
            logger.error(f"JWT validation error: {e}")
            return ValidationResult(
                valid=False,
                error="Token validation failed",
                error_code="VALIDATION_ERROR"
            )
    
    def _extract_claims(self, payload: Dict[str, Any]) -> JWTClaims:
        """Extract standardized claims from JWT payload"""
        
        issued_at = None
        expires_at = None
        
        if 'iat' in payload:
            issued_at = datetime.fromtimestamp(payload['iat'])
        if 'exp' in payload:
            expires_at = datetime.fromtimestamp(payload['exp'])
        
        return JWTClaims(
            user_id=payload.get('sub', ''),
            tenant_id=payload.get('tenant_id'),
            email=payload.get('email'),
            roles=payload.get('roles', []),
            permissions=payload.get('permissions', []),
            scopes=payload.get('scope', '').split() if payload.get('scope') else [],
            issued_at=issued_at,
            expires_at=expires_at,
            issuer=payload.get('iss', 'dotmac'),
            audience=payload.get('aud', 'dotmac-api'),
            token_type=payload.get('token_type', 'access'),
            metadata=payload.get('metadata', {})
        )
    
    def determine_route_sensitivity(self, path: str, method: str) -> RoutesSensitivity:
        """Determine sensitivity level for a given route"""
        
        # Check explicit configuration first
        route_key = f"{method} {path}"
        if route_key in self.route_sensitivity:
            return self.route_sensitivity[route_key]
        
        # Check pattern-based sensitivity
        for pattern in self.admin_path_patterns:
            if self._matches_pattern(path, pattern):
                return RoutesSensitivity.ADMIN
        
        for pattern in self.sensitive_path_patterns:
            if self._matches_pattern(path, pattern):
                return RoutesSensitivity.SENSITIVE
        
        # Default for API routes
        if path.startswith('/api/'):
            return RoutesSensitivity.AUTHENTICATED
        
        # Public by default
        return RoutesSensitivity.PUBLIC
    
    def _matches_pattern(self, path: str, pattern: str) -> bool:
        """Simple pattern matching for route sensitivity"""
        import fnmatch
        return fnmatch.fnmatch(path, pattern)
    
    def configure_route_sensitivity(self, routes: Dict[str, RoutesSensitivity]):
        """Configure specific route sensitivity levels"""
        self.route_sensitivity.update(routes)
    
    async def extract_token_from_request(self, request: Request) -> Optional[str]:
        """Extract JWT token from request headers"""
        try:
            # Try Authorization header first
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                return auth_header[7:]  # Remove 'Bearer ' prefix
            
            # Try X-Access-Token header
            token_header = request.headers.get('X-Access-Token')
            if token_header:
                return token_header
            
            # Try query parameter (less secure, for specific use cases)
            token_param = request.query_params.get('access_token')
            if token_param:
                logger.warning("Token provided via query parameter", extra={
                    "path": request.url.path,
                    "client_ip": request.client.host if request.client else None
                })
                return token_param
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to extract token from request: {e}")
            return None


class EdgeAuthMiddleware:
    """
    Authentication middleware for edge JWT validation.
    Works in conjunction with TenantMiddleware.
    """
    
    def __init__(
        self,
        jwt_validator: EdgeJWTValidator,
        skip_paths: List[str] = None,
        enforce_tenant_match: bool = True
    ):
        self.jwt_validator = jwt_validator
        self.skip_paths = skip_paths or ["/health", "/metrics", "/docs", "/openapi.json"]
        self.enforce_tenant_match = enforce_tenant_match
    
    async def __call__(self, request: Request, call_next):
        """Process authentication for incoming requests"""
        
        # Skip authentication for certain paths
        if self._should_skip_auth(request.url.path):
            return await call_next(request)
        
        # Determine route sensitivity
        sensitivity = self.jwt_validator.determine_route_sensitivity(
            request.url.path, 
            request.method
        )
        
        # Skip JWT validation for public routes
        if sensitivity == RoutesSensitivity.PUBLIC:
            return await call_next(request)
        
        # Extract token
        token = await self.jwt_validator.extract_token_from_request(request)
        
        # Get tenant context from request state (set by TenantMiddleware)
        tenant_context = getattr(request.state, 'tenant', None)
        
        # Determine required scopes based on sensitivity
        required_scopes = self._get_required_scopes(sensitivity, request.url.path)
        
        # Validate token
        validation_result = await self.jwt_validator.validate_token(
            token or "",
            tenant_context=tenant_context,
            required_scopes=required_scopes
        )
        
        if not validation_result.valid:
            logger.warning("JWT validation failed", extra={
                "error": validation_result.error,
                "error_code": validation_result.error_code,
                "path": request.url.path,
                "method": request.method,
                "client_ip": request.client.host if request.client else None
            })
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=validation_result.error,
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Check tenant match for non-management routes
        if (self.enforce_tenant_match and 
            tenant_context and 
            not tenant_context.is_management and 
            not validation_result.tenant_match):
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token tenant does not match request context"
            )
        
        # Set authentication context in request state
        request.state.auth_claims = validation_result.claims
        request.state.auth_valid = True
        
        return await call_next(request)
    
    def _should_skip_auth(self, path: str) -> bool:
        """Check if path should skip authentication"""
        return any(path.startswith(skip_path) for skip_path in self.skip_paths)
    
    def _get_required_scopes(self, sensitivity: RoutesSensitivity, path: str) -> List[str]:
        """Get required scopes based on route sensitivity"""
        if sensitivity == RoutesSensitivity.ADMIN:
            return ["admin"]
        elif sensitivity == RoutesSensitivity.SENSITIVE:
            return ["api:read", "api:write"]
        elif sensitivity == RoutesSensitivity.AUTHENTICATED:
            return ["api:read"]
        else:
            return []


# Global validator instance (should be configured per application)
edge_jwt_validator = None


def get_jwt_validator() -> EdgeJWTValidator:
    """Get the configured JWT validator"""
    global edge_jwt_validator
    if not edge_jwt_validator:
        # This should be configured during application startup
        raise RuntimeError("JWT validator not configured")
    return edge_jwt_validator


def configure_jwt_validator(
    jwt_secret: str,
    jwt_algorithm: str = "HS256", 
    **kwargs
) -> EdgeJWTValidator:
    """Configure the global JWT validator"""
    global edge_jwt_validator
    edge_jwt_validator = EdgeJWTValidator(
        jwt_secret=jwt_secret,
        jwt_algorithm=jwt_algorithm,
        **kwargs
    )
    return edge_jwt_validator