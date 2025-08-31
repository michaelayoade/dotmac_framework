"""Service management repositories for data access layer."""

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload

from dotmac_isp.shared.base_repository import BaseTenantRepository
from dotmac_isp.shared.exceptions import EntityNotFoundError
from .models import (
    ServicePlan,
    ServiceInstance,
    ServiceProvisioning, 
    ServiceStatusHistory,
    ServiceUsageMetric
)

logger = logging.getLogger(__name__)


class ServicePlanRepository(BaseTenantRepository[ServicePlan]):
    """Repository for service plan data access."""
    
    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, ServicePlan, tenant_id)

    def get_by_code(self, plan_code: str) -> Optional[ServicePlan]:
        """Get service plan by plan code."""
        return self.db.query(ServicePlan).filter(
            and_(
                ServicePlan.tenant_id == self.tenant_id,
                ServicePlan.plan_code == plan_code
            )
        ).first()

    def get_active_plans(self) -> List[ServicePlan]:
        """Get all active service plans."""
        return self.db.query(ServicePlan).filter(
            and_(
                ServicePlan.tenant_id == self.tenant_id,
                ServicePlan.is_active == True
            )
        ).order_by(ServicePlan.service_type, ServicePlan.name).all()

    def get_public_plans(self) -> List[ServicePlan]:
        """Get all public service plans for customer selection."""
        return self.db.query(ServicePlan).filter(
            and_(
                ServicePlan.tenant_id == self.tenant_id,
                ServicePlan.is_active == True,
                ServicePlan.is_public == True
            )
        ).order_by(ServicePlan.monthly_price).all()

    def get_plans_by_type(self, service_type: str) -> List[ServicePlan]:
        """Get service plans by type."""
        return self.db.query(ServicePlan).filter(
            and_(
                ServicePlan.tenant_id == self.tenant_id,
                ServicePlan.service_type == service_type,
                ServicePlan.is_active == True
            )
        ).order_by(ServicePlan.monthly_price).all()

    def search_plans(self, query: str) -> List[ServicePlan]:
        """Search service plans by name or description."""
        search_term = f"%{query}%"
        return self.db.query(ServicePlan).filter(
            and_(
                ServicePlan.tenant_id == self.tenant_id,
                or_(
                    ServicePlan.name.ilike(search_term),
                    ServicePlan.description.ilike(search_term),
                    ServicePlan.plan_code.ilike(search_term)
                )
            )
        ).order_by(ServicePlan.name).all()


