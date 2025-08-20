"""
In-memory services for DotMac Identity operations.
"""

from .account_service import AccountService
from .address_service import AddressService
from .consent_service import ConsentService
from .contact_service import ContactService
from .customer_service import CustomerService
from .organization_service import OrganizationService
from .portal_service import PortalService
from .profile_service import ProfileService
from .verification_service import VerificationService

__all__ = [
    "AccountService",
    "ProfileService",
    "OrganizationService",
    "ContactService",
    "AddressService",
    "VerificationService",
    "ConsentService",
    "CustomerService",
    "PortalService",
]
