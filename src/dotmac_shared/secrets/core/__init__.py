"""
Core secrets management components.
"""

# Handle optional dependencies gracefully
try:
    from .enterprise_secrets_manager import (
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
    from .vault_client import OpenBaoClient, VaultConfig
except ImportError as e:
    import warnings

    warnings.warn(f"Vault client not available: {e}")
    OpenBaoClient = VaultConfig = None

try:
    from .field_encryption import (
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
    from .rbac import (
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

__all__ = [
    "EnterpriseSecretsManager",
    "SecretType",
    "SecretSource",
    "SecretValidationRule",
    "SecretMetadata",
    "SecretValidationResult",
    "OpenBaoClient",
    "VaultConfig",
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
]