class ServiceInstanceRepository(BaseTenantRepository[ServiceInstance]):
    """Repository for service instance data access."""
    
    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, ServiceInstance, tenant_id)

    def get_by_service_number(self, service_number: str) -> Optional[ServiceInstance]:
        """Get service instance by service number."""
        return self.db.query(ServiceInstance).filter(
            and_(
                ServiceInstance.tenant_id == self.tenant_id,
                ServiceInstance.service_number == service_number
            )
        ).first()

    def get_customer_services(self, customer_id: UUID) -> List[ServiceInstance]:
        """Get all services for a customer."""
        return self.db.query(ServiceInstance).options(
            joinedload(ServiceInstance.service_plan)
        ).filter(
            and_(
                ServiceInstance.tenant_id == self.tenant_id,
                ServiceInstance.customer_id == customer_id
            )
        ).order_by(ServiceInstance.created_at.desc()).all()

    def get_active_services(self, customer_id: Optional[UUID] = None) -> List[ServiceInstance]:
        """Get active services, optionally filtered by customer."""
        query = self.db.query(ServiceInstance).filter(
            and_(
                ServiceInstance.tenant_id == self.tenant_id,
                ServiceInstance.status == "active"
            )
        )
        
        if customer_id:
            query = query.filter(ServiceInstance.customer_id == customer_id)
            
        return query.order_by(ServiceInstance.activation_date.desc()).all()

    def get_services_by_status(self, status: str) -> List[ServiceInstance]:
        """Get services by status."""
        return self.db.query(ServiceInstance).options(
            joinedload(ServiceInstance.service_plan)
        ).filter(
            and_(
                ServiceInstance.tenant_id == self.tenant_id,
                ServiceInstance.status == status
            )
        ).order_by(ServiceInstance.created_at.desc()).all()

    def get_services_for_billing(self, billing_date: date) -> List[ServiceInstance]:
        """Get services that should be billed for a specific date."""
        return self.db.query(ServiceInstance).options(
            joinedload(ServiceInstance.service_plan)
        ).filter(
            and_(
                ServiceInstance.tenant_id == self.tenant_id,
                ServiceInstance.status.in_(["active", "suspended"]),
                or_(
                    ServiceInstance.activation_date <= billing_date,
                    ServiceInstance.activation_date.is_(None)
                ),
                or_(
                    ServiceInstance.cancellation_date > billing_date,
                    ServiceInstance.cancellation_date.is_(None)
                )
            )
        ).all()

    def get_expiring_contracts(self, days_ahead: int = 30) -> List[ServiceInstance]:
        """Get services with contracts expiring within specified days."""
        expiry_date = date.today() + timedelta(days=days_ahead)
        
        return self.db.query(ServiceInstance).options(
            joinedload(ServiceInstance.service_plan)
        ).filter(
            and_(
                ServiceInstance.tenant_id == self.tenant_id,
                ServiceInstance.status == "active",
                ServiceInstance.contract_end_date.is_not(None),
                ServiceInstance.contract_end_date <= expiry_date
            )
        ).order_by(ServiceInstance.contract_end_date).all()

    def get_service_revenue_by_period(self, start_date: date, end_date: date) -> Decimal:
        """Get total service revenue for a period."""
        result = self.db.query(
            func.sum(ServiceInstance.monthly_price)
        ).filter(
            and_(
                ServiceInstance.tenant_id == self.tenant_id,
                ServiceInstance.status.in_(["active", "suspended"]),
                ServiceInstance.activation_date <= end_date,
                or_(
                    ServiceInstance.cancellation_date > start_date,
                    ServiceInstance.cancellation_date.is_(None)
                )
            )
        ).scalar()
        
        return result or Decimal("0")

    def get_service_statistics(self) -> Dict[str, Any]:
        """Get service statistics for dashboard."""
        stats = {}
        
        # Count by status
        status_counts = self.db.query(
            ServiceInstance.status,
            func.count(ServiceInstance.id)
        ).filter(
            ServiceInstance.tenant_id == self.tenant_id
        ).group_by(ServiceInstance.status).all()
        
        stats["status_breakdown"] = {status: count for status, count in status_counts}
        
        # Revenue statistics
        total_revenue = self.db.query(
            func.sum(ServiceInstance.monthly_price)
        ).filter(
            and_(
                ServiceInstance.tenant_id == self.tenant_id,
                ServiceInstance.status == "active"
            )
        ).scalar()
        
        stats["monthly_recurring_revenue"] = float(total_revenue or 0)
        
        # Service type breakdown
        type_counts = self.db.query(
            ServicePlan.service_type,
            func.count(ServiceInstance.id)
        ).join(ServicePlan).filter(
            ServiceInstance.tenant_id == self.tenant_id
        ).group_by(ServicePlan.service_type).all()
        
        stats["service_type_breakdown"] = {service_type: count for service_type, count in type_counts}
        
        return stats


class ServiceProvisioningRepository(BaseTenantRepository[ServiceProvisioning]):
    """Repository for service provisioning data access."""
    
    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, ServiceProvisioning, tenant_id)

    def get_by_service_instance(self, service_instance_id: UUID) -> Optional[ServiceProvisioning]:
        """Get provisioning record by service instance."""
        return self.db.query(ServiceProvisioning).filter(
            and_(
                ServiceProvisioning.tenant_id == self.tenant_id,
                ServiceProvisioning.service_instance_id == service_instance_id
            )
        ).first()

    def get_pending_provisioning(self) -> List[ServiceProvisioning]:
        """Get all pending provisioning tasks."""
        return self.db.query(ServiceProvisioning).options(
            joinedload(ServiceProvisioning.service_instance)
        ).filter(
            and_(
                ServiceProvisioning.tenant_id == self.tenant_id,
                ServiceProvisioning.provisioning_status == "pending"
            )
        ).order_by(ServiceProvisioning.scheduled_date.asc()).all()

    def get_technician_tasks(self, technician_id: UUID) -> List[ServiceProvisioning]:
        """Get provisioning tasks assigned to a technician."""
        return self.db.query(ServiceProvisioning).options(
            joinedload(ServiceProvisioning.service_instance)
        ).filter(
            and_(
                ServiceProvisioning.tenant_id == self.tenant_id,
                ServiceProvisioning.assigned_technician_id == technician_id,
                ServiceProvisioning.provisioning_status.in_(["pending", "in_progress"])
            )
        ).order_by(ServiceProvisioning.scheduled_date.asc()).all()

    def get_overdue_provisioning(self) -> List[ServiceProvisioning]:
        """Get overdue provisioning tasks."""
        today = datetime.now().date()
        
        return self.db.query(ServiceProvisioning).options(
            joinedload(ServiceProvisioning.service_instance)
        ).filter(
            and_(
                ServiceProvisioning.tenant_id == self.tenant_id,
                ServiceProvisioning.provisioning_status.in_(["pending", "in_progress"]),
                ServiceProvisioning.scheduled_date < today
            )
        ).order_by(ServiceProvisioning.scheduled_date.asc()).all()

    def get_provisioning_statistics(self) -> Dict[str, Any]:
        """Get provisioning statistics for dashboard."""
        stats = {}
        
        # Count by status
        status_counts = self.db.query(
            ServiceProvisioning.provisioning_status,
            func.count(ServiceProvisioning.id)
        ).filter(
            ServiceProvisioning.tenant_id == self.tenant_id
        ).group_by(ServiceProvisioning.provisioning_status).all()
        
        stats["status_breakdown"] = {status: count for status, count in status_counts}
        
        # Average completion time
        avg_completion = self.db.query(
            func.avg(
                func.extract('epoch', ServiceProvisioning.completed_date - ServiceProvisioning.started_date) / 3600
            )
        ).filter(
            and_(
                ServiceProvisioning.tenant_id == self.tenant_id,
                ServiceProvisioning.provisioning_status == "completed",
                ServiceProvisioning.completed_date.is_not(None),
                ServiceProvisioning.started_date.is_not(None)
            )
        ).scalar()
        
        stats["avg_completion_hours"] = float(avg_completion or 0)
        
        # Success rate
        total_completed = self.db.query(func.count(ServiceProvisioning.id)).filter(
            and_(
                ServiceProvisioning.tenant_id == self.tenant_id,
                ServiceProvisioning.provisioning_status.in_(["completed", "failed"])
            )
        ).scalar()
        
        successful_completed = self.db.query(func.count(ServiceProvisioning.id)).filter(
            and_(
                ServiceProvisioning.tenant_id == self.tenant_id,
                ServiceProvisioning.provisioning_status == "completed"
            )
        ).scalar()
        
        stats["success_rate"] = (successful_completed / total_completed * 100) if total_completed > 0 else 0
        
        return stats


