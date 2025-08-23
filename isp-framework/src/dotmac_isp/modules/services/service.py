"""Service layer for ISP service provisioning and management."""

from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.orm import Session

from dotmac_isp.core.settings import get_settings
from dotmac_isp.core.celery_app import celery_app
from dotmac_isp.modules.services import schemas
from dotmac_isp.modules.services.models import (
    ServicePlan,
    ServiceInstance,
    ProvisioningTask,
    ServiceAddon,
    ServiceType,
    ServiceStatus,
    ProvisioningStatus,
)
from dotmac_isp.modules.services.repository import (
    ServicePlanRepository,
    ServiceInstanceRepository,
    ProvisioningTaskRepository,
)
from dotmac_isp.shared.exceptions import (
    ServiceError,
    NotFoundError,
    ValidationError,
    ConflictError,
)
from dotmac_isp.sdks.networking.device_provisioning import DeviceProvisioningSDK
from dotmac_isp.sdks.services.provisioning_bindings import ProvisioningBindingsSDK


class ServiceProvisioningService:
    """Service layer for ISP service provisioning operations."""

    def __init__(self, db: Session, tenant_id: Optional[str] = None):
        """Initialize service provisioning service."""
        self.db = db
        self.settings = get_settings()
        self.tenant_id = UUID(tenant_id) if tenant_id else UUID(self.settings.tenant_id)

        # Repositories
        self.plan_repo = ServicePlanRepository(db, self.tenant_id)
        self.instance_repo = ServiceInstanceRepository(db, self.tenant_id)
        self.task_repo = ProvisioningTaskRepository(db, self.tenant_id)

        # SDKs for network integration
        self.device_provisioning_sdk = DeviceProvisioningSDK(str(self.tenant_id))
        self.provisioning_bindings_sdk = ProvisioningBindingsSDK(str(self.tenant_id))

    # Service Plan Management
    async def create_service_plan(
        self, plan_data: schemas.ServicePlanCreate
    ) -> ServicePlan:
        """Create a new service plan."""
        try:
            # Validate plan data
            if plan_data.monthly_price < 0:
                raise ValidationError("Monthly price cannot be negative")

            # Convert Pydantic model to dict for repository
            plan_dict = plan_data.dict()
            plan_dict["monthly_price"] = Decimal(str(plan_data.monthly_price))
            plan_dict["setup_fee"] = Decimal(str(plan_data.setup_fee))
            plan_dict["cancellation_fee"] = Decimal(str(plan_data.cancellation_fee))

            # Create plan
            plan = self.plan_repo.create(plan_dict)

            return plan

        except Exception as e:
            raise ServiceError(f"Failed to create service plan: {str(e)}")

    async def get_service_plan(self, plan_id: UUID) -> ServicePlan:
        """Get service plan by ID."""
        plan = self.plan_repo.get_by_id(plan_id)
        if not plan:
            raise NotFoundError(f"Service plan not found: {plan_id}")
        return plan

    async def get_service_plan_by_code(self, plan_code: str) -> ServicePlan:
        """Get service plan by plan code."""
        plan = self.plan_repo.get_by_plan_code(plan_code)
        if not plan:
            raise NotFoundError(f"Service plan not found: {plan_code}")
        return plan

    async def list_service_plans(
        self,
        service_type: Optional[ServiceType] = None,
        is_active: Optional[bool] = None,
        is_public: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ServicePlan]:
        """List service plans with filtering."""
        return self.plan_repo.list_plans(
            service_type=service_type,
            is_active=is_active,
            is_public=is_public,
            skip=skip,
            limit=limit,
        )

    # Service Instance Management
    async def provision_service(
        self,
        customer_id: UUID,
        service_plan_id: UUID,
        provisioning_data: schemas.ServiceProvisioningRequest,
    ) -> ServiceInstance:
        """Provision a new service for a customer."""
        try:
            # Get service plan
            plan = await self.get_service_plan(service_plan_id)

            # Create service instance
            instance_data = {
                "customer_id": customer_id,
                "service_plan_id": service_plan_id,
                "status": ServiceStatus.PENDING,
                "monthly_price": plan.monthly_price,
                "service_address": provisioning_data.service_address,
                "service_coordinates": provisioning_data.service_coordinates,
                "contract_start_date": provisioning_data.contract_start_date,
                "contract_end_date": provisioning_data.contract_end_date,
                "notes": provisioning_data.notes,
                "custom_config": provisioning_data.custom_config,
            }

            service_instance = self.instance_repo.create(instance_data)

            # Create provisioning task
            provisioning_task = await self._create_provisioning_task(
                service_instance.id,
                "activate",
                "Initial service activation",
                provisioning_data.dict(),
            )

            # Start background provisioning
            await self._start_provisioning_workflow(service_instance, provisioning_task)

            return service_instance

        except Exception as e:
            raise ServiceError(f"Failed to provision service: {str(e)}")

    async def get_service_instance(self, instance_id: UUID) -> ServiceInstance:
        """Get service instance by ID."""
        instance = self.instance_repo.get_by_id(instance_id)
        if not instance:
            raise NotFoundError(f"Service instance not found: {instance_id}")
        return instance

    async def get_service_by_number(self, service_number: str) -> ServiceInstance:
        """Get service instance by service number."""
        instance = self.instance_repo.get_by_service_number(service_number)
        if not instance:
            raise NotFoundError(f"Service not found: {service_number}")
        return instance

    async def list_customer_services(
        self, customer_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[ServiceInstance]:
        """List services for a specific customer."""
        return self.instance_repo.list_by_customer(customer_id, skip, limit)

    async def update_service_status(
        self, instance_id: UUID, status: ServiceStatus, notes: Optional[str] = None
    ) -> ServiceInstance:
        """Update service instance status."""
        instance = self.instance_repo.update_status(instance_id, status, notes)
        if not instance:
            raise NotFoundError(f"Service instance not found: {instance_id}")

        # Create status change task if needed
        if status == ServiceStatus.SUSPENDED:
            await self._create_provisioning_task(
                instance_id,
                "suspend",
                f'Service suspended: {notes or "No reason provided"}',
            )
        elif status == ServiceStatus.CANCELLED:
            await self._create_provisioning_task(
                instance_id,
                "deactivate",
                f'Service cancelled: {notes or "No reason provided"}',
            )

        return instance

    async def modify_service(
        self, instance_id: UUID, modification_data: schemas.ServiceModificationRequest
    ) -> ServiceInstance:
        """Modify an existing service."""
        try:
            instance = await self.get_service_instance(instance_id)

            update_data = {}

            # Handle plan change
            if modification_data.new_service_plan_id:
                new_plan = await self.get_service_plan(
                    modification_data.new_service_plan_id
                )
                update_data["service_plan_id"] = modification_data.new_service_plan_id
                update_data["monthly_price"] = new_plan.monthly_price

                # Create modification task
                await self._create_provisioning_task(
                    instance_id,
                    "modify",
                    f"Plan change from {instance.service_plan_id} to {modification_data.new_service_plan_id}",
                    {
                        "old_plan_id": str(instance.service_plan_id),
                        "new_plan_id": str(modification_data.new_service_plan_id),
                    },
                )

            # Handle address change
            if modification_data.new_service_address:
                update_data["service_address"] = modification_data.new_service_address
                update_data["service_coordinates"] = (
                    modification_data.new_service_coordinates
                )

                await self._create_provisioning_task(
                    instance_id,
                    "relocate",
                    "Service relocation",
                    {
                        "old_address": instance.service_address,
                        "new_address": modification_data.new_service_address,
                    },
                )

            # Update other fields
            if modification_data.notes:
                update_data["notes"] = (
                    f"{instance.notes or ''}\n{datetime.utcnow().isoformat()}: {modification_data.notes}".strip()
                )

            if modification_data.custom_config:
                update_data["custom_config"] = {
                    **(instance.custom_config or {}),
                    **modification_data.custom_config,
                }

            # Apply updates
            updated_instance = self.instance_repo.update(instance_id, update_data)
            if not updated_instance:
                raise ServiceError("Failed to update service instance")

            return updated_instance

        except Exception as e:
            raise ServiceError(f"Failed to modify service: {str(e)}")

    # Provisioning Task Management
    async def _create_provisioning_task(
        self,
        service_instance_id: UUID,
        task_type: str,
        description: str,
        task_data: Optional[Dict[str, Any]] = None,
    ) -> ProvisioningTask:
        """Create a provisioning task."""
        task_data_dict = {
            "service_instance_id": service_instance_id,
            "task_type": task_type,
            "description": description,
            "task_data": task_data or {},
            "status": ProvisioningStatus.PENDING,
        }

        return self.task_repo.create(task_data_dict)

    async def get_provisioning_task(self, task_id: UUID) -> ProvisioningTask:
        """Get provisioning task by ID."""
        task = self.task_repo.get_by_id(task_id)
        if not task:
            raise NotFoundError(f"Provisioning task not found: {task_id}")
        return task

    async def list_service_tasks(
        self, service_instance_id: UUID
    ) -> List[ProvisioningTask]:
        """List provisioning tasks for a service instance."""
        return self.task_repo.list_by_service_instance(service_instance_id)

    async def update_task_status(
        self,
        task_id: UUID,
        status: ProvisioningStatus,
        result_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> ProvisioningTask:
        """Update provisioning task status."""
        task = self.task_repo.update_status(task_id, status, result_data, error_message)
        if not task:
            raise NotFoundError(f"Provisioning task not found: {task_id}")
        return task

    # Private helper methods
    async def _start_provisioning_workflow(
        self, service_instance: ServiceInstance, provisioning_task: ProvisioningTask
    ):
        """Start the provisioning workflow."""
        try:
            # Update task status to in progress
            await self.update_task_status(
                provisioning_task.id, ProvisioningStatus.IN_PROGRESS
            )

            # Create device provisioning workflow
            workflow = (
                await self.device_provisioning_sdk.create_service_activation_workflow(
                    customer_id=str(service_instance.customer_id),
                    service_type=service_instance.service_plan.service_type.value,
                    device_id=f"device-{service_instance.service_number}",
                    service_parameters={
                        "bandwidth": service_instance.service_plan.download_speed,
                        "service_plan_id": str(service_instance.service_plan_id),
                        "service_address": service_instance.service_address,
                    },
                )
            )

            # Execute workflow
            result = await self.device_provisioning_sdk.execute_provisioning_workflow(
                workflow["workflow_id"]
            )

            if result["status"] == "completed":
                # Update service status to active
                await self.update_service_status(
                    service_instance.id,
                    ServiceStatus.ACTIVE,
                    "Service automatically activated",
                )

                # Update task status
                await self.update_task_status(
                    provisioning_task.id,
                    ProvisioningStatus.COMPLETED,
                    result_data={"workflow_result": result},
                )
            else:
                # Update task status to failed
                await self.update_task_status(
                    provisioning_task.id,
                    ProvisioningStatus.FAILED,
                    error_message=result.get("error", "Provisioning workflow failed"),
                )

        except Exception as e:
            # Update task status to failed
            await self.update_task_status(
                provisioning_task.id, ProvisioningStatus.FAILED, error_message=str(e)
            )

            # Schedule retry or manual intervention
            celery_app.send_task(
                "dotmac_isp.modules.services.tasks.handle_provisioning_failure",
                args=[str(service_instance.id), str(provisioning_task.id), str(e)],
            )

    async def _calculate_monthly_price(
        self, plan: ServicePlan, modifications: Optional[Dict[str, Any]] = None
    ) -> Decimal:
        """Calculate monthly price with modifications."""
        base_price = plan.monthly_price

        if not modifications:
            return base_price

        # Add logic for price modifications based on customizations
        # For example: bandwidth upgrades, additional IPs, etc.

        return base_price


class ServicePlanService:
    """Service layer for service plan management."""

    def __init__(self, db: Session, tenant_id: Optional[str] = None):
        """Initialize service plan service."""
        self.db = db
        self.settings = get_settings()
        self.tenant_id = UUID(tenant_id) if tenant_id else UUID(self.settings.tenant_id)
        self.plan_repo = ServicePlanRepository(db, self.tenant_id)

    async def create_plan(self, plan_data: schemas.ServicePlanCreate) -> ServicePlan:
        """Create a new service plan."""
        service = ServiceProvisioningService(self.db, str(self.tenant_id))
        return await service.create_service_plan(plan_data)

    async def get_plan(self, plan_id: UUID) -> ServicePlan:
        """Get service plan by ID."""
        service = ServiceProvisioningService(self.db, str(self.tenant_id))
        return await service.get_service_plan(plan_id)

    async def update_plan(
        self, plan_id: UUID, update_data: schemas.ServicePlanUpdate
    ) -> ServicePlan:
        """Update service plan."""
        try:
            # Convert Pydantic model to dict, excluding None values
            update_dict = {
                k: v
                for k, v in update_data.dict(exclude_unset=True).items()
                if v is not None
            }

            # Convert decimal fields
            if "monthly_price" in update_dict:
                update_dict["monthly_price"] = Decimal(
                    str(update_dict["monthly_price"])
                )
            if "setup_fee" in update_dict:
                update_dict["setup_fee"] = Decimal(str(update_dict["setup_fee"]))
            if "cancellation_fee" in update_dict:
                update_dict["cancellation_fee"] = Decimal(
                    str(update_dict["cancellation_fee"])
                )

            plan = self.plan_repo.update(plan_id, update_dict)
            if not plan:
                raise NotFoundError(f"Service plan not found: {plan_id}")

            return plan

        except Exception as e:
            raise ServiceError(f"Failed to update service plan: {str(e)}")

    async def delete_plan(self, plan_id: UUID) -> bool:
        """Delete service plan."""
        success = self.plan_repo.delete(plan_id)
        if not success:
            raise NotFoundError(f"Service plan not found: {plan_id}")
        return success

    async def list_plans(
        self,
        service_type: Optional[ServiceType] = None,
        is_active: Optional[bool] = None,
        is_public: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ServicePlan]:
        """List service plans."""
        return self.plan_repo.list_plans(
            service_type=service_type,
            is_active=is_active,
            is_public=is_public,
            skip=skip,
            limit=limit,
        )
