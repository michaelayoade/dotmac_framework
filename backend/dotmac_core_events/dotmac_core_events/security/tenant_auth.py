"""
Tenancy security with authorization and producer identity signing.
"""

import asyncio
import hashlib
import hmac
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

import structlog

from ..models.envelope import EventEnvelope

logger = structlog.get_logger(__name__)


class AuthorizationResult(str, Enum):
    """Authorization result."""

    ALLOWED = "allowed"
    DENIED = "denied"
    FORBIDDEN = "forbidden"


class ProducerRole(str, Enum):
    """Producer roles for authorization."""

    SERVICE = "service"
    ADMIN = "admin"
    SYSTEM = "system"
    USER = "user"


@dataclass
class ProducerIdentity:
    """Producer identity information."""

    producer_id: str
    tenant_id: str
    role: ProducerRole
    service_name: Optional[str] = None
    user_id: Optional[str] = None
    permissions: Set[str] = field(default_factory=set)
    expires_at: Optional[datetime] = None

    def is_expired(self) -> bool:
        """Check if identity is expired."""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    def can_publish_to_topic(self, topic: str) -> bool:
        """Check if producer can publish to topic."""
        # System producers can publish to any topic
        if self.role == ProducerRole.SYSTEM:
            return True

        # Admin producers can publish to any topic in their tenant
        if self.role == ProducerRole.ADMIN:
            return True

        # Service producers can publish to their service topics
        if self.role == ProducerRole.SERVICE and self.service_name:
            service_topics = [
                f"svc.{self.service_name}.",
                f"ops.{self.service_name}.",
                f"prov.{self.service_name}."
            ]
            return any(topic.startswith(prefix) for prefix in service_topics)

        # Check explicit permissions
        topic_permission = f"publish:{topic}"
        wildcard_permission = f"publish:{topic.split('.')[0]}.*"

        return (topic_permission in self.permissions or
                wildcard_permission in self.permissions)

    def can_consume_from_topic(self, topic: str) -> bool:
        """Check if producer can consume from topic."""
        # System and admin roles can consume from any topic
        if self.role in [ProducerRole.SYSTEM, ProducerRole.ADMIN]:
            return True

        # Check explicit permissions
        topic_permission = f"consume:{topic}"
        wildcard_permission = f"consume:{topic.split('.')[0]}.*"

        return (topic_permission in self.permissions or
                wildcard_permission in self.permissions)


