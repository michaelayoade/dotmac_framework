"""Portal Account models for authentication and account management."""

import enum


class PortalAccountType(enum.Enum):
    """Portal account type enumeration."""

    CUSTOMER = "customer"
    TECHNICIAN = "technician"
    ADMIN = "admin"
    RESELLER = "reseller"


class PortalAccountStatus(enum.Enum):
    """Portal account status enumeration."""

    PENDING_ACTIVATION = "pending_activation"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    LOCKED = "locked"
    EXPIRED = "expired"
    DISABLED = "disabled"


# PortalAccount model moved to dotmac_isp.modules.portal_management.models
# This module now only contains the enums used across modules
