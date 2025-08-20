"""
DotMac API Gateway - Centralized API management, authentication, rate limiting, and monitoring.

This plane provides comprehensive API Gateway functionality for the DotMac ISP framework,
including request routing, authentication, rate limiting, API versioning, analytics,
and developer documentation.
"""

from .runtime import APIGatewayApp, create_gateway_app, run_gateway

__version__ = "1.0.0"
__author__ = "DotMac Framework Team"
__description__ = "API Gateway plane for DotMac ISP operations framework"

__all__ = [
    "APIGatewayApp",
    "create_gateway_app",
    "run_gateway"
]
