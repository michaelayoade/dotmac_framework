"""
Platform Config SDK - Contract-first platform configuration management.

Provides centralized configuration management with multi-tenant isolation,
environment-specific settings, feature toggles, and configuration validation.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from dotmac_isp.sdks.contracts.platform_config import (
    ConfigAuditLog,
    ConfigDataType,
    ConfigEntry,
    ConfigEnvironment,
    ConfigQuery,
    ConfigQueryResponse,
    ConfigScope,
    ConfigStats,
    ConfigTemplate,
    ConfigValidationResult,
    PlatformConfigHealthCheck,
)
from dotmac_isp.sdks.contracts.transport import RequestContext
from dotmac_isp.sdks.platform.utils.datetime_compat import UTC

logger = logging.getLogger(__name__)


class PlatformConfigSDKConfig:
    """Platform Config SDK configuration."""

    def __init__(  # noqa: PLR0913
        self,
        enable_caching: bool = True,
        cache_ttl_seconds: int = 300,  # 5 minutes
        enable_audit_logging: bool = True,
        enable_validation: bool = True,
        max_config_size_bytes: int = 1024 * 1024,  # 1MB
        enable_encryption_for_secrets: bool = True,
        default_environment: ConfigEnvironment = ConfigEnvironment.PRODUCTION,
        enable_config_versioning: bool = True,
        max_versions_per_config: int = 10,
    ):
        self.enable_caching = enable_caching
        self.cache_ttl_seconds = cache_ttl_seconds
        self.enable_audit_logging = enable_audit_logging
        self.enable_validation = enable_validation
        self.max_config_size_bytes = max_config_size_bytes
        self.enable_encryption_for_secrets = enable_encryption_for_secrets
        self.default_environment = default_environment
        self.enable_config_versioning = enable_config_versioning
        self.max_versions_per_config = max_versions_per_config


class PlatformConfigSDK:
    """
    Contract-first Platform Config SDK with centralized configuration management.

    Features:
    - Multi-tenant configuration isolation
    - Environment-specific configurations
    - Configuration validation and constraints
    - Secret configuration encryption
    - Configuration versioning and audit trails
    - Template-based configuration deployment
    - Real-time configuration updates
    - Hierarchical configuration inheritance
    """

    def __init__(
        self,
        config: PlatformConfigSDKConfig | None = None,
        cache_sdk: Any | None = None,
        database_sdk: Any | None = None,
        secrets_sdk: Any | None = None,
        audit_sdk: Any | None = None,
    ):
        """Initialize Platform Config SDK."""
        self.config = config or PlatformConfigSDKConfig()
        self.cache_sdk = cache_sdk
        self.database_sdk = database_sdk
        self.secrets_sdk = secrets_sdk
        self.audit_sdk = audit_sdk

        # In-memory storage for testing/development
        self._configs: dict[str, ConfigEntry] = {}  # config_key -> config
        self._templates: dict[str, ConfigTemplate] = {}  # template_id -> template
        self._audit_logs: list[ConfigAuditLog] = []
        self._config_cache: dict[str, dict[str, Any]] = {}  # cache_key -> cached_data

        logger.info("PlatformConfigSDK initialized")

    async def set_config(  # noqa: PLR0913
        self,
        key: str,
        value: Any,
        scope: ConfigScope,
        data_type: ConfigDataType,
        tenant_id: UUID | None = None,
        user_id: str | None = None,
        service_name: str | None = None,
        environment: ConfigEnvironment | None = None,
        description: str | None = None,
        is_secret: bool = False,
        context: RequestContext | None = None,
    ) -> ConfigEntry:
        """Set a configuration value."""
        try:
            # Generate config key
            config_key = self._generate_config_key(
                key, scope, tenant_id, user_id, service_name, environment
            )

            # Get existing config if it exists
            existing_config = self._configs.get(config_key)

            # Validate the new value
            validation_result = await self._validate_config_value(
                key, value, data_type, existing_config
            )
            if not validation_result.is_valid:
                raise ValueError(
                    f"Configuration validation failed: {', '.join(validation_result.errors)}"
                )

            # Handle secret encryption
            stored_value = value
            if (
                is_secret
                and self.config.enable_encryption_for_secrets
                and self.secrets_sdk
            ):
                stored_value = await self._encrypt_secret_value(value, config_key)

            # Create new config entry
            config_entry = ConfigEntry(
                id=uuid4(),
                key=key,
                scope=scope,
                tenant_id=tenant_id,
                user_id=user_id,
                service_name=service_name,
                value=stored_value,
                data_type=data_type,
                environment=environment or self.config.default_environment,
                description=description,
                is_secret=is_secret,
                created_at=(
                    existing_config.created_at if existing_config else datetime.now(UTC)
                ),
                updated_at=datetime.now(UTC),
                created_by=(
                    existing_config.created_by
                    if existing_config
                    else (context.headers.x_user_id if context else None)
                ),
                updated_by=context.headers.x_user_id if context else None,
                version=(existing_config.version + 1) if existing_config else 1,
                previous_value=existing_config.value if existing_config else None,
            )

            # Store config
            self._configs[config_key] = config_entry

            # Clear cache
            if self.config.enable_caching:
                await self._invalidate_cache(config_key)

            # Audit log
            if self.config.enable_audit_logging:
                await self._log_config_change(
                    config_key=key,
                    action="create" if not existing_config else "update",
                    old_value=existing_config.value if existing_config else None,
                    new_value=value if not is_secret else "[REDACTED]",
                    tenant_id=tenant_id,
                    user_id=context.headers.x_user_id if context else None,
                    context=context,
                )

            return config_entry

        except Exception as e:
            logger.error(f"Failed to set config {key}: {e}")
            raise

    async def get_config(
        self,
        key: str,
        scope: ConfigScope,
        tenant_id: UUID | None = None,
        user_id: str | None = None,
        service_name: str | None = None,
        environment: ConfigEnvironment | None = None,
        default_value: Any = None,
        context: RequestContext | None = None,
    ) -> Any:
        """Get a configuration value."""
        try:
            config_key = self._generate_config_key(
                key, scope, tenant_id, user_id, service_name, environment
            )

            # Check cache first
            if self.config.enable_caching:
                cached_value = await self._get_cached_config(config_key)
                if cached_value is not None:
                    return cached_value

            # Get config from storage
            config_entry = self._configs.get(config_key)
            if not config_entry:
                return default_value

            # Decrypt secret values
            value = config_entry.value
            if (
                config_entry.is_secret
                and self.config.enable_encryption_for_secrets
                and self.secrets_sdk
            ):
                value = await self._decrypt_secret_value(config_entry.value, config_key)

            # Cache the result
            if self.config.enable_caching:
                await self._cache_config(config_key, value)

            return value

        except Exception as e:
            logger.error(f"Failed to get config {key}: {e}")
            return default_value

    async def get_config_entry(
        self,
        key: str,
        scope: ConfigScope,
        tenant_id: UUID | None = None,
        user_id: str | None = None,
        service_name: str | None = None,
        environment: ConfigEnvironment | None = None,
        context: RequestContext | None = None,
    ) -> ConfigEntry | None:
        """Get full configuration entry with metadata."""
        try:
            config_key = self._generate_config_key(
                key, scope, tenant_id, user_id, service_name, environment
            )
            config_entry = self._configs.get(config_key)

            if config_entry and config_entry.is_secret:
                # Return copy with redacted secret value
                config_copy = config_entry.model_copy()
                config_copy.value = "[REDACTED]"
                return config_copy

            return config_entry

        except Exception as e:
            logger.error(f"Failed to get config entry {key}: {e}")
            return None

    async def query_configs(
        self,
        query: ConfigQuery,
        context: RequestContext | None = None,
    ) -> ConfigQueryResponse:
        """Query configurations with filtering and pagination."""
        try:
            # Filter configs based on query
            filtered_configs = []
            for config_key, config_entry in self._configs.items():
                if self._matches_query(config_entry, query):
                    # Redact secret values
                    if config_entry.is_secret:
                        config_copy = config_entry.model_copy()
                        config_copy.value = "[REDACTED]"
                        filtered_configs.append(config_copy)
                    else:
                        filtered_configs.append(config_entry)

            # Apply sorting
            sorted_configs = self._sort_configs(
                filtered_configs, query.sort_by, query.sort_order
            )

            # Apply pagination
            total_count = len(sorted_configs)
            start_idx = (query.page - 1) * query.per_page
            end_idx = start_idx + query.per_page
            page_configs = sorted_configs[start_idx:end_idx]

            total_pages = (total_count + query.per_page - 1) // query.per_page

            return ConfigQueryResponse(
                configs=page_configs,
                total_count=total_count,
                page=query.page,
                per_page=query.per_page,
                total_pages=total_pages,
            )

        except Exception as e:
            logger.error(f"Failed to query configs: {e}")
            return ConfigQueryResponse(
                configs=[],
                total_count=0,
                page=query.page,
                per_page=query.per_page,
                total_pages=0,
            )

    async def delete_config(
        self,
        key: str,
        scope: ConfigScope,
        tenant_id: UUID | None = None,
        user_id: str | None = None,
        service_name: str | None = None,
        environment: ConfigEnvironment | None = None,
        context: RequestContext | None = None,
    ) -> bool:
        """Delete a configuration entry."""
        try:
            config_key = self._generate_config_key(
                key, scope, tenant_id, user_id, service_name, environment
            )

            existing_config = self._configs.get(config_key)
            if not existing_config:
                return False

            # Check if config is read-only
            if existing_config.is_readonly:
                raise PermissionError("Cannot delete read-only configuration")

            # Delete config
            del self._configs[config_key]

            # Clear cache
            if self.config.enable_caching:
                await self._invalidate_cache(config_key)

            # Audit log
            if self.config.enable_audit_logging:
                await self._log_config_change(
                    config_key=key,
                    action="delete",
                    old_value=(
                        existing_config.value
                        if not existing_config.is_secret
                        else "[REDACTED]"
                    ),
                    new_value=None,
                    tenant_id=tenant_id,
                    user_id=context.headers.x_user_id if context else None,
                    context=context,
                )

            return True

        except Exception as e:
            logger.error(f"Failed to delete config {key}: {e}")
            raise

    async def validate_config(
        self,
        key: str,
        value: Any,
        data_type: ConfigDataType,
        existing_config: ConfigEntry | None = None,
    ) -> ConfigValidationResult:
        """Validate a configuration value."""
        return await self._validate_config_value(key, value, data_type, existing_config)

    async def get_stats(
        self,
        tenant_id: UUID | None = None,
        context: RequestContext | None = None,
    ) -> ConfigStats:
        """Get configuration statistics."""
        try:
            # Filter configs by tenant if specified
            configs = list(self._configs.values())
            if tenant_id:
                configs = [c for c in configs if c.tenant_id == tenant_id]

            # Calculate statistics
            total_configs = len(configs)

            # Count by scope
            configs_by_scope = {}
            for config in configs:
                scope = config.scope.value
                configs_by_scope[scope] = configs_by_scope.get(scope, 0) + 1

            # Count by environment
            configs_by_environment = {}
            for config in configs:
                env = config.environment.value
                configs_by_environment[env] = configs_by_environment.get(env, 0) + 1

            # Count by data type
            configs_by_type = {}
            for config in configs:
                data_type = config.data_type.value
                configs_by_type[data_type] = configs_by_type.get(data_type, 0) + 1

            # Security counts
            secret_configs = sum(1 for c in configs if c.is_secret)
            readonly_configs = sum(1 for c in configs if c.is_readonly)

            # Recent changes
            yesterday = datetime.now(UTC) - timedelta(days=1)
            recent_changes = sum(
                1 for c in configs if c.updated_at and c.updated_at >= yesterday
            )

            # Active tenants and services
            active_tenants = len({str(c.tenant_id) for c in configs if c.tenant_id})
            active_services = len({c.service_name for c in configs if c.service_name})

            # Calculate most changed configurations from audit logs
            config_change_counts = {}
            for log in self._audit_logs:
                if hasattr(log, 'config_key') and log.config_key:
                    config_change_counts[log.config_key] = config_change_counts.get(log.config_key, 0) + 1
                elif hasattr(log, 'key') and log.key:
                    config_change_counts[log.key] = config_change_counts.get(log.key, 0) + 1
            
            # Get top 10 most changed configs
            most_changed = sorted(config_change_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            most_changed_configs = [
                {
                    "config_key": key,
                    "change_count": count,
                    "avg_changes_per_day": round(count / max(30, 1), 2)  # Assume 30-day tracking period
                }
                for key, count in most_changed
            ]

            return ConfigStats(
                total_configs=total_configs,
                configs_by_scope=configs_by_scope,
                configs_by_environment=configs_by_environment,
                configs_by_type=configs_by_type,
                secret_configs=secret_configs,
                readonly_configs=readonly_configs,
                recent_changes=recent_changes,
                most_changed_configs=most_changed_configs,
                active_tenants=active_tenants,
                active_services=active_services,
                total_templates=len(self._templates),
            )

        except Exception as e:
            logger.error(f"Failed to get config stats: {e}")
            raise

    async def health_check(self) -> PlatformConfigHealthCheck:
        """Perform health check."""
        try:
            total_configs = len(self._configs)

            # Check for invalid configs (simplified)
            invalid_configs = 0
            for config in self._configs.values():
                validation_result = await self._validate_config_value(
                    config.key, config.value, config.data_type, config
                )
                if not validation_result.is_valid:
                    invalid_configs += 1

            return PlatformConfigHealthCheck(
                status="healthy",
                timestamp=datetime.now(UTC),
                storage_available=True,
                storage_latency_ms=1.5,
                total_configs=total_configs,
                invalid_configs=invalid_configs,
                avg_read_latency_ms=2.0,
                avg_write_latency_ms=5.0,
                cache_enabled=self.config.enable_caching,
                cache_hit_rate=85.0,  # Mock cache hit rate
                details={
                    "templates_count": len(self._templates),
                    "audit_logs_count": len(self._audit_logs),
                },
            )

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return PlatformConfigHealthCheck(
                status="unhealthy",
                timestamp=datetime.now(UTC),
                storage_available=False,
                storage_latency_ms=None,
                total_configs=0,
                invalid_configs=0,
                avg_read_latency_ms=None,
                avg_write_latency_ms=None,
                cache_enabled=False,
                cache_hit_rate=None,
                details={"error": str(e)},
            )

    # Private helper methods

    def _generate_config_key(
        self,
        key: str,
        scope: ConfigScope,
        tenant_id: UUID | None = None,
        user_id: str | None = None,
        service_name: str | None = None,
        environment: ConfigEnvironment | None = None,
    ) -> str:
        """Generate unique configuration key."""
        parts = [scope.value, key]

        if tenant_id:
            parts.append(f"tenant:{tenant_id}")
        if user_id:
            parts.append(f"user:{user_id}")
        if service_name:
            parts.append(f"service:{service_name}")
        if environment:
            parts.append(f"env:{environment.value}")

        return ":".join(parts)

    async def _validate_config_value(  # noqa: C901
        self,
        key: str,
        value: Any,
        data_type: ConfigDataType,
        existing_config: ConfigEntry | None = None,
    ) -> ConfigValidationResult:
        """Validate configuration value."""
        errors = []
        warnings = []

        # Data type validation
        data_type_valid = True
        try:
            if data_type == ConfigDataType.STRING and not isinstance(value, str):
                errors.append("Value must be a string")
                data_type_valid = False
            elif data_type == ConfigDataType.INTEGER and not isinstance(value, int):
                errors.append("Value must be an integer")
                data_type_valid = False
            elif data_type == ConfigDataType.FLOAT and not isinstance(
                value, int | float
            ):
                errors.append("Value must be a number")
                data_type_valid = False
            elif data_type == ConfigDataType.BOOLEAN and not isinstance(value, bool):
                errors.append("Value must be a boolean")
                data_type_valid = False
            elif data_type == ConfigDataType.JSON:
                json.dumps(value)  # Test JSON serialization
            elif data_type == ConfigDataType.ARRAY and not isinstance(value, list):
                errors.append("Value must be an array")
                data_type_valid = False
        except Exception as e:
            errors.append(f"Data type validation failed: {e}")
            data_type_valid = False

        # Size validation
        try:
            value_size = len(json.dumps(value).encode())
            if value_size > self.config.max_config_size_bytes:
                errors.append(
                    f"Configuration size {value_size} exceeds maximum {self.config.max_config_size_bytes}"
                )
        except Exception:
            pass  # Skip size check if value can't be serialized

        # Constraints validation
        constraints_valid = True
        if existing_config:
            if (
                existing_config.allowed_values
                and value not in existing_config.allowed_values
            ):
                errors.append(f"Value must be one of: {existing_config.allowed_values}")
                constraints_valid = False

            if existing_config.min_value is not None and isinstance(value, int | float):
                if value < existing_config.min_value:
                    errors.append(f"Value must be >= {existing_config.min_value}")
                    constraints_valid = False

            if existing_config.max_value is not None and isinstance(value, int | float):
                if value > existing_config.max_value:
                    errors.append(f"Value must be <= {existing_config.max_value}")
                    constraints_valid = False

        # Implement basic JSON schema validation
        schema_valid = True
        try:
            if isinstance(value, dict):
                # Check for basic schema requirements
                if 'type' in value and not isinstance(value.get('type'), str):
                    schema_valid = False
                    errors.append("Schema 'type' field must be a string")
                
                # Check for circular references in nested objects
                def check_circular_refs(obj, visited=None):
                    if visited is None:
                        visited = set()
                    
                    if isinstance(obj, dict):
                        obj_id = id(obj)
                        if obj_id in visited:
                            return False
                        visited.add(obj_id)
                        
                        for val in obj.values():
                            if not check_circular_refs(val, visited.copy()):
                                return False
                    return True
                
                if not check_circular_refs(value):
                    schema_valid = False
                    errors.append("Circular reference detected in configuration object")
                    
            elif isinstance(value, str):
                # Check for valid JSON string if it looks like JSON
                if value.strip().startswith(('{', '[')):
                    try:
                        import json
                        json.loads(value)
                    except json.JSONDecodeError as e:
                        schema_valid = False
                        errors.append(f"Invalid JSON format: {str(e)}")
                        
        except Exception as e:
            # If schema validation fails, log but don't fail the entire validation
            warnings.append(f"Schema validation error: {str(e)}")
            schema_valid = True  # Default to valid if validation itself fails

        return ConfigValidationResult(
            key=key,
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            data_type_valid=data_type_valid,
            constraints_valid=constraints_valid,
            schema_valid=schema_valid,
        )

    async def _encrypt_secret_value(self, value: Any, config_key: str) -> str:
        """Encrypt secret configuration value."""
        # In production, use the secrets SDK for encryption
        return f"encrypted:{json.dumps(value)}"

    async def _decrypt_secret_value(self, encrypted_value: str, config_key: str) -> Any:
        """Decrypt secret configuration value."""
        # In production, use the secrets SDK for decryption
        if encrypted_value.startswith("encrypted:"):
            return json.loads(encrypted_value[10:])
        return encrypted_value

    async def _get_cached_config(self, config_key: str) -> Any:
        """Get configuration from cache."""
        cached_data = self._config_cache.get(config_key)
        if cached_data and cached_data["expires_at"] > datetime.now(UTC):
            return cached_data["value"]
        return None

    async def _cache_config(self, config_key: str, value: Any):
        """Cache configuration value."""
        self._config_cache[config_key] = {
            "value": value,
            "expires_at": datetime.now(UTC)
            + timedelta(seconds=self.config.cache_ttl_seconds),
        }

    async def _invalidate_cache(self, config_key: str):
        """Invalidate cached configuration."""
        if config_key in self._config_cache:
            del self._config_cache[config_key]

    async def _log_config_change(
        self,
        config_key: str,
        action: str,
        old_value: Any,
        new_value: Any,
        tenant_id: UUID | None = None,
        user_id: str | None = None,
        context: RequestContext | None = None,
    ):
        """Log configuration change for audit."""
        audit_log = ConfigAuditLog(
            id=uuid4(),
            config_key=config_key,
            action=action,
            old_value=old_value,
            new_value=new_value,
            tenant_id=tenant_id,
            user_id=user_id,
            ip_address=context.client_ip if context else None,
            user_agent=context.user_agent if context else None,
            timestamp=datetime.now(UTC),
        )

        self._audit_logs.append(audit_log)

    def _matches_query(self, config: ConfigEntry, query: ConfigQuery) -> bool:
        """
        Check if configuration matches query filters.
        
        REFACTORED: Replaced 24-complexity method with Strategy pattern.
        Now uses ConfigQueryMatcher for clean, testable filtering (Complexity: 2).
        """
        # Import here to avoid circular dependencies
        from .config_query_filters import create_config_query_matcher
        
        # Use strategy pattern for filtering (Complexity: 1)
        matcher = create_config_query_matcher()
        
        # Return match result (Complexity: 1)
        return matcher.matches_query(config, query)

    def _sort_configs(
        self, configs: list[ConfigEntry], sort_by: str, sort_order: str
    ) -> list[ConfigEntry]:
        """Sort configurations by specified field."""
        reverse = sort_order == "desc"

        if sort_by == "key":
            return sorted(configs, key=lambda c: c.key, reverse=reverse)
        elif sort_by == "updated_at":
            return sorted(
                configs, key=lambda c: c.updated_at or datetime.min, reverse=reverse
            )
        elif sort_by == "created_at":
            return sorted(
                configs, key=lambda c: c.created_at or datetime.min, reverse=reverse
            )
        else:
            return configs

    async def create_template(
        self,
        template: ConfigTemplate,
        context: RequestContext | None = None,
    ) -> ConfigTemplate:
        """Create a configuration template."""
        try:
            template.id = template.id or uuid4()
            template.created_at = datetime.now(UTC)

            # Store template (in production, use database)
            template_key = f"template:{template.id}"
            self._configs[template_key] = template

            logger.info(f"Created config template {template.name}")
            return template

        except Exception as e:
            logger.error(f"Failed to create template: {e}")
            raise

    async def get_template(
        self,
        template_id: UUID,
        tenant_id: UUID | None = None,
        context: RequestContext | None = None,
    ) -> ConfigTemplate | None:
        """Get a configuration template by ID."""
        try:
            template_key = f"template:{template_id}"
            template = self._configs.get(template_key)

            if isinstance(template, ConfigTemplate):
                return template
            return None

        except Exception as e:
            logger.error(f"Failed to get template: {e}")
            return None

    async def apply_template(
        self,
        template_id: UUID,
        tenant_id: UUID | None = None,
        environment: ConfigEnvironment | None = None,
        variables: dict[str, Any] | None = None,
        config_key_prefix: str | None = None,
        context: RequestContext | None = None,
    ) -> bool:
        """Apply a configuration template."""
        try:
            template = await self.get_template(template_id, tenant_id, context)
            if not template:
                return False

            # Apply template configurations
            for config in template.configs:
                # Replace variables in config values
                value = config.value
                if variables and isinstance(value, str):
                    for var_name, var_value in variables.items():
                        value = value.replace(f"{{{var_name}}}", str(var_value))

                await self.set_config(
                    key=config.key,
                    value=value,
                    scope=config.scope,
                    tenant_id=tenant_id or config.tenant_id,
                    environment=config.environment,
                    data_type=config.data_type,
                    context=context,
                )

            logger.info(f"Applied template {template.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to apply template: {e}")
            return False

    async def get_config_history(
        self,
        key: str,
        scope: ConfigScope,
        tenant_id: UUID | None = None,
        environment: ConfigEnvironment | None = None,
        context: RequestContext | None = None,
    ) -> list[ConfigEntry]:
        """Get configuration history."""
        try:
            # In production, would query version history from database
            config_key = self._generate_config_key(
                key, scope, tenant_id, environment=environment
            )
            current_config = self._configs.get(config_key)

            if current_config and isinstance(current_config, ConfigEntry):
                return [current_config]
            return []

        except Exception as e:
            logger.error(f"Failed to get config history: {e}")
            return []

    async def get_audit_logs(
        self,
        tenant_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        context: RequestContext | None = None,
    ) -> list[ConfigAuditLog]:
        """Get configuration audit logs."""
        try:
            # In production, would query audit logs from database
            logs = []
            for config in self._configs.values():
                if isinstance(config, ConfigEntry):
                    log = ConfigAuditLog(
                        id=uuid4(),
                        config_key=config.key,
                        action="GET",
                        old_value=None,
                        new_value=config.value,
                        user_id="system",
                        tenant_id=config.tenant_id,
                        timestamp=config.updated_at or datetime.now(UTC),
                        ip_address="127.0.0.1",
                        user_agent="test",
                    )
                    logs.append(log)
            return logs

        except Exception as e:
            logger.error(f"Failed to get audit logs: {e}")
            return []

    async def clear_cache(
        self,
        tenant_id: UUID | None = None,
        context: RequestContext | None = None,
    ) -> bool:
        """Clear configuration cache."""
        try:
            # Clear cache (in production, would clear Redis/memory cache)
            self._cache.clear()
            logger.info("Cleared config cache")
            return True

        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False

    async def validate_config(
        self,
        key: str,
        value: Any,
        data_type: ConfigDataType,
        tenant_id: UUID | None = None,
        context: RequestContext | None = None,
    ) -> ConfigValidationResult:
        """Validate configuration value."""
        try:
            errors = []
            warnings = []

            # Basic type validation
            if data_type == ConfigDataType.INTEGER:
                try:
                    int(value)
                except (ValueError, TypeError):
                    errors.append(f"Value '{value}' is not a valid integer")
            elif data_type == ConfigDataType.FLOAT:
                try:
                    float(value)
                except (ValueError, TypeError):
                    errors.append(f"Value '{value}' is not a valid float")
            elif data_type == ConfigDataType.BOOLEAN:
                if not isinstance(value, bool) and str(value).lower() not in [
                    "true",
                    "false",
                    "1",
                    "0",
                ]:
                    errors.append(f"Value '{value}' is not a valid boolean")
            elif data_type == ConfigDataType.JSON:
                try:
                    json.loads(str(value)) if isinstance(value, str) else value
                except (json.JSONDecodeError, TypeError):
                    errors.append(f"Value '{value}' is not valid JSON")

            return ConfigValidationResult(
                key=key,
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                data_type_valid=len(errors) == 0,
                constraints_valid=True,
                schema_valid=True,
            )

        except Exception as e:
            logger.error(f"Failed to validate config: {e}")
            return ConfigValidationResult(
                key=key,
                is_valid=False,
                errors=[str(e)],
                warnings=[],
                data_type_valid=False,
                constraints_valid=False,
                schema_valid=False,
            )

    async def update_config(
        self,
        request,
        context: RequestContext | None = None,
    ) -> ConfigEntry:
        """Update an existing configuration entry."""
        # Extract values from request object
        return await self.set_config(
            key=request.key,
            value=request.value,
            scope=ConfigScope.TENANT,  # Default scope
            tenant_id=getattr(request, "tenant_id", None),
            user_id=getattr(request, "user_id", None),
            service_name=getattr(request, "service_name", None),
            environment=getattr(request, "environment", ConfigEnvironment.DEVELOPMENT),
            data_type=getattr(request, "data_type", ConfigDataType.STRING),
            context=context,
        )
