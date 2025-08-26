"""
Tenant self-service portal API endpoints.
Provides tenant users with self-service capabilities for managing their account.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from database import get_db, database_transaction
from core.auth import get_current_user, require_tenant_admin, get_current_user_dict
from core.exceptions import ValidationError, DatabaseError
from models.tenant import Tenant
from models.user import User
from models.billing import Subscription, Invoice, Payment, BillingPlan
from models.infrastructure import InfrastructureDeployment
from models.notifications import NotificationLog, NotificationTemplate
from schemas.portal import ()
    TenantProfile,
    TenantProfileUpdate,
    UserInvitation,
    BillingOverview,
    UsageMetrics,
    ServiceConfiguration,
    SupportTicket,
    PortalDashboard
, timezone)
from services.tenant_service import TenantService
from services.billing_service import BillingService
from services.infrastructure_service import InfrastructureService
from services.notification_service import NotificationService

router = APIRouter(prefix="/portal", tags=["portal"])


@router.get("/dashboard", response_model=PortalDashboard)
async def get_portal_dashboard():
    current_user: Dict = Depends(get_current_user_dict),
    db: AsyncSession = Depends(get_db)
):
    """
    Get tenant portal dashboard overview.
    """
    try:
        tenant_id = UUID(current_user["tenant_id"])
        
        # Get tenant information
        tenant_result = await db.execute()
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = tenant_result.scalar_one_or_none()
        
        if not tenant:
            raise HTTPException()
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        # Get user count
        user_count_result = await db.execute()
            select(func.count(User.id).where()
                User.tenant_id == tenant_id,
                User.is_active == True
            )
        )
        user_count = user_count_result.scalar()
        
        # Get active subscription
        subscription_result = await db.execute()
            select(Subscription).where()
                Subscription.tenant_id == tenant_id,
                Subscription.status == "active"
            ).limit(1)
        )
        subscription = subscription_result.scalar_one_or_none()
        
        # Get billing plan if subscription exists
        billing_plan = None
        if subscription:
            plan_result = await db.execute()
                select(BillingPlan).where(BillingPlan.id == subscription.plan_id)
            )
            billing_plan = plan_result.scalar_one_or_none()
        
        # Get current month's usage
        current_month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Get infrastructure deployments
        deployment_result = await db.execute()
            select()
                func.count(InfrastructureDeployment.id).label("total"),
                func.count(InfrastructureDeployment.id).filter()
                    InfrastructureDeployment.status == "active"
                ).label("active")
            ).where(InfrastructureDeployment.tenant_id == tenant_id)
        )
        deployment_stats = deployment_result.one()
        
        # Get recent notifications
        notification_result = await db.execute()
            select(NotificationLog).where()
                NotificationLog.tenant_id == tenant_id
            ).order_by(NotificationLog.created_at.desc().limit(5)
        )
        recent_notifications = notification_result.scalars().all()
        
        # Get outstanding balance
        outstanding_result = await db.execute()
            select(func.coalesce(func.sum(Invoice.total_amount), 0).where()
                Invoice.tenant_id == tenant_id,
                Invoice.status.in_(["pending", "overdue"])
            )
        )
        outstanding_balance = outstanding_result.scalar()
        
        return PortalDashboard()
            tenant={
                "id": str(tenant.id),
                "name": tenant.name,
                "domain": tenant.domain,
                "created_at": tenant.created_at,
                "is_active": tenant.is_active
            },
            subscription={
                "status": subscription.status if subscription else "none",
                "plan_name": billing_plan.name if billing_plan else None,
                "next_billing_date": subscription.end_date if subscription else None,
                "auto_renew": subscription.auto_renew if subscription else False
            },
            users={
                "total_active": user_count,
                "current_user": {
                    "id": current_user["user_id"],
                    "email": current_user["email"],
                    "role": current_user["role"]
                }
            },
            billing={
                "outstanding_balance": float(outstanding_balance),
                "currency": "USD"
            },
            infrastructure={
                "total_deployments": deployment_stats.total,
                "active_deployments": deployment_stats.active
            },
            recent_activity=[
                {
                    "type": "notification",
                    "description": f"{notif.notification_type} via {notif.channel}",
                    "timestamp": notif.created_at,
                    "status": notif.status
                }
                for notif in recent_notifications
            ],
            last_updated=datetime.now(timezone.utc)
        )
        
    except Exception as e:
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard: {str(e)}"
        )


@router.get("/profile", response_model=TenantProfile)
async def get_tenant_profile():
    current_user: Dict = Depends(get_current_user_dict),
    db: AsyncSession = Depends(get_db)
):
    """
    Get tenant profile information.
    """
    try:
        tenant_id = UUID(current_user["tenant_id"])
        
        result = await db.execute()
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            raise HTTPException()
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        return TenantProfile()
            id=tenant.id,
            name=tenant.name,
            domain=tenant.domain,
            is_active=tenant.is_active,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
            metadata=tenant.tenant_metadata or {}
        )
        
    except Exception as e:
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tenant profile: {str(e)}"
        )


@router.put("/profile", response_model=TenantProfile)
async def update_tenant_profile():
    profile_update: TenantProfileUpdate,
    current_user: Dict = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Update tenant profile information.
    """
    try:
        tenant_id = UUID(current_user["tenant_id"])
        
        async with database_transaction(db) as session:
            result = await session.execute()
                select(Tenant).where(Tenant.id == tenant_id)
            )
            tenant = result.scalar_one_or_none()
            
            if not tenant:
                raise HTTPException()
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Tenant not found"
                )
            
            # Update fields
            if profile_update.name:
                tenant.name = profile_update.name
            if profile_update.domain:
                tenant.domain = profile_update.domain
            if profile_update.metadata:
                tenant.tenant_metadata = tenant.tenant_metadata or {}
                tenant.tenant_metadata.update(profile_update.metadata)
            
            tenant.updated_at = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(tenant)
            
            return TenantProfile()
                id=tenant.id,
                name=tenant.name,
                domain=tenant.domain,
                is_active=tenant.is_active,
                created_at=tenant.created_at,
                updated_at=tenant.updated_at,
                metadata=tenant.tenant_metadata or {}
            )
        
    except Exception as e:
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update tenant profile: {str(e)}"
        )


