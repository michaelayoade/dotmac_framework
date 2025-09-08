"""
Error classes for services and repositories.

This module provides standardized exception classes for the service kernel,
ensuring consistent error handling across all services and repositories.
"""


class ServiceError(Exception):
    """Base exception for service-related errors.

    This exception serves as the base class for all service-related errors.
    It should be caught by API layers and converted to appropriate HTTP responses.

    Attributes:
        message: Human-readable error message
        error_code: Optional error code for programmatic handling
        details: Optional additional error details
    """

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, str] | None = None
    ) -> None:
        """Initialize service error.

        Args:
            message: Human-readable error message
            error_code: Optional error code for programmatic handling
            details: Optional additional error details
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class RepositoryError(Exception):
    """Base exception for repository-related errors.

    This exception serves as the base class for all repository-related errors,
    typically related to data access, constraints, or persistence issues.

    Attributes:
        message: Human-readable error message
        error_code: Optional error code for programmatic handling
        details: Optional additional error details
    """

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, str] | None = None
    ) -> None:
        """Initialize repository error.

        Args:
            message: Human-readable error message
            error_code: Optional error code for programmatic handling
            details: Optional additional error details
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class ValidationError(ServiceError):
    """Service validation error.

    Raised when service input validation fails.
    """

    def __init__(
        self,
        message: str = "Validation failed",
        field_errors: dict[str, list[str]] | None = None
    ) -> None:
        """Initialize validation error.

        Args:
            message: General validation error message
            field_errors: Field-specific validation errors
        """
        super().__init__(message, error_code="validation_error")
        self.field_errors = field_errors or {}


class NotFoundError(ServiceError):
    """Service not found error.

    Raised when a requested resource cannot be found.
    """

    def __init__(self, resource: str, identifier: str | int | None = None) -> None:
        """Initialize not found error.

        Args:
            resource: Name of the resource that was not found
            identifier: Optional identifier of the resource
        """
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} with id '{identifier}' not found"

        super().__init__(message, error_code="not_found")
        self.resource = resource
        self.identifier = identifier


class ConflictError(ServiceError):
    """Service conflict error.

    Raised when an operation conflicts with current state.
    """

    def __init__(self, message: str, conflicting_resource: str | None = None) -> None:
        """Initialize conflict error.

        Args:
            message: Description of the conflict
            conflicting_resource: Optional name of the conflicting resource
        """
        super().__init__(message, error_code="conflict")
        self.conflicting_resource = conflicting_resource


class ServicePermissionError(ServiceError):
    """Service permission error.

    Raised when access is denied to a resource or operation.
    """

    def __init__(self, message: str = "Permission denied", resource: str | None = None) -> None:
        """Initialize permission error.

        Args:
            message: Permission error message
            resource: Optional name of the protected resource
        """
        super().__init__(message, error_code="permission_denied")
        self.resource = resource


__all__ = [
    "ServiceError",
    "RepositoryError",
    "ValidationError",
    "NotFoundError",
    "ConflictError",
    "PermissionError",
]
