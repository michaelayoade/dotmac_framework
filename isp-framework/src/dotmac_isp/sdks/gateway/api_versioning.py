"""
API Versioning SDK - Semantic versioning, backward compatibility, deprecation.
"""

from datetime import datetime
from ..core.datetime_utils import (
    utc_now_iso,
    utc_now,
    expires_in_days,
    expires_in_hours,
    time_ago_minutes,
    time_ago_hours,
    is_expired_iso,
)
from typing import Any, Dict, List
from uuid import uuid4


class APIVersioningService:
    """In-memory service for API versioning operations."""

    def __init__(self):
        self._api_versions: Dict[str, Dict[str, Any]] = {}
        self._version_mappings: Dict[str, Dict[str, Any]] = {}
        self._deprecation_schedules: Dict[str, Dict[str, Any]] = {}

    async def create_api_version(self, **kwargs) -> Dict[str, Any]:
        """Create API version."""
        version_id = kwargs.get("version_id") or str(uuid4())

        version = {
            "version_id": version_id,
            "api_name": kwargs["api_name"],
            "version": kwargs["version"],  # e.g., "v1", "v2", "1.0.0"
            "gateway_id": kwargs["gateway_id"],
            "base_path": kwargs.get("base_path", f"/{kwargs['version']}"),
            "status": kwargs.get("status", "active"),  # active, deprecated, retired
            "is_default": kwargs.get("is_default", False),
            "deprecation_date": kwargs.get("deprecation_date"),
            "retirement_date": kwargs.get("retirement_date"),
            "migration_guide_url": kwargs.get("migration_guide_url"),
            "changelog_url": kwargs.get("changelog_url"),
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
            "metadata": kwargs.get("metadata", {}),
        }

        self._api_versions[version_id] = version
        return version

    async def create_versioned_route(self, **kwargs) -> Dict[str, Any]:
        """Create versioned route."""
        mapping_id = kwargs.get("mapping_id") or str(uuid4())

        mapping = {
            "mapping_id": mapping_id,
            "api_name": kwargs["api_name"],
            "version": kwargs["version"],
            "path": kwargs["path"],
            "upstream_service": kwargs["upstream_service"],
            "upstream_path": kwargs.get("upstream_path", kwargs["path"]),
            "methods": kwargs.get("methods", ["GET"]),
            "versioning_strategy": kwargs.get(
                "versioning_strategy", "path"
            ),  # path, header, content_negotiation
            "version_header": kwargs.get("version_header", "API-Version"),
            "media_type": kwargs.get("media_type"),
            "status": kwargs.get("status", "active"),
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
        }

        self._version_mappings[mapping_id] = mapping
        return mapping

    async def configure_header_versioning(self, **kwargs) -> Dict[str, Any]:
        """Configure header-based versioning."""
        config = {
            "api_name": kwargs["api_name"],
            "version_header": kwargs.get("version_header", "API-Version"),
            "default_version": kwargs["default_version"],
            "supported_versions": kwargs["supported_versions"],
            "strict_versioning": kwargs.get("strict_versioning", True),
            "created_at": utc_now_iso(),
        }

        return config

    async def configure_content_negotiation_versioning(
        self, **kwargs
    ) -> Dict[str, Any]:
        """Configure content negotiation versioning."""
        config = {
            "api_name": kwargs["api_name"],
            "media_types": kwargs[
                "media_types"
            ],  # {"application/vnd.api.v1+json": "v1"}
            "default_media_type": kwargs.get("default_media_type"),
            "created_at": utc_now_iso(),
        }

        return config


class APIVersioningSDK:
    """SDK for API versioning management."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._service = APIVersioningService()

    async def create_api_version(
        self, api_name: str, version: str, gateway_id: str, **kwargs
    ) -> Dict[str, Any]:
        """Create API version."""
        return await self._service.create_api_version(
            api_name=api_name, version=version, gateway_id=gateway_id, **kwargs
        )

    async def create_versioned_route(
        self, api_name: str, version: str, path: str, upstream_service: str, **kwargs
    ) -> Dict[str, Any]:
        """Create versioned route."""
        return await self._service.create_versioned_route(
            api_name=api_name,
            version=version,
            path=path,
            upstream_service=upstream_service,
            **kwargs,
        )

    async def configure_header_versioning(
        self,
        api_name: str,
        default_version: str,
        supported_versions: List[str],
        **kwargs,
    ) -> Dict[str, Any]:
        """Configure header-based versioning."""
        return await self._service.configure_header_versioning(
            api_name=api_name,
            default_version=default_version,
            supported_versions=supported_versions,
            **kwargs,
        )

    async def configure_content_negotiation_versioning(
        self, api_name: str, media_types: Dict[str, str], **kwargs
    ) -> Dict[str, Any]:
        """Configure content negotiation versioning."""
        return await self._service.configure_content_negotiation_versioning(
            api_name=api_name, media_types=media_types, **kwargs
        )
