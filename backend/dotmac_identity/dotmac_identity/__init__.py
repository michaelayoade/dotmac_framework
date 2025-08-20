"""
DotMac Identity - Identity & Customer Management Platform

A comprehensive identity and customer management system for ISP operations,
providing small, composable SDKs for user accounts, profiles, organizations,
contacts, verification, consent, customer lifecycle, and portal management.
"""

from .core.config import IdentityConfig
from .core.exceptions import (
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
from .sdks.addresses import AddressesSDK
from .sdks.consent_preferences import ConsentPreferencesSDK
from .sdks.contacts import ContactsSDK
from .sdks.customer_management import CustomerManagementSDK
from .sdks.customer_portal import CustomerPortalSDK
from .sdks.email import EmailSDK

# SDK imports
from .sdks.identity_account import IdentityAccountSDK
from .sdks.organizations import OrganizationsSDK
from .sdks.phone import PhoneSDK
from .sdks.portal_management import PortalManagementSDK
from .sdks.reseller_portal import ResellerPortalSDK
from .sdks.user_profile import UserProfileSDK

__version__ = "1.0.0"
__author__ = "DotMac Team"
__email__ = "support@dotmac.com"

__all__ = [
    # Core
    "IdentityConfig",
    # Exceptions
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
    # SDKs
    "IdentityAccountSDK",
    "UserProfileSDK",
    "OrganizationsSDK",
    "ContactsSDK",
    "AddressesSDK",
    "EmailSDK",
    "PhoneSDK",
    "ConsentPreferencesSDK",
    "CustomerManagementSDK",
    "PortalManagementSDK",
    "CustomerPortalSDK",
    "ResellerPortalSDK",
]