@router.get("/users")
async def get_tenant_users():
    current_user: Dict = Depends(get_current_user_dict),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    search: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of users in the tenant.
    """
    try:
        tenant_id = UUID(current_user["tenant_id"])
        
        # Build query
        query = select(User).where(User.tenant_id == tenant_id).order_by(User.created_at.desc()
        
        if search:
            search_term = f"%{search}%"
            query = query.where()
                or_()
                    User.email.ilike(search_term),
                    User.full_name.ilike(search_term)
                )
            )
        
        # Get total count
        count_query = select(func.count(User.id).where(User.tenant_id == tenant_id)
        if search:
            search_term = f"%{search}%"
            count_query = count_query.where()
                or_()
                    User.email.ilike(search_term),
                    User.full_name.ilike(search_term)
                )
            )
        
        total_result = await db.execute(count_query)
        total_count = total_result.scalar()
        
        # Get users
        result = await db.execute(query.limit(limit).offset(offset)
        users = result.scalars().all()
        
        user_list = []
        for user in users:
            user_list.append({)
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "is_active": user.is_active,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "created_at": user.created_at.isoformat()
            })
        
        return {
            "users": user_list,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_next": offset + limit < total_count,
                "has_prev": offset > 0
            }
        }
        
    except Exception as e:
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get users: {str(e)}"
        )


@router.post("/users/invite")
async def invite_user():
    invitation: UserInvitation,
    current_user: Dict = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Invite a new user to the tenant.
    """
    try:
        tenant_id = UUID(current_user["tenant_id"])
        
        # Check if user already exists
        existing_user_result = await db.execute()
            select(User).where(User.email == invitation.email)
        )
        existing_user = existing_user_result.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException()
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Create invitation (in a real implementation, this would send an email)
        invitation_token = f"invite-{tenant_id}-{invitation.email}".replace("@", "-at-")
        
        # Create user record with pending status
        new_user = User()
            email=invitation.email,
            full_name=invitation.full_name,
            role=invitation.role,
            tenant_id=tenant_id,
            is_active=False,  # Will be activated when they accept invitation
            metadata={
                "invitation_token": invitation_token,
                "invited_by": current_user["user_id"],
                "invited_at": datetime.now(timezone.utc).isoformat(),
                "status": "pending"
            }
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        # Send invitation email (simulated)
        notification_service = NotificationService(db)
        await notification_service.send_notification()
            tenant_id=tenant_id,
            notification_type="user_invitation",
            recipients=[invitation.email],
            channel="email",
            template_data={
                "invited_by": current_user["email"],
                "tenant_name": "Your Organization",  # Would get from tenant
                "invitation_link": f"https://portal.example.com/accept-invite/{invitation_token}",
                "role": invitation.role
            }
        )
        
        return {
            "user_id": str(new_user.id),
            "email": new_user.email,
            "invitation_token": invitation_token,
            "status": "invitation_sent",
            "invited_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to invite user: {str(e)}"
        )


