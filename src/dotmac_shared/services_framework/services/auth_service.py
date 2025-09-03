"""
Authentication service implementation for DotMac Services Framework.
"""

import hashlib
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import jwt

from ...application.config import DeploymentContext, DeploymentMode
from ..core.base import ServiceHealth, ServiceStatus, StatefulService

logger = logging.getLogger(__name__)


@dataclass
class AuthServiceConfig:
    """Authentication service configuration."""

    jwt_secret: Optional[str] = None
    issuer: str = "dotmac"
    expiry_hours: int = 24
    algorithm: str = "HS256"
    deployment_context: Optional[DeploymentContext] = None

    # Token management settings
    max_active_tokens: int = 1000
    cleanup_expired_tokens: bool = True
    token_cleanup_interval_minutes: int = 60

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.jwt_secret:
            # Try to get from environment
            self.jwt_secret = os.getenv("JWT_SECRET")

            # Try tenant-specific secret if in tenant mode
            if (
                self.deployment_context
                and self.deployment_context.mode == DeploymentMode.TENANT_CONTAINER
                and self.deployment_context.tenant_id
            ):
                tenant_secret = os.getenv(
                    f"TENANT_{self.deployment_context.tenant_id.upper()}_JWT_SECRET"
                )
                if tenant_secret:
                    self.jwt_secret = tenant_secret

        if not self.jwt_secret:
            raise ValueError("JWT secret is required for auth service")


