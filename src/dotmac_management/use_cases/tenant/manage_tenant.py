"""
Manage Tenant Use Case
Handles tenant lifecycle management operations
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from dotmac.database.base import get_db_session
from dotmac_shared.core.logging import get_logger
from dotmac_shared.exceptions import ExceptionContext

from ...infrastructure import get_adapter_factory
from ...models.tenant import CustomerTenant, TenantStatus
from ..base import TransactionalUseCase, UseCaseContext, UseCaseResult

logger = get_logger(__name__)


class TenantOperation(str, Enum):
    """Available tenant management operations"""

    SUSPEND = "suspend"
    RESUME = "resume"
    SCALE = "scale"
    UPDATE_CONFIG = "update_config"
    BACKUP = "backup"
    RESTORE = "restore"
    DELETE = "delete"


@dataclass
class ManageTenantInput:
    """Input data for tenant management operations"""

    tenant_id: str
    operation: TenantOperation
    parameters: dict[str, Any] = None
    reason: str = ""
    scheduled_at: Optional[str] = None

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


@dataclass
class ManageTenantOutput:
    """Output data for tenant management operations"""

    tenant_id: str
    operation: TenantOperation
    success: bool
    previous_status: TenantStatus
    new_status: TenantStatus
    operation_details: dict[str, Any]
    rollback_info: Optional[dict[str, Any]] = None


class ManageTenantUseCase(TransactionalUseCase[ManageTenantInput, ManageTenantOutput]):
    """
    Manage tenant lifecycle operations.

    Supports operations like:
    - Suspend/Resume tenant services
    - Scale tenant resources
    - Update tenant configuration
    - Backup/Restore tenant data
    - Delete tenant

    Each operation is transactional with rollback capabilities.
    """

    def __init__(self, input_data: dict[str, Any]):
        super().__init__()
        self.adapter_factory = None

    async def _ensure_dependencies(self, input_data: dict[str, Any]):
        """Ensure all dependencies are initialized"""
        if self.adapter_factory is None:
            self.adapter_factory = await get_adapter_factory()

    async def validate_input(self, input_data: ManageTenantInput) -> bool:
        """Validate tenant management input"""
        if not input_data.tenant_id or not input_data.tenant_id.strip():
            return False

        if not input_data.operation:
            return False

        # Validate operation-specific parameters
        if input_data.operation == TenantOperation.SCALE:
            if "instances" not in input_data.parameters:
                return False
            try:
                int(input_data.parameters["instances"])
            except (ValueError, TypeError):
                return False

        elif input_data.operation == TenantOperation.RESTORE:
            if "backup_id" not in input_data.parameters:
                return False

        return True

    async def can_execute(self, input_data: dict[str, Any], context: Optional[UseCaseContext] = None) -> bool:
        """Check if tenant management operation can be executed"""

        # Check permissions
        if context and context.permissions:
            required_permission = f"tenant.{input_data.operation.value}"
            user_permissions = context.permissions.get("actions", [])

            if required_permission not in user_permissions:
                return False

        # Check infrastructure availability
        try:
            await self._ensure_dependencies()
            return True

        except ExceptionContext.LIFECYCLE_EXCEPTIONS as e:
            self.logger.error(f"Cannot execute tenant management: {e}")
            return False

    async def _execute_transaction(
        self, input_data: ManageTenantInput, context: Optional[UseCaseContext] = None
    ) -> UseCaseResult[ManageTenantOutput]:
        """Execute the tenant management transaction"""

        try:
            await self._ensure_dependencies()

            # Get tenant from database
            tenant = await self._get_tenant(input_data.tenant_id)
            if not tenant:
                return self._create_error_result(
                    f"Tenant {input_data.tenant_id} not found",
                    error_code="TENANT_NOT_FOUND",
                )

            previous_status = tenant.status

            # Execute the specific operation
            operation_result = await self._execute_operation(tenant, input_data)

            if not operation_result["success"]:
                return self._create_error_result(operation_result["error"], error_code="OPERATION_FAILED")

            # Update tenant status if needed
            new_status = operation_result.get("new_status", previous_status)
            if new_status != previous_status:
                await self._update_tenant_status(tenant, new_status)
                self.add_rollback_action(lambda: self._rollback_tenant_status(tenant.id, previous_status))

            # Create output data
            output_data = ManageTenantOutput(
                tenant_id=input_data.tenant_id,
                operation=input_data.operation,
                success=True,
                previous_status=previous_status,
                new_status=new_status,
                operation_details=operation_result.get("details", {}),
                rollback_info=operation_result.get("rollback_info"),
            )

            self.logger.info(
                "Tenant management operation completed",
                extra={
                    "tenant_id": input_data.tenant_id,
                    "operation": input_data.operation.value,
                    "previous_status": previous_status.value,
                    "new_status": new_status.value,
                },
            )

            return self._create_success_result(output_data)

        except ExceptionContext.LIFECYCLE_EXCEPTIONS as e:
            self.logger.error(f"Tenant management transaction failed: {e}")
            return self._create_error_result(str(e), error_code="TRANSACTION_FAILED")

    async def _get_tenant(self, tenant_id: str, input_data: dict[str, Any]) -> Optional[CustomerTenant]:
        """Get tenant from database"""
        with get_db_session() as db:
            return db.query(CustomerTenant).filter_by(tenant_id=tenant_id).first()

    async def _execute_operation(self, tenant: CustomerTenant, input_data: ManageTenantInput) -> dict[str, Any]:
        """Execute the specific tenant operation"""

        operation_map = {
            TenantOperation.SUSPEND: self._suspend_tenant,
            TenantOperation.RESUME: self._resume_tenant,
            TenantOperation.SCALE: self._scale_tenant,
            TenantOperation.UPDATE_CONFIG: self._update_tenant_config,
            TenantOperation.BACKUP: self._backup_tenant,
            TenantOperation.RESTORE: self._restore_tenant,
            TenantOperation.DELETE: self._delete_tenant,
        }

        operation_func = operation_map.get(input_data.operation)
        if not operation_func:
            return {
                "success": False,
                "error": f"Unsupported operation: {input_data.operation}",
            }

        return await operation_func(tenant, input_data.parameters)

    async def _suspend_tenant(self, tenant: CustomerTenant, parameters: dict[str, Any]) -> dict[str, Any]:
        """Suspend tenant services"""
        try:
            deployment_adapter = await self.adapter_factory.get_deployment_adapter()

            if tenant.container_id:
                success = await deployment_adapter.stop_deployment(tenant.container_id)
                if not success:
                    return {
                        "success": False,
                        "error": "Failed to stop tenant deployment",
                    }

            return {
                "success": True,
                "new_status": TenantStatus.SUSPENDED,
                "details": {
                    "suspended_at": datetime.utcnow().isoformat(),
                    "reason": parameters.get("reason", "Administrative action"),
                },
                "rollback_info": {
                    "action": "resume",
                    "container_id": tenant.container_id,
                },
            }

        except ExceptionContext.EXTERNAL_SERVICE_EXCEPTIONS as e:
            return {"success": False, "error": f"Suspend operation failed: {e}"}

    async def _resume_tenant(self, tenant: CustomerTenant, parameters: dict[str, Any]) -> dict[str, Any]:
        """Resume tenant services"""
        try:
            deployment_adapter = await self.adapter_factory.get_deployment_adapter()

            if tenant.container_id:
                # Check current status
                status = await deployment_adapter.get_deployment_status(tenant.container_id)

                if status.get("status") != "running":
                    # Would implement resume logic based on deployment provider
                    pass

            return {
                "success": True,
                "new_status": TenantStatus.ACTIVE,
                "details": {
                    "resumed_at": datetime.utcnow().isoformat(),
                    "reason": parameters.get("reason", "Administrative action"),
                },
            }

        except ExceptionContext.EXTERNAL_SERVICE_EXCEPTIONS as e:
            return {"success": False, "error": f"Resume operation failed: {e}"}

    async def _scale_tenant(self, tenant: CustomerTenant, parameters: dict[str, Any]) -> dict[str, Any]:
        """Scale tenant resources"""
        try:
            instances = int(parameters["instances"])
            deployment_adapter = await self.adapter_factory.get_deployment_adapter()

            if tenant.container_id:
                success = await deployment_adapter.scale_deployment(tenant.container_id, instances)
                if not success:
                    return {
                        "success": False,
                        "error": "Failed to scale tenant deployment",
                    }

            return {
                "success": True,
                "details": {
                    "scaled_to": instances,
                    "scaled_at": datetime.utcnow().isoformat(),
                },
            }

        except (
            ValueError,
            TypeError,
            ExceptionContext.EXTERNAL_SERVICE_EXCEPTIONS,
        ) as e:
            return {"success": False, "error": f"Scale operation failed: {e}"}

    async def _update_tenant_config(self, tenant: CustomerTenant, parameters: dict[str, Any]) -> dict[str, Any]:
        """Update tenant configuration"""
        try:
            config_updates = parameters.get("config", {})

            # Update tenant settings
            tenant.settings = tenant.settings or {}
            tenant.settings.update(config_updates)
            tenant.settings["config_updated_at"] = datetime.utcnow().isoformat()

            return {
                "success": True,
                "details": {
                    "updated_config": config_updates,
                    "updated_at": datetime.utcnow().isoformat(),
                },
            }

        except (ValueError, TypeError, KeyError) as e:
            return {"success": False, "error": f"Config update failed: {e}"}

    async def _backup_tenant(self, tenant: CustomerTenant, parameters: dict[str, Any]) -> dict[str, Any]:
        """Create tenant backup"""
        try:
            # Would implement backup logic using storage adapter
            backup_id = f"backup-{tenant.tenant_id}-{int(datetime.utcnow().timestamp())}"

            return {
                "success": True,
                "details": {
                    "backup_id": backup_id,
                    "created_at": datetime.utcnow().isoformat(),
                    "backup_type": parameters.get("backup_type", "full"),
                },
            }

        except ExceptionContext.LIFECYCLE_EXCEPTIONS as e:
            return {"success": False, "error": f"Backup operation failed: {e}"}

    async def _restore_tenant(self, tenant: CustomerTenant, parameters: dict[str, Any]) -> dict[str, Any]:
        """Restore tenant from backup"""
        try:
            backup_id = parameters["backup_id"]

            # Would implement restore logic using storage adapter

            return {
                "success": True,
                "new_status": TenantStatus.RESTORING,
                "details": {
                    "backup_id": backup_id,
                    "restore_started_at": datetime.utcnow().isoformat(),
                },
            }

        except (KeyError, ExceptionContext.LIFECYCLE_EXCEPTIONS) as e:
            return {"success": False, "error": f"Restore operation failed: {e}"}

    async def _delete_tenant(self, tenant: CustomerTenant, parameters: dict[str, Any]) -> dict[str, Any]:
        """Delete tenant and all resources"""
        try:
            force_delete = parameters.get("force", False)

            if not force_delete and tenant.status == TenantStatus.ACTIVE:
                return {
                    "success": False,
                    "error": "Cannot delete active tenant without force flag",
                }

            deployment_adapter = await self.adapter_factory.get_deployment_adapter()

            # Remove deployment
            if tenant.container_id:
                await deployment_adapter.remove_deployment(tenant.container_id)

            return {
                "success": True,
                "new_status": TenantStatus.DELETED,
                "details": {
                    "deleted_at": datetime.utcnow().isoformat(),
                    "force_delete": force_delete,
                },
            }

        except ExceptionContext.EXTERNAL_SERVICE_EXCEPTIONS as e:
            return {"success": False, "error": f"Delete operation failed: {e}"}

    async def _update_tenant_status(self, tenant: CustomerTenant, new_status: TenantStatus):
        """Update tenant status in database"""
        with get_db_session() as db:
            db_tenant = db.query(CustomerTenant).filter_by(id=tenant.id).first()
            if db_tenant:
                db_tenant.status = new_status
                db.commit()

    async def _rollback_tenant_status(self, tenant_id: int, previous_status: TenantStatus):
        """Rollback tenant status change"""
        try:
            with get_db_session() as db:
                tenant = db.query(CustomerTenant).filter_by(id=tenant_id).first()
                if tenant:
                    tenant.status = previous_status
                    db.commit()

                    self.logger.info(
                        "Rolled back tenant status",
                        extra={"tenant_id": tenant_id, "status": previous_status.value},
                    )

        except (SQLAlchemyError, ExceptionContext.LIFECYCLE_EXCEPTIONS) as e:
            self.logger.error(f"Failed to rollback tenant status: {e}")
