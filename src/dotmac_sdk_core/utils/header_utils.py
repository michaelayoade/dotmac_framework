"""
Header utilities for HTTP requests and responses.

Provides utilities for building standard headers, extracting context,
and handling DotMac-specific header conventions.
"""

import base64
import logging
from typing import Any, Dict, Optional, Tuple
from urllib.parse import quote

logger = logging.getLogger(__name__)


def build_headers(
    api_key: Optional[str] = None,
    bearer_token: Optional[str] = None,
    basic_auth: Optional[Tuple[str, str]] = None,
    tenant_id: Optional[str] = None,
    user_id: Optional[str] = None,
    custom_headers: Optional[Dict[str, str]] = None,
    user_agent: str = "DotMac-SDK-Core/1.0.0",
) -> Dict[str, str]:
    """
    Build standardized headers for HTTP requests.

    Args:
        api_key: API key for authentication
        bearer_token: Bearer token for authentication
        basic_auth: Username/password tuple for basic auth
        tenant_id: Tenant context identifier
        user_id: User context identifier
        custom_headers: Additional custom headers
        user_agent: User agent string

    Returns:
        Dictionary of HTTP headers
    """
    headers = {
        "User-Agent": user_agent,
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    }

    # Add authentication headers
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"
    elif api_key:
        headers["Authorization"] = f"Bearer {api_key}"  # Assume API key as bearer
        headers["X-API-Key"] = api_key  # Also add as X-API-Key
    elif basic_auth:
        username, password = basic_auth
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        headers["Authorization"] = f"Basic {credentials}"

    # Add tenant context
    if tenant_id:
        headers["X-Tenant-ID"] = tenant_id

    # Add user context
    if user_id:
        headers["X-User-ID"] = user_id

    # Add custom headers
    if custom_headers:
        headers.update(custom_headers)

    return headers


def extract_tenant_context(headers: Dict[str, str]) -> Optional[str]:
    """
    Extract tenant context from headers.

    Args:
        headers: HTTP headers dictionary

    Returns:
        Tenant ID or None
    """
    # Try common tenant header names
    tenant_headers = [
        "X-Tenant-ID",
        "X-Tenant-Id",
        "X-TenantId",
        "Tenant-ID",
        "Tenant-Id",
        "TenantId",
    ]

    for header_name in tenant_headers:
        if header_name in headers:
            return headers[header_name]

        # Try case-insensitive lookup
        for key, value in headers.items():
            if key.lower() == header_name.lower():
                return value

    return None


def extract_user_context(headers: Dict[str, str]) -> Optional[str]:
    """
    Extract user context from headers.

    Args:
        headers: HTTP headers dictionary

    Returns:
        User ID or None
    """
    # Try common user header names
    user_headers = [
        "X-User-ID",
        "X-User-Id",
        "X-UserId",
        "User-ID",
        "User-Id",
        "UserId",
    ]

    for header_name in user_headers:
        if header_name in headers:
            return headers[header_name]

        # Try case-insensitive lookup
        for key, value in headers.items():
            if key.lower() == header_name.lower():
                return value

    return None


def extract_trace_context(headers: Dict[str, str]) -> Dict[str, str]:
    """
    Extract distributed tracing context from headers.

    Args:
        headers: HTTP headers dictionary

    Returns:
        Tracing context headers
    """
    trace_headers = {}

    # W3C Trace Context headers
    trace_context_headers = ["traceparent", "tracestate", "baggage"]

    # Jaeger headers
    jaeger_headers = ["uber-trace-id"]

    # B3 Propagation headers
    b3_headers = [
        "X-B3-TraceId",
        "X-B3-SpanId",
        "X-B3-ParentSpanId",
        "X-B3-Sampled",
        "X-B3-Flags",
    ]

    all_trace_headers = trace_context_headers + jaeger_headers + b3_headers

    for header_name in all_trace_headers:
        if header_name in headers:
            trace_headers[header_name] = headers[header_name]
        else:
            # Try case-insensitive lookup
            for key, value in headers.items():
                if key.lower() == header_name.lower():
                    trace_headers[header_name] = value
                    break

    return trace_headers


