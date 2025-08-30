"""Authentication providers for captive portal access."""

from .base import AuthenticationResult, BaseAuthProvider
from .email import EmailAuthProvider
from .manager import AuthenticationManager
from .social import SocialAuthProvider
from .voucher import VoucherAuthProvider

__all__ = [
    "BaseAuthProvider",
    "AuthenticationResult",
    "EmailAuthProvider",
    "SocialAuthProvider",
    "VoucherAuthProvider",
    "AuthenticationManager",
]
