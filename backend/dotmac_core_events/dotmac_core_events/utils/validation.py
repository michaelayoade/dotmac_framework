"""
Input validation utilities for secure data handling.
"""

import re
from typing import Any, Dict

from pydantic import BaseModel, validator


class ValidationError(Exception):
    """Custom validation error."""
    pass


def validate_tenant_id(tenant_id: str) -> bool:
    """
    Validate tenant ID format.

    Args:
        tenant_id: Tenant identifier to validate

    Returns:
        True if valid

    Raises:
        ValidationError: If tenant ID is invalid
    """
    if not tenant_id:
        raise ValidationError("Tenant ID cannot be empty")

    # Allow alphanumeric, hyphens, underscores, max 64 chars
    pattern = r"^[a-zA-Z0-9_-]{1,64}$"
    if not re.match(pattern, tenant_id):
        raise ValidationError(
            "Tenant ID must contain only alphanumeric characters, hyphens, "
            "and underscores, and be 1-64 characters long"
        )

    return True


def validate_event_type(event_type: str) -> bool:
    """
    Validate event type format.

    Args:
        event_type: Event type to validate

    Returns:
        True if valid

    Raises:
        ValidationError: If event type is invalid
    """
    if not event_type:
        raise ValidationError("Event type cannot be empty")

    # Allow dot-separated alphanumeric segments
    pattern = r"^[a-zA-Z0-9][a-zA-Z0-9_-]*(\.[a-zA-Z0-9][a-zA-Z0-9_-]*)*$"
    if not re.match(pattern, event_type):
        raise ValidationError(
            "Event type must be dot-separated alphanumeric segments "
            "(e.g., 'user.created', 'order.payment.completed')"
        )

    # Check length
    if len(event_type) > 255:
        raise ValidationError("Event type cannot exceed 255 characters")

    return True


def validate_subscription_id(subscription_id: str, expected_tenant_id: str) -> bool:
    """
    Validate subscription ID format and tenant ownership.

    Args:
        subscription_id: Subscription ID to validate
        expected_tenant_id: Expected tenant ID for ownership check

    Returns:
        True if valid

    Raises:
        ValidationError: If subscription ID is invalid
    """
    if not subscription_id:
        raise ValidationError("Subscription ID cannot be empty")

    # Format: tenant_id:consumer_group:event_types
    pattern = r"^[a-zA-Z0-9_-]+:[a-zA-Z0-9_.-]+:[a-zA-Z0-9_.:|-]+$"
    if not re.match(pattern, subscription_id):
        raise ValidationError(
            "Subscription ID must follow format: tenant_id:consumer_group:event_types"
        )

    parts = subscription_id.split(":", 2)
    if len(parts) != 3:
        raise ValidationError("Subscription ID must have exactly 3 parts")

    tenant_id, consumer_group, event_types = parts

    # Validate tenant ownership
    if tenant_id != expected_tenant_id:
        raise ValidationError("Subscription ID does not belong to the specified tenant")

    # Validate tenant ID part
    validate_tenant_id(tenant_id)

    # Validate consumer group
    if not re.match(r"^[a-zA-Z0-9_.-]{1,255}$", consumer_group):
        raise ValidationError(
            "Consumer group must be alphanumeric with dots, hyphens, underscores (1-255 chars)"
        )

    return True


def validate_consumer_group(consumer_group: str) -> bool:
    """
    Validate consumer group name.

    Args:
        consumer_group: Consumer group name to validate

    Returns:
        True if valid

    Raises:
        ValidationError: If consumer group is invalid
    """
    if not consumer_group:
        raise ValidationError("Consumer group cannot be empty")

    # Allow alphanumeric, dots, hyphens, underscores
    pattern = r"^[a-zA-Z0-9_.-]{1,255}$"
    if not re.match(pattern, consumer_group):
        raise ValidationError(
            "Consumer group must contain only alphanumeric characters, dots, "
            "hyphens, and underscores, and be 1-255 characters long"
        )

    return True


