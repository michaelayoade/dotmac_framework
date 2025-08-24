"""
Zero-Trust Architecture Implementation

Never trust, always verify. This module implements comprehensive
zero-trust security patterns for the DotMac platform.
"""

import base64
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from ..utils.datetime_compat import utcnow
from dotmac_isp.sdks.platform.utils.datetime_compat import (
    utcnow,
    utc_now_iso,
    expires_in_days,
    expires_in_hours,
    is_expired,
)
from enum import Enum
from typing import Any, Protocol

import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


class TrustLevel(Enum):
    """Trust levels in zero-trust architecture"""

    UNTRUSTED = "untrusted"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERIFIED = "verified"


class SecurityZone(Enum):
    """Security zones for network segmentation"""

    DMZ = "dmz"
    INTERNAL = "internal"
    RESTRICTED = "restricted"
    CRITICAL = "critical"
    ADMIN = "admin"


@dataclass
class SecurityContext:
    """Complete security context for zero-trust decisions"""

    user_id: str
    session_id: str
    device_id: str
    ip_address: str
    user_agent: str
    trust_level: TrustLevel
    security_zone: SecurityZone
    permissions: set[str] = field(default_factory=set)
    initial_creation: bool = False
    risk_score: float = 0.0
    last_verified: datetime = field(default_factory=utcnow)
    multi_factor_verified: bool = False
    device_trusted: bool = False
    location_verified: bool = False

    def is_expired(self, max_age_minutes: int = 30) -> bool:
        """Check if security context has expired"""
        age = utcnow() - self.last_verified
        return age > timedelta(minutes=max_age_minutes)

    def calculate_risk_score(self) -> float:
        """Calculate dynamic risk score based on context"""
        score = 0.0

        # Base risk from trust level
        risk_weights = {
            TrustLevel.UNTRUSTED: 1.0,
            TrustLevel.LOW: 0.8,
            TrustLevel.MEDIUM: 0.5,
            TrustLevel.HIGH: 0.2,
            TrustLevel.VERIFIED: 0.0,
        }
        score += risk_weights[self.trust_level]

        # Device and location factors
        if not self.device_trusted:
            score += 0.3
        if not self.location_verified:
            score += 0.2
        if not self.multi_factor_verified:
            score += 0.4

        # Time-based decay
        age_hours = (utcnow() - self.last_verified).total_seconds() / 3600
        score += min(age_hours * 0.1, 0.5)

        self.risk_score = min(score, 1.0)
        return self.risk_score


class ZeroTrustPolicy(BaseModel):
    """Zero-trust security policy definition"""

    name: str
    description: str
    required_trust_level: TrustLevel
    allowed_security_zones: list[SecurityZone]
    require_mfa: bool = True
    require_device_trust: bool = True
    require_location_verification: bool = False
    max_risk_score: float = 0.3
    session_timeout_minutes: int = 30
    continuous_verification_interval: int = 5

    def evaluate(self, context: SecurityContext) -> bool:
        """Evaluate if security context meets policy requirements"""
        # Check trust level - define trust level hierarchy
        trust_hierarchy = {
            TrustLevel.UNTRUSTED: 0,
            TrustLevel.LOW: 1,
            TrustLevel.MEDIUM: 2,
            TrustLevel.HIGH: 3,
            TrustLevel.VERIFIED: 4,
        }

        if (
            trust_hierarchy[context.trust_level]
            < trust_hierarchy[self.required_trust_level]
        ):
            return False

        # Check security zone
        if context.security_zone not in self.allowed_security_zones:
            return False

        # Check MFA requirement
        if self.require_mfa and not context.multi_factor_verified:
            return False

        # Check device trust
        if self.require_device_trust and not context.device_trusted:
            return False

        # Check location verification
        if self.require_location_verification and not context.location_verified:
            return False

        # Check risk score
        if context.calculate_risk_score() > self.max_risk_score:
            return False

        # Check session expiry
        return not context.is_expired(self.session_timeout_minutes)


class SecurityVerifier(Protocol):
    """Interface for security verification providers"""

    async def verify_device(self, device_id: str, context: SecurityContext) -> bool:
        """Verify device trustworthiness"""
        ...

    async def verify_location(self, ip_address: str, context: SecurityContext) -> bool:
        """Verify location trustworthiness"""
        ...

    async def verify_behavior(self, context: SecurityContext) -> bool:
        """Verify behavioral patterns"""
        ...


