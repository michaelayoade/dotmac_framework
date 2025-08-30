"""Configuration validation service with comprehensive checks."""

import asyncio
import ipaddress
import logging
import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError

from ..schemas.config_schemas import DatabaseConfig, ISPConfiguration, SecurityConfig
from ..schemas.tenant_schemas import TenantInfo

logger = logging.getLogger(__name__)


class ValidationLevel(str, Enum):
    """Validation severity levels."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationError(BaseModel):
    """Individual validation error or warning."""

    level: ValidationLevel = Field(..., description="Severity level")
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable message")
    path: str = Field(..., description="Configuration path where error occurred")
    value: Optional[Any] = Field(None, description="Invalid value")
    expected: Optional[str] = Field(None, description="Expected value or format")

    def __str__(self) -> str:
        return f"[{self.level.upper()}] {self.code}: {self.message} at {self.path}"


class ValidationResult(BaseModel):
    """Comprehensive validation result."""

    valid: bool = Field(..., description="Overall validation status")
    errors: List[ValidationError] = Field(
        default_factory=list, description="Validation errors"
    )
    warnings: List[ValidationError] = Field(
        default_factory=list, description="Validation warnings"
    )
    info: List[ValidationError] = Field(
        default_factory=list, description="Validation info messages"
    )

    # Summary statistics
    total_checks: int = Field(default=0, description="Total number of checks performed")
    error_count: int = Field(default=0, description="Number of errors")
    warning_count: int = Field(default=0, description="Number of warnings")

    # Validation metadata
    validated_at: datetime = Field(
        default_factory=datetime.now, description="Validation timestamp"
    )
    validation_duration_ms: float = Field(
        default=0.0, description="Validation duration in milliseconds"
    )
    validator_version: str = Field(default="1.0.0", description="Validator version")

    def add_error(
        self,
        code: str,
        message: str,
        path: str,
        value: Any = None,
        expected: str = None,
    ):
        """Add a validation error."""
        error = ValidationError(
            level=ValidationLevel.ERROR,
            code=code,
            message=message,
            path=path,
            value=value,
            expected=expected,
        )
        self.errors.append(error)
        self.error_count += 1
        self.valid = False

    def add_warning(
        self,
        code: str,
        message: str,
        path: str,
        value: Any = None,
        expected: str = None,
    ):
        """Add a validation warning."""
        warning = ValidationError(
            level=ValidationLevel.WARNING,
            code=code,
            message=message,
            path=path,
            value=value,
            expected=expected,
        )
        self.warnings.append(warning)
        self.warning_count += 1

    def add_info(self, code: str, message: str, path: str, value: Any = None):
        """Add a validation info message."""
        info = ValidationError(
            level=ValidationLevel.INFO,
            code=code,
            message=message,
            path=path,
            value=value,
        )
        self.info.append(info)

    def get_all_messages(self) -> List[ValidationError]:
        """Get all validation messages sorted by severity."""
        return self.errors + self.warnings + self.info

    def has_critical_errors(self) -> bool:
        """Check if there are any critical errors."""
        critical_codes = [
            "DATABASE_CONNECTION_FAILED",
            "REDIS_CONNECTION_FAILED",
            "INVALID_ENCRYPTION_KEY",
            "MISSING_REQUIRED_SECRET",
            "CIRCULAR_DEPENDENCY",
        ]
        return any(error.code in critical_codes for error in self.errors)

    def to_summary(self) -> str:
        """Get a summary string of validation results."""
        if self.valid:
            return f"✅ Configuration valid ({self.warning_count} warnings)"
        else:
            return f"❌ Configuration invalid ({self.error_count} errors, {self.warning_count} warnings)"


class SecurityValidator:
    """Validates security-related configuration."""

    def __init__(self):
        self.weak_passwords = {
            "password",
            "123456",
            "admin",
            "root",
            "guest",
            "test",
            "demo",
            "changeme",
            "default",
        }

        self.insecure_patterns = [
            re.compile(r'password\s*=\s*["\']?\w{1,5}["\']?', re.IGNORECASE),
            re.compile(r'secret\s*=\s*["\']?\w{1,8}["\']?', re.IGNORECASE),
            re.compile(r'key\s*=\s*["\']?test["\']?', re.IGNORECASE),
        ]

    async def validate_security_config(
        self, config: SecurityConfig, result: ValidationResult, path: str = "security"
    ):
        """Validate security configuration."""
        result.total_checks += 1

        # JWT Secret validation
        if len(config.jwt_secret_key) < 32:
            result.add_error(
                "WEAK_JWT_SECRET",
                "JWT secret key should be at least 32 characters",
                f"{path}.jwt_secret_key",
                len(config.jwt_secret_key),
                "At least 32 characters",
            )

        # Check for placeholder secrets
        if config.jwt_secret_key.startswith("${SECRET:"):
            result.add_info(
                "SECRET_PLACEHOLDER",
                "JWT secret uses placeholder",
                f"{path}.jwt_secret_key",
            )
        elif config.jwt_secret_key.lower() in self.weak_passwords:
            result.add_error(
                "WEAK_JWT_SECRET_VALUE",
                "JWT secret appears to be a weak/common password",
                f"{path}.jwt_secret_key",
            )

        # Encryption key validation
        if len(config.encryption_key) < 32:
            result.add_error(
                "WEAK_ENCRYPTION_KEY",
                "Encryption key should be at least 32 characters",
                f"{path}.encryption_key",
                len(config.encryption_key),
                "At least 32 characters",
            )

        # CORS validation
        if config.cors_enabled and not config.cors_origins:
            result.add_warning(
                "CORS_NO_ORIGINS",
                "CORS is enabled but no origins are specified",
                f"{path}.cors_origins",
            )

        # Rate limiting validation
        if config.rate_limit_enabled:
            if config.rate_limit_requests_per_minute > 10000:
                result.add_warning(
                    "HIGH_RATE_LIMIT",
                    "Very high rate limit may impact performance",
                    f"{path}.rate_limit_requests_per_minute",
                    config.rate_limit_requests_per_minute,
                )
            elif config.rate_limit_requests_per_minute < 10:
                result.add_warning(
                    "LOW_RATE_LIMIT",
                    "Very low rate limit may impact user experience",
                    f"{path}.rate_limit_requests_per_minute",
                    config.rate_limit_requests_per_minute,
                )

    async def validate_secrets_in_config(
        self, config_dict: Dict[str, Any], result: ValidationResult, path: str = ""
    ):
        """Recursively validate secrets in configuration."""
        for key, value in config_dict.items():
            current_path = f"{path}.{key}" if path else key

            if isinstance(value, dict):
                await self.validate_secrets_in_config(value, result, current_path)
            elif isinstance(value, str):
                # Check for insecure patterns
                for pattern in self.insecure_patterns:
                    if pattern.search(value):
                        result.add_warning(
                            "POTENTIAL_HARDCODED_SECRET",
                            "Potential hardcoded secret detected",
                            current_path,
                            value[:20] + "..." if len(value) > 20 else value,
                        )

                # Check for unresolved secret placeholders
                if "${SECRET:" in value and not value.startswith("${SECRET:"):
                    result.add_warning(
                        "PARTIAL_SECRET_PLACEHOLDER",
                        "Partial secret placeholder detected - may not be properly injected",
                        current_path,
                        value,
                    )


class NetworkValidator:
    """Validates network-related configuration."""

    async def validate_network_config(
        self, config: Any, result: ValidationResult, path: str = "network"
    ):
        """Validate network configuration."""
        result.total_checks += 1

        # Port validation
        if hasattr(config, "port"):
            if not (1 <= config.port <= 65535):
                result.add_error(
                    "INVALID_PORT",
                    "Port must be between 1 and 65535",
                    f"{path}.port",
                    config.port,
                    "1-65535",
                )
            elif config.port < 1024:
                result.add_warning(
                    "PRIVILEGED_PORT",
                    "Using privileged port (< 1024) may require special permissions",
                    f"{path}.port",
                    config.port,
                )

        # Host validation
        if hasattr(config, "host"):
            try:
                ipaddress.ip_address(config.host)
                if config.host == "0.0.0.0":
                    result.add_info(
                        "BIND_ALL_INTERFACES",
                        "Binding to all interfaces",
                        f"{path}.host",
                    )
            except ValueError:
                if config.host not in ["localhost", "0.0.0.0"]:
                    result.add_warning(
                        "CUSTOM_HOST",
                        "Using custom host - ensure DNS resolution works",
                        f"{path}.host",
                        config.host,
                    )

    async def validate_service_dependencies(
        self, services: List[Any], result: ValidationResult, path: str = "services"
    ):
        """Validate service dependencies for circular references."""
        result.total_checks += 1

        # Build dependency graph
        dependencies = {}
        service_names = set()

        for service in services:
            service_names.add(service.name)
            dependencies[service.name] = getattr(service, "depends_on", [])

        # Check for missing dependencies
        for service in services:
            for dep in getattr(service, "depends_on", []):
                if dep not in service_names:
                    result.add_error(
                        "MISSING_DEPENDENCY",
                        f"Service {service.name} depends on unknown service {dep}",
                        f"{path}.{service.name}.depends_on",
                        dep,
                    )

        # Check for circular dependencies using DFS
        def has_cycle(node: str, visited: Set[str], rec_stack: Set[str]) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in dependencies.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.discard(node)
            return False

        visited = set()
        for service_name in service_names:
            if service_name not in visited:
                if has_cycle(service_name, visited, set()):
                    result.add_error(
                        "CIRCULAR_DEPENDENCY",
                        f"Circular dependency detected involving service {service_name}",
                        f"{path}.dependencies",
                    )
                    break


class DatabaseValidator:
    """Validates database configuration."""

    async def validate_database_config(
        self, config: DatabaseConfig, result: ValidationResult, path: str = "database"
    ):
        """Validate database configuration."""
        result.total_checks += 1

        # Connection pool validation
        if config.pool_size <= 0:
            result.add_error(
                "INVALID_POOL_SIZE",
                "Database pool size must be greater than 0",
                f"{path}.pool_size",
                config.pool_size,
                "> 0",
            )
        elif config.pool_size > 100:
            result.add_warning(
                "LARGE_POOL_SIZE",
                "Large connection pool may consume excessive resources",
                f"{path}.pool_size",
                config.pool_size,
            )

        if config.max_overflow < 0:
            result.add_error(
                "INVALID_MAX_OVERFLOW",
                "Max overflow cannot be negative",
                f"{path}.max_overflow",
                config.max_overflow,
                ">= 0",
            )

        # Timeout validation
        if config.pool_timeout <= 0:
            result.add_error(
                "INVALID_TIMEOUT",
                "Pool timeout must be greater than 0",
                f"{path}.pool_timeout",
                config.pool_timeout,
                "> 0",
            )

        # Password validation
        if not config.password.startswith("${SECRET:") and len(config.password) < 8:
            result.add_warning(
                "WEAK_DATABASE_PASSWORD",
                "Database password should be at least 8 characters",
                f"{path}.password",
                len(config.password),
            )

        # SSL validation
        if config.ssl_mode not in [
            "disable",
            "allow",
            "prefer",
            "require",
            "verify-ca",
            "verify-full",
        ]:
            result.add_warning(
                "INVALID_SSL_MODE",
                "Unknown SSL mode",
                f"{path}.ssl_mode",
                config.ssl_mode,
                "One of: disable, allow, prefer, require, verify-ca, verify-full",
            )

    async def validate_database_connectivity(
        self, config: DatabaseConfig, result: ValidationResult, path: str = "database"
    ):
        """Validate database connectivity (placeholder)."""
        result.total_checks += 1

        # In production, this would attempt actual connection
        # For now, just validate host format
        if not config.host:
            result.add_error(
                "MISSING_DATABASE_HOST", "Database host is required", f"{path}.host"
            )
        elif config.host.startswith("localhost") and not config.host.startswith(
            "localhost:"
        ):
            result.add_info(
                "LOCALHOST_DATABASE",
                "Using localhost database - ensure it's accessible",
                f"{path}.host",
            )


class EnvironmentValidator:
    """Validates environment-specific configuration."""

    def __init__(self):
        self.production_requirements = {
            "logging.log_to_file": True,
            "monitoring.metrics_enabled": True,
            "security.enable_security_headers": True,
        }

        self.development_warnings = [
            (
                "security.jwt_access_token_expire_minutes",
                60,
                "Consider shorter expiry in production",
            ),
            ("database.pool_size", 20, "Consider smaller pool in development"),
        ]

    async def validate_environment_config(
        self, config: ISPConfiguration, result: ValidationResult
    ):
        """Validate configuration based on environment."""
        result.total_checks += 1

        env = config.environment.lower()

        if env == "production":
            await self._validate_production_config(config, result)
        elif env == "development":
            await self._validate_development_config(config, result)
        elif env == "staging":
            await self._validate_staging_config(config, result)
        else:
            result.add_warning(
                "UNKNOWN_ENVIRONMENT",
                f"Unknown environment '{env}' - using default validations",
                "environment",
                env,
            )

    async def _validate_production_config(
        self, config: ISPConfiguration, result: ValidationResult
    ):
        """Validate production-specific requirements."""
        # Logging requirements
        if not config.logging.log_to_file:
            result.add_warning(
                "PROD_NO_FILE_LOGGING",
                "Production should enable file logging",
                "logging.log_to_file",
            )

        if config.logging.level.value == "DEBUG":
            result.add_warning(
                "PROD_DEBUG_LOGGING",
                "DEBUG logging in production may impact performance and expose sensitive data",
                "logging.level",
                config.logging.level.value,
                "INFO or WARNING",
            )

        # Security requirements
        if not config.security.enable_security_headers:
            result.add_error(
                "PROD_MISSING_SECURITY_HEADERS",
                "Production must enable security headers",
                "security.enable_security_headers",
            )

        if config.security.jwt_access_token_expire_minutes > 60:
            result.add_warning(
                "PROD_LONG_TOKEN_EXPIRY",
                "Long token expiry in production may be a security risk",
                "security.jwt_access_token_expire_minutes",
                config.security.jwt_access_token_expire_minutes,
                "<= 60 minutes",
            )

        # Monitoring requirements
        if not config.monitoring.metrics_enabled:
            result.add_warning(
                "PROD_NO_METRICS",
                "Production should enable metrics collection",
                "monitoring.metrics_enabled",
            )

    async def _validate_development_config(
        self, config: ISPConfiguration, result: ValidationResult
    ):
        """Validate development-specific configuration."""
        # Development-specific info messages
        if config.database.pool_size > 10:
            result.add_info(
                "DEV_LARGE_POOL",
                "Large connection pool in development - consider reducing for resource efficiency",
                "database.pool_size",
                config.database.pool_size,
            )

        if config.logging.level.value != "DEBUG":
            result.add_info(
                "DEV_NON_DEBUG_LOGGING",
                "Consider DEBUG logging level in development",
                "logging.level",
                config.logging.level.value,
            )

    async def _validate_staging_config(
        self, config: ISPConfiguration, result: ValidationResult
    ):
        """Validate staging-specific configuration."""
        # Staging should be similar to production
        result.add_info(
            "STAGING_ENVIRONMENT",
            "Staging environment detected - ensure configuration matches production closely",
            "environment",
        )


class ConfigurationValidator:
    """
    Comprehensive configuration validator.

    Performs multi-level validation including syntax, security,
    networking, dependencies, and environment-specific checks.
    """

    def __init__(self, strict_mode: bool = False):
        """Initialize the validator."""
        self.strict_mode = strict_mode
        self.security_validator = SecurityValidator()
        self.network_validator = NetworkValidator()
        self.database_validator = DatabaseValidator()
        self.environment_validator = EnvironmentValidator()

    async def validate_configuration(
        self, config: ISPConfiguration, tenant_info: Optional[TenantInfo] = None
    ) -> ValidationResult:
        """
        Perform comprehensive configuration validation.

        Args:
            config: Configuration to validate
            tenant_info: Optional tenant information for context

        Returns:
            Detailed validation result
        """
        start_time = datetime.now()
        result = ValidationResult(valid=True)

        logger.info(f"Starting configuration validation for tenant {config.tenant_id}")

        try:
            # Basic structure validation
            await self._validate_basic_structure(config, result)

            # Component-specific validation
            await self.security_validator.validate_security_config(
                config.security, result
            )
            await self.database_validator.validate_database_config(
                config.database, result
            )
            await self.network_validator.validate_network_config(config.network, result)
            await self.network_validator.validate_service_dependencies(
                config.services, result
            )

            # Secret validation
            config_dict = config.model_dump()
            await self.security_validator.validate_secrets_in_config(
                config_dict, result
            )

            # Environment-specific validation
            await self.environment_validator.validate_environment_config(config, result)

            # Feature flag validation
            await self._validate_feature_flags(config, result)

            # Business logic validation
            if tenant_info:
                await self._validate_business_rules(config, tenant_info, result)

            # Cross-component validation
            await self._validate_cross_component_consistency(config, result)

            # Final validation state
            result.valid = result.error_count == 0 and (
                not self.strict_mode or result.warning_count == 0
            )

            # Calculate duration
            end_time = datetime.now()
            result.validation_duration_ms = (
                end_time - start_time
            ).total_seconds() * 1000

            logger.info(f"Configuration validation completed: {result.to_summary()}")
            return result

        except Exception as e:
            logger.error(f"Validation failed with exception: {e}")
            result.add_error(
                "VALIDATION_EXCEPTION",
                f"Validation failed with exception: {str(e)}",
                "validator",
            )
            result.valid = False
            return result

    async def _validate_basic_structure(
        self, config: ISPConfiguration, result: ValidationResult
    ):
        """Validate basic configuration structure."""
        result.total_checks += 1

        # Check required fields
        if not config.tenant_id:
            result.add_error("MISSING_TENANT_ID", "Tenant ID is required", "tenant_id")

        if not config.environment:
            result.add_error(
                "MISSING_ENVIRONMENT", "Environment is required", "environment"
            )

        # Check service names are unique
        service_names = [s.name for s in config.services]
        if len(service_names) != len(set(service_names)):
            duplicates = [
                name for name in service_names if service_names.count(name) > 1
            ]
            result.add_error(
                "DUPLICATE_SERVICE_NAMES",
                f"Duplicate service names: {', '.join(set(duplicates))}",
                "services",
                duplicates,
            )

    async def _validate_feature_flags(
        self, config: ISPConfiguration, result: ValidationResult
    ):
        """Validate feature flag configuration."""
        result.total_checks += 1

        # Check for duplicate feature names
        feature_names = [f.feature_name for f in config.feature_flags]
        if len(feature_names) != len(set(feature_names)):
            duplicates = [
                name for name in feature_names if feature_names.count(name) > 1
            ]
            result.add_error(
                "DUPLICATE_FEATURE_FLAGS",
                f"Duplicate feature flag names: {', '.join(set(duplicates))}",
                "feature_flags",
                duplicates,
            )

        # Validate rollout percentages
        for i, flag in enumerate(config.feature_flags):
            if not (0.0 <= flag.rollout_percentage <= 100.0):
                result.add_error(
                    "INVALID_ROLLOUT_PERCENTAGE",
                    "Rollout percentage must be between 0 and 100",
                    f"feature_flags[{i}].rollout_percentage",
                    flag.rollout_percentage,
                    "0-100",
                )

    async def _validate_business_rules(
        self,
        config: ISPConfiguration,
        tenant_info: TenantInfo,
        result: ValidationResult,
    ):
        """Validate business logic and tenant-specific rules."""
        result.total_checks += 1

        # Validate subscription plan limits
        plan_limits = {
            "basic": {"max_services": 5, "max_external_services": 3},
            "premium": {"max_services": 15, "max_external_services": 10},
            "enterprise": {
                "max_services": -1,
                "max_external_services": -1,
            },  # Unlimited
        }

        plan = tenant_info.subscription_plan.lower()
        limits = plan_limits.get(plan, plan_limits["basic"])

        if limits["max_services"] > 0 and len(config.services) > limits["max_services"]:
            result.add_error(
                "PLAN_SERVICE_LIMIT_EXCEEDED",
                f"Plan '{plan}' allows max {limits['max_services']} services, but {len(config.services)} configured",
                "services",
                len(config.services),
                f"<= {limits['max_services']}",
            )

        if (
            limits["max_external_services"] > 0
            and len(config.external_services) > limits["max_external_services"]
        ):
            result.add_error(
                "PLAN_EXTERNAL_SERVICE_LIMIT_EXCEEDED",
                f"Plan '{plan}' allows max {limits['max_external_services']} external services",
                "external_services",
                len(config.external_services),
                f"<= {limits['max_external_services']}",
            )

    async def _validate_cross_component_consistency(
        self, config: ISPConfiguration, result: ValidationResult
    ):
        """Validate consistency across configuration components."""
        result.total_checks += 1

        # Validate Redis and database are using different ports if on same host
        if (
            config.database.host == config.redis.host
            and config.database.port == config.redis.port
        ):
            result.add_error(
                "PORT_CONFLICT",
                "Database and Redis cannot use the same host:port combination",
                "database.port, redis.port",
            )

        # Validate monitoring and logging consistency
        if config.monitoring.metrics_enabled and not config.logging.log_to_file:
            result.add_warning(
                "MONITORING_WITHOUT_LOGGING",
                "Metrics enabled but file logging disabled - may lose important data",
                "monitoring.metrics_enabled, logging.log_to_file",
            )

        # Validate feature flags match enabled services
        analytics_service_exists = any(s.name == "analytics" for s in config.services)
        analytics_feature_enabled = any(
            f.feature_name == "advanced_analytics" and f.enabled
            for f in config.feature_flags
        )

        if analytics_feature_enabled and not analytics_service_exists:
            result.add_warning(
                "FEATURE_SERVICE_MISMATCH",
                "Advanced analytics feature enabled but analytics service not configured",
                "feature_flags, services",
            )

    async def validate_schema(self, config_dict: Dict[str, Any]) -> ValidationResult:
        """Validate configuration against Pydantic schema."""
        result = ValidationResult(valid=True)

        try:
            ISPConfiguration.model_validate(config_dict)
            result.add_info(
                "SCHEMA_VALID", "Configuration passes schema validation", "schema"
            )
        except ValidationError as e:
            for error in e.errors():
                loc = ".".join(str(x) for x in error["loc"])
                result.add_error(
                    "SCHEMA_ERROR",
                    error["msg"],
                    loc,
                    error.get("input"),
                    error.get("type"),
                )

        return result

    async def quick_validate(self, config: ISPConfiguration) -> bool:
        """Perform quick validation returning only boolean result."""
        result = await self.validate_configuration(config)
        return result.valid and result.error_count == 0
