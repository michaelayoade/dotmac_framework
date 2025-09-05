"""
Deployment repository implementations.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.deployment import Deployment, InfrastructureTemplate
from ..repositories.base import BaseRepository


class InfrastructureTemplateRepository(BaseRepository[InfrastructureTemplate]):
    """Repository for infrastructure template operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, InfrastructureTemplate)


class DeploymentRepository(BaseRepository[Deployment]):
    """Repository for deployment operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Deployment)
