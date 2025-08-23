"""Notification system API endpoints."""

import secrets
import string
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

from dotmac_isp.core.database import get_db
from dotmac_isp.shared.auth import get_current_tenant
from .models import (
    NotificationTemplate,
    NotificationRule,
    Notification,
    NotificationDelivery,
    NotificationPreference,
    NotificationQueue,
    NotificationLog,
    NotificationPriority,
    NotificationType,
    NotificationChannel,
    NotificationStatus,
)
from .schemas import (
    NotificationTemplateCreate,
    NotificationTemplateUpdate,
    NotificationTemplateResponse,
    NotificationRuleCreate,
    NotificationRuleUpdate,
    NotificationRuleResponse,
    NotificationCreate,
    NotificationUpdate,
    NotificationResponse,
    NotificationDeliveryCreate,
    NotificationDeliveryResponse,
    NotificationPreferenceCreate,
    NotificationPreferenceUpdate,
    NotificationPreferenceResponse,
    NotificationSendRequest,
    NotificationBulkSendRequest,
    NotificationStatsResponse,
    NotificationDashboardResponse,
    NotificationQueueResponse,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


def generate_notification_id() -> str:
    """Generate a unique notification ID."""
    timestamp = int(datetime.utcnow().timestamp())
    random_chars = "".join(
        secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6)
    )
    return f"NOT-{timestamp}-{random_chars}"


async def process_notification_delivery(notification_id: str, db: Session):
    """Background task to process notification delivery."""
    # This would integrate with actual delivery providers
    # For now, we'll just update the status
    notification = (
        db.query(Notification).filter(Notification.id == notification_id).first()
    )
    if notification:
        notification.status = NotificationStatus.SENT
        notification.sent_at = datetime.utcnow()
        db.commit()


