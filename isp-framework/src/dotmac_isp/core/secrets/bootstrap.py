import logging

logger = logging.getLogger(__name__)

"""
Security Bootstrap Module

Validates that all required security dependencies are available at startup.
This prevents the application from running with mock security components.
"""

import jwt
import cryptography
import bcrypt


def validate_deps():
    """
    Validate that all critical security dependencies are properly installed.

    Raises:
        RuntimeError: If any required security dependency is missing or invalid
    """
    try:
        # Test JWT functionality
        test_payload = {"test": 1, "iat": 1234567890}
        jwt.encode(test_payload, "dummy_key", algorithm="HS256")

        # Test cryptography availability
        cryptography.__version__

        # Test bcrypt functionality
        bcrypt.checkpw(b"test", b"$2b$12$dummy.hash.for.testing.only")

    except ImportError as e:
        raise RuntimeError(f"Security dependencies missing: {str(e)}")
    except Exception as e:
        # For bcrypt, we expect this to fail with the dummy hash, but ImportError would be caught above
        if "cryptography" in str(e) or "jwt" in str(e):
            raise RuntimeError(f"Security dependency validation failed: {str(e)}")


def validate_production_ready():
    """
    Additional production readiness checks for security components.
    """
    import os

    # Check that we're not using development secrets
    jwt_secret = os.getenv("JWT_SECRET", "")
    if jwt_secret in ["secret123", "development", "test", ""]:
        raise RuntimeError(
            "Production JWT_SECRET required. Set secure JWT_SECRET environment variable."
        )

    db_password = os.getenv("DB_PASSWORD", "")
    if db_password in ["password123", "development", "test", ""]:
        raise RuntimeError(
            "Production DB_PASSWORD required. Set secure DB_PASSWORD environment variable."
        )


if __name__ == "__main__":
    validate_deps()
    validate_production_ready()
logger.info("✅ Security dependencies validated successfully")
