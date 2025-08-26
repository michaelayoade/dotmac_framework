"""
Enhanced settings with integrated security features.
Replaces the original settings.py with comprehensive security management.
"""

import os
import logging
from functools import lru_cache
from typing import Optional, Dict, Any
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .secrets_manager import get_secrets_manager, SecretType
from .config_encryption import get_config_encryption
from .config_audit import get_config_audit, ChangeType, ChangeSource
from .config_backup import get_config_backup, BackupType
from .config_hotreload import get_config_hotreload
from .secure_config_validator import get_secure_validator, ComplianceFramework

logger = logging.getLogger(__name__)


class EnhancedSettings(BaseSettings):
    """
    Enhanced application settings with integrated security features.
    Provides secure configuration management with encryption, audit trails, and validation.
    """

    model_config = SettingsConfigDict(
        env_file=[".env", ".env.local"],
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Core application settings
    app_name: str = "DotMac ISP Framework"
    app_version: str = "1.0.0"

    # Environment configuration with strict validation
    environment: str = Field(
        default="development",
        pattern="^(development|staging|production)$",
        description="Deployment environment - must be development, staging, or production",
    )

    # Security-first debug configuration
    debug: bool = Field(
        default=False, description="Debug mode - automatically disabled in production"
    )

    # Server configuration
    host: str = Field(
        default="127.0.0.1",  # More secure default
        description="Host to bind - use 127.0.0.1 for local, 0.0.0.0 for external",
    )
    port: int = Field(default=8000, ge=1, le=65535, description="Port to bind")

    # API configuration with environment awareness
    api_v1_prefix: str = "/api/v1"
    docs_url: Optional[str] = Field(
        default="/docs",
        description="API docs URL - disabled in production for security",
    )
    redoc_url: Optional[str] = Field(
        default="/redoc", description="ReDoc URL - disabled in production for security"
    )
    openapi_url: Optional[str] = Field(
        default="/openapi.json",
        description="OpenAPI spec URL - disabled in production for security",
    )

    # Database configuration with security validation
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/dotmac_isp",
        description="Primary database URL - must use SSL in production",
    )
    async_database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/dotmac_isp",
        description="Async database URL - must use SSL in production",
    )

    # Redis configuration
    redis_url: str = Field(
        default="redis://localhost:6379/0", description="Redis connection URL"
    )

    # Enhanced security configuration
    secret_key: str = Field(
        default="",  # Will be loaded from secrets manager
        min_length=32,
        description="Application secret key - loaded from secure storage",
    )
    jwt_secret_key: str = Field(
        default="",  # Will be loaded from secrets manager
        min_length=32,
        description="JWT secret key - loaded from secure storage",
    )
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # CORS configuration with strict defaults
    cors_origins: str = Field(
        default="http://localhost:3000",  # Single localhost only
        description="Allowed CORS origins (comma-separated)",
    )

    # Trusted hosts configuration
    allowed_hosts: str = Field(
        default="localhost,127.0.0.1",
        description="Allowed host headers (comma-separated)",
    )

    # External service configuration
    smtp_server: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_tls: bool = True
    from_email: Optional[str] = None

    # Twilio configuration
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_phone_number: Optional[str] = None

    # Stripe configuration
    stripe_publishable_key: Optional[str] = None
    stripe_secret_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None

    # Celery configuration
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Logging configuration
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # File upload configuration
    max_upload_size: int = 10 * 1024 * 1024  # 10MB
    upload_directory: str = "uploads"

    # Pagination configuration
    default_page_size: int = 20
    max_page_size: int = 100

    # Rate limiting configuration
    rate_limit_per_minute: int = 60  # More conservative default

    # SSL/TLS configuration
    ssl_enabled: bool = Field(
        default=False, description="Enable HTTPS with SSL certificates"
    )
    ssl_email: Optional[str] = None
    ssl_domains: str = ""
    ssl_cert_dir: str = "/etc/ssl/dotmac"

    # Multi-tenancy configuration
    enable_multi_tenancy: bool = True
    tenant_id: str = "00000000-0000-0000-0000-000000000001"

    # Portal ID configuration
    portal_id_pattern: str = "alphanumeric_clean"
    portal_id_length: int = Field(default=8, ge=4, le=20)
    portal_id_prefix: str = Field(default="", max_length=5)
    portal_id_custom_charset: str = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    portal_id_exclude_ambiguous: bool = True

    # Enterprise backend integrations
    minio_endpoint: str = "localhost:9002"
    minio_access_key: str = "dotmacadmin"
    minio_secret_key: str = "dotmacpassword"
    minio_secure: bool = False
    minio_default_bucket: str = "dotmac-isp-storage"

    # SignOz observability
    signoz_endpoint: str = "localhost:4317"
    signoz_access_token: Optional[str] = None
    enable_observability: bool = True

    # OpenBao secrets management
    openbao_url: str = "http://localhost:8200"
    openbao_token: Optional[str] = None
    enable_secrets_management: bool = True

    # Event bus configuration
    enable_event_bus: bool = True
    event_bus_prefix: str = "dotmac:events"

    # API gateway configuration
    enable_rate_limiting: bool = True
    default_rate_limit: int = 100

    # Security enhancement features
    enable_config_encryption: bool = Field(
        default=True, description="Enable configuration encryption for sensitive data"
    )
    enable_config_audit: bool = Field(
        default=True, description="Enable configuration audit logging"
    )
    enable_config_backup: bool = Field(
        default=True, description="Enable automated configuration backups"
    )
    enable_hot_reload: bool = Field(
        default=True, description="Enable configuration hot-reloading"
    )

    # Compliance configuration
    compliance_frameworks: str = Field(
        default="soc2,iso27001",
        description="Comma-separated list of compliance frameworks to enforce",
    )

    # Internal state (not loaded from environment)
    _secrets_loaded: bool = False
    _security_validated: bool = False
    _config_managers_initialized: bool = False

    def __init__(self, **kwargs):
        """Initialize enhanced settings with security features."""
        super().__init__(**kwargs)

        # Initialize security managers
        self._initialize_security_managers()

        # Load secrets from secure storage
        self._load_secrets_from_secure_storage()

        # Validate security configuration
        self._validate_security_configuration()

        # Create initial backup
        self._create_initial_backup()

        # Log configuration load
        self._log_configuration_load()

    def _initialize_security_managers(self):
        """Initialize security management components."""
        try:
            if self.enable_secrets_management:
                # Initialize secrets manager
                from .secrets_manager import init_secrets_manager

                init_secrets_manager(
                    backend="openbao" if self.openbao_token else "local",
                    openbao_url=self.openbao_url,
                    openbao_token=self.openbao_token,
                )

            if self.enable_config_encryption:
                # Initialize config encryption
                from .config_encryption import init_config_encryption

                init_config_encryption(
                    master_key=os.getenv("CONFIG_MASTER_KEY"), key_rotation_enabled=True
                )

            if self.enable_config_audit:
                # Initialize config audit
                from .config_audit import init_config_audit

                init_config_audit(
                    require_approval=self.environment == "production",
                    encryption_enabled=self.enable_config_encryption,
                )

            if self.enable_config_backup:
                # Initialize config backup
                from .config_backup import init_config_backup

                init_config_backup(encryption_key=os.getenv("BACKUP_ENCRYPTION_KEY"))

            if self.enable_hot_reload:
                # Initialize hot reload (will be configured by application)
                pass

            self._config_managers_initialized = True
            logger.info("Security managers initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize security managers: {e}")
            if self.environment == "production":
                raise  # Fail fast in production

    def _load_secrets_from_secure_storage(self):
        """Load sensitive configuration from secure storage."""
        if not self.enable_secrets_management:
            return

        try:
            secrets_manager = get_secrets_manager()

            # Load JWT secret key
            if not self.jwt_secret_key:
                jwt_secret = secrets_manager.get_secret("jwt_secret_key")
                if jwt_secret:
                    self.jwt_secret_key = jwt_secret.value
                elif self.environment == "production":
                    raise ValueError("JWT secret key not found in secure storage")

            # Load application secret key
            if not self.secret_key:
                app_secret = secrets_manager.get_secret("app_secret_key")
                if app_secret:
                    self.secret_key = app_secret.value
                elif self.environment == "production":
                    raise ValueError(
                        "Application secret key not found in secure storage"
                    )

            # Load database credentials from secrets if URL doesn't contain them
            if self.database_url and "@" not in self.database_url:
                db_password = secrets_manager.get_secret("database_password")
                if db_password:
                    # Update database URLs with secure credentials
                    self.database_url = self.database_url.replace(
                        "postgres:postgres@", f"postgres:{db_password.value}@"
                    )
                    self.async_database_url = self.async_database_url.replace(
                        "postgres:postgres@", f"postgres:{db_password.value}@"
                    )

            self._secrets_loaded = True
            logger.info("Secrets loaded from secure storage")

        except Exception as e:
            logger.error(f"Failed to load secrets from secure storage: {e}")
            if self.environment == "production":
                raise

    def _validate_security_configuration(self):
        """Validate configuration using secure validator."""
        try:
            validator = get_secure_validator()

            # Get compliance frameworks
            frameworks = []
            if self.compliance_frameworks:
                framework_names = [
                    f.strip() for f in self.compliance_frameworks.split(",")
                ]
                frameworks = [
                    ComplianceFramework(name) for name in framework_names if name
                ]

            # Validate configuration
            config_dict = self.model_dump()
            result = validator.validate_configuration(
                config=config_dict,
                environment=self.environment,
                service="core",
                compliance_frameworks=frameworks,
            )

            # Handle validation results
            if not result.is_valid:
                error_msg = f"Configuration validation failed with {len(result.critical_issues)} critical and {len(result.error_issues)} error issues"
                logger.error(error_msg)

                # Log critical issues
                for issue in result.critical_issues:
                    logger.critical(f"CRITICAL: {issue.field_path} - {issue.message}")

                # Log error issues
                for issue in result.error_issues:
                    logger.error(f"ERROR: {issue.field_path} - {issue.message}")

                if self.environment == "production":
                    raise ValueError(error_msg)

            # Log warnings
            for issue in result.warning_issues:
                logger.warning(f"WARNING: {issue.field_path} - {issue.message}")

            self._security_validated = True
            logger.info(
                f"Security validation passed (score: {result.security_score:.1f}/100)"
            )

        except Exception as e:
            logger.error(f"Security validation failed: {e}")
            if self.environment == "production":
                raise

    def _create_initial_backup(self):
        """Create initial configuration backup."""
        if not self.enable_config_backup:
            return

        try:
            backup_manager = get_config_backup()
            config_dict = self.model_dump()

            backup_id = backup_manager.create_backup(
                config_data=config_dict,
                backup_type=BackupType.SNAPSHOT,
                environments=[self.environment],
                services=["core"],
                tags=["initial", "startup"],
                created_by="system",
            )

            logger.info(f"Initial configuration backup created: {backup_id}")

        except Exception as e:
            logger.warning(f"Failed to create initial backup: {e}")

    def _log_configuration_load(self):
        """Log configuration load event."""
        if not self.enable_config_audit:
            return

        try:
            audit = get_config_audit()

            audit.log_configuration_change(
                field_path="__system_startup__",
                old_value=None,
                new_value="configuration_loaded",
                change_type=ChangeType.ACCESS,
                source=ChangeSource.SYSTEM,
                environment=self.environment,
                service="core",
                change_reason="Application startup configuration load",
            )

        except Exception as e:
            logger.warning(f"Failed to log configuration load: {e}")

    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as a list."""
        return [
            origin.strip() for origin in self.cors_origins.split(",") if origin.strip()
        ]

    @property
    def allowed_hosts_list(self) -> list[str]:
        """Get allowed hosts as a list."""
        return [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]

    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL."""
        return self.database_url.replace("+asyncpg", "").replace("+aiomysql", "")

    @property
    def compliance_frameworks_list(self) -> list[str]:
        """Get compliance frameworks as a list."""
        return [
            fw.strip() for fw in self.compliance_frameworks.split(",") if fw.strip()
        ]

    @model_validator(mode="after")
    def validate_environment_security(self):
        """Validate environment-specific security settings."""
        # Production security validation
        if self.environment == "production":
            errors = []

            # Debug mode must be False
            if self.debug:
                errors.append("DEBUG mode MUST be False in production")

            # API documentation must be disabled
            if self.docs_url or self.redoc_url or self.openapi_url:
                logger.warning(
                    "API documentation endpoints enabled in production - consider disabling"
                )
                # Auto-disable in production
                self.docs_url = None
                self.redoc_url = None
                self.openapi_url = None

            # CORS origins must not be localhost
            if any(
                host in self.cors_origins.lower() for host in ["localhost", "127.0.0.1"]
            ):
                errors.append("CORS origins must not include localhost in production")

            # Allowed hosts must not be localhost only
            if self.allowed_hosts == "localhost,127.0.0.1":
                errors.append("Allowed hosts must be configured for production domains")

            # SSL should be enabled
            if not self.ssl_enabled:
                logger.warning("SSL is not enabled in production")

            # Rate limiting should be enabled
            if not self.enable_rate_limiting:
                logger.warning("Rate limiting is disabled in production")

            if errors:
                error_msg = "CRITICAL PRODUCTION SECURITY ISSUES:\n" + "\n".join(
                    f"- {error}" for error in errors
                )
                logger.critical(error_msg)
                raise ValueError(error_msg)

        # Staging environment warnings
        elif self.environment == "staging":
            if self.debug:
                logger.warning("Debug mode enabled in staging environment")

        return self

    @field_validator("jwt_secret_key", "secret_key")
    @classmethod
    def validate_secret_keys(cls, v: str, info) -> str:
        """Validate secret key strength."""
        field_name = info.field_name

        if not v:
            # Will be loaded from secrets manager, so this is acceptable
            return v

        if len(v) < 32:
            raise ValueError(f"{field_name} must be at least 32 characters long")

        # Check for weak secrets
        weak_patterns = ["secret", "change", "test", "demo", "default", "password"]
        if any(pattern in v.lower() for pattern in weak_patterns):
            logger.warning(f"Potentially weak {field_name} detected")

        return v

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment setting."""
        valid_environments = ["development", "staging", "production"]
        if v not in valid_environments:
            raise ValueError(
                f"Environment must be one of: {', '.join(valid_environments)}"
            )
        return v

    def update_setting(
        self,
        field_path: str,
        new_value: Any,
        user_id: Optional[str] = None,
        change_reason: Optional[str] = None,
    ) -> bool:
        """
        Securely update a configuration setting with audit trail.

        Args:
            field_path: Path to the setting (e.g., 'debug', 'cors_origins')
            new_value: New value for the setting
            user_id: User making the change
            change_reason: Reason for the change

        Returns:
            True if update was successful
        """
        if not self.enable_config_audit:
            # Direct update without audit
            setattr(self, field_path, new_value)
            return True

        try:
            # Get current value
            old_value = getattr(self, field_path, None)

            # Log the change
            audit = get_config_audit()
            event_id = audit.log_configuration_change(
                field_path=field_path,
                old_value=old_value,
                new_value=new_value,
                change_type=ChangeType.UPDATE,
                source=ChangeSource.API if user_id else ChangeSource.SYSTEM,
                environment=self.environment,
                user_id=user_id,
                service="core",
                change_reason=change_reason,
            )

            # Apply the change (if not requiring approval)
            if not audit.require_approval or self.environment != "production":
                setattr(self, field_path, new_value)
                logger.info(f"Configuration updated: {field_path} (event: {event_id})")
                return True
            else:
                logger.info(
                    f"Configuration change pending approval: {field_path} (event: {event_id})"
                )
                return False

        except Exception as e:
            logger.error(f"Failed to update configuration {field_path}: {e}")
            return False

    def get_security_status(self) -> Dict[str, Any]:
        """Get security status of configuration."""
        return {
            "secrets_loaded": self._secrets_loaded,
            "security_validated": self._security_validated,
            "managers_initialized": self._config_managers_initialized,
            "environment": self.environment,
            "ssl_enabled": self.ssl_enabled,
            "debug_mode": self.debug,
            "secrets_management_enabled": self.enable_secrets_management,
            "config_encryption_enabled": self.enable_config_encryption,
            "config_audit_enabled": self.enable_config_audit,
            "config_backup_enabled": self.enable_config_backup,
            "hot_reload_enabled": self.enable_hot_reload,
            "compliance_frameworks": self.compliance_frameworks_list,
        }


@lru_cache()
def get_enhanced_settings() -> EnhancedSettings:
    """Get cached enhanced application settings."""
    return EnhancedSettings()


# Backwards compatibility
def get_settings() -> EnhancedSettings:
    """Get enhanced settings (backwards compatible)."""
    return get_enhanced_settings()


# Export for easy import
Settings = EnhancedSettings
