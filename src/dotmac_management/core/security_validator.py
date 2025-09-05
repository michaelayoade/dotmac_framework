"""
Security validation utilities for configuration and runtime security checks.
"""

import re
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

from dotmac_shared.exceptions import ExceptionContext

from ..config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)


class SecurityValidator:
    """Validates security configuration and identifies potential issues."""

    @staticmethod
    def generate_secure_secret(length: int = 64) -> str:
        """Generate cryptographically secure secret key."""
        return secrets.token_urlsafe(length)

    @staticmethod
    def validate_secret_strength(secret: str, min_length: int = 32) -> dict[str, Any]:
        """Validate secret key strength and security."""
        issues = []
        recommendations = []

        # Length check
        if len(secret) < min_length:
            issues.append(
                f"Secret too short: {len(secret)} characters (minimum: {min_length})"
            )
            recommendations.append(f"Use secrets with at least {min_length} characters")

        # Pattern checks for common insecure values
        insecure_patterns = [
            (r"development|dev", "Contains 'development' or 'dev'"),
            (r"test|demo|example", "Contains testing/demo keywords"),
            (r"change|replace|update", "Contains placeholder language"),
            (r"secret|password|key", "Contains generic security terms"),
            (r"123|abc|qwerty", "Contains common weak patterns"),
            (r"^.{1,10}$", "Too short for secure use"),
        ]

        for pattern, description in insecure_patterns:
            if re.search(pattern, secret.lower()):
                issues.append(f"Insecure pattern: {description}")

        # Character diversity check
        char_types = [
            (r"[a-z]", "lowercase letters"),
            (r"[A-Z]", "uppercase letters"),
            (r"[0-9]", "numbers"),
            (r"[^a-zA-Z0-9]", "special characters"),
        ]

        missing_types = []
        for pattern, char_type in char_types:
            if not re.search(pattern, secret):
                missing_types.append(char_type)

        if missing_types:
            recommendations.append(f"Consider including: {', '.join(missing_types)}")

        return {
            "is_secure": len(issues) == 0,
            "strength_score": max(
                0, 100 - (len(issues) * 20) - (len(missing_types) * 5)
            ),
            "issues": issues,
            "recommendations": recommendations,
        }

    @staticmethod
    def validate_production_config() -> dict[str, Any]:
        """Comprehensive production configuration validation."""
        issues = []
        warnings = []
        recommendations = []

        # Environment check
        if not settings.is_production:
            warnings.append("Not running in production mode")

        # Secret validation
        secret_validation = SecurityValidator.validate_secret_strength(
            settings.secret_key
        )
        jwt_validation = SecurityValidator.validate_secret_strength(
            settings.jwt_secret_key
        )

        if not secret_validation["is_secure"]:
            issues.extend(
                [f"Secret key: {issue}" for issue in secret_validation["issues"]]
            )
            recommendations.extend(
                [f"Secret key: {rec}" for rec in secret_validation["recommendations"]]
            )

        if not jwt_validation["is_secure"]:
            issues.extend(
                [f"JWT secret: {issue}" for issue in jwt_validation["issues"]]
            )
            recommendations.extend(
                [f"JWT secret: {rec}" for rec in jwt_validation["recommendations"]]
            )

        # Same secrets check
        if settings.secret_key == settings.jwt_secret_key:
            issues.append("secret_key and jwt_secret_key must be different")

        # Network configuration checks
        if settings.is_production:
            # Database URL checks
            if (
                "localhost" in settings.database_url
                or "127.0.0.1" in settings.database_url
            ):
                issues.append("Production database should not use localhost")

            # Redis URL checks
            if "localhost" in settings.redis_url or "127.0.0.1" in settings.redis_url:
                issues.append("Production Redis should not use localhost")

            # CORS checks
            localhost_origins = [
                origin
                for origin in settings.cors_origins
                if "localhost" in origin or "127.0.0.1" in origin
            ]
            if localhost_origins:
                warnings.append(f"CORS includes localhost origins: {localhost_origins}")

            # SSL/TLS checks
            if any(
                "http://" in url
                for url in [settings.database_url, settings.redis_url]
                if url and not url.startswith("redis://")
            ):  # Redis uses redis:// scheme
                warnings.append("Consider using encrypted connections (https/ssl)")

        # External service configuration
        external_services = {
            "Stripe": settings.stripe_secret_key,
            "SendGrid": settings.sendgrid_api_key,
            "AWS": settings.aws_access_key_id,
            "Vault": settings.vault_token,
            "SignOz": settings.signoz_access_token,
        }

        missing_services = []
        placeholder_services = []

        for service, key in external_services.items():
            if not key:
                missing_services.append(service)
            elif key and (
                "placeholder" in key.lower()
                or "example" in key.lower()
                or "test" in key.lower()
                or len(key) < 10
            ):
                placeholder_services.append(service)

        if missing_services:
            warnings.append(
                f"Missing external service keys: {', '.join(missing_services)}"
            )

        if placeholder_services:
            issues.append(
                f"Placeholder/test keys found for: {', '.join(placeholder_services)}"
            )

        return {
            "is_secure": len(issues) == 0,
            "is_production_ready": len(issues) == 0 and settings.is_production,
            "issues": issues,
            "warnings": warnings,
            "recommendations": recommendations,
            "secret_strength": {
                "secret_key": secret_validation["strength_score"],
                "jwt_secret_key": jwt_validation["strength_score"],
            },
        }

    @staticmethod
    def create_secure_env_template() -> str:
        """Create a secure .env template with generated secrets."""
        secret_key = SecurityValidator.generate_secure_secret(64)
        jwt_secret_key = SecurityValidator.generate_secure_secret(64)

        template = f"""# DotMac Management Platform - Production Environment Configuration
# Generated on: {datetime.now().isoformat()}
# SECURITY: Keep this file secure and never commit to version control

# ==================== REQUIRED PRODUCTION SETTINGS ====================

# Environment Configuration
ENVIRONMENT=production
APP_NAME="DotMac Management Platform"
DEBUG=false
LOG_LEVEL=INFO
LOG_FORMAT=json

# Security Configuration (GENERATED - KEEP SECURE)
SECRET_KEY={secret_key}
JWT_SECRET_KEY={jwt_secret_key}
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database Configuration (REQUIRED)
DATABASE_URL=postgresql+asyncpg://username:password@database-host:5432/database_name
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40
DATABASE_ECHO=false

# Redis Configuration (REQUIRED)
REDIS_URL=redis://:password@redis-host:6379/0
REDIS_MAX_CONNECTIONS=100

# Background Tasks (REQUIRED)
CELERY_BROKER_URL=redis://:password@redis-host:6379/1
CELERY_RESULT_BACKEND=redis://:password@redis-host:6379/2
CELERY_WORKER_CONCURRENCY=8

# Server Configuration
HOST=0.0.0.0
PORT=8000
RELOAD=false

# Monitoring Configuration (REQUIRED)
SIGNOZ_ENDPOINT=your-signoz-endpoint:4317
SIGNOZ_ACCESS_TOKEN=your-signoz-token
ENABLE_METRICS=true

# ==================== EXTERNAL SERVICES (Configure as needed) ====================

# Stripe Payment Processing
STRIPE_SECRET_KEY=sk_live_your_stripe_secret_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
STRIPE_TEST_MODE=false

# Email Service (SendGrid)
SENDGRID_API_KEY=SG.your_sendgrid_api_key
SENDGRID_FROM_EMAIL=noreply@yourdomain.com

# AWS Configuration (for deployment automation)
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_REGION=us-east-1

# OpenBao/Vault (for secrets management)
VAULT_URL=https://your-vault-url:8200
VAULT_TOKEN=your_vault_token

# ==================== PRODUCTION NETWORK CONFIGURATION ====================

# CORS Origins (Update with your production domains)
CORS_ORIGINS=["https://admin.yourdomain.com","https://tenant.yourdomain.com","https://reseller.yourdomain.com"]

# Multi-tenant Configuration
ENABLE_TENANT_ISOLATION=true
MAX_TENANTS_PER_INSTANCE=1000
DEFAULT_TENANT_TIER=standard

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=1000

# Kubernetes Configuration (if using K8s deployment)
KUBERNETES_NAMESPACE_PREFIX=dotmac-tenant

# ==================== SECURITY NOTES ====================
# 1. All URLs should use HTTPS in production
# 2. Database and Redis should use SSL/TLS connections
# 3. Store this file securely and restrict access
# 4. Rotate secrets regularly
# 5. Monitor for unauthorized access
# 6. Use environment-specific service accounts
"""
        return template

    @staticmethod
    def validate_runtime_security() -> dict[str, Any]:
        """Validate runtime security configuration."""
        issues = []
        warnings = []

        try:
            # Check if configuration validation passes
            config_issues = settings.validate_production_security()
            if config_issues:
                issues.extend(config_issues)

            # Check file permissions if running in production
            if settings.is_production:
                env_files = [".env", ".env.production", ".env.local"]
                for env_file in env_files:
                    env_path = Path(env_file)
                    if env_path.exists():
                        stat = env_path.stat()
                        # Check if file is readable by others (security risk)
                        if stat.st_mode & 0o044:  # World or group readable
                            warnings.append(
                                f"Environment file {env_file} has overly permissive permissions"
                            )

        except ExceptionContext.FILE_EXCEPTIONS + (ValueError, AttributeError) as e:
            issues.append(f"Runtime security validation error: {str(e)}")

        return {
            "is_secure": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "timestamp": datetime.now().isoformat(),
        }


