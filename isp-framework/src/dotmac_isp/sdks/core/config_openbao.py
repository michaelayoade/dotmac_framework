"""
Enhanced configuration with OpenBao integration.
Extends base configuration to retrieve secrets from OpenBao.
"""

import os
import logging
from typing import Optional, Dict, Any
from functools import cached_property

from .config_validator import BaseServiceConfig, Environment
from .openbao_client import OpenBaoClient, get_openbao_client

logger = logging.getLogger(__name__)


class OpenBaoConfig(BaseServiceConfig):
    """
    Enhanced configuration that retrieves secrets from OpenBao.
    Falls back to environment variables if OpenBao is unavailable.
    """

    # OpenBao configuration
    openbao_enabled: bool = True
    openbao_addr: Optional[str] = None
    openbao_role_id: Optional[str] = None
    openbao_secret_id: Optional[str] = None

    def __init__(self, **data):
        """Initialize configuration with OpenBao integration."""
        # Check if OpenBao is enabled
        self.openbao_enabled = os.getenv("OPENBAO_ENABLED", "true").lower() == "true"

        # Try to load secrets from OpenBao first
        if self.openbao_enabled:
            try:
                openbao_secrets = self._load_from_openbao()
                # Merge OpenBao secrets with environment (env takes precedence)
                for key, value in openbao_secrets.items():
                    if key not in os.environ:
                        os.environ[key] = str(value)
                logger.info("Successfully loaded secrets from OpenBao")
            except Exception as e:
                logger.warning(
                    f"Failed to load from OpenBao: {e}. Using environment variables."
                )

        # Initialize base configuration (will read from env vars)
        super().__init__(**data)

    @cached_property
    def openbao_client(self) -> Optional[OpenBaoClient]:
        """Get or create OpenBao client."""
        if not self.openbao_enabled:
            return None

        try:
            return get_openbao_client(self.service_name)
        except Exception as e:
            logger.error(f"Failed to create OpenBao client: {e}")
            return None

    def _load_from_openbao(self) -> Dict[str, Any]:
        """
        Load configuration from OpenBao.

        Returns:
            Dictionary of configuration values
        """
        secrets = {}

        try:
            # Get client
            client = get_openbao_client(self.service_name)

            # Get complete service configuration
            service_config = client.get_service_config()

            # Map OpenBao keys to environment variables
            mapping = {
                # Database
                "database_url": "DATABASE_URL",
                "database_pool_size": "DATABASE_POOL_SIZE",
                # Redis
                "redis_password": "REDIS_PASSWORD",
                "redis_max_connections": "REDIS_MAX_CONNECTIONS",
                # Security
                "service_key": "SECRET_KEY",
                "api_key": "API_KEY",
                "encryption_key": "ENCRYPTION_KEY",
                "jwt_secret_key": "JWT_SECRET_KEY",
                "jwt_algorithm": "JWT_ALGORITHM",
                "jwt_issuer": "JWT_ISSUER",
                "jwt_audience": "JWT_AUDIENCE",
                # Observability
                "signoz_endpoint": "SIGNOZ_ENDPOINT",
                "signoz_access_token": "SIGNOZ_ACCESS_TOKEN",
                "trace_sampling_rate": "TRACE_SAMPLING_RATE",
                # External services
                "stripe_secret_key": "STRIPE_SECRET_KEY",
                "sendgrid_api_key": "SENDGRID_API_KEY",
                "twilio_auth_token": "TWILIO_AUTH_TOKEN",
                "aws_access_key_id": "AWS_ACCESS_KEY_ID",
                "aws_secret_access_key": "AWS_SECRET_ACCESS_KEY",
            }

            for openbao_key, env_key in mapping.items():
                if openbao_key in service_config:
                    secrets[env_key] = service_config[openbao_key]

            # Get dynamic database credentials if not using static URL
            if not os.getenv("DATABASE_URL"):
                try:
                    db_creds = client.get_database_credentials()
                    db_host = os.getenv("DB_HOST", "postgres")
                    db_port = os.getenv("DB_PORT", "5432")
                    db_name = os.getenv("DB_NAME", f"dotmac_{self.service_name}")

                    secrets["DATABASE_URL"] = (
                        f"postgresql://{db_creds['username']}:{db_creds['password']}@"
                        f"{db_host}:{db_port}/{db_name}"
                    )

                    logger.info(
                        f"Using dynamic database credentials (TTL: {db_creds['ttl']}s)"
                    )
                except Exception as e:
                    logger.warning(f"Failed to get dynamic DB credentials: {e}")

            # Build Redis URL with password if available
            if "REDIS_PASSWORD" in secrets and not os.getenv("REDIS_URL"):
                redis_host = os.getenv("REDIS_HOST", "redis")
                redis_port = os.getenv("REDIS_PORT", "6379")
                redis_db = os.getenv("REDIS_DB", "0")
                secrets["REDIS_URL"] = (
                    f"redis://:{secrets['REDIS_PASSWORD']}@"
                    f"{redis_host}:{redis_port}/{redis_db}"
                )

            return secrets

        except Exception as e:
            logger.error(f"Error loading from OpenBao: {e}")
            raise

    def refresh_secrets(self) -> bool:
        """
        Refresh secrets from OpenBao.

        Returns:
            True if successful, False otherwise
        """
        if not self.openbao_client:
            return False

        try:
            secrets = self._load_from_openbao()

            # Update configuration attributes
            for env_key, value in secrets.items():
                # Convert env key to attribute name
                attr_name = env_key.lower()
                if hasattr(self, attr_name):
                    setattr(self, attr_name, value)

            logger.info("Successfully refreshed secrets from OpenBao")
            return True

        except Exception as e:
            logger.error(f"Failed to refresh secrets: {e}")
            return False

    def encrypt_field(self, value: str) -> str:
        """
        Encrypt a field value using OpenBao Transit.

        Args:
            value: Value to encrypt

        Returns:
            Encrypted ciphertext or original value if encryption fails
        """
        if not self.openbao_client:
            logger.warning("OpenBao not available, returning unencrypted value")
            return value

        try:
            return self.openbao_client.encrypt(value)
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return value

    def decrypt_field(self, ciphertext: str) -> str:
        """
        Decrypt a field value using OpenBao Transit.

        Args:
            ciphertext: Encrypted value

        Returns:
            Decrypted plaintext or original value if decryption fails
        """
        if not self.openbao_client:
            logger.warning("OpenBao not available, returning encrypted value")
            return ciphertext

        try:
            return self.openbao_client.decrypt(ciphertext)
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return ciphertext

    def get_external_api_key(self, service: str) -> Optional[str]:
        """
        Get an external API key from OpenBao.

        Args:
            service: External service name (e.g., 'stripe', 'sendgrid')

        Returns:
            API key or None if not found
        """
        if not self.openbao_client:
            # Fall back to environment
            return os.getenv(f"{service.upper()}_API_KEY")

        try:
            secret = self.openbao_client.get_secret("external")
            key_name = f"{service.lower()}_api_key"
            if key_name in secret.data:
                return secret.data[key_name]

            # Try alternative naming
            key_name = f"{service.lower()}_secret_key"
            if key_name in secret.data:
                return secret.data[key_name]

        except Exception as e:
            logger.warning(f"Failed to get API key for {service}: {e}")

        # Fall back to environment
        return os.getenv(f"{service.upper()}_API_KEY")

    def __del__(self):
        """Cleanup OpenBao client on deletion."""
        if hasattr(self, "openbao_client") and self.openbao_client:
            try:
                self.openbao_client.close()
            except Exception as e:
                logger.warning(f"Error closing OpenBao client: {e}")


