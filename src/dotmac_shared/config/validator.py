"""
Centralized Environment Configuration Validator
Validates environment variables and OpenBao integration for production readiness
"""

import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from dotmac_shared.core.logging import get_logger

logger = get_logger(__name__)


class EnvironmentTier(str, Enum):
    """Environment tiers for configuration validation"""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class ValidationSeverity(str, Enum):
    """Severity levels for configuration issues"""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationResult:
    """Result of environment variable validation"""

    variable: str
    is_valid: bool
    severity: ValidationSeverity
    message: str
    current_value: Optional[str] = None
    suggested_value: Optional[str] = None


class EnvironmentValidator:
    """
    Centralized validator for environment variables and OpenBao integration.
    Provides comprehensive validation for different environment tiers.
    """

    def __init__(self):
        self.validation_results: list[ValidationResult] = []

    def validate_environment(self, tier: EnvironmentTier = EnvironmentTier.DEVELOPMENT) -> dict[str, Any]:
        """
        Comprehensive environment validation for the specified tier.

        Args:
            tier: Environment tier to validate against

        Returns:
            Dict containing validation results and status
        """
        logger.info(f"Starting environment validation for tier: {tier.value}")

        self.validation_results = []

        # Core infrastructure validation
        self._validate_core_infrastructure(tier)

        # Security validation
        self._validate_security_config(tier)

        # Database validation
        self._validate_database_config(tier)

        # External service validation
        self._validate_external_services(tier)

        # Application-specific validation
        self._validate_application_config(tier)

        # Categorize results
        errors = [r for r in self.validation_results if r.severity == ValidationSeverity.ERROR]
        warnings = [r for r in self.validation_results if r.severity == ValidationSeverity.WARNING]
        info = [r for r in self.validation_results if r.severity == ValidationSeverity.INFO]

        result = {
            "tier": tier.value,
            "timestamp": "2025-09-05T08:34:44+02:00",  # Current time
            "overall_status": "healthy" if not errors else "unhealthy",
            "summary": {
                "total_variables": len(self.validation_results),
                "errors": len(errors),
                "warnings": len(warnings),
                "info": len(info),
            },
            "results": {
                "errors": [self._result_to_dict(r) for r in errors],
                "warnings": [self._result_to_dict(r) for r in warnings],
                "info": [self._result_to_dict(r) for r in info],
            },
        }

        if errors:
            logger.error(f"Environment validation failed: {len(errors)} errors found")
            for error in errors:
                logger.error(f"  - {error.variable}: {error.message}")
        elif warnings:
            logger.warning(f"Environment validation passed with {len(warnings)} warnings")

        return result

    def _validate_core_infrastructure(self, tier: EnvironmentTier) -> None:
        """Validate core infrastructure environment variables"""

        # Environment tier
        self._validate_required_var("ENVIRONMENT", tier)

        # OpenBao/Vault configuration
        if tier == EnvironmentTier.PRODUCTION:
            self._validate_openbao_config()
        else:
            self._validate_openbao_config(optional=True)

        # Database configuration
        self._validate_database_config(tier)

        # Redis configuration
        self._validate_redis_config(tier)

    def _validate_openbao_config(self, optional: bool = False) -> None:
        """Validate OpenBao/Vault configuration"""

        openbao_url = os.getenv("OPENBAO_URL")
        vault_token = os.getenv("VAULT_TOKEN")
        openbao_token = os.getenv("OPENBAO_TOKEN")

        if not optional and not any([openbao_url, vault_token, openbao_token]):
            self._add_result(
                "OPENBAO_CONFIG",
                False,
                ValidationSeverity.ERROR,
                "No OpenBao/Vault configuration found. Set OPENBAO_URL and token variables.",
            )
            return

        # Validate URL format if provided
        if openbao_url:
            if not openbao_url.startswith(("http://", "https://")):
                self._add_result(
                    "OPENBAO_URL",
                    False,
                    ValidationSeverity.ERROR,
                    "OPENBAO_URL must be a valid HTTP/HTTPS URL",
                )

        # Check for token
        effective_token = openbao_token or vault_token
        if not effective_token:
            severity = ValidationSeverity.WARNING if optional else ValidationSeverity.ERROR
            self._add_result(
                "OPENBAO_TOKEN",
                False,
                severity,
                "No OpenBao/Vault token found. Set OPENBAO_TOKEN or VAULT_TOKEN.",
            )
        elif len(effective_token) < 20:
            self._add_result(
                "OPENBAO_TOKEN",
                False,
                ValidationSeverity.WARNING,
                "Token appears to be too short. Ensure it's a valid token.",
            )

    def _validate_database_config(self, tier: EnvironmentTier) -> None:
        """Validate database configuration"""

        db_url = os.getenv("DATABASE_URL")

        if not db_url:
            severity = ValidationSeverity.ERROR if tier == EnvironmentTier.PRODUCTION else ValidationSeverity.WARNING
            self._add_result("DATABASE_URL", False, severity, "DATABASE_URL is not set")
            return

        # Check for SQLite in production
        if tier == EnvironmentTier.PRODUCTION and db_url.startswith("sqlite"):
            self._add_result(
                "DATABASE_URL",
                False,
                ValidationSeverity.ERROR,
                "SQLite is not suitable for production. Use PostgreSQL.",
            )

        # Validate PostgreSQL URL format
        if db_url.startswith("postgresql://"):
            # Basic URL validation
            if "@" not in db_url or "/" not in db_url.split("@")[1]:
                self._add_result(
                    "DATABASE_URL",
                    False,
                    ValidationSeverity.WARNING,
                    "DATABASE_URL format appears invalid for PostgreSQL",
                )

    def _validate_redis_config(self, tier: EnvironmentTier) -> None:
        """Validate Redis configuration"""

        redis_url = os.getenv("REDIS_URL")

        if not redis_url:
            severity = ValidationSeverity.ERROR if tier == EnvironmentTier.PRODUCTION else ValidationSeverity.WARNING
            self._add_result("REDIS_URL", False, severity, "REDIS_URL is not set")
            return

        if not redis_url.startswith(("redis://", "rediss://")):
            self._add_result(
                "REDIS_URL",
                False,
                ValidationSeverity.WARNING,
                "REDIS_URL should start with redis:// or rediss://",
            )

    def _validate_security_config(self, tier: EnvironmentTier) -> None:
        """Validate security-related configuration"""

        # JWT Secret
        jwt_secret = os.getenv("JWT_SECRET")
        if not jwt_secret:
            severity = ValidationSeverity.ERROR if tier == EnvironmentTier.PRODUCTION else ValidationSeverity.WARNING
            self._add_result("JWT_SECRET", False, severity, "JWT_SECRET is not set")
        elif tier == EnvironmentTier.PRODUCTION and len(jwt_secret) < 32:
            self._add_result(
                "JWT_SECRET",
                False,
                ValidationSeverity.WARNING,
                "JWT_SECRET should be at least 32 characters for production",
            )

        # CORS origins
        cors_origins = os.getenv("CORS_ORIGINS")
        if tier == EnvironmentTier.PRODUCTION and not cors_origins:
            self._add_result(
                "CORS_ORIGINS",
                False,
                ValidationSeverity.WARNING,
                "CORS_ORIGINS should be explicitly set in production",
            )

    def _validate_external_services(self, tier: EnvironmentTier) -> None:
        """Validate external service configurations"""

        # SMTP configuration (if email is enabled)
        if os.getenv("SMTP_HOST"):
            smtp_vars = ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD"]
            for var in smtp_vars:
                if not os.getenv(var):
                    self._add_result(
                        var,
                        False,
                        ValidationSeverity.WARNING,
                        f"{var} is set but {var} is missing",
                    )

        # Webhook secrets
        webhook_secret = os.getenv("WEBHOOK_SECRET")
        if tier == EnvironmentTier.PRODUCTION and not webhook_secret:
            self._add_result(
                "WEBHOOK_SECRET",
                False,
                ValidationSeverity.WARNING,
                "WEBHOOK_SECRET should be set for production webhooks",
            )

    def _validate_application_config(self, tier: EnvironmentTier) -> None:
        """Validate application-specific configuration"""

        # Admin configuration
        admin_email = os.getenv("ADMIN_EMAIL")
        if tier == EnvironmentTier.PRODUCTION and not admin_email:
            self._add_result(
                "ADMIN_EMAIL",
                False,
                ValidationSeverity.WARNING,
                "ADMIN_EMAIL should be set for production",
            )

        # Application version
        app_version = os.getenv("APP_VERSION", "1.0.0")
        if app_version == "1.0.0":
            self._add_result(
                "APP_VERSION",
                True,
                ValidationSeverity.INFO,
                "Consider setting APP_VERSION for better tracking",
                suggested_value="Set to current application version",
            )

        # Feature flags
        if tier == EnvironmentTier.PRODUCTION:
            strict_mode = os.getenv("STRICT_PROD_BASELINE", "false").lower() == "true"
            if not strict_mode:
                self._add_result(
                    "STRICT_PROD_BASELINE",
                    True,
                    ValidationSeverity.INFO,
                    "Consider enabling STRICT_PROD_BASELINE=true for enhanced production safety",
                )

    def _validate_required_var(self, var_name: str, tier: EnvironmentTier) -> None:
        """Validate a required environment variable"""

        value = os.getenv(var_name)
        if not value:
            severity = ValidationSeverity.ERROR if tier == EnvironmentTier.PRODUCTION else ValidationSeverity.WARNING
            self._add_result(var_name, False, severity, f"{var_name} is required but not set")
        else:
            self._add_result(
                var_name,
                True,
                ValidationSeverity.INFO,
                f"{var_name} is set",
                current_value="***" if "secret" in var_name.lower() else value,
            )

    def _add_result(
        self,
        variable: str,
        is_valid: bool,
        severity: ValidationSeverity,
        message: str,
        current_value: Optional[str] = None,
        suggested_value: Optional[str] = None,
    ) -> None:
        """Add a validation result"""

        result = ValidationResult(
            variable=variable,
            is_valid=is_valid,
            severity=severity,
            message=message,
            current_value=current_value,
            suggested_value=suggested_value,
        )
        self.validation_results.append(result)

    def _result_to_dict(self, result: ValidationResult) -> dict[str, Any]:
        """Convert validation result to dictionary"""
        return {
            "variable": result.variable,
            "is_valid": result.is_valid,
            "severity": result.severity,
            "message": result.message,
            "current_value": result.current_value,
            "suggested_value": result.suggested_value,
        }

    @staticmethod
    def validate_production_readiness() -> dict[str, Any]:
        """
        Quick production readiness check.
        Returns validation results for production deployment.
        """
        validator = EnvironmentValidator()
        return validator.validate_environment(EnvironmentTier.PRODUCTION)

    @staticmethod
    def get_missing_critical_vars() -> list[str]:
        """
        Get list of missing critical environment variables.
        """
        critical_vars = ["ENVIRONMENT", "DATABASE_URL", "REDIS_URL", "JWT_SECRET"]

        missing = []
        for var in critical_vars:
            if not os.getenv(var):
                missing.append(var)

        return missing


# Convenience functions for external use
def validate_environment_config(tier: str = "development") -> dict[str, Any]:
    """Validate environment configuration for the specified tier"""
    validator = EnvironmentValidator()
    return validator.validate_environment(EnvironmentTier(tier))


def check_production_readiness() -> dict[str, Any]:
    """Check if environment is ready for production deployment"""
    return EnvironmentValidator.validate_production_readiness()


def get_critical_missing_vars() -> list[str]:
    """Get list of missing critical environment variables"""
    return EnvironmentValidator.get_missing_critical_vars()