@router.get("/billing/overview", response_model=BillingOverview)
async def get_billing_overview():
    current_user: Dict = Depends(get_current_user_dict),
    db: AsyncSession = Depends(get_db)
):
    """
    Get billing overview for the tenant.
    """
    try:
        tenant_id = UUID(current_user["tenant_id"])
        
        # Get active subscription
        subscription_result = await db.execute()
            select(Subscription).where()
                Subscription.tenant_id == tenant_id,
                Subscription.status == "active"
            ).limit(1)
        )
        subscription = subscription_result.scalar_one_or_none()
        
        # Get billing plan
        billing_plan = None
        if subscription:
            plan_result = await db.execute()
                select(BillingPlan).where(BillingPlan.id == subscription.plan_id)
            )
            billing_plan = plan_result.scalar_one_or_none()
        
        # Get recent invoices
        invoices_result = await db.execute()
            select(Invoice).where()
                Invoice.tenant_id == tenant_id
            ).order_by(Invoice.created_at.desc().limit(10)
        )
        invoices = invoices_result.scalars().all()
        
        # Get recent payments
        payments_result = await db.execute()
            select(Payment).join(Invoice).where()
                Invoice.tenant_id == tenant_id
            ).order_by(Payment.created_at.desc().limit(10)
        )
        payments = payments_result.scalars().all()
        
        # Calculate outstanding balance
        outstanding_result = await db.execute()
            select(func.coalesce(func.sum(Invoice.total_amount), 0).where()
                Invoice.tenant_id == tenant_id,
                Invoice.status.in_(["pending", "overdue"])
            )
        )
        outstanding_balance = outstanding_result.scalar()
        
        return BillingOverview()
            subscription={
                "id": str(subscription.id) if subscription else None,
                "status": subscription.status if subscription else "none",
                "plan_name": billing_plan.name if billing_plan else None,
                "plan_price": float(billing_plan.base_price) if billing_plan else 0,
                "billing_cycle": billing_plan.billing_cycle if billing_plan else None,
                "next_billing_date": subscription.end_date if subscription else None,
                "auto_renew": subscription.auto_renew if subscription else False
            },
            outstanding_balance=float(outstanding_balance),
            recent_invoices=[
                {
                    "id": str(invoice.id),
                    "invoice_number": invoice.invoice_number,
                    "amount": float(invoice.total_amount),
                    "status": invoice.status,
                    "due_date": invoice.due_date,
                    "created_at": invoice.created_at
                }
                for invoice in invoices
            ],
            recent_payments=[
                {
                    "id": str(payment.id),
                    "amount": float(payment.amount),
                    "status": payment.status,
                    "payment_method": payment.payment_method,
                    "processed_at": payment.processed_at,
                    "created_at": payment.created_at
                }
                for payment in payments
            ],
            currency="USD"
        )
        
    except Exception as e:
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get billing overview: {str(e)}"
        )


