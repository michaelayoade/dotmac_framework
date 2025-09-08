"""
Onboarding repositories for requests, steps, and artifacts.
"""

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.onboarding import (
    OnboardingArtifact,
    OnboardingRequest,
    OnboardingStatus,
    OnboardingStep,
    StepStatus,
)
from .base import BaseRepository


class OnboardingRequestRepository(BaseRepository[OnboardingRequest]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, OnboardingRequest)

    async def get_by_workflow_id(self, workflow_id: str) -> Optional[OnboardingRequest]:
        return await self.get_by_field("workflow_id", workflow_id)

    async def list_paginated(
        self, page: int, size: int, partner_id: Optional[UUID] = None
    ) -> tuple[list[OnboardingRequest], int]:
        query = select(OnboardingRequest).where(OnboardingRequest.is_deleted is False)
        if partner_id:
            query = query.where(OnboardingRequest.partner_id == partner_id)
        total_result = await self.db.execute(query.with_only_columns(OnboardingRequest.id))
        total = len(total_result.scalars().all())
        result = await self.db.execute(
            query.order_by(OnboardingRequest.created_at.desc()).offset((page - 1) * size).limit(size)
        )
        return result.scalars().all(), total

    async def list_active_by_partner(self, partner_id: UUID) -> list[OnboardingRequest]:
        query = select(OnboardingRequest).where(
            OnboardingRequest.is_deleted is False,
            OnboardingRequest.partner_id == partner_id,
            OnboardingRequest.status == OnboardingStatus.IN_PROGRESS,
        )
        result = await self.db.execute(query)
        return result.scalars().all()


class OnboardingStepRepository(BaseRepository[OnboardingStep]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, OnboardingStep)

    async def upsert_step(self, request_id: UUID, step_key: str, name: str) -> OnboardingStep:
        query = select(OnboardingStep).where(
            OnboardingStep.request_id == request_id, OnboardingStep.step_key == step_key
        )
        result = await self.db.execute(query)
        step = result.scalar_one_or_none()
        if not step:
            step = OnboardingStep(
                request_id=request_id,
                step_key=step_key,
                name=name,
            )
            self.db.add(step)
            await self.db.flush()
            await self.db.refresh(step)
        return step

    async def set_status(
        self,
        step_id: UUID,
        status: StepStatus,
        error_message: Optional[str] = None,
        data: Optional[dict[str, Any]] = None,
    ) -> OnboardingStep:
        step = await self.get_by_id(step_id)
        if not step:
            return None
        step.status = status
        now = datetime.now(timezone.utc)
        if status == StepStatus.RUNNING and not step.started_at:
            step.started_at = now
        if status in (StepStatus.COMPLETED, StepStatus.FAILED):
            step.completed_at = now
        if error_message:
            step.error_message = error_message
        if data:
            d = dict(step.data or {})
            d.update(data)
            step.data = d
        await self.db.flush()
        await self.db.refresh(step)
        return step

    async def set_status_by_key(self, step_key: str, status: StepStatus, reason: Optional[str] = None) -> int:
        """Update all steps with a given key across requests."""
        # Fetch steps by key; perform python-side updates to set timestamps correctly
        query = select(OnboardingStep).where(OnboardingStep.step_key == step_key)
        result = await self.db.execute(query)
        steps = result.scalars().all()
        now = datetime.now(timezone.utc)
        count = 0
        for step in steps:
            step.status = status
            if status == StepStatus.RUNNING and not step.started_at:
                step.started_at = now
            if status in (StepStatus.COMPLETED, StepStatus.FAILED):
                step.completed_at = now
            if reason and status == StepStatus.FAILED:
                step.error_message = reason
            count += 1
        if steps:
            await self.db.flush()
        return count


class OnboardingArtifactRepository(BaseRepository[OnboardingArtifact]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, OnboardingArtifact)
