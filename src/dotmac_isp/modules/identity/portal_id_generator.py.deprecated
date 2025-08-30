"""Configurable Portal ID generation system."""

import secrets
import string
from typing import Optional, Set
from enum import Enum

from dotmac_isp.core.settings import get_settings
from dotmac_isp.shared.exceptions import ValidationError


class PortalIdPattern(str, Enum):
    """Available Portal ID generation patterns."""

    ALPHANUMERIC_CLEAN = "alphanumeric_clean"  # A-Z, 2-9 (excludes 0,O,I,1)
    ALPHANUMERIC = "alphanumeric"  # A-Z, 0-9
    NUMERIC = "numeric"  # 0-9 only
    CUSTOM = "custom"  # User-defined character set


class PortalIdGenerator:
    """Configurable Portal ID generator with multiple patterns and validation."""

    def __init__(self):
        """Initialize generator with current settings."""
        self.settings = get_settings()
        self._validate_settings()

    def generate_portal_id(self, existing_ids: Optional[Set[str]] = None) -> str:
        """
        Generate a unique Portal ID based on configuration.

        Args:
            existing_ids: Set of existing Portal IDs to avoid duplicates

        Returns:
            Generated unique Portal ID

        Raises:
            RuntimeError: If unable to generate unique ID after max attempts
        """
        existing_ids = existing_ids or set()
        max_attempts = 100  # Increased for better collision handling

        for attempt in range(max_attempts):
            portal_id = self._generate_single_id()

            if portal_id not in existing_ids:
                return portal_id

        raise RuntimeError(
            f"Could not generate unique Portal ID after {max_attempts} attempts. "
            f"Consider increasing length or changing pattern."
        )

    def _generate_single_id(self) -> str:
        """Generate a single Portal ID based on current pattern."""
        charset = self._get_character_set()

        # Calculate available length after prefix
        available_length = self.settings.portal_id_length
        prefix = self.settings.portal_id_prefix

        if prefix:
            available_length = max(1, available_length - len(prefix))

        # Generate random part
        random_part = "".join(secrets.choice(charset) for _ in range(available_length))

        return f"{prefix}{random_part}"

    def _get_character_set(self) -> str:
        """Get character set based on configured pattern."""
        pattern = PortalIdPattern(self.settings.portal_id_pattern)

        if pattern == PortalIdPattern.ALPHANUMERIC_CLEAN:
            # Default safe character set
            charset = string.ascii_uppercase + string.digits
            if self.settings.portal_id_exclude_ambiguous:
                # Remove ambiguous characters
                charset = (
                    charset.replace("0", "")
                    .replace("O", "")
                    .replace("I", "")
                    .replace("1", "")
                )
            return charset

        elif pattern == PortalIdPattern.ALPHANUMERIC:
            charset = string.ascii_uppercase + string.digits
            if self.settings.portal_id_exclude_ambiguous:
                charset = (
                    charset.replace("0", "")
                    .replace("O", "")
                    .replace("I", "")
                    .replace("1", "")
                )
            return charset

        elif pattern == PortalIdPattern.NUMERIC:
            charset = string.digits
            if self.settings.portal_id_exclude_ambiguous:
                charset = charset.replace("0", "").replace("1", "")
                if not charset:  # If all numbers are excluded
                    charset = "23456789"  # Fallback to safe numbers
            return charset

        elif pattern == PortalIdPattern.CUSTOM:
            return self.settings.portal_id_custom_charset

        else:
            raise ValidationError(f"Unknown Portal ID pattern: {pattern}")

    def _validate_settings(self) -> None:
        """Validate Portal ID generation settings."""
        # Check pattern is valid
        try:
            PortalIdPattern(self.settings.portal_id_pattern)
        except ValueError:
            raise ValidationError(
                f"Invalid portal_id_pattern: {self.settings.portal_id_pattern}. "
                f"Must be one of: {[p.value for p in PortalIdPattern]}"
            )

        # Check length is reasonable
        if self.settings.portal_id_length < 4:
            raise ValidationError("Portal ID length must be at least 4 characters")

        if self.settings.portal_id_length > 20:
            raise ValidationError("Portal ID length must not exceed 20 characters")

        # Check prefix length doesn't exceed total length
        if len(self.settings.portal_id_prefix) >= self.settings.portal_id_length:
            raise ValidationError(
                f"Portal ID prefix length ({len(self.settings.portal_id_prefix)}) "
                f"must be less than total length ({self.settings.portal_id_length})"
            )

        # Check custom charset is not empty
        if (
            self.settings.portal_id_pattern == "custom"
            and not self.settings.portal_id_custom_charset.strip()
        ):
            raise ValidationError(
                "Custom character set cannot be empty when using 'custom' pattern"
            )

        # Check character set has enough characters for uniqueness
        charset = self._get_character_set()
        effective_length = self.settings.portal_id_length - len(
            self.settings.portal_id_prefix
        )

        if len(charset) == 0:
            raise ValidationError(
                "Character set is empty - check your exclusion settings"
            )

        # Warn if character set is too small for good uniqueness
        max_combinations = len(charset) ** effective_length
        if max_combinations < 10000:  # Less than 10K combinations
            import warnings

            warnings.warn(
                f"Portal ID configuration may not provide enough unique combinations "
                f"({max_combinations:,}). Consider increasing length or expanding character set.",
                UserWarning,
            )

    def get_configuration_summary(self) -> dict:
        """Get a summary of current Portal ID configuration."""
        charset = self._get_character_set()
        effective_length = self.settings.portal_id_length - len(
            self.settings.portal_id_prefix
        )
        max_combinations = len(charset) ** effective_length

        return {
            "pattern": self.settings.portal_id_pattern,
            "total_length": self.settings.portal_id_length,
            "prefix": self.settings.portal_id_prefix or "(none)",
            "effective_length": effective_length,
            "character_set": charset,
            "character_count": len(charset),
            "exclude_ambiguous": self.settings.portal_id_exclude_ambiguous,
            "max_combinations": max_combinations,
            "example": self._generate_single_id(),
        }

    @classmethod
    def get_pattern_examples(cls) -> dict:
        """Get examples of different Portal ID patterns."""
        return {
            "alphanumeric_clean": {
                "description": "Letters A-Z and numbers 2-9 (excludes 0,O,I,1)",
                "example": "X7N2K8QR",
                "recommended_for": "General use - avoids confusion",
            },
            "alphanumeric": {
                "description": "Letters A-Z and numbers 0-9",
                "example": "X7N0K1IR",
                "recommended_for": "Maximum variety",
            },
            "numeric": {
                "description": "Numbers only",
                "example": "87562349",
                "recommended_for": "Phone/numeric systems integration",
            },
            "custom": {
                "description": "User-defined character set",
                "example": "Based on your custom_charset setting",
                "recommended_for": "Specific organizational requirements",
            },
        }


# Global generator instance
_portal_id_generator: Optional[PortalIdGenerator] = None


def get_portal_id_generator() -> PortalIdGenerator:
    """Get or create the global Portal ID generator instance."""
    global _portal_id_generator
    if _portal_id_generator is None:
        _portal_id_generator = PortalIdGenerator()
    return _portal_id_generator


def generate_portal_id(existing_ids: Optional[Set[str]] = None) -> str:
    """
    Convenience function to generate a Portal ID.

    Args:
        existing_ids: Set of existing Portal IDs to avoid duplicates

    Returns:
        Generated unique Portal ID
    """
    return get_portal_id_generator().generate_portal_id(existing_ids)


def reload_generator_settings():
    """Reload the generator with fresh settings (useful for testing)."""
    global _portal_id_generator
    _portal_id_generator = None
