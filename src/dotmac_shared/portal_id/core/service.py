"""
Unified Portal ID Generation Service.

This service consolidates all portal ID generation logic across platforms,
eliminating duplication and providing consistent, configurable ID generation.
"""

import logging
import secrets
import string
import warnings
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class PortalIdPattern(str, Enum):
    """Available Portal ID generation patterns."""

    ALPHANUMERIC_CLEAN = "alphanumeric_clean"  # A-Z, 2-9 (excludes 0,O,I,1)
    ALPHANUMERIC = "alphanumeric"  # A-Z, 0-9
    NUMERIC = "numeric"  # 0-9 only
    TIMESTAMP_BASED = "timestamp_based"  # Timestamp + random chars
    CUSTOM = "custom"  # User-defined character set


class PortalIdConfig:
    """Configuration for portal ID generation."""

    def __init__(
        self,
        pattern: PortalIdPattern = PortalIdPattern.ALPHANUMERIC_CLEAN,
        length: int = 8,
        prefix: str = "",
        exclude_ambiguous: bool = True,
        custom_charset: str = "",
        collision_check: bool = True,
        max_attempts: int = 100,
    ):
        self.pattern = pattern
        self.length = length
        self.prefix = prefix
        self.exclude_ambiguous = exclude_ambiguous
        self.custom_charset = custom_charset
        self.collision_check = collision_check
        self.max_attempts = max_attempts


class PortalIdCollisionChecker(ABC):
    """Abstract base class for checking portal ID collisions."""

    @abstractmethod
    async def check_collision(self, portal_id: str) -> bool:
        """Check if portal ID already exists. Return True if collision exists."""
        pass


