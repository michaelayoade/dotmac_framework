"""
DRY shared exception utilities to reduce HTTPException duplication.
Provides standardized error responses across the platform.
"""

from fastapi import HTTPException, status
from typing import Optional
from enum import Enum


class ErrorCode(Enum):
    """Standardized error codes across the platform"""
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    PROVISIONING_ERROR = "PROVISIONING_ERROR"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"


class StandardExceptions:
    """
    DRY utility class for common HTTPException patterns.
    Reduces duplication across API endpoints.
    """
    
    @staticmethod
    def not_found(resource: str, identifier: str = None) -> HTTPException:
        """Standard 404 Not Found exception"""
        detail = f"{resource} not found"
        if identifier:
            detail += f": {identifier}"
        
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            headers={"X-Error-Code": ErrorCode.NOT_FOUND.value}
        )
    
    @staticmethod
    def already_exists(resource: str, identifier: str = None) -> HTTPException:
        """Standard 409 Conflict exception for existing resources"""
        detail = f"{resource} already exists"
        if identifier:
            detail += f": {identifier}"
            
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            headers={"X-Error-Code": ErrorCode.ALREADY_EXISTS.value}
        )
    
    @staticmethod
    def validation_error(message: str, field: str = None) -> HTTPException:
        """Standard 422 Validation Error exception"""
        detail = message
        if field:
            detail = f"{field}: {message}"
            
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            headers={"X-Error-Code": ErrorCode.VALIDATION_ERROR.value}
        )
    
    @staticmethod
    def unauthorized(message: str = "Authentication required") -> HTTPException:
        """Standard 401 Unauthorized exception"""
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=message,
            headers={
                "WWW-Authenticate": "Bearer",
                "X-Error-Code": ErrorCode.AUTHENTICATION_ERROR.value
            }
        )
    
    @staticmethod
    def forbidden(message: str = "Insufficient permissions") -> HTTPException:
        """Standard 403 Forbidden exception"""
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=message,
            headers={"X-Error-Code": ErrorCode.AUTHORIZATION_ERROR.value}
        )
    
    @staticmethod
    def internal_error(operation: str, error: str = None) -> HTTPException:
        """Standard 500 Internal Server Error exception"""
        detail = f"{operation} failed"
        if error:
            detail += f": {error}"
            
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            headers={"X-Error-Code": ErrorCode.EXTERNAL_SERVICE_ERROR.value}
        )
    
    @staticmethod
    def rate_limited(message: str = "Too many requests") -> HTTPException:
        """Standard 429 Rate Limit exception"""
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=message,
            headers={
                "X-Error-Code": ErrorCode.RATE_LIMIT_ERROR.value,
                "Retry-After": "60"
            }
        )
    
    @staticmethod
    def tenant_error(operation: str, tenant_id: str = None) -> HTTPException:
        """Standard tenant provisioning error"""
        detail = f"Tenant {operation} failed"
        if tenant_id:
            detail += f" for {tenant_id}"
            
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            headers={"X-Error-Code": ErrorCode.PROVISIONING_ERROR.value}
        )
    
    @staticmethod
    def config_error(setting: str, message: str = None) -> HTTPException:
        """Standard configuration error"""
        detail = f"Configuration error: {setting}"
        if message:
            detail += f" - {message}"
            
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            headers={"X-Error-Code": ErrorCode.CONFIGURATION_ERROR.value}
        )


# Convenience functions for common patterns
def tenant_not_found(tenant_id: str) -> HTTPException:
    """Tenant not found exception"""
    return StandardExceptions.not_found("Tenant", tenant_id)


def subdomain_taken(subdomain: str) -> HTTPException:
    """Subdomain already taken exception"""
    return StandardExceptions.already_exists("Subdomain", f"'{subdomain}'")


def provisioning_failed(tenant_id: str, reason: str = None) -> HTTPException:
    """Tenant provisioning failed exception"""
    detail = f"Provisioning failed for tenant {tenant_id}"
    if reason:
        detail += f": {reason}"
    return StandardExceptions.tenant_error("provisioning", tenant_id)


def coolify_error(operation: str, error: str = None) -> HTTPException:
    """Coolify API error exception"""
    return StandardExceptions.internal_error(f"Coolify {operation}", error)


# Export for easy importing
__all__ = [
    "StandardExceptions", 
    "ErrorCode",
    "tenant_not_found",
    "subdomain_taken", 
    "provisioning_failed",
    "coolify_error"
]