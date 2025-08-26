"""
Unified secrets management for DotMac Management Platform.
Extends ISP Framework secrets manager with multi-tenant capabilities.
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel, Field
import hashlib
import uuid

# Import base secrets manager from ISP Framework
import sys
sys.path.append('/home/dotmac_framework/dotmac_isp_framework/src', timezone)
from dotmac_isp.core.secrets_manager import ()
    SecretsManager as BaseSecretsManager,
    SecretType,
    SecretMetadata,
    SecretValue,
    ReloadTrigger
)

logger = logging.getLogger(__name__)


class TenantSecretType(str, Enum):
    """Tenant-specific secret types for management platform."""
    TENANT_DATABASE_PASSWORD = "tenant_database_password"
    TENANT_API_KEY = "tenant_api_key"
    TENANT_JWT_SECRET = "tenant_jwt_secret"
    TENANT_WEBHOOK_SECRET = "tenant_webhook_secret"
    TENANT_ENCRYPTION_KEY = "tenant_encryption_key"
    PLUGIN_LICENSE_KEY = "plugin_license_key"
    KUBERNETES_SECRET = "kubernetes_secret"
    BILLING_API_KEY = "billing_api_key"


class TenantSecretMetadata(SecretMetadata):
    """Extended secret metadata for multi-tenant environment."""
    tenant_id: Optional[str] = None
    tenant_tier: Optional[str] = None
    plugin_id: Optional[str] = None
    kubernetes_namespace: Optional[str] = None
    billing_subscription_id: Optional[str] = None
    
    # Multi-tenant isolation
    isolation_level: str = "tenant"  # tenant, shared, global
    cross_tenant_access: bool = False
    
    # SaaS-specific metadata
    subscription_tier: Optional[str] = None
    usage_tracking_enabled: bool = True
    cost_center: Optional[str] = None


class MultiTenantSecretsManager(BaseSecretsManager):
    """
    Extended secrets manager for multi-tenant SaaS platform.
    Provides tenant isolation, billing integration, and plugin licensing.
    """
    
    def __init__()
        self,
        backend: str = "openbao",
        openbao_url: Optional[str] = None,
        openbao_token: Optional[str] = None,
        encryption_key: Optional[str] = None,
        local_storage_path: str = "/etc/dotmac/mgmt-secrets",
        tenant_isolation_enabled: bool = True
    ):
        """
        Initialize multi-tenant secrets manager.
        
        Args:
            backend: Secrets backend (openbao, local)
            openbao_url: OpenBao server URL
            openbao_token: OpenBao authentication token
            encryption_key: Local encryption key
            local_storage_path: Local storage path
            tenant_isolation_enabled: Enable strict tenant isolation
        """
        super().__init__()
            backend=backend,
            openbao_url=openbao_url,
            openbao_token=openbao_token,
            encryption_key=encryption_key,
            local_storage_path=local_storage_path
        )
        
        self.tenant_isolation_enabled = tenant_isolation_enabled
        self.tenant_secret_cache = {}
        self.plugin_license_cache = {}
        
    async def create_tenant_secret_namespace():
        self,
        tenant_id: str,
        tenant_tier: str = "small",
        encryption_enabled: bool = True
    ) -> Dict[str, Any]:
        """
        Create isolated secret namespace for a tenant.
        
        Args:
            tenant_id: Unique tenant identifier
            tenant_tier: Tenant subscription tier
            encryption_enabled: Enable encryption for tenant secrets
            
        Returns:
            Namespace creation result
        """
        try:
            # Create namespace path
            namespace_path = f"tenant/{tenant_id}"
            
            if self.backend == "openbao" and self._vault_client:
                # Create tenant-specific mount point
                mount_path = f"tenant-{tenant_id}"
                
                try:
                    # Enable KV secrets engine for tenant
                    self._vault_client.sys.enable_secrets_engine()
                        backend_type='kv',
                        path=mount_path,
                        options={'version': '2'}
                    )
                    
                    # Create tenant-specific policy
                    policy_name = f"tenant-{tenant_id}-policy"
                    policy_rules = f"""
                    path "{mount_path}/*" {{
                        capabilities = ["create", "read", "update", "delete", "list"]
                    }}
                    
                    path "{mount_path}/metadata/*" {{
                        capabilities = ["list", "read", "delete"]
                    }}
                    """
                    
                    self._vault_client.sys.create_or_update_policy()
                        name=policy_name,
                        policy=policy_rules
                    )
                    
                    logger.info(f"Created OpenBao namespace for tenant: {tenant_id}")
                    
                except Exception as e:
                    if "path is already in use" not in str(e):
                        raise
                    logger.info(f"OpenBao namespace already exists for tenant: {tenant_id}")
            
            # Initialize default tenant secrets
            await self._initialize_tenant_default_secrets(tenant_id, tenant_tier)
            
            return {
                "tenant_id": tenant_id,
                "namespace_path": namespace_path,
                "encryption_enabled": encryption_enabled,
                "status": "created",
                "default_secrets_count": 5
            }
            
        except Exception as e:
            logger.error(f"Failed to create tenant secret namespace for {tenant_id}: {e}")
            raise
    
    async def _initialize_tenant_default_secrets(self, tenant_id: str, tenant_tier: str):
        """Initialize default secrets for a new tenant."""
        default_secrets = [
            {
                "secret_id": f"tenant-{tenant_id}-jwt-secret",
                "secret_type": TenantSecretType.TENANT_JWT_SECRET,
                "value": self._generate_secret_value(SecretType.JWT_SECRET)
            },
            {
                "secret_id": f"tenant-{tenant_id}-api-key",
                "secret_type": TenantSecretType.TENANT_API_KEY,
                "value": f"tenant_{tenant_id}_{self._generate_secret_value(SecretType.API_KEY)}"
            },
            {
                "secret_id": f"tenant-{tenant_id}-webhook-secret",
                "secret_type": TenantSecretType.TENANT_WEBHOOK_SECRET,
                "value": self._generate_secret_value(SecretType.WEBHOOK_SECRET)
            },
            {
                "secret_id": f"tenant-{tenant_id}-encryption-key",
                "secret_type": TenantSecretType.TENANT_ENCRYPTION_KEY,
                "value": self._generate_secret_value(SecretType.ENCRYPTION_KEY)
            },
            {
                "secret_id": f"tenant-{tenant_id}-db-password",
                "secret_type": TenantSecretType.TENANT_DATABASE_PASSWORD,
                "value": self._generate_secret_value(SecretType.DATABASE_PASSWORD)
            }
        ]
        
        for secret_info in default_secrets:
            await self.store_tenant_secret()
                tenant_id=tenant_id,
                secret_id=secret_info["secret_id"],
                value=secret_info["value"],
                secret_type=secret_info["secret_type"],
                tenant_tier=tenant_tier,
                tags=["default", "initialization"]
            )
    
    async def store_tenant_secret():
        self,
        tenant_id: str,
        secret_id: str,
        value: str,
        secret_type: Union[SecretType, TenantSecretType],
        tenant_tier: str = "small",
        plugin_id: Optional[str] = None,
        kubernetes_namespace: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        rotation_interval_days: Optional[int] = None,
        tags: Optional[List[str]] = None,
        overwrite: bool = False
    ) -> TenantSecretMetadata:
        """
        Store a tenant-specific secret with proper isolation.
        
        Args:
            tenant_id: Tenant identifier
            secret_id: Secret identifier
            value: Secret value
            secret_type: Type of secret
            tenant_tier: Tenant subscription tier
            plugin_id: Associated plugin ID
            kubernetes_namespace: Kubernetes namespace
            expires_at: Expiration datetime
            rotation_interval_days: Rotation interval
            tags: Organization tags
            overwrite: Whether to overwrite existing
            
        Returns:
            TenantSecretMetadata
        """
        # Ensure tenant isolation
        if self.tenant_isolation_enabled:
            secret_id = f"tenant-{tenant_id}-{secret_id}"
        
        # Create tenant-specific metadata
        metadata = TenantSecretMetadata()
            secret_id=secret_id,
            secret_type=secret_type,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=expires_at,
            rotation_interval_days=rotation_interval_days,
            environment="production",  # Management platform is always production-grade
            service="management-platform",
            tags=tags or [],
            encrypted=True,
            tenant_id=tenant_id,
            tenant_tier=tenant_tier,
            plugin_id=plugin_id,
            kubernetes_namespace=kubernetes_namespace,
            subscription_tier=tenant_tier,
            usage_tracking_enabled=True
        )
        
        # Store using base functionality with tenant path
        await self.store_secret()
            secret_id=secret_id,
            value=value,
            secret_type=secret_type,
            environment="production",
            service=f"tenant-{tenant_id}",
            expires_at=expires_at,
            rotation_interval_days=rotation_interval_days,
            tags=tags,
            overwrite=overwrite
        )
        
        # Cache tenant secret for quick access
        if tenant_id not in self.tenant_secret_cache:
            self.tenant_secret_cache[tenant_id] = {}
        self.tenant_secret_cache[tenant_id][secret_id] = metadata
        
        logger.info(f"Stored tenant secret: {secret_id} for tenant {tenant_id}")
        return metadata
    
    async def get_tenant_secret():
        self,
        tenant_id: str,
        secret_id: str,
        verify_isolation: bool = True
    ) -> Optional[SecretValue]:
        """
        Get tenant-specific secret with isolation verification.
        
        Args:
            tenant_id: Tenant identifier
            secret_id: Secret identifier
            verify_isolation: Verify tenant isolation
            
        Returns:
            SecretValue if found and authorized
        """
        # Apply tenant isolation
        if self.tenant_isolation_enabled:
            full_secret_id = f"tenant-{tenant_id}-{secret_id}"
        else:
            full_secret_id = secret_id
        
        # Get secret using base functionality
        secret = await self.get_secret(full_secret_id)
        
        if secret and verify_isolation:
            # Verify tenant has access to this secret
            if hasattr(secret.metadata, 'tenant_id') and secret.metadata.tenant_id != tenant_id:
                logger.warning(f"Tenant isolation violation: {tenant_id} attempted to access secret for {secret.metadata.tenant_id}")
                return None
        
        return secret
    
    async def list_tenant_secrets():
        self,
        tenant_id: str,
        secret_type: Optional[Union[SecretType, TenantSecretType]] = None,
        include_expired: bool = False
    ) -> List[TenantSecretMetadata]:
        """
        List all secrets for a specific tenant.
        
        Args:
            tenant_id: Tenant identifier
            secret_type: Filter by secret type
            include_expired: Include expired secrets
            
        Returns:
            List of tenant secret metadata
        """
        # Get all secrets and filter by tenant
        all_secrets = await self.list_secrets()
            environment="production",
            service=f"tenant-{tenant_id}",
            secret_type=secret_type,
            include_expired=include_expired
        )
        
        # Convert to tenant metadata and apply additional filtering
        tenant_secrets = []
        for secret_meta in all_secrets:
            if hasattr(secret_meta, 'tenant_id') and secret_meta.tenant_id == tenant_id:
                tenant_secrets.append(TenantSecretMetadata(**secret_meta.model_dump()
            elif self.tenant_isolation_enabled and f"tenant-{tenant_id}" in secret_meta.secret_id:
                # Create tenant metadata from base metadata
                tenant_meta = TenantSecretMetadata()
                    **secret_meta.model_dump(),
                    tenant_id=tenant_id,
                    isolation_level="tenant"
                )
                tenant_secrets.append(tenant_meta)
        
        return tenant_secrets
    
    async def rotate_tenant_secret():
        self,
        tenant_id: str,
        secret_id: str,
        new_value: Optional[str] = None,
        notify_tenant: bool = True
    ) -> TenantSecretMetadata:
        """
        Rotate a tenant-specific secret and optionally notify tenant.
        
        Args:
            tenant_id: Tenant identifier
            secret_id: Secret to rotate
            new_value: New secret value
            notify_tenant: Whether to notify tenant of rotation
            
        Returns:
            Updated metadata
        """
        # Apply tenant isolation
        if self.tenant_isolation_enabled:
            full_secret_id = f"tenant-{tenant_id}-{secret_id}"
        else:
            full_secret_id = secret_id
        
        # Rotate using base functionality
        base_metadata = await self.rotate_secret(full_secret_id, new_value)
        
        # Create tenant metadata
        tenant_metadata = TenantSecretMetadata()
            **base_metadata.model_dump(),
            tenant_id=tenant_id,
            last_rotated=datetime.now(timezone.utc)
        )
        
        # Update cache
        if tenant_id in self.tenant_secret_cache:
            self.tenant_secret_cache[tenant_id][full_secret_id] = tenant_metadata
        
        # Notify tenant if requested
        if notify_tenant:
            await self._notify_tenant_secret_rotation(tenant_id, secret_id)
        
        logger.info(f"Rotated tenant secret: {secret_id} for tenant {tenant_id}")
        return tenant_metadata
    
    async def delete_tenant_namespace():
        self,
        tenant_id: str,
        backup_secrets: bool = True,
        force_delete: bool = False
    ) -> Dict[str, Any]:
        """
        Delete entire tenant secret namespace.
        
        Args:
            tenant_id: Tenant identifier
            backup_secrets: Create backup before deletion
            force_delete: Force deletion without backup
            
        Returns:
            Deletion result
        """
        try:
            deleted_secrets = []
            
            if backup_secrets and not force_delete:
                # Create backup of all tenant secrets
                tenant_secrets = await self.list_tenant_secrets(tenant_id, include_expired=True)
                backup_data = {
                    "tenant_id": tenant_id,
                    "backup_timestamp": datetime.now(timezone.utc).isoformat(),
                    "secrets_count": len(tenant_secrets),
                    "secrets": [secret.model_dump() for secret in tenant_secrets]
                }
                
                # Store backup
                backup_path = f"/var/backups/dotmac/tenant-secrets/{tenant_id}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.json"
                os.makedirs(os.path.dirname(backup_path), exist_ok=True)
                with open(backup_path, 'w') as f:
                    json.dump(backup_data, f, indent=2, default=str)
                
                logger.info(f"Created tenant secrets backup: {backup_path}")
            
            # Delete all tenant secrets
            tenant_secrets = await self.list_tenant_secrets(tenant_id, include_expired=True)
            for secret_meta in tenant_secrets:
                try:
                    success = await self.delete_secret(secret_meta.secret_id)
                    if success:
                        deleted_secrets.append(secret_meta.secret_id)
                except Exception as e:
                    logger.warning(f"Failed to delete secret {secret_meta.secret_id}: {e}")
            
            # Clean up OpenBao namespace if using OpenBao
            if self.backend == "openbao" and self._vault_client:
                try:
                    mount_path = f"tenant-{tenant_id}"
                    self._vault_client.sys.disable_secrets_engine(path=mount_path)
                    
                    # Delete tenant policy
                    policy_name = f"tenant-{tenant_id}-policy"
                    self._vault_client.sys.delete_policy(name=policy_name)
                    
                    logger.info(f"Deleted OpenBao namespace for tenant: {tenant_id}")
                    
                except Exception as e:
                    logger.warning(f"Failed to cleanup OpenBao namespace for {tenant_id}: {e}")
            
            # Clean up cache
            if tenant_id in self.tenant_secret_cache:
                del self.tenant_secret_cache[tenant_id]
            
            return {
                "tenant_id": tenant_id,
                "deleted_secrets": deleted_secrets,
                "deleted_count": len(deleted_secrets),
                "backup_created": backup_secrets and not force_delete,
                "status": "deleted"
            }
            
        except Exception as e:
            logger.error(f"Failed to delete tenant namespace for {tenant_id}: {e}")
            raise
    
    async def create_plugin_license_secret():
        self,
        tenant_id: str,
        plugin_id: str,
        license_key: str,
        license_tier: str,
        expires_at: Optional[datetime] = None
    ) -> TenantSecretMetadata:
        """
        Create plugin license secret for tenant.
        
        Args:
            tenant_id: Tenant identifier
            plugin_id: Plugin identifier
            license_key: Plugin license key
            license_tier: License tier (free, basic, premium, enterprise)
            expires_at: License expiration
            
        Returns:
            License secret metadata
        """
        secret_id = f"plugin-{plugin_id}-license"
        
        # Store license secret
        metadata = await self.store_tenant_secret()
            tenant_id=tenant_id,
            secret_id=secret_id,
            value=license_key,
            secret_type=TenantSecretType.PLUGIN_LICENSE_KEY,
            plugin_id=plugin_id,
            expires_at=expires_at,
            tags=["plugin", "license", license_tier]
        )
        
        # Cache for billing/usage tracking
        if tenant_id not in self.plugin_license_cache:
            self.plugin_license_cache[tenant_id] = {}
        
        self.plugin_license_cache[tenant_id][plugin_id] = {
            "license_key": license_key,
            "license_tier": license_tier,
            "expires_at": expires_at,
            "secret_id": secret_id
        }
        
        logger.info(f"Created plugin license secret for tenant {tenant_id}, plugin {plugin_id}")
        return metadata
    
    async def validate_plugin_license():
        self,
        tenant_id: str,
        plugin_id: str
    ) -> Dict[str, Any]:
        """
        Validate plugin license for tenant.
        
        Args:
            tenant_id: Tenant identifier
            plugin_id: Plugin identifier
            
        Returns:
            License validation result
        """
        try:
            # Get license secret
            secret_id = f"plugin-{plugin_id}-license"
            license_secret = await self.get_tenant_secret(tenant_id, secret_id)
            
            if not license_secret:
                return {
                    "valid": False,
                    "reason": "License not found",
                    "plugin_id": plugin_id,
                    "tenant_id": tenant_id
                }
            
            # Check expiration
            if hasattr(license_secret.metadata, 'expires_at') and license_secret.metadata.expires_at:
                if license_secret.metadata.expires_at < datetime.now(timezone.utc):
                    return {
                        "valid": False,
                        "reason": "License expired",
                        "expired_at": license_secret.metadata.expires_at,
                        "plugin_id": plugin_id,
                        "tenant_id": tenant_id
                    }
            
            # Validate license key format
            license_key = license_secret.value
            if not license_key or len(license_key) < 10:
                return {
                    "valid": False,
                    "reason": "Invalid license key format",
                    "plugin_id": plugin_id,
                    "tenant_id": tenant_id
                }
            
            return {
                "valid": True,
                "license_key": license_key,
                "plugin_id": plugin_id,
                "tenant_id": tenant_id,
                "expires_at": getattr(license_secret.metadata, 'expires_at', None),
                "license_tier": getattr(license_secret.metadata, 'subscription_tier', 'unknown')
            }
            
        except Exception as e:
            logger.error(f"Failed to validate plugin license for tenant {tenant_id}, plugin {plugin_id}: {e}")
            return {
                "valid": False,
                "reason": f"Validation error: {e}",
                "plugin_id": plugin_id,
                "tenant_id": tenant_id
            }
    
    async def _notify_tenant_secret_rotation(self, tenant_id: str, secret_id: str):
        """Notify tenant of secret rotation (placeholder for integration)."""
        logger.info(f"Secret rotation notification for tenant {tenant_id}: {secret_id}")
        # This would integrate with notification system
    
    async def get_tenant_secrets_health(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get health status of tenant secrets.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Health status
        """
        try:
            tenant_secrets = await self.list_tenant_secrets(tenant_id, include_expired=True)
            
            total_secrets = len(tenant_secrets)
            expired_secrets = 0
            rotation_due = 0
            
            now = datetime.now(timezone.utc)
            
            for secret in tenant_secrets:
                # Check expiration
                if secret.expires_at and secret.expires_at < now:
                    expired_secrets += 1
                
                # Check rotation due
                if (secret.rotation_interval_days and secret.last_rotated and
                    secret.last_rotated + timedelta(days=secret.rotation_interval_days) < now):
                    rotation_due += 1
            
            # Determine health status
            if expired_secrets > 0:
                health_status = "critical"
            elif rotation_due > 0:
                health_status = "warning"
            else:
                health_status = "healthy"
            
            return {
                "tenant_id": tenant_id,
                "health_status": health_status,
                "total_secrets": total_secrets,
                "expired_secrets": expired_secrets,
                "rotation_due": rotation_due,
                "last_check": now.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to check tenant secrets health for {tenant_id}: {e}")
            return {
                "tenant_id": tenant_id,
                "health_status": "error",
                "error": str(e),
                "last_check": datetime.now(timezone.utc).isoformat()
            }


# Global multi-tenant secrets manager instance
_mt_secrets_manager: Optional[MultiTenantSecretsManager] = None


def get_mt_secrets_manager() -> MultiTenantSecretsManager:
    """Get global multi-tenant secrets manager instance."""
    global _mt_secrets_manager
    if _mt_secrets_manager is None:
        _mt_secrets_manager = MultiTenantSecretsManager()
    return _mt_secrets_manager


def init_mt_secrets_manager()
    backend: str = "openbao",
    openbao_url: Optional[str] = None,
    openbao_token: Optional[str] = None,
    encryption_key: Optional[str] = None,
    tenant_isolation_enabled: bool = True
) -> MultiTenantSecretsManager:
    """Initialize global multi-tenant secrets manager."""
    global _mt_secrets_manager
    _mt_secrets_manager = MultiTenantSecretsManager()
        backend=backend,
        openbao_url=openbao_url,
        openbao_token=openbao_token,
        encryption_key=encryption_key,
        tenant_isolation_enabled=tenant_isolation_enabled
    )
    return _mt_secrets_manager