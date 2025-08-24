"""
Common exceptions for all DotMac SDKs.
"""

from typing import Optional, Any, Dict


class SDKError(Exception):
    """Base exception for all SDK errors."""

    def __init__(
        """  Init   operation."""
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

    def __str__(self):
        """  Str   operation."""
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details,
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


class AlarmStormDetectedError(SDKError):
    """Raised when alarm storm is detected in network monitoring."""

    pass


class ConfigDriftDetectedError(SDKError):
    """Raised when configuration drift is detected in network devices."""

    pass


class RoutingError(SDKError):
    """Raised when routing fails in gateway."""

    pass


class ConfigurationError(SDKError):
    """Raised when SDK configuration is invalid."""

    pass


class ValidationError(SDKError):
    """Raised when data validation fails."""

    pass


class SDKRateLimitError(SDKError):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        """  Init   operation."""
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


class ConsentError(SDKError):
    """Raised when consent-related operations fail."""

    pass


class AnalyticsError(SDKError):
    """Raised when analytics operations fail."""

    pass


class AlarmError(SDKError):
    """Raised when alarm/alert operations fail."""

    pass


class GatewayError(SDKError):
    """Raised when API gateway operations fail."""

    pass


# Additional specific exceptions
class CustomerError(SDKError):
    """Raised when customer operations fail."""

    pass


class PortalError(SDKError):
    """Raised when portal operations fail."""

    pass


class PortalNotFoundError(PortalError):
    """Raised when portal is not found."""

    pass


class AccountError(SDKError):
    """Raised when account operations fail."""

    pass


class OrganizationError(SDKError):
    """Raised when organization operations fail."""

    pass


class ProfileError(SDKError):
    """Raised when profile operations fail."""

    pass


class VerificationError(SDKError):
    """Raised when verification operations fail."""

    pass


class VerificationExpiredError(VerificationError):
    """Raised when verification token has expired."""

    pass


class VerificationFailedError(VerificationError):
    """Raised when verification fails."""

    pass


class ConfigError(SDKError):
    """Raised when configuration operations fail."""

    pass


class ResourceAllocationError(SDKError):
    """Raised when resource allocation fails."""

    pass


class ResourceBindingError(SDKError):
    """Raised when resource binding fails."""

    pass


class PolicyIntentError(SDKError):
    """Raised when policy intent operations fail."""

    pass


class PricingRuleError(SDKError):
    """Raised when pricing rule operations fail."""

    pass


class TariffError(SDKError):
    """Raised when tariff operations fail."""

    pass


class InvalidStateTransitionError(SDKError):
    """Raised when invalid state transition is attempted."""

    pass


class ProvisioningError(SDKError):
    """Raised when provisioning operations fail."""

    pass


class ServiceNotFoundError(SDKNotFoundError):
    """Raised when service is not found."""

    pass


class ServiceStateError(SDKError):
    """Raised when service state operations fail."""

    pass


class NotFoundError(SDKNotFoundError):
    """Generic not found error."""

    pass


class DeviceError(SDKError):
    """Raised when device operations fail."""

    pass


class AddOnError(SDKError):
    """Raised when add-on operations fail."""

    pass


class DeviceNotFoundError(SDKNotFoundError):
    """Raised when device is not found."""

    pass


class BundleError(SDKError):
    """Raised when bundle operations fail."""

    pass


class ServiceDefinitionError(SDKError):
    """Raised when service definition operations fail."""

    pass


class MonitoringDataUnavailableError(SDKError):
    """Raised when monitoring data is unavailable."""

    pass


class ServicePlanError(SDKError):
    """Raised when service plan operations fail."""

    pass


class MonitoringError(SDKError):
    """Raised when monitoring operations fail."""

    pass


# Additional networking error class
class NetworkingError(SDKError):
    """Raised when networking operations fail."""
    
    pass


class RepositoryError(SDKError):
    """Raised when repository operations fail."""
    
    pass


class IPAddressConflictError(NetworkingError):
    """Raised when IP address conflicts occur."""
    
    pass


class IPAMError(NetworkingError):
    """Raised when IPAM (IP Address Management) operations fail."""
    
    pass


class AutomationError(NetworkingError):
    """Raised when network automation operations fail."""
    
    pass


class TopologyError(NetworkingError):
    """Raised when network topology operations fail."""
    
    pass


class RADIUSError(NetworkingError):
    """Raised when RADIUS operations fail."""
    
    pass


class RADIUSAuthenticationError(RADIUSError):
    """Raised when RADIUS authentication fails."""
    
    pass


class CoAFailedError(RADIUSError):
    """Raised when RADIUS Change of Authorization (CoA) fails."""
    
    pass


class VLANError(NetworkingError):
    """Raised when VLAN operations fail."""
    
    pass


class VLANConflictError(VLANError):
    """Raised when VLAN conflicts occur."""
    
    pass


# Aliases for backward compatibility
AuthenticationError = SDKAuthenticationError
AuthorizationError = SDKAuthenticationError  # Use same class for now
NetworkError = SDKConnectionError
TimeoutError = SDKTimeoutError
RateLimitError = SDKRateLimitError
