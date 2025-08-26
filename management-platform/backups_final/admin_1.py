"""
Admin dashboard API endpoints.
Provides comprehensive administrative functionality for platform management.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from database import get_db, database_transaction
from core.auth import get_current_admin_user, AdminRole
from core.exceptions import ValidationError, DatabaseError
from models.tenant import Tenant
from models.user import User
from models.billing import Subscription, Invoice, Payment
from models.infrastructure import InfrastructureDeployment
from models.notifications import NotificationLog
from schemas.admin import ()
    AdminDashboardStats,
    TenantOverview,
    SystemHealth,
    UserActivity,
    RevenueMetrics,
    InfrastructureMetrics,
    NotificationMetrics
, timezone)
from services.tenant_service import TenantService
from services.billing_service import BillingService
from services.infrastructure_service import InfrastructureService
from services.notification_service import NotificationService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard/stats", response_model=AdminDashboardStats)
async def get_dashboard_stats():
    current_admin: Dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive dashboard statistics for admin overview.
    """
    try:
        # Calculate date ranges
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        seven_days_ago = now - timedelta(days=7)
        
        # Get tenant statistics
        tenant_result = await db.execute()
            select()
                func.count(Tenant.id).label("total"),
                func.count(Tenant.id).filter(Tenant.created_at >= thirty_days_ago).label("new_this_month"),
                func.count(Tenant.id).filter(Tenant.is_active == True).label("active"),
                func.count(Tenant.id).filter(Tenant.is_active == False).label("inactive")
            )
        )
        tenant_stats = tenant_result.one()
        
        # Get user statistics
        user_result = await db.execute()
            select()
                func.count(User.id).label("total"),
                func.count(User.id).filter(User.created_at >= seven_days_ago).label("new_this_week"),
                func.count(User.id).filter(User.last_login >= seven_days_ago).label("active_this_week")
            )
        )
        user_stats = user_result.one()
        
        # Get subscription statistics
        subscription_result = await db.execute()
            select()
                func.count(Subscription.id).label("total"),
                func.count(Subscription.id).filter(Subscription.status == "active").label("active"),
                func.count(Subscription.id).filter(Subscription.status == "trialing").label("trial"),
                func.count(Subscription.id).filter(Subscription.status == "cancelled").label("cancelled")
            )
        )
        subscription_stats = subscription_result.one()
        
        # Get revenue statistics
        revenue_result = await db.execute()
            select()
                func.coalesce(func.sum(Payment.amount), 0).label("total_revenue"),
                func.coalesce(func.sum(Payment.amount).filter(Payment.processed_at >= thirty_days_ago), 0).label("revenue_this_month"),
                func.count(Payment.id).filter(Payment.status == "completed").label("successful_payments"),
                func.count(Payment.id).filter(Payment.status == "failed").label("failed_payments")
            )
        )
        revenue_stats = revenue_result.one()
        
        # Get infrastructure statistics
        infrastructure_result = await db.execute()
            select()
                func.count(InfrastructureDeployment.id).label("total_deployments"),
                func.count(InfrastructureDeployment.id).filter(InfrastructureDeployment.status == "active").label("active_deployments"),
                func.count(InfrastructureDeployment.id).filter(InfrastructureDeployment.status == "provisioning").label("provisioning"),
                func.count(InfrastructureDeployment.id).filter(InfrastructureDeployment.status == "failed").label("failed_deployments")
            )
        )
        infrastructure_stats = infrastructure_result.one()
        
        # Get notification statistics
        notification_result = await db.execute()
            select()
                func.count(NotificationLog.id).label("total_sent"),
                func.count(NotificationLog.id).filter(NotificationLog.sent_at >= seven_days_ago).label("sent_this_week"),
                func.count(NotificationLog.id).filter(NotificationLog.status == "delivered").label("delivered"),
                func.count(NotificationLog.id).filter(NotificationLog.status == "failed").label("failed")
            )
        )
        notification_stats = notification_result.one()
        
        return AdminDashboardStats()
            tenants={
                "total": tenant_stats.total,
                "new_this_month": tenant_stats.new_this_month,
                "active": tenant_stats.active,
                "inactive": tenant_stats.inactive,
                "growth_rate": (tenant_stats.new_this_month / max(tenant_stats.total - tenant_stats.new_this_month, 1) * 100
            },
            users={
                "total": user_stats.total,
                "new_this_week": user_stats.new_this_week,
                "active_this_week": user_stats.active_this_week,
                "activity_rate": (user_stats.active_this_week / max(user_stats.total, 1) * 100
            },
            subscriptions={
                "total": subscription_stats.total,
                "active": subscription_stats.active,
                "trial": subscription_stats.trial,
                "cancelled": subscription_stats.cancelled,
                "conversion_rate": (subscription_stats.active / max(subscription_stats.active + subscription_stats.trial, 1) * 100
            },
            revenue={
                "total": float(revenue_stats.total_revenue),
                "this_month": float(revenue_stats.revenue_this_month),
                "successful_payments": revenue_stats.successful_payments,
                "failed_payments": revenue_stats.failed_payments,
                "success_rate": (revenue_stats.successful_payments / max(revenue_stats.successful_payments + revenue_stats.failed_payments, 1) * 100
            },
            infrastructure={
                "total_deployments": infrastructure_stats.total_deployments,
                "active_deployments": infrastructure_stats.active_deployments,
                "provisioning": infrastructure_stats.provisioning,
                "failed_deployments": infrastructure_stats.failed_deployments,
                "success_rate": (infrastructure_stats.active_deployments / max(infrastructure_stats.total_deployments, 1) * 100
            },
            notifications={
                "total_sent": notification_stats.total_sent,
                "sent_this_week": notification_stats.sent_this_week,
                "delivered": notification_stats.delivered,
                "failed": notification_stats.failed,
                "delivery_rate": (notification_stats.delivered / max(notification_stats.total_sent, 1) * 100
            },
            last_updated=now
        )
        
    except Exception as e:
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard stats: {str(e)}"
        )


@router.get("/tenants/overview")
async def get_tenants_overview():
    current_admin: Dict = Depends(get_current_admin_user),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    status_filter: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db)
):
    """
    Get overview of all tenants with filtering and pagination.
    """
    try:
        # Build query
        query = select(Tenant).order_by(Tenant.created_at.desc()
        
        # Apply filters
        if status_filter:
            if status_filter == "active":
                query = query.where(Tenant.is_active == True)
            elif status_filter == "inactive":
                query = query.where(Tenant.is_active == False)
        
        if search:
            search_term = f"%{search}%"
            query = query.where()
                or_()
                    Tenant.name.ilike(search_term),
                    Tenant.domain.ilike(search_term)
                )
            )
        
        # Execute paginated query
        result = await db.execute(query.limit(limit).offset(offset)
        tenants = result.scalars().all()
        
        # Get total count for pagination
        count_query = select(func.count(Tenant.id)
        if status_filter:
            if status_filter == "active":
                count_query = count_query.where(Tenant.is_active == True)
            elif status_filter == "inactive":
                count_query = count_query.where(Tenant.is_active == False)
        if search:
            search_term = f"%{search}%"
            count_query = count_query.where()
                or_()
                    Tenant.name.ilike(search_term),
                    Tenant.domain.ilike(search_term)
                )
            )
        
        total_result = await db.execute(count_query)
        total_count = total_result.scalar()
        
        # Format response
        tenant_list = []
        for tenant in tenants:
            # Get subscription info
            subscription_result = await db.execute()
                select(Subscription).where()
                    Subscription.tenant_id == tenant.id,
                    Subscription.status == "active"
                ).limit(1)
            )
            subscription = subscription_result.scalar_one_or_none()
            
            # Get user count
            user_count_result = await db.execute()
                select(func.count(User.id).where(User.tenant_id == tenant.id)
            )
            user_count = user_count_result.scalar()
            
            # Get last activity
            last_activity_result = await db.execute()
                select(func.max(User.last_login).where(User.tenant_id == tenant.id)
            )
            last_activity = last_activity_result.scalar()
            
            tenant_list.append({)
                "tenant_id": str(tenant.id),
                "name": tenant.name,
                "domain": tenant.domain,
                "is_active": tenant.is_active,
                "created_at": tenant.created_at.isoformat(),
                "user_count": user_count,
                "subscription_status": subscription.status if subscription else "none",
                "last_activity": last_activity.isoformat() if last_activity else None,
                "metadata": tenant.tenant_metadata
            })
        
        return {
            "tenants": tenant_list,
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
            detail=f"Failed to get tenants overview: {str(e)}"
        )


