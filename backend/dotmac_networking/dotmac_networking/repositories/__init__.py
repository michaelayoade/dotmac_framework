"""
PostgreSQL-based repositories for persistent storage.
Replaces in-memory dictionaries with proper database persistence.
"""

from .base_repository import BaseRepository
from .radius_repository import RadiusRepository
from .nas_repository import NASRepository
from .device_repository import DeviceRepository

__all__ = [
    "BaseRepository",
    "RadiusRepository", 
    "NASRepository",
    "DeviceRepository",
]