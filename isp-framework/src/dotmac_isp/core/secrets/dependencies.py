"""
Security Module Dependencies

This module handles optional dependencies and provides graceful degradation
when security packages are not installed.
"""

import sys
import warnings
from typing import Any

# Track missing dependencies
MISSING_DEPENDENCIES = []


def import_optional(module_name: str, package_name: str = None) -> Any | None:
    """
    Import optional dependency with graceful fallback

    Args:
        module_name: Name of module to import
        package_name: Name of package for installation (if different from module)

    Returns:
        Imported module or None if not available
    """
    try:
        return __import__(module_name)
    except ImportError:
        pkg_name = package_name or module_name
        if pkg_name not in MISSING_DEPENDENCIES:
            MISSING_DEPENDENCIES.append(pkg_name)
        return None


def check_security_dependencies() -> tuple[bool, list[str]]:
    """
    Check if all security dependencies are available

    Returns:
        Tuple of (all_available, missing_packages)
    """
    # Core dependencies for security functionality
    dependencies = [
        ("structlog", "structlog"),
        ("pydantic", "pydantic"),
        ("cryptography", "cryptography"),
        ("jwt", "PyJWT"),
    ]

    missing = []
    for module, package in dependencies:
        if import_optional(module, package) is None:
            missing.append(package)

    return len(missing) == 0, missing


def require_security_dependencies():
    """
    Check dependencies and raise helpful error if missing
    """
    all_available, missing = check_security_dependencies()

    if not all_available:
        error_msg = f"""
Security dependencies missing. Please install:

pip install {' '.join(missing)}

Missing packages: {missing}

The DotMac security module requires these packages for:
- structlog: Structured logging for audit trails
- pydantic: Data validation and serialization
- cryptography: Encryption and certificate management
- PyJWT: JWT token handling

For production deployment, install all dependencies:
pip install -e ".[security]"
"""
        raise ImportError(error_msg)


def get_logger():
    """Get logger with fallback"""
    structlog = import_optional("structlog")
    if structlog:
        return structlog.get_logger(__name__)
    else:
        import logging

        return logging.getLogger(__name__)


# Common imports with fallbacks
logger = get_logger()

# Try to import key packages
try:
    import structlog
except ImportError:
    structlog = None

try:
    from pydantic import BaseModel, ConfigDict, Field, field_validator
except ImportError:
    # Create mock classes for development
    class BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    def Field(*args, **kwargs):
        return None

    def field_validator(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

    def ConfigDict(*args, **kwargs):
        return {}


try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa

    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    raise ImportError(
        "cryptography is required for production. Install with: pip install cryptography"
    )

try:
    import jwt
except ImportError:
    raise ImportError(
        "PyJWT is required for production. Install with: pip install PyJWT"
    )

# Warn about missing dependencies in development
if MISSING_DEPENDENCIES and not sys.flags.quiet:
    warnings.warn(
        f"Security dependencies missing: {MISSING_DEPENDENCIES}. "
        f"Install with: pip install {' '.join(MISSING_DEPENDENCIES)}",
        ImportWarning,
    )