@router.get("/tenants/{tenant_id}/details")
async def get_tenant_details():
    tenant_id: UUID,
    current_admin: Dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a specific tenant.
    """
    try:
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
        
        # Get users
        users_result = await db.execute()
            select(User).where(User.tenant_id == tenant_id).order_by(User.created_at.desc()
        )
        users = users_result.scalars().all()
        
        # Get subscriptions
        subscriptions_result = await db.execute()
            select(Subscription).where(Subscription.tenant_id == tenant_id).order_by(Subscription.created_at.desc()
        )
        subscriptions = subscriptions_result.scalars().all()
        
        # Get recent invoices
        invoices_result = await db.execute()
            select(Invoice).where(Invoice.tenant_id == tenant_id).order_by(Invoice.created_at.desc().limit(10)
        )
        invoices = invoices_result.scalars().all()
        
        # Get infrastructure deployments
        deployments_result = await db.execute()
            select(InfrastructureDeployment).where(InfrastructureDeployment.tenant_id == tenant_id)
        )
        deployments = deployments_result.scalars().all()
        
        # Calculate statistics
        total_revenue_result = await db.execute()
            select(func.coalesce(func.sum(Payment.amount), 0).join(Invoice).where(Invoice.tenant_id == tenant_id)
        )
        total_revenue = total_revenue_result.scalar()
        
        return {
            "tenant": {
                "id": str(tenant.id),
                "name": tenant.name,
                "domain": tenant.domain,
                "is_active": tenant.is_active,
                "created_at": tenant.created_at.isoformat(),
                "metadata": tenant.tenant_metadata
            },
            "users": [
                {
                    "id": str(user.id),
                    "email": user.email,
                    "full_name": user.full_name,
                    "is_active": user.is_active,
                    "role": user.role,
                    "last_login": user.last_login.isoformat() if user.last_login else None,
                    "created_at": user.created_at.isoformat()
                }
                for user in users
            ],
            "subscriptions": [
                {
                    "id": str(sub.id),
                    "status": sub.status,
                    "start_date": sub.start_date.isoformat(),
                    "end_date": sub.end_date.isoformat() if sub.end_date else None,
                    "auto_renew": sub.auto_renew,
                    "created_at": sub.created_at.isoformat()
                }
                for sub in subscriptions
            ],
            "recent_invoices": [
                {
                    "id": str(invoice.id),
                    "invoice_number": invoice.invoice_number,
                    "status": invoice.status,
                    "total_amount": float(invoice.total_amount),
                    "due_date": invoice.due_date.isoformat(),
                    "created_at": invoice.created_at.isoformat()
                }
                for invoice in invoices
            ],
            "infrastructure": [
                {
                    "id": str(deployment.id),
                    "name": deployment.name,
                    "status": deployment.status,
                    "created_at": deployment.created_at.isoformat(),
                    "metadata": deployment.metadata
                }
                for deployment in deployments
            ],
            "statistics": {
                "total_users": len(users),
                "active_users": len([u for u in users if u.is_active]),
                "total_subscriptions": len(subscriptions),
                "active_subscriptions": len([s for s in subscriptions if s.status == "active"]),
                "total_revenue": float(total_revenue),
                "infrastructure_deployments": len(deployments)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tenant details: {str(e)}"
        )


@router.post("/tenants/{tenant_id}/actions/suspend")
async def suspend_tenant():
    tenant_id: UUID,
    reason: str,
    current_admin: Dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Suspend a tenant (deactivate without deletion).
    """
    try:
        async with database_transaction(db) as session:
            # Get tenant
            tenant_result = await session.execute()
                select(Tenant).where(Tenant.id == tenant_id)
            )
            tenant = tenant_result.scalar_one_or_none()
            
            if not tenant:
                raise HTTPException()
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Tenant not found"
                )
            
            # Update tenant status
            tenant.is_active = False
            tenant.tenant_metadata = tenant.tenant_metadata or {}
            tenant.tenant_metadata.update({)
                "suspended_at": datetime.now(timezone.utc).isoformat(),
                "suspended_by": current_admin["user_id"],
                "suspension_reason": reason
            })
            
            # Deactivate all users
            await session.execute()
                select(User).where(User.tenant_id == tenant_id).update({"is_active": False})
            )
            
            await session.commit()
            
            return {
                "tenant_id": str(tenant_id),
                "status": "suspended",
                "reason": reason,
                "suspended_at": datetime.now(timezone.utc).isoformat(),
                "suspended_by": current_admin["user_id"]
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to suspend tenant: {str(e)}"
        )