def validate_partition_key(partition_key: str) -> bool:
    """
    Validate partition key format.

    Args:
        partition_key: Partition key to validate

    Returns:
        True if valid

    Raises:
        ValidationError: If partition key is invalid
    """
    if not partition_key:
        return True  # Partition key is optional

    # Allow reasonable characters, max length 512
    if len(partition_key) > 512:
        raise ValidationError("Partition key cannot exceed 512 characters")

    # Disallow control characters and some special chars
    pattern = r"^[a-zA-Z0-9_.-]+$"
    if not re.match(pattern, partition_key):
        raise ValidationError(
            "Partition key must contain only alphanumeric characters, "
            "dots, hyphens, and underscores"
        )

    return True


def validate_topic_name(topic_name: str) -> bool:
    """
    Validate topic name format.

    Args:
        topic_name: Topic name to validate

    Returns:
        True if valid

    Raises:
        ValidationError: If topic name is invalid
    """
    if not topic_name:
        raise ValidationError("Topic name cannot be empty")

    # Kafka/Redis compatible topic names
    pattern = r"^[a-zA-Z0-9._-]{1,249}$"
    if not re.match(pattern, topic_name):
        raise ValidationError(
            "Topic name must contain only alphanumeric characters, dots, "
            "hyphens, and underscores, and be 1-249 characters long"
        )

    # Disallow reserved patterns
    reserved_patterns = [r"^__.*", r".*\.$", r"^\.$", r"^\.\.$"]
    for pattern in reserved_patterns:
        if re.match(pattern, topic_name):
            raise ValidationError(f"Topic name matches reserved pattern: {pattern}")

    return True


def sanitize_string(value: str, max_length: int = 1000) -> str:
    """
    Sanitize string input by removing/escaping dangerous characters.

    Args:
        value: String to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized string

    Raises:
        ValidationError: If string is too long
    """
    if not isinstance(value, str):
        raise ValidationError("Value must be a string")

    if len(value) > max_length:
        raise ValidationError(f"String cannot exceed {max_length} characters")

    # Remove null bytes and control characters except tab, newline, carriage return
    sanitized = "".join(
        char for char in value
        if ord(char) >= 32 or char in "\t\n\r"
    )

    return sanitized


def validate_pagination_params(limit: int, offset: int) -> bool:
    """
    Validate pagination parameters.

    Args:
        limit: Maximum number of records
        offset: Number of records to skip

    Returns:
        True if valid

    Raises:
        ValidationError: If parameters are invalid
    """
    if limit <= 0:
        raise ValidationError("Limit must be greater than 0")

    if limit > 1000:
        raise ValidationError("Limit cannot exceed 1000")

    if offset < 0:
        raise ValidationError("Offset cannot be negative")

    if offset > 100000:
        raise ValidationError("Offset cannot exceed 100,000")

    return True


class SecureRequestModel(BaseModel):
    """Base model with secure validation."""

    @validator("*", pre=True)
    def sanitize_strings(cls, v):
        """Sanitize all string fields."""
        if isinstance(v, str):
            return sanitize_string(v)
        return v


def validate_json_size(data: Dict[str, Any], max_size: int = 1024 * 1024) -> bool:
    """
    Validate JSON payload size.

    Args:
        data: JSON data to validate
        max_size: Maximum size in bytes

    Returns:
        True if valid

    Raises:
        ValidationError: If payload is too large
    """
    import json

    try:
        json_str = json.dumps(data)
        size = len(json_str.encode("utf-8"))

        if size > max_size:
            raise ValidationError(
                f"JSON payload size ({size} bytes) exceeds maximum ({max_size} bytes)"
            )

        return True
    except (TypeError, ValueError) as e:
        raise ValidationError(f"Invalid JSON data: {str(e)}")
