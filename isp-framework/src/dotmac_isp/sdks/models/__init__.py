"""SDK models package."""

from dataclasses import dataclass
from typing import Optional

# Import model modules
from .addresses import AddressModel, AddressType
from .dashboards import Dashboard, ChartWidget, ChartType, Widget
from .consent import (
    ConsentType,
    ConsentStatus,
    ConsentSource,
    ConsentPreference,
    ConsentProfile,
    create_default_consent_profile,
    validate_gdpr_compliance,
)


@dataclass
class BaseModel:
    """Base model for all SDK models."""

    id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


__all__ = [
    "BaseModel",
    "AddressModel",
    "AddressType",
    "Dashboard",
    "ChartWidget",
    "ChartType",
    "Widget",
    "ConsentType",
    "ConsentStatus",
    "ConsentSource",
    "ConsentPreference",
    "ConsentProfile",
    "create_default_consent_profile",
    "validate_gdpr_compliance",
]
