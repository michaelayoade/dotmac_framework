"""
Security validation for environment variables and configuration.
"""

import os
import re
import secrets
from typing import Any, Dict, List

import structlog

logger = structlog.get_logger(__name__)


class SecurityValidationError(Exception):
    """Security validation error."""
    pass


class EnvironmentSecurityValidator:
    """Validator for security-critical environment variables."""

    # Weak/default secrets that should not be used in production
    WEAK_SECRETS = {
        "secret",
        "password",
        "your-secret-key",
        "your-password",
        "changeme",
        "admin",
        "test",
        "dev",
        "development",
        "localhost",
        "example",
        "demo",
        "default",
        "123456",
        "password123",
        "<REPLACE_WITH_STRONG_RANDOM_SECRET>",
        "<REPLACE_WITH_REDIS_PASSWORD>",
    }

    def __init__(self, production_mode: bool = False):
        self.production_mode = production_mode
        self.warnings: List[str] = []
        self.errors: List[str] = []

    def validate_all(self) -> Dict[str, Any]:
        """
        Validate all security-critical configuration.

        Returns:
            Validation results with warnings and errors

        Raises:
            SecurityValidationError: If critical security issues found
        """
        self.warnings.clear()
        self.errors.clear()

        # Validate JWT configuration
        self._validate_jwt_config()

        # Validate CORS configuration
        self._validate_cors_config()

        # Validate database configuration
        self._validate_database_config()

        # Validate adapter configurations
        self._validate_adapter_configs()

        # Production-specific validations
        if self.production_mode:
            self._validate_production_security()

        results = {
            "warnings": self.warnings,
            "errors": self.errors,
            "passed": len(self.errors) == 0
        }

        if self.errors:
            error_msg = "Critical security validation failures:\n" + "\n".join(f"- {e}" for e in self.errors)
            raise SecurityValidationError(error_msg)

        if self.warnings:
            logger.warning("Security validation warnings", warnings=self.warnings)

        return results

    def _validate_jwt_config(self):
        """Validate JWT configuration."""
        jwt_secret = os.getenv("JWT_SECRET_KEY")

        if not jwt_secret:
            self.errors.append("JWT_SECRET_KEY environment variable is not set")
            return

        # Check for weak/default secrets
        if jwt_secret.lower() in self.WEAK_SECRETS:
            self.errors.append(f"JWT_SECRET_KEY uses a weak/default value: {jwt_secret}")
            return

        # Check minimum length
        if len(jwt_secret) < 32:
            self.errors.append(f"JWT_SECRET_KEY is too short ({len(jwt_secret)} chars). Minimum 32 characters required.")

        # Check if it looks like a proper random secret
        if not self._is_strong_secret(jwt_secret):
            self.warnings.append("JWT_SECRET_KEY doesn't appear to be randomly generated")

        # Check algorithm
        algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        if algorithm not in ["HS256", "HS384", "HS512"]:
            self.errors.append(f"JWT_ALGORITHM '{algorithm}' is not a secure HMAC algorithm")

    def _validate_cors_config(self):
        """Validate CORS configuration."""
        cors_origins = os.getenv("CORS_ORIGINS", "")

        if not cors_origins:
            if self.production_mode:
                self.warnings.append("CORS_ORIGINS not configured - CORS will be disabled")
            return

        origins = [origin.strip() for origin in cors_origins.split(",")]

        # Check for dangerous wildcard
        if "*" in origins:
            self.errors.append("CORS_ORIGINS contains wildcard '*' which is insecure")

        # Check for localhost/development origins in production
        if self.production_mode:
            dev_origins = [o for o in origins if "localhost" in o or "127.0.0.1" in o]
            if dev_origins:
                self.warnings.append(f"CORS_ORIGINS contains development origins in production: {dev_origins}")

        # Check for HTTP origins
        http_origins = [o for o in origins if o.startswith("http://")]
        if http_origins:
            self.warnings.append(f"CORS_ORIGINS contains insecure HTTP origins: {http_origins}")

    def _validate_database_config(self):
        """Validate database configuration."""
        db_url = os.getenv("DATABASE_URL")

        if not db_url:
            return  # Database is optional

        # Check for weak passwords in URL
        if any(weak in db_url.lower() for weak in self.WEAK_SECRETS):
            self.errors.append("DATABASE_URL contains weak/default credentials")

        # Check for HTTP instead of encrypted connection
        if db_url.startswith("postgresql://") and not db_url.startswith("postgresql+asyncpg://"):
            self.warnings.append("DATABASE_URL should use asyncpg driver for better security")

        # Check for localhost in production
        if self.production_mode and ("localhost" in db_url or "127.0.0.1" in db_url):
            self.warnings.append("DATABASE_URL points to localhost in production")

    def _validate_adapter_configs(self):
        """Validate event adapter configurations."""
        adapter_type = os.getenv("ADAPTER_TYPE", "memory")

        if adapter_type == "redis":
            self._validate_redis_config()
        elif adapter_type == "kafka":
            self._validate_kafka_config()

    def _validate_redis_config(self):
        """Validate Redis configuration."""
        password = os.getenv("REDIS_PASSWORD")

        if not password:
            self.warnings.append("REDIS_PASSWORD not set - Redis authentication disabled")
        elif password.lower() in self.WEAK_SECRETS:
            self.errors.append(f"REDIS_PASSWORD uses weak/default value: {password}")
        elif len(password) < 16:
            self.warnings.append(f"REDIS_PASSWORD is short ({len(password)} chars). Consider 16+ characters.")

        # Check SSL
        ssl_enabled = os.getenv("REDIS_SSL", "false").lower() == "true"
        if self.production_mode and not ssl_enabled:
            self.warnings.append("REDIS_SSL is disabled in production")

        # Check host
        host = os.getenv("REDIS_HOST", "localhost")
        if self.production_mode and host in ["localhost", "127.0.0.1"]:
            self.warnings.append("REDIS_HOST points to localhost in production")

    def _validate_kafka_config(self):
        """Validate Kafka configuration."""
        username = os.getenv("KAFKA_SASL_USERNAME")
        password = os.getenv("KAFKA_SASL_PASSWORD")

        if not username or not password:
            self.warnings.append("Kafka SASL credentials not configured")
        else:
            if username.lower() in self.WEAK_SECRETS:
                self.errors.append(f"KAFKA_SASL_USERNAME uses weak value: {username}")

            if password.lower() in self.WEAK_SECRETS:
                self.errors.append("KAFKA_SASL_PASSWORD uses weak/default value")
            elif len(password) < 16:
                self.warnings.append("KAFKA_SASL_PASSWORD is short. Consider 16+ characters.")

        # Check security protocol
        security_protocol = os.getenv("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT")
        if self.production_mode and security_protocol == "PLAINTEXT":
            self.warnings.append("KAFKA_SECURITY_PROTOCOL is PLAINTEXT in production")

    def _validate_production_security(self):
        """Additional validations for production environments."""
        # Check debug mode
        debug = os.getenv("DEBUG", "false").lower() == "true"
        if debug:
            self.errors.append("DEBUG mode is enabled in production")

        # Check if running on default ports
        port = int(os.getenv("PORT", "8000"))
        if port in [8000, 8080, 3000]:
            self.warnings.append(f"Running on common development port {port} in production")

        # Check for missing TLS configuration
        # Note: TLS is typically handled by reverse proxy, but we can warn
        self.warnings.append("Ensure TLS/HTTPS is configured at the load balancer/proxy level")

    def _is_strong_secret(self, secret: str) -> bool:
        """Check if secret appears to be randomly generated."""
        if len(secret) < 16:
            return False

        # Check for variety in characters
        has_upper = any(c.isupper() for c in secret)
        has_lower = any(c.islower() for c in secret)
        has_digit = any(c.isdigit() for c in secret)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in secret)

        # Should have at least 3 types of characters
        variety_count = sum([has_upper, has_lower, has_digit, has_special])

        # Check for common patterns
        common_patterns = [
            r"(.)\1{3,}",  # Repeated characters
            r"123|abc|xyz",  # Sequential characters
            r"qwerty|password|secret",  # Common words
        ]

        for pattern in common_patterns:
            if re.search(pattern, secret.lower()):
                return False

        return variety_count >= 3

    def generate_secure_secret(self, length: int = 32) -> str:
        """Generate a cryptographically secure random secret."""
        return secrets.token_hex(length)

    def generate_jwt_secret(self) -> str:
        """Generate a secure JWT secret."""
        return self.generate_secure_secret(32)


