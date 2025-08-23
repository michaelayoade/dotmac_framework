"""Exception classes for plugin licensing service."""


class LicensingError(Exception):
    """Base exception for plugin licensing errors."""
    pass


class PluginNotFoundError(LicensingError):
    """Raised when a plugin is not found."""
    pass


class LicenseExpiredError(LicensingError):
    """Raised when a plugin license has expired."""
    pass


class UsageLimitExceededError(LicensingError):
    """Raised when plugin usage limits are exceeded."""
    pass


class InvalidLicenseError(LicensingError):
    """Raised when a license is invalid or corrupted."""
    pass


class LicenseValidationError(LicensingError):
    """Raised when license validation fails."""
    pass


class PluginSubscriptionError(LicensingError):
    """Raised when plugin subscription operations fail."""
    pass


class EntitlementError(LicensingError):
    """Raised when entitlement operations fail."""
    pass