class ServiceStatusHistoryRepository(BaseTenantRepository[ServiceStatusHistory]):
    """Repository for service status history data access."""
    
    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, ServiceStatusHistory, tenant_id)

    def get_service_history(self, service_instance_id: UUID, limit: int = 50) -> List[ServiceStatusHistory]:
        """Get status history for a service instance."""
        return self.db.query(ServiceStatusHistory).filter(
            and_(
                ServiceStatusHistory.tenant_id == self.tenant_id,
                ServiceStatusHistory.service_instance_id == service_instance_id
            )
        ).order_by(ServiceStatusHistory.created_at.desc()).limit(limit).all()

    def add_status_change(
        self, 
        service_instance_id: UUID,
        old_status: Optional[str],
        new_status: str,
        change_reason: Optional[str] = None,
        changed_by_user_id: Optional[UUID] = None,
        effective_date: Optional[datetime] = None
    ) -> ServiceStatusHistory:
        """Add a new status change record."""
        history_record = ServiceStatusHistory(
            tenant_id=self.tenant_id,
            service_instance_id=service_instance_id,
            old_status=old_status,
            new_status=new_status,
            change_reason=change_reason,
            changed_by_user_id=changed_by_user_id,
            effective_date=effective_date or datetime.utcnow()
        )
        
        self.db.add(history_record)
        return history_record

    def get_status_changes_by_period(self, start_date: date, end_date: date) -> List[ServiceStatusHistory]:
        """Get status changes within a date range."""
        return self.db.query(ServiceStatusHistory).filter(
            and_(
                ServiceStatusHistory.tenant_id == self.tenant_id,
                ServiceStatusHistory.effective_date >= start_date,
                ServiceStatusHistory.effective_date <= end_date
            )
        ).order_by(ServiceStatusHistory.effective_date.desc()).all()


