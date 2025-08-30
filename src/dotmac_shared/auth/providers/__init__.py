"""
Authentication providers.

This module contains different authentication providers:
- Local database authentication
- OAuth2/OIDC integration
- LDAP/Active Directory integration
"""

from .ldap_provider import LDAPProvider
from .local_provider import LocalAuthProvider
from .oauth_provider import OAuth2Provider

__all__ = [
    "LocalAuthProvider",
    "OAuth2Provider",
    "LDAPProvider",
]
