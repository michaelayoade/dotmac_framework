"""
Core utilities for SDK operations.

Provides common utility functions for HTTP operations, data parsing,
validation, and other shared functionality across all SDKs.
"""

from typing import Dict, Any, Optional, Union, List
from datetime import datetime
import json
import uuid
import httpx
import logging

logger = logging.getLogger(__name__)


def build_headers(
    api_key: Optional[str] = None,
    tenant_id: Optional[str] = None,
    additional_headers: Optional[Dict[str, str]] = None
) -> Dict[str, str]:
    """
    Build HTTP headers for SDK requests.
    
    Args:
        api_key: Optional API key for authentication
        tenant_id: Tenant ID for multi-tenant isolation
        additional_headers: Additional custom headers
        
    Returns:
        Dictionary of HTTP headers
    """
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "dotmac-isp-sdk/1.0.0",
    }
    
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    if tenant_id:
        headers["X-Tenant-ID"] = tenant_id
    
    if additional_headers:
        headers.update(additional_headers)
    
    return headers


def parse_response(response: httpx.Response) -> Dict[str, Any]:
    """
    Parse HTTP response into dictionary.
    
    Args:
        response: HTTP response object
        
    Returns:
        Parsed response data
        
    Raises:
        ValueError: If response cannot be parsed
    """
    try:
        if response.headers.get("content-type", "").startswith("application/json"):
            return response.json()
        else:
            # Return text content wrapped in dict for non-JSON responses
            return {"content": response.text, "status_code": response.status_code}
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse response JSON: {e}")
        return {"error": "Invalid JSON response", "content": response.text}


def validate_uuid(value: Union[str, uuid.UUID]) -> uuid.UUID:
    """
    Validate and convert UUID value.
    
    Args:
        value: UUID string or UUID object
        
    Returns:
        Valid UUID object
        
    Raises:
        ValueError: If value is not a valid UUID
    """
    if isinstance(value, uuid.UUID):
        return value
    
    try:
        return uuid.UUID(str(value))
    except ValueError as e:
        raise ValueError(f"Invalid UUID format: {value}") from e


def validate_email(email: str) -> bool:
    """
    Basic email validation.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if email appears valid
    """
    if not email or "@" not in email:
        return False
    
    parts = email.split("@")
    if len(parts) != 2:
        return False
    
    local, domain = parts
    if not local or not domain:
        return False
    
    if "." not in domain:
        return False
    
    return True


def validate_phone(phone: str) -> bool:
    """
    Basic phone number validation.
    
    Args:
        phone: Phone number to validate
        
    Returns:
        True if phone appears valid
    """
    if not phone:
        return False
    
    # Remove common formatting characters
    cleaned = "".join(c for c in phone if c.isdigit() or c == "+")
    
    # Check length (international format)
    if len(cleaned) < 10 or len(cleaned) > 15:
        return False
    
    return True


def sanitize_string(value: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize string input for security.
    
    Args:
        value: String to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        value = str(value)
    
    # Strip whitespace
    value = value.strip()
    
    # Remove null bytes and control characters
    value = "".join(c for c in value if ord(c) >= 32 or c in ['\n', '\r', '\t'])
    
    # Truncate if necessary
    if max_length and len(value) > max_length:
        value = value[:max_length]
    
    return value


def paginate_list(
    items: List[Any],
    page: int = 1,
    page_size: int = 50,
    max_page_size: int = 1000
) -> Dict[str, Any]:
    """
    Paginate a list of items.
    
    Args:
        items: List of items to paginate
        page: Page number (1-based)
        page_size: Items per page
        max_page_size: Maximum allowed page size
        
    Returns:
        Paginated response with metadata
    """
    # Validate pagination parameters
    page = max(1, page)
    page_size = max(1, min(page_size, max_page_size))
    
    total_items = len(items)
    total_pages = (total_items + page_size - 1) // page_size
    
    # Calculate slice bounds
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    
    # Get page items
    page_items = items[start_index:end_index]
    
    return {
        "items": page_items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1,
        }
    }


def generate_request_id() -> str:
    """
    Generate unique request ID for tracing.
    
    Returns:
        Unique request identifier
    """
    return f"req_{uuid.uuid4().hex[:16]}"


def format_datetime(dt: datetime) -> str:
    """
    Format datetime for API responses.
    
    Args:
        dt: Datetime to format
        
    Returns:
        ISO formatted datetime string
    """
    return dt.isoformat() if dt else None


def parse_datetime(dt_str: str) -> Optional[datetime]:
    """
    Parse datetime string from API.
    
    Args:
        dt_str: Datetime string to parse
        
    Returns:
        Parsed datetime object or None
    """
    if not dt_str:
        return None
    
    try:
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except ValueError:
        logger.warning(f"Failed to parse datetime: {dt_str}")
        return None


def build_query_params(
    params: Dict[str, Any],
    exclude_none: bool = True
) -> Dict[str, str]:
    """
    Build query parameters for HTTP requests.
    
    Args:
        params: Parameters dictionary
        exclude_none: Whether to exclude None values
        
    Returns:
        Cleaned query parameters
    """
    if not params:
        return {}
    
    query_params = {}
    
    for key, value in params.items():
        if value is None and exclude_none:
            continue
        
        if isinstance(value, bool):
            query_params[key] = str(value).lower()
        elif isinstance(value, (list, tuple)):
            query_params[key] = ",".join(str(v) for v in value)
        else:
            query_params[key] = str(value)
    
    return query_params


def deep_merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries.
    
    Args:
        dict1: First dictionary
        dict2: Second dictionary (takes precedence)
        
    Returns:
        Merged dictionary
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if (key in result and 
            isinstance(result[key], dict) and 
            isinstance(value, dict)):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result


def mask_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mask sensitive data in dictionary for logging.
    
    Args:
        data: Dictionary containing potentially sensitive data
        
    Returns:
        Dictionary with sensitive fields masked
    """
    sensitive_fields = {
        'password', 'token', 'secret', 'key', 'api_key',
        'auth_token', 'access_token', 'refresh_token',
        'credit_card', 'ssn', 'social_security_number'
    }
    
    def mask_dict(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {
                key: "***MASKED***" if key.lower() in sensitive_fields else mask_dict(value)
                for key, value in obj.items()
            }
        elif isinstance(obj, list):
            return [mask_dict(item) for item in obj]
        else:
            return obj
    
    return mask_dict(data)


class RequestContext:
    """
    Context object for tracking request information across SDK operations.
    """
    
    def __init__(
        self,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None
    ):
        """
        Initialize request context.
        
        Args:
            request_id: Unique request identifier
            user_id: User making the request
            tenant_id: Tenant context
        """
        self.request_id = request_id or generate_request_id()
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.start_time = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert context to dictionary.
        
        Returns:
            Context as dictionary
        """
        return {
            "request_id": self.request_id,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "start_time": self.start_time.isoformat(),
        }