"""
Secrets SDK for Platform using contract-first design with Pydantic v2.

Provides secure secrets management with encryption, rotation, audit logging,
and comprehensive access control.
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from typing import Any

from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession

from dotmac_isp.sdks.contracts.secrets import (
    Secret,
    SecretAccessLogEntry,
    SecretAuditRequest,
    SecretAuditResponse,
    SecretCreateRequest,
    SecretGetRequest,
    SecretGetResponse,
    SecretListRequest,
    SecretListResponse,
    SecretMetadata,
    SecretRotateRequest,
    SecretRotateResponse,
    SecretStatsResponse,
    SecretStatus,
    SecretType,
    SecretUpdateRequest,
    SecretValue,
)
from dotmac_isp.sdks.contracts.transport import RequestContext
from dotmac_isp.sdks.platform.repositories.secrets import (
    SecretAccessLogRepository,
    SecretRepository,
    SecretVersionRepository,
)
from dotmac_isp.sdks.platform.services.encryption import EncryptionService
from dotmac_isp.sdks.platform.utils.datetime_compat import UTC

logger = logging.getLogger(__name__)


class SecretsError(Exception):
    """Base secrets error."""

    pass


class SecretNotFoundError(SecretsError):
    """Secret not found error."""

    pass


class SecretAccessDeniedError(SecretsError):
    """Secret access denied error."""

    pass


class SecretExpiredError(SecretsError):
    """Secret expired error."""

    pass


class SecretsSDKConfig:
    """Secrets SDK configuration."""

    def __init__(self, *args, **kwargs):
        """Initialize operation."""
        self.master_encryption_key = master_encryption_key
        self.cache_ttl = cache_ttl
        self.enable_caching = enable_caching
        self.enable_audit_logging = enable_audit_logging
        self.max_secret_size = max_secret_size
        self.default_expiry_days = default_expiry_days
        self.auto_rotate_warning_days = auto_rotate_warning_days
        self.max_versions = max_versions


class SecretsSDK:
    """
    Contract-first Secrets SDK with comprehensive secrets management.

    Features:
    - AES-256 encryption for secret values
    - Automatic secret rotation
    - Comprehensive audit logging
    - Version management
    - Tenant isolation
    - Access control integration
    - Expiration management
    - Secure random generation
    """

    def __init__(
        self,
        db_session: AsyncSession,
        config: SecretsSDKConfig | None = None,
        cache_sdk: Any | None = None,
    ):
        """Initialize Secrets SDK."""
        self.config = config or SecretsSDKConfig()
        self.db_session = db_session
        self.cache_sdk = cache_sdk

        # Initialize encryption service
        self.encryption = EncryptionService(self.config.master_encryption_key)

        # Repositories
        self.secret_repo = SecretRepository(db_session)
        self.version_repo = SecretVersionRepository(db_session)
        self.access_log_repo = SecretAccessLogRepository(db_session)

        # Performance tracking
        self._stats = {
            "secrets_created": 0,
            "secrets_accessed": 0,
            "secrets_rotated": 0,
            "access_denied": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }

        logger.info("SecretsSDK initialized with database backend")

    async def _get_cache_key(
        self, key_type: str, identifier: str, tenant_id: str | None = None
    ) -> str:
        """Generate cache key with tenant isolation."""
        tenant_prefix = f"tenant:{tenant_id}:" if tenant_id else "global:"
        return f"secrets:{tenant_prefix}{key_type}:{identifier}"

    async def _cache_get(self, key: str) -> Any | None:
        """Get value from cache."""
        if not self.cache_sdk or not self.config.enable_caching:
            return None

        try:
            result = await self.cache_sdk.get(key)
            if result is not None:
                self._stats["cache_hits"] += 1
            else:
                self._stats["cache_misses"] += 1
            return result
        except Exception as e:
            logger.warning(f"Cache get failed for key {key}: {e}")
            self._stats["cache_misses"] += 1
            return None

    async def _cache_set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value in cache."""
        if not self.cache_sdk or not self.config.enable_caching:
            return

        try:
            await self.cache_sdk.set(key, value, ttl or self.config.cache_ttl)
        except Exception as e:
            logger.warning(f"Cache set failed for key {key}: {e}")

    async def _cache_delete(self, key: str) -> None:
        """Delete value from cache."""
        if not self.cache_sdk or not self.config.enable_caching:
            return

        try:
            await self.cache_sdk.delete(key)
        except Exception as e:
            logger.warning(f"Cache delete failed for key {key}: {e}")

    def _encrypt_value(self, value: str) -> str:
        """Encrypt secret value."""
        return self.encryption.encrypt(value)

    def _decrypt_value(self, encrypted_value: str) -> str:
        """Decrypt secret value."""
        return self.encryption.decrypt(encrypted_value)

    def _generate_checksum(self, value: str) -> str:
        """Generate checksum for secret value."""
        return f"sha256:{hashlib.sha256(value.encode()).hexdigest()}"

    def _generate_secret_value(self, secret_type: SecretType, length: int = 32) -> str:
        """Generate secure random secret value."""
        if secret_type == SecretType.PASSWORD:
            # Generate password with mixed case, numbers, and symbols
            chars = (
                "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
            )
            return "".join(secrets.choice(chars) for _ in range(length))
        elif secret_type == SecretType.API_KEY:
            # Generate API key format
            return f"ak_{secrets.token_urlsafe(24)}"
        elif secret_type == SecretType.TOKEN:
            # Generate JWT-like token
            return secrets.token_urlsafe(32)
        else:
            # Generate generic secure random string
            return secrets.token_urlsafe(length)

    async def _log_access(
        self,
        secret_id: str,
        secret_name: str,
        access_type: str,
        success: bool,
        context: RequestContext | None = None,
        error_message: str | None = None,
    ) -> None:
        """Log secret access for audit."""
        if not self.config.enable_audit_logging:
            return

        log_entry = SecretAccessLogEntry(
            secret_id=secret_id,
            secret_name=secret_name,
            accessed_by=context.user_id if context else "system",
            accessed_at=datetime.now(UTC),
            access_type=access_type,
            ip_address=getattr(context, "ip_address", None) if context else None,
            user_agent=getattr(context, "user_agent", None) if context else None,
            success=success,
            error_message=error_message,
        )

        self._access_logs.append(log_entry)

        # Log to system logger
        logger.info(
            f"Secret access: id={secret_id}, name={secret_name}, "
            f"type={access_type}, user={context.user_id if context else 'system'}, "
            f"success={success}, error={error_message}"
        )

    async def create_secret(
        self,
        request: SecretCreateRequest,
        context: RequestContext | None = None,
    ) -> Secret:
        """Create a new secret."""
        try:
            tenant_id = context.tenant_id if context else "global"
            user_id = context.user_id if context else "system"

            # Validate secret value size and content
            secret_value = request.value.get_secret_value()
            if len(secret_value.encode()) > self.config.max_secret_size:
                raise SecretsError(
                    f"Secret value exceeds maximum size of {self.config.max_secret_size} bytes"
                )

            # Validate secret content (no null bytes, basic sanitization)
            if "\x00" in secret_value:
                raise SecretsError("Secret value cannot contain null bytes")

            # Validate secret name format
            if not request.name or not request.name.strip():
                raise SecretsError("Secret name cannot be empty")

            if len(request.name) > 255:
                raise SecretsError("Secret name cannot exceed 255 characters")

            # Check for valid name characters (alphanumeric, underscore, hyphen, dot)
            import re

            if not re.match(r"^[a-zA-Z0-9._-]+$", request.name):
                raise SecretsError(
                    "Secret name can only contain letters, numbers, underscore, hyphen, and dot"
                )

            # Generate secret ID
            secret_id = f"secret-{len(self._secrets) + 1}"

            # Create metadata
            metadata = SecretMetadata(
                name=request.name,
                description=request.description,
                type=request.type,
                tags=request.tags,
                created_by=user_id,
                expires_at=request.expires_at,
            )

            # Encrypt secret value
            encrypted_value = self._encrypt_value(secret_value)
            checksum = self._generate_checksum(secret_value)

            # Create secret
            secret = Secret(
                id=secret_id,
                tenant_id=tenant_id,
                metadata=metadata,
                version=1,
                checksum=checksum,
            )

            # Store encrypted secret
            secret_value_obj = SecretValue(
                secret=secret,
                value=request.value,
                previous_versions=[],
            )

            self._secrets[secret_id] = secret_value_obj
            self._stats["secrets_created"] += 1

            # Log access
            await self._log_access(
                secret_id=secret_id,
                secret_name=request.name,
                access_type="create",
                success=True,
                context=context,
            )

            logger.info(
                f"Secret created: id={secret_id}, name={request.name}, "
                f"type={request.type}, tenant={tenant_id}, created_by={user_id}"
            )

            return secret

        except Exception as e:
            logger.error(f"Secret creation failed: {e}")
            await self._log_access(
                secret_id="unknown",
                secret_name=request.name,
                access_type="create",
                success=False,
                context=context,
                error_message=str(e),
            )
            raise SecretsError(f"Failed to create secret: {str(e)}")

    async def get_secret(
        self,
        request: SecretGetRequest,
        context: RequestContext | None = None,
    ) -> SecretGetResponse:
        """Get secret by ID."""
        try:
            tenant_id = context.tenant_id if context else "global"

            # Get secret
            secret_value_obj = self._secrets.get(request.secret_id)
            if not secret_value_obj:
                raise SecretNotFoundError(f"Secret {request.secret_id} not found")

            secret = secret_value_obj.secret

            # Check tenant isolation
            if tenant_id not in (secret.tenant_id, "global"):
                raise SecretAccessDeniedError(
                    "Access denied: secret belongs to different tenant"
                )

            # Check if secret is expired
            if (
                secret.metadata.expires_at
                and secret.metadata.expires_at < datetime.now(UTC)
            ):
                raise SecretExpiredError(f"Secret {request.secret_id} has expired")

            # Check if secret is active
            if secret.metadata.status != SecretStatus.ACTIVE:
                raise SecretAccessDeniedError(
                    f"Secret {request.secret_id} is not active"
                )

            self._stats["secrets_accessed"] += 1

            # Prepare response
            response = SecretGetResponse(
                secret=secret,
                value=None,
                access_logged=True,
            )

            # Include value if requested
            if not getattr(request, "include_metadata_only", False):
                decrypted_value = self._decrypt_value(
                    secret_value_obj.value.get_secret_value()
                )
                response.value = decrypted_value

            # Log access
            await self._log_access(
                secret_id=request.secret_id,
                secret_name=secret.metadata.name,
                access_type="read",
                success=True,
                context=context,
            )

            return response

        except (SecretNotFoundError, SecretAccessDeniedError, SecretExpiredError) as e:
            self._stats["access_denied"] += 1
            await self._log_access(
                secret_id=request.secret_id,
                secret_name="unknown",
                access_type="read",
                success=False,
                context=context,
                error_message=str(e),
            )
            raise
        except Exception as e:
            logger.error(f"Secret retrieval failed: {e}")
            await self._log_access(
                secret_id=request.secret_id,
                secret_name="unknown",
                access_type="read",
                success=False,
                context=context,
                error_message=str(e),
            )
            raise SecretsError(f"Failed to retrieve secret: {str(e)}")

    async def update_secret(  # noqa: C901
        self,
        secret_id: str,
        request: SecretUpdateRequest,
        context: RequestContext | None = None,
    ) -> Secret:
        """Update secret."""
        try:
            tenant_id = context.tenant_id if context else "global"

            # Get existing secret
            secret_value_obj = self._secrets.get(secret_id)
            if not secret_value_obj:
                raise SecretNotFoundError(f"Secret {secret_id} not found")

            secret = secret_value_obj.secret

            # Check tenant isolation
            if tenant_id not in (secret.tenant_id, "global"):
                raise SecretAccessDeniedError(
                    "Access denied: secret belongs to different tenant"
                )

            # Update metadata
            if request.description is not None:
                secret.metadata.description = request.description

            if request.tags is not None:
                secret.metadata.tags = request.tags

            if request.expires_at is not None:
                secret.metadata.expires_at = request.expires_at

            if request.status is not None:
                secret.metadata.status = request.status

            # Update value if provided
            if request.value is not None:
                # Store previous version
                previous_version = {
                    "version": secret.version,
                    "value": secret_value_obj.value.get_secret_value(),
                    "checksum": secret.checksum,
                    "updated_at": secret.metadata.updated_at.isoformat(),
                }
                secret_value_obj.previous_versions.append(previous_version)

                # Limit version history
                if len(secret_value_obj.previous_versions) > self.config.max_versions:
                    secret_value_obj.previous_versions.pop(0)

                # Update to new value
                new_value = request.value.get_secret_value()
                secret_value_obj.value = request.value
                secret.checksum = self._generate_checksum(new_value)
                secret.version += 1

            secret.metadata.updated_at = datetime.now(UTC)

            # Store updated secret
            self._secrets[secret_id] = secret_value_obj

            # Clear cache
            cache_key = await self._get_cache_key("secret", secret_id, tenant_id)
            await self._cache_delete(cache_key)

            # Log access
            await self._log_access(
                secret_id=secret_id,
                secret_name=secret.metadata.name,
                access_type="update",
                success=True,
                context=context,
            )

            return secret

        except (SecretNotFoundError, SecretAccessDeniedError) as e:
            await self._log_access(
                secret_id=secret_id,
                secret_name="unknown",
                access_type="update",
                success=False,
                context=context,
                error_message=str(e),
            )
            raise
        except Exception as e:
            logger.error(f"Secret update failed: {e}")
            await self._log_access(
                secret_id=secret_id,
                secret_name="unknown",
                access_type="update",
                success=False,
                context=context,
                error_message=str(e),
            )
            raise SecretsError(f"Failed to update secret: {str(e)}")

    async def rotate_secret(
        self,
        request: SecretRotateRequest,
        context: RequestContext | None = None,
    ) -> SecretRotateResponse:
        """Rotate secret value."""
        try:
            tenant_id = context.tenant_id if context else "global"

            # Get existing secret
            secret_value_obj = self._secrets.get(request.secret_id)
            if not secret_value_obj:
                raise SecretNotFoundError(f"Secret {request.secret_id} not found")

            secret = secret_value_obj.secret

            # Check tenant isolation
            if tenant_id not in (secret.tenant_id, "global"):
                raise SecretAccessDeniedError(
                    "Access denied: secret belongs to different tenant"
                )

            # Check if rotation is needed (unless forced)
            if not request.force:
                # Check if secret has auto-rotation enabled
                # For now, always allow rotation
                pass

            # Generate or use provided new value
            if request.new_value:
                new_value = request.new_value.get_secret_value()
            else:
                new_value = self._generate_secret_value(secret.metadata.type)

            # Store previous version
            previous_version = {
                "version": secret.version,
                "value": secret_value_obj.value.get_secret_value(),
                "checksum": secret.checksum,
                "rotated_at": datetime.now(UTC).isoformat(),
            }
            secret_value_obj.previous_versions.append(previous_version)

            # Limit version history
            if len(secret_value_obj.previous_versions) > self.config.max_versions:
                secret_value_obj.previous_versions.pop(0)

            # Update to new value
            from pydantic import SecretStr

            secret_value_obj.value = SecretStr(new_value)
            secret.checksum = self._generate_checksum(new_value)
            secret.version += 1
            secret.metadata.updated_at = datetime.now(UTC)

            # Store updated secret
            self._secrets[request.secret_id] = secret_value_obj
            self._stats["secrets_rotated"] += 1

            # Clear cache
            cache_key = await self._get_cache_key(
                "secret", request.secret_id, tenant_id
            )
            await self._cache_delete(cache_key)

            # Log access
            await self._log_access(
                secret_id=request.secret_id,
                secret_name=secret.metadata.name,
                access_type="rotate",
                success=True,
                context=context,
            )

            return SecretRotateResponse(
                secret=secret,
                rotated=True,
                new_version=secret.version,
            )

        except (SecretNotFoundError, SecretAccessDeniedError) as e:
            await self._log_access(
                secret_id=request.secret_id,
                secret_name="unknown",
                access_type="rotate",
                success=False,
                context=context,
                error_message=str(e),
            )
            raise
        except Exception as e:
            logger.error(f"Secret rotation failed: {e}")
            await self._log_access(
                secret_id=request.secret_id,
                secret_name="unknown",
                access_type="rotate",
                success=False,
                context=context,
                error_message=str(e),
            )
            raise SecretsError(f"Failed to rotate secret: {str(e)}")

    async def list_secrets(
        self,
        request: SecretListRequest,
        context: RequestContext | None = None,
    ) -> SecretListResponse:
        """List secrets with filtering."""
        tenant_id = context.tenant_id if context else "global"

        # Get all secrets for tenant
        secrets = []
        for secret_value_obj in self._secrets.values():
            secret = secret_value_obj.secret

            # Check tenant isolation
            if tenant_id not in (secret.tenant_id, "global"):
                continue

            secrets.append(secret)

        # Apply filters
        if request.type is not None:
            secrets = [s for s in secrets if s.metadata.type == request.type]

        if request.status is not None:
            secrets = [s for s in secrets if s.metadata.status == request.status]

        if request.tags:
            secrets = [
                s
                for s in secrets
                if all(tag in s.metadata.tags for tag in request.tags)
            ]

        if request.search:
            search_lower = request.search.lower()
            secrets = [
                s
                for s in secrets
                if search_lower in s.metadata.name.lower()
                or (
                    s.metadata.description
                    and search_lower in s.metadata.description.lower()
                )
            ]

        if request.expires_within_days is not None:
            cutoff_date = datetime.now(UTC) + timedelta(
                days=request.expires_within_days
            )
            secrets = [
                s
                for s in secrets
                if s.metadata.expires_at and s.metadata.expires_at <= cutoff_date
            ]

        if request.created_by is not None:
            secrets = [
                s for s in secrets if s.metadata.created_by == request.created_by
            ]

        # Apply pagination
        total = len(secrets)
        start_idx = (request.page - 1) * request.page_size
        end_idx = start_idx + request.page_size
        paginated_secrets = secrets[start_idx:end_idx]

        return SecretListResponse(
            secrets=paginated_secrets,
            page=request.page,
            page_size=request.page_size,
            total=total,
            has_next=end_idx < total,
        )

    async def get_audit_log(
        self,
        request: SecretAuditRequest,
        context: RequestContext | None = None,
    ) -> SecretAuditResponse:
        """Get secret access audit log."""
        entries = self._access_logs.model_copy()

        # Apply filters
        if request.secret_id:
            entries = [e for e in entries if e.secret_id == request.secret_id]

        if request.accessed_by:
            entries = [e for e in entries if e.accessed_by == request.accessed_by]

        if request.access_type:
            entries = [e for e in entries if e.access_type == request.access_type]

        if request.start_date:
            entries = [e for e in entries if e.accessed_at >= request.start_date]

        if request.end_date:
            entries = [e for e in entries if e.accessed_at <= request.end_date]

        # Sort by access time (newest first)
        entries.sort(key=lambda e: e.accessed_at, reverse=True)

        # Apply pagination
        total = len(entries)
        start_idx = (request.page - 1) * request.page_size
        end_idx = start_idx + request.page_size
        paginated_entries = entries[start_idx:end_idx]

        return SecretAuditResponse(
            entries=paginated_entries,
            page=request.page,
            page_size=request.page_size,
            total=total,
            has_next=end_idx < total,
        )

    async def get_stats(self) -> SecretStatsResponse:
        """Get secrets statistics."""
        secrets = list(self._secrets.values())

        # Count by type
        secrets_by_type = {}
        for secret_type in SecretType:
            secrets_by_type[secret_type.value] = len(
                [s for s in secrets if s.secret.metadata.type == secret_type]
            )

        # Count by status
        secrets_by_status = {}
        for status in SecretStatus:
            secrets_by_status[status.value] = len(
                [s for s in secrets if s.secret.metadata.status == status]
            )

        # Count expiring soon
        cutoff_date = datetime.now(UTC) + timedelta(days=30)
        expiring_soon = len(
            [
                s
                for s in secrets
                if s.secret.metadata.expires_at
                and s.secret.metadata.expires_at <= cutoff_date
            ]
        )

        # Count auto-rotate enabled (placeholder)
        auto_rotate_enabled = 0  # Would be tracked in metadata

        # Count recent accesses
        recent_cutoff = datetime.now(UTC) - timedelta(hours=24)
        recent_access_count = len(
            [e for e in self._access_logs if e.accessed_at >= recent_cutoff]
        )

        return SecretStatsResponse(
            total_secrets=len(secrets),
            active_secrets=len(
                [s for s in secrets if s.secret.metadata.status == SecretStatus.ACTIVE]
            ),
            secrets_by_type=secrets_by_type,
            secrets_by_status=secrets_by_status,
            expiring_soon=expiring_soon,
            auto_rotate_enabled=auto_rotate_enabled,
            total_access_count=len(self._access_logs),
            recent_access_count=recent_access_count,
        )

    async def health_check(self) -> dict[str, Any]:
        """Perform health check."""
        try:
            # Test encryption/decryption
            test_value = "health_check_test"
            encrypted = self._encrypt_value(test_value)
            decrypted = self._decrypt_value(encrypted)

            if decrypted != test_value:
                raise SecretsError("Encryption/decryption test failed")

            return {
                "status": "healthy",
                "secrets_count": len(self._secrets),
                "active_secrets_count": len(
                    [
                        s
                        for s in self._secrets.values()
                        if s.secret.metadata.status == SecretStatus.ACTIVE
                    ]
                ),
                "encryption_working": True,
                "audit_logging": self.config.enable_audit_logging,
                "cache_enabled": self.config.enable_caching,
            }

        except Exception as e:
            logger.error(f"Secrets health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "secrets_count": len(self._secrets),
                "encryption_working": False,
            }


__all__ = [
    "SecretsSDKConfig",
    "SecretsSDK",
    "SecretsError",
    "SecretNotFoundError",
    "SecretAccessDeniedError",
    "SecretExpiredError",
]
