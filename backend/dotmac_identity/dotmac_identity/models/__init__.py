"""
Data models for DotMac Identity.
"""

from .accounts import Account, Credential, MFAFactor
from .addresses import Address
from .consent import ConsentAudit, ConsentPreference
from .contacts import Contact, ContactEmail, ContactPhone
from .customers import Customer, CustomerState
from .organizations import Organization, OrganizationMember
from .portals import CustomerPortalBinding, Portal, PortalSettings, ResellerPortalAccess
from .profiles import UserProfile
from .verification import EmailVerification, PhoneVerification

__all__ = [
    # Accounts
    "Account",
    "Credential",
    "MFAFactor",
    # Profiles
    "UserProfile",
    # Organizations
    "Organization",
    "OrganizationMember",
    # Contacts
    "Contact",
    "ContactEmail",
    "ContactPhone",
    # Addresses
    "Address",
    # Verification
    "EmailVerification",
    "PhoneVerification",
    # Consent
    "ConsentPreference",
    "ConsentAudit",
    # Customers
    "Customer",
    "CustomerState",
    # Portals
    "Portal",
    "PortalSettings",
    "CustomerPortalBinding",
    "ResellerPortalAccess",
]
