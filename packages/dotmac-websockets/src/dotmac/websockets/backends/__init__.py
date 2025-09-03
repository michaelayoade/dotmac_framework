"""
Scaling backends for WebSocket gateway.
"""

from .base import ScalingBackend
from .local import LocalBackend

# Try to import Redis backend (optional dependency)
try:
    from .redis import RedisScalingBackend
except ImportError:
    RedisScalingBackend = None

__all__ = [
    "ScalingBackend",
    "LocalBackend",
    "RedisScalingBackend",  # May be None if Redis not available
]