class AuthService(StatefulService):
    """Service layer - exceptions bubble up to router @standard_exception_handler."""

    """Authentication service implementation."""

    def __init__(self, config: AuthServiceConfig):
        """__init__ service method."""
        super().__init__(
            name="auth",
            config=config.__dict__,
            required_config=["jwt_secret", "issuer", "algorithm"],
        )
        self.auth_config = config
        self.active_tokens: Dict[str, float] = {}  # token_hash -> expiry_timestamp
        self.priority = 100  # High priority - other services depend on auth
        self.last_cleanup = 0

    async def _initialize_stateful_service(self) -> bool:
        """Initialize authentication service."""
        # Validate JWT secret
        if len(self.auth_config.jwt_secret) < 32:
            raise ValueError("JWT secret must be at least 32 characters")

        # Test JWT operations
        test_payload = {"test": True, "iss": self.auth_config.issuer}
        test_token = jwt.encode(
            test_payload,
            self.auth_config.jwt_secret,
            algorithm=self.auth_config.algorithm,
        )
        decoded = jwt.decode(
            test_token,
            self.auth_config.jwt_secret,
            algorithms=[self.auth_config.algorithm],
        )

        if decoded.get("iss") != self.auth_config.issuer:
            raise ValueError("JWT encode/decode test failed")

        # Initialize state
        self.set_state("tokens_created", 0)
        self.set_state("tokens_verified", 0)
        self.set_state("tokens_revoked", 0)
        self.set_state("verification_errors", 0)

        await self._set_status(
            ServiceStatus.READY,
            f"Auth service ready with issuer: {self.auth_config.issuer}",
            {
                "issuer": self.auth_config.issuer,
                "algorithm": self.auth_config.algorithm,
                "expiry_hours": self.auth_config.expiry_hours,
                "max_active_tokens": self.auth_config.max_active_tokens,
            },
        )
        return True

    async def shutdown(self) -> bool:
        """Shutdown authentication service."""
        await self._set_status(
            ServiceStatus.SHUTTING_DOWN, "Shutting down auth service"
        )

        # Clear active tokens
        self.active_tokens.clear()
        self.clear_state()

        await self._set_status(ServiceStatus.SHUTDOWN, "Auth service shutdown complete")
        return True

    async def _health_check_stateful_service(self) -> ServiceHealth:
        """Perform health check."""
        # Test JWT operations
        test_payload = {"health": "check", "iss": self.auth_config.issuer}
        test_token = jwt.encode(
            test_payload,
            self.auth_config.jwt_secret,
            algorithm=self.auth_config.algorithm,
        )
        jwt.decode(
            test_token,
            self.auth_config.jwt_secret,
            algorithms=[self.auth_config.algorithm],
        )

        # Cleanup expired tokens if needed
        if self.auth_config.cleanup_expired_tokens:
            self._cleanup_expired_tokens()

        # Check if we're hitting token limits
        warning_threshold = self.auth_config.max_active_tokens * 0.8
        active_count = len(self.active_tokens)

        if active_count > warning_threshold:
            return ServiceHealth(
                status=ServiceStatus.READY,
                message=f"Auth service healthy but approaching token limit ({active_count}/{self.auth_config.max_active_tokens})",
                details={
                    "active_tokens": active_count,
                    "issuer": self.auth_config.issuer,
                    "tokens_created": self.get_state("tokens_created", 0),
                    "tokens_verified": self.get_state("tokens_verified", 0),
                    "tokens_revoked": self.get_state("tokens_revoked", 0),
                    "verification_errors": self.get_state("verification_errors", 0),
                },
            )

        return ServiceHealth(
            status=ServiceStatus.READY,
            message="Auth service healthy",
            details={
                "active_tokens": active_count,
                "issuer": self.auth_config.issuer,
                "tokens_created": self.get_state("tokens_created", 0),
                "tokens_verified": self.get_state("tokens_verified", 0),
                "tokens_revoked": self.get_state("tokens_revoked", 0),
                "verification_errors": self.get_state("verification_errors", 0),
            },
        )

    def create_token(
        self, payload: Dict[str, Any], user_id: Optional[str] = None
    ) -> str:
        """Create JWT token."""
        if not self.is_ready():
            raise RuntimeError("Auth service not ready")

        # Check token limits
        if len(self.active_tokens) >= self.auth_config.max_active_tokens:
            # Try to cleanup expired tokens first
            self._cleanup_expired_tokens()

            if len(self.active_tokens) >= self.auth_config.max_active_tokens:
                raise RuntimeError("Maximum active tokens limit reached")

        now = datetime.now(timezone.utc)
        expiry = now + timedelta(hours=self.auth_config.expiry_hours)

        token_payload = {
            **payload,
            "iss": self.auth_config.issuer,
            "iat": now,
            "exp": expiry,
        }

        if user_id:
            token_payload["sub"] = user_id

        # Add tenant context if available
        if (
            self.auth_config.deployment_context
            and self.auth_config.deployment_context.tenant_id
        ):
            token_payload["tenant_id"] = self.auth_config.deployment_context.tenant_id

        token = jwt.encode(
            token_payload,
            self.auth_config.jwt_secret,
            algorithm=self.auth_config.algorithm,
        )
        token_hash = self._hash_token(token)

        # Store with expiry timestamp
        self.active_tokens[token_hash] = expiry.timestamp()

        # Update statistics
        tokens_created = self.get_state("tokens_created", 0)
        self.set_state("tokens_created", tokens_created + 1)

        return token

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token."""
        if not self.is_ready():
            raise RuntimeError("Auth service not ready")

        payload = jwt.decode(
            token,
            self.auth_config.jwt_secret,
            algorithms=[self.auth_config.algorithm],
            issuer=self.auth_config.issuer,
        )

        # Check if token is in active set
        token_hash = self._hash_token(token)
        if token_hash not in self.active_tokens:
            logger.warning("Token not in active set - may have been revoked")
            # Don't fail verification for this, just log

        # Update statistics
        tokens_verified = self.get_state("tokens_verified", 0)
        self.set_state("tokens_verified", tokens_verified + 1)

        return payload

    def revoke_token(self, token: str) -> bool:
        """Revoke a JWT token."""
        token_hash = self._hash_token(token)
        if token_hash in self.active_tokens:
            del self.active_tokens[token_hash]

            # Update statistics
            tokens_revoked = self.get_state("tokens_revoked", 0)
            self.set_state("tokens_revoked", tokens_revoked + 1)

            return True
        return False

    def revoke_all_tokens(self) -> int:
        """Revoke all active tokens. Returns count of revoked tokens."""
        count = len(self.active_tokens)
        self.active_tokens.clear()

        # Update statistics
        tokens_revoked = self.get_state("tokens_revoked", 0)
        self.set_state("tokens_revoked", tokens_revoked + count)

        return count

    def get_active_token_count(self) -> int:
        """Get count of active tokens."""
        self._cleanup_expired_tokens()
        return len(self.active_tokens)

    def _cleanup_expired_tokens(self):
        """Remove expired tokens from active set."""
        current_time = time.time()

        # Only run cleanup at configured intervals
        if current_time - self.last_cleanup < (
            self.auth_config.token_cleanup_interval_minutes * 60
        ):
            return

        self.last_cleanup = current_time

        expired_tokens = [
            token_hash
            for token_hash, expiry in self.active_tokens.items()
            if expiry <= current_time
        ]

        for token_hash in expired_tokens:
            del self.active_tokens[token_hash]

        if expired_tokens:
            logger.debug(f"Cleaned up {len(expired_tokens)} expired tokens")

    def _increment_verification_errors(self):
        """Increment verification error count."""
        errors = self.get_state("verification_errors", 0)
        self.set_state("verification_errors", errors + 1)

    def _hash_token(self, token: str) -> str:
        """Create hash of token for storage."""
        return hashlib.sha256(token.encode()).hexdigest()

    def get_issuer(self) -> str:
        """Get configured issuer."""
        return self.auth_config.issuer

    def get_auth_stats(self) -> Dict[str, Any]:
        """Get authentication service statistics."""
        return {
            "active_tokens": len(self.active_tokens),
            "max_tokens": self.auth_config.max_active_tokens,
            "tokens_created": self.get_state("tokens_created", 0),
            "tokens_verified": self.get_state("tokens_verified", 0),
            "tokens_revoked": self.get_state("tokens_revoked", 0),
            "verification_errors": self.get_state("verification_errors", 0),
            "issuer": self.auth_config.issuer,
            "algorithm": self.auth_config.algorithm,
            "expiry_hours": self.auth_config.expiry_hours,
        }


async def create_auth_service(config: AuthServiceConfig) -> AuthService:
    """Create and initialize auth service."""
    service = AuthService(config)

    # Service will be initialized by the registry
    return service
