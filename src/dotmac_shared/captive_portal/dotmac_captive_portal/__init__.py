"""
Unified Captive Portal Package for DotMac Framework.

Provides comprehensive WiFi captive portal functionality including:
- Guest network management and access control
- Multi-authentication methods (social, vouchers, RADIUS)
- Billing integration with usage tracking and payments
- Portal customization with themes and branding
- Session management and monitoring
- RADIUS integration for network enforcement
- Analytics and reporting

This package consolidates captive portal functionality across the DotMac ecosystem,
replacing scattered implementations with a unified, production-ready solution.
"""

from .auth import (
    AuthenticationManager,
    RADIUSAuth,
    SocialAuth,
    VoucherAuth,
)
from .billing import BillingIntegration, PaymentProcessor, UsageTracker
from .core import CaptivePortal, CaptivePortalConfig
from .customization import BrandingConfig, PortalCustomizer, Theme
from .guest_manager import GuestNetwork, GuestNetworkManager
from .models import (
    AuthMethod,
    BillingPlan,
    GuestUser,
    Portal,
    Session,
    Voucher,
)

__version__ = "1.0.0"
__author__ = "DotMac Development Team"

__all__ = [
    # Core classes
    "CaptivePortal",
    "CaptivePortalConfig",
    # Guest network management
    "GuestNetworkManager",
    "GuestNetwork",
    # Authentication
    "AuthenticationManager",
    "SocialAuth",
    "VoucherAuth",
    "RADIUSAuth",
    # Billing and usage
    "BillingIntegration",
    "UsageTracker",
    "PaymentProcessor",
    # Customization
    "PortalCustomizer",
    "Theme",
    "BrandingConfig",
    # Models
    "Portal",
    "GuestUser",
    "Session",
    "Voucher",
    "AuthMethod",
    "BillingPlan",
]