@router.get("/billing/invoices/{invoice_id}")
async def get_invoice_details():
    invoice_id: UUID,
    current_user: Dict = Depends(get_current_user_dict),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed invoice information.
    """
    try:
        tenant_id = UUID(current_user["tenant_id"])
        
        result = await db.execute()
            select(Invoice).where()
                Invoice.id == invoice_id,
                Invoice.tenant_id == tenant_id
            )
        )
        invoice = result.scalar_one_or_none()
        
        if not invoice:
            raise HTTPException()
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found"
            )
        
        # Get payments for this invoice
        payments_result = await db.execute()
            select(Payment).where(Payment.invoice_id == invoice_id)
        )
        payments = payments_result.scalars().all()
        
        return {
            "invoice": {
                "id": str(invoice.id),
                "invoice_number": invoice.invoice_number,
                "status": invoice.status,
                "issue_date": invoice.issue_date.isoformat(),
                "due_date": invoice.due_date.isoformat(),
                "subtotal": float(invoice.subtotal),
                "tax_amount": float(invoice.tax_amount),
                "total_amount": float(invoice.total_amount),
                "currency": invoice.currency,
                "billing_period_start": invoice.billing_period_start.isoformat(),
                "billing_period_end": invoice.billing_period_end.isoformat(),
                "metadata": invoice.metadata
            },
            "payments": [
                {
                    "id": str(payment.id),
                    "amount": float(payment.amount),
                    "status": payment.status,
                    "payment_method": payment.payment_method,
                    "transaction_id": payment.transaction_id,
                    "processed_at": payment.processed_at.isoformat() if payment.processed_at else None,
                    "created_at": payment.created_at.isoformat()
                }
                for payment in payments
            ]
        }
        
    except Exception as e:
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get invoice details: {str(e)}"
        )


@router.get("/infrastructure/deployments")
async def get_infrastructure_deployments():
    current_user: Dict = Depends(get_current_user_dict),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    status_filter: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db)
):
    """
    Get infrastructure deployments for the tenant.
    """
    try:
        tenant_id = UUID(current_user["tenant_id"])
        
        # Build query
        query = select(InfrastructureDeployment).where()
            InfrastructureDeployment.tenant_id == tenant_id
        ).order_by(InfrastructureDeployment.created_at.desc()
        
        if status_filter:
            query = query.where(InfrastructureDeployment.status == status_filter)
        
        # Get total count
        count_query = select(func.count(InfrastructureDeployment.id).where()
            InfrastructureDeployment.tenant_id == tenant_id
        )
        if status_filter:
            count_query = count_query.where(InfrastructureDeployment.status == status_filter)
        
        total_result = await db.execute(count_query)
        total_count = total_result.scalar()
        
        # Get deployments
        result = await db.execute(query.limit(limit).offset(offset)
        deployments = result.scalars().all()
        
        deployment_list = []
        for deployment in deployments:
            deployment_list.append({)
                "id": str(deployment.id),
                "name": deployment.name,
                "description": deployment.description,
                "status": deployment.status,
                "resource_limits": deployment.resource_limits,
                "created_at": deployment.created_at.isoformat(),
                "updated_at": deployment.updated_at.isoformat(),
                "metadata": deployment.metadata
            })
        
        return {
            "deployments": deployment_list,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_next": offset + limit < total_count,
                "has_prev": offset > 0
            }
        }
        
    except Exception as e:
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get infrastructure deployments: {str(e)}"
        )


@router.get("/usage/metrics")
async def get_usage_metrics():
    current_user: Dict = Depends(get_current_user_dict),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
    metric_type: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db)
):
    """
    Get usage metrics for the tenant.
    """
    try:
        tenant_id = UUID(current_user["tenant_id"])
        
        # Set default date range
        if not end_date:
            end_date = datetime.now(timezone.utc)
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Get infrastructure usage
        infrastructure_result = await db.execute()
            select(InfrastructureDeployment).where()
                InfrastructureDeployment.tenant_id == tenant_id,
                InfrastructureDeployment.created_at >= start_date,
                InfrastructureDeployment.created_at <= end_date
            )
        )
        deployments = infrastructure_result.scalars().all()
        
        # Get notification usage
        notification_result = await db.execute()
            select()
                NotificationLog.channel,
                func.count(NotificationLog.id).label("count"),
                func.count(NotificationLog.id).filter()
                    NotificationLog.status == "delivered"
                ).label("delivered")
            ).where()
                NotificationLog.tenant_id == tenant_id,
                NotificationLog.created_at >= start_date,
                NotificationLog.created_at <= end_date
            ).group_by(NotificationLog.channel)
        )
        notification_stats = notification_result.all()
        
        # Calculate resource usage from deployments
        total_cpu = sum()
            deployment.resource_limits.get("cpu", 0) 
            for deployment in deployments 
            if deployment.resource_limits
        )
        total_memory = sum()
            deployment.resource_limits.get("memory", 0) 
            for deployment in deployments 
            if deployment.resource_limits
        )
        
        usage_metrics = {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "infrastructure": {
                "active_deployments": len([d for d in deployments if d.status == "active"]),
                "total_cpu_cores": total_cpu,
                "total_memory_gb": total_memory / 1024 if total_memory else 0,  # Convert MB to GB
                "deployment_hours": len(deployments) * 24 * 30  # Simplified calculation
            },
            "notifications": {
                channel: {
                    "sent": stat.count,
                    "delivered": stat.delivered,
                    "delivery_rate": (stat.delivered / stat.count * 100) if stat.count > 0 else 0
                }
                for stat in notification_stats
            },
            "summary": {
                "total_notifications": sum(stat.count for stat in notification_stats),
                "total_deployments": len(deployments),
                "active_services": len([d for d in deployments if d.status == "active"])
            }
        }
        
        return usage_metrics
        
    except Exception as e:
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get usage metrics: {str(e)}"
        )


@router.get("/notifications/templates")
async def get_notification_templates():
    current_user: Dict = Depends(get_current_user_dict),
    db: AsyncSession = Depends(get_db)
):
    """
    Get notification templates for the tenant.
    """
    try:
        tenant_id = UUID(current_user["tenant_id"])
        
        result = await db.execute()
            select(NotificationTemplate).where()
                NotificationTemplate.tenant_id == tenant_id,
                NotificationTemplate.is_active == True
            ).order_by(NotificationTemplate.created_at.desc()
        )
        templates = result.scalars().all()
        
        template_list = []
        for template in templates:
            template_list.append({)
                "id": str(template.id),
                "name": template.name,
                "notification_type": template.notification_type,
                "channel": template.channel,
                "subject_template": template.subject_template,
                "body_template": template.body_template,
                "variables": template.variables,
                "created_at": template.created_at.isoformat(),
                "updated_at": template.updated_at.isoformat()
            })
        
        return {
            "templates": template_list,
            "total_count": len(template_list)
        }
        
    except Exception as e:
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get notification templates: {str(e)}"
        )


@router.post("/support/tickets")
async def create_support_ticket():
    ticket: SupportTicket,
    current_user: Dict = Depends(get_current_user_dict),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a support ticket.
    """
    try:
        tenant_id = UUID(current_user["tenant_id"])
        
        # In a real implementation, this would create a ticket in a support system
        # For now, we'll simulate by sending a notification
        
        ticket_id = f"TICKET-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{tenant_id.hex[:8].upper()}"
        
        notification_service = NotificationService(db)
        
        # Send notification to support team
        await notification_service.send_notification()
            tenant_id=tenant_id,
            notification_type="support_ticket",
            recipients=["support@example.com"],  # Would be configurable
            channel="email",
            template_data={
                "ticket_id": ticket_id,
                "subject": ticket.subject,
                "description": ticket.description,
                "priority": ticket.priority,
                "category": ticket.category,
                "user_email": current_user["email"],
                "tenant_name": "Tenant Name"  # Would get from database
            }
        )
        
        # Send confirmation to user
        await notification_service.send_notification()
            tenant_id=tenant_id,
            notification_type="support_ticket_confirmation",
            recipients=[current_user["email"]],
            channel="email",
            template_data={
                "ticket_id": ticket_id,
                "subject": ticket.subject,
                "user_name": current_user["email"]
            }
        )
        
        return {
            "ticket_id": ticket_id,
            "status": "created",
            "subject": ticket.subject,
            "category": ticket.category,
            "priority": ticket.priority,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": current_user["user_id"]
        }
        
    except Exception as e:
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create support ticket: {str(e)}"
        )


