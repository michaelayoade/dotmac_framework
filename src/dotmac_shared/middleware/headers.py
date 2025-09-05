"""
Header Extractor for DotMac Framework.

Provides standardized header extraction and parsing to eliminate
duplication in header handling across middleware components.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from fastapi import Request

logger = logging.getLogger(__name__)


@dataclass
class HeaderConfig:
    """Configuration for header extraction."""

    # Standard header mappings with fallbacks
    STANDARD_HEADERS = {
        "tenant_id": ["X-Tenant-ID", "x-tenant-id", "Tenant-ID"],
        "api_version": [
            "X-API-Version",
            "x-api-version",
            "API-Version",
            "Accept-Version",
        ],
        "idempotency_key": ["Idempotency-Key", "idempotency-key", "X-Idempotency-Key"],
        "container_tenant": ["X-Container-Tenant", "x-container-tenant"],
        "user_id": ["X-User-ID", "x-user-id", "User-ID"],
        "session_id": ["X-Session-ID", "x-session-id", "Session-ID"],
        "correlation_id": ["X-Correlation-ID", "x-correlation-id", "Correlation-ID"],
        "trace_id": ["X-Trace-ID", "x-trace-id", "Trace-ID"],
        "request_id": ["X-Request-ID", "x-request-id", "Request-ID"],
        "forwarded_for": ["X-Forwarded-For", "x-forwarded-for"],
        "real_ip": ["X-Real-IP", "x-real-ip"],
        "origin": ["Origin", "X-Origin"],
        "referer": ["Referer", "Referrer"],
        "csrf_token": ["X-CSRF-Token", "x-csrf-token", "CSRF-Token"],
        "auth_token": ["Authorization", "X-Auth-Token"],
        "client_version": ["X-Client-Version", "x-client-version"],
        "platform": ["X-Platform", "x-platform"],
        "device_id": ["X-Device-ID", "x-device-id"],
    }

    # Content type mappings
    CONTENT_TYPE_MAPPINGS = {
        "json": ["application/json", "text/json"],
        "xml": ["application/xml", "text/xml"],
        "form": ["application/x-www-form-urlencoded"],
        "multipart": ["multipart/form-data"],
        "text": ["text/plain"],
        "html": ["text/html"],
    }


@dataclass
class ExtractedHeaders:
    """Container for extracted headers with metadata."""

    # Standard fields
    tenant_id: str | None = None
    api_version: str | None = None
    idempotency_key: str | None = None
    container_tenant: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    correlation_id: str | None = None

    # Client info
    client_ip: str | None = None
    user_agent: str | None = None
    origin: str | None = None
    referer: str | None = None

    # Security
    csrf_token: str | None = None
    auth_token: str | None = None

    # Content info
    content_type: str | None = None
    content_length: int | None = None
    accept: str | None = None

    # Custom headers
    custom: dict[str, str] = field(default_factory=dict)

    # Extraction metadata
    sources: dict[str, str] = field(default_factory=dict)  # field -> source_header
    validation_errors: list[str] = field(default_factory=list)


class HeaderExtractor:
    """Standardized header extraction with validation and fallbacks."""

    def __init__(self, config: HeaderConfig | None = None):
        """Initialize header extractor.

        Args:
            config: Optional header configuration
        """
        self.config = config or HeaderConfig()

    def extract_all(self, request: Request) -> ExtractedHeaders:
        """Extract all standard headers from request.

        Args:
            request: FastAPI request object

        Returns:
            ExtractedHeaders with all extracted values
        """
        extracted = ExtractedHeaders()

        # Extract standard headers
        for field_name, header_variations in self.config.STANDARD_HEADERS.items():
            value, source = self._extract_header_with_fallback(request, header_variations)
            if value:
                setattr(extracted, field_name, value)
                extracted.sources[field_name] = source

        # Extract client IP (with proxy handling)
        extracted.client_ip = self._extract_client_ip(request)

        # Extract content info
        extracted.content_type = self._normalize_content_type(request.headers.get("content-type", ""))
        extracted.content_length = self._safe_int(request.headers.get("content-length"))
        extracted.accept = request.headers.get("accept")
        extracted.user_agent = request.headers.get("user-agent")

        # Validate extracted headers
        extracted.validation_errors = self._validate_headers(extracted)

        logger.debug(f"Extracted headers: {len([f for f in extracted.__dict__ if getattr(extracted, f)])}")

        return extracted

    def extract(self, request: Request, header_key: str) -> str | None:
        """Extract specific header with fallback variations.

        Args:
            request: FastAPI request object
            header_key: Key from STANDARD_HEADERS or custom header name

        Returns:
            Header value if found, None otherwise
        """
        if header_key in self.config.STANDARD_HEADERS:
            value, _ = self._extract_header_with_fallback(request, self.config.STANDARD_HEADERS[header_key])
            return value
        else:
            # Direct header lookup
            return request.headers.get(header_key)

    def extract_multiple(self, request: Request, header_keys: list[str]) -> dict[str, str | None]:
        """Extract multiple headers at once.

        Args:
            request: FastAPI request object
            header_keys: List of header keys to extract

        Returns:
            Dictionary of extracted headers
        """
        result = {}
        for key in header_keys:
            result[key] = self.extract(request, key)
        return result

    def extract_tenant_context(self, request: Request) -> tuple[str | None, str, dict[str, str]]:
        """Extract tenant context with source tracking.

        Args:
            request: FastAPI request object

        Returns:
            Tuple of (tenant_id, source, all_sources)
        """
        sources = {}

        # Priority order: gateway header > container > subdomain > JWT

        # 1. Gateway header (highest priority)
        gateway_tenant, gateway_source = self._extract_header_with_fallback(request, ["X-Tenant-ID", "x-tenant-id"])
        if gateway_tenant:
            sources["gateway"] = gateway_tenant

        # 2. Container context
        container_tenant, container_source = self._extract_header_with_fallback(
            request, ["X-Container-Tenant", "x-container-tenant"]
        )
        if container_tenant:
            sources["container"] = container_tenant

        # 3. Subdomain extraction
        subdomain_tenant = self._extract_tenant_from_subdomain(request)
        if subdomain_tenant:
            sources["subdomain"] = subdomain_tenant

        # 4. JWT token (would need JWT parsing - placeholder for now)
        jwt_tenant = self._extract_tenant_from_jwt(request)
        if jwt_tenant:
            sources["jwt"] = jwt_tenant

        # Determine primary tenant (highest priority available)
        if gateway_tenant:
            return gateway_tenant, "gateway_header", sources
        elif container_tenant:
            return container_tenant, "container_context", sources
        elif subdomain_tenant:
            return subdomain_tenant, "subdomain", sources
        elif jwt_tenant:
            return jwt_tenant, "jwt_token", sources
        else:
            return None, "none", sources

    def extract_versioning_info(self, request: Request) -> tuple[str | None, str]:
        """Extract API version with source tracking.

        Args:
            request: FastAPI request object

        Returns:
            Tuple of (version, source)
        """
        # Priority: header > query param > path

        # 1. Header (preferred)
        version, source = self._extract_header_with_fallback(request, ["X-API-Version", "x-api-version", "API-Version"])
        if version:
            return self._normalize_version(version), "header"

        # 2. Query parameter
        version = request.query_params.get("version")
        if version:
            return self._normalize_version(version), "query_param"

        # 3. Path extraction (e.g., /api/v1/...)
        path_version = self._extract_version_from_path(request.url.path)
        if path_version:
            return path_version, "path"

        return None, "none"

    def extract_security_headers(self, request: Request) -> dict[str, Any]:
        """Extract security-related headers.

        Args:
            request: FastAPI request object

        Returns:
            Dictionary of security headers
        """
        return {
            "csrf_token": self.extract(request, "csrf_token"),
            "auth_token": self.extract(request, "auth_token"),
            "origin": self.extract(request, "origin"),
            "referer": self.extract(request, "referer"),
            "client_ip": self._extract_client_ip(request),
            "user_agent": request.headers.get("user-agent"),
            "forwarded_proto": request.headers.get("x-forwarded-proto"),
            "forwarded_host": request.headers.get("x-forwarded-host"),
        }

    def _extract_header_with_fallback(
        self, request: Request, header_variations: list[str]
    ) -> tuple[str | None, str | None]:
        """Extract header with fallback variations.

        Args:
            request: FastAPI request object
            header_variations: List of header names to try

        Returns:
            Tuple of (value, source_header)
        """
        for header in header_variations:
            value = request.headers.get(header)
            if value:
                return value.strip(), header
        return None, None

    def _extract_client_ip(self, request: Request) -> str | None:
        """Extract client IP with proxy support.

        Args:
            request: FastAPI request object

        Returns:
            Client IP address
        """
        # Check proxy headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Get first IP from comma-separated list
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()

        # Fallback to direct client IP
        if request.client:
            return request.client.host

        return None

    def _extract_tenant_from_subdomain(self, request: Request) -> str | None:
        """Extract tenant ID from subdomain.

        Args:
            request: FastAPI request object

        Returns:
            Tenant ID from subdomain
        """
        try:
            host = request.headers.get("host", "")
            if not host or "." not in host:
                return None

            subdomain = host.split(".")[0]

            # Validate subdomain format (alphanumeric with hyphens/underscores)
            if len(subdomain) >= 3 and re.match(r"^[a-zA-Z0-9_-]+$", subdomain):
                # Exclude common non-tenant subdomains
                excluded_subdomains = {
                    "www",
                    "api",
                    "admin",
                    "app",
                    "cdn",
                    "static",
                    "assets",
                }
                if subdomain.lower() not in excluded_subdomains:
                    return subdomain

        except Exception as e:
            logger.warning(f"Failed to extract tenant from subdomain: {e}")

        return None

    def _extract_tenant_from_jwt(self, request: Request) -> str | None:
        """Extract tenant ID from JWT token.

        Args:
            request: FastAPI request object

        Returns:
            Tenant ID from JWT (placeholder implementation)
        """
        # This would require JWT parsing - placeholder for now
        # In practice, you'd decode the JWT and extract the tenant claim
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            # TODO: Implement JWT parsing to extract tenant_id claim
            pass
        return None

    def _extract_version_from_path(self, path: str) -> str | None:
        """Extract API version from request path.

        Args:
            path: Request path

        Returns:
            Version from path (e.g., 'v1' from '/api/v1/...')
        """
        # Match patterns like /api/v1/, /v2/, etc.
        version_match = re.search(r"/v(\d+(?:\.\d+)?)", path)
        if version_match:
            return f"v{version_match.group(1)}"

        return None

    def _normalize_version(self, version: str) -> str:
        """Normalize version string.

        Args:
            version: Raw version string

        Returns:
            Normalized version string
        """
        version = version.lower().strip()
        if not version.startswith("v"):
            version = f"v{version}"
        return version

    def _normalize_content_type(self, content_type: str) -> str | None:
        """Normalize content type to standard categories.

        Args:
            content_type: Raw content type header

        Returns:
            Normalized content type category
        """
        if not content_type:
            return None

        content_type = content_type.lower().split(";")[0].strip()

        for category, types in self.config.CONTENT_TYPE_MAPPINGS.items():
            if content_type in types:
                return category

        return content_type

    def _safe_int(self, value: str | None) -> int | None:
        """Safely convert string to int.

        Args:
            value: String value

        Returns:
            Integer value or None
        """
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    def _validate_headers(self, extracted: ExtractedHeaders) -> list[str]:
        """Validate extracted headers.

        Args:
            extracted: Extracted headers

        Returns:
            List of validation errors
        """
        errors = []

        # Validate tenant ID format
        if extracted.tenant_id and len(extracted.tenant_id) < 3:
            errors.append("Tenant ID too short")

        # Validate API version format
        if extracted.api_version and not re.match(r"^v\d+(\.\d+)?$", extracted.api_version):
            errors.append("Invalid API version format")

        # Validate idempotency key format
        if extracted.idempotency_key and len(extracted.idempotency_key) < 8:
            errors.append("Idempotency key too short")

        return errors


# Convenience functions
def extract_headers(request: Request) -> ExtractedHeaders:
    """Convenience function to extract all headers."""
    extractor = HeaderExtractor()
    return extractor.extract_all(request)


def extract_header(request: Request, header_key: str) -> str | None:
    """Convenience function to extract single header."""
    extractor = HeaderExtractor()
    return extractor.extract(request, header_key)


def extract_tenant_info(request: Request) -> tuple[str | None, str, dict[str, str]]:
    """Convenience function to extract tenant context."""
    extractor = HeaderExtractor()
    return extractor.extract_tenant_context(request)
