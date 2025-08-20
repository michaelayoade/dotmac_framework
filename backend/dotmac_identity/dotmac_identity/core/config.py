"""
Configuration management for DotMac Identity.
"""

import os
from dataclasses import dataclass, field


@dataclass
class DatabaseConfig:
    """Database configuration."""
    url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///identity.db"))
    pool_size: int = field(default_factory=lambda: int(os.getenv("DB_POOL_SIZE", "10")))
    max_overflow: int = field(default_factory=lambda: int(os.getenv("DB_MAX_OVERFLOW", "20")))
    pool_timeout: int = field(default_factory=lambda: int(os.getenv("DB_POOL_TIMEOUT", "30")))
    pool_recycle: int = field(default_factory=lambda: int(os.getenv("DB_POOL_RECYCLE", "3600")))
    echo: bool = field(default_factory=lambda: os.getenv("DB_ECHO", "false").lower() == "true")


@dataclass
class CacheConfig:
    """Cache configuration."""
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379"))
    default_ttl: int = field(default_factory=lambda: int(os.getenv("CACHE_DEFAULT_TTL", "3600")))
    key_prefix: str = field(default_factory=lambda: os.getenv("CACHE_KEY_PREFIX", "identity:"))


@dataclass
class SecurityConfig:
    """Security configuration."""
    secret_key: str = field(default_factory=lambda: os.getenv("SECRET_KEY", "dev-secret-key"))
    encryption_key: str = field(default_factory=lambda: os.getenv("ENCRYPTION_KEY", "dev-encryption-key"))
    jwt_secret: str = field(default_factory=lambda: os.getenv("JWT_SECRET", "jwt-secret"))
    jwt_algorithm: str = field(default_factory=lambda: os.getenv("JWT_ALGORITHM", "HS256"))
    jwt_expiration: int = field(default_factory=lambda: int(os.getenv("JWT_EXPIRATION", "3600")))
    password_min_length: int = field(default_factory=lambda: int(os.getenv("PASSWORD_MIN_LENGTH", "8")))
    mfa_issuer: str = field(default_factory=lambda: os.getenv("MFA_ISSUER", "DotMac Identity"))


@dataclass
class VerificationConfig:
    """Verification configuration."""
    email_verification_ttl: int = field(default_factory=lambda: int(os.getenv("EMAIL_VERIFICATION_TTL", "3600")))
    phone_verification_ttl: int = field(default_factory=lambda: int(os.getenv("PHONE_VERIFICATION_TTL", "300")))
    otp_length: int = field(default_factory=lambda: int(os.getenv("OTP_LENGTH", "6")))
    max_verification_attempts: int = field(default_factory=lambda: int(os.getenv("MAX_VERIFICATION_ATTEMPTS", "3")))


@dataclass
class NotificationConfig:
    """Notification configuration."""
    email_provider: str = field(default_factory=lambda: os.getenv("EMAIL_PROVIDER", "smtp"))
    smtp_host: str = field(default_factory=lambda: os.getenv("SMTP_HOST", "localhost"))
    smtp_port: int = field(default_factory=lambda: int(os.getenv("SMTP_PORT", "587")))
    smtp_username: str = field(default_factory=lambda: os.getenv("SMTP_USERNAME", ""))
    smtp_password: str = field(default_factory=lambda: os.getenv("SMTP_PASSWORD", ""))
    smtp_use_tls: bool = field(default_factory=lambda: os.getenv("SMTP_USE_TLS", "true").lower() == "true")

    sms_provider: str = field(default_factory=lambda: os.getenv("SMS_PROVIDER", "twilio"))
    twilio_account_sid: str = field(default_factory=lambda: os.getenv("TWILIO_ACCOUNT_SID", ""))
    twilio_auth_token: str = field(default_factory=lambda: os.getenv("TWILIO_AUTH_TOKEN", ""))
    twilio_from_number: str = field(default_factory=lambda: os.getenv("TWILIO_FROM_NUMBER", ""))


@dataclass
class ComplianceConfig:
    """Compliance configuration."""
    gdpr_enabled: bool = field(default_factory=lambda: os.getenv("GDPR_ENABLED", "true").lower() == "true")
    ccpa_enabled: bool = field(default_factory=lambda: os.getenv("CCPA_ENABLED", "true").lower() == "true")
    data_retention_days: int = field(default_factory=lambda: int(os.getenv("DATA_RETENTION_DAYS", "2555")))  # 7 years
    audit_log_retention_days: int = field(default_factory=lambda: int(os.getenv("AUDIT_LOG_RETENTION_DAYS", "2555")))


@dataclass
class PortalConfig:
    """Portal configuration."""
    default_session_timeout: int = field(default_factory=lambda: int(os.getenv("PORTAL_SESSION_TIMEOUT", "3600")))
    max_login_attempts: int = field(default_factory=lambda: int(os.getenv("PORTAL_MAX_LOGIN_ATTEMPTS", "5")))
    lockout_duration: int = field(default_factory=lambda: int(os.getenv("PORTAL_LOCKOUT_DURATION", "900")))
    password_reset_ttl: int = field(default_factory=lambda: int(os.getenv("PORTAL_PASSWORD_RESET_TTL", "3600")))


@dataclass
class IdentityConfig:
    """Main identity configuration."""
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    # Sub-configurations
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    verification: VerificationConfig = field(default_factory=VerificationConfig)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    compliance: ComplianceConfig = field(default_factory=ComplianceConfig)
    portal: PortalConfig = field(default_factory=PortalConfig)

    # Feature flags
    enable_mfa: bool = field(default_factory=lambda: os.getenv("ENABLE_MFA", "true").lower() == "true")
    enable_email_verification: bool = field(default_factory=lambda: os.getenv("ENABLE_EMAIL_VERIFICATION", "true").lower() == "true")
    enable_phone_verification: bool = field(default_factory=lambda: os.getenv("ENABLE_PHONE_VERIFICATION", "true").lower() == "true")
    enable_audit_logging: bool = field(default_factory=lambda: os.getenv("ENABLE_AUDIT_LOGGING", "true").lower() == "true")

    def validate(self) -> None:
        """Validate configuration."""
        if not self.security.secret_key or self.security.secret_key == "dev-secret-key":
            if self.environment == "production":
                raise ValueError("SECRET_KEY must be set in production")

        if not self.security.encryption_key or self.security.encryption_key == "dev-encryption-key":
            if self.environment == "production":
                raise ValueError("ENCRYPTION_KEY must be set in production")

        if self.security.password_min_length < 8:
            raise ValueError("Password minimum length must be at least 8 characters")

        if self.verification.otp_length < 4 or self.verification.otp_length > 10:
            raise ValueError("OTP length must be between 4 and 10 digits")


# Global configuration instance
config = IdentityConfig()
config.validate()


def get_config() -> IdentityConfig:
    """Get the global configuration instance."""
    return config


def update_config(**kwargs) -> None:
    """Update configuration values."""
    global config
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
    config.validate()
