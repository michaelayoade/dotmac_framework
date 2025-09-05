"""
Configuration validation handler.
Validates merged configuration data for consistency and security.
"""

import logging
import re
from pathlib import Path
from typing import Any

from .configuration_handler import (
    ConfigurationHandler,
    ConfigurationHandlerError,
    ReloadContext,
)

logger = logging.getLogger(__name__)


class ValidationHandler(ConfigurationHandler):
    """Handler for validating merged configuration data."""

    def can_handle(self, config_path: Path, context: ReloadContext) -> bool:
        """This handler always runs as the final validation step."""
        return True

    def handle(self, config_path: Path, context: ReloadContext) -> ReloadContext:
        """
        Validate merged configuration data.

        REFACTORED: Extracted from 22-complexity _perform_reload method.
        This handler focuses only on configuration validation.
        """
        try:
            if not context.new_config:
                context.add_warning("No configuration data to validate")
                return context

            # Perform comprehensive validation
            self._validate_configuration_structure(context)
            self._validate_security_constraints(context)
            self._validate_business_rules(context)
            self._validate_cross_references(context)

            if not context.has_errors():
                logger.info("Configuration validation passed successfully")
            else:
                logger.error(
                    f"Configuration validation failed with {len(context.errors)} errors"
                )

        except Exception as e:
            raise ConfigurationHandlerError(
                f"Configuration validation failed: {str(e)}"
            ) from e

        return context

    def _validate_configuration_structure(self, context: ReloadContext) -> None:
        """Validate basic configuration structure."""
        config = context.new_config

        # Check for required top-level sections
        required_sections = ["database", "redis", "api"]
        missing_sections = [
            section for section in required_sections if section not in config
        ]

        if missing_sections:
            context.add_error(
                f"Missing required configuration sections: {missing_sections}"
            )

        # Validate database configuration
        if "database" in config:
            self._validate_database_config(config["database"], context)

        # Validate Redis configuration
        if "redis" in config:
            self._validate_redis_config(config["redis"], context)

        # Validate API configuration
        if "api" in config:
            self._validate_api_config(config["api"], context)

    def _validate_database_config(self, db_config: Any, context: ReloadContext) -> None:
        """Validate database configuration."""
        if not isinstance(db_config, dict):
            context.add_error("Database configuration must be an object")
            return

        required_db_keys = ["host", "port", "database", "username"]
        missing_keys = [key for key in required_db_keys if key not in db_config]

        if missing_keys:
            context.add_error(
                f"Missing required database configuration keys: {missing_keys}"
            )

        # Validate port number
        if "port" in db_config:
            try:
                port = int(db_config["port"])
                if not (1 <= port <= 65535):
                    context.add_error(
                        f"Database port {port} is not valid (must be 1-65535)"
                    )
            except (ValueError, TypeError):
                context.add_error(
                    f"Database port '{db_config['port']}' is not a valid number"
                )

        # Validate connection pool settings
        if "pool_size" in db_config:
            try:
                pool_size = int(db_config["pool_size"])
                if pool_size < 1 or pool_size > 100:
                    context.add_warning(
                        f"Database pool_size {pool_size} may be suboptimal (recommended: 5-20)"
                    )
            except (ValueError, TypeError):
                context.add_error(
                    f"Database pool_size '{db_config['pool_size']}' is not a valid number"
                )

    def _validate_redis_config(self, redis_config: Any, context: ReloadContext) -> None:
        """Validate Redis configuration."""
        if not isinstance(redis_config, dict):
            context.add_error("Redis configuration must be an object")
            return

        required_redis_keys = ["host", "port"]
        missing_keys = [key for key in required_redis_keys if key not in redis_config]

        if missing_keys:
            context.add_error(
                f"Missing required Redis configuration keys: {missing_keys}"
            )

        # Validate port number
        if "port" in redis_config:
            try:
                port = int(redis_config["port"])
                if not (1 <= port <= 65535):
                    context.add_error(
                        f"Redis port {port} is not valid (must be 1-65535)"
                    )
            except (ValueError, TypeError):
                context.add_error(
                    f"Redis port '{redis_config['port']}' is not a valid number"
                )

        # Validate database number
        if "db" in redis_config:
            try:
                db_num = int(redis_config["db"])
                if not (0 <= db_num <= 15):
                    context.add_error(
                        f"Redis database number {db_num} is not valid (must be 0-15)"
                    )
            except (ValueError, TypeError):
                context.add_error(
                    f"Redis database '{redis_config['db']}' is not a valid number"
                )

    def _validate_api_config(self, api_config: Any, context: ReloadContext) -> None:
        """Validate API configuration."""
        if not isinstance(api_config, dict):
            context.add_error("API configuration must be an object")
            return

        # Validate API port
        if "port" in api_config:
            try:
                port = int(api_config["port"])
                if not (1024 <= port <= 65535):
                    context.add_warning(
                        f"API port {port} should be >= 1024 for non-privileged operation"
                    )
            except (ValueError, TypeError):
                context.add_error(
                    f"API port '{api_config['port']}' is not a valid number"
                )

        # Validate host binding
        if "host" in api_config:
            host = api_config["host"]
            if host == "0.0.0.0":
                context.add_warning(
                    "API host '0.0.0.0' binds to all interfaces (security risk)"
                )

        # Validate rate limiting
        if "rate_limit" in api_config:
            rate_limit = api_config["rate_limit"]
            if isinstance(rate_limit, dict):
                if "requests_per_minute" in rate_limit:
                    try:
                        rpm = int(rate_limit["requests_per_minute"])
                        if rpm <= 0:
                            context.add_error(
                                "API rate limit requests_per_minute must be positive"
                            )
                        elif rpm > 10000:
                            context.add_warning(
                                f"API rate limit {rpm} RPM is very high"
                            )
                    except (ValueError, TypeError):
                        context.add_error(
                            "API rate limit requests_per_minute must be a number"
                        )

    def _validate_security_constraints(self, context: ReloadContext) -> None:
        """Validate security-related configuration constraints."""
        config = context.new_config

        # Check for secrets in configuration
        self._check_for_exposed_secrets(config, context)

        # Validate SSL/TLS settings
        self._validate_tls_config(config, context)

        # Check authentication settings
        self._validate_auth_config(config, context)

    def _check_for_exposed_secrets(
        self, config: dict[str, Any], context: ReloadContext
    ) -> None:
        """Check for potentially exposed secrets in configuration."""
        secret_patterns = [
            (r'password.*["\'].*[a-zA-Z0-9]{8,}.*["\']', "password"),
            (r'secret.*["\'].*[a-zA-Z0-9]{16,}.*["\']', "secret"),
            (r'key.*["\'].*[a-zA-Z0-9]{16,}.*["\']', "api key"),
            (r'token.*["\'].*[a-zA-Z0-9]{16,}.*["\']', "token"),
        ]

        config_str = str(config).lower()

        for pattern, secret_type in secret_patterns:
            if re.search(pattern, config_str):
                context.add_warning(
                    f"Configuration may contain exposed {secret_type}. "
                    f"Use environment variables or secure vaults instead."
                )

    def _validate_tls_config(
        self, config: dict[str, Any], context: ReloadContext
    ) -> None:
        """Validate TLS/SSL configuration."""
        # Check if TLS is disabled in production-like environments
        env = config.get("environment", "").lower()
        if env in ["production", "prod", "staging"]:
            if config.get("api", {}).get("ssl_enabled", True) is False:
                context.add_error("SSL must be enabled in production environments")

            tls_version = config.get("api", {}).get("tls_version", "")
            if tls_version and tls_version < "1.2":
                context.add_error(
                    f"TLS version {tls_version} is deprecated, use TLS 1.2 or higher"
                )

    def _validate_auth_config(
        self, config: dict[str, Any], context: ReloadContext
    ) -> None:
        """Validate authentication configuration."""
        auth_config = config.get("authentication", {})

        if isinstance(auth_config, dict):
            # Check JWT settings
            jwt_config = auth_config.get("jwt", {})
            if isinstance(jwt_config, dict):
                if "secret_key" in jwt_config:
                    secret_key = jwt_config["secret_key"]
                    if isinstance(secret_key, str) and len(secret_key) < 32:
                        context.add_error(
                            "JWT secret key must be at least 32 characters"
                        )

                if "expiration" in jwt_config:
                    try:
                        exp = int(jwt_config["expiration"])
                        if exp > 86400 * 7:  # 7 days
                            context.add_warning(
                                f"JWT expiration {exp}s is longer than recommended (7 days max)"
                            )
                    except (ValueError, TypeError):
                        context.add_error("JWT expiration must be a number (seconds)")

    def _validate_business_rules(self, context: ReloadContext) -> None:
        """Validate business logic configuration rules."""
        config = context.new_config

        # Validate tenant isolation settings
        if "multi_tenant" in config and config["multi_tenant"]:
            if not config.get("tenant_isolation", {}).get("enabled", False):
                context.add_error(
                    "Multi-tenant mode requires tenant isolation to be enabled"
                )

        # Validate service dependencies
        services = config.get("services", {})
        if isinstance(services, dict):
            for service_name, service_config in services.items():
                if isinstance(service_config, dict):
                    self._validate_service_config(service_name, service_config, context)

    def _validate_service_config(
        self, service_name: str, service_config: dict[str, Any], context: ReloadContext
    ) -> None:
        """Validate individual service configuration."""
        # Check required service settings
        if "enabled" not in service_config:
            context.add_warning(f"Service '{service_name}' missing 'enabled' setting")

        # Validate resource limits
        if "resources" in service_config:
            resources = service_config["resources"]
            if isinstance(resources, dict):
                if "memory_mb" in resources:
                    try:
                        memory = int(resources["memory_mb"])
                        if memory < 128:
                            context.add_warning(
                                f"Service '{service_name}' memory limit {memory}MB is very low"
                            )
                        elif memory > 8192:
                            context.add_warning(
                                f"Service '{service_name}' memory limit {memory}MB is very high"
                            )
                    except (ValueError, TypeError):
                        context.add_error(
                            f"Service '{service_name}' memory_mb must be a number"
                        )

    def _validate_cross_references(self, context: ReloadContext) -> None:
        """Validate cross-references between configuration sections."""
        config = context.new_config

        # Validate database references
        services = config.get("services", {})
        db_config = config.get("database", {})

        if isinstance(services, dict) and isinstance(db_config, dict):
            db_name = db_config.get("database", "")

            for service_name, service_config in services.items():
                if isinstance(service_config, dict):
                    service_db = service_config.get("database", "")
                    if service_db and service_db != db_name:
                        context.add_warning(
                            f"Service '{service_name}' references database '{service_db}' "
                            f"but main database is '{db_name}'"
                        )
        # Validate Redis references
        redis_config = config.get("redis", {})
        if isinstance(redis_config, dict) and isinstance(services, dict):
            redis_host = redis_config.get("host", "localhost")

            for service_name, service_config in services.items():
                if isinstance(service_config, dict):
                    service_redis = service_config.get("redis_host", "")
                    if service_redis and service_redis != redis_host:
                        context.add_warning(
                            f"Service '{service_name}' references Redis host '{service_redis}' "
                            f"but main Redis host is '{redis_host}'"
                        )
