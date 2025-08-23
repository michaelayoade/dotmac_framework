"""
Unified security components for DotMac Management Platform.
Provides enterprise-grade security features shared with ISP Framework.
"""

# Import security components (will create symlinks or copies)
from .secrets_manager import (
    MultiTenantSecretsManager,
    TenantSecretType,
    TenantSecretMetadata,
    get_mt_secrets_manager,
    init_mt_secrets_manager
)

__all__ = [
    "MultiTenantSecretsManager",
    "TenantSecretType", 
    "TenantSecretMetadata",
    "get_mt_secrets_manager",
    "init_mt_secrets_manager"
]