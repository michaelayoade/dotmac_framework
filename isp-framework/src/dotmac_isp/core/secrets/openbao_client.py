"""
OpenBao Integration for Secrets Management

Provides secure secrets management using OpenBao (open-source fork of HashiCorp Vault).
This module extends the existing openbao_client.py to support both Vault and OpenBao.
"""

import os
from typing import Any

# Import native OpenBao client
from .openbao_native_client import (
    OpenBaoClient as NativeOpenBaoClient,
    OpenBaoConfig as NativeOpenBaoConfig,
    OpenBaoSecretManager as NativeOpenBaoSecretManager,
    SecretMetadata,
    OpenBaoAPIException,
    create_openbao_client,
    create_secret_manager as create_native_secret_manager
)

# OpenBao is API-compatible with Vault, so we can reuse the existing client
# with minor configuration adjustments


class OpenBaoConfig(NativeOpenBaoConfig):
    """OpenBao-specific configuration settings"""

    def __init__(self, **kwargs):
        """Initialize OpenBao configuration."""
        # Set OpenBao-specific defaults
        kwargs.setdefault("url", os.getenv("OPENBAO_ADDR", "http://localhost:8200"))
        kwargs.setdefault("token", os.getenv("OPENBAO_TOKEN", os.getenv("BAO_TOKEN", "")))

        # OpenBao uses the same environment variables as Vault for compatibility
        # but we check for OpenBao-specific ones first
        super().__init__(**kwargs)


class OpenBaoClient(NativeOpenBaoClient):
    """
    OpenBao client for secure secrets management.

    This client is fully compatible with the OpenBaoClient API, allowing
    seamless migration from HashiCorp Vault to OpenBao.

    Features:
    - Full API compatibility with HashiCorp Vault
    - Same authentication methods (Token, AppRole, Kubernetes, AWS)
    - Identical secret management operations
    - Drop-in replacement for OpenBaoClient
    """

    def __init__(self, config: OpenBaoConfig | None = None):
        """Initialize OpenBao client with configuration"""
        if config is None:
            config = self._load_openbao_config()
        super().__init__(config)

    def _load_openbao_config(self) -> OpenBaoConfig:
        """Load OpenBao configuration from environment variables"""
        return OpenBaoConfig(
            url=os.getenv(
                "OPENBAO_ADDR", os.getenv("VAULT_ADDR", "http://localhost:8200")
            ),
            token=os.getenv(
                "OPENBAO_TOKEN", os.getenv("BAO_TOKEN", os.getenv("VAULT_TOKEN"))
            ),
            namespace=os.getenv("OPENBAO_NAMESPACE", os.getenv("VAULT_NAMESPACE")),
            mount_point=os.getenv(
                "OPENBAO_MOUNT_POINT", os.getenv("VAULT_MOUNT_POINT", "secret")
            ),
            kv_version=int(
                os.getenv("OPENBAO_KV_VERSION", os.getenv("VAULT_KV_VERSION", "2"))
            ),
            auth_method=os.getenv(
                "OPENBAO_AUTH_METHOD", os.getenv("VAULT_AUTH_METHOD", "token")
            ),
            role_id=os.getenv("OPENBAO_ROLE_ID", os.getenv("VAULT_ROLE_ID")),
            secret_id=os.getenv("OPENBAO_SECRET_ID", os.getenv("VAULT_SECRET_ID")),
            kubernetes_role=os.getenv(
                "OPENBAO_KUBERNETES_ROLE", os.getenv("VAULT_KUBERNETES_ROLE")
            ),
            aws_role=os.getenv("OPENBAO_AWS_ROLE", os.getenv("VAULT_AWS_ROLE")),
        )

    async def health_check(self) -> dict[str, Any]:
        """Check OpenBao health status"""
        health = await super().health_check()
        # Add OpenBao-specific information
        health["backend"] = "OpenBao"
        health["api_compatible"] = True
        return health


class OpenBaoSecretManager(NativeOpenBaoSecretManager):
    """
    High-level secret manager using OpenBao.

    Provides the same interface as VaultSecretManager, ensuring
    compatibility for applications migrating from Vault to OpenBao.
    """

    def __init__(self, openbao_client: OpenBaoClient | None = None):
        """Initialize the OpenBao secret manager"""
        if openbao_client is None:
            openbao_client = OpenBaoClient()
        super().__init__(openbao_client)


# Factory functions for unified interface
def get_secret_backend() -> OpenBaoClient:
    """
    Get the appropriate secret backend based on configuration.

    Returns OpenBaoClient if OPENBAO_ADDR is set, otherwise OpenBaoClient.
    This allows automatic selection of the backend without code changes.
    """
    # Always return OpenBao client since we've migrated away from Vault
    return OpenBaoClient()


def get_unified_secret_manager() -> OpenBaoSecretManager:
    """
    Get the appropriate secret manager based on configuration.

    Returns OpenBaoSecretManager if OpenBao is configured, otherwise VaultSecretManager.
    """
    # Always return OpenBao secret manager since we've migrated away from Vault
    return OpenBaoSecretManager()


# Migration utilities
async def migrate_secrets_to_openbao(
    source_client: OpenBaoClient,
    target_client: OpenBaoClient,
    paths: list[str] | None = None,
) -> dict[str, Any]:
    """
    Migrate secrets from HashiCorp Vault to OpenBao.

    Args:
        source_client: OpenBaoClient instance (source)
        target_client: OpenBaoClient instance (target)
        paths: List of secret paths to migrate (None = migrate all)

    Returns:
        Migration statistics
    """
    stats = {"migrated": 0, "failed": 0, "errors": []}

    # If no paths specified, list all secrets
    if paths is None:
        paths = await source_client.list_secrets()

    for path in paths:
        try:
            # Read from source
            secret_data = await source_client.get_secret(path, use_cache=False)

            # Write to target
            await target_client.set_secret(path, secret_data)

            stats["migrated"] += 1
        except Exception as e:
            stats["failed"] += 1
            stats["errors"].append({"path": path, "error": str(e)})

    return stats


async def verify_migration(
    source_client: OpenBaoClient,
    target_client: OpenBaoClient,
    paths: list[str],
) -> dict[str, Any]:
    """
    Verify that secrets were correctly migrated.

    Args:
        source_client: OpenBaoClient instance (source)
        target_client: OpenBaoClient instance (target)
        paths: List of secret paths to verify

    Returns:
        Verification results
    """
    results = {"verified": 0, "mismatched": 0, "missing": 0, "details": []}

    for path in paths:
        try:
            source_data = await source_client.get_secret(path, use_cache=False)
            target_data = await target_client.get_secret(path, use_cache=False)

            if source_data == target_data:
                results["verified"] += 1
            else:
                results["mismatched"] += 1
                results["details"].append({"path": path, "issue": "data_mismatch"})
        except KeyError:
            results["missing"] += 1
            results["details"].append({"path": path, "issue": "missing_in_target"})
        except Exception as e:
            results["details"].append(
                {"path": path, "issue": "verification_error", "error": str(e)}
            )

    return results


__all__ = [
    # OpenBao-specific classes
    "OpenBaoConfig",
    "OpenBaoClient",
    "OpenBaoSecretManager",
    # Unified interface
    "get_secret_backend",
    "get_unified_secret_manager",
    # Migration utilities
    "migrate_secrets_to_openbao",
    "verify_migration",
    # Native OpenBao components
    "NativeOpenBaoClient",
    "NativeOpenBaoConfig", 
    "NativeOpenBaoSecretManager",
    "SecretMetadata",
    "OpenBaoAPIException",
]