def startup_security_check():
    """Perform security validation during application startup."""
    logger.info("Performing startup security validation...")

    validation_result = SecurityValidator.validate_production_config()
    runtime_result = SecurityValidator.validate_runtime_security()

    # Log security status
    if validation_result["is_secure"] and runtime_result["is_secure"]:
        logger.info("✅ Security validation passed")
    else:
        logger.warning("⚠️ Security validation found issues")

        for issue in validation_result.get("issues", []):
            logger.error(f"Security issue: {issue}")

        for issue in runtime_result.get("issues", []):
            logger.error(f"Runtime security issue: {issue}")

    # Log warnings
    for warning in validation_result.get("warnings", []):
        logger.warning(f"Security warning: {warning}")

    for warning in runtime_result.get("warnings", []):
        logger.warning(f"Runtime warning: {warning}")

    # In production, fail startup if critical issues found
    if settings.is_production and not validation_result["is_secure"]:
        critical_issues = [
            issue
            for issue in validation_result["issues"]
            if "secret" in issue.lower() or "placeholder" in issue.lower()
        ]
        if critical_issues:
            logger.error("💥 Critical security issues prevent production startup")
            raise RuntimeError(
                f"Production startup blocked by security issues: {critical_issues}"
            )

    return {
        "config_validation": validation_result,
        "runtime_validation": runtime_result,
    }


# (imports consolidated at top)