class ServiceUsageMetricRepository(BaseTenantRepository[ServiceUsageMetric]):
    """Repository for service usage metrics data access."""
    
    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, ServiceUsageMetric, tenant_id)

    def get_service_usage(
        self, 
        service_instance_id: UUID, 
        start_date: date, 
        end_date: date
    ) -> List[ServiceUsageMetric]:
        """Get usage metrics for a service within date range."""
        return self.db.query(ServiceUsageMetric).filter(
            and_(
                ServiceUsageMetric.tenant_id == self.tenant_id,
                ServiceUsageMetric.service_instance_id == service_instance_id,
                ServiceUsageMetric.usage_date >= start_date,
                ServiceUsageMetric.usage_date <= end_date
            )
        ).order_by(ServiceUsageMetric.usage_date.asc()).all()

    def get_usage_summary(
        self, 
        service_instance_id: UUID, 
        start_date: date, 
        end_date: date
    ) -> Dict[str, Any]:
        """Get usage summary for a service within date range."""
        metrics = self.db.query(
            func.sum(ServiceUsageMetric.data_downloaded_mb).label('total_download'),
            func.sum(ServiceUsageMetric.data_uploaded_mb).label('total_upload'),
            func.max(ServiceUsageMetric.peak_download_speed_mbps).label('max_download_speed'),
            func.max(ServiceUsageMetric.peak_upload_speed_mbps).label('max_upload_speed'),
            func.sum(ServiceUsageMetric.uptime_minutes).label('total_uptime'),
            func.sum(ServiceUsageMetric.downtime_minutes).label('total_downtime'),
            func.sum(ServiceUsageMetric.connection_drops).label('total_drops')
        ).filter(
            and_(
                ServiceUsageMetric.tenant_id == self.tenant_id,
                ServiceUsageMetric.service_instance_id == service_instance_id,
                ServiceUsageMetric.usage_date >= start_date,
                ServiceUsageMetric.usage_date <= end_date
            )
        ).first()

        return {
            "total_data_downloaded_gb": float(metrics.total_download or 0) / 1024,
            "total_data_uploaded_gb": float(metrics.total_upload or 0) / 1024,
            "peak_download_speed_mbps": float(metrics.max_download_speed or 0),
            "peak_upload_speed_mbps": float(metrics.max_upload_speed or 0),
            "uptime_percentage": (
                float(metrics.total_uptime or 0) / 
                (float(metrics.total_uptime or 0) + float(metrics.total_downtime or 0)) * 100
            ) if (metrics.total_uptime or metrics.total_downtime) else 100,
            "total_connection_drops": int(metrics.total_drops or 0)
        }

    def record_daily_usage(
        self,
        service_instance_id: UUID,
        usage_date: date,
        data_downloaded_mb: float,
        data_uploaded_mb: float,
        peak_download_speed_mbps: Optional[float] = None,
        peak_upload_speed_mbps: Optional[float] = None,
        uptime_minutes: int = 0,
        downtime_minutes: int = 0,
        connection_drops: int = 0,
        custom_metrics: Optional[Dict[str, Any]] = None
    ) -> ServiceUsageMetric:
        """Record daily usage metrics for a service."""
        # Check if record already exists for this date
        existing_metric = self.db.query(ServiceUsageMetric).filter(
            and_(
                ServiceUsageMetric.tenant_id == self.tenant_id,
                ServiceUsageMetric.service_instance_id == service_instance_id,
                ServiceUsageMetric.usage_date == usage_date,
                ServiceUsageMetric.usage_hour.is_(None)  # Daily record
            )
        ).first()

        if existing_metric:
            # Update existing record
            existing_metric.data_downloaded_mb = data_downloaded_mb
            existing_metric.data_uploaded_mb = data_uploaded_mb
            existing_metric.peak_download_speed_mbps = peak_download_speed_mbps
            existing_metric.peak_upload_speed_mbps = peak_upload_speed_mbps
            existing_metric.uptime_minutes = uptime_minutes
            existing_metric.downtime_minutes = downtime_minutes
            existing_metric.connection_drops = connection_drops
            existing_metric.custom_metrics = custom_metrics or {}
            return existing_metric
        else:
            # Create new record
            usage_metric = ServiceUsageMetric(
                tenant_id=self.tenant_id,
                service_instance_id=service_instance_id,
                usage_date=usage_date,
                data_downloaded_mb=data_downloaded_mb,
                data_uploaded_mb=data_uploaded_mb,
                peak_download_speed_mbps=peak_download_speed_mbps,
                peak_upload_speed_mbps=peak_upload_speed_mbps,
                uptime_minutes=uptime_minutes,
                downtime_minutes=downtime_minutes,
                connection_drops=connection_drops,
                custom_metrics=custom_metrics or {}
            )
            
            self.db.add(usage_metric)
            return usage_metric

    def get_top_usage_services(self, limit: int = 10, period_days: int = 30) -> List[Dict[str, Any]]:
        """Get top services by data usage."""
        start_date = date.today() - timedelta(days=period_days)
        
        results = self.db.query(
            ServiceUsageMetric.service_instance_id,
            func.sum(ServiceUsageMetric.data_downloaded_mb + ServiceUsageMetric.data_uploaded_mb).label('total_data')
        ).filter(
            and_(
                ServiceUsageMetric.tenant_id == self.tenant_id,
                ServiceUsageMetric.usage_date >= start_date
            )
        ).group_by(
            ServiceUsageMetric.service_instance_id
        ).order_by(
            func.sum(ServiceUsageMetric.data_downloaded_mb + ServiceUsageMetric.data_uploaded_mb).desc()
        ).limit(limit).all()

        return [
            {
                "service_instance_id": str(result.service_instance_id),
                "total_data_gb": float(result.total_data) / 1024
            }
            for result in results
        ]