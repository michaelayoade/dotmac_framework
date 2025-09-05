"""
Onboarding API for tenant onboarding workflows used by management-reseller portal.
Provides a pragmatic implementation using existing tenant schemas where possible.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from dotmac_shared.api.dependencies import (
    PaginatedDependencies,
    StandardDependencies,
    get_paginated_deps,
    get_standard_deps,
)
from dotmac_shared.api.rate_limiting_decorators import rate_limit, rate_limit_strict
from fastapi import Depends, HTTPException

from dotmac.application import standard_exception_handler
from dotmac.application.api.router_factory import RouterFactory

from ..repositories.onboarding import (
    OnboardingArtifactRepository,
    OnboardingRequestRepository,
    OnboardingStepRepository,
)
from ..schemas.tenant import (
    TenantOnboardingRequest,
    TenantOnboardingResponse,
    TenantResponse,
)
from ..services.onboarding_service import OnboardingService

# Use DRY RouterFactory for router creation
router = RouterFactory("Onboarding").create_router(
    prefix="/onboarding", tags=["Onboarding"]
)


# In-memory store for simple workflow steps (replace with DB or workflow engine later)
_WORKFLOWS: dict[str, dict[str, Any]] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/", response_model=dict[str, Any])
@rate_limit(max_requests=60, time_window_seconds=60)
@standard_exception_handler
async def list_onboarding_requests(
    deps: PaginatedDependencies = Depends(get_paginated_deps),
) -> dict[str, Any]:
    repo = OnboardingRequestRepository(deps.db)
    items, total = await repo.list_paginated(deps.pagination.page, deps.pagination.size)
    return {
        "items": [
            {
                "id": str(it.id),
                "workflow_id": it.workflow_id,
                "tenant": {"name": it.tenant_name, "slug": it.tenant_slug},
                "status": it.status.value
                if hasattr(it.status, "value")
                else str(it.status),
                "endpoint_url": it.endpoint_url,
                "created_at": it.created_at,
                "updated_at": it.updated_at,
            }
            for it in items
        ],
        "total": total,
        "page": deps.pagination.page,
        "size": deps.pagination.size,
    }


@router.post("/", response_model=TenantOnboardingResponse, status_code=201)
@rate_limit_strict(max_requests=10, time_window_seconds=60)
@standard_exception_handler
async def create_onboarding_request(
    request: TenantOnboardingRequest,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> TenantOnboardingResponse:
    service = OnboardingService(deps.db)
    req = await service.create_request(request)

    # Launch background workflow execution
    await service.start_async(req, request)

    # Response using request data
    tenant_resp = TenantResponse(
        id=UUID(int=0),
        name=req.tenant_name,
        slug=req.tenant_slug,
        status="pending",
        created_at=req.created_at,
        updated_at=req.updated_at,
    )
    steps = [
        {
            "id": "provision_container",
            "name": "Provision Container",
            "status": "PENDING",
        },
        {"id": "validate_health", "name": "Validate Health", "status": "PENDING"},
    ]
    return TenantOnboardingResponse(
        tenant=tenant_resp,
        workflow_id=req.workflow_id,
        estimated_completion_hours=1,
        deployment_steps=steps,
    )


@router.get("/steps/{partner_id}", response_model=list[dict[str, Any]])
@rate_limit(max_requests=120, time_window_seconds=60)
@standard_exception_handler
async def get_steps(
    partner_id: str, deps: StandardDependencies = Depends(get_standard_deps)
) -> list[dict[str, Any]]:
    # Provide canonical onboarding steps available for partners
    return [
        {"id": "provision_container", "name": "Provision Container"},
        {"id": "validate_health", "name": "Validate Health"},
        {"id": "setup_billing", "name": "Set Up Billing"},
        {"id": "enable_features", "name": "Enable Plan Features"},
    ]


@router.put("/steps/{step_id}", response_model=dict[str, Any])
@rate_limit_strict(max_requests=30, time_window_seconds=60)
@standard_exception_handler
async def update_step(
    step_id: str,
    data: dict[str, Any],
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    # Update all DB steps with this key
    step_repo = OnboardingStepRepository(deps.db)
    status = data.get("status")
    reason = data.get("rejection_reason")
    updated = 0
    if status in ("PENDING", "RUNNING", "COMPLETED", "FAILED"):
        from ...models.onboarding import StepStatus

        updated = await step_repo.set_status_by_key(
            step_id, StepStatus(status), reason=reason
        )
    else:
        updated = 0
    if updated == 0:
        raise HTTPException(status_code=404, detail="Step not found")
    return {"message": "Step updated", "count": updated}


@router.post("/steps/{step_id}/approve", response_model=dict[str, Any])
@rate_limit_strict(max_requests=60, time_window_seconds=60)
@standard_exception_handler
async def approve_step(
    step_id: str, deps: StandardDependencies = Depends(get_standard_deps)
) -> dict[str, Any]:
    return await update_step(
        step_id, {"status": "COMPLETED", "approved_at": _now_iso()}, deps
    )


@router.post("/steps/{step_id}/reject", response_model=dict[str, Any])
@rate_limit_strict(max_requests=60, time_window_seconds=60)
@standard_exception_handler
async def reject_step(
    step_id: str,
    reason: str,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    return await update_step(
        step_id,
        {"status": "FAILED", "rejection_reason": reason, "rejected_at": _now_iso()},
        deps,
    )


@router.post("/{partner_id}/complete", response_model=dict[str, Any])
@rate_limit_strict(max_requests=20, time_window_seconds=60)
@standard_exception_handler
async def complete_onboarding(
    partner_id: str,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    from ...models.onboarding import OnboardingStatus
    from ..repositories.onboarding import OnboardingRequestRepository

    repo = OnboardingRequestRepository(deps.db)
    try:
        partner_uuid = UUID(partner_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid partner_id") from e
    active = await repo.list_active_by_partner(partner_uuid)
    count = 0
    for req in active:
        req.status = OnboardingStatus.COMPLETED
        count += 1
    if count:
        await deps.db.flush()
    if count == 0:
        raise HTTPException(status_code=404, detail="No active onboarding to complete")
    return {"message": "Onboarding completed", "count": count}


@router.get("/{request_id}", response_model=dict[str, Any])
@rate_limit(max_requests=120, time_window_seconds=60)
@standard_exception_handler
async def get_onboarding_request(
    request_id: UUID,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    req_repo = OnboardingRequestRepository(deps.db)
    req = await req_repo.get_by_id(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Onboarding request not found")
    from sqlalchemy import select

    from ...models.onboarding import OnboardingStep

    result = await deps.db.execute(
        select(OnboardingStep).where(OnboardingStep.request_id == request_id)
    )
    steps = result.scalars().all()
    return {
        "id": str(req.id),
        "workflow_id": req.workflow_id,
        "tenant": {"name": req.tenant_name, "slug": req.tenant_slug},
        "status": req.status.value if hasattr(req.status, "value") else str(req.status),
        "endpoint_url": req.endpoint_url,
        "created_at": req.created_at,
        "updated_at": req.updated_at,
        "steps": [
            {
                "id": str(s.id),
                "key": s.step_key,
                "name": s.name,
                "status": s.status.value
                if hasattr(s.status, "value")
                else str(s.status),
                "started_at": s.started_at,
                "completed_at": s.completed_at,
                "error_message": s.error_message,
                "data": s.data,
            }
            for s in steps
        ],
    }


@router.get("/{request_id}/artifacts", response_model=dict[str, Any])
@rate_limit(max_requests=120, time_window_seconds=60)
@standard_exception_handler
async def get_onboarding_artifacts(
    request_id: UUID,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    OnboardingArtifactRepository(deps.db)
    from sqlalchemy import select

    from ...models.onboarding import OnboardingArtifact

    result = await deps.db.execute(
        select(OnboardingArtifact).where(OnboardingArtifact.request_id == request_id)
    )
    artifacts = result.scalars().all()
    return {
        "items": [
            {
                "id": str(a.id),
                "artifact_type": a.artifact_type,
                "data": a.data,
                "created_at": a.created_at,
            }
            for a in artifacts
        ]
    }


@router.get("/{request_id}/logs", response_model=dict[str, Any])
@rate_limit(max_requests=120, time_window_seconds=60)
@standard_exception_handler
async def get_onboarding_logs(
    request_id: UUID,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    from sqlalchemy import select

    from ...models.onboarding import OnboardingArtifact

    result = await deps.db.execute(
        select(OnboardingArtifact).where(
            OnboardingArtifact.request_id == request_id,
            OnboardingArtifact.artifact_type == "provisioning_logs",
        )
    )
    row = result.scalars().first()
    logs = []
    if row and isinstance(row.data, dict):
        logs = row.data.get("logs", [])
    return {"logs": logs}