@router.post("/tenants/{tenant_id}/actions/reactivate")
async def reactivate_tenant():
    tenant_id: UUID,
    current_admin: Dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Reactivate a suspended tenant.
    """
    try:
        async with database_transaction(db) as session:
            # Get tenant
            tenant_result = await session.execute()
                select(Tenant).where(Tenant.id == tenant_id)
            )
            tenant = tenant_result.scalar_one_or_none()
            
            if not tenant:
                raise HTTPException()
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Tenant not found"
                )
            
            # Update tenant status
            tenant.is_active = True
            tenant.tenant_metadata = tenant.tenant_metadata or {}
            tenant.tenant_metadata.update({)
                "reactivated_at": datetime.now(timezone.utc).isoformat(),
                "reactivated_by": current_admin["user_id"]
            })
            
            # Reactivate all users (they can choose to deactivate individually if needed)
            await session.execute()
                select(User).where(User.tenant_id == tenant_id).update({"is_active": True})
            )
            
            await session.commit()
            
            return {
                "tenant_id": str(tenant_id),
                "status": "active",
                "reactivated_at": datetime.now(timezone.utc).isoformat(),
                "reactivated_by": current_admin["user_id"]
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reactivate tenant: {str(e)}"
        )


@router.get("/system/health")
async def get_system_health():
    current_admin: Dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive system health status.
    """
    try:
        # Database health
        db_start = datetime.now(timezone.utc)
        await db.execute(select(1)
        db_response_time = (datetime.now(timezone.utc) - db_start).total_seconds() * 1000
        
        # Check recent errors
        error_threshold = datetime.now(timezone.utc) - timedelta(hours=1)
        
        # Get failed infrastructure deployments
        failed_deployments_result = await db.execute()
            select(func.count(InfrastructureDeployment.id).where()
                and_()
                    InfrastructureDeployment.status == "failed",
                    InfrastructureDeployment.updated_at >= error_threshold
                )
            )
        )
        failed_deployments = failed_deployments_result.scalar()
        
        # Get failed notifications
        failed_notifications_result = await db.execute()
            select(func.count(NotificationLog.id).where()
                and_()
                    NotificationLog.status == "failed",
                    NotificationLog.created_at >= error_threshold
                )
            )
        )
        failed_notifications = failed_notifications_result.scalar()
        
        # Get failed payments
        failed_payments_result = await db.execute()
            select(func.count(Payment.id).where()
                and_()
                    Payment.status == "failed",
                    Payment.created_at >= error_threshold
                )
            )
        )
        failed_payments = failed_payments_result.scalar()
        
        # Determine overall health status
        health_status = "healthy"
        if db_response_time > 1000:  # 1 second
            health_status = "degraded"
        if failed_deployments > 5 or failed_notifications > 50 or failed_payments > 10:
            health_status = "unhealthy"
        
        return {
            "overall_status": health_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": {
                "database": {
                    "status": "healthy" if db_response_time < 1000 else "degraded",
                    "response_time_ms": round(db_response_time, 2),
                    "last_checked": datetime.now(timezone.utc).isoformat()
                },
                "infrastructure": {
                    "status": "healthy" if failed_deployments < 5 else "unhealthy",
                    "failed_deployments_last_hour": failed_deployments,
                    "last_checked": datetime.now(timezone.utc).isoformat()
                },
                "notifications": {
                    "status": "healthy" if failed_notifications < 50 else "degraded",
                    "failed_notifications_last_hour": failed_notifications,
                    "last_checked": datetime.now(timezone.utc).isoformat()
                },
                "payments": {
                    "status": "healthy" if failed_payments < 10 else "unhealthy",
                    "failed_payments_last_hour": failed_payments,
                    "last_checked": datetime.now(timezone.utc).isoformat()
                }
            },
            "metrics": {
                "uptime_percentage": 99.9,  # This would come from monitoring service
                "avg_response_time_ms": round(db_response_time, 2),
                "active_connections": 10,  # This would come from connection pool
                "memory_usage_percentage": 65.3,  # This would come from system monitoring
                "cpu_usage_percentage": 23.7  # This would come from system monitoring
            }
        }
        
    except Exception as e:
        return {
            "overall_status": "unhealthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
            "components": {
                "database": {"status": "unhealthy", "error": str(e)},
                "infrastructure": {"status": "unknown"},
                "notifications": {"status": "unknown"},
                "payments": {"status": "unknown"}
            }
        }


