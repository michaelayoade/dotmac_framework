"""
Tenant Provisioning Operations

Idempotent operations and saga orchestration for tenant provisioning
with proper compensation and rollback handling.
"""

import asyncio
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from ...standard_exception_handler import standard_exception_handler
from ..exceptions import ErrorContext, ProvisioningError
from ..idempotency import IdempotentOperation
from ..sagas import CompensationHandler, SagaContext, SagaDefinition, SagaStep


class CreateTenantStep(SagaStep):
    """Step to create tenant record in database"""

    def __init__(self):
        super().__init__(
            name="create_tenant",
            timeout_seconds=30,
            retry_count=3,
            compensation_required=True,
        )

    @standard_exception_handler
    async def execute(self, context: SagaContext) -> dict[str, Any]:
        """Create tenant record"""
        tenant_data = context.get_shared_data("tenant_request")

        # Simulate tenant creation logic
        tenant_id = str(uuid4())

        # In real implementation, this would create database records
        tenant_record = {
            "id": tenant_id,
            "name": tenant_data["name"],
            "domain": tenant_data["domain"],
            "plan": tenant_data["plan"],
            "status": "creating",
            "created_at": datetime.utcnow().isoformat(),
        }

        # Store tenant info for other steps
        context.set_shared_data("tenant_id", tenant_id)
        context.set_shared_data("tenant_record", tenant_record)

        await asyncio.sleep(0.1)  # Simulate database operation

        return {
            "tenant_id": tenant_id,
            "status": "created",
            "domain": tenant_data["domain"],
        }

    @standard_exception_handler
    async def compensate(self, context: SagaContext) -> None:
        """Rollback tenant creation"""
        tenant_id = context.get_shared_data("tenant_id")

        if tenant_id:
            # In real implementation, delete tenant record
            await asyncio.sleep(0.1)  # Simulate deletion

            context.set_shared_data("tenant_deleted", True)


class ConfigureDatabaseStep(SagaStep):
    """Step to configure tenant database and schema"""

    def __init__(self):
        super().__init__(
            name="configure_database",
            timeout_seconds=60,
            retry_count=2,
            compensation_required=True,
        )

    @standard_exception_handler
    async def execute(self, context: SagaContext) -> dict[str, Any]:
        """Configure tenant database"""
        tenant_id = context.get_shared_data("tenant_id")
        context.get_shared_data("tenant_request")

        if not tenant_id:
            raise ProvisioningError(
                message="Tenant ID not found in context",
                provisioning_type="tenant",
                target_id="unknown",
                step_failed="configure_database",
            )

        # Simulate database configuration
        database_config = {
            "tenant_id": tenant_id,
            "database_name": f"tenant_{tenant_id.replace('-', '_')}",
            "schema_version": "1.0.0",
            "tables_created": ["users", "customers", "services", "billing"],
            "configured_at": datetime.utcnow().isoformat(),
        }

        context.set_shared_data("database_config", database_config)

        await asyncio.sleep(0.2)  # Simulate database setup

        return database_config

    @standard_exception_handler
    async def compensate(self, context: SagaContext) -> None:
        """Rollback database configuration"""
        database_config = context.get_shared_data("database_config")

        if database_config:
            # In real implementation, drop database/schema
            await asyncio.sleep(0.1)  # Simulate cleanup

            context.set_shared_data("database_cleaned", True)


class SetupDefaultsStep(SagaStep):
    """Step to setup default configurations and data"""

    def __init__(self):
        super().__init__(
            name="setup_defaults",
            timeout_seconds=45,
            retry_count=3,
            compensation_required=True,
        )

    @standard_exception_handler
    async def execute(self, context: SagaContext) -> dict[str, Any]:
        """Setup default configurations"""
        tenant_id = context.get_shared_data("tenant_id")
        tenant_data = context.get_shared_data("tenant_request")

        # Setup default configurations based on plan
        plan = tenant_data.get("plan", "basic")

        defaults_config = {
            "tenant_id": tenant_id,
            "plan": plan,
            "default_settings": {
                "user_limit": 100 if plan == "basic" else 1000,
                "storage_gb": 50 if plan == "basic" else 500,
                "bandwidth_mbps": 100 if plan == "basic" else 1000,
                "features_enabled": ["dashboard", "user_management", "basic_reports"]
                + (["advanced_analytics", "api_access"] if plan != "basic" else []),
            },
            "admin_user": {
                "username": tenant_data.get("admin_email", "admin@tenant.com"),
                "role": "tenant_admin",
                "created_at": datetime.utcnow().isoformat(),
            },
            "configured_at": datetime.utcnow().isoformat(),
        }

        context.set_shared_data("defaults_config", defaults_config)

        await asyncio.sleep(0.15)  # Simulate configuration setup

        return defaults_config

    @standard_exception_handler
    async def compensate(self, context: SagaContext) -> None:
        """Rollback default configurations"""
        defaults_config = context.get_shared_data("defaults_config")

        if defaults_config:
            # In real implementation, remove default configurations
            await asyncio.sleep(0.1)  # Simulate cleanup

            context.set_shared_data("defaults_cleaned", True)


