"""Repository pattern for services database operations."""

from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, func
from decimal import Decimal

from dotmac_isp.modules.services.models import (
    ServicePlan,
    ServiceInstance,
    ProvisioningTask,
    ServiceAddon,
    ServiceUsage,
    ServiceAlert,
    ServiceInstanceAddon,
    ServiceType,
    ServiceStatus,
    ProvisioningStatus,
)
from dotmac_isp.shared.exceptions import NotFoundError, ConflictError, ValidationError


class ServicePlanRepository:
    """Repository for service plan database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def create(self, plan_data: Dict[str, Any]) -> ServicePlan:
        """Create a new service plan."""
        try:
            plan = ServicePlan(id=uuid4(), tenant_id=self.tenant_id, **plan_data)

            self.db.add(plan)
            self.db.commit()
            self.db.refresh(plan)
            return plan

        except IntegrityError as e:
            self.db.rollback()
            if "plan_code" in str(e):
                raise ConflictError(
                    f"Plan code {plan_data.get('plan_code')} already exists"
                )
            raise ConflictError("Service plan creation failed due to data conflict")

    def get_by_id(self, plan_id: UUID) -> Optional[ServicePlan]:
        """Get service plan by ID."""
        return (
            self.db.query(ServicePlan)
            .filter(
                and_(ServicePlan.id == plan_id, ServicePlan.tenant_id == self.tenant_id)
            )
            .first()
        )

    def get_by_plan_code(self, plan_code: str) -> Optional[ServicePlan]:
        """Get service plan by plan code."""
        return (
            self.db.query(ServicePlan)
            .filter(
                and_(
                    ServicePlan.plan_code == plan_code,
                    ServicePlan.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    def list_plans(
        self,
        service_type: Optional[ServiceType] = None,
        is_active: Optional[bool] = None,
        is_public: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ServicePlan]:
        """List service plans with filtering."""
        query = self.db.query(ServicePlan).filter(
            ServicePlan.tenant_id == self.tenant_id
        )

        if service_type:
            query = query.filter(ServicePlan.service_type == service_type)
        if is_active is not None:
            query = query.filter(ServicePlan.is_active == is_active)
        if is_public is not None:
            query = query.filter(ServicePlan.is_public == is_public)

        return query.offset(skip).limit(limit).all()

    def update(
        self, plan_id: UUID, update_data: Dict[str, Any]
    ) -> Optional[ServicePlan]:
        """Update service plan."""
        plan = self.get_by_id(plan_id)
        if not plan:
            return None

        for key, value in update_data.items():
            if hasattr(plan, key):
                setattr(plan, key, value)

        plan.updated_at = datetime.utcnow()

        try:
            self.db.commit()
            self.db.refresh(plan)
            return plan
        except IntegrityError:
            self.db.rollback()
            raise ConflictError("Service plan update failed due to data conflict")

    def delete(self, plan_id: UUID) -> bool:
        """Delete service plan."""
        plan = self.get_by_id(plan_id)
        if not plan:
            return False

        self.db.delete(plan)
        self.db.commit()
        return True


class ServiceInstanceRepository:
    """Repository for service instance database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def create(self, instance_data: Dict[str, Any]) -> ServiceInstance:
        """Create a new service instance."""
        try:
            # Generate service number if not provided
            if not instance_data.get("service_number"):
                instance_data["service_number"] = self._generate_service_number()

            instance = ServiceInstance(
                id=uuid4(), tenant_id=self.tenant_id, **instance_data
            )

            self.db.add(instance)
            self.db.commit()
            self.db.refresh(instance)
            return instance

        except IntegrityError as e:
            self.db.rollback()
            if "service_number" in str(e):
                raise ConflictError(
                    f"Service number {instance_data.get('service_number')} already exists"
                )
            raise ConflictError("Service instance creation failed due to data conflict")

    def get_by_id(self, instance_id: UUID) -> Optional[ServiceInstance]:
        """Get service instance by ID."""
        return (
            self.db.query(ServiceInstance)
            .filter(
                and_(
                    ServiceInstance.id == instance_id,
                    ServiceInstance.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    def get_by_service_number(self, service_number: str) -> Optional[ServiceInstance]:
        """Get service instance by service number."""
        return (
            self.db.query(ServiceInstance)
            .filter(
                and_(
                    ServiceInstance.service_number == service_number,
                    ServiceInstance.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    def list_by_customer(
        self, customer_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[ServiceInstance]:
        """List service instances for a customer."""
        return (
            self.db.query(ServiceInstance)
            .filter(
                and_(
                    ServiceInstance.customer_id == customer_id,
                    ServiceInstance.tenant_id == self.tenant_id,
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def list_instances(
        self,
        customer_id: Optional[UUID] = None,
        status: Optional[ServiceStatus] = None,
        service_plan_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ServiceInstance]:
        """List service instances with filtering."""
        query = self.db.query(ServiceInstance).filter(
            ServiceInstance.tenant_id == self.tenant_id
        )

        if customer_id:
            query = query.filter(ServiceInstance.customer_id == customer_id)
        if status:
            query = query.filter(ServiceInstance.status == status)
        if service_plan_id:
            query = query.filter(ServiceInstance.service_plan_id == service_plan_id)

        return query.offset(skip).limit(limit).all()

    def update_status(
        self, instance_id: UUID, status: ServiceStatus, notes: Optional[str] = None
    ) -> Optional[ServiceInstance]:
        """Update service instance status."""
        instance = self.get_by_id(instance_id)
        if not instance:
            return None

        instance.status = status
        instance.updated_at = datetime.utcnow()

        if status == ServiceStatus.ACTIVE and not instance.activation_date:
            instance.activation_date = datetime.utcnow()
        elif status == ServiceStatus.SUSPENDED and not instance.suspension_date:
            instance.suspension_date = datetime.utcnow()
        elif status == ServiceStatus.CANCELLED and not instance.cancellation_date:
            instance.cancellation_date = datetime.utcnow()

        if notes:
            instance.notes = f"{instance.notes or ''}\n{datetime.utcnow().isoformat()}: {notes}".strip()

        self.db.commit()
        self.db.refresh(instance)
        return instance

    def update(
        self, instance_id: UUID, update_data: Dict[str, Any]
    ) -> Optional[ServiceInstance]:
        """Update service instance."""
        instance = self.get_by_id(instance_id)
        if not instance:
            return None

        for key, value in update_data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        instance.updated_at = datetime.utcnow()

        try:
            self.db.commit()
            self.db.refresh(instance)
            return instance
        except IntegrityError:
            self.db.rollback()
            raise ConflictError("Service instance update failed due to data conflict")

    def _generate_service_number(self) -> str:
        """Generate unique service number."""
        # Get current count for today
        today = date.today()
        count = (
            self.db.query(func.count(ServiceInstance.id))
            .filter(
                and_(
                    ServiceInstance.tenant_id == self.tenant_id,
                    func.date(ServiceInstance.created_at) == today,
                )
            )
            .scalar()
        )

        return f"SVC-{today.strftime('%Y%m%d')}-{count + 1:04d}"


class ProvisioningTaskRepository:
    """Repository for provisioning task database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def create(self, task_data: Dict[str, Any]) -> ProvisioningTask:
        """Create a new provisioning task."""
        task = ProvisioningTask(id=uuid4(), tenant_id=self.tenant_id, **task_data)

        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def get_by_id(self, task_id: UUID) -> Optional[ProvisioningTask]:
        """Get provisioning task by ID."""
        return (
            self.db.query(ProvisioningTask)
            .filter(
                and_(
                    ProvisioningTask.id == task_id,
                    ProvisioningTask.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    def list_by_service_instance(
        self, service_instance_id: UUID
    ) -> List[ProvisioningTask]:
        """List provisioning tasks for a service instance."""
        return (
            self.db.query(ProvisioningTask)
            .filter(
                and_(
                    ProvisioningTask.service_instance_id == service_instance_id,
                    ProvisioningTask.tenant_id == self.tenant_id,
                )
            )
            .order_by(ProvisioningTask.created_at.desc())
            .all()
        )

    def list_pending_tasks(self, limit: int = 100) -> List[ProvisioningTask]:
        """List pending provisioning tasks."""
        return (
            self.db.query(ProvisioningTask)
            .filter(
                and_(
                    ProvisioningTask.status == ProvisioningStatus.PENDING,
                    ProvisioningTask.tenant_id == self.tenant_id,
                )
            )
            .order_by(ProvisioningTask.created_at)
            .limit(limit)
            .all()
        )

    def update_status(
        self,
        task_id: UUID,
        status: ProvisioningStatus,
        result_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> Optional[ProvisioningTask]:
        """Update provisioning task status."""
        task = self.get_by_id(task_id)
        if not task:
            return None

        task.status = status
        task.updated_at = datetime.utcnow()

        if status == ProvisioningStatus.IN_PROGRESS and not task.started_date:
            task.started_date = datetime.utcnow()
        elif status in [
            ProvisioningStatus.COMPLETED,
            ProvisioningStatus.FAILED,
            ProvisioningStatus.CANCELLED,
        ]:
            task.completed_date = datetime.utcnow()

        if result_data:
            task.result_data = result_data
        if error_message:
            task.error_message = error_message

        self.db.commit()
        self.db.refresh(task)
        return task
