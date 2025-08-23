"""
Small, composable SDKs for DotMac Identity.
"""

from .schemas import (
    CustomerCreate,
    CustomerUpdate,
    CustomerResponse,
    CustomerListFilters,
)
from .addresses import AddressesSDK
from .consent_preferences import ConsentPreferencesSDK
from .contacts import ContactsSDK
from .customer_management import CustomerManagementSDK
from .customer_portal import CustomerPortalSDK
from .email import EmailSDK
from .identity_account import IdentityAccountSDK
from .organizations import OrganizationsSDK
from .phone import PhoneSDK
from .portal_management import PortalManagementSDK
from .reseller_portal import ResellerPortalSDK
from .user_profile import UserProfileSDK

__all__ = [
    # Schemas
    "CustomerCreate",
    "CustomerUpdate", 
    "CustomerResponse",
    "CustomerListFilters",
    # Core directory & profiles
    "IdentityAccountSDK",
    "UserProfileSDK",
    "OrganizationsSDK",
    "ContactsSDK",
    "AddressesSDK",
    # Verification & consent
    "EmailSDK",
    "PhoneSDK",
    "ConsentPreferencesSDK",
    # Customer entity & lifecycle
    "CustomerManagementSDK",
    # Portals
    "PortalManagementSDK",
    "CustomerPortalSDK",
    "ResellerPortalSDK",
]
