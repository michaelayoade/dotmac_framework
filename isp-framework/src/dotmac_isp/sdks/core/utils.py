"""
Utility functions shared across all SDKs.
"""

from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timezone
import json
import warnings
import httpx
from functools import wraps
import hashlib
import hmac

from .exceptions import SDKError, SDKDeprecationWarning


def build_headers(
    api_key: Optional[str] = None,
    content_type: str = "application/json",
    additional_headers: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """
    Build standard headers for API requests.

    Args:
        api_key: Optional API key for authentication
        content_type: Content type header value
        additional_headers: Additional headers to include

    Returns:
        Dictionary of headers
    """
    headers = {
        "Content-Type": content_type,
        "Accept": "application/json",
        "User-Agent": "DotMac-SDK/1.0.0",
        "X-SDK-Version": "1.0.0",
        "X-Request-ID": generate_request_id(),
    }

    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    if additional_headers:
        headers.update(additional_headers)

    return headers


def parse_response(response: httpx.Response) -> Dict[str, Any]:
    """
    Parse HTTP response to dictionary.

    Args:
        response: HTTP response object

    Returns:
        Parsed response data

    Raises:
        SDKError: On parsing failure
    """
    try:
        # Check for deprecation headers
        if "X-Deprecated" in response.headers:
            warnings.warn(
                f"API endpoint is deprecated: {response.headers.get('X-Deprecated-Message', 'No details provided')}",
                SDKDeprecationWarning,
                stacklevel=2,
            )

        # Handle empty responses
        if not response.content:
            return {}

        # Parse JSON response
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()

        # Return raw text for non-JSON responses
        return {"data": response.text}

    except json.JSONDecodeError as e:
        raise SDKError(f"Failed to parse response: {e}")
    except Exception as e:
        raise SDKError(f"Response parsing error: {e}")


def handle_deprecation(
    deprecated_in: Optional[str] = None,
    removed_in: Optional[str] = None,
    alternative: Optional[str] = None,
):
    """
    Decorator to mark deprecated SDK methods.

    Args:
        deprecated_in: Version when deprecated
        removed_in: Version when will be removed
        alternative: Alternative method to use
    """

    def decorator(func):
        """Decorator operation."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            """Wrapper operation."""
            message = f"{func.__name__} is deprecated"

            if deprecated_in:
                message += f" since version {deprecated_in}"

            if removed_in:
                message += f" and will be removed in version {removed_in}"

            if alternative:
                message += f". Use {alternative} instead"

            warnings.warn(message, SDKDeprecationWarning, stacklevel=2)

            return func(*args, **kwargs)

        # Mark function as deprecated for documentation
        wrapper.__deprecated__ = True
        wrapper.__deprecated_info__ = {
            "deprecated_in": deprecated_in,
            "removed_in": removed_in,
            "alternative": alternative,
        }

        return wrapper

    return decorator


def generate_request_id() -> str:
    """
    Generate unique request ID for tracing.

    Returns:
        Unique request ID string
    """
    import uuid

    return str(uuid.uuid4())


def sanitize_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize query parameters for API requests.

    Args:
        params: Raw parameters

    Returns:
        Sanitized parameters
    """
    sanitized = {}

    for key, value in params.items():
        # Skip None values
        if value is None:
            continue

        # Convert datetime to ISO format
        if isinstance(value, datetime):
            sanitized[key] = value.isoformat()
        # Convert lists to comma-separated strings
        elif isinstance(value, list):
            sanitized[key] = ",".join(str(v) for v in value)
        # Convert booleans to lowercase strings
        elif isinstance(value, bool):
            sanitized[key] = str(value).lower()
        else:
            sanitized[key] = str(value)

    return sanitized


def filter_deprecated_items(
    items: List[Dict[str, Any]], include_deprecated: bool = False
) -> List[Dict[str, Any]]:
    """
    Filter out deprecated items from a list.

    Args:
        items: List of items to filter
        include_deprecated: Whether to include deprecated items

    Returns:
        Filtered list of items
    """
    if include_deprecated:
        return items

    return [
        item
        for item in items
        if not item.get("deprecated", False) and item.get("status") != "deprecated"
    ]


def validate_tenant_id(tenant_id: Optional[str]) -> str:
    """
    Validate and normalize tenant ID.

    Args:
        tenant_id: Tenant ID to validate

    Returns:
        Validated tenant ID

    Raises:
        SDKError: If tenant ID is invalid
    """
    if not tenant_id:
        return "default"

    # Remove whitespace and convert to lowercase
    tenant_id = tenant_id.strip().lower()

    # Validate format (alphanumeric + hyphens)
    import re

    if not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$", tenant_id):
        raise SDKError(f"Invalid tenant ID format: {tenant_id}")

    return tenant_id


def calculate_signature(
    secret: str, method: str, uri: str, timestamp: str, body: Optional[str] = None
) -> str:
    """
    Calculate HMAC signature for request authentication.

    Args:
        secret: Secret key for signing
        method: HTTP method
        uri: Request URI
        timestamp: Request timestamp
        body: Optional request body

    Returns:
        Base64-encoded signature
    """
    # Build string to sign
    string_to_sign = f"{method.upper()}\n{uri}\n{timestamp}"

    if body:
        # Add body hash to signature
        body_hash = hashlib.sha256(body.encode()).hexdigest()
        string_to_sign += f"\n{body_hash}"

    # Calculate HMAC-SHA256
    signature = hmac.new(
        secret.encode(), string_to_sign.encode(), hashlib.sha256
    ).digest()

    # Return base64-encoded signature
    import base64

    return base64.b64encode(signature).decode()


def format_error_response(
    error: Exception, request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Format exception as standardized error response.

    Args:
        error: Exception to format
        request_id: Optional request ID for tracing

    Returns:
        Formatted error response
    """
    if isinstance(error, SDKError):
        response = error.to_dict()
    else:
        response = {
            "error": error.__class__.__name__,
            "message": str(error),
            "details": {},
        }

    if request_id:
        response["request_id"] = request_id

    response["timestamp"] = datetime.now(timezone.utc).isoformat()

    return response


def chunk_list(items: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Split a list into chunks of specified size.

    Args:
        items: List to chunk
        chunk_size: Maximum size of each chunk

    Returns:
        List of chunks
    """
    return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]


def merge_configs(*configs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge multiple configuration dictionaries.
    Later configs override earlier ones.

    Args:
        *configs: Configuration dictionaries to merge

    Returns:
        Merged configuration
    """
    result = {}

    for config in configs:
        if config:
            result.update(config)

    return result
