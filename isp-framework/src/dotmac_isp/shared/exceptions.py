"""Shared exceptions for the DotMac ISP Framework."""

from typing import Optional, Any, Dict


class DotMacISPError(Exception):
    """Base exception for DotMac ISP Framework."""

    def __init__(
        """  Init   operation."""
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(DotMacISPError):
    """Raised when data validation fails."""

    def __init__(
        """  Init   operation."""
        self,
        message: str = "Validation failed",
        field: Optional[str] = None,
        value: Optional[Any] = None,
        **kwargs,
    ):
        self.field = field
        self.value = value
        super().__init__(message, error_code="VALIDATION_ERROR", **kwargs)


class NotFoundError(DotMacISPError):
    """Raised when a requested resource is not found."""

    def __init__(
        """  Init   operation."""
        self,
        message: str = "Resource not found",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs,
    ):
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(message, error_code="NOT_FOUND", **kwargs)


class ConflictError(DotMacISPError):
    """Raised when a resource conflict occurs."""

    def __init__(
        """  Init   operation."""
        self,
        message: str = "Resource conflict",
        resource_type: Optional[str] = None,
        conflicting_field: Optional[str] = None,
        **kwargs,
    ):
        self.resource_type = resource_type
        self.conflicting_field = conflicting_field
        super().__init__(message, error_code="CONFLICT", **kwargs)


class AuthenticationError(DotMacISPError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed", **kwargs):
        """  Init   operation."""
        super().__init__(message, error_code="AUTHENTICATION_ERROR", **kwargs)


class AuthorizationError(DotMacISPError):
    """Raised when authorization fails."""

    def __init__(
        """  Init   operation."""
        self,
        message: str = "Authorization failed",
        required_permission: Optional[str] = None,
        **kwargs,
    ):
        self.required_permission = required_permission
        super().__init__(message, error_code="AUTHORIZATION_ERROR", **kwargs)


class ServiceError(DotMacISPError):
    """Raised when a service operation fails."""

    def __init__(
        """  Init   operation."""
        self,
        message: str = "Service operation failed",
        service_name: Optional[str] = None,
        **kwargs,
    ):
        self.service_name = service_name
        super().__init__(message, error_code="SERVICE_ERROR", **kwargs)


class ExternalServiceError(DotMacISPError):
    """Raised when an external service call fails."""

    def __init__(
        """  Init   operation."""
        self,
        message: str = "External service error",
        service_name: Optional[str] = None,
        status_code: Optional[int] = None,
        **kwargs,
    ):
        self.service_name = service_name
        self.status_code = status_code
        super().__init__(message, error_code="EXTERNAL_SERVICE_ERROR", **kwargs)


class NetworkError(DotMacISPError):
    """Raised when network-related operations fail."""

    def __init__(
        """  Init   operation."""
        self,
        message: str = "Network operation failed",
        network_resource: Optional[str] = None,
        **kwargs,
    ):
        self.network_resource = network_resource
        super().__init__(message, error_code="NETWORK_ERROR", **kwargs)


class BillingError(DotMacISPError):
    """Raised when billing operations fail."""

    def __init__(
        """  Init   operation."""
        self,
        message: str = "Billing operation failed",
        billing_component: Optional[str] = None,
        **kwargs,
    ):
        self.billing_component = billing_component
        super().__init__(message, error_code="BILLING_ERROR", **kwargs)


class TenantError(DotMacISPError):
    """Raised when tenant-related operations fail."""

    def __init__(
        """  Init   operation."""
        self,
        message: str = "Tenant operation failed",
        tenant_id: Optional[str] = None,
        **kwargs,
    ):
        self.tenant_id = tenant_id
        super().__init__(message, error_code="TENANT_ERROR", **kwargs)


class RateLimitError(DotMacISPError):
    """Raised when rate limit is exceeded."""

    def __init__(
        """  Init   operation."""
        self,
        message: str = "Rate limit exceeded",
        limit: Optional[int] = None,
        reset_time: Optional[str] = None,
        **kwargs,
    ):
        self.limit = limit
        self.reset_time = reset_time
        super().__init__(message, error_code="RATE_LIMIT_ERROR", **kwargs)


class ConfigurationError(DotMacISPError):
    """Raised when configuration is invalid or missing."""

    def __init__(
        """  Init   operation."""
        self,
        message: str = "Configuration error",
        config_key: Optional[str] = None,
        **kwargs,
    ):
        self.config_key = config_key
        super().__init__(message, error_code="CONFIGURATION_ERROR", **kwargs)


class EntityNotFoundError(DotMacISPError):
    """Raised when a requested entity is not found in the database."""

    def __init__(
        """  Init   operation."""
        self,
        message: str = "Entity not found",
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        **kwargs,
    ):
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(message, error_code="ENTITY_NOT_FOUND", **kwargs)


class BusinessRuleError(DotMacISPError):
    """Raised when a business rule is violated."""

    def __init__(
        """  Init   operation."""
        self,
        message: str = "Business rule violation",
        rule_name: Optional[str] = None,
        **kwargs,
    ):
        self.rule_name = rule_name
        super().__init__(message, error_code="BUSINESS_RULE_ERROR", **kwargs)


class DuplicateEntityError(DotMacISPError):
    """Raised when attempting to create a duplicate entity."""

    def __init__(
        """  Init   operation."""
        self,
        message: str = "Duplicate entity",
        entity_type: Optional[str] = None,
        conflicting_field: Optional[str] = None,
        **kwargs,
    ):
        self.entity_type = entity_type
        self.conflicting_field = conflicting_field
        super().__init__(message, error_code="DUPLICATE_ENTITY", **kwargs)


class DatabaseError(DotMacISPError):
    """Raised when a database operation fails."""

    def __init__(
        """  Init   operation."""
        self,
        message: str = "Database operation failed",
        operation: Optional[str] = None,
        **kwargs,
    ):
        self.operation = operation
        super().__init__(message, error_code="DATABASE_ERROR", **kwargs)
