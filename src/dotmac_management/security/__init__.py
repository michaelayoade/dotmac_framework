"""
DotMac Management API Security Module

Centralized security configuration and utilities for the DotMac Management API.
Leverages dotmac_shared security components for consistent security policies
across the platform.
"""

from .management_api_security_config import (
    ManagementAPISecurityConfig,
    EndpointSensitivity,
    SecurityPolicy,
    management_security,
    get_rate_limit_rules,
    get_cors_config,
    get_security_headers,
    get_authentication_config,
    setup_management_api_security
)

__all__ = [
    "ManagementAPISecurityConfig",
    "EndpointSensitivity", 
    "SecurityPolicy",
    "management_security",
    "get_rate_limit_rules",
    "get_cors_config", 
    "get_security_headers",
    "get_authentication_config",
    "setup_management_api_security"
]