# Template Management
@router.post("/templates", response_model=NotificationTemplateResponse)
async def create_template(
    template: NotificationTemplateCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Create a new notification template."""

    # Check if template code already exists for this tenant
    existing = (
        db.query(NotificationTemplate)
        .filter(
            and_(
                NotificationTemplate.tenant_id == tenant_id,
                NotificationTemplate.template_code == template.template_code,
            )
        )
        .first()
    )

    if existing:
        raise HTTPException(status_code=400, detail="Template code already exists")

    db_template = NotificationTemplate(
        id=str(uuid4()), tenant_id=tenant_id, **template.dict()
    )

    db.add(db_template)
    db.commit()
    db.refresh(db_template)

    return db_template


@router.get("/templates", response_model=List[NotificationTemplateResponse])
async def list_templates(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    notification_type: Optional[NotificationType] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """List notification templates."""

    query = db.query(NotificationTemplate).filter(
        NotificationTemplate.tenant_id == tenant_id
    )

    if notification_type:
        query = query.filter(
            NotificationTemplate.notification_type == notification_type
        )
    if is_active is not None:
        query = query.filter(NotificationTemplate.is_active == is_active)

    templates = (
        query.order_by(desc(NotificationTemplate.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return templates


@router.get("/templates/{template_id}", response_model=NotificationTemplateResponse)
async def get_template(
    template_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Get a specific notification template."""

    template = (
        db.query(NotificationTemplate)
        .filter(
            and_(
                NotificationTemplate.id == template_id,
                NotificationTemplate.tenant_id == tenant_id,
            )
        )
        .first()
    )

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return template


@router.put("/templates/{template_id}", response_model=NotificationTemplateResponse)
async def update_template(
    template_id: str,
    template_update: NotificationTemplateUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Update a notification template."""

    template = (
        db.query(NotificationTemplate)
        .filter(
            and_(
                NotificationTemplate.id == template_id,
                NotificationTemplate.tenant_id == tenant_id,
            )
        )
        .first()
    )

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Update only provided fields
    for field, value in template_update.dict(exclude_unset=True).items():
        setattr(template, field, value)

    template.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(template)

    return template


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Delete a notification template."""

    template = (
        db.query(NotificationTemplate)
        .filter(
            and_(
                NotificationTemplate.id == template_id,
                NotificationTemplate.tenant_id == tenant_id,
            )
        )
        .first()
    )

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Check if template is in use
    notifications_count = (
        db.query(Notification).filter(Notification.template_id == template_id).count()
    )

    if notifications_count > 0:
        raise HTTPException(
            status_code=400, detail="Template is in use and cannot be deleted"
        )

    db.delete(template)
    db.commit()

    return {"message": "Template deleted successfully"}


# Rule Management
@router.post("/rules", response_model=NotificationRuleResponse)
async def create_rule(
    rule: NotificationRuleCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Create a new notification rule."""

    # Verify template exists
    template = (
        db.query(NotificationTemplate)
        .filter(
            and_(
                NotificationTemplate.id == rule.template_id,
                NotificationTemplate.tenant_id == tenant_id,
            )
        )
        .first()
    )

    if not template:
        raise HTTPException(status_code=400, detail="Template not found")

    db_rule = NotificationRule(id=str(uuid4()), tenant_id=tenant_id, **rule.dict())

    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)

    return db_rule


@router.get("/rules", response_model=List[NotificationRuleResponse])
async def list_rules(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    event_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """List notification rules."""

    query = db.query(NotificationRule).filter(NotificationRule.tenant_id == tenant_id)

    if event_type:
        query = query.filter(NotificationRule.event_type == event_type)
    if is_active is not None:
        query = query.filter(NotificationRule.is_active == is_active)

    rules = (
        query.order_by(desc(NotificationRule.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return rules


@router.get("/rules/{rule_id}", response_model=NotificationRuleResponse)
async def get_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Get a specific notification rule."""

    rule = (
        db.query(NotificationRule)
        .filter(
            and_(
                NotificationRule.id == rule_id, NotificationRule.tenant_id == tenant_id
            )
        )
        .first()
    )

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    return rule


@router.put("/rules/{rule_id}", response_model=NotificationRuleResponse)
async def update_rule(
    rule_id: str,
    rule_update: NotificationRuleUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Update a notification rule."""

    rule = (
        db.query(NotificationRule)
        .filter(
            and_(
                NotificationRule.id == rule_id, NotificationRule.tenant_id == tenant_id
            )
        )
        .first()
    )

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    # Update only provided fields
    for field, value in rule_update.dict(exclude_unset=True).items():
        setattr(rule, field, value)

    rule.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(rule)

    return rule


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Delete a notification rule."""

    rule = (
        db.query(NotificationRule)
        .filter(
            and_(
                NotificationRule.id == rule_id, NotificationRule.tenant_id == tenant_id
            )
        )
        .first()
    )

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    db.delete(rule)
    db.commit()

    return {"message": "Rule deleted successfully"}


# Notification Management
@router.post("/send", response_model=NotificationResponse)
async def send_notification(
    send_request: NotificationSendRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Send a single notification."""

    # Get template
    template = (
        db.query(NotificationTemplate)
        .filter(
            and_(
                NotificationTemplate.template_code == send_request.template_code,
                NotificationTemplate.tenant_id == tenant_id,
                NotificationTemplate.is_active == True,
            )
        )
        .first()
    )

    if not template:
        raise HTTPException(status_code=404, detail="Template not found or inactive")

    # Create notification
    notification_id = generate_notification_id()

    # Process template with variables
    subject = template.subject_template
    body = template.body_template
    html_body = template.html_template

    if send_request.variables:
        for key, value in send_request.variables.items():
            if subject:
                subject = subject.replace(f"{{{key}}}", str(value))
            body = body.replace(f"{{{key}}}", str(value))
            if html_body:
                html_body = html_body.replace(f"{{{key}}}", str(value))

    db_notification = Notification(
        id=str(uuid4()),
        tenant_id=tenant_id,
        notification_id=notification_id,
        template_id=template.id,
        notification_type=template.notification_type,
        priority=send_request.priority,
        subject=subject,
        body=body,
        html_body=html_body,
        recipient_type=send_request.recipient_type,
        recipient_id=send_request.recipient_id,
        recipient_email=send_request.recipient_email,
        recipient_phone=send_request.recipient_phone,
        recipient_name=send_request.recipient_name,
        channels=send_request.channels or template.supported_channels,
        preferred_channel=(
            send_request.channels[0]
            if send_request.channels
            else template.default_channel
        ),
        scheduled_at=send_request.scheduled_at,
        notification_metadata=send_request.notification_metadata,
        variables=send_request.variables,
        status=NotificationStatus.PENDING,
    )

    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)

    # Queue for background processing
    background_tasks.add_task(process_notification_delivery, db_notification.id, db)

    return db_notification


@router.post("/send/bulk")
async def send_bulk_notifications(
    bulk_request: NotificationBulkSendRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Send bulk notifications."""

    # Get template
    template = (
        db.query(NotificationTemplate)
        .filter(
            and_(
                NotificationTemplate.template_code == bulk_request.template_code,
                NotificationTemplate.tenant_id == tenant_id,
                NotificationTemplate.is_active == True,
            )
        )
        .first()
    )

    if not template:
        raise HTTPException(status_code=404, detail="Template not found or inactive")

    notification_ids = []

    # Process recipients in batches
    for i in range(0, len(bulk_request.recipients), bulk_request.batch_size):
        batch = bulk_request.recipients[i : i + bulk_request.batch_size]

        for recipient_data in batch:
            notification_id = generate_notification_id()

            # Merge common and recipient-specific variables
            variables = {
                **(bulk_request.variables or {}),
                **recipient_data.get("variables", {}),
            }

            # Process template with variables
            subject = template.subject_template
            body = template.body_template
            html_body = template.html_template

            for key, value in variables.items():
                if subject:
                    subject = subject.replace(f"{{{key}}}", str(value))
                body = body.replace(f"{{{key}}}", str(value))
                if html_body:
                    html_body = html_body.replace(f"{{{key}}}", str(value))

            db_notification = Notification(
                id=str(uuid4()),
                tenant_id=tenant_id,
                notification_id=notification_id,
                template_id=template.id,
                notification_type=template.notification_type,
                priority=bulk_request.priority,
                subject=subject,
                body=body,
                html_body=html_body,
                recipient_type=recipient_data.get("recipient_type", "user"),
                recipient_id=recipient_data.get("recipient_id"),
                recipient_email=recipient_data.get("recipient_email"),
                recipient_phone=recipient_data.get("recipient_phone"),
                recipient_name=recipient_data.get("recipient_name"),
                channels=bulk_request.channels or template.supported_channels,
                preferred_channel=(
                    bulk_request.channels[0]
                    if bulk_request.channels
                    else template.default_channel
                ),
                scheduled_at=bulk_request.scheduled_at,
                notification_metadata=recipient_data.get("metadata"),
                variables=variables,
                status=NotificationStatus.PENDING,
            )

            db.add(db_notification)
            notification_ids.append(notification_id)

        db.commit()

    return {
        "message": f"Queued {len(notification_ids)} notifications",
        "notification_ids": notification_ids,
    }


@router.get("/", response_model=List[NotificationResponse])
async def list_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[NotificationStatus] = None,
    notification_type: Optional[NotificationType] = None,
    priority: Optional[NotificationPriority] = None,
    recipient_type: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """List notifications."""

    query = db.query(Notification).filter(Notification.tenant_id == tenant_id)

    if status:
        query = query.filter(Notification.status == status)
    if notification_type:
        query = query.filter(Notification.notification_type == notification_type)
    if priority:
        query = query.filter(Notification.priority == priority)
    if recipient_type:
        query = query.filter(Notification.recipient_type == recipient_type)

    notifications = (
        query.order_by(desc(Notification.created_at)).offset(skip).limit(limit).all()
    )
    return notifications


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Get a specific notification."""

    notification = (
        db.query(Notification)
        .filter(
            and_(
                or_(
                    Notification.id == notification_id,
                    Notification.notification_id == notification_id,
                ),
                Notification.tenant_id == tenant_id,
            )
        )
        .first()
    )

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    return notification


@router.put("/{notification_id}", response_model=NotificationResponse)
async def update_notification(
    notification_id: str,
    notification_update: NotificationUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Update a notification."""

    notification = (
        db.query(Notification)
        .filter(
            and_(
                or_(
                    Notification.id == notification_id,
                    Notification.notification_id == notification_id,
                ),
                Notification.tenant_id == tenant_id,
            )
        )
        .first()
    )

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    # Update only provided fields
    for field, value in notification_update.dict(exclude_unset=True).items():
        setattr(notification, field, value)

    notification.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(notification)

    return notification


@router.post("/{notification_id}/retry")
async def retry_notification(
    notification_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Retry a failed notification."""

    notification = (
        db.query(Notification)
        .filter(
            and_(
                or_(
                    Notification.id == notification_id,
                    Notification.notification_id == notification_id,
                ),
                Notification.tenant_id == tenant_id,
            )
        )
        .first()
    )

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    if notification.status not in [
        NotificationStatus.FAILED,
        NotificationStatus.CANCELLED,
    ]:
        raise HTTPException(status_code=400, detail="Notification cannot be retried")

    if notification.retry_count >= notification.max_retries:
        raise HTTPException(status_code=400, detail="Maximum retries exceeded")

    # Reset status and schedule retry
    notification.status = NotificationStatus.PENDING
    notification.retry_count += 1
    notification.next_retry_at = datetime.utcnow() + timedelta(minutes=5)
    notification.updated_at = datetime.utcnow()

    db.commit()

    # Queue for background processing
    background_tasks.add_task(process_notification_delivery, notification.id, db)

    return {"message": "Notification queued for retry"}


# Delivery Management
@router.get(
    "/{notification_id}/deliveries", response_model=List[NotificationDeliveryResponse]
)
async def get_notification_deliveries(
    notification_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Get delivery attempts for a notification."""

    # First verify notification exists
    notification = (
        db.query(Notification)
        .filter(
            and_(
                or_(
                    Notification.id == notification_id,
                    Notification.notification_id == notification_id,
                ),
                Notification.tenant_id == tenant_id,
            )
        )
        .first()
    )

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    deliveries = (
        db.query(NotificationDelivery)
        .filter(NotificationDelivery.notification_id == notification.id)
        .order_by(desc(NotificationDelivery.attempted_at))
        .all()
    )

    return deliveries


# Preferences Management
@router.post("/preferences", response_model=NotificationPreferenceResponse)
async def create_preference(
    preference: NotificationPreferenceCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Create a notification preference."""

    # Check if preference already exists
    existing = (
        db.query(NotificationPreference)
        .filter(
            and_(
                NotificationPreference.tenant_id == tenant_id,
                NotificationPreference.user_id == preference.user_id,
                NotificationPreference.notification_type
                == preference.notification_type,
            )
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Preference already exists for this user and notification type",
        )

    db_preference = NotificationPreference(
        id=str(uuid4()), tenant_id=tenant_id, **preference.dict()
    )

    db.add(db_preference)
    db.commit()
    db.refresh(db_preference)

    return db_preference


@router.get("/preferences", response_model=List[NotificationPreferenceResponse])
async def list_preferences(
    user_id: Optional[str] = None,
    notification_type: Optional[NotificationType] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """List notification preferences."""

    query = db.query(NotificationPreference).filter(
        NotificationPreference.tenant_id == tenant_id
    )

    if user_id:
        query = query.filter(NotificationPreference.user_id == user_id)
    if notification_type:
        query = query.filter(
            NotificationPreference.notification_type == notification_type
        )

    preferences = (
        query.order_by(desc(NotificationPreference.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return preferences


@router.get(
    "/preferences/{preference_id}", response_model=NotificationPreferenceResponse
)
async def get_preference(
    preference_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Get a specific notification preference."""

    preference = (
        db.query(NotificationPreference)
        .filter(
            and_(
                NotificationPreference.id == preference_id,
                NotificationPreference.tenant_id == tenant_id,
            )
        )
        .first()
    )

    if not preference:
        raise HTTPException(status_code=404, detail="Preference not found")

    return preference


@router.put(
    "/preferences/{preference_id}", response_model=NotificationPreferenceResponse
)
async def update_preference(
    preference_id: str,
    preference_update: NotificationPreferenceUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Update a notification preference."""

    preference = (
        db.query(NotificationPreference)
        .filter(
            and_(
                NotificationPreference.id == preference_id,
                NotificationPreference.tenant_id == tenant_id,
            )
        )
        .first()
    )

    if not preference:
        raise HTTPException(status_code=404, detail="Preference not found")

    # Update only provided fields
    for field, value in preference_update.dict(exclude_unset=True).items():
        setattr(preference, field, value)

    preference.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(preference)

    return preference


@router.delete("/preferences/{preference_id}")
async def delete_preference(
    preference_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Delete a notification preference."""

    preference = (
        db.query(NotificationPreference)
        .filter(
            and_(
                NotificationPreference.id == preference_id,
                NotificationPreference.tenant_id == tenant_id,
            )
        )
        .first()
    )

    if not preference:
        raise HTTPException(status_code=404, detail="Preference not found")

    db.delete(preference)
    db.commit()

    return {"message": "Preference deleted successfully"}


# Statistics and Dashboard
@router.get("/stats/overview", response_model=NotificationStatsResponse)
async def get_notification_stats(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Get notification statistics."""

    since_date = datetime.utcnow() - timedelta(days=days)

    # Basic counts
    total_notifications = (
        db.query(Notification)
        .filter(
            and_(
                Notification.tenant_id == tenant_id,
                Notification.created_at >= since_date,
            )
        )
        .count()
    )

    status_counts = (
        db.query(Notification.status, func.count(Notification.id))
        .filter(
            and_(
                Notification.tenant_id == tenant_id,
                Notification.created_at >= since_date,
            )
        )
        .group_by(Notification.status)
        .all()
    )

    status_dict = {status.value: 0 for status in NotificationStatus}
    for status, count in status_counts:
        status_dict[status.value] = count

    # Channel statistics
    channel_stats = {}
    deliveries = (
        db.query(
            NotificationDelivery.channel,
            NotificationDelivery.status,
            func.count(NotificationDelivery.id),
        )
        .join(Notification)
        .filter(
            and_(
                Notification.tenant_id == tenant_id,
                Notification.created_at >= since_date,
            )
        )
        .group_by(NotificationDelivery.channel, NotificationDelivery.status)
        .all()
    )

    for channel, status, count in deliveries:
        if channel.value not in channel_stats:
            channel_stats[channel.value] = {}
        channel_stats[channel.value][status.value] = count

    # Type statistics
    type_stats = {}
    type_counts = (
        db.query(
            Notification.notification_type,
            Notification.status,
            func.count(Notification.id),
        )
        .filter(
            and_(
                Notification.tenant_id == tenant_id,
                Notification.created_at >= since_date,
            )
        )
        .group_by(Notification.notification_type, Notification.status)
        .all()
    )

    for ntype, status, count in type_counts:
        if ntype.value not in type_stats:
            type_stats[ntype.value] = {}
        type_stats[ntype.value][status.value] = count

    # Calculate delivery rate
    delivered = status_dict.get(NotificationStatus.DELIVERED.value, 0)
    delivery_rate = (
        (delivered / total_notifications * 100) if total_notifications > 0 else 0
    )

    # Average delivery time
    avg_delivery_time = (
        db.query(
            func.avg(
                func.extract(
                    "epoch",
                    NotificationDelivery.completed_at
                    - NotificationDelivery.attempted_at,
                )
                * 1000
            )
        )
        .join(Notification)
        .filter(
            and_(
                Notification.tenant_id == tenant_id,
                Notification.created_at >= since_date,
                NotificationDelivery.completed_at.isnot(None),
            )
        )
        .scalar()
    )

    return NotificationStatsResponse(
        total_notifications=total_notifications,
        pending_notifications=status_dict.get(NotificationStatus.PENDING.value, 0),
        sent_notifications=status_dict.get(NotificationStatus.SENT.value, 0),
        delivered_notifications=status_dict.get(NotificationStatus.DELIVERED.value, 0),
        failed_notifications=status_dict.get(NotificationStatus.FAILED.value, 0),
        delivery_rate=delivery_rate,
        avg_delivery_time_ms=avg_delivery_time,
        channel_stats=channel_stats,
        type_stats=type_stats,
    )


@router.get("/dashboard", response_model=NotificationDashboardResponse)
async def get_dashboard(
    db: Session = Depends(get_db), tenant_id: str = Depends(get_current_tenant)
):
    """Get notification dashboard data."""

    # Get overall stats
    stats = await get_notification_stats(days=7, db=db, tenant_id=tenant_id)

    # Recent notifications
    recent_notifications = (
        db.query(Notification)
        .filter(Notification.tenant_id == tenant_id)
        .order_by(desc(Notification.created_at))
        .limit(10)
        .all()
    )

    # Recent failed deliveries
    failed_deliveries = (
        db.query(NotificationDelivery)
        .join(Notification)
        .filter(
            and_(
                Notification.tenant_id == tenant_id,
                NotificationDelivery.status == "failed",
            )
        )
        .order_by(desc(NotificationDelivery.attempted_at))
        .limit(10)
        .all()
    )

    # Top templates
    top_templates = (
        db.query(
            NotificationTemplate.template_name,
            NotificationTemplate.template_code,
            func.count(Notification.id).label("usage_count"),
        )
        .join(Notification)
        .filter(Notification.tenant_id == tenant_id)
        .group_by(
            NotificationTemplate.template_name, NotificationTemplate.template_code
        )
        .order_by(desc("usage_count"))
        .limit(5)
        .all()
    )

    top_templates_list = [
        {"template_name": name, "template_code": code, "usage_count": count}
        for name, code, count in top_templates
    ]

    # Alert summary
    alert_summary = {}
    alert_counts = (
        db.query(Notification.notification_type, func.count(Notification.id))
        .filter(
            and_(
                Notification.tenant_id == tenant_id,
                Notification.notification_type.in_(
                    [
                        NotificationType.SYSTEM_ALERT,
                        NotificationType.NETWORK_ALERT,
                        NotificationType.BILLING_ALERT,
                        NotificationType.SERVICE_ALERT,
                        NotificationType.SECURITY_ALERT,
                    ]
                ),
            )
        )
        .group_by(Notification.notification_type)
        .all()
    )

    for ntype, count in alert_counts:
        alert_summary[ntype.value] = count

    return NotificationDashboardResponse(
        stats=stats,
        recent_notifications=recent_notifications,
        failed_deliveries=failed_deliveries,
        top_templates=top_templates_list,
        alert_summary=alert_summary,
    )


@router.get("/queue/status", response_model=List[NotificationQueueResponse])
async def get_queue_status(
    db: Session = Depends(get_db), tenant_id: str = Depends(get_current_tenant)
):
    """Get notification queue status."""

    queue_stats = (
        db.query(
            NotificationQueue.queue_name,
            NotificationQueue.status,
            func.count(NotificationQueue.id).label("count"),
            func.min(NotificationQueue.scheduled_at).label("oldest_scheduled"),
        )
        .filter(NotificationQueue.tenant_id == tenant_id)
        .group_by(NotificationQueue.queue_name, NotificationQueue.status)
        .all()
    )

    # Group by queue name
    queue_data = {}
    for queue_name, status, count, oldest_scheduled in queue_stats:
        if queue_name not in queue_data:
            queue_data[queue_name] = {
                "total_items": 0,
                "pending_items": 0,
                "processing_items": 0,
                "failed_items": 0,
                "oldest_scheduled": oldest_scheduled,
            }

        queue_data[queue_name]["total_items"] += count
        if status == "queued":
            queue_data[queue_name]["pending_items"] = count
        elif status == "processing":
            queue_data[queue_name]["processing_items"] = count
        elif status == "failed":
            queue_data[queue_name]["failed_items"] = count

        # Track oldest item
        if oldest_scheduled and (
            not queue_data[queue_name]["oldest_scheduled"]
            or oldest_scheduled < queue_data[queue_name]["oldest_scheduled"]
        ):
            queue_data[queue_name]["oldest_scheduled"] = oldest_scheduled

    # Calculate age in seconds for oldest item
    now = datetime.utcnow()
    queue_responses = []
    for queue_name, data in queue_data.items():
        oldest_age = None
        if data["oldest_scheduled"]:
            oldest_age = int((now - data["oldest_scheduled"]).total_seconds())

        queue_responses.append(
            NotificationQueueResponse(
                queue_name=queue_name,
                total_items=data["total_items"],
                pending_items=data["pending_items"],
                processing_items=data["processing_items"],
                failed_items=data["failed_items"],
                oldest_item_age_seconds=oldest_age,
            )
        )

    return queue_responses