def build_cors_headers(
    allow_origins: Optional[list] = None,
    allow_methods: Optional[list] = None,
    allow_headers: Optional[list] = None,
    allow_credentials: bool = False,
    max_age: int = 86400,
) -> Dict[str, str]:
    """
    Build CORS headers for responses.

    Args:
        allow_origins: Allowed origins
        allow_methods: Allowed HTTP methods
        allow_headers: Allowed headers
        allow_credentials: Allow credentials
        max_age: Preflight cache max age

    Returns:
        CORS headers
    """
    headers = {}

    if allow_origins:
        if "*" in allow_origins:
            headers["Access-Control-Allow-Origin"] = "*"
        else:
            headers["Access-Control-Allow-Origin"] = ",".join(allow_origins)

    if allow_methods:
        headers["Access-Control-Allow-Methods"] = ",".join(allow_methods)

    if allow_headers:
        headers["Access-Control-Allow-Headers"] = ",".join(allow_headers)

    if allow_credentials:
        headers["Access-Control-Allow-Credentials"] = "true"

    headers["Access-Control-Max-Age"] = str(max_age)

    return headers


def sanitize_header_value(value: str) -> str:
    """
    Sanitize header value to prevent header injection.

    Args:
        value: Raw header value

    Returns:
        Sanitized header value
    """
    if not value:
        return ""

    # Remove control characters and newlines
    sanitized = "".join(
        char for char in value if ord(char) >= 32 and char not in "\r\n"
    )

    # Limit length
    return sanitized[:8192]  # 8KB limit


def build_content_headers(
    content_type: Optional[str] = None,
    content_length: Optional[int] = None,
    content_encoding: Optional[str] = None,
    content_disposition: Optional[str] = None,
    cache_control: Optional[str] = None,
    etag: Optional[str] = None,
) -> Dict[str, str]:
    """
    Build content-related headers.

    Args:
        content_type: Content MIME type
        content_length: Content length in bytes
        content_encoding: Content encoding
        content_disposition: Content disposition
        cache_control: Cache control directives
        etag: Entity tag

    Returns:
        Content headers
    """
    headers = {}

    if content_type:
        headers["Content-Type"] = content_type

    if content_length is not None:
        headers["Content-Length"] = str(content_length)

    if content_encoding:
        headers["Content-Encoding"] = content_encoding

    if content_disposition:
        headers["Content-Disposition"] = content_disposition

    if cache_control:
        headers["Cache-Control"] = cache_control

    if etag:
        headers["ETag"] = etag

    return headers


def parse_www_authenticate_header(header_value: str) -> Dict[str, Any]:
    """
    Parse WWW-Authenticate header value.

    Args:
        header_value: WWW-Authenticate header value

    Returns:
        Parsed authentication challenge
    """
    if not header_value:
        return {}

    # Split by scheme
    parts = header_value.split(" ", 1)
    if len(parts) != 2:
        return {"scheme": header_value}

    scheme, params_str = parts
    challenge = {"scheme": scheme}

    # Parse parameters
    if params_str:
        # Simple parameter parsing (doesn't handle all edge cases)
        params = {}
        for param in params_str.split(","):
            param = param.strip()
            if "=" in param:
                key, value = param.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"')
                params[key] = value

        challenge["params"] = params

    return challenge


def build_pagination_headers(
    total_count: int,
    page: int,
    per_page: int,
    base_url: str,
    query_params: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """
    Build pagination headers (RFC 5988 Link header).

    Args:
        total_count: Total number of items
        page: Current page number
        per_page: Items per page
        base_url: Base URL for links
        query_params: Additional query parameters

    Returns:
        Pagination headers
    """
    headers = {
        "X-Total-Count": str(total_count),
        "X-Page": str(page),
        "X-Per-Page": str(per_page),
    }

    # Calculate total pages
    total_pages = (total_count + per_page - 1) // per_page
    headers["X-Total-Pages"] = str(total_pages)

    # Build Link header
    links = []
    query_str = ""
    if query_params:
        query_parts = [f"{k}={quote(str(v))}" for k, v in query_params.items()]
        query_str = "&" + "&".join(query_parts) if query_parts else ""

    # First page
    if page > 1:
        links.append(f'<{base_url}?page=1&per_page={per_page}{query_str}>; rel="first"')

    # Previous page
    if page > 1:
        links.append(
            f'<{base_url}?page={page-1}&per_page={per_page}{query_str}>; rel="prev"'
        )

    # Next page
    if page < total_pages:
        links.append(
            f'<{base_url}?page={page+1}&per_page={per_page}{query_str}>; rel="next"'
        )

    # Last page
    if page < total_pages:
        links.append(
            f'<{base_url}?page={total_pages}&per_page={per_page}{query_str}>; rel="last"'
        )

    if links:
        headers["Link"] = ", ".join(links)

    return headers
