"""
Zero-Trust Security Framework for DotMac Platform

This module implements comprehensive security patterns including:
- Zero-trust network architecture
- Encryption at rest and in transit
- Comprehensive audit logging
- Role-based access control (RBAC)
- Multi-factor authentication
- Continuous security validation
"""

import warnings

from .dependencies import MISSING_DEPENDENCIES, check_security_dependencies

# Check dependencies on import
try:
    from .audit import (
        AuditContext,
        AuditEvent,
        AuditEventType,
        AuditLogger,
        AuditMetadata,
        AuditSeverity,
        AuditTrail,
    )
    from .encryption import DataClassification, EncryptionService, FieldEncryption
    from .identity import IdentityProvider, SessionManager, TokenValidator
    from .network import CertificateManager, NetworkSecurityManager, TLSManager
    from .rbac import (
        AccessDecision,
        AccessRequest,
        Permission,
        PermissionAction,
        PermissionScope,
        PolicyEngine,
        RBACManager,
        ResourceType,
        Role,
        Subject,
    )
    from .zero_trust import (
        SecurityContext,
        SecurityZone,
        TrustLevel,
        ZeroTrustManager,
        ZeroTrustPolicy,
    )

    # Check if all dependencies are available
    all_available, missing = check_security_dependencies()
    if not all_available:
        warnings.warn(
            f"Some security features may not work properly. "
            f"Missing dependencies: {missing}. "
            f"Install with: pip install {' '.join(missing)}",
            ImportWarning,
        )

except ImportError as e:
    warnings.warn(
        f"Security module import failed: {e}. "
        f"Install dependencies with: pip install structlog pydantic cryptography PyJWT",
        ImportWarning,
    )

    # Provide minimal fallback classes
    class SecurityModuleUnavailable:
        """Class for SecurityModuleUnavailable operations."""
        def __init__(self, *args, **kwargs):
            """  Init   operation."""
            raise ImportError(
                "Security module requires additional dependencies. "
                "Install with: pip install structlog pydantic cryptography PyJWT"
            )

    # Fallback exports
    ZeroTrustManager = SecurityModuleUnavailable
    ZeroTrustPolicy = SecurityModuleUnavailable
    SecurityContext = SecurityModuleUnavailable
    TrustLevel = SecurityModuleUnavailable
    SecurityZone = SecurityModuleUnavailable
    EncryptionService = SecurityModuleUnavailable
    FieldEncryption = SecurityModuleUnavailable
    DataClassification = SecurityModuleUnavailable
    AuditLogger = SecurityModuleUnavailable
    AuditEvent = SecurityModuleUnavailable
    AuditTrail = SecurityModuleUnavailable
    AuditEventType = SecurityModuleUnavailable
    AuditSeverity = SecurityModuleUnavailable
    AuditContext = SecurityModuleUnavailable
    AuditMetadata = SecurityModuleUnavailable
    RBACManager = SecurityModuleUnavailable
    Role = SecurityModuleUnavailable
    Permission = SecurityModuleUnavailable
    PolicyEngine = SecurityModuleUnavailable
    Subject = SecurityModuleUnavailable
    AccessRequest = SecurityModuleUnavailable
    AccessDecision = SecurityModuleUnavailable
    PermissionAction = SecurityModuleUnavailable
    ResourceType = SecurityModuleUnavailable
    PermissionScope = SecurityModuleUnavailable
    IdentityProvider = SecurityModuleUnavailable
    TokenValidator = SecurityModuleUnavailable
    SessionManager = SecurityModuleUnavailable
    NetworkSecurityManager = SecurityModuleUnavailable
    TLSManager = SecurityModuleUnavailable
    CertificateManager = SecurityModuleUnavailable

__all__ = [
    # Zero Trust
    "ZeroTrustManager",
    "ZeroTrustPolicy",
    "SecurityContext",
    "TrustLevel",
    "SecurityZone",
    # Encryption
    "EncryptionService",
    "FieldEncryption",
    "DataClassification",
    # Audit
    "AuditLogger",
    "AuditEvent",
    "AuditTrail",
    "AuditEventType",
    "AuditSeverity",
    "AuditContext",
    "AuditMetadata",
    # RBAC
    "RBACManager",
    "Role",
    "Permission",
    "PolicyEngine",
    "Subject",
    "AccessRequest",
    "AccessDecision",
    "PermissionAction",
    "ResourceType",
    "PermissionScope",
    # Identity
    "IdentityProvider",
    "TokenValidator",
    "SessionManager",
    # Network Security
    "NetworkSecurityManager",
    "TLSManager",
    "CertificateManager",
]
