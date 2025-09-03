"""
API Versioning Middleware for DotMac Framework.

Provides standardized API versioning with:
- Standard header X-API-Version
- Deprecation headers and routing policy
- Version compatibility checks
- Sunset date notifications
"""

import logging
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime
from datetime import timezone as dt_timezone
from dataclasses import dataclass
from enum import Enum

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class VersionStatus(str, Enum):
    """API version status."""
    CURRENT = "current"
    SUPPORTED = "supported" 
    DEPRECATED = "deprecated"
    SUNSET = "sunset"


@dataclass
class APIVersionInfo:
    """API version information."""
    version: str
    status: VersionStatus
    sunset_date: Optional[datetime] = None
    replacement_version: Optional[str] = None
    breaking_changes: List[str] = None
    
    def __post_init__(self):
        if self.breaking_changes is None:
            self.breaking_changes = []


class APIVersioningMiddleware:
    """API versioning middleware with deprecation support."""
    
    def __init__(self, 
                 default_version: str = "v1",
                 supported_versions: Optional[Dict[str, APIVersionInfo]] = None):
        """Initialize API versioning middleware.
        
        Args:
            default_version: Default API version if none specified
            supported_versions: Dictionary of version info
        """
        self.default_version = default_version
        self.supported_versions = supported_versions or self._get_default_versions()
        self.exempt_paths: Set[str] = {
            "/docs", "/redoc", "/openapi.json", "/health", "/metrics"
        }
        
    def _get_default_versions(self) -> Dict[str, APIVersionInfo]:
        """Get default version configuration."""
        return {
            "v1": APIVersionInfo(
                version="v1",
                status=VersionStatus.CURRENT
            ),
            "v2": APIVersionInfo(
                version="v2", 
                status=VersionStatus.SUPPORTED
            )
        }
        
    async def process_request(self, request: Request) -> Tuple[str, Optional[Dict[str, str]]]:
        """Process API version from request.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Tuple of (version, warning_headers)
        """
        # Skip exempt paths
        if self._is_exempt_path(request.url.path):
            return self.default_version, None
            
        # Extract version from request
        requested_version = self._extract_version(request)
        
        # Validate version
        version_info = await self._validate_version(requested_version)
        
        # Generate warning headers
        warning_headers = self._generate_warning_headers(version_info)
        
        # Set request state
        request.state.api_version = version_info.version
        request.state.version_info = version_info
        
        return version_info.version, warning_headers
        
    def _extract_version(self, request: Request) -> str:
        """Extract API version from request."""
        # Priority order: header > query param > path > default
        
        # 1. X-API-Version header (preferred)
        version = request.headers.get("X-API-Version") or request.headers.get("x-api-version")
        if version:
            return self._normalize_version(version)
            
        # 2. Query parameter
        version = request.query_params.get("version")
        if version:
            return self._normalize_version(version)
            
        # 3. Path prefix (e.g., /api/v1/...)
        path_parts = request.url.path.strip("/").split("/")
        if len(path_parts) >= 2 and path_parts[0] == "api" and path_parts[1].startswith("v"):
            return path_parts[1]
            
        # 4. Default version
        return self.default_version
        
    def _normalize_version(self, version: str) -> str:
        """Normalize version string."""
        version = version.lower().strip()
        if not version.startswith("v"):
            version = f"v{version}"
        return version
        
    async def _validate_version(self, requested_version: str) -> APIVersionInfo:
        """Validate requested version.
        
        Args:
            requested_version: Requested API version
            
        Returns:
            APIVersionInfo for the version
            
        Raises:
            HTTPException: If version is not supported
        """
        version_info = self.supported_versions.get(requested_version)
        
        if not version_info:
            # Try to find closest supported version
            closest = self._find_closest_version(requested_version)
            if closest:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"API version '{requested_version}' not supported. Use '{closest}' instead.",
                    headers={"X-Supported-Versions": ", ".join(self.supported_versions.keys())}
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"API version '{requested_version}' not supported",
                    headers={"X-Supported-Versions": ", ".join(self.supported_versions.keys())}
                )
                
        # Check if version is sunset
        if version_info.status == VersionStatus.SUNSET:
            replacement = version_info.replacement_version or self.default_version
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail=f"API version '{requested_version}' is no longer available. Use '{replacement}' instead.",
                headers={
                    "X-Replacement-Version": replacement,
                    "X-Sunset-Date": version_info.sunset_date.isoformat() if version_info.sunset_date else ""
                }
            )
            
        return version_info
        
    def _find_closest_version(self, requested_version: str) -> Optional[str]:
        """Find closest supported version."""
        # Simple logic - find highest supported version
        supported = [v for v, info in self.supported_versions.items() 
                    if info.status in [VersionStatus.CURRENT, VersionStatus.SUPPORTED]]
        
        if not supported:
            return None
            
        # Sort versions (assumes v1, v2, v3... format)
        try:
            sorted_versions = sorted(supported, key=lambda x: int(x[1:]) if x[1:].isdigit() else 0, reverse=True)
            return sorted_versions[0]
        except (ValueError, IndexError):
            return supported[0]
            
    def _generate_warning_headers(self, version_info: APIVersionInfo) -> Optional[Dict[str, str]]:
        """Generate warning headers for deprecated/sunset versions."""
        headers = {}
        
        if version_info.status == VersionStatus.DEPRECATED:
            warning_msg = f"API version '{version_info.version}' is deprecated"
            
            if version_info.replacement_version:
                warning_msg += f". Use '{version_info.replacement_version}' instead"
                headers["X-Replacement-Version"] = version_info.replacement_version
                
            if version_info.sunset_date:
                warning_msg += f". Will be sunset on {version_info.sunset_date.date()}"
                headers["X-Sunset-Date"] = version_info.sunset_date.isoformat()
                
            headers["Warning"] = f"299 - \"{warning_msg}\""
            headers["X-API-Deprecation-Warning"] = "true"
            
        # Always include supported versions
        headers["X-Supported-Versions"] = ", ".join(
            v for v, info in self.supported_versions.items() 
            if info.status in [VersionStatus.CURRENT, VersionStatus.SUPPORTED, VersionStatus.DEPRECATED]
        )
        
        return headers if headers else None
        
    def _is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from versioning."""
        return any(path.startswith(exempt_path) for exempt_path in self.exempt_paths)
        
    def add_version_route(self, version: str, version_info: APIVersionInfo):
        """Add or update version information."""
        self.supported_versions[version] = version_info
        logger.info(f"Added API version: {version} ({version_info.status})")
        
    def deprecate_version(self, version: str, replacement: str, sunset_date: Optional[datetime] = None):
        """Mark a version as deprecated."""
        if version in self.supported_versions:
            self.supported_versions[version].status = VersionStatus.DEPRECATED
            self.supported_versions[version].replacement_version = replacement
            if sunset_date:
                self.supported_versions[version].sunset_date = sunset_date
            logger.info(f"Deprecated API version: {version} -> {replacement}")
            
    def sunset_version(self, version: str):
        """Mark a version as sunset (no longer available)."""
        if version in self.supported_versions:
            self.supported_versions[version].status = VersionStatus.SUNSET
            logger.info(f"Sunset API version: {version}")


async def api_versioning_middleware(request: Request, call_next, versioning: APIVersioningMiddleware):
    """FastAPI middleware function for API versioning."""
    try:
        # Process API version
        version, warning_headers = await versioning.process_request(request)
        
        # Process request
        response = await call_next(request)
        
        # Add version headers to response
        response.headers["X-API-Version"] = version
        
        if warning_headers:
            for key, value in warning_headers.items():
                response.headers[key] = value
                
        return response
        
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.detail},
            headers=getattr(e, "headers", {})
        )
    except Exception as e:
        logger.error(f"API versioning middleware error: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": "API versioning validation failed"}
        )


def add_api_versioning_middleware(app: FastAPI, 
                                 versioning: Optional[APIVersioningMiddleware] = None):
    """Add API versioning middleware to FastAPI app.
    
    Args:
        app: FastAPI application
        versioning: Optional custom versioning instance
    """
    if not versioning:
        versioning = APIVersioningMiddleware()
        
    @app.middleware("http") 
    async def versioning_middleware(request: Request, call_next):
        return await api_versioning_middleware(request, call_next, versioning)
        
    logger.info("API versioning middleware added")