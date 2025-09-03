"""
Authentication Exceptions

Comprehensive exception classes for the DotMac authentication system.
"""

from typing import Any, Dict, Optional


class AuthError(Exception):
    """Base authentication error"""
    
    def __init__(
        self, 
        message: str = "Authentication failed",
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code or "AUTH_ERROR"
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses"""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details
        }


class TokenError(AuthError):
    """Base token-related error"""
    
    def __init__(
        self, 
        message: str = "Token error",
        error_code: str = "TOKEN_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, details)


class TokenExpired(TokenError):
    """Token has expired"""
    
    def __init__(
        self, 
        message: str = "Token has expired",
        expired_at: Optional[str] = None
    ):
        details = {"expired_at": expired_at} if expired_at else {}
        super().__init__(message, "TOKEN_EXPIRED", details)


class TokenNotFound(TokenError):
    """Token not provided or found"""
    
    def __init__(self, message: str = "Authentication token required"):
        super().__init__(message, "TOKEN_NOT_FOUND")


class InvalidToken(TokenError):
    """Token is invalid or malformed"""
    
    def __init__(
        self, 
        message: str = "Invalid authentication token",
        reason: Optional[str] = None
    ):
        details = {"reason": reason} if reason else {}
        super().__init__(message, "INVALID_TOKEN", details)


class InvalidSignature(TokenError):
    """Token signature verification failed"""
    
    def __init__(self, message: str = "Token signature verification failed"):
        super().__init__(message, "INVALID_SIGNATURE")


class InvalidAlgorithm(TokenError):
    """Unsupported or invalid JWT algorithm"""
    
    def __init__(
        self, 
        message: str = "Invalid JWT algorithm",
        algorithm: Optional[str] = None
    ):
        details = {"algorithm": algorithm} if algorithm else {}
        super().__init__(message, "INVALID_ALGORITHM", details)


class InvalidAudience(TokenError):
    """Token audience claim does not match expected value"""
    
    def __init__(
        self, 
        message: str = "Token audience mismatch",
        expected: Optional[str] = None,
        actual: Optional[str] = None
    ):
        details = {}
        if expected:
            details["expected_audience"] = expected
        if actual:
            details["actual_audience"] = actual
        super().__init__(message, "INVALID_AUDIENCE", details)


class InvalidIssuer(TokenError):
    """Token issuer claim does not match expected value"""
    
    def __init__(
        self, 
        message: str = "Token issuer mismatch",
        expected: Optional[str] = None,
        actual: Optional[str] = None
    ):
        details = {}
        if expected:
            details["expected_issuer"] = expected
        if actual:
            details["actual_issuer"] = actual
        super().__init__(message, "INVALID_ISSUER", details)


class InsufficientScope(AuthError):
    """User lacks required scope/permissions"""
    
    def __init__(
        self, 
        message: str = "Insufficient permissions",
        required_scopes: Optional[list] = None,
        user_scopes: Optional[list] = None
    ):
        details = {}
        if required_scopes:
            details["required_scopes"] = required_scopes
        if user_scopes:
            details["user_scopes"] = user_scopes
        super().__init__(message, "INSUFFICIENT_SCOPE", details)


class InsufficientRole(AuthError):
    """User lacks required role"""
    
    def __init__(
        self, 
        message: str = "Insufficient role permissions",
        required_roles: Optional[list] = None,
        user_roles: Optional[list] = None
    ):
        details = {}
        if required_roles:
            details["required_roles"] = required_roles
        if user_roles:
            details["user_roles"] = user_roles
        super().__init__(message, "INSUFFICIENT_ROLE", details)


class TenantMismatch(AuthError):
    """Token tenant does not match expected tenant"""
    
    def __init__(
        self, 
        message: str = "Tenant context mismatch",
        expected_tenant: Optional[str] = None,
        token_tenant: Optional[str] = None
    ):
        details = {}
        if expected_tenant:
            details["expected_tenant"] = expected_tenant
        if token_tenant:
            details["token_tenant"] = token_tenant
        super().__init__(message, "TENANT_MISMATCH", details)


class ServiceTokenError(AuthError):
    """Service-to-service token error"""
    
    def __init__(
        self, 
        message: str = "Service token error",
        error_code: str = "SERVICE_TOKEN_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, details)


class UnauthorizedService(ServiceTokenError):
    """Service is not authorized for the requested operation"""
    
    def __init__(
        self, 
        message: str = "Service not authorized",
        service_name: Optional[str] = None,
        target_service: Optional[str] = None,
        operation: Optional[str] = None
    ):
        details = {}
        if service_name:
            details["service_name"] = service_name
        if target_service:
            details["target_service"] = target_service
        if operation:
            details["operation"] = operation
        super().__init__(message, "UNAUTHORIZED_SERVICE", details)


class InvalidServiceToken(ServiceTokenError):
    """Service token is invalid"""
    
    def __init__(
        self, 
        message: str = "Invalid service token",
        reason: Optional[str] = None
    ):
        details = {"reason": reason} if reason else {}
        super().__init__(message, "INVALID_SERVICE_TOKEN", details)


class SecretsProviderError(AuthError):
    """Secrets provider error"""
    
    def __init__(
        self, 
        message: str = "Secrets provider error",
        provider: Optional[str] = None,
        operation: Optional[str] = None
    ):
        details = {}
        if provider:
            details["provider"] = provider
        if operation:
            details["operation"] = operation
        super().__init__(message, "SECRETS_PROVIDER_ERROR", details)


class ConfigurationError(AuthError):
    """Authentication configuration error"""
    
    def __init__(
        self, 
        message: str = "Authentication configuration error",
        component: Optional[str] = None
    ):
        details = {"component": component} if component else {}
        super().__init__(message, "CONFIGURATION_ERROR", details)


# Exception mapping for HTTP status codes
EXCEPTION_STATUS_MAP = {
    TokenNotFound: 401,
    TokenExpired: 401,
    InvalidToken: 401,
    InvalidSignature: 401,
    InvalidAlgorithm: 401,
    InvalidAudience: 401,
    InvalidIssuer: 401,
    InsufficientScope: 403,
    InsufficientRole: 403,
    TenantMismatch: 403,
    UnauthorizedService: 403,
    InvalidServiceToken: 401,
    SecretsProviderError: 500,
    ConfigurationError: 500,
    AuthError: 401,  # Default for base class
}


def get_http_status(exception: AuthError) -> int:
    """Get appropriate HTTP status code for authentication exception"""
    return EXCEPTION_STATUS_MAP.get(type(exception), 401)