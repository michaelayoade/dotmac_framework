"""
Common validation patterns for DotMac Framework
"""

import re

from email_validator import EmailNotValidError, validate_email

from dotmac.core import ValidationError


class CommonValidators:
    """Collection of common validation utilities"""

    # Regex patterns
    SUBDOMAIN_PATTERN = re.compile(r"^[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?$")
    TENANT_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9\-_]{2,31}$")
    PHONE_PATTERN = re.compile(r"^\+?1?\d{9,15}$")

    @staticmethod
    def validate_email_address(email: str) -> str:
        """
        Validate email address format

        Args:
            email: Email address to validate

        Returns:
            Normalized email address

        Raises:
            ValidationError: If email is invalid
        """
        try:
            # Use email-validator library for comprehensive validation
            validated = validate_email(email)
            return validated.email
        except EmailNotValidError as e:
            msg = f"Invalid email address: {e}"

            raise ValidationError(msg) from e

    @staticmethod
    def validate_subdomain(subdomain: str) -> str:
        """
        Validate subdomain format

        Args:
            subdomain: Subdomain to validate

        Returns:
            Normalized subdomain

        Raises:
            ValidationError: If subdomain is invalid
        """
        if not subdomain:
            msg = "Subdomain cannot be empty"
            raise ValidationError(msg)

        subdomain = subdomain.lower().strip()

        if not CommonValidators.SUBDOMAIN_PATTERN.match(subdomain):
            raise ValidationError(
                "Subdomain must contain only lowercase letters, numbers, and hyphens. "
                "Cannot start or end with a hyphen."
            )

        if len(subdomain) > 63:
            msg = "Subdomain cannot exceed 63 characters"
            raise ValidationError(msg)

        # Check for reserved subdomains
        reserved = ["www", "api", "admin", "mail", "ftp", "localhost"]
        if subdomain in reserved:
            msg = f"Subdomain '{subdomain}' is reserved"

            raise ValidationError(msg)

        return subdomain

    @staticmethod
    def validate_tenant_id(tenant_id: str) -> str:
        """
        Validate tenant ID format

        Args:
            tenant_id: Tenant ID to validate

        Returns:
            Normalized tenant ID

        Raises:
            ValidationError: If tenant ID is invalid
        """
        if not tenant_id:
            msg = "Tenant ID cannot be empty"
            raise ValidationError(msg)

        tenant_id = tenant_id.lower().strip()

        if not CommonValidators.TENANT_ID_PATTERN.match(tenant_id):
            raise ValidationError(
                "Tenant ID must start with alphanumeric character and contain only "
                "lowercase letters, numbers, hyphens, and underscores (3-32 characters)"
            )

        return tenant_id

    @staticmethod
    def validate_phone_number(phone: str) -> str:
        """
        Validate phone number format

        Args:
            phone: Phone number to validate

        Returns:
            Normalized phone number

        Raises:
            ValidationError: If phone number is invalid
        """
        if not phone:
            msg = "Phone number cannot be empty"

            raise ValidationError(msg)

        # Remove all non-digit characters except +
        cleaned = re.sub(r"[^\d+]", "", phone)

        if not CommonValidators.PHONE_PATTERN.match(cleaned):
            raise ValidationError(
                "Invalid phone number format. Must be 9-15 digits, optionally starting with +"
            )

        return cleaned

    @staticmethod
    def validate_required_fields(data: dict, required_fields: list[str]) -> None:
        """
        Validate that all required fields are present and not empty

        Args:
            data: Data dictionary to validate
            required_fields: List of required field names

        Raises:
            ValidationError: If any required field is missing or empty
        """
        missing_fields = []
        empty_fields = []

        for field in required_fields:
            if field not in data:
                missing_fields.append(field)
            elif not data[field] or (isinstance(data[field], str) and not data[field].strip()):
                empty_fields.append(field)

        errors = []
        if missing_fields:
            errors.append(f"Missing required fields: {', '.join(missing_fields)}")
        if empty_fields:
            errors.append(f"Empty required fields: {', '.join(empty_fields)}")

        if errors:
            raise ValidationError("; ".join(errors))

    @staticmethod
    def validate_string_length(
        value: str,
        field_name: str,
        min_length: int | None = None,
        max_length: int | None = None,
    ) -> None:
        """
        Validate string length constraints

        Args:
            value: String value to validate
            field_name: Name of the field for error messages
            min_length: Minimum required length
            max_length: Maximum allowed length

        Raises:
            ValidationError: If length constraints are violated
        """
        if min_length is not None and len(value) < min_length:
            msg = f"{field_name} must be at least {min_length} characters long"

            raise ValidationError(msg)

        if max_length is not None and len(value) > max_length:
            msg = f"{field_name} cannot exceed {max_length} characters"

            raise ValidationError(msg)