class DeviceVerifier:
    """Device trust verification service"""

    def __init__(self):
        """  Init   operation."""
        self.trusted_devices: dict[str, dict[str, Any]] = {}
        self.device_fingerprints: dict[str, str] = {}

    async def verify_device(self, device_id: str, context: SecurityContext) -> bool:
        """Verify device trustworthiness"""
        try:
            # Check if device is in trusted registry
            device_info = self.trusted_devices.get(device_id)
            if not device_info:
                logger.warning("Unknown device attempted access", device_id=device_id)
                return False

            # Verify device fingerprint
            expected_fingerprint = device_info.get("fingerprint")
            current_fingerprint = self._generate_fingerprint(context)

            if expected_fingerprint != current_fingerprint:
                logger.warning("Device fingerprint mismatch", device_id=device_id)
                return False

            # Check device reputation
            reputation_score = device_info.get("reputation_score", 0.0)
            if reputation_score < 0.7:
                logger.warning(
                    "Low device reputation", device_id=device_id, score=reputation_score
                )
                return False

            return True

        except Exception as e:
            logger.error(
                "Device verification failed", device_id=device_id, error=str(e)
            )
            return False

    def _generate_fingerprint(self, context: SecurityContext) -> str:
        """Generate device fingerprint from context"""
        fingerprint_data = f"{context.user_agent}:{context.device_id}"
        return base64.b64encode(fingerprint_data.encode()).decode()

    async def register_trusted_device(
        self, device_id: str, context: SecurityContext, reputation_score: float = 1.0
    ) -> None:
        """Register a new trusted device"""
        fingerprint = self._generate_fingerprint(context)

        self.trusted_devices[device_id] = {
            "fingerprint": fingerprint,
            "reputation_score": reputation_score,
            "registered_at": utcnow().isoformat(),
            "last_seen": utcnow().isoformat(),
        }

        logger.info("Trusted device registered", device_id=device_id)


class LocationVerifier:
    """Location-based verification service"""

    def __init__(self):
        """  Init   operation."""
        self.trusted_locations: set[str] = set()
        self.suspicious_locations: set[str] = set()
        self.geolocation_cache: dict[str, dict[str, Any]] = {}

    async def verify_location(self, ip_address: str, context: SecurityContext) -> bool:
        """Verify location trustworthiness"""
        try:
            # Check against trusted locations
            if ip_address in self.trusted_locations:
                return True

            # Check against suspicious locations
            if ip_address in self.suspicious_locations:
                logger.warning("Access from suspicious location", ip_address=ip_address)
                return False

            # Perform geolocation lookup
            location_info = await self._get_geolocation(ip_address)

            # Apply location-based rules
            if location_info.get("country") in [
                "CN",
                "RU",
                "KP",
            ]:  # Example restricted countries
                logger.warning(
                    "Access from restricted country",
                    ip_address=ip_address,
                    country=location_info.get("country"),
                )
                return False

            # Check for VPN/Proxy indicators
            if location_info.get("is_proxy", False):
                logger.warning("Access through proxy/VPN", ip_address=ip_address)
                return False

            return True

        except Exception as e:
            logger.error(
                "Location verification failed", ip_address=ip_address, error=str(e)
            )
            return False

    async def _get_geolocation(self, ip_address: str) -> dict[str, Any]:
        """Get geolocation data for IP address"""
        # Check cache first
        if ip_address in self.geolocation_cache:
            return self.geolocation_cache[ip_address]

        # In production, this would call a real geolocation service
        # For now, return mock data
        mock_data = {
            "country": "US",
            "region": "CA",
            "city": "San Francisco",
            "is_proxy": False,
            "confidence": 0.95,
        }

        self.geolocation_cache[ip_address] = mock_data
        return mock_data


class BehaviorVerifier:
    """Behavioral analysis verification service"""

    def __init__(self):
        """  Init   operation."""
        self.user_patterns: dict[str, dict[str, Any]] = {}
        self.anomaly_threshold = 0.8

    async def verify_behavior(self, context: SecurityContext) -> bool:
        """Verify behavioral patterns match user profile"""
        try:
            user_pattern = self.user_patterns.get(context.user_id)
            if not user_pattern:
                # No pattern established yet, assume normal
                await self._update_user_pattern(context)
                return True

            # Analyze current behavior against pattern
            anomaly_score = self._calculate_anomaly_score(context, user_pattern)

            if anomaly_score > self.anomaly_threshold:
                logger.warning(
                    "Behavioral anomaly detected",
                    user_id=context.user_id,
                    anomaly_score=anomaly_score,
                )
                return False

            # Update pattern with current behavior
            await self._update_user_pattern(context)
            return True

        except Exception as e:
            logger.error(
                "Behavior verification failed", user_id=context.user_id, error=str(e)
            )
            return False

    def _calculate_anomaly_score(
        self, context: SecurityContext, pattern: dict[str, Any]
    ) -> float:
        """Calculate behavioral anomaly score"""
        score = 0.0

        # Time-based patterns
        current_hour = utcnow().hour
        typical_hours = pattern.get("typical_hours", [])
        if typical_hours and current_hour not in typical_hours:
            score += 0.3

        # Location patterns
        current_location = context.ip_address
        typical_locations = pattern.get("typical_locations", [])
        if typical_locations and current_location not in typical_locations:
            score += 0.4

        # Device patterns
        current_device = context.device_id
        typical_devices = pattern.get("typical_devices", [])
        if typical_devices and current_device not in typical_devices:
            score += 0.3

        return min(score, 1.0)

    async def _update_user_pattern(self, context: SecurityContext) -> None:
        """Update user behavioral pattern"""
        if context.user_id not in self.user_patterns:
            self.user_patterns[context.user_id] = {
                "typical_hours": [],
                "typical_locations": [],
                "typical_devices": [],
                "last_updated": utcnow().isoformat(),
            }

        pattern = self.user_patterns[context.user_id]

        # Update patterns (simplified version)
        current_hour = utcnow().hour
        if current_hour not in pattern["typical_hours"]:
            pattern["typical_hours"].append(current_hour)

        if context.ip_address not in pattern["typical_locations"]:
            pattern["typical_locations"].append(context.ip_address)

        if context.device_id not in pattern["typical_devices"]:
            pattern["typical_devices"].append(context.device_id)

        pattern["last_updated"] = utcnow().isoformat()


