"""Notification template API endpoints."""

from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from dotmac_isp.core.database import get_db
from dotmac_isp.shared.auth import get_current_tenant
from ..models import NotificationTemplate, NotificationChannel, NotificationType
from ..schemas import (
    NotificationTemplateCreate,
    NotificationTemplateUpdate,
    NotificationTemplateResponse)
from datetime import datetime, timezone

router = APIRouter()


@router.post("/templates", response_model=NotificationTemplateResponse)
async def create_template(
    template_data: NotificationTemplateCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Create a new notification template."""
    try:
        template = NotificationTemplate(
            id=str(uuid4()),
            tenant_id=tenant_id,
            **template_data.model_dump(),
            created_at=datetime.now(timezone.utc),
            is_active=True,
        )

        db.add(template)
        db.commit()
        db.refresh(template)

        return NotificationTemplateResponse(
            id=template.id,
            name=template.name,
            channel=template.channel,
            type=template.type,
            subject_template=template.subject_template,
            content_template=template.content_template,
            variables=template.variables,
            is_active=template.is_active,
            created_at=template.created_at,
            updated_at=template.updated_at,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create template: {str(e)}",
        )


@router.get("/templates/{template_id}", response_model=NotificationTemplateResponse)
async def get_template(
    template_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Get template by ID."""
    template = (
        db.query(NotificationTemplate)
        .filter(
            NotificationTemplate.id == template_id,
            NotificationTemplate.tenant_id == tenant_id,
        )
        .first()
    )

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template not found"
        )

    return NotificationTemplateResponse(
        id=template.id,
        name=template.name,
        channel=template.channel,
        type=template.type,
        subject_template=template.subject_template,
        content_template=template.content_template,
        variables=template.variables,
        is_active=template.is_active,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@router.get("/templates", response_model=List[NotificationTemplateResponse])
async def list_templates(
    channel: Optional[NotificationChannel] = Query(None),
    type: Optional[NotificationType] = Query(None),
    is_active: Optional[bool] = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """List notification templates with filtering."""
    query = db.query(NotificationTemplate).filter(
        NotificationTemplate.tenant_id == tenant_id
    )

    if channel:
        query = query.filter(NotificationTemplate.channel == channel)
    if type:
        query = query.filter(NotificationTemplate.type == type)
    if is_active is not None:
        query = query.filter(NotificationTemplate.is_active == is_active)

    templates = (
        query.order_by(NotificationTemplate.name).offset(offset).limit(limit).all()
    )

    return [
        NotificationTemplateResponse(
            id=t.id,
            name=t.name,
            channel=t.channel,
            type=t.type,
            subject_template=t.subject_template,
            content_template=t.content_template,
            variables=t.variables,
            is_active=t.is_active,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in templates
    ]


@router.put("/templates/{template_id}", response_model=NotificationTemplateResponse)
async def update_template(
    template_id: str,
    update_data: NotificationTemplateUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Update notification template."""
    template = (
        db.query(NotificationTemplate)
        .filter(
            NotificationTemplate.id == template_id,
            NotificationTemplate.tenant_id == tenant_id,
        )
        .first()
    )

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template not found"
        )

    # Update fields
    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(template, field, value)

    template.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(template)

    return NotificationTemplateResponse(
        id=template.id,
        name=template.name,
        channel=template.channel,
        type=template.type,
        subject_template=template.subject_template,
        content_template=template.content_template,
        variables=template.variables,
        is_active=template.is_active,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Delete notification template."""
    template = (
        db.query(NotificationTemplate)
        .filter(
            NotificationTemplate.id == template_id,
            NotificationTemplate.tenant_id == tenant_id,
        )
        .first()
    )

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template not found"
        )

    db.delete(template)
    db.commit()

    return {"message": "Template deleted successfully"}


@router.post("/templates/{template_id}/activate")
async def activate_template(
    template_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Activate notification template."""
    template = (
        db.query(NotificationTemplate)
        .filter(
            NotificationTemplate.id == template_id,
            NotificationTemplate.tenant_id == tenant_id,
        )
        .first()
    )

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template not found"
        )

    template.is_active = True
    template.updated_at = datetime.now(timezone.utc)

    db.commit()

    return {"message": "Template activated successfully"}


@router.post("/templates/{template_id}/deactivate")
async def deactivate_template(
    template_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Deactivate notification template."""
    template = (
        db.query(NotificationTemplate)
        .filter(
            NotificationTemplate.id == template_id,
            NotificationTemplate.tenant_id == tenant_id,
        )
        .first()
    )

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template not found"
        )

    template.is_active = False
    template.updated_at = datetime.now(timezone.utc)

    db.commit()

    return {"message": "Template deactivated successfully"}