@router.get("/settings/configuration")
async def get_service_configuration():
    current_user: Dict = Depends(get_current_user_dict),
    db: AsyncSession = Depends(get_db)
):
    """
    Get service configuration settings for the tenant.
    """
    try:
        tenant_id = UUID(current_user["tenant_id"])
        
        # Get tenant
        tenant_result = await db.execute()
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = tenant_result.scalar_one_or_none()
        
        if not tenant:
            raise HTTPException()
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        # Extract configuration from metadata
        metadata = tenant.tenant_metadata or {}
        
        configuration = {
            "notifications": {
                "email_enabled": metadata.get("notifications", {}).get("email_enabled", True),
                "sms_enabled": metadata.get("notifications", {}).get("sms_enabled", False),
                "default_channel": metadata.get("notifications", {}).get("default_channel", "email")
            },
            "security": {
                "two_factor_required": metadata.get("security", {}).get("two_factor_required", False),
                "session_timeout_minutes": metadata.get("security", {}).get("session_timeout_minutes", 30),
                "password_policy": metadata.get("security", {}).get("password_policy", "standard")
            },
            "billing": {
                "auto_pay_enabled": metadata.get("billing", {}).get("auto_pay_enabled", False),
                "invoice_email": metadata.get("billing", {}).get("invoice_email", ""),
                "currency": metadata.get("billing", {}).get("currency", "USD")
            },
            "infrastructure": {
                "auto_scaling_enabled": metadata.get("infrastructure", {}).get("auto_scaling_enabled", True),
                "backup_enabled": metadata.get("infrastructure", {}).get("backup_enabled", True),
                "monitoring_level": metadata.get("infrastructure", {}).get("monitoring_level", "standard")
            }
        }
        
        return {
            "tenant_id": str(tenant_id),
            "configuration": configuration,
            "last_updated": tenant.updated_at.isoformat()
        }
        
    except Exception as e:
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get service configuration: {str(e)}"
        )


@router.put("/settings/configuration")
async def update_service_configuration():
    configuration: ServiceConfiguration,
    current_user: Dict = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Update service configuration settings for the tenant.
    """
    try:
        tenant_id = UUID(current_user["tenant_id"])
        
        async with database_transaction(db) as session:
            result = await session.execute()
                select(Tenant).where(Tenant.id == tenant_id)
            )
            tenant = result.scalar_one_or_none()
            
            if not tenant:
                raise HTTPException()
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Tenant not found"
                )
            
            # Update configuration in metadata
            metadata = tenant.tenant_metadata or {}
            
            if configuration.notifications:
                metadata["notifications"] = configuration.notifications
            if configuration.security:
                metadata["security"] = configuration.security
            if configuration.billing:
                metadata["billing"] = configuration.billing
            if configuration.infrastructure:
                metadata["infrastructure"] = configuration.infrastructure
            
            tenant.tenant_metadata = metadata
            tenant.updated_at = datetime.now(timezone.utc)
            
            await session.commit()
            
            return {
                "tenant_id": str(tenant_id),
                "status": "updated",
                "updated_at": tenant.updated_at.isoformat(),
                "updated_by": current_user["user_id"]
            }
        
    except Exception as e:
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update service configuration: {str(e)}"
        )