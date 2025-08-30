"""
SDK package for DotMac API Gateway - Individual SDK exports for composable usage.
"""

# Core gateway management
# API documentation
from .api_documentation import APIDocumentationSDK

# API versioning
from .api_versioning import APIVersioningSDK

# Authentication and authorization
from .authentication_proxy import AuthenticationProxySDK
from .gateway import GatewaySDK

# Gateway analytics and monitoring
from .gateway_analytics import GatewayAnalyticsSDK

# Rate limiting and throttling
from .rate_limiting import RateLimitingSDK

__all__ = [
    # Core gateway management
    "GatewaySDK",
    # Authentication and authorization
    "AuthenticationProxySDK",
    # Rate limiting and throttling
    "RateLimitingSDK",
    # API versioning
    "APIVersioningSDK",
    # Gateway analytics and monitoring
    "GatewayAnalyticsSDK",
    # API documentation
    "APIDocumentationSDK",
]
