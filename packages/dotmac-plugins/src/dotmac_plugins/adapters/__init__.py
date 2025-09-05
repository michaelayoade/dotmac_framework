"""
Domain-specific plugin adapters.

Provides specialized interfaces and utilities for different plugin domains
like communication, storage, authentication, and networking.
"""

from .authentication import AuthenticationAdapter
from .communication import CommunicationAdapter
from .networking import NetworkingAdapter
from .storage import StorageAdapter

__all__ = [
    "CommunicationAdapter",
    "StorageAdapter",
    "AuthenticationAdapter",
    "NetworkingAdapter",
]
