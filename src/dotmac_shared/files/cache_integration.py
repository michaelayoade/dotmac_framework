"""
File Service Cache Integration

Integrates file generation and template processing with Developer A's cache service
for high-performance template caching, rendered content caching, and metadata storage.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from ..cache import CacheManagerProtocol, create_cache_service
from .core.templates import TemplateInfo

logger = logging.getLogger(__name__)


class CacheServiceTemplateStore:
    """
    Template caching implementation using Developer A's cache service.

    Provides distributed template caching with tenant isolation,
    version control, and performance optimization.
    """

    def __init__(
        self,
        cache_manager: CacheManagerProtocol,
        template_namespace: str = "file_templates",
        content_namespace: str = "rendered_content",
        metadata_namespace: str = "template_metadata",
    ):
        """
        Initialize cache service template store.

        Args:
            cache_manager: Cache manager from Developer A's service
            template_namespace: Namespace for template data
            content_namespace: Namespace for rendered content
            metadata_namespace: Namespace for template metadata
        """
        self.cache = cache_manager
        self.template_namespace = template_namespace
        self.content_namespace = content_namespace
        self.metadata_namespace = metadata_namespace

        logger.info("Cache Service Template Store initialized")

    def _template_key(self, template_name: str, version: str = "latest") -> str:
        """Generate cache key for template."""
        return f"{self.template_namespace}:{template_name}:{version}"

    def _content_key(self, template_name: str, context_hash: str) -> str:
        """Generate cache key for rendered content."""
        return f"{self.content_namespace}:{template_name}:{context_hash}"

    def _metadata_key(self, template_name: str) -> str:
        """Generate cache key for template metadata."""
        return f"{self.metadata_namespace}:{template_name}"

    def _compute_context_hash(self, context: Dict[str, Any]) -> str:
        """Compute hash of template context for caching."""
        # Sort context for consistent hashing
        sorted_context = json.dumps(context, sort_keys=True, default=str)
        return hashlib.sha256(sorted_context.encode()).hexdigest()[:16]

    async def store_template(
        self,
        template_name: str,
        template_content: str,
        template_info: TemplateInfo,
        tenant_id: Optional[str] = None,
    ) -> bool:
        """Store template in cache."""
        try:
            template_key = self._template_key(template_name, template_info.version)
            metadata_key = self._metadata_key(template_name)

            # Convert tenant_id to UUID for cache service
            tenant_uuid = UUID(tenant_id) if tenant_id else None

            # Calculate TTL based on template size and usage patterns
            base_ttl = 3600  # 1 hour base
            size_factor = min(
                template_info.size / 1024, 10
            )  # Up to 10x for large templates
            ttl_seconds = int(base_ttl * (1 + size_factor))

            # Store template content
            template_data = {
                "content": template_content,
                "info": template_info.__dict__,
                "cached_at": datetime.now(timezone.utc).isoformat(),
                "cache_version": "1.0",
            }

            success = await self.cache.set(
                template_key, template_data, ttl=ttl_seconds, tenant_id=tenant_uuid
            )

            if success:
                # Store template metadata separately with longer TTL
                metadata = {
                    "name": template_name,
                    "current_version": template_info.version,
                    "size": template_info.size,
                    "modified_at": (
                        template_info.modified_at.isoformat()
                        if hasattr(template_info.modified_at, "isoformat")
                        else str(template_info.modified_at)
                    ),
                    "variables": template_info.variables,
                    "includes": template_info.includes,
                    "extends": template_info.extends,
                    "language": template_info.language,
                    "last_cached": datetime.now(timezone.utc).isoformat(),
                }

                await self.cache.set(
                    metadata_key,
                    metadata,
                    ttl=ttl_seconds * 2,  # Longer TTL for metadata
                    tenant_id=tenant_uuid,
                )

            return success

        except Exception as e:
            logger.error(f"Failed to store template {template_name}: {e}")
            return False

    async def get_template(
        self,
        template_name: str,
        version: str = "latest",
        tenant_id: Optional[str] = None,
    ) -> Optional[Tuple[str, TemplateInfo]]:
        """Retrieve template from cache."""
        try:
            template_key = self._template_key(template_name, version)
            tenant_uuid = UUID(tenant_id) if tenant_id else None

            template_data = await self.cache.get(template_key, tenant_id=tenant_uuid)

            if not template_data:
                return None

            # Extract template content and info
            content = template_data["content"]
            info_dict = template_data["info"]

            # Reconstruct TemplateInfo object
            template_info = TemplateInfo(
                name=info_dict["name"],
                path=info_dict.get("path"),
                size=info_dict["size"],
                modified_at=(
                    datetime.fromisoformat(info_dict["modified_at"])
                    if isinstance(info_dict["modified_at"], str)
                    else info_dict["modified_at"]
                ),
                version=info_dict["version"],
                variables=info_dict["variables"],
                includes=info_dict["includes"],
                extends=info_dict.get("extends"),
                language=info_dict.get("language", "en"),
                tenant_id=info_dict.get("tenant_id"),
                custom_metadata=info_dict.get("custom_metadata", {}),
            )

            return content, template_info

        except Exception as e:
            logger.error(f"Failed to get template {template_name}: {e}")
            return None

    async def store_rendered_content(
        self,
        template_name: str,
        context: Dict[str, Any],
        rendered_content: str,
        content_type: str = "html",
        tenant_id: Optional[str] = None,
    ) -> bool:
        """Store rendered template content."""
        try:
            context_hash = self._compute_context_hash(context)
            content_key = self._content_key(template_name, context_hash)
            tenant_uuid = UUID(tenant_id) if tenant_id else None

            # Store rendered content with shorter TTL (content changes more frequently)
            content_data = {
                "content": rendered_content,
                "template_name": template_name,
                "context_hash": context_hash,
                "content_type": content_type,
                "size": len(rendered_content),
                "rendered_at": datetime.now(timezone.utc).isoformat(),
                "tenant_id": tenant_id,
            }

            # Shorter TTL for rendered content (30 minutes)
            ttl_seconds = 1800

            success = await self.cache.set(
                content_key, content_data, ttl=ttl_seconds, tenant_id=tenant_uuid
            )

            return success

        except Exception as e:
            logger.error(f"Failed to store rendered content for {template_name}: {e}")
            return False

    async def get_rendered_content(
        self,
        template_name: str,
        context: Dict[str, Any],
        tenant_id: Optional[str] = None,
    ) -> Optional[str]:
        """Retrieve rendered template content from cache."""
        try:
            context_hash = self._compute_context_hash(context)
            content_key = self._content_key(template_name, context_hash)
            tenant_uuid = UUID(tenant_id) if tenant_id else None

            content_data = await self.cache.get(content_key, tenant_id=tenant_uuid)

            if not content_data:
                return None

            return content_data["content"]

        except Exception as e:
            logger.error(f"Failed to get rendered content for {template_name}: {e}")
            return None

    async def invalidate_template(
        self, template_name: str, tenant_id: Optional[str] = None
    ) -> int:
        """Invalidate all cached data for a template."""
        try:
            tenant_uuid = UUID(tenant_id) if tenant_id else None

            # Clear template cache entries
            template_pattern = f"{self.template_namespace}:{template_name}:*"
            content_pattern = f"{self.content_namespace}:{template_name}:*"
            metadata_pattern = f"{self.metadata_namespace}:{template_name}"

            deleted = 0
            deleted += await self.cache.clear(template_pattern, tenant_id=tenant_uuid)
            deleted += await self.cache.clear(content_pattern, tenant_id=tenant_uuid)
            deleted += await self.cache.clear(metadata_pattern, tenant_id=tenant_uuid)

            logger.info(
                f"Invalidated {deleted} cache entries for template {template_name}"
            )
            return deleted

        except Exception as e:
            logger.error(f"Failed to invalidate template {template_name}: {e}")
            return 0

    async def get_template_metadata(
        self, template_name: str, tenant_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get template metadata from cache."""
        try:
            metadata_key = self._metadata_key(template_name)
            tenant_uuid = UUID(tenant_id) if tenant_id else None

            metadata = await self.cache.get(metadata_key, tenant_id=tenant_uuid)
            return metadata

        except Exception as e:
            logger.error(f"Failed to get template metadata for {template_name}: {e}")
            return None

    async def health_check(self) -> bool:
        """Check if cache service is healthy."""
        try:
            return await self.cache.ping()
        except Exception as e:
            logger.error(f"Cache service health check failed: {e}")
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring."""
        try:
            cache_stats = await self.cache.get_stats()
            return {
                "cache_stats": cache_stats,
                "template_store_healthy": await self.health_check(),
                "namespaces": {
                    "templates": self.template_namespace,
                    "content": self.content_namespace,
                    "metadata": self.metadata_namespace,
                },
            }
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"error": str(e)}


class CacheServiceFileStorage:
    """
    File metadata and reference caching using Developer A's cache service.

    Provides caching for file metadata, storage locations, and access patterns
    to optimize file operations and reduce storage backend calls.
    """

    def __init__(
        self,
        cache_manager: CacheManagerProtocol,
        file_namespace: str = "file_metadata",
        access_namespace: str = "file_access",
    ):
        """Initialize cache service file storage."""
        self.cache = cache_manager
        self.file_namespace = file_namespace
        self.access_namespace = access_namespace

        logger.info("Cache Service File Storage initialized")

    def _file_key(self, file_id: str) -> str:
        """Generate cache key for file metadata."""
        return f"{self.file_namespace}:{file_id}"

    def _access_key(self, file_id: str) -> str:
        """Generate cache key for file access tracking."""
        return f"{self.access_namespace}:{file_id}"

    async def store_file_metadata(
        self,
        file_id: str,
        metadata: Dict[str, Any],
        tenant_id: Optional[str] = None,
        ttl: int = 7200,  # 2 hours
    ) -> bool:
        """Store file metadata in cache."""
        try:
            file_key = self._file_key(file_id)
            tenant_uuid = UUID(tenant_id) if tenant_id else None

            # Add caching metadata
            cached_metadata = {
                **metadata,
                "cached_at": datetime.now(timezone.utc).isoformat(),
                "cache_ttl": ttl,
            }

            success = await self.cache.set(
                file_key, cached_metadata, ttl=ttl, tenant_id=tenant_uuid
            )

            return success

        except Exception as e:
            logger.error(f"Failed to store file metadata for {file_id}: {e}")
            return False

    async def get_file_metadata(
        self, file_id: str, tenant_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Retrieve file metadata from cache."""
        try:
            file_key = self._file_key(file_id)
            tenant_uuid = UUID(tenant_id) if tenant_id else None

            metadata = await self.cache.get(file_key, tenant_id=tenant_uuid)
            return metadata

        except Exception as e:
            logger.error(f"Failed to get file metadata for {file_id}: {e}")
            return None

    async def track_file_access(
        self,
        file_id: str,
        access_type: str,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> bool:
        """Track file access patterns."""
        try:
            access_key = self._access_key(file_id)
            tenant_uuid = UUID(tenant_id) if tenant_id else None

            # Get current access count
            current_count = await self.cache.increment(
                access_key, amount=1, tenant_id=tenant_uuid
            )

            # Store access metadata separately
            if current_count == 1:  # First access
                access_metadata = {
                    "file_id": file_id,
                    "first_access": datetime.now(timezone.utc).isoformat(),
                    "access_types": [access_type],
                    "users": [user_id] if user_id else [],
                }

                await self.cache.set(
                    f"{access_key}:meta",
                    access_metadata,
                    ttl=86400,  # 24 hours
                    tenant_id=tenant_uuid,
                )

            return True

        except Exception as e:
            logger.error(f"Failed to track file access for {file_id}: {e}")
            return False


class FileServiceCacheIntegrationFactory:
    """Factory for creating file service cache integration components."""

    @staticmethod
    async def create_template_store(
        cache_service_config: Optional[Dict[str, Any]] = None
    ) -> CacheServiceTemplateStore:
        """Create template store with cache integration."""
        try:
            # Create cache service
            cache_service = create_cache_service()
            await cache_service.initialize()

            # Get cache manager
            cache_manager = cache_service.cache_manager

            # Create template store
            template_store = CacheServiceTemplateStore(cache_manager)

            logger.info("Template store with cache integration created")
            return template_store

        except Exception as e:
            logger.error(f"Failed to create template store: {e}")
            raise

    @staticmethod
    async def create_file_storage(
        cache_service_config: Optional[Dict[str, Any]] = None
    ) -> CacheServiceFileStorage:
        """Create file storage with cache integration."""
        try:
            # Create cache service
            cache_service = create_cache_service()
            await cache_service.initialize()

            # Get cache manager
            cache_manager = cache_service.cache_manager

            # Create file storage
            file_storage = CacheServiceFileStorage(cache_manager)

            logger.info("File storage with cache integration created")
            return file_storage

        except Exception as e:
            logger.error(f"Failed to create file storage: {e}")
            raise

    @staticmethod
    async def create_integrated_components(
        cache_service_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create all file service cache-integrated components."""
        try:
            # Create cache service
            cache_service = create_cache_service()
            await cache_service.initialize()

            # Get cache manager
            cache_manager = cache_service.cache_manager

            # Create all components
            components = {
                "template_store": CacheServiceTemplateStore(cache_manager),
                "file_storage": CacheServiceFileStorage(cache_manager),
                "cache_service": cache_service,
                "cache_manager": cache_manager,
            }

            logger.info("All file service cache integration components created")
            return components

        except Exception as e:
            logger.error(f"Failed to create integrated components: {e}")
            raise