def get_service_config(
    service_name: Optional[str] = None, use_openbao: bool = True
) -> OpenBaoConfig:
    """
    Get service configuration with OpenBao integration.

    Args:
        service_name: Service name
        use_openbao: Whether to use OpenBao for secrets

    Returns:
        Configuration instance
    """
    if service_name:
        os.environ["SERVICE_NAME"] = service_name

    if not use_openbao:
        os.environ["OPENBAO_ENABLED"] = "false"

    return OpenBaoConfig()


# Example service-specific configuration
class IdentityServiceConfig(OpenBaoConfig):
    """Configuration for Identity service with OpenBao integration."""

    # Identity-specific settings
    password_min_length: int = 8
    password_require_special: bool = True
    mfa_enabled: bool = True
    session_timeout: int = 3600
    max_login_attempts: int = 5

    def __init__(self, **data):
        """Initialize Identity service configuration."""
        # Set service name
        os.environ["SERVICE_NAME"] = "identity"
        super().__init__(**data)


class BillingServiceConfig(OpenBaoConfig):
    """Configuration for Billing service with OpenBao integration."""

    # Billing-specific settings
    stripe_webhook_secret: Optional[str] = None
    tax_calculation_enabled: bool = True
    invoice_prefix: str = "INV"
    payment_retry_attempts: int = 3

    def __init__(self, **data):
        """Initialize Billing service configuration."""
        # Set service name
        os.environ["SERVICE_NAME"] = "billing"
        super().__init__(**data)

        # Get Stripe webhook secret from OpenBao
        if self.openbao_client:
            try:
                secret = self.openbao_client.get_secret("billing")
                self.stripe_webhook_secret = secret.get("stripe_webhook_secret")
            except Exception as e:
                logger.warning(f"Could not load billing secrets: {e}")


# CLI for testing
if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Test OpenBao configuration")
    parser.add_argument("--service", default="test", help="Service name")
    parser.add_argument("--no-openbao", action="store_true", help="Disable OpenBao")
    parser.add_argument(
        "--validate", action="store_true", help="Validate configuration"
    )
    parser.add_argument("--refresh", action="store_true", help="Refresh secrets")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Get configuration
    config = get_service_config(
        service_name=args.service, use_openbao=not args.no_openbao
    )

    print(f"\nConfiguration for {config.service_name}:")
    print(f"  Environment: {config.environment}")
    print(f"  OpenBao enabled: {config.openbao_enabled}")

    if args.validate:
        result = config.validate_all()
        print(f"\n  Validation: {'✓ PASS' if result.is_valid else '✗ FAIL'}")
        if result.errors:
            print("  Errors:")
            for error in result.errors:
                print(f"    - {error}")
        if result.warnings:
            print("  Warnings:")
            for warning in result.warnings:
                print(f"    - {warning}")

    if args.refresh and config.openbao_enabled:
        success = config.refresh_secrets()
        print(f"\n  Secret refresh: {'✓ SUCCESS' if success else '✗ FAILED'}")

    # Display configuration (redacted)
    print("\n  Settings:")
    for key, value in config.dict().items():
        if any(s in key.lower() for s in ["secret", "key", "password", "token"]):
            print(f"    {key}: ***REDACTED***")
        else:
            print(f"    {key}: {value}")
