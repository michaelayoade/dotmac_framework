"""Ansible Integration API router."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from dotmac_isp.core.database import get_db
from dotmac_isp.integrations.ansible.models import (
    AnsiblePlaybook,
    PlaybookExecution,
    DeviceInventory,
    ConfigurationTemplate,
    AutomationTask,

from dotmac_isp.integrations.ansible.schemas import (
    PlaybookCreate,
    PlaybookResponse,
    ExecutionCreate,
    ExecutionResponse,
    InventoryCreate,
    InventoryResponse,
    TemplateCreate,
    TemplateResponse,
, timezone)
from dotmac_isp.integrations.ansible.client import AnsibleClient

router = APIRouter(prefix="/api/v1/ansible", tags=["Ansible Integration"])


# Playbook Management


@router.post("/playbooks", response_model=PlaybookResponse)
async def create_playbook(playbook: PlaybookCreate, db: AsyncSession = Depends(get_db):
    """Create a new Ansible playbook."""
    db_playbook = AnsiblePlaybook(**playbook.model_dump()
    db.add(db_playbook)
    await db.commit()
    await db.refresh(db_playbook)
    return PlaybookResponse.model_validate(db_playbook)


@router.get("/playbooks", response_model=List[PlaybookResponse])
async def list_playbooks(
    playbook_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List Ansible playbooks with filtering."""
    query = select(AnsiblePlaybook)

    filters = []
    if playbook_type:
        filters.append(AnsiblePlaybook.playbook_type == playbook_type)
    if search:
        filters.append(AnsiblePlaybook.name.ilike(f"%{search}%")

    if filters:
        query = query.where(and_(*filters)

    result = await db.execute(query)
    playbooks = result.scalars().all()

    return [PlaybookResponse.model_validate(playbook) for playbook in playbooks]


@router.get("/playbooks/{playbook_id}", response_model=PlaybookResponse)
async def get_playbook(
    playbook_id: str = Path(...), db: AsyncSession = Depends(get_db)
):
    """Get a specific playbook by ID."""
    result = await db.execute(
        select(AnsiblePlaybook).where(AnsiblePlaybook.id == playbook_id)
    )
    playbook = result.scalar_one_or_none()

    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook not found")

    return PlaybookResponse.model_validate(playbook)


@router.post("/playbooks/{playbook_id}/execute", response_model=ExecutionResponse)
async def execute_playbook(
    playbook_id: str = Path(...),
    execution_data: ExecutionCreate = None,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
):
    """Execute an Ansible playbook."""
    # Get playbook
    result = await db.execute(
        select(AnsiblePlaybook).where(AnsiblePlaybook.id == playbook_id)
    )
    playbook = result.scalar_one_or_none()

    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook not found")

    # Create execution record
    execution = PlaybookExecution(
        playbook_id=playbook_id, **execution_data.model_dump()
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    # Execute playbook in background
    if background_tasks:
        background_tasks.add_task(run_ansible_playbook, execution.id)

    return ExecutionResponse.model_validate(execution)


@router.get(
    "/playbooks/{playbook_id}/executions", response_model=List[ExecutionResponse]
)
async def list_playbook_executions(
    playbook_id: str = Path(...),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List executions for a playbook."""
    query = select(PlaybookExecution).where(
        PlaybookExecution.playbook_id == playbook_id
    )

    if status:
        query = query.where(PlaybookExecution.status == status)

    query = query.order_by(PlaybookExecution.created_at.desc().limit(limit)

    result = await db.execute(query)
    executions = result.scalars().all()

    return [ExecutionResponse.model_validate(execution) for execution in executions]


# Inventory Management


@router.post("/inventories", response_model=InventoryResponse)
async def create_inventory(
    inventory: InventoryCreate, db: AsyncSession = Depends(get_db)
):
    """Create a new device inventory."""
    db_inventory = DeviceInventory(**inventory.model_dump()
    db.add(db_inventory)
    await db.commit()
    await db.refresh(db_inventory)
    return InventoryResponse.model_validate(db_inventory)


@router.get("/inventories", response_model=List[InventoryResponse])
async def list_inventories(
    inventory_type: Optional[str] = Query(None), db: AsyncSession = Depends(get_db)
):
    """List device inventories."""
    query = select(DeviceInventory)

    if inventory_type:
        query = query.where(DeviceInventory.inventory_type == inventory_type)

    result = await db.execute(query)
    inventories = result.scalars().all()

    return [InventoryResponse.model_validate(inventory) for inventory in inventories]


@router.post("/inventories/{inventory_id}/validate")
async def validate_inventory(
    inventory_id: str = Path(...), db: AsyncSession = Depends(get_db)
):
    """Validate an inventory configuration."""
    result = await db.execute(
        select(DeviceInventory).where(DeviceInventory.id == inventory_id)
    )
    inventory = result.scalar_one_or_none()

    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")

    # Validate inventory using Ansible client
    client = AnsibleClient()
    is_valid, errors = await client.validate_inventory(inventory.inventory_content)

    return {
        "inventory_id": inventory_id,
        "is_valid": is_valid,
        "errors": errors,
        "validated_at": datetime.now(timezone.utc),
    }


# Configuration Templates


@router.post("/templates", response_model=TemplateResponse)
async def create_configuration_template(
    template: TemplateCreate, db: AsyncSession = Depends(get_db)
):
    """Create a new configuration template."""
    db_template = ConfigurationTemplate(**template.model_dump()
    db.add(db_template)
    await db.commit()
    await db.refresh(db_template)
    return TemplateResponse.model_validate(db_template)


@router.get("/templates", response_model=List[TemplateResponse])
async def list_configuration_templates(
    template_type: Optional[str] = Query(None),
    device_type: Optional[str] = Query(None),
    vendor: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List configuration templates with filtering."""
    query = select(ConfigurationTemplate)

    filters = []
    if template_type:
        filters.append(ConfigurationTemplate.template_type == template_type)
    if device_type:
        filters.append(ConfigurationTemplate.device_type == device_type)
    if vendor:
        filters.append(ConfigurationTemplate.vendor == vendor)

    if filters:
        query = query.where(and_(*filters)

    result = await db.execute(query)
    templates = result.scalars().all()

    return [TemplateResponse.model_validate(template) for template in templates]


# Execution Monitoring


@router.get("/executions", response_model=List[ExecutionResponse])
async def list_all_executions(
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List all playbook executions."""
    query = select(PlaybookExecution)

    if status:
        query = query.where(PlaybookExecution.status == status)

    query = query.order_by(PlaybookExecution.created_at.desc().limit(limit)

    result = await db.execute(query)
    executions = result.scalars().all()

    return [ExecutionResponse.model_validate(execution) for execution in executions]


@router.get("/executions/{execution_id}", response_model=ExecutionResponse)
async def get_execution(
    execution_id: str = Path(...), db: AsyncSession = Depends(get_db)
):
    """Get a specific execution by ID."""
    result = await db.execute(
        select(PlaybookExecution).where(PlaybookExecution.id == execution_id)
    )
    execution = result.scalar_one_or_none()

    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    return ExecutionResponse.model_validate(execution)


@router.post("/executions/{execution_id}/cancel")
async def cancel_execution(
    execution_id: str = Path(...), db: AsyncSession = Depends(get_db)
):
    """Cancel a running execution."""
    result = await db.execute(
        select(PlaybookExecution).where(PlaybookExecution.id == execution_id)
    )
    execution = result.scalar_one_or_none()

    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    if execution.status not in ["pending", "running"]:
        raise HTTPException(
            status_code=400, detail="Execution cannot be cancelled in current status"
        )

    # Mark as cancelled
    execution.status = "cancelled"
    execution.completed_at = datetime.now(timezone.utc)
    await db.commit()

    return {"message": "Execution cancelled successfully"}


# Dashboard and Statistics


@router.get("/dashboard/summary")
async def get_ansible_dashboard_summary(db: AsyncSession = Depends(get_db):
    """Get Ansible integration dashboard summary."""
    # Get total playbooks
    total_playbooks_result = await db.execute(select(func.count(AnsiblePlaybook.id)
    total_playbooks = total_playbooks_result.scalar()

    # Get total executions in last 30 days
    thirty_days_ago = datetime.now(timezone.utc).replace(day=datetime.now(timezone.utc).day - 30)
    recent_executions_result = await db.execute(
        select(func.count(PlaybookExecution.id).where(
            PlaybookExecution.created_at >= thirty_days_ago
        )
    )
    recent_executions = recent_executions_result.scalar()

    # Get execution status counts
    status_counts_query = (
        select(
            PlaybookExecution.status, func.count(PlaybookExecution.id).label("count")
        )
        .where(PlaybookExecution.created_at >= thirty_days_ago)
        .group_by(PlaybookExecution.status)
    )

    status_counts_result = await db.execute(status_counts_query)
    status_counts = {row.status: row.count for row in status_counts_result}

    # Get success rate
    total_recent = sum(status_counts.values()
    success_count = status_counts.get("success", 0)
    success_rate = (success_count / total_recent * 100) if total_recent > 0 else 0

    return {
        "total_playbooks": total_playbooks,
        "recent_executions": recent_executions,
        "status_counts": status_counts,
        "success_rate": round(success_rate, 2),
        "timestamp": datetime.now(timezone.utc),
    }


# Background task functions


async def run_ansible_playbook(execution_id: str):
    """Background task to run Ansible playbook."""
    # This would implement the actual playbook execution
    # using the AnsibleClient
    pass
