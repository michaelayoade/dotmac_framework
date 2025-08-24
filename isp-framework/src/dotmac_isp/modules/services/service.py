"""Service layer for ISP service provisioning and management."""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.orm import Session

from dotmac_isp.shared.base_service import BaseTenantService
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
from dotmac_isp.shared.exceptions import (
    ServiceError,
    EntityNotFoundError,
    ValidationError,
    BusinessRuleError,
)
from dotmac_isp.sdks.networking.device_provisioning import DeviceProvisioningSDK
from dotmac_isp.sdks.services.provisioning_bindings import ProvisioningBindingsSDK


class ServicePlanService(BaseTenantService[ServicePlan, schemas.ServicePlanCreate, schemas.ServicePlanUpdate, schemas.ServicePlanResponse]):
    """Service for service plan management."""

    def __init__(self, db: Session, tenant_id: str):
        """  Init   operation."""
        super().__init__(
            db=db,
            model_class=ServicePlan,
            create_schema=schemas.ServicePlanCreate,
            update_schema=schemas.ServicePlanUpdate,
            response_schema=schemas.ServicePlanResponse,
            tenant_id=tenant_id
        )

    async def _validate_create_rules(self, data: schemas.ServicePlanCreate) -> None:
        """Validate business rules for service plan creation."""
        # Ensure plan name is unique for tenant
        if await self.repository.exists({'name': data.name}):
            raise BusinessRuleError(
                f"Service plan with name '{data.name}' already exists",
                rule_name="unique_plan_name"
            )
        
        # Validate pricing is positive
        if data.price <= 0:
            raise ValidationError("Service plan price must be positive")

    async def _validate_update_rules(self, entity: ServicePlan, data: schemas.ServicePlanUpdate) -> None:
        """Validate business rules for service plan updates."""
        # Prevent price reduction if there are active subscriptions
        if data.price and data.price < entity.price:
            # Check for active service instances (simplified check)
            active_instances = await self.repository.count({'service_plan_id': entity.id, 'status': ServiceStatus.ACTIVE})
            if active_instances > 0:
                raise BusinessRuleError(
                    "Cannot reduce price of service plan with active instances",
                    rule_name="active_instances_price_protection"
                )


class ServiceInstanceService(BaseTenantService[ServiceInstance, schemas.ServiceInstanceCreate, schemas.ServiceInstanceUpdate, schemas.ServiceInstanceResponse]):
    """Service for service instance management."""

    def __init__(self, db: Session, tenant_id: str):
        """  Init   operation."""
        super().__init__(
            db=db,
            model_class=ServiceInstance,
            create_schema=schemas.ServiceInstanceCreate,
            update_schema=schemas.ServiceInstanceUpdate,
            response_schema=schemas.ServiceInstanceResponse,
            tenant_id=tenant_id
        )
        
        # SDKs for network integration
        self.device_provisioning_sdk = DeviceProvisioningSDK(tenant_id)
        self.provisioning_bindings_sdk = ProvisioningBindingsSDK(tenant_id)

    async def _validate_create_rules(self, data: schemas.ServiceInstanceCreate) -> None:
        """Validate business rules for service instance creation."""
        # Ensure customer exists (would need identity module integration)
        # For now, just validate required fields
        if not data.customer_id:
            raise ValidationError("Customer ID is required for service instance")
        
        if not data.service_plan_id:
            raise ValidationError("Service plan ID is required")

    async def _post_create_hook(self, entity: ServiceInstance, data: schemas.ServiceInstanceCreate) -> None:
        """Start provisioning process after service instance creation."""
        try:
            # Create provisioning task
            from .tasks import start_service_provisioning
            task_result = start_service_provisioning.delay(str(entity.id), str(self.tenant_id))
            
            # Update instance with task ID
            await self.repository.update(entity.id, {'provisioning_task_id': task_result.id}, commit=True)
            
        except Exception as e:
            self._logger.error(f"Failed to start provisioning for service instance {entity.id}: {e}")
            # Update status to indicate provisioning failed
            await self.repository.update(entity.id, {'status': ServiceStatus.SUSPENDED}, commit=True)

    async def _validate_update_rules(self, entity: ServiceInstance, data: schemas.ServiceInstanceUpdate) -> None:
        """Validate business rules for service instance updates."""
        # Prevent status changes if provisioning is in progress
        if data.status and entity.provisioning_status == ProvisioningStatus.IN_PROGRESS:
            raise BusinessRuleError(
                "Cannot change service status while provisioning is in progress",
                rule_name="provisioning_in_progress_protection"
            )


class ProvisioningTaskService(BaseTenantService[ProvisioningTask, schemas.ProvisioningTaskCreate, schemas.ProvisioningTaskUpdate, schemas.ProvisioningTaskResponse]):
    """Service for provisioning task management."""

    def __init__(self, db: Session, tenant_id: str):
        """  Init   operation."""
        super().__init__(
            db=db,
            model_class=ProvisioningTask,
            create_schema=schemas.ProvisioningTaskCreate,
            update_schema=schemas.ProvisioningTaskUpdate,
            response_schema=schemas.ProvisioningTaskResponse,
            tenant_id=tenant_id
        )

    async def _validate_create_rules(self, data: schemas.ProvisioningTaskCreate) -> None:
        """Validate business rules for provisioning task creation."""
        if not data.service_instance_id:
            raise ValidationError("Service instance ID is required for provisioning task")

    async def _post_update_hook(self, entity: ProvisioningTask, data: schemas.ProvisioningTaskUpdate) -> None:
        """Update service instance status when task completes."""
        if data.status == ProvisioningStatus.COMPLETED:
            # Update service instance status to active
            service_instance_service = ServiceInstanceService(self.db, self.tenant_id)
            await service_instance_service.update(
                entity.service_instance_id,
                schemas.ServiceInstanceUpdate(status=ServiceStatus.ACTIVE, provisioning_status=ProvisioningStatus.COMPLETED)
            )
        elif data.status == ProvisioningStatus.FAILED:
            # Update service instance status to suspended
            service_instance_service = ServiceInstanceService(self.db, self.tenant_id)
            await service_instance_service.update(
                entity.service_instance_id,
                schemas.ServiceInstanceUpdate(status=ServiceStatus.SUSPENDED, provisioning_status=ProvisioningStatus.FAILED)
            )


# Legacy service for backward compatibility
class ServiceProvisioningService:
    """Legacy service provisioning service - use individual services instead."""

    def __init__(self, db: Session, tenant_id: str):
        """  Init   operation."""
        self.db = db
        self.tenant_id = tenant_id
        self.plan_service = ServicePlanService(db, tenant_id)
        self.instance_service = ServiceInstanceService(db, tenant_id)
        self.task_service = ProvisioningTaskService(db, tenant_id)

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
