"""
Core utilities for DotMac Identity package.
"""

from .config import IdentityConfig
from .exceptions import (
    AccountError,
    AddressError,
    ConsentError,
    ContactError,
    CustomerError,
    IdentityError,
    OrganizationError,
    PortalError,
    ProfileError,
    VerificationError,
)

__all__ = [
    "IdentityConfig",
    "IdentityError",
    "AccountError",
    "ProfileError",
    "OrganizationError",
    "ContactError",
    "AddressError",
    "VerificationError",
    "ConsentError",
    "CustomerError",
    "PortalError",
]

from .datetime_utils import utc_now, is_expired, expires_in_hours, expires_in_minutes
