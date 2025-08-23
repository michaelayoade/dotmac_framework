"""Core notification API endpoints."""

import secrets
import string
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status
from sqlalchemy.orm import Session

from dotmac_isp.core.database import get_db
from dotmac_isp.shared.auth import get_current_tenant
from ..models import (
    Notification,
    NotificationDelivery,
    NotificationQueue,
    NotificationPriority,
    NotificationType,
    NotificationChannel,
    NotificationStatus,
)
from ..schemas import (
    NotificationCreate,
    NotificationUpdate,
    NotificationResponse,
    NotificationSendRequest,
    NotificationBulkSendRequest,
)

router = APIRouter()


def generate_notification_id() -> str:
    """Generate a unique notification ID."""
    timestamp = int(datetime.utcnow().timestamp())
    random_chars = "".join(
        secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6)
    )
    return f"NOT-{timestamp}-{random_chars}"


async def process_notification_delivery(notification_id: str, db: Session):
    """Background task to process notification delivery."""
    notification = (
        db.query(Notification).filter(Notification.id == notification_id).first()
    )
    if notification:
        notification.status = NotificationStatus.SENT
        notification.sent_at = datetime.utcnow()
        db.commit()


@router.post("/", response_model=NotificationResponse)
async def create_notification(
    notification_data: NotificationCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Create a new notification."""
    try:
        notification_id = generate_notification_id()

        notification = Notification(
            id=notification_id,
            tenant_id=tenant_id,
            **notification_data.dict(),
            created_at=datetime.utcnow(),
            status=NotificationStatus.PENDING,
        )

        db.add(notification)
        db.commit()
        db.refresh(notification)

        # Schedule delivery
        background_tasks.add_task(process_notification_delivery, notification_id, db)

        return NotificationResponse(
            id=notification.id,
            recipient=notification.recipient,
            channel=notification.channel,
            type=notification.type,
            priority=notification.priority,
            subject=notification.subject,
            content=notification.content,
            status=notification.status,
            created_at=notification.created_at,
            sent_at=notification.sent_at,
            metadata=notification.metadata,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create notification: {str(e)}",
        )


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Get notification by ID."""
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.tenant_id == tenant_id)
        .first()
    )

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )

    return NotificationResponse(
        id=notification.id,
        recipient=notification.recipient,
        channel=notification.channel,
        type=notification.type,
        priority=notification.priority,
        subject=notification.subject,
        content=notification.content,
        status=notification.status,
        created_at=notification.created_at,
        sent_at=notification.sent_at,
        metadata=notification.metadata,
    )


@router.get("/", response_model=List[NotificationResponse])
async def list_notifications(
    recipient: Optional[str] = Query(None),
    channel: Optional[NotificationChannel] = Query(None),
    type: Optional[NotificationType] = Query(None),
    status: Optional[NotificationStatus] = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """List notifications with filtering."""
    query = db.query(Notification).filter(Notification.tenant_id == tenant_id)

    if recipient:
        query = query.filter(Notification.recipient.contains(recipient))
    if channel:
        query = query.filter(Notification.channel == channel)
    if type:
        query = query.filter(Notification.type == type)
    if status:
        query = query.filter(Notification.status == status)

    notifications = (
        query.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()
    )

    return [
        NotificationResponse(
            id=n.id,
            recipient=n.recipient,
            channel=n.channel,
            type=n.type,
            priority=n.priority,
            subject=n.subject,
            content=n.content,
            status=n.status,
            created_at=n.created_at,
            sent_at=n.sent_at,
            metadata=n.metadata,
        )
        for n in notifications
    ]


@router.post("/send", response_model=Dict[str, str])
async def send_notification(
    send_request: NotificationSendRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Send a notification immediately."""
    try:
        notification_data = NotificationCreate(
            recipient=send_request.recipient,
            channel=send_request.channel,
            type=send_request.type,
            priority=send_request.priority,
            subject=send_request.subject,
            content=send_request.content,
            template_id=send_request.template_id,
            metadata=send_request.metadata or {},
        )

        notification_id = generate_notification_id()

        notification = Notification(
            id=notification_id,
            tenant_id=tenant_id,
            **notification_data.dict(),
            created_at=datetime.utcnow(),
            status=NotificationStatus.SENDING,
        )

        db.add(notification)
        db.commit()

        # Process immediately
        background_tasks.add_task(process_notification_delivery, notification_id, db)

        return {"notification_id": notification_id, "status": "queued"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to send notification: {str(e)}",
        )


@router.post("/bulk-send", response_model=Dict[str, Any])
async def bulk_send_notifications(
    bulk_request: NotificationBulkSendRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Send notifications to multiple recipients."""
    try:
        notification_ids = []

        for recipient in bulk_request.recipients:
            notification_data = NotificationCreate(
                recipient=recipient,
                channel=bulk_request.channel,
                type=bulk_request.type,
                priority=bulk_request.priority,
                subject=bulk_request.subject,
                content=bulk_request.content,
                template_id=bulk_request.template_id,
                metadata=bulk_request.metadata or {},
            )

            notification_id = generate_notification_id()

            notification = Notification(
                id=notification_id,
                tenant_id=tenant_id,
                **notification_data.dict(),
                created_at=datetime.utcnow(),
                status=NotificationStatus.PENDING,
            )

            db.add(notification)
            notification_ids.append(notification_id)

        db.commit()

        # Schedule all deliveries
        for notification_id in notification_ids:
            background_tasks.add_task(
                process_notification_delivery, notification_id, db
            )

        return {
            "notification_ids": notification_ids,
            "total_count": len(notification_ids),
            "status": "queued",
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to send bulk notifications: {str(e)}",
        )


@router.put("/{notification_id}", response_model=NotificationResponse)
async def update_notification(
    notification_id: str,
    update_data: NotificationUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Update notification."""
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.tenant_id == tenant_id)
        .first()
    )

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )

    # Update fields
    for field, value in update_data.dict(exclude_unset=True).items():
        setattr(notification, field, value)

    notification.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(notification)

    return NotificationResponse(
        id=notification.id,
        recipient=notification.recipient,
        channel=notification.channel,
        type=notification.type,
        priority=notification.priority,
        subject=notification.subject,
        content=notification.content,
        status=notification.status,
        created_at=notification.created_at,
        sent_at=notification.sent_at,
        metadata=notification.metadata,
    )


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Delete notification."""
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.tenant_id == tenant_id)
        .first()
    )

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )

    db.delete(notification)
    db.commit()

    return {"message": "Notification deleted successfully"}


@router.post("/{notification_id}/retry")
async def retry_notification(
    notification_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Retry failed notification."""
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.tenant_id == tenant_id)
        .first()
    )

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )

    if notification.status not in [
        NotificationStatus.FAILED,
        NotificationStatus.EXPIRED,
    ]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only failed or expired notifications can be retried",
        )

    # Reset status and retry
    notification.status = NotificationStatus.PENDING
    notification.retry_count = (notification.retry_count or 0) + 1
    notification.updated_at = datetime.utcnow()

    db.commit()

    # Schedule retry
    background_tasks.add_task(process_notification_delivery, notification_id, db)

    return {
        "message": "Notification retry scheduled",
        "retry_count": notification.retry_count,
    }
