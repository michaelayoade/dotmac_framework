"""
Health check module for DotMac Framework.
Provides health endpoints and monitoring.
"""

from .endpoints import add_health_endpoints, get_health_status, health_router

__all__ = ["health_router", "get_health_status", "add_health_endpoints"]
