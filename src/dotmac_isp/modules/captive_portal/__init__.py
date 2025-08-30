"""Captive Portal module for WiFi hotspot authentication and session management.

This module provides enterprise-grade captive portal functionality integrated
with the DotMac ISP Framework infrastructure, including existing identity,
billing, and analytics modules.

Features:
- Multi-authentication methods (social, voucher, RADIUS, SMS)
- Session management with usage tracking
- Integration with existing billing and customer systems
- Portal customization and branding
- Analytics and reporting
"""

from .models import (
    AuthMethod,
    AuthMethodType,
    CaptivePortalConfig,
    CaptivePortalSession,
    PortalCustomization,
    PortalUsageStats,
    SessionStatus,
    Voucher,
    VoucherBatch,
)
from .repository import CaptivePortalRepository
from .schemas import (
    AuthenticationRequest,
    AuthenticationResponse,
    CaptivePortalConfigCreate,
    CaptivePortalConfigResponse,
    SessionResponse,
    VoucherCreateRequest,
    VoucherResponse,
)
from .service import CaptivePortalService

__all__ = [
    # Models
    "CaptivePortalConfig",
    "CaptivePortalSession",
    "SessionStatus",
    "AuthMethodType",
    "AuthMethod",
    "Voucher",
    "VoucherBatch",
    "PortalCustomization",
    "PortalUsageStats",
    # Schemas
    "CaptivePortalConfigCreate",
    "CaptivePortalConfigResponse",
    "AuthenticationRequest",
    "AuthenticationResponse",
    "SessionResponse",
    "VoucherCreateRequest",
    "VoucherResponse",
    # Services
    "CaptivePortalService",
    "CaptivePortalRepository",
]