@router.get("/analytics/revenue")
async def get_revenue_analytics():
    current_admin: Dict = Depends(get_current_admin_user),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
    granularity: str = Query(default="daily", regex="^(daily|weekly|monthly)$"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get revenue analytics with time-series data.
    """
    try:
        # Set default date range
        if not end_date:
            end_date = datetime.now(timezone.utc)
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Get revenue data
        revenue_query = select()
            Payment.processed_at,
            Payment.amount,
            Payment.status
        ).where()
            and_()
                Payment.processed_at >= start_date,
                Payment.processed_at <= end_date,
                Payment.status == "completed"
            )
        ).order_by(Payment.processed_at)
        
        result = await db.execute(revenue_query)
        payments = result.all()
        
        # Group by time period
        revenue_data = []
        current_period = start_date
        
        if granularity == "daily":
            delta = timedelta(days=1)
        elif granularity == "weekly":
            delta = timedelta(weeks=1)
        else:  # monthly
            delta = timedelta(days=30)
        
        while current_period <= end_date:
            period_end = current_period + delta
            period_payments = [
                p for p in payments 
                if current_period <= p.processed_at < period_end
            ]
            
            period_revenue = sum(float(p.amount) for p in period_payments)
            payment_count = len(period_payments)
            
            revenue_data.append({)
                "period": current_period.isoformat(),
                "revenue": period_revenue,
                "payment_count": payment_count,
                "average_payment": period_revenue / payment_count if payment_count > 0 else 0
            })
            
            current_period = period_end
        
        # Calculate totals
        total_revenue = sum(item["revenue"] for item in revenue_data)
        total_payments = sum(item["payment_count"] for item in revenue_data)
        
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "granularity": granularity
            },
            "summary": {
                "total_revenue": total_revenue,
                "total_payments": total_payments,
                "average_payment": total_revenue / total_payments if total_payments > 0 else 0,
                "periods": len(revenue_data)
            },
            "time_series": revenue_data
        }
        
    except Exception as e:
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get revenue analytics: {str(e)}"
        )


@router.get("/logs/activity")
async def get_activity_logs():
    current_admin: Dict = Depends(get_current_admin_user),
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0),
    level: Optional[str] = Query(default=None),
    component: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db)
):
    """
    Get system activity logs with filtering.
    """
    try:
        # This would typically query a logging table or external logging service
        # For now, we'll return recent notification logs as an example
        
        query = select(NotificationLog).order_by(NotificationLog.created_at.desc()
        
        if component == "notifications":
            # Already filtered to notifications
            pass
        
        result = await db.execute(query.limit(limit).offset(offset)
        logs = result.scalars().all()
        
        activity_logs = []
        for log in logs:
            activity_logs.append({)
                "timestamp": log.created_at.isoformat(),
                "level": "INFO" if log.status == "delivered" else "ERROR" if log.status == "failed" else "DEBUG",
                "component": "notifications",
                "message": f"Notification {log.status}: {log.channel} to {log.recipient}",
                "metadata": {
                    "tenant_id": str(log.tenant_id),
                    "notification_type": log.notification_type,
                    "channel": log.channel,
                    "status": log.status
                }
            })
        
        return {
            "logs": activity_logs,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": len(activity_logs)
            },
            "filters": {
                "level": level,
                "component": component
            }
        }
        
    except Exception as e:
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get activity logs: {str(e)}"
        )