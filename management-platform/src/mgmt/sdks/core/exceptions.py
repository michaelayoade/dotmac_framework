"""
Core SDK exceptions for the DotMac ISP Framework.

Provides a hierarchy of exceptions for consistent error handling
across all SDK components with proper error categorization.
"""

from typing import Optional, Dict, Any


class SDKError(Exception):
    """
    Base exception for all SDK errors.
    
    This is the base class for all SDK-related exceptions,
    providing common functionality for error handling.
    """
    
    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        """
        Initialize SDK error.
        
        Args:
            message: Human-readable error message
            code: Error code for programmatic handling
            details: Additional error details
            original_error: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.original_error = original_error
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary format.
        
        Returns:
            Dictionary representation of the error
        """
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "code": self.code,
            "details": self.details,
        }
    
    def __str__(self) -> str:
        """String representation of the error."""
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message


class SDKConnectionError(SDKError):
    """
    Exception raised for network/connection issues.
    
    This includes DNS resolution failures, connection timeouts,
    network unreachable errors, and other connectivity problems.
    """
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, code="CONNECTION_ERROR", **kwargs)


class SDKAuthenticationError(SDKError):
    """
    Exception raised for authentication/authorization failures.
    
    This includes invalid API keys, expired tokens, insufficient
    permissions, and other auth-related issues.
    """
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, code="AUTHENTICATION_ERROR", **kwargs)


class SDKValidationError(SDKError):
    """
    Exception raised for data validation failures.
    
    This includes invalid input data, schema validation errors,
    constraint violations, and other data integrity issues.
    """
    
    def __init__(self, message: str, validation_errors: Optional[Dict[str, Any]] = None, **kwargs):
        details = kwargs.get('details', {})
        if validation_errors:
            details['validation_errors'] = validation_errors
        kwargs['details'] = details
        super().__init__(message, code="VALIDATION_ERROR", **kwargs)


class SDKRateLimitError(SDKError):
    """
    Exception raised when API rate limits are exceeded.
    
    This includes both per-user and global rate limiting,
    with information about when to retry.
    """
    
    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        details = kwargs.get('details', {})
        if retry_after:
            details['retry_after'] = retry_after
        kwargs['details'] = details
        super().__init__(message, code="RATE_LIMIT_ERROR", **kwargs)


class SDKTimeoutError(SDKError):
    """
    Exception raised for request timeout errors.
    
    This includes both connection timeouts and read timeouts,
    indicating the request took too long to complete.
    """
    
    def __init__(self, message: str, timeout_duration: Optional[float] = None, **kwargs):
        details = kwargs.get('details', {})
        if timeout_duration:
            details['timeout_duration'] = timeout_duration
        kwargs['details'] = details
        super().__init__(message, code="TIMEOUT_ERROR", **kwargs)


class SDKNotFoundError(SDKError):
    """
    Exception raised when a requested resource is not found.
    
    This is used for 404 errors and cases where a specific
    resource (customer, service, etc.) doesn't exist.
    """
    
    def __init__(self, message: str, resource_type: Optional[str] = None, resource_id: Optional[str] = None, **kwargs):
        details = kwargs.get('details', {})
        if resource_type:
            details['resource_type'] = resource_type
        if resource_id:
            details['resource_id'] = resource_id
        kwargs['details'] = details
        super().__init__(message, code="NOT_FOUND_ERROR", **kwargs)


class SDKConfigurationError(SDKError):
    """
    Exception raised for SDK configuration issues.
    
    This includes missing required configuration, invalid
    settings, and other setup-related problems.
    """
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, code="CONFIGURATION_ERROR", **kwargs)


class SDKServiceUnavailableError(SDKError):
    """
    Exception raised when a service is temporarily unavailable.
    
    This includes maintenance windows, service overload,
    and other temporary service disruptions.
    """
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, code="SERVICE_UNAVAILABLE_ERROR", **kwargs)


# Service-specific exceptions
class CustomerError(SDKError):
    """Exception for customer management operations."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, code="CUSTOMER_ERROR", **kwargs)


class IPAMError(SDKError):
    """Exception for IPAM operations."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, code="IPAM_ERROR", **kwargs)


class IPAddressConflictError(IPAMError):
    """Exception for IP address conflicts."""
    
    def __init__(self, ip_address: str, **kwargs):
        message = f"IP address {ip_address} is already allocated or reserved"
        details = kwargs.get('details', {})
        details['ip_address'] = ip_address
        kwargs['details'] = details
        super().__init__(message, code="IP_CONFLICT_ERROR", **kwargs)


class ServiceDefinitionError(SDKError):
    """Exception for service definition operations."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, code="SERVICE_DEFINITION_ERROR", **kwargs)


class ServicePlanError(SDKError):
    """Exception for service plan operations."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, code="SERVICE_PLAN_ERROR", **kwargs)


class TenantError(SDKError):
    """Exception for tenant management operations."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, code="TENANT_ERROR", **kwargs)


# Utility functions for exception handling
def handle_sdk_error(error: Exception) -> SDKError:
    """
    Convert generic exceptions to SDK errors.
    
    Args:
        error: Exception to convert
        
    Returns:
        Appropriate SDK error instance
    """
    if isinstance(error, SDKError):
        return error
    
    error_message = str(error)
    
    # Map common exception types to SDK errors
    if isinstance(error, (ConnectionError, OSError)):
        return SDKConnectionError(error_message, original_error=error)
    elif isinstance(error, TimeoutError):
        return SDKTimeoutError(error_message, original_error=error)
    elif isinstance(error, ValueError):
        return SDKValidationError(error_message, original_error=error)
    else:
        return SDKError(error_message, original_error=error)


def is_retryable_error(error: Exception) -> bool:
    """
    Determine if an error is retryable.
    
    Args:
        error: Exception to check
        
    Returns:
        True if the error is retryable
    """
    if isinstance(error, (SDKConnectionError, SDKTimeoutError, SDKServiceUnavailableError)):
        return True
    
    if isinstance(error, SDKRateLimitError):
        # Rate limit errors are retryable with backoff
        return True
    
    # Authentication, validation, and not found errors are typically not retryable
    if isinstance(error, (SDKAuthenticationError, SDKValidationError, SDKNotFoundError)):
        return False
    
    return False