def validate_environment_security(production_mode: bool = None) -> Dict[str, Any]:
    """
    Validate environment security configuration.

    Args:
        production_mode: Whether to apply production-specific validations.
                        If None, auto-detect based on environment.

    Returns:
        Validation results

    Raises:
        SecurityValidationError: If critical issues found
    """
    if production_mode is None:
        # Auto-detect production mode
        production_mode = (
            os.getenv("DEBUG", "false").lower() != "true" and
            os.getenv("ENVIRONMENT", "development").lower() in ["production", "prod", "live"]
        )

    validator = EnvironmentSecurityValidator(production_mode=production_mode)
    return validator.validate_all()


def log_security_warnings():
    """Log security warnings without failing."""
    try:
        results = validate_environment_security()
        if results["warnings"]:
            logger.warning("Security validation completed with warnings",
                         warnings=results["warnings"])
        else:
            logger.info("Security validation passed")
    except SecurityValidationError as e:
        logger.error("Critical security validation failures", error=str(e))
        raise
    except Exception as e:
        logger.error("Security validation error", error=str(e))


if __name__ == "__main__":
    # CLI tool for security validation
    import sys

    try:
        production = "--production" in sys.argv
        results = validate_environment_security(production_mode=production)

        if results["warnings"]:
            print("⚠️  Security Warnings:")
            for warning in results["warnings"]:
                print(f"  - {warning}")
            print()

        print("✅ Security validation passed")

        if "--generate-secrets" in sys.argv:
            validator = EnvironmentSecurityValidator()
            print("\n🔐 Generated secure secrets:")
            print(f"JWT_SECRET_KEY={validator.generate_jwt_secret()}")
            print(f"REDIS_PASSWORD={validator.generate_secure_secret(24)}")
            print(f"KAFKA_SASL_PASSWORD={validator.generate_secure_secret(24)}")

    except SecurityValidationError as e:
        print(f"❌ Security validation failed:\n{e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Validation error: {e}")
        sys.exit(1)