class ActivateTenantStep(SagaStep):
    """Step to activate tenant and make it available"""

    def __init__(self):
        super().__init__(
            name="activate_tenant",
            timeout_seconds=30,
            retry_count=3,
            compensation_required=False,  # Final step, no compensation needed
        )

    @standard_exception_handler
    async def execute(self, context: SagaContext) -> dict[str, Any]:
        """Activate tenant"""
        tenant_id = context.get_shared_data("tenant_id")
        tenant_record = context.get_shared_data("tenant_record")

        # Update tenant status to active
        if tenant_record:
            tenant_record["status"] = "active"
            tenant_record["activated_at"] = datetime.utcnow().isoformat()

        activation_result = {
            "tenant_id": tenant_id,
            "status": "active",
            "domain": tenant_record.get("domain") if tenant_record else None,
            "activated_at": datetime.utcnow().isoformat(),
            "access_url": f"https://{tenant_record.get('domain')}.platform.com"
            if tenant_record
            else None,
        }

        context.set_shared_data("activation_result", activation_result)

        await asyncio.sleep(0.1)  # Simulate activation

        return activation_result

    @standard_exception_handler
    async def compensate(self, context: SagaContext) -> None:
        """No compensation needed for activation step"""
        pass


class TenantProvisioningCompensationHandler(CompensationHandler):
    """Custom compensation handler for tenant provisioning"""

    @standard_exception_handler
    async def compensate(
        self, context: SagaContext, failed_step: str, completed_steps: list
    ) -> None:
        """Execute custom compensation logic"""

        tenant_id = context.get_shared_data("tenant_id")

        # Log compensation details
        compensation_log = {
            "tenant_id": tenant_id,
            "failed_step": failed_step,
            "completed_steps": completed_steps,
            "compensation_started_at": datetime.utcnow().isoformat(),
        }

        context.set_shared_data("compensation_log", compensation_log)

        # Perform additional cleanup if needed
        if tenant_id:
            # Send notifications, update external systems, etc.
            await asyncio.sleep(0.1)  # Simulate cleanup operations

            context.set_shared_data("custom_compensation_completed", True)


class TenantProvisioningOperation(IdempotentOperation[dict[str, Any]]):
    """Idempotent tenant provisioning operation"""

    def __init__(self):
        super().__init__(
            operation_type="tenant_provisioning",
            max_attempts=2,  # Sagas handle their own retries
            timeout_seconds=300,
            ttl_seconds=3600,
        )

    def validate_operation_data(self, operation_data: dict[str, Any]) -> None:
        """Validate tenant provisioning request data"""
        required_fields = ["name", "domain", "plan", "admin_email"]

        for field in required_fields:
            if field not in operation_data:
                raise ValueError(f"Missing required field: {field}")

        # Validate plan
        valid_plans = ["basic", "pro", "enterprise"]
        if operation_data["plan"] not in valid_plans:
            raise ValueError(
                f"Invalid plan: {operation_data['plan']}. Must be one of {valid_plans}"
            )

        # Validate domain format
        domain = operation_data["domain"]
        if not isinstance(domain, str) or len(domain) < 3 or len(domain) > 63:
            raise ValueError("Domain must be 3-63 characters long")

        # Basic email validation
        admin_email = operation_data["admin_email"]
        if not isinstance(admin_email, str) or "@" not in admin_email:
            raise ValueError("Valid admin email is required")

    @standard_exception_handler
    async def execute(
        self, operation_data: dict[str, Any], context: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Execute tenant provisioning via saga orchestration"""

        context = context or {}

        # Import here to avoid circular imports
        from ..sagas import SagaContext

        # Create saga context
        saga_context = SagaContext(
            saga_id=str(uuid4()),
            tenant_id=context.get("tenant_id", "system"),
            user_id=context.get("user_id"),
            correlation_id=context.get("correlation_id", str(uuid4())),
        )

        # Store operation data in saga context
        saga_context.set_shared_data("tenant_request", operation_data)
        saga_context.set_shared_data("operation_context", context)

        # Create and execute saga
        TenantProvisioningSaga.create_definition()

        # For this example, we'll simulate saga execution
        # In real implementation, you'd use SagaCoordinator
        try:
            # Execute steps sequentially (simplified)
            steps = [
                CreateTenantStep(),
                ConfigureDatabaseStep(),
                SetupDefaultsStep(),
                ActivateTenantStep(),
            ]

            step_results = {}

            for step in steps:
                result = await step.execute(saga_context)
                step_results[step.name] = result

            # Return consolidated result
            tenant_id = saga_context.get_shared_data("tenant_id")
            activation_result = saga_context.get_shared_data("activation_result")

            return {
                "tenant_id": tenant_id,
                "status": "provisioned",
                "provisioning_completed_at": datetime.utcnow().isoformat(),
                "step_results": step_results,
                "access_details": activation_result,
                "saga_context": {
                    "saga_id": saga_context.saga_id,
                    "correlation_id": saga_context.correlation_id,
                },
            }

        except Exception as e:
            # Handle compensation in real implementation
            error_context = ErrorContext(
                operation="tenant_provisioning",
                resource_type="tenant",
                resource_id=operation_data.get("domain", "unknown"),
                tenant_id=context.get("tenant_id", "system"),
                user_id=context.get("user_id"),
                correlation_id=saga_context.correlation_id,
            )

            raise ProvisioningError(
                message=f"Tenant provisioning failed: {str(e)}",
                provisioning_type="tenant",
                target_id=operation_data.get("domain", "unknown"),
                step_failed="unknown",
                rollback_required=True,
                context=error_context,
                saga_id=saga_context.saga_id,
            ) from e


class TenantProvisioningSaga:
    """Saga definition for tenant provisioning"""

    @staticmethod
    def create_definition() -> SagaDefinition:
        """Create tenant provisioning saga definition"""

        definition = SagaDefinition(
            name="tenant_provisioning",
            description="Complete tenant provisioning with database setup and configuration",
            timeout_seconds=300,
            compensation_handler=TenantProvisioningCompensationHandler(),
        )

        # Add steps in order
        definition.add_steps(
            [
                CreateTenantStep(),
                ConfigureDatabaseStep(),
                SetupDefaultsStep(),
                ActivateTenantStep(),
            ]
        )

        return definition
