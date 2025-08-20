"""
Custom exceptions for DotMac Identity operations.
"""


class IdentityError(Exception):
    """Base exception for identity operations."""

    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "IDENTITY_ERROR"
        self.details = details or {}


class AccountError(IdentityError):
    """Exception for account-related operations."""

    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message, error_code or "ACCOUNT_ERROR", details)


class ProfileError(IdentityError):
    """Exception for profile-related operations."""

    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message, error_code or "PROFILE_ERROR", details)


class OrganizationError(IdentityError):
    """Exception for organization-related operations."""

    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message, error_code or "ORGANIZATION_ERROR", details)


class ContactError(IdentityError):
    """Exception for contact-related operations."""

    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message, error_code or "CONTACT_ERROR", details)


class AddressError(IdentityError):
    """Exception for address-related operations."""

    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message, error_code or "ADDRESS_ERROR", details)


class VerificationError(IdentityError):
    """Exception for verification-related operations."""

    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message, error_code or "VERIFICATION_ERROR", details)


class ConsentError(IdentityError):
    """Exception for consent-related operations."""

    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message, error_code or "CONSENT_ERROR", details)


class CustomerError(IdentityError):
    """Exception for customer-related operations."""

    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message, error_code or "CUSTOMER_ERROR", details)


class PortalError(IdentityError):
    """Exception for portal-related operations."""

    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message, error_code or "PORTAL_ERROR", details)


# Specific error types
class AccountNotFoundError(AccountError):
    """Account not found."""

    def __init__(self, account_id: str):
        super().__init__(f"Account not found: {account_id}", "ACCOUNT_NOT_FOUND", {"account_id": account_id})


class AccountDisabledError(AccountError):
    """Account is disabled."""

    def __init__(self, account_id: str):
        super().__init__(f"Account is disabled: {account_id}", "ACCOUNT_DISABLED", {"account_id": account_id})


class InvalidCredentialsError(AccountError):
    """Invalid credentials provided."""

    def __init__(self):
        super().__init__("Invalid credentials", "INVALID_CREDENTIALS")


class MFARequiredError(AccountError):
    """MFA verification required."""

    def __init__(self, account_id: str):
        super().__init__(f"MFA verification required for account: {account_id}", "MFA_REQUIRED", {"account_id": account_id})


class VerificationExpiredError(VerificationError):
    """Verification code has expired."""

    def __init__(self, verification_type: str):
        super().__init__(f"{verification_type} verification has expired", "VERIFICATION_EXPIRED", {"type": verification_type})


class VerificationFailedError(VerificationError):
    """Verification failed."""

    def __init__(self, verification_type: str, attempts_remaining: int = None):
        details = {"type": verification_type}
        if attempts_remaining is not None:
            details["attempts_remaining"] = attempts_remaining
        super().__init__(f"{verification_type} verification failed", "VERIFICATION_FAILED", details)


class CustomerNotFoundError(CustomerError):
    """Customer not found."""

    def __init__(self, customer_id: str):
        super().__init__(f"Customer not found: {customer_id}", "CUSTOMER_NOT_FOUND", {"customer_id": customer_id})


class PortalNotFoundError(PortalError):
    """Portal not found."""

    def __init__(self, portal_id: str):
        super().__init__(f"Portal not found: {portal_id}", "PORTAL_NOT_FOUND", {"portal_id": portal_id})


class PortalAccessDeniedError(PortalError):
    """Portal access denied."""

    def __init__(self, portal_id: str, reason: str = None):
        details = {"portal_id": portal_id}
        if reason:
            details["reason"] = reason
        super().__init__(f"Portal access denied: {portal_id}", "PORTAL_ACCESS_DENIED", details)