class ZeroTrustManager:
    """Main zero-trust architecture manager"""

    def __init__(self):
        """  Init   operation."""
        self.policies: dict[str, ZeroTrustPolicy] = {}
        self.security_contexts: dict[str, SecurityContext] = {}
        self.device_verifier = DeviceVerifier()
        self.location_verifier = LocationVerifier()
        self.behavior_verifier = BehaviorVerifier()
        self.verification_cache: dict[str, dict[str, Any]] = {}

        # Default policies
        self._setup_default_policies()

    def _setup_default_policies(self) -> None:
        """Setup default zero-trust policies"""
        # Admin operations require highest security
        admin_policy = ZeroTrustPolicy(
            name="admin_operations",
            description="High-security policy for administrative operations",
            required_trust_level=TrustLevel.VERIFIED,
            allowed_security_zones=[SecurityZone.ADMIN],
            require_mfa=True,
            require_device_trust=True,
            require_location_verification=True,
            max_risk_score=0.1,
            session_timeout_minutes=15,
            continuous_verification_interval=2,
        )

        # Standard user operations
        user_policy = ZeroTrustPolicy(
            name="user_operations",
            description="Standard policy for user operations",
            required_trust_level=TrustLevel.MEDIUM,
            allowed_security_zones=[SecurityZone.INTERNAL, SecurityZone.RESTRICTED],
            require_mfa=True,
            require_device_trust=True,
            require_location_verification=False,
            max_risk_score=0.3,
            session_timeout_minutes=30,
            continuous_verification_interval=5,
        )

        # Public API access
        api_policy = ZeroTrustPolicy(
            name="api_access",
            description="Policy for API access",
            required_trust_level=TrustLevel.LOW,
            allowed_security_zones=[SecurityZone.DMZ, SecurityZone.INTERNAL],
            require_mfa=False,
            require_device_trust=False,
            require_location_verification=False,
            max_risk_score=0.7,  # Allow higher risk for API access
            session_timeout_minutes=60,
            continuous_verification_interval=10,
        )

        self.policies.update(
            {"admin": admin_policy, "user": user_policy, "api": api_policy}
        )

    async def create_security_context(
        self,
        user_id: str,
        session_id: str,
        device_id: str,
        ip_address: str,
        user_agent: str,
        initial_trust_level: TrustLevel = TrustLevel.UNTRUSTED,
    ) -> SecurityContext:
        """Create and validate new security context"""
        context = SecurityContext(
            user_id=user_id,
            session_id=session_id,
            device_id=device_id,
            ip_address=ip_address,
            user_agent=user_agent,
            trust_level=initial_trust_level,
            security_zone=SecurityZone.DMZ,  # Start in DMZ
        )

        # Perform initial verification but preserve initial trust level
        original_trust_level = context.trust_level
        await self._perform_continuous_verification(context)

        # If initial trust level was UNTRUSTED, keep it UNTRUSTED for initial creation
        # This ensures new contexts start as UNTRUSTED regardless of verification results
        if original_trust_level == TrustLevel.UNTRUSTED:
            context.trust_level = TrustLevel.UNTRUSTED
            context.initial_creation = True  # Mark as initial creation

        # Store context
        self.security_contexts[session_id] = context

        logger.info(
            "Security context created",
            user_id=user_id,
            session_id=session_id,
            trust_level=context.trust_level.value,
            risk_score=context.risk_score,
        )

        return context

    async def verify_access(
        self, session_id: str, policy_name: str, operation: str = "default"
    ) -> bool:
        """Verify access using zero-trust principles"""
        try:
            # Get security context
            context = self.security_contexts.get(session_id)
            if not context:
                logger.warning("No security context found", session_id=session_id)
                return False

            # Get policy
            policy = self.policies.get(policy_name)
            if not policy:
                logger.warning("No policy found", policy_name=policy_name)
                return False

            # Perform continuous verification if needed
            await self._maybe_reverify(context, policy)

            # Evaluate policy
            access_granted = policy.evaluate(context)

            logger.info(
                "Access verification",
                session_id=session_id,
                policy_name=policy_name,
                operation=operation,
                access_granted=access_granted,
                trust_level=context.trust_level.value,
                risk_score=context.risk_score,
            )

            return access_granted

        except Exception as e:
            logger.error(
                "Access verification failed",
                session_id=session_id,
                policy_name=policy_name,
                error=str(e),
            )
            return False

    async def _maybe_reverify(
        self, context: SecurityContext, policy: ZeroTrustPolicy
    ) -> None:
        """Perform continuous verification if needed"""
        time_since_verification = utcnow() - context.last_verified
        interval_minutes = policy.continuous_verification_interval

        # Always reverify if this is after initial creation or if interval has passed
        if context.initial_creation or time_since_verification > timedelta(
            minutes=interval_minutes
        ):
            context.initial_creation = False  # Clear initial creation flag
            await self._perform_continuous_verification(context)

    async def _perform_continuous_verification(self, context: SecurityContext) -> None:
        """Perform comprehensive continuous verification"""
        try:
            # Verify device trust
            device_trusted = await self.device_verifier.verify_device(
                context.device_id, context
            )
            context.device_trusted = device_trusted

            # Verify location
            location_verified = await self.location_verifier.verify_location(
                context.ip_address, context
            )
            context.location_verified = location_verified

            # Verify behavior
            behavior_normal = await self.behavior_verifier.verify_behavior(context)

            # Update trust level based on verifications
            if device_trusted and location_verified and behavior_normal:
                if context.multi_factor_verified:
                    context.trust_level = TrustLevel.VERIFIED
                    context.security_zone = SecurityZone.INTERNAL
                else:
                    context.trust_level = TrustLevel.HIGH
                    context.security_zone = SecurityZone.INTERNAL
            elif device_trusted and (location_verified or behavior_normal):
                context.trust_level = TrustLevel.MEDIUM
                context.security_zone = SecurityZone.RESTRICTED
            elif device_trusted or location_verified:
                context.trust_level = TrustLevel.LOW
                context.security_zone = SecurityZone.DMZ
            else:
                context.trust_level = TrustLevel.UNTRUSTED
                context.security_zone = SecurityZone.DMZ

            # Calculate risk score
            context.calculate_risk_score()
            context.last_verified = utcnow()

            logger.debug(
                "Continuous verification completed",
                user_id=context.user_id,
                trust_level=context.trust_level.value,
                risk_score=context.risk_score,
                device_trusted=device_trusted,
                location_verified=location_verified,
                behavior_normal=behavior_normal,
            )

        except Exception as e:
            logger.error(
                "Continuous verification failed", user_id=context.user_id, error=str(e)
            )
            # On verification failure, reduce trust
            context.trust_level = TrustLevel.UNTRUSTED
            context.security_zone = SecurityZone.DMZ

    @asynccontextmanager
    async def secure_operation(self, session_id: str, policy_name: str, operation: str):
        """Context manager for secure operations with automatic verification"""
        access_granted = await self.verify_access(session_id, policy_name, operation)

        if not access_granted:
            raise PermissionError(f"Access denied for operation: {operation}")

        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            logger.info(
                "Secure operation completed",
                session_id=session_id,
                operation=operation,
                duration=duration,
            )

    def add_policy(self, name: str, policy: ZeroTrustPolicy) -> None:
        """Add custom security policy"""
        self.policies[name] = policy
        logger.info("Security policy added", name=name)

    def revoke_session(self, session_id: str) -> None:
        """Revoke security context/session"""
        if session_id in self.security_contexts:
            context = self.security_contexts[session_id]
            del self.security_contexts[session_id]

            logger.warning(
                "Session revoked", session_id=session_id, user_id=context.user_id
            )

    async def get_security_status(self, session_id: str) -> dict[str, Any]:
        """Get comprehensive security status"""
        context = self.security_contexts.get(session_id)
        if not context:
            return {"error": "Session not found"}

        return {
            "user_id": context.user_id,
            "session_id": context.session_id,
            "trust_level": context.trust_level.value,
            "security_zone": context.security_zone.value,
            "risk_score": context.risk_score,
            "multi_factor_verified": context.multi_factor_verified,
            "device_trusted": context.device_trusted,
            "location_verified": context.location_verified,
            "last_verified": context.last_verified.isoformat(),
            "is_expired": context.is_expired(),
            "permissions": list(context.permissions),
        }
