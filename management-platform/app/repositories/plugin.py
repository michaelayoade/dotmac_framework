"""
Plugin repository implementations.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.plugin import Plugin, PluginCategory, PluginLicense
from repositories.base import BaseRepository


class PluginCategoryRepository(BaseRepository[PluginCategory]):
    """Repository for plugin category operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, PluginCategory)


class PluginRepository(BaseRepository[Plugin]):
    """Repository for plugin operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Plugin)


class PluginLicenseRepository(BaseRepository[PluginLicense]):
    """Repository for plugin license operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, PluginLicense)