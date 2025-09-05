"""
Common business validation utilities for DotMac Framework.
Provides reusable validation logic across modules.
"""

import re
from typing import Any, Optional
from uuid import UUID

from ..core.exceptions import ValidationError


class BusinessValidators:
    """Collection of common business validation rules."""

    @staticmethod
    def validate_email(email: str) -> str:
        """Validate email format and normalize."""
        if not email:
            raise ValidationError("Email is required")

        email = email.strip().lower()

        # Basic email regex
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, email):
            raise ValidationError("Invalid email format")

        if len(email) > 254:
            raise ValidationError("Email address too long")

        return email

    @staticmethod
    def validate_phone(phone: Optional[str]) -> Optional[str]:
        """Validate and normalize phone number."""
        if not phone:
            return None

        # Remove all non-digit characters
        digits_only = re.sub(r"\D", "", phone)

        if len(digits_only) < 10:
            raise ValidationError("Phone number must have at least 10 digits")

        if len(digits_only) > 15:
            raise ValidationError("Phone number too long")

        return digits_only

    @staticmethod
    def validate_name(name: str, field_name: str = "Name") -> str:
        """Validate person/company name."""
        if not name:
            raise ValidationError(f"{field_name} is required")

        name = name.strip()

        if len(name) < 2:
            raise ValidationError(f"{field_name} must be at least 2 characters")

        if len(name) > 100:
            raise ValidationError(f"{field_name} must be less than 100 characters")

        # Check for valid characters (letters, spaces, hyphens, apostrophes)
        if not re.match(r"^[a-zA-Z\s\-'\.]+$", name):
            raise ValidationError(f"{field_name} contains invalid characters")

        return name

    @staticmethod
    def validate_username(username: str) -> str:
        """Validate username format."""
        if not username:
            raise ValidationError("Username is required")

        username = username.strip().lower()

        if len(username) < 3:
            raise ValidationError("Username must be at least 3 characters")

        if len(username) > 50:
            raise ValidationError("Username must be less than 50 characters")

        # Username can contain letters, numbers, underscores, hyphens
        if not re.match(r"^[a-z0-9_-]+$", username):
            raise ValidationError(
                "Username can only contain letters, numbers, underscores, and hyphens"
            )

        # Cannot start or end with special characters
        if username.startswith(("-", "_")) or username.endswith(("-", "_")):
            raise ValidationError(
                "Username cannot start or end with special characters"
            )

        return username

    @staticmethod
    def validate_password(password: str) -> None:
        """Validate password strength."""
        if not password:
            raise ValidationError("Password is required")

        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long")

        if len(password) > 128:
            raise ValidationError("Password must be less than 128 characters")

        # Check for at least one lowercase letter
        if not re.search(r"[a-z]", password):
            raise ValidationError("Password must contain at least one lowercase letter")

        # Check for at least one uppercase letter
        if not re.search(r"[A-Z]", password):
            raise ValidationError("Password must contain at least one uppercase letter")

        # Check for at least one digit
        if not re.search(r"\d", password):
            raise ValidationError("Password must contain at least one number")

        # Check for at least one special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError(
                "Password must contain at least one special character"
            )

    @staticmethod
    def validate_url(url: str, field_name: str = "URL") -> str:
        """Validate URL format."""
        if not url:
            raise ValidationError(f"{field_name} is required")

        url = url.strip()

        # Basic URL validation
        url_pattern = r"^https?:\/\/(?:[-\w.])+(?:\:[0-9]+)?(?:\/(?:[\w\/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?$"
        if not re.match(url_pattern, url, re.IGNORECASE):
            raise ValidationError(f"Invalid {field_name} format")

        return url

    @staticmethod
    def validate_domain(domain: str) -> str:
        """Validate domain name format."""
        if not domain:
            raise ValidationError("Domain is required")

        domain = domain.strip().lower()

        # Remove protocol if present
        domain = re.sub(r"^https?://", "", domain)

        # Remove path if present
        domain = domain.split("/")[0]

        # Domain validation
        domain_pattern = (
            r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*"
            r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$"
        )
        if not re.match(domain_pattern, domain):
            raise ValidationError("Invalid domain format")

        return domain

    @staticmethod
    def validate_ip_address(ip: str, field_name: str = "IP address") -> str:
        """Validate IP address format (IPv4 or IPv6)."""
        if not ip:
            raise ValidationError(f"{field_name} is required")

        ip = ip.strip()

        # IPv4 pattern
        ipv4_pattern = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"

        # IPv6 pattern (simplified)
        ipv6_pattern = r"^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$|^::1$|^::$"

        if not (re.match(ipv4_pattern, ip) or re.match(ipv6_pattern, ip)):
            raise ValidationError(f"Invalid {field_name} format")

        return ip

    @staticmethod
    def validate_mac_address(mac: str) -> str:
        """Validate MAC address format."""
        if not mac:
            raise ValidationError("MAC address is required")

        mac = mac.strip().upper()

        # Support different MAC address formats
        mac_patterns = [
            r"^([0-9A-F]{2}[:-]){5}([0-9A-F]{2})$",  # AA:BB:CC:DD:EE:FF or AA-BB-CC-DD-EE-FF
            r"^([0-9A-F]{4}\.){2}([0-9A-F]{4})$",  # AABB.CCDD.EEFF
            r"^([0-9A-F]{12})$",  # AABBCCDDEEFF
        ]

        if not any(re.match(pattern, mac) for pattern in mac_patterns):
            raise ValidationError("Invalid MAC address format")

        return mac

    @staticmethod
    def validate_vlan_id(vlan_id: int) -> int:
        """Validate VLAN ID range."""
        if not isinstance(vlan_id, int):
            raise ValidationError("VLAN ID must be an integer")

        if vlan_id < 1 or vlan_id > 4094:
            raise ValidationError("VLAN ID must be between 1 and 4094")

        return vlan_id

    @staticmethod
    def validate_port_number(port: int, field_name: str = "Port") -> int:
        """Validate network port number."""
        if not isinstance(port, int):
            raise ValidationError(f"{field_name} must be an integer")

        if port < 1 or port > 65535:
            raise ValidationError(f"{field_name} must be between 1 and 65535")

        return port

    @staticmethod
    def validate_currency_code(code: str) -> str:
        """Validate ISO 4217 currency code."""
        if not code:
            raise ValidationError("Currency code is required")

        code = code.strip().upper()

        if len(code) != 3:
            raise ValidationError("Currency code must be exactly 3 characters")

        if not re.match(r"^[A-Z]{3}$", code):
            raise ValidationError("Currency code must contain only uppercase letters")

        # Basic check for common currency codes
        common_currencies = {
            "USD",
            "EUR",
            "GBP",
            "JPY",
            "CAD",
            "AUD",
            "CHF",
            "CNY",
            "SEK",
            "NZD",
            "MXN",
            "SGD",
            "HKD",
            "NOK",
            "TRY",
            "RUB",
            "INR",
            "BRL",
            "ZAR",
            "KRW",
        }

        if code not in common_currencies:
            # Still allow it but could log a warning
            pass

        return code

    @staticmethod
    def validate_amount(amount: float, field_name: str = "Amount") -> float:
        """Validate monetary amount."""
        if amount is None:
            raise ValidationError(f"{field_name} is required")

        if not isinstance(amount, (int, float)):
            raise ValidationError(f"{field_name} must be a number")

        if amount < 0:
            raise ValidationError(f"{field_name} cannot be negative")

        # Check for reasonable precision (2 decimal places for most currencies)
        if round(amount, 2) != amount:
            raise ValidationError(f"{field_name} can have at most 2 decimal places")

        # Check for reasonable maximum (adjust as needed)
        if amount > 999999999.99:
            raise ValidationError(f"{field_name} is too large")

        return float(amount)

    @staticmethod
    def validate_tenant_isolation(
        entity_tenant_id: Optional[str], user_tenant_id: Optional[str]
    ) -> None:
        """Validate tenant isolation rules."""
        if not entity_tenant_id and not user_tenant_id:
            return  # Both None is OK

        if entity_tenant_id != user_tenant_id:
            raise ValidationError("Access denied: tenant isolation violation")

    @staticmethod
    def validate_slug(slug: str, field_name: str = "Slug") -> str:
        """Validate URL-friendly slug."""
        if not slug:
            raise ValidationError(f"{field_name} is required")

        slug = slug.strip().lower()

        if len(slug) < 2:
            raise ValidationError(f"{field_name} must be at least 2 characters")

        if len(slug) > 100:
            raise ValidationError(f"{field_name} must be less than 100 characters")

        # Slug can only contain lowercase letters, numbers, and hyphens
        if not re.match(r"^[a-z0-9-]+$", slug):
            raise ValidationError(
                f"{field_name} can only contain lowercase letters, numbers, and hyphens"
            )

        # Cannot start or end with hyphen
        if slug.startswith("-") or slug.endswith("-"):
            raise ValidationError(f"{field_name} cannot start or end with hyphens")

        # Cannot have consecutive hyphens
        if "--" in slug:
            raise ValidationError(f"{field_name} cannot have consecutive hyphens")

        return slug

    @staticmethod
    def validate_uuid(uuid_str: str, field_name: str = "ID") -> UUID:
        """Validate UUID format."""
        if not uuid_str:
            raise ValidationError(f"{field_name} is required")

        try:
            return UUID(uuid_str)
        except ValueError as e:
            raise ValidationError(f"Invalid {field_name} format") from e

    @staticmethod
    def validate_json_data(
        data: Any, required_fields: list[str] | None = None
    ) -> dict[str, Any]:
        """Validate JSON data structure."""
        if not isinstance(data, dict):
            raise ValidationError("Data must be a JSON object")

        if required_fields:
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                raise ValidationError(
                    f"Missing required fields: {', '.join(missing_fields)}"
                )

        return data