class UnifiedPortalIdService:
    """
    Unified Portal ID generation service that consolidates all platform implementations.

    This service replaces:
    - dotmac_isp.modules.identity.portal_id_generator
    - dotmac_isp.modules.portal_management.service._generate_portal_id
    - dotmac_isp.modules.portal_management.models._generate_portal_id
    - dotmac_isp.modules.identity.repository._generate_portal_id
    """

    def __init__(
        self,
        config: PortalIdConfig,
        collision_checker: Optional[PortalIdCollisionChecker] = None,
    ):
        self.config = config
        self.collision_checker = collision_checker
        self._validate_config()
        logger.info(
            f"Unified Portal ID service initialized with pattern: {config.pattern}"
        )

    async def generate_portal_id(
        self, existing_ids: Optional[Set[str]] = None, tenant_id: Optional[str] = None
    ) -> str:
        """
        Generate a unique Portal ID based on configuration.

        Args:
            existing_ids: Set of existing Portal IDs to avoid duplicates
            tenant_id: Optional tenant ID for tenant-specific patterns

        Returns:
            Generated unique Portal ID

        Raises:
            RuntimeError: If unable to generate unique ID after max attempts
        """
        existing_ids = existing_ids or set()

        for attempt in range(self.config.max_attempts):
            portal_id = self._generate_single_id()

            # Check against provided existing IDs
            if portal_id in existing_ids:
                continue

            # Check collision with database if checker is provided
            if self.config.collision_check and self.collision_checker:
                if await self.collision_checker.check_collision(portal_id):
                    continue

            logger.debug(f"Generated portal ID: {portal_id} (attempt {attempt + 1})")
            return portal_id

        raise RuntimeError(
            f"Could not generate unique Portal ID after {self.config.max_attempts} attempts. "
            f"Consider increasing length, changing pattern, or reducing collision space."
        )

    def generate_portal_id_sync(self, existing_ids: Optional[Set[str]] = None) -> str:
        """
        Synchronous version of generate_portal_id for backward compatibility.
        Note: Does not use collision checker.
        """
        existing_ids = existing_ids or set()

        for attempt in range(self.config.max_attempts):
            portal_id = self._generate_single_id()

            if portal_id not in existing_ids:
                return portal_id

        raise RuntimeError(
            f"Could not generate unique Portal ID after {self.config.max_attempts} attempts."
        )

    def _generate_single_id(self) -> str:
        """Generate a single Portal ID based on current pattern."""
        if self.config.pattern == PortalIdPattern.TIMESTAMP_BASED:
            return self._generate_timestamp_based_id()

        charset = self._get_character_set()

        # Calculate available length after prefix
        available_length = max(1, self.config.length - len(self.config.prefix))

        # Generate random part
        random_part = "".join(secrets.choice(charset) for _ in range(available_length))

        return f"{self.config.prefix}{random_part}"

    def _generate_timestamp_based_id(self) -> str:
        """Generate timestamp-based portal ID (legacy compatibility)."""
        timestamp = int(datetime.now(timezone.utc).timestamp())
        random_chars = "".join(
            secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6)
        )
        return f"{self.config.prefix or 'PRT'}-{timestamp}-{random_chars}"

    def _get_character_set(self) -> str:
        """Get character set based on configured pattern."""
        pattern = self.config.pattern

        if pattern == PortalIdPattern.ALPHANUMERIC_CLEAN:
            charset = string.ascii_uppercase + string.digits
            if self.config.exclude_ambiguous:
                charset = (
                    charset.replace("0", "")
                    .replace("O", "")
                    .replace("I", "")
                    .replace("1", "")
                )
            return charset

        elif pattern == PortalIdPattern.ALPHANUMERIC:
            charset = string.ascii_uppercase + string.digits
            if self.config.exclude_ambiguous:
                charset = (
                    charset.replace("0", "")
                    .replace("O", "")
                    .replace("I", "")
                    .replace("1", "")
                )
            return charset

        elif pattern == PortalIdPattern.NUMERIC:
            charset = string.digits
            if self.config.exclude_ambiguous:
                charset = charset.replace("0", "").replace("1", "")
                if not charset:  # If all numbers are excluded
                    charset = "23456789"  # Fallback to safe numbers
            return charset

        elif pattern == PortalIdPattern.CUSTOM:
            return self.config.custom_charset

        else:
            raise ValueError(f"Unknown Portal ID pattern: {pattern}")

    def _validate_config(self) -> None:
        """Validate Portal ID generation configuration."""
        # Check pattern is valid
        if not isinstance(self.config.pattern, PortalIdPattern):
            raise ValueError(
                f"Invalid pattern. Must be one of: {list(PortalIdPattern)}"
            )

        # Check length is reasonable
        if self.config.length < 4:
            raise ValueError("Portal ID length must be at least 4 characters")

        if self.config.length > 50:
            raise ValueError("Portal ID length must not exceed 50 characters")

        # Check prefix length doesn't exceed total length
        if (
            len(self.config.prefix) >= self.config.length
            and self.config.pattern != PortalIdPattern.TIMESTAMP_BASED
        ):
            raise ValueError(
                f"Portal ID prefix length ({len(self.config.prefix)}) "
                f"must be less than total length ({self.config.length})"
            )

        # Check custom charset is not empty
        if (
            self.config.pattern == PortalIdPattern.CUSTOM
            and not self.config.custom_charset.strip()
        ):
            raise ValueError(
                "Custom character set cannot be empty when using 'custom' pattern"
            )

        # Validate character set for uniqueness warnings
        if self.config.pattern != PortalIdPattern.TIMESTAMP_BASED:
            self._validate_uniqueness()

    def _validate_uniqueness(self) -> None:
        """Validate configuration provides enough uniqueness."""
        charset = self._get_character_set()
        effective_length = self.config.length - len(self.config.prefix)

        if len(charset) == 0:
            raise ValueError("Character set is empty - check your exclusion settings")

        max_combinations = len(charset) ** effective_length
        if max_combinations < 10000:  # Less than 10K combinations
            warnings.warn(
                f"Portal ID configuration may not provide enough unique combinations "
                f"({max_combinations:,}). Consider increasing length or expanding character set.",
                UserWarning,
            )

    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get a summary of current Portal ID configuration."""
        if self.config.pattern == PortalIdPattern.TIMESTAMP_BASED:
            return {
                "pattern": self.config.pattern.value,
                "format": f"{self.config.prefix or 'PRT'}-timestamp-6random",
                "collision_check": self.config.collision_check,
                "example": self._generate_single_id(),
            }

        charset = self._get_character_set()
        effective_length = self.config.length - len(self.config.prefix)
        max_combinations = len(charset) ** effective_length

        return {
            "pattern": self.config.pattern.value,
            "total_length": self.config.length,
            "prefix": self.config.prefix or "(none)",
            "effective_length": effective_length,
            "character_set": charset,
            "character_count": len(charset),
            "exclude_ambiguous": self.config.exclude_ambiguous,
            "collision_check": self.config.collision_check,
            "max_combinations": max_combinations,
            "example": self._generate_single_id(),
        }


class PortalIdServiceFactory:
    """Factory for creating pre-configured Portal ID services."""

    @staticmethod
    def create_isp_service(
        collision_checker: Optional[PortalIdCollisionChecker] = None,
    ) -> UnifiedPortalIdService:
        """Create service configured for ISP Framework (configurable pattern)."""
        config = PortalIdConfig(
            pattern=PortalIdPattern.ALPHANUMERIC_CLEAN,
            length=8,
            prefix="",
            exclude_ambiguous=True,
            collision_check=True,
        )
        return UnifiedPortalIdService(config, collision_checker)

    @staticmethod
    def create_legacy_service(
        collision_checker: Optional[PortalIdCollisionChecker] = None,
    ) -> UnifiedPortalIdService:
        """Create service configured for legacy timestamp-based IDs."""
        config = PortalIdConfig(
            pattern=PortalIdPattern.TIMESTAMP_BASED,
            prefix="PRT",
            collision_check=False,  # Timestamp-based are unlikely to collide
        )
        return UnifiedPortalIdService(config, collision_checker)

    @staticmethod
    def create_management_service(
        collision_checker: Optional[PortalIdCollisionChecker] = None,
    ) -> UnifiedPortalIdService:
        """Create service configured for Management Platform."""
        config = PortalIdConfig(
            pattern=PortalIdPattern.ALPHANUMERIC_CLEAN,
            length=12,
            prefix="MGT-",
            exclude_ambiguous=True,
            collision_check=True,
        )
        return UnifiedPortalIdService(config, collision_checker)

    @staticmethod
    def create_custom_service(
        pattern: PortalIdPattern,
        length: int = 8,
        prefix: str = "",
        exclude_ambiguous: bool = True,
        custom_charset: str = "",
        collision_checker: Optional[PortalIdCollisionChecker] = None,
    ) -> UnifiedPortalIdService:
        """Create service with custom configuration."""
        config = PortalIdConfig(
            pattern=pattern,
            length=length,
            prefix=prefix,
            exclude_ambiguous=exclude_ambiguous,
            custom_charset=custom_charset,
            collision_check=collision_checker is not None,
        )
        return UnifiedPortalIdService(config, collision_checker)


# Global service instances for backward compatibility
_global_services: Dict[str, UnifiedPortalIdService] = {}


def get_portal_id_service(service_type: str = "isp") -> UnifiedPortalIdService:
    """Get or create a global portal ID service instance."""
    global _global_services

    if service_type not in _global_services:
        if service_type == "isp":
            _global_services[service_type] = PortalIdServiceFactory.create_isp_service()
        elif service_type == "legacy":
            _global_services[service_type] = (
                PortalIdServiceFactory.create_legacy_service()
            )
        elif service_type == "management":
            _global_services[service_type] = (
                PortalIdServiceFactory.create_management_service()
            )
        else:
            raise ValueError(f"Unknown service type: {service_type}")

    return _global_services[service_type]


def generate_portal_id(
    existing_ids: Optional[Set[str]] = None, service_type: str = "isp"
) -> str:
    """Convenience function to generate a Portal ID synchronously."""
    service = get_portal_id_service(service_type)
    return service.generate_portal_id_sync(existing_ids)


async def generate_portal_id_async(
    existing_ids: Optional[Set[str]] = None,
    service_type: str = "isp",
    collision_checker: Optional[PortalIdCollisionChecker] = None,
) -> str:
    """Convenience function to generate a Portal ID asynchronously."""
    if collision_checker:
        # Create a new service with collision checker
        if service_type == "isp":
            service = PortalIdServiceFactory.create_isp_service(collision_checker)
        elif service_type == "legacy":
            service = PortalIdServiceFactory.create_legacy_service(collision_checker)
        elif service_type == "management":
            service = PortalIdServiceFactory.create_management_service(
                collision_checker
            )
        else:
            raise ValueError(f"Unknown service type: {service_type}")
    else:
        service = get_portal_id_service(service_type)

    return await service.generate_portal_id(existing_ids)


def reload_global_services():
    """Reload global services (useful for testing)."""
    global _global_services
    _global_services.clear()
