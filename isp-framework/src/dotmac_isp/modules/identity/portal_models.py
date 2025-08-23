"""Portal Account models for authentication and account management."""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from dotmac_isp.shared.database.base import TenantModel


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
