"""
Request builder for constructing HTTP requests with DotMac conventions.

Provides standardized request construction with authentication,
tenant context, and DotMac-specific headers.
"""

import json
import logging
from typing import Any, Dict, Optional, Union
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


class RequestBuilder:
    """
    Builds standardized HTTP requests for DotMac services.

    Handles authentication, tenant context, headers, and request formatting
    according to DotMac conventions.
    """

    def __init__(self, config: "HTTPClientConfig"):
        """
        Initialize request builder.

        Args:
            config: HTTP client configuration
        """
        self.config = config

    def build_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Union[str, bytes, Dict[str, Any]]] = None,
        files: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Build HTTP request parameters.

        Args:
            method: HTTP method
            url: Request URL
            params: Query parameters
            json: JSON request body
            data: Request body data
            files: File uploads
            headers: Additional headers
            timeout: Request timeout
            tenant_id: Tenant context
            user_id: User context
            **kwargs: Additional request parameters

        Returns:
            Dictionary of request parameters for httpx
        """
        # Build URL
        request_url = self._build_url(url)

        # Build headers
        request_headers = self._build_headers(
            headers=headers,
            tenant_id=tenant_id,
            user_id=user_id,
            has_json=json is not None,
            has_files=files is not None,
        )

        # Build request parameters
        request_params = {
            "method": method.upper(),
            "url": request_url,
            "headers": request_headers,
        }

        # Add query parameters
        if params:
            request_params["params"] = self._clean_params(params)

        # Add request body
        if json is not None:
            request_params["json"] = json
        elif data is not None:
            request_params["data"] = data

        # Add files
        if files:
            request_params["files"] = files

        # Add timeout
        if timeout is not None:
            request_params["timeout"] = timeout
        elif self.config.timeout:
            request_params["timeout"] = self.config.timeout

        # Add any additional parameters
        request_params.update(kwargs)

        return request_params

    def _build_url(self, url: str) -> str:
        """
        Build complete request URL.

        Args:
            url: Relative or absolute URL

        Returns:
            Complete URL
        """
        # If already absolute URL, return as-is
        if urlparse(url).netloc:
            return url

        # Join with base URL
        return urljoin(self.config.base_url, url.lstrip("/"))

    def _build_headers(
        self,
        headers: Optional[Dict[str, str]] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        has_json: bool = False,
        has_files: bool = False,
    ) -> Dict[str, str]:
        """
        Build request headers.

        Args:
            headers: Additional headers
            tenant_id: Tenant context
            user_id: User context
            has_json: Whether request has JSON body
            has_files: Whether request has file uploads

        Returns:
            Complete headers dictionary
        """
        request_headers = {}

        # Start with default headers from config
        request_headers.update(self.config.default_headers)

        # Add User-Agent
        request_headers["User-Agent"] = self.config.user_agent

        # Add Content-Type for JSON requests
        if has_json and not has_files:
            request_headers["Content-Type"] = "application/json"

        # Add Accept header
        if "Accept" not in request_headers:
            request_headers["Accept"] = "application/json, text/plain, */*"

        # Add tenant context
        if tenant_id:
            request_headers[self.config.tenant_header_name] = tenant_id

        # Add user context
        if user_id:
            request_headers[self.config.user_header_name] = user_id

        # Add authentication headers
        if self.config.auth_provider:
            auth_headers = self.config.auth_provider.get_auth_headers()
            request_headers.update(auth_headers)

        # Add request ID for tracing
        request_headers["X-Request-ID"] = self._generate_request_id()

        # Add DotMac service identification
        request_headers["X-DotMac-Service"] = self.config.service_name

        # Override with provided headers
        if headers:
            request_headers.update(headers)

        return request_headers

    def _clean_params(self, params: Dict[str, Any]) -> Dict[str, str]:
        """
        Clean and normalize query parameters.

        Args:
            params: Raw parameters

        Returns:
            Cleaned parameters
        """
        cleaned = {}

        for key, value in params.items():
            if value is None:
                continue

            # Convert to string
            if isinstance(value, bool):
                cleaned[key] = "true" if value else "false"
            elif isinstance(value, (list, tuple)):
                # Handle array parameters
                if len(value) == 1:
                    cleaned[key] = str(value[0])
                else:
                    # Multiple values - use comma separation
                    cleaned[key] = ",".join(str(v) for v in value)
            else:
                cleaned[key] = str(value)

        return cleaned

    def _generate_request_id(self) -> str:
        """
        Generate unique request ID for tracing.

        Returns:
            Unique request identifier
        """
        import uuid

        return str(uuid.uuid4())

    def build_pagination_params(
        self,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build standardized pagination parameters.

        Args:
            page: Page number (1-based)
            per_page: Items per page
            limit: Maximum items to return
            offset: Number of items to skip
            cursor: Cursor for cursor-based pagination

        Returns:
            Pagination parameters
        """
        params = {}

        # Page-based pagination
        if page is not None:
            params["page"] = max(1, page)

        if per_page is not None:
            params["per_page"] = max(1, min(per_page, 1000))  # Cap at 1000

        # Offset-based pagination
        if limit is not None:
            params["limit"] = max(1, min(limit, 1000))  # Cap at 1000

        if offset is not None:
            params["offset"] = max(0, offset)

        # Cursor-based pagination
        if cursor is not None:
            params["cursor"] = cursor

        return params

    def build_filter_params(
        self,
        filters: Optional[Dict[str, Any]] = None,
        search: Optional[str] = None,
        sort: Optional[str] = None,
        sort_direction: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build standardized filter parameters.

        Args:
            filters: Field filters
            search: Search query
            sort: Sort field
            sort_direction: Sort direction ('asc' or 'desc')

        Returns:
            Filter parameters
        """
        params = {}

        # Add search
        if search:
            params["search"] = search.strip()

        # Add sorting
        if sort:
            if sort_direction and sort_direction.lower() in ("desc", "descending"):
                params["sort"] = f"-{sort}"
            else:
                params["sort"] = sort

        # Add filters
        if filters:
            for key, value in filters.items():
                if value is not None:
                    # Use filter prefix for field filters
                    filter_key = (
                        f"filter[{key}]" if not key.startswith("filter[") else key
                    )
                    params[filter_key] = value

        return params

    def build_include_params(
        self,
        include: Optional[Union[str, list]] = None,
        fields: Optional[Dict[str, Union[str, list]]] = None,
    ) -> Dict[str, Any]:
        """
        Build JSON:API-style include/fields parameters.

        Args:
            include: Related resources to include
            fields: Sparse fieldsets per resource type

        Returns:
            Include/fields parameters
        """
        params = {}

        # Add includes
        if include:
            if isinstance(include, list):
                params["include"] = ",".join(include)
            else:
                params["include"] = include

        # Add sparse fieldsets
        if fields:
            for resource_type, field_list in fields.items():
                if isinstance(field_list, list):
                    params[f"fields[{resource_type}]"] = ",".join(field_list)
                else:
                    params[f"fields[{resource_type}]"] = field_list

        return params
