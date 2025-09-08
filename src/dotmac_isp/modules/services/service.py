"""Service management business logic layer."""

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from dotmac.application import standard_exception_handler
from dotmac.core.exceptions import (
    BusinessRuleError,
    EntityNotFoundError,
    ValidationError,
)
from dotmac_shared.services.base import BaseManagementService as BaseTenantService

from . import schemas
from .models import ServiceInstance
from .repository import (
    ServiceInstanceRepository,
    ServicePlanRepository,
    ServiceProvisioningRepository,
    ServiceStatusHistoryRepository,
    ServiceUsageMetricRepository,
)

logger = logging.getLogger(__name__)


class ServicesService(BaseTenantService):
    """Main services orchestrator for service management operations."""

    def __init__(self, db: Session, tenant_id: str):
        super().__init__(
            db=db,
            model_class=ServiceInstance,
            create_schema=schemas.ServiceInstanceCreate,
            update_schema=schemas.ServiceInstanceUpdate,
            response_schema=schemas.ServiceInstanceResponse,
            tenant_id=tenant_id,
        )

        # Initialize repositories
        self.service_plan_repo = ServicePlanRepository(db, tenant_id)
        self.service_instance_repo = ServiceInstanceRepository(db, tenant_id)
        self.provisioning_repo = ServiceProvisioningRepository(db, tenant_id)
        self.status_history_repo = ServiceStatusHistoryRepository(db, tenant_id)
        self.usage_repo = ServiceUsageMetricRepository(db, tenant_id)

    # =================================================================
    # SERVICE PLAN MANAGEMENT
    # =================================================================

    @standard_exception_handler
    async def create_service_plan(self, plan_data: schemas.ServicePlanCreate) -> schemas.ServicePlanResponse:
        """Create a new service plan."""
        # Validate plan code is unique
        existing_plan = self.service_plan_repo.get_by_code(plan_data.plan_code)
        if existing_plan:
            raise ValidationError(f"Service plan with code '{plan_data.plan_code}' already exists")

        # Validate business rules
        await self._validate_service_plan_rules(plan_data)

        plan = self.service_plan_repo.create(plan_data.model_dump())
        logger.info(f"Created service plan: {plan.plan_code}")

        return schemas.ServicePlanResponse.model_validate(plan)

    @standard_exception_handler
    async def get_service_plan(self, plan_id: UUID) -> Optional[schemas.ServicePlanResponse]:
        """Get service plan by ID."""
        plan = self.service_plan_repo.get_by_id(plan_id)
        if not plan:
            return None
        return schemas.ServicePlanResponse.model_validate(plan)

    @standard_exception_handler
    async def get_service_plan_by_code(self, plan_code: str) -> Optional[schemas.ServicePlanResponse]:
        """Get service plan by code."""
        plan = self.service_plan_repo.get_by_code(plan_code)
        if not plan:
            return None
        return schemas.ServicePlanResponse.model_validate(plan)

    @standard_exception_handler
    async def list_service_plans(
        self, filters: Optional[dict[str, Any]] = None, limit: int = 50, offset: int = 0
    ) -> list[schemas.ServicePlanResponse]:
        """List service plans with filtering."""
        plans = self.service_plan_repo.list(filters=filters, limit=limit, offset=offset, sort_by="name")
        return [schemas.ServicePlanResponse.model_validate(plan) for plan in plans]

    @standard_exception_handler
    async def get_public_service_plans(self) -> list[schemas.ServicePlanResponse]:
        """Get all public service plans for customer selection."""
        plans = self.service_plan_repo.get_public_plans()
        return [schemas.ServicePlanResponse.model_validate(plan) for plan in plans]

    @standard_exception_handler
    async def get_service_plans_by_type(self, service_type: str) -> list[schemas.ServicePlanResponse]:
        """Get service plans by type."""
        plans = self.service_plan_repo.get_plans_by_type(service_type)
        return [schemas.ServicePlanResponse.model_validate(plan) for plan in plans]

    # =================================================================
    # SERVICE INSTANCE MANAGEMENT
    # =================================================================

    @standard_exception_handler
    async def activate_service(
        self, activation_request: schemas.ServiceActivationRequest
    ) -> schemas.ServiceActivationResponse:
        """Activate a new service for a customer."""
        # Validate service plan exists and is active
        service_plan = self.service_plan_repo.get_by_id(activation_request.service_plan_id)
        if not service_plan:
            raise EntityNotFoundError(f"Service plan not found: {activation_request.service_plan_id}")

        if not service_plan.is_active:
            raise BusinessRuleError("Service plan is not currently active")

        # Generate unique service number
        service_number = await self._generate_service_number(service_plan.service_type)

        # Calculate pricing
        monthly_price = service_plan.monthly_price
        setup_cost = service_plan.setup_fee

        # Create service instance
        service_data = {
            "service_number": service_number,
            "customer_id": activation_request.customer_id,
            "service_plan_id": activation_request.service_plan_id,
            "status": "pending",
            "service_address": activation_request.service_address,
            "service_coordinates": activation_request.service_coordinates,
            "monthly_price": monthly_price,
            "contract_start_date": date.today(),
        }

        if activation_request.contract_months:
            service_data["contract_end_date"] = date.today() + timedelta(days=activation_request.contract_months * 30)

        service_instance = self.service_instance_repo.create(service_data)

        # Create provisioning task
        provisioning_data = {
            "service_instance_id": service_instance.id,
            "provisioning_status": "pending",
            "scheduled_date": activation_request.preferred_installation_date or (datetime.now() + timedelta(days=3)),
            "installation_notes": activation_request.installation_notes,
            "equipment_required": [],  # Will be populated based on service type
        }

        provisioning_task = self.provisioning_repo.create(provisioning_data)

        # Record status change
        self.status_history_repo.add_status_change(
            service_instance.id,
            None,
            "pending",
            "Service activation requested",
            effective_date=datetime.now(),
        )

        logger.info(f"Activated service {service_number} for customer {activation_request.customer_id}")

        return schemas.ServiceActivationResponse(
            service_instance=schemas.ServiceInstanceResponse.model_validate(service_instance),
            provisioning_task=schemas.ProvisioningTaskResponse.model_validate(provisioning_task),
            estimated_activation=provisioning_data["scheduled_date"],
            total_setup_cost=setup_cost,
            monthly_recurring_cost=monthly_price,
        )

    @standard_exception_handler
    async def get_service_instance(self, service_id: UUID) -> Optional[schemas.ServiceInstanceResponse]:
        """Get service instance by ID."""
        service = self.service_instance_repo.get_by_id(service_id)
        if not service:
            return None
        return schemas.ServiceInstanceResponse.model_validate(service)

    @standard_exception_handler
    async def get_service_by_number(self, service_number: str) -> Optional[schemas.ServiceInstanceResponse]:
        """Get service instance by service number."""
        service = self.service_instance_repo.get_by_service_number(service_number)
        if not service:
            return None
        return schemas.ServiceInstanceResponse.model_validate(service)

    @standard_exception_handler
    async def get_customer_services(self, customer_id: UUID) -> list[schemas.ServiceInstanceResponse]:
        """Get all services for a customer."""
        services = self.service_instance_repo.get_customer_services(customer_id)
        return [schemas.ServiceInstanceResponse.model_validate(service) for service in services]

    @standard_exception_handler
    async def update_service_status(
        self,
        service_id: UUID,
        status_update: schemas.ServiceStatusUpdate,
        user_id: Optional[UUID] = None,
    ) -> schemas.ServiceInstanceResponse:
        """Update service status with history tracking."""
        service = self.service_instance_repo.get_by_id_or_raise(service_id)
        old_status = service.status

        # Validate status transition
        await self._validate_status_transition(old_status, status_update.status)

        # Update service
        update_data = {"status": status_update.status}

        if status_update.effective_date:
            if status_update.status == "active":
                update_data["activation_date"] = status_update.effective_date
            elif status_update.status == "suspended":
                update_data["suspension_date"] = status_update.effective_date
            elif status_update.status == "cancelled":
                update_data["cancellation_date"] = status_update.effective_date

        updated_service = self.service_instance_repo.update(service_id, update_data)

        # Record status change
        self.status_history_repo.add_status_change(
            service_id,
            old_status,
            status_update.status,
            status_update.reason,
            user_id,
            status_update.effective_date,
        )

        logger.info(f"Updated service {service.service_number} status: {old_status} -> {status_update.status}")

        return schemas.ServiceInstanceResponse.model_validate(updated_service)

    @standard_exception_handler
    async def suspend_service(
        self, service_id: UUID, reason: str, user_id: Optional[UUID] = None
    ) -> schemas.ServiceInstanceResponse:
        """Suspend a service."""
        status_update = schemas.ServiceStatusUpdate(status="suspended", reason=reason, effective_date=datetime.now())
        return await self.update_service_status(service_id, status_update, user_id)

    @standard_exception_handler
    async def reactivate_service(
        self, service_id: UUID, reason: str, user_id: Optional[UUID] = None
    ) -> schemas.ServiceInstanceResponse:
        """Reactivate a suspended service."""
        status_update = schemas.ServiceStatusUpdate(status="active", reason=reason, effective_date=datetime.now())
        return await self.update_service_status(service_id, status_update, user_id)

    @standard_exception_handler
    async def cancel_service(
        self,
        service_id: UUID,
        reason: str,
        effective_date: Optional[datetime] = None,
        user_id: Optional[UUID] = None,
    ) -> schemas.ServiceInstanceResponse:
        """Cancel a service."""
        status_update = schemas.ServiceStatusUpdate(
            status="cancelled",
            reason=reason,
            effective_date=effective_date or datetime.now(),
        )
        return await self.update_service_status(service_id, status_update, user_id)

    # =================================================================
    # PROVISIONING MANAGEMENT
    # =================================================================

    @standard_exception_handler
    async def get_pending_provisioning(self) -> list[schemas.ProvisioningTaskResponse]:
        """Get all pending provisioning tasks."""
        tasks = self.provisioning_repo.get_pending_provisioning()
        return [schemas.ProvisioningTaskResponse.model_validate(task) for task in tasks]

    @standard_exception_handler
    async def assign_provisioning_technician(
        self, provisioning_id: UUID, technician_id: UUID
    ) -> schemas.ProvisioningTaskResponse:
        """Assign technician to provisioning task."""
        task = self.provisioning_repo.update(
            provisioning_id,
            {
                "assigned_technician_id": technician_id,
                "provisioning_status": "in_progress",
            },
        )

        logger.info(f"Assigned technician {technician_id} to provisioning task {provisioning_id}")

        return schemas.ProvisioningTaskResponse.model_validate(task)

    @standard_exception_handler
    async def complete_provisioning(
        self, provisioning_id: UUID, completion_data: dict[str, Any]
    ) -> schemas.ProvisioningTaskResponse:
        """Complete provisioning task."""
        update_data = {
            "provisioning_status": "completed",
            "completed_date": datetime.now(),
            "completion_notes": completion_data.get("notes"),
            "test_results": completion_data.get("test_results", {}),
            "tested": completion_data.get("tested", False),
            "customer_signature": completion_data.get("customer_signature"),
        }

        task = self.provisioning_repo.update(provisioning_id, update_data)

        # Auto-activate service if provisioning is successful
        if completion_data.get("tested", False):
            await self.update_service_status(
                task.service_instance_id,
                schemas.ServiceStatusUpdate(
                    status="active",
                    reason="Provisioning completed successfully",
                    effective_date=datetime.now(),
                ),
            )

        logger.info(f"Completed provisioning task {provisioning_id}")

        return schemas.ProvisioningTaskResponse.model_validate(task)

    # =================================================================
    # USAGE AND ANALYTICS
    # =================================================================

    @standard_exception_handler
    async def record_service_usage(
        self,
        service_id: UUID,
        usage_date: date,
        data_downloaded_mb: float,
        data_uploaded_mb: float,
        **kwargs,
    ) -> schemas.ServiceUsageResponse:
        """Record daily usage for a service."""
        usage = self.usage_repo.record_daily_usage(
            service_id, usage_date, data_downloaded_mb, data_uploaded_mb, **kwargs
        )

        return schemas.ServiceUsageResponse.model_validate(usage)

    @standard_exception_handler
    async def get_service_usage(
        self, service_id: UUID, start_date: date, end_date: date
    ) -> list[schemas.ServiceUsageResponse]:
        """Get usage metrics for a service."""
        usage_records = self.usage_repo.get_service_usage(service_id, start_date, end_date)
        return [schemas.ServiceUsageResponse.model_validate(record) for record in usage_records]

    @standard_exception_handler
    async def get_service_dashboard(self) -> schemas.ServiceDashboard:
        """Get service dashboard metrics."""
        stats = self.service_instance_repo.get_service_statistics()

        # Calculate churn rate (cancelled services in last 30 days / total active at start of period)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        recent_cancellations = await self.service_instance_repo.count_cancelled_since(thirty_days_ago)
        churn_rate = Decimal("0")
        if stats["status_breakdown"].get("active", 0) > 0:
            churn_rate = (
                Decimal(str(recent_cancellations)) / Decimal(str(stats["status_breakdown"]["active"]))
            ) * Decimal("100")

        # Get most popular plans
        popular_plans = await self.service_plan_repo.get_most_popular_plans(limit=5)

        return schemas.ServiceDashboard(
            total_services=sum(stats["status_breakdown"].values()),
            active_services=stats["status_breakdown"].get("active", 0),
            pending_activations=stats["status_breakdown"].get("pending", 0),
            suspended_services=stats["status_breakdown"].get("suspended", 0),
            cancelled_services=stats["status_breakdown"].get("cancelled", 0),
            monthly_revenue=Decimal(str(stats["monthly_recurring_revenue"])),
            avg_service_value=Decimal(str(stats["monthly_recurring_revenue"]))
            / max(stats["status_breakdown"].get("active", 1), 1),
            churn_rate=churn_rate,
            most_popular_plans=[plan.name for plan in popular_plans],
        )

    # =================================================================
    # BUSINESS RULE VALIDATION
    # =================================================================

    async def _validate_service_plan_rules(self, plan_data: schemas.ServicePlanCreate) -> None:
        """Validate service plan business rules."""
        if plan_data.max_contract_months and plan_data.min_contract_months > plan_data.max_contract_months:
            raise BusinessRuleError("Minimum contract months cannot exceed maximum contract months")

        if plan_data.monthly_price <= 0:
            raise BusinessRuleError("Monthly price must be greater than zero")

        if plan_data.service_type == "internet" and not plan_data.download_speed:
            raise BusinessRuleError("Internet services must have download speed specified")

    async def _validate_status_transition(self, current_status: str, new_status: str) -> None:
        """Validate service status transitions."""
        valid_transitions = {
            "pending": ["active", "cancelled"],
            "active": ["suspended", "maintenance", "cancelled"],
            "suspended": ["active", "cancelled"],
            "maintenance": ["active", "cancelled"],
            "cancelled": [],  # No transitions from cancelled
        }

        if new_status not in valid_transitions.get(current_status, []):
            raise BusinessRuleError(f"Invalid status transition from {current_status} to {new_status}")

    async def _generate_service_number(self, service_type: str) -> str:
        """Generate unique service number."""
        prefix_map = {
            "internet": "INT",
            "phone": "PHN",
            "tv": "TV",
            "bundle": "BDL",
            "hosting": "HST",
            "cloud": "CLD",
            "managed_services": "MSV",
        }

        prefix = prefix_map.get(service_type, "SVC")
        timestamp = datetime.now().strftime("%Y%m%d")
        random_suffix = uuid4().hex[:6].upper()

        return f"{prefix}-{timestamp}-{random_suffix}"


# Export main service
__all__ = ["ServicesService"]
