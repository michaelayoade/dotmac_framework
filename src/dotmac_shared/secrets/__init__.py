"""
DotMac Secrets - Enterprise Secrets Management Package

This package provides comprehensive secrets management capabilities including:
- Enterprise-grade secrets management with compliance support
- OpenBao/Vault integration for secure secret storage
- Field-level encryption for sensitive data protection
- Role-Based Access Control (RBAC) for secrets access
- Multi-tenant secrets isolation
- Secrets rotation and lifecycle management
- Audit logging for security compliance

Features:
- SOC2, PCI DSS, ISO27001, GDPR compliant secret handling
- Multiple authentication methods (Token, AppRole, Kubernetes, AWS)
- Secret caching with TTL for performance
- Encryption as a Service capabilities
- Dynamic secret generation
- Hierarchical permission system
"""

# Core imports with graceful handling of missing dependencies
try:
    from .core.enterprise_secrets_manager import (
        EnterpriseSecretsManager,
        SecretMetadata,
        SecretSource,
        SecretType,
        SecretValidationResult,
        SecretValidationRule,
    )
except ImportError as e:
    import warnings

    warnings.warn(f"Enterprise secrets manager not available: {e}")
    EnterpriseSecretsManager = SecretType = SecretSource = None
    SecretValidationRule = SecretMetadata = SecretValidationResult = None

try:
    from .core.vault_client import OpenBaoClient
    from .core.vault_client import SecretMetadata as VaultSecretMetadata
    from .core.vault_client import VaultConfig
except ImportError as e:
    import warnings

    warnings.warn(f"Vault client not available: {e}")
    OpenBaoClient = VaultConfig = VaultSecretMetadata = None

try:
    from .core.field_encryption import (
        DataClassification,
        EncryptedField,
        decrypt_sensitive_fields,
        encrypt_sensitive_fields,
        encrypted_field,
    )
except ImportError as e:
    import warnings

    warnings.warn(f"Field encryption not available: {e}")
    EncryptedField = DataClassification = encrypted_field = None
    encrypt_sensitive_fields = decrypt_sensitive_fields = None

try:
    from .core.rbac import (
        AccessDecision,
        Permission,
        PermissionAction,
        PermissionScope,
        PolicyEvaluationContext,
        RBACManager,
        ResourceType,
        Role,
    )
except ImportError as e:
    import warnings

    warnings.warn(f"RBAC system not available: {e}")
    RBACManager = Permission = Role = PermissionAction = None
    ResourceType = PermissionScope = PolicyEvaluationContext = AccessDecision = None

# Adapter imports
try:
    from .adapters.isp_adapter import ISPSecretsAdapter
except ImportError:
    ISPSecretsAdapter = None

try:
    from .adapters.management_adapter import ManagementPlatformSecretsAdapter
except ImportError:
    ManagementPlatformSecretsAdapter = None

# Version info
__version__ = "1.0.0"
__author__ = "DotMac Team"
__email__ = "dev@dotmac.com"

# Main exports
__all__ = [
    # Core secrets management
    "EnterpriseSecretsManager",
    "SecretType",
    "SecretSource",
    "SecretValidationRule",
    "SecretMetadata",
    "SecretValidationResult",
    # Vault integration
    "OpenBaoClient",
    "VaultConfig",
    "VaultSecretMetadata",
    # Field encryption
    "EncryptedField",
    "DataClassification",
    "encrypted_field",
    "encrypt_sensitive_fields",
    "decrypt_sensitive_fields",
    "RBACManager",
    "Permission",
    "Role",
    "PermissionAction",
    "ResourceType",
    "PermissionScope",
    "PolicyEvaluationContext",
    "AccessDecision",
    # Platform adapters
    "ISPSecretsAdapter",
    "ManagementPlatformSecretsAdapter",
    # Version info
    "__version__",
]

# Configuration defaults
DEFAULT_CONFIG = {
    "vault": {
        "url": "http://localhost:8200",
        "mount_point": "secret",
        "kv_version": 2,
        "ssl_verify": True,
        "timeout": 30,
        "max_retries": 3,
        "cache_ttl": 300,
        "auth_method": "token",
    },
    "encryption": {
        "algorithm": "AES-256-GCM",
        "key_rotation_days": 90,
        "default_classification": "confidential",
    },
    "rbac": {
        "default_session_timeout": 3600,
        "max_role_depth": 5,
        "audit_all_access": True,
        "cache_policies": True,
        "policy_cache_ttl": 1800,
    },
    "compliance": {
        "frameworks": ["SOC2", "PCI_DSS", "ISO27001", "GDPR"],
        "audit_retention_days": 2555,  # 7 years
        "require_approval": True,
        "auto_rotate_critical": True,
    },
}


def get_version():
    """Get package version."""
    return __version__


def get_config():
    """Get default configuration."""
    return DEFAULT_CONFIG.copy()
