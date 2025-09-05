from .api_documentation import APIDocumentationSDK
from .api_versioning import APIVersioningSDK
from .authentication_proxy import AuthenticationProxySDK
from .gateway import GatewaySDK
from .gateway_analytics import GatewayAnalyticsSDK
from .rate_limiting import RateLimitingSDK

"""
SDK package for DotMac API Gateway - Individual SDK exports for composable usage.
"""

# Core gateway management
# API documentation

# API versioning

# Authentication and authorization

# Gateway analytics and monitoring

# Rate limiting and throttling

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
