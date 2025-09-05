"""
Onboarding service orchestrating the workflow and persisting state.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from dotmac.communications.events import create_memory_event_bus, create_redis_event_bus
from dotmac.communications.events.message import Event as EventRecord
from dotmac_shared.core.error_utils import publish_event
from dotmac_shared.provisioning import provision_isp_container, validate_container_health
from dotmac_shared.provisioning.core.models import InfrastructureType, ISPConfig, PlanType
from dotmac_shared.workflows.task import create_sequential_workflow
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.websocket_manager import websocket_manager
from ..database import async_session_maker
from ..models.onboarding import OnboardingRequest, OnboardingStatus, StepStatus
from ..repositories.onboarding import (
    OnboardingArtifactRepository,
    OnboardingRequestRepository,
    OnboardingStepRepository,
)
from ..schemas.tenant import TenantOnboardingRequest

# Simple in-process event bus (can be swapped to Redis/Kafka in prod)
_event_bus = None
try:
    from ..core.settings import get_settings

    _settings = get_settings()
    if _settings.events_redis_url:
        _event_bus = create_redis_event_bus(_settings.events_redis_url)
    else:
        _event_bus = create_memory_event_bus()
except (ImportError, AttributeError):
    _event_bus = None


class OnboardingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.req_repo = OnboardingRequestRepository(db)
        self.step_repo = OnboardingStepRepository(db)
        self.art_repo = OnboardingArtifactRepository(db)

    async def create_request(
        self, request: TenantOnboardingRequest, partner_id: Optional[UUID] = None
    ) -> OnboardingRequest:
        workflow_id = f"wf_{int(datetime.now(timezone.utc).timestamp())}_{request.tenant_info.slug}"
        req = await self.req_repo.create(
            {
                "workflow_id": workflow_id,
                "partner_id": partner_id,
                "tenant_name": request.tenant_info.name,
                "tenant_slug": request.tenant_info.slug,
                "status": OnboardingStatus.IN_PROGRESS,
            }
        )
        # Seed steps
        for key, name in (
            ("provision_container", "Provision Container"),
            ("validate_health", "Validate Health"),
        ):
            step = await self.step_repo.upsert_step(req.id, key, name)
            await self.step_repo.set_status(step.id, StepStatus.PENDING)
        return req

    async def run_workflow(self, onboarding_id: UUID, request: TenantOnboardingRequest):
        # Use a new session in the background task
        async with async_session_maker() as session:
            req_repo = OnboardingRequestRepository(session)
            step_repo = OnboardingStepRepository(session)
            art_repo = OnboardingArtifactRepository(session)

            req = await req_repo.get_by_id(onboarding_id)
            if not req:
                return

            plan = PlanType.PREMIUM if "advanced_analytics" in (request.enabled_features or []) else PlanType.STANDARD
            isp_config = ISPConfig(
                tenant_name=request.tenant_info.slug,
                display_name=request.tenant_info.name,
                plan_type=plan,
            )
            isp_id = uuid4()

            async def _emit(event_type: str, payload: dict[str, Any]):
                if _event_bus:
                    await publish_event(_event_bus, EventRecord(event_type=event_type, data=payload))
                # Also broadcast to admins via WS
                try:
                    await websocket_manager.broadcast_to_admins(
                        {
                            "type": event_type,
                            "onboarding": {"workflow_id": req.workflow_id, "request_id": str(req.id)},
                            "payload": payload,
                        }
                    )
                except (RuntimeError, ConnectionError, TimeoutError):
                    # Ignore transient WS errors during emit
                    pass

            async def mark_step(
                key: str, status: StepStatus, data: Optional[dict[str, Any]] = None, error: Optional[str] = None
            ):
                step = await step_repo.upsert_step(req.id, key, key.replace("_", " ").title())
                await step_repo.set_status(step.id, status, error_message=error, data=data or {})
                await _emit(
                    "onboarding.step.updated",
                    {
                        "step_key": key,
                        "status": status.value,
                        "error": error,
                        "data": data or {},
                    },
                )

            async def step_provision():
                await mark_step("provision_container", StepStatus.RUNNING)
                result = await provision_isp_container(
                    isp_id=isp_id,
                    customer_count=100,
                    config=isp_config,
                    infrastructure_type=InfrastructureType.KUBERNETES,
                    region=request.deployment_region,
                    timeout=300,
                )
                req.endpoint_url = result.endpoint_url
                await session.flush()
                # Persist artifacts and logs
                if result.artifacts:
                    await art_repo.create(
                        {
                            "request_id": req.id,
                            "artifact_type": "deployment_artifacts",
                            "data": result.artifacts.model_dump(),
                        }
                    )
                if result.provisioning_logs:
                    await art_repo.create(
                        {
                            "request_id": req.id,
                            "artifact_type": "provisioning_logs",
                            "data": {"logs": result.provisioning_logs},
                        }
                    )
                await mark_step(
                    "provision_container",
                    StepStatus.COMPLETED if result.success else StepStatus.FAILED,
                    data={"endpoint_url": result.endpoint_url},
                    error=None if result.success else (result.error_message or "provisioning_failed"),
                )
                if not result.success:
                    raise RuntimeError(result.error_message or "Provisioning failed")

            async def step_validate():
                await mark_step("validate_health", StepStatus.RUNNING)
                if not req.endpoint_url:
                    raise RuntimeError("No endpoint URL for health validation")
                health = await validate_container_health(base_url=req.endpoint_url, timeout=60)
                await mark_step(
                    "validate_health",
                    StepStatus.COMPLETED
                    if getattr(health, "overall_status", None) and health.overall_status.value == "healthy"
                    else StepStatus.FAILED,
                    data={
                        "health": getattr(health, "overall_status", None).value
                        if getattr(health, "overall_status", None)
                        else "unknown"
                    },
                )

            workflow = create_sequential_workflow(
                ("provision_container", step_provision),
                ("validate_health", step_validate),
                workflow_id=req.workflow_id,
            )

            try:
                await workflow.execute()
                req.status = OnboardingStatus.COMPLETED
                await _emit(
                    "onboarding.status.updated",
                    {"status": req.status.value, "endpoint_url": req.endpoint_url},
                )
            except (RuntimeError, ValueError) as e:
                req.status = OnboardingStatus.FAILED
                req.error_message = str(e)
                await _emit(
                    "onboarding.status.updated",
                    {"status": req.status.value, "error": req.error_message},
                )
            finally:
                await session.flush()

    async def start_async(self, req: OnboardingRequest, request: TenantOnboardingRequest):
        asyncio.create_task(self.run_workflow(req.id, request))