class ProducerSignature:
    """Producer identity signature for authentication."""

    def __init__(self, secret_key: str):
        self.secret_key = secret_key.encode()

    def sign_identity(self, identity: ProducerIdentity) -> str:
        """Create signature for producer identity."""
        # Create payload to sign
        payload_data = {
            "producer_id": identity.producer_id,
            "tenant_id": identity.tenant_id,
            "role": identity.role.value,
            "service_name": identity.service_name,
            "user_id": identity.user_id,
            "permissions": sorted(list(identity.permissions)),
            "expires_at": identity.expires_at.isoformat() if identity.expires_at else None,
            "timestamp": int(time.time())
        }

        # Create canonical string
        payload_str = self._canonicalize_payload(payload_data)

        # Generate HMAC signature
        signature = hmac.new(
            self.secret_key,
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()

        return signature

    def verify_signature(self, identity: ProducerIdentity, signature: str) -> bool:
        """Verify producer identity signature."""
        try:
            expected_signature = self.sign_identity(identity)
            return hmac.compare_digest(signature, expected_signature)
        except Exception as e:
            logger.error("Signature verification failed", error=str(e))
            return False

    def _canonicalize_payload(self, payload: Dict[str, Any]) -> str:
        """Create canonical string representation of payload."""
        items = []
        for key in sorted(payload.keys()):
            value = payload[key]
            if value is not None:
                if isinstance(value, list):
                    value = ",".join(str(v) for v in value)
                items.append(f"{key}={value}")
        return "&".join(items)


class TenantAuthorizer:
    """Tenant-based authorization for event operations."""

    def __init__(self):
        self.topic_policies: Dict[str, Dict[str, Any]] = {}
        self.tenant_policies: Dict[str, Dict[str, Any]] = {}
        self.global_policies: Dict[str, Any] = {}

    def add_topic_policy(
        self,
        topic_pattern: str,
        required_roles: List[ProducerRole],
        tenant_isolation: bool = True
    ):
        """Add topic-specific authorization policy."""
        self.topic_policies[topic_pattern] = {
            "required_roles": required_roles,
            "tenant_isolation": tenant_isolation
        }

    def add_tenant_policy(
        self,
        tenant_id: str,
        allowed_topics: List[str],
        denied_topics: List[str] = None
    ):
        """Add tenant-specific policy."""
        self.tenant_policies[tenant_id] = {
            "allowed_topics": allowed_topics,
            "denied_topics": denied_topics or []
        }

    def set_global_policy(self, cross_tenant_allowed: bool = False):
        """Set global authorization policies."""
        self.global_policies["cross_tenant_allowed"] = cross_tenant_allowed

    async def authorize_publish(
        self,
        identity: ProducerIdentity,
        envelope: EventEnvelope
    ) -> AuthorizationResult:
        """Authorize event publishing."""
        # Check if identity is expired
        if identity.is_expired():
            logger.warning("Expired producer identity", producer_id=identity.producer_id)
            return AuthorizationResult.FORBIDDEN

        # Enforce tenant isolation
        if not self._check_tenant_isolation(identity, envelope):
            logger.warning(
                "Cross-tenant access denied",
                producer_tenant=identity.tenant_id,
                event_tenant=envelope.tenant_id,
                producer_id=identity.producer_id
            )
            return AuthorizationResult.FORBIDDEN

        # Check topic-specific policies
        topic = envelope.get_topic_name()
        if not self._check_topic_authorization(identity, topic, "publish"):
            logger.warning(
                "Topic publish access denied",
                producer_id=identity.producer_id,
                topic=topic,
                role=identity.role.value
            )
            return AuthorizationResult.DENIED

        # Check tenant-specific policies
        if not self._check_tenant_policies(identity, topic, "publish"):
            logger.warning(
                "Tenant policy denied publish",
                producer_id=identity.producer_id,
                tenant_id=identity.tenant_id,
                topic=topic
            )
            return AuthorizationResult.DENIED

        logger.debug(
            "Publish authorized",
            producer_id=identity.producer_id,
            topic=topic,
            event_id=envelope.id
        )
        return AuthorizationResult.ALLOWED

    async def authorize_consume(
        self,
        identity: ProducerIdentity,
        topic: str,
        consumer_group: str
    ) -> AuthorizationResult:
        """Authorize event consumption."""
        # Check if identity is expired
        if identity.is_expired():
            logger.warning("Expired producer identity", producer_id=identity.producer_id)
            return AuthorizationResult.FORBIDDEN

        # Check topic-specific policies
        if not self._check_topic_authorization(identity, topic, "consume"):
            logger.warning(
                "Topic consume access denied",
                producer_id=identity.producer_id,
                topic=topic,
                consumer_group=consumer_group
            )
            return AuthorizationResult.DENIED

        # Check tenant-specific policies
        if not self._check_tenant_policies(identity, topic, "consume"):
            logger.warning(
                "Tenant policy denied consume",
                producer_id=identity.producer_id,
                tenant_id=identity.tenant_id,
                topic=topic
            )
            return AuthorizationResult.DENIED

        logger.debug(
            "Consume authorized",
            producer_id=identity.producer_id,
            topic=topic,
            consumer_group=consumer_group
        )
        return AuthorizationResult.ALLOWED

    def _check_tenant_isolation(
        self,
        identity: ProducerIdentity,
        envelope: EventEnvelope
    ) -> bool:
        """Check tenant isolation rules."""
        # System role can cross tenants if globally allowed
        if identity.role == ProducerRole.SYSTEM:
            return self.global_policies.get("cross_tenant_allowed", False) or \
                   identity.tenant_id == envelope.tenant_id

        # All other roles must match tenant
        return identity.tenant_id == envelope.tenant_id

    def _check_topic_authorization(
        self,
        identity: ProducerIdentity,
        topic: str,
        operation: str
    ) -> bool:
        """Check topic-specific authorization."""
        # Check role-based topic access
        if operation == "publish":
            if not identity.can_publish_to_topic(topic):
                return False
        elif operation == "consume":
            if not identity.can_consume_from_topic(topic):
                return False

        # Check topic policies
        for pattern, policy in self.topic_policies.items():
            if self._topic_matches_pattern(topic, pattern):
                required_roles = policy.get("required_roles", [])
                if required_roles and identity.role not in required_roles:
                    return False

        return True

    def _check_tenant_policies(
        self,
        identity: ProducerIdentity,
        topic: str,
        operation: str
    ) -> bool:
        """Check tenant-specific policies."""
        tenant_policy = self.tenant_policies.get(identity.tenant_id)
        if not tenant_policy:
            return True  # No specific policy, allow

        # Check denied topics
        denied_topics = tenant_policy.get("denied_topics", [])
        if any(self._topic_matches_pattern(topic, pattern) for pattern in denied_topics):
            return False

        # Check allowed topics
        allowed_topics = tenant_policy.get("allowed_topics", [])
        if allowed_topics:
            return any(self._topic_matches_pattern(topic, pattern) for pattern in allowed_topics)

        return True

    def _topic_matches_pattern(self, topic: str, pattern: str) -> bool:
        """Check if topic matches pattern (supports wildcards)."""
        if pattern == "*":
            return True

        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return topic.startswith(prefix)

        return topic == pattern


class EventAuthenticationMiddleware:
    """Middleware for event authentication and authorization."""

    def __init__(
        self,
        signature_verifier: ProducerSignature,
        authorizer: TenantAuthorizer
    ):
        self.signature_verifier = signature_verifier
        self.authorizer = authorizer
        self.identity_cache: Dict[str, ProducerIdentity] = {}
        self.cache_ttl = 300  # 5 minutes
        self._cache_cleanup_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """Start middleware."""
        if self._running:
            return

        self._running = True
        self._cache_cleanup_task = asyncio.create_task(self._cache_cleanup_loop())
        logger.info("Event authentication middleware started")

    async def stop(self):
        """Stop middleware."""
        self._running = False

        if self._cache_cleanup_task:
            self._cache_cleanup_task.cancel()
            try:
                await self._cache_cleanup_task
            except asyncio.CancelledError:
                pass

        logger.info("Event authentication middleware stopped")

    async def authenticate_producer(
        self,
        producer_token: str,
        signature: str
    ) -> Optional[ProducerIdentity]:
        """Authenticate producer from token and signature."""
        try:
            # Check cache first
            cache_key = f"{producer_token}:{signature}"
            if cache_key in self.identity_cache:
                identity = self.identity_cache[cache_key]
                if not identity.is_expired():
                    return identity
                else:
                    del self.identity_cache[cache_key]

            # Parse producer token (in production, this would decode JWT or similar)
            identity = self._parse_producer_token(producer_token)
            if not identity:
                return None

            # Verify signature
            if not self.signature_verifier.verify_signature(identity, signature):
                logger.warning("Invalid producer signature", producer_id=identity.producer_id)
                return None

            # Cache identity
            self.identity_cache[cache_key] = identity

            return identity

        except Exception as e:
            logger.error("Producer authentication failed", error=str(e))
            return None

    async def authorize_publish(
        self,
        identity: ProducerIdentity,
        envelope: EventEnvelope
    ) -> bool:
        """Authorize event publishing."""
        result = await self.authorizer.authorize_publish(identity, envelope)
        return result == AuthorizationResult.ALLOWED

    async def authorize_consume(
        self,
        identity: ProducerIdentity,
        topic: str,
        consumer_group: str
    ) -> bool:
        """Authorize event consumption."""
        result = await self.authorizer.authorize_consume(identity, topic, consumer_group)
        return result == AuthorizationResult.ALLOWED

    def _parse_producer_token(self, token: str) -> Optional[ProducerIdentity]:
        """Parse producer token (simplified implementation)."""
        try:
            # In production, this would be JWT parsing or similar
            # For now, assume token is a JSON-like string
            import base64
            import json

            # Decode base64 token
            decoded = base64.b64decode(token).decode()
            data = json.loads(decoded)

            # Create identity
            identity = ProducerIdentity(
                producer_id=data["producer_id"],
                tenant_id=data["tenant_id"],
                role=ProducerRole(data["role"]),
                service_name=data.get("service_name"),
                user_id=data.get("user_id"),
                permissions=set(data.get("permissions", [])),
                expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None
            )

            return identity

        except Exception as e:
            logger.error("Failed to parse producer token", error=str(e))
            return None

    async def _cache_cleanup_loop(self):
        """Clean up expired cache entries."""
        while self._running:
            try:
                now = datetime.now(timezone.utc)
                expired_keys = []

                for key, identity in self.identity_cache.items():
                    if identity.is_expired():
                        expired_keys.append(key)

                for key in expired_keys:
                    del self.identity_cache[key]

                if expired_keys:
                    logger.debug("Cleaned up expired identity cache entries", count=len(expired_keys))

                await asyncio.sleep(60)  # Clean up every minute

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Cache cleanup error", error=str(e))
                await asyncio.sleep(60)


class CrossTenantReplayPrevention:
    """Prevent cross-tenant event replay attacks."""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.replay_window = 3600  # 1 hour
        self.key_prefix = "replay_prevention:"

    async def record_event_signature(
        self,
        envelope: EventEnvelope,
        producer_id: str
    ) -> bool:
        """Record event signature to prevent replay."""
        # Create signature from event content
        signature = self._create_event_signature(envelope, producer_id)
        key = f"{self.key_prefix}{signature}"

        try:
            # Use Redis SET with NX (not exists) and EX (expiration)
            result = await self.redis.set(key, "1", nx=True, ex=self.replay_window)

            if not result:
                logger.warning(
                    "Potential replay attack detected",
                    envelope_id=envelope.id,
                    producer_id=producer_id,
                    tenant_id=envelope.tenant_id
                )
                return False

            return True

        except Exception as e:
            logger.error("Failed to record event signature", error=str(e))
            return False

    def _create_event_signature(self, envelope: EventEnvelope, producer_id: str) -> str:
        """Create unique signature for event."""
        # Combine key fields to create signature
        signature_data = f"{envelope.id}:{envelope.tenant_id}:{producer_id}:{envelope.occurred_at.isoformat()}"
        return hashlib.sha256(signature_data.encode()).hexdigest()


# Factory functions
def create_service_identity(
    service_name: str,
    tenant_id: str,
    permissions: List[str] = None
) -> ProducerIdentity:
    """Create service producer identity."""
    return ProducerIdentity(
        producer_id=f"service:{service_name}",
        tenant_id=tenant_id,
        role=ProducerRole.SERVICE,
        service_name=service_name,
        permissions=set(permissions or [])
    )


def create_default_authorizer() -> TenantAuthorizer:
    """Create default tenant authorizer with common policies."""
    authorizer = TenantAuthorizer()

    # System events require admin or system role
    authorizer.add_topic_policy("system.*", [ProducerRole.ADMIN, ProducerRole.SYSTEM])

    # Admin events require admin role
    authorizer.add_topic_policy("admin.*", [ProducerRole.ADMIN])

    # Service events allow service and admin roles
    authorizer.add_topic_policy("svc.*", [ProducerRole.SERVICE, ProducerRole.ADMIN, ProducerRole.SYSTEM])
    authorizer.add_topic_policy("prov.*", [ProducerRole.SERVICE, ProducerRole.ADMIN, ProducerRole.SYSTEM])
    authorizer.add_topic_policy("ops.*", [ProducerRole.SERVICE, ProducerRole.ADMIN, ProducerRole.SYSTEM])

    # Set global policy
    authorizer.set_global_policy(cross_tenant_allowed=False)

    return authorizer


def create_production_auth_middleware(secret_key: str) -> EventAuthenticationMiddleware:
    """Create production authentication middleware."""
    signature_verifier = ProducerSignature(secret_key)
    authorizer = create_default_authorizer()

    return EventAuthenticationMiddleware(signature_verifier, authorizer)
