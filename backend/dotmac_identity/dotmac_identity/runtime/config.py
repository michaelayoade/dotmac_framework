"""
Runtime configuration for dotmac_identity.
"""

import os

from pydantic import BaseModel, Field


class SecurityConfig(BaseModel):
    """Security configuration for identity services."""

    secret_key: str = Field(..., description="Application secret key")
    encryption_key: str = Field(..., description="Encryption key")
    jwt_secret: str = Field(..., description="JWT secret")
    password_min_length: int = Field(8, description="Minimum password length")


class VerificationConfig(BaseModel):
    """Verification configuration."""

    email_verification_ttl: int = Field(3600, description="Email verification TTL in seconds")
    phone_verification_ttl: int = Field(300, description="Phone verification TTL in seconds")
    otp_length: int = Field(6, description="OTP code length")
    max_verification_attempts: int = Field(3, description="Max verification attempts")


class RuntimeConfig(BaseModel):
    """Complete runtime configuration for identity services."""

    environment: str = Field("development", description="Runtime environment")
    debug: bool = Field(False, description="Debug mode")
    enable_mfa: bool = Field(True, description="Enable MFA")
    enable_email_verification: bool = Field(True, description="Enable email verification")

    security: SecurityConfig
    verification: VerificationConfig


def load_config() -> RuntimeConfig:
    """Load configuration from environment variables."""

    security_config = SecurityConfig(
        secret_key=os.getenv("SECRET_KEY", "your-secret-key"),
        encryption_key=os.getenv("ENCRYPTION_KEY", "your-encryption-key"),
        jwt_secret=os.getenv("JWT_SECRET", "jwt-secret"),
        password_min_length=int(os.getenv("PASSWORD_MIN_LENGTH", "8"))
    )

    verification_config = VerificationConfig(
        email_verification_ttl=int(os.getenv("EMAIL_VERIFICATION_TTL", "3600")),
        phone_verification_ttl=int(os.getenv("PHONE_VERIFICATION_TTL", "300")),
        otp_length=int(os.getenv("OTP_LENGTH", "6")),
        max_verification_attempts=int(os.getenv("MAX_VERIFICATION_ATTEMPTS", "3"))
    )

    return RuntimeConfig(
        environment=os.getenv("ENVIRONMENT", "development"),
        debug=os.getenv("DEBUG", "false").lower() == "true",
        enable_mfa=os.getenv("ENABLE_MFA", "true").lower() == "true",
        enable_email_verification=os.getenv("ENABLE_EMAIL_VERIFICATION", "true").lower() == "true",
        security=security_config,
        verification=verification_config
    )
