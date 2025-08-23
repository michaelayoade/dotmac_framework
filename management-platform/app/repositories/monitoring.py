"""
Monitoring repository implementations.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.monitoring import Alert, HealthCheck, Metric, SLARecord
from .base import BaseRepository


class HealthCheckRepository(BaseRepository[HealthCheck]):
    """Repository for health check operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, HealthCheck)


class MetricRepository(BaseRepository[Metric]):
    """Repository for metric operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Metric)


class AlertRepository(BaseRepository[Alert]):
    """Repository for alert operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Alert)


class SLARecordRepository(BaseRepository[SLARecord]):
    """Repository for SLA record operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, SLARecord)