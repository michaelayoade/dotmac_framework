"""
Common exceptions for all DotMac SDKs.
"""

from typing import Optional, Any, Dict


class SDKError(Exception):
    """Base exception for all SDK errors."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
    
    def __str__(self):
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details
        }


class SDKConnectionError(SDKError):
    """Raised when connection to service fails."""
    pass


class SDKAuthenticationError(SDKError):
    """Raised when authentication fails."""
    pass


class SDKValidationError(SDKError):
    """Raised when request validation fails."""
    pass


class SDKRateLimitError(SDKError):
    """Raised when rate limit is exceeded."""
    
    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class SDKTimeoutError(SDKError):
    """Raised when request times out."""
    pass


class SDKNotFoundError(SDKError):
    """Raised when requested resource is not found."""
    pass


class SDKConflictError(SDKError):
    """Raised when resource conflict occurs."""
    pass


class SDKServiceUnavailableError(SDKError):
    """Raised when service is temporarily unavailable."""
    pass


class SDKDeprecationWarning(UserWarning):
    """Warning for deprecated SDK methods or parameters."""
    pass