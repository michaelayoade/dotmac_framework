"""
Type definitions for middleware system.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict


class MiddlewareType(str, Enum):
    """Types of middleware."""

    AUTH = "auth"
    SECURITY = "security"
    LOGGING = "logging"
    MONITORING = "monitoring"
    CACHING = "caching"
    RATE_LIMITING = "rate_limiting"
    TENANT = "tenant"
    CUSTOM = "custom"


class MiddlewareConfig(BaseModel):
    """Configuration for middleware."""

    name: str
    type: MiddlewareType
    enabled: bool = True
    priority: int = 100
    config: dict[str, Any] = {}

    model_config = ConfigDict(use_enum_values=True)
