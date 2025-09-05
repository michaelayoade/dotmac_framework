"""
Template engine for dynamic content generation.

This module provides a Jinja2-based template system with advanced features like
template inheritance, custom filters, multi-language support, and security features.
"""

import hashlib
import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union

import jinja2
from jinja2 import DictLoader, Environment, FileSystemLoader, select_autoescape
from jinja2.exceptions import TemplateError, TemplateNotFound, TemplateSyntaxError
from jinja2.sandbox import SandboxedEnvironment

logger = logging.getLogger(__name__)


@dataclass
class TemplateInfo:
    """Information about a template."""

    name: str
    path: Optional[str]
    size: int
    modified_at: datetime
    version: str
    variables: list[str]
    includes: list[str]
    extends: Optional[str]
    language: str = "en"
    tenant_id: Optional[str] = None
    custom_metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.custom_metadata is None:
            self.custom_metadata = {}


class TemplateCache:
    """
    Template cache with support for both in-memory and distributed caching.

    Can use either simple in-memory caching or integrate with Developer A's
    cache service for distributed, high-performance template caching.
    """

    def __init__(
        self,
        max_size: int = 100,
        ttl: int = 3600,
        cache_service_store=None,
        tenant_id: Optional[str] = None,
    ):
        """
        Initialize template cache.

        Args:
            max_size: Maximum in-memory cache size
            ttl: Time to live for cache entries
            cache_service_store: Optional CacheServiceTemplateStore for distributed caching
            tenant_id: Tenant ID for multi-tenant caching
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache_service_store = cache_service_store
        self.tenant_id = tenant_id
        self._cache: dict[str, dict[str, Any]] = {}
        self._use_distributed_cache = cache_service_store is not None

    async def get(self, key: str) -> Optional[Any]:
        """Get item from cache (distributed or local)."""
        if self._use_distributed_cache:
            try:
                # Try distributed cache first
                return await self._get_from_distributed_cache(key)
            except Exception as e:
                logger.warning(
                    f"Distributed cache get failed, falling back to local: {e}"
                )

        # Fallback to local cache
        return self._get_from_local_cache(key)

    async def set(self, key: str, value: Any):
        """Set item in cache (distributed and local)."""
        if self._use_distributed_cache:
            try:
                await self._set_in_distributed_cache(key, value)
            except Exception as e:
                logger.warning(f"Distributed cache set failed: {e}")

        # Always update local cache for fast access
        self._set_in_local_cache(key, value)

    async def clear(self):
        """Clear all cache entries."""
        if self._use_distributed_cache:
            try:
                await self.cache_service_store.invalidate_template("*", self.tenant_id)
            except Exception as e:
                logger.warning(f"Distributed cache clear failed: {e}")

        self._cache.clear()

    async def invalidate(self, pattern: Optional[str] = None):
        """Invalidate cache entries matching pattern."""
        if pattern is None:
            await self.clear()
            return

        if self._use_distributed_cache:
            try:
                await self.cache_service_store.invalidate_template(
                    pattern, self.tenant_id
                )
            except Exception as e:
                logger.warning(f"Distributed cache invalidate failed: {e}")

        # Local cache invalidation
        keys_to_remove = []
        for key in self._cache.keys():
            if pattern in key:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._cache[key]

    def _get_from_local_cache(self, key: str) -> Optional[Any]:
        """Get item from local cache."""
        if key in self._cache:
            item = self._cache[key]
            if datetime.now().timestamp() - item["timestamp"] < self.ttl:
                return item["value"]
            else:
                del self._cache[key]
        return None

    def _set_in_local_cache(self, key: str, value: Any):
        """Set item in local cache."""
        # Simple LRU eviction
        if len(self._cache) >= self.max_size:
            oldest_key = min(
                self._cache.keys(), key=lambda k: self._cache[k]["timestamp"]
            )
            del self._cache[oldest_key]

        self._cache[key] = {"value": value, "timestamp": datetime.now().timestamp()}

    async def _get_from_distributed_cache(self, key: str) -> Optional[Any]:
        """Get item from distributed cache."""
        if not self.cache_service_store:
            return None

        # For templates, key format is template_name
        result = await self.cache_service_store.get_template(
            key, tenant_id=self.tenant_id
        )
        if result:
            content, info = result
            return {"content": content, "info": info}

        return None

    async def _set_in_distributed_cache(self, key: str, value: Any):
        """Set item in distributed cache."""
        if not self.cache_service_store or not isinstance(value, dict):
            return

        if "content" in value and "info" in value:
            await self.cache_service_store.store_template(
                key, value["content"], value["info"], self.tenant_id
            )


class TemplateEngine:
    """Advanced Jinja2-based template engine with multi-tenant support."""

    def __init__(
        self,
        template_dirs: Optional[Union[str, list[str]]] = None,
        config: Optional[dict[str, Any]] = None,
        enable_cache: bool = True,
        sandboxed: bool = True,
    ):
        """
        Initialize template engine.

        Args:
            template_dirs: Template directory paths
            config: Configuration dictionary
            enable_cache: Whether to enable template caching
            sandboxed: Whether to use sandboxed environment for security
        """
        self.config = config or {}
        self.enable_cache = enable_cache
        self.sandboxed = sandboxed

        # Setup template directories
        if isinstance(template_dirs, str):
            template_dirs = [template_dirs]
        self.template_dirs = template_dirs or [
            os.path.join(os.path.dirname(__file__), "..", "templates")
        ]

        # Initialize cache
        if self.enable_cache:
            cache_config = self.config.get("cache", {})
            self.cache = TemplateCache(
                max_size=cache_config.get("max_size", 100),
                ttl=cache_config.get("ttl", 3600),
            )
        else:
            self.cache = None

        # Initialize Jinja2 environment
        self._setup_environment()

        # Initialize custom filters and functions
        self._setup_custom_filters()
        self._setup_custom_functions()

        logger.info(
            f"Template engine initialized with {len(self.template_dirs)} template directories"
        )

    def _setup_environment(self):
        """Setup Jinja2 environment."""
        # Create loaders for all template directories
        loaders = []
        for template_dir in self.template_dirs:
            if os.path.exists(template_dir):
                loaders.append(FileSystemLoader(template_dir))

        # Combine loaders
        if loaders:
            if len(loaders) == 1:
                loader = loaders[0]
            else:
                loader = jinja2.ChoiceLoader(loaders)
        else:
            # Fallback to empty dict loader
            loader = DictLoader({})

        # Create environment
        if self.sandboxed:
            self.env = SandboxedEnvironment(
                loader=loader,
                autoescape=select_autoescape(["html", "xml"]),
                trim_blocks=True,
                lstrip_blocks=True,
            )
        else:
            self.env = Environment(
                loader=loader,
                autoescape=select_autoescape(["html", "xml"]),
                trim_blocks=True,
                lstrip_blocks=True,
            )

        # Configure caching
        if self.enable_cache:
            self.env.cache_size = self.config.get("cache", {}).get(
                "template_cache_size", 400
            )

    def _setup_custom_filters(self):
        """Setup custom Jinja2 filters."""

        def currency_filter(value, currency="USD", locale="en_US"):
            """Format number as currency."""
            try:
                if isinstance(value, (int, float)):
                    return f"{currency} {value:,.2f}"
                return str(value)
            except Exception:
                return str(value)

        def datetime_filter(value, format="%Y-%m-%d %H:%M:%S"):
            """Format datetime value."""
            try:
                if isinstance(value, str):
                    # Try to parse ISO format
                    value = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if isinstance(value, datetime):
                    return value.strftime(format)
                return str(value)
            except Exception:
                return str(value)

        def truncate_filter(value, length=50, suffix="..."):
            """Truncate text to specified length."""
            try:
                text = str(value)
                if len(text) <= length:
                    return text
                return text[: length - len(suffix)] + suffix
            except Exception:
                return str(value)

        def slug_filter(value):
            """Convert text to URL-friendly slug."""
            import re

            try:
                text = str(value).lower()
                text = re.sub(r"[^\w\s-]", "", text)
                text = re.sub(r"[-\s]+", "-", text)
                return text.strip("-")
            except Exception:
                return str(value)

        def nl2br_filter(value):
            """Convert newlines to HTML breaks."""
            try:
                return str(value).replace("\n", "<br>")
            except Exception:
                return str(value)

        def file_size_filter(value):
            """Format file size in human readable format."""
            try:
                size = int(value)
                for unit in ["B", "KB", "MB", "GB", "TB"]:
                    if size < 1024.0:
                        return f"{size:.1f} {unit}"
                    size /= 1024.0
                return f"{size:.1f} PB"
            except Exception:
                return str(value)

        # Register filters
        self.env.filters["currency"] = currency_filter
        self.env.filters["datetime"] = datetime_filter
        self.env.filters["truncate"] = truncate_filter
        self.env.filters["slug"] = slug_filter
        self.env.filters["nl2br"] = nl2br_filter
        self.env.filters["file_size"] = file_size_filter

    def _setup_custom_functions(self):
        """Setup custom global functions."""

        def now(format=None):
            """Get current datetime."""
            current_time = datetime.now(timezone.utc)
            if format:
                return current_time.strftime(format)
            return current_time.isoformat()

        def version():
            """Get template engine version."""
            return "1.0.0"

        def range_func(*args):
            """Python range function for templates."""
            return range(*args)

        def enumerate_func(iterable, start=0):
            """Python enumerate function for templates."""
            return enumerate(iterable, start)

        def zip_func(*iterables):
            """Python zip function for templates."""
            return zip(*iterables)

        # Register global functions
        self.env.globals["now"] = now
        self.env.globals["version"] = version
        self.env.globals["range"] = range_func
        self.env.globals["enumerate"] = enumerate_func
        self.env.globals["zip"] = zip_func

    def render_template(
        self,
        template_name: str,
        context: dict[str, Any],
        tenant_id: Optional[str] = None,
        language: str = "en",
    ) -> str:
        """
        Render template with context data.

        Args:
            template_name: Name of the template file
            context: Template context variables
            tenant_id: Tenant ID for multi-tenant templates
            language: Language code for internationalization

        Returns:
            Rendered template content

        Raises:
            TemplateNotFound: If template is not found
            TemplateSyntaxError: If template has syntax errors
            TemplateError: For other template-related errors
        """
        try:
            # Check cache first
            if self.cache:
                cache_key = self._generate_cache_key(
                    template_name, context, tenant_id, language
                )
                cached_result = self.cache.get(cache_key)
                if cached_result:
                    logger.debug(f"Template cache hit for: {template_name}")
                    return cached_result

            # Find template (with tenant and language support)
            template = self._find_template(template_name, tenant_id, language)

            # Enhance context
            enhanced_context = self._enhance_context(context, tenant_id, language)

            # Render template
            result = template.render(enhanced_context)

            # Cache result
            if self.cache:
                self.cache.set(cache_key, result)

            logger.debug(f"Rendered template: {template_name}")
            return result

        except TemplateNotFound:
            logger.error(f"Template not found: {template_name}")
            raise
        except TemplateSyntaxError as e:
            logger.error(f"Template syntax error in {template_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error rendering template {template_name}: {e}")
            raise TemplateError(
                f"Failed to render template {template_name}: {e}"
            ) from e

    def render_string(
        self,
        template_string: str,
        context: dict[str, Any],
        tenant_id: Optional[str] = None,
        language: str = "en",
    ) -> str:
        """
        Render template from string.

        Args:
            template_string: Template content as string
            context: Template context variables
            tenant_id: Tenant ID for context
            language: Language code

        Returns:
            Rendered template content
        """
        try:
            template = self.env.from_string(template_string)
            enhanced_context = self._enhance_context(context, tenant_id, language)
            return template.render(enhanced_context)
        except Exception as e:
            logger.error(f"Error rendering template string: {e}")
            raise TemplateError(f"Failed to render template string: {e}") from e

    def validate_template(self, template_content: str) -> dict[str, Any]:
        """
        Validate template syntax and extract information.

        Args:
            template_content: Template content to validate

        Returns:
            Dictionary with validation results and template info
        """
        try:
            # Parse template
            ast = self.env.parse(template_content)

            # Extract variables
            variables = list(jinja2.meta.find_undeclared_variables(ast))

            # Extract includes and extends
            referenced_templates = list(jinja2.meta.find_referenced_templates(ast))

            return {
                "valid": True,
                "variables": variables,
                "referenced_templates": referenced_templates,
                "error": None,
            }

        except TemplateSyntaxError as e:
            return {
                "valid": False,
                "variables": [],
                "referenced_templates": [],
                "error": str(e),
            }
        except Exception as e:
            return {
                "valid": False,
                "variables": [],
                "referenced_templates": [],
                "error": f"Validation error: {e}",
            }

    def get_template_info(
        self, template_name: str, tenant_id: Optional[str] = None
    ) -> TemplateInfo:
        """
        Get information about a template.

        Args:
            template_name: Name of the template
            tenant_id: Tenant ID

        Returns:
            TemplateInfo object with template details
        """
        try:
            self._find_template(template_name, tenant_id)
            template_path = None

            # Try to find the actual file path
            for template_dir in self.template_dirs:
                potential_path = Path(template_dir) / template_name
                if potential_path.exists():
                    template_path = str(potential_path)
                    break

            # Get template source
            source, _ = (
                self.env.get_or_select_template(template_name)
                .new_context()
                .environment.loader.get_source(self.env, template_name)
            )

            # Validate and extract info
            validation_result = self.validate_template(source)

            # Get file stats if path exists
            if template_path and Path(template_path).exists():
                stat = Path(template_path).stat()
                size = stat.st_size
                modified_at = datetime.fromtimestamp(stat.st_mtime, timezone.utc)
            else:
                size = len(source)
                modified_at = datetime.now(timezone.utc)

            return TemplateInfo(
                name=template_name,
                path=template_path,
                size=size,
                modified_at=modified_at,
                version="1.0.0",
                variables=validation_result["variables"],
                includes=validation_result["referenced_templates"],
                extends=None,  # Could be extracted from AST if needed
                tenant_id=tenant_id,
            )

        except Exception as e:
            logger.error(f"Error getting template info for {template_name}: {e}")
            raise TemplateError(f"Failed to get template info: {e}") from e

    def list_templates(
        self, pattern: str = "*", tenant_id: Optional[str] = None
    ) -> list[TemplateInfo]:
        """
        List available templates matching pattern.

        Args:
            pattern: Glob pattern to match template names
            tenant_id: Tenant ID to filter templates

        Returns:
            List of TemplateInfo objects
        """
        import fnmatch

        templates = []

        for template_dir in self.template_dirs:
            if not os.path.exists(template_dir):
                continue

            for root, _dirs, files in os.walk(template_dir):
                for file in files:
                    if file.endswith((".html", ".txt", ".xml", ".json", ".md")):
                        # Get relative path from template directory
                        rel_path = os.path.relpath(
                            os.path.join(root, file), template_dir
                        )

                        # Convert to forward slashes for consistency
                        template_name = rel_path.replace(os.path.sep, "/")

                        # Check pattern match
                        if fnmatch.fnmatch(template_name, pattern):
                            try:
                                info = self.get_template_info(template_name, tenant_id)
                                templates.append(info)
                            except Exception as e:
                                logger.warning(
                                    f"Could not get info for template {template_name}: {e}"
                                )

        return sorted(templates, key=lambda t: t.name)

    def add_template_dir(self, directory: str):
        """Add a new template directory."""
        if directory not in self.template_dirs:
            self.template_dirs.append(directory)
            # Reinitialize environment with new directories
            self._setup_environment()
            logger.info(f"Added template directory: {directory}")

    def remove_template_dir(self, directory: str):
        """Remove a template directory."""
        if directory in self.template_dirs:
            self.template_dirs.remove(directory)
            # Reinitialize environment
            self._setup_environment()
            logger.info(f"Removed template directory: {directory}")

    def clear_cache(self):
        """Clear template cache."""
        if self.cache:
            self.cache.clear()
            logger.info("Template cache cleared")

    def invalidate_cache(self, pattern: Optional[str] = None):
        """Invalidate cache entries."""
        if self.cache:
            self.cache.invalidate(pattern)
            logger.info(f"Cache invalidated for pattern: {pattern}")

    def add_filter(self, name: str, filter_func: Callable):
        """Add custom filter to template engine."""
        self.env.filters[name] = filter_func
        logger.info(f"Added custom filter: {name}")

    def add_global(self, name: str, global_func: Callable):
        """Add global function to template engine."""
        self.env.globals[name] = global_func
        logger.info(f"Added global function: {name}")

    def _find_template(
        self, template_name: str, tenant_id: Optional[str] = None, language: str = "en"
    ):
        """Find template with tenant and language support."""
        # Template resolution order:
        # 1. tenant_id/language/template_name
        # 2. tenant_id/template_name
        # 3. language/template_name
        # 4. template_name

        template_candidates = []

        if tenant_id and language != "en":
            template_candidates.append(f"{tenant_id}/{language}/{template_name}")
        if tenant_id:
            template_candidates.append(f"{tenant_id}/{template_name}")
        if language != "en":
            template_candidates.append(f"{language}/{template_name}")
        template_candidates.append(template_name)

        for candidate in template_candidates:
            try:
                return self.env.get_template(candidate)
            except TemplateNotFound:
                continue

        # If we get here, none of the candidates were found
        raise TemplateNotFound(template_name)

    def _enhance_context(
        self,
        context: dict[str, Any],
        tenant_id: Optional[str] = None,
        language: str = "en",
    ) -> dict[str, Any]:
        """Enhance template context with additional variables."""
        enhanced_context = context.copy()

        # Add system variables
        enhanced_context.update(
            {
                "_tenant_id": tenant_id,
                "_language": language,
                "_generated_at": datetime.now(timezone.utc).isoformat(),
                "_engine_version": "1.0.0",
            }
        )

        # Add configuration variables
        if self.config.get("global_context"):
            enhanced_context.update(self.config["global_context"])

        return enhanced_context

    def _generate_cache_key(
        self,
        template_name: str,
        context: dict[str, Any],
        tenant_id: Optional[str] = None,
        language: str = "en",
    ) -> str:
        """Generate cache key for template and context."""
        # Create a hash of the context for cache key
        context_str = str(sorted(context.items()))
        context_hash = hashlib.md5(context_str.encode()).hexdigest()[:8]

        cache_key_parts = [template_name, context_hash]
        if tenant_id:
            cache_key_parts.append(tenant_id)
        if language != "en":
            cache_key_parts.append(language)

        return ":".join(cache_key_parts)
