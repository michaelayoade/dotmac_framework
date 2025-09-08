"""
Provision Tenant Use Case
Orchestrates the complete tenant provisioning workflow
"""

import json
import os
import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from dotmac.database.base import get_db_session
from dotmac_shared.core.logging import get_logger
from dotmac_shared.exceptions import ExceptionContext
from dotmac_shared.security.secrets import SecretsManager

from ...infrastructure import get_adapter_factory
from ...infrastructure.interfaces.deployment_provider import (
    ApplicationConfig,
    ServiceConfig,
)
from ...models.tenant import CustomerTenant, TenantStatus
from ...services.tenant_provisioning import TenantProvisioningService
from ..base import TransactionalUseCase, UseCaseContext, UseCaseResult
from dotmac_shared.business_logic.idempotency import (
    IdempotencyKey,
    IdempotencyManager,
    IdempotentOperation,
    OperationResult,
    OperationStatus,
)

logger = get_logger(__name__)


@dataclass
class ProvisionTenantInput:
    """Input data for tenant provisioning use case"""

    tenant_id: str
    company_name: str
    admin_email: str
    admin_name: str
    subdomain: str
    plan: str
    region: str
    billing_info: dict[str, Any]
    notification_preferences: dict[str, Any] = None
    custom_configuration: dict[str, Any] = None

    def __post_init__(self):
        if self.notification_preferences is None:
            self.notification_preferences = {}
        if self.custom_configuration is None:
            self.custom_configuration = {}


@dataclass
class ProvisionTenantOutput:
    """Output data for tenant provisioning use case"""

    tenant_db_id: int
    tenant_id: str
    status: TenantStatus
    domain: str
    admin_portal_url: str
    customer_portal_url: str
    admin_credentials: dict[str, str]
    provisioning_summary: dict[str, Any]
    estimated_ready_time: Optional[str] = None


class ProvisionTenantUseCase(TransactionalUseCase[ProvisionTenantInput, ProvisionTenantOutput]):
    """
    Provision a new tenant with complete infrastructure setup.

    This use case orchestrates:
    1. Tenant record creation and validation
    2. Subdomain availability checking
    3. Infrastructure provisioning (database, cache, containers)
    4. Initial data seeding
    5. Admin account creation
    6. License provisioning
    7. Health checks and activation
    8. Notification and welcome flow

    This is a transactional use case that supports rollback
    if any step in the provisioning process fails.
    """

    def __init__(self):
        super().__init__()
        self.secrets_manager = SecretsManager()
        self.provisioning_service = TenantProvisioningService()
        self.adapter_factory = None

    async def _ensure_dependencies(self):
        """Ensure all dependencies are initialized"""
        if self.adapter_factory is None:
            self.adapter_factory = await get_adapter_factory()

    async def validate_input(self, input_data: ProvisionTenantInput) -> bool:
        """Validate tenant provisioning input"""
        if not input_data.tenant_id or not input_data.tenant_id.strip():
            return False

        if not input_data.company_name or not input_data.company_name.strip():
            return False

        if not input_data.admin_email or "@" not in input_data.admin_email:
            return False

        if not input_data.subdomain or not input_data.subdomain.strip():
            return False

        if not input_data.plan or input_data.plan not in [
            "starter",
            "professional",
            "enterprise",
        ]:
            return False

        return True

    async def can_execute(self, context: Optional[UseCaseContext] = None) -> bool:
        """Check if tenant provisioning can be executed"""

        # Check if user has tenant provisioning permissions
        if context and context.permissions:
            required_permissions = ["tenant.create", "infrastructure.provision"]
            user_permissions = context.permissions.get("actions", [])

            if not all(perm in user_permissions for perm in required_permissions):
                return False

        # Check system capacity and limits
        try:
            await self._ensure_dependencies()

            # Check infrastructure health
            health_result = await self.adapter_factory.health_check_all()
            if not health_result.get("overall_healthy", False):
                self.logger.warning("Infrastructure not healthy for tenant provisioning")
                return False

            return True

        except (
            ExceptionContext.LIFECYCLE_EXCEPTIONS,
            ExceptionContext.EXTERNAL_SERVICE_EXCEPTIONS,
        ) as e:
            self.logger.error(f"Cannot execute tenant provisioning: {e}")
            return False

    async def _execute_transaction(
        self, input_data: ProvisionTenantInput, context: Optional[UseCaseContext] = None
    ) -> UseCaseResult[ProvisionTenantOutput]:
        """Execute the tenant provisioning transaction"""

        try:
            await self._ensure_dependencies()
            correlation_id = context.correlation_id if context else f"provision-{secrets.token_hex(8)}"

            # Phase 3: Saga Coordinator integration - Use coordinated workflows when enabled
            if os.getenv("BUSINESS_LOGIC_WORKFLOWS_ENABLED", "false").lower() == "true":
                return await self._execute_with_saga_coordinator(input_data, context, correlation_id)

            # Full Idempotency integration: wrap provisioning in an idempotent operation
            if os.getenv("BUSINESS_LOGIC_IDEMPOTENCY_FULL", "false").lower() == "true":
                from dataclasses import asdict

                op_key = IdempotencyKey.generate(
                    operation_type="tenant_provisioning",
                    tenant_id=input_data.tenant_id,
                    operation_data={
                        "company_name": input_data.company_name,
                        "subdomain": input_data.subdomain,
                        "admin_email": input_data.admin_email,
                        "plan": input_data.plan,
                        "region": input_data.region,
                    },
                )

                op_context = {
                    "correlation_id": correlation_id,
                    "initiator": (context.user_id if context else None),
                    "use_case": "ProvisionTenantUseCase",
                }

                from dotmac.database.base import get_db_session

                def _db_session_factory():
                    return get_db_session()

                manager = IdempotencyManager(db_session_factory=_db_session_factory)

                outer_self = self

                class ProvisionTenantOperation(IdempotentOperation[dict[str, Any]]):
                    def __init__(self):
                        super().__init__(operation_type="tenant_provisioning", max_attempts=1, ttl_seconds=3600)

                    def validate_operation_data(self, data: dict[str, Any]) -> None:
                        required = ["company_name", "subdomain", "admin_email", "plan", "region"]
                        missing = [k for k in required if not data.get(k)]
                        if missing:
                            raise ValueError(f"Missing required fields: {', '.join(missing)}")

                    async def execute(self, data: dict[str, Any], _ctx: Optional[dict[str, Any]] = None) -> dict[str, Any]:
                        # Delegate to the core provisioning logic of the use case
                        output: ProvisionTenantOutput = await outer_self._provision_core(input_data, correlation_id)
                        return asdict(output)

                manager.register_operation("tenant_provisioning", ProvisionTenantOperation)

                try:
                    op_result: OperationResult = await manager.execute_idempotent(
                        op_key, op_key.model_dump(), op_context  # type: ignore[attr-defined]
                    )
                    if op_result.success and op_result.data:
                        # Reconstruct output and return success
                        output = ProvisionTenantOutput(**op_result.data)
                        return self._create_success_result(
                            output,
                            metadata={
                                "correlation_id": correlation_id,
                                "provisioning_started": True,
                                "idempotent": True,
                                "from_cache": op_result.from_cache,
                            },
                        )
                    # In-progress or other statuses
                    if op_result.status == OperationStatus.IN_PROGRESS:
                        return self._create_error_result(
                            "Provisioning request already in progress",
                            error_code="PROVISIONING_IN_PROGRESS",
                        )
                except Exception:
                    # Fall back to non-idempotent execution if manager fails
                    self.logger.exception("Full idempotent provisioning failed; falling back to direct execution")

            # Optional Idempotency integration (record + dedupe)
            if os.getenv("BUSINESS_LOGIC_IDEMPOTENCY", "false").lower() == "true":
                # Build deterministic key based on core input fields
                op_key = IdempotencyKey.generate(
                    operation_type="tenant_provisioning",
                    tenant_id=input_data.tenant_id,
                    operation_data={
                        "company_name": input_data.company_name,
                        "subdomain": input_data.subdomain,
                        "admin_email": input_data.admin_email,
                        "plan": input_data.plan,
                        "region": input_data.region,
                    },
                )

                # Context to attach to operation metadata
                op_context = {
                    "correlation_id": correlation_id,
                    "initiator": (context.current_user if context else None),
                    "use_case": "ProvisionTenantUseCase",
                }

                # Session factory compatible with IdempotencyManager
                from dotmac.database.base import get_db_session

                def _db_session_factory():
                    return get_db_session()

                manager = IdempotencyManager(db_session_factory=_db_session_factory)

                # Lightweight operation for recording + validation (does not perform provisioning)
                class _RecordProvisionRequest(IdempotentOperation[dict[str, Any]]):
                    def __init__(self):
                        super().__init__(operation_type="tenant_provisioning", max_attempts=1, ttl_seconds=3600)

                    def validate_operation_data(self, data: dict[str, Any]) -> None:
                        required = ["company_name", "subdomain", "admin_email", "plan", "region"]
                        missing = [k for k in required if not data.get(k)]
                        if missing:
                            raise ValueError(f"Missing required fields: {', '.join(missing)}")

                    async def execute(self, data: dict[str, Any], _ctx: Optional[dict[str, Any]] = None) -> dict[str, Any]:
                        # No side effects; this records the request via IdempotencyManager
                        return {"accepted": True, "data_fingerprint": list(sorted(data.keys()))}

                manager.register_operation("tenant_provisioning", _RecordProvisionRequest)

                try:
                    op_result: OperationResult = await manager.execute_idempotent(op_key, op_key.model_dump(), op_context)  # type: ignore[attr-defined]
                    # If already completed recently, short-circuit to avoid duplicate start
                    if op_result.from_cache and op_result.status in (OperationStatus.COMPLETED, OperationStatus.IN_PROGRESS):
                        return self._create_error_result(
                            "Provisioning already requested for this tenant",
                            error_code="DUPLICATE_PROVISION_REQUEST",
                        )
                except Exception:
                    # Do not fail provisioning if idempotency logging fails
                    self.logger.exception("Idempotency manager execution failed; continuing without dedupe")

            self.logger.info(
                "Starting tenant provisioning",
                extra={
                    "tenant_id": input_data.tenant_id,
                    "correlation_id": correlation_id,
                },
            )

            # Direct execution path
            output_data = await self._provision_core(input_data, correlation_id)
            return self._create_success_result(
                output_data,
                metadata={
                    "correlation_id": correlation_id,
                    "provisioning_started": True,
                    "estimated_completion_minutes": 15,
                },
            )

        except (
            ExceptionContext.LIFECYCLE_EXCEPTIONS,
            ExceptionContext.EXTERNAL_SERVICE_EXCEPTIONS,
        ) as e:
            self.logger.error(f"Tenant provisioning transaction failed: {e}")
            return self._create_error_result(str(e), error_code="TRANSACTION_FAILED")

    async def _create_tenant_record(self, input_data: ProvisionTenantInput, correlation_id: str) -> int:
        """Create the tenant database record"""

        with get_db_session() as db:
            tenant = CustomerTenant(
                tenant_id=input_data.tenant_id,
                company_name=input_data.company_name,
                admin_email=input_data.admin_email,
                admin_name=input_data.admin_name,
                subdomain=input_data.subdomain,
                plan=input_data.plan,
                region=input_data.region,
                status=TenantStatus.CREATING,
                settings={
                    "billing_info": input_data.billing_info,
                    "notification_preferences": input_data.notification_preferences,
                    "custom_configuration": input_data.custom_configuration,
                    "correlation_id": correlation_id,
                    "created_via": "use_case_orchestration",
                },
            )

            db.add(tenant)
            db.commit()
            db.refresh(tenant)

            self.logger.info(
                "Created tenant record",
                extra={"tenant_id": input_data.tenant_id, "tenant_db_id": tenant.id},
            )

            return tenant.id

    async def _start_provisioning_workflow(self, tenant_db_id: int, correlation_id: str) -> dict[str, Any]:
        """Start the comprehensive provisioning workflow using orchestrated business logic"""

        try:
            with get_db_session() as db:
                tenant = db.query(CustomerTenant).filter_by(id=tenant_db_id).first()
                if not tenant:
                    return {
                        "success": False,
                        "workflow_id": correlation_id,
                        "error": "Tenant not found",
                    }

                # Step 1: Validate tenant configuration
                validation_result = await self.provisioning_service.validate_tenant_configuration(
                    tenant, correlation_id
                )
                if not validation_result.get("success", True):
                    return {
                        "success": False,
                        "workflow_id": correlation_id,
                        "error": f"Configuration validation failed: {validation_result.get('error')}",
                    }

                # Step 2: Generate tenant secrets
                tenant_secrets = await self.provisioning_service.generate_tenant_secrets(tenant, correlation_id)

                # Store encrypted secrets
                tenant.environment_vars = await self.secrets_manager.encrypt(json.dumps(tenant_secrets))

                # Step 3: Create database and Redis resources using infrastructure
                await self._create_infrastructure_resources(tenant, correlation_id)

                # Step 4: Deploy container stack
                deployment_adapter = await self.adapter_factory.get_deployment_adapter()
                compose_content = await self.provisioning_service.generate_docker_compose(tenant)

                # Create application config
                app_config = ApplicationConfig(
                    name=f"tenant-{tenant.subdomain}",
                    description=f"DotMac ISP tenant for {tenant.company_name}",
                    docker_compose=compose_content,
                    domains=[f"{tenant.subdomain}.{os.getenv('BASE_DOMAIN', 'example.com')}"],
                    environment=tenant_secrets,
                )

                deployment_result = await deployment_adapter.deploy_application(app_config)

                if not deployment_result.success:
                    return {
                        "success": False,
                        "workflow_id": correlation_id,
                        "error": f"Deployment failed: {deployment_result.error}",
                    }

                # Store deployment info
                tenant.container_id = deployment_result.deployment_id
                tenant.domain = f"{tenant.subdomain}.{os.getenv('BASE_DOMAIN', 'example.com')}"

                # Step 5: Wait for deployment to be ready and run health checks
                await self._wait_for_deployment_ready(deployment_result.deployment_id)

                health_check_passed = await self.provisioning_service.perform_health_checks(tenant, correlation_id)

                if not health_check_passed:
                    return {
                        "success": False,
                        "workflow_id": correlation_id,
                        "error": "Health checks failed",
                    }

                # Step 6: Create admin user and provision license
                admin_info = await self.provisioning_service.create_tenant_admin_user(tenant, correlation_id)

                license_info = await self.provisioning_service.provision_tenant_license(tenant, correlation_id)

                # Step 7: Update final status
                tenant.status = TenantStatus.ACTIVE
                tenant.provisioning_completed_at = datetime.utcnow()

                db.commit()

                return {
                    "success": True,
                    "workflow_id": correlation_id,
                    "admin_info": admin_info,
                    "license_info": license_info,
                    "deployment_id": deployment_result.deployment_id,
                }

        except (
            SQLAlchemyError,
            ExceptionContext.EXTERNAL_SERVICE_EXCEPTIONS,
            ExceptionContext.LIFECYCLE_EXCEPTIONS,
        ) as e:
            self.logger.error(f"Provisioning workflow failed: {e}")
            return {"success": False, "workflow_id": correlation_id, "error": str(e)}

    async def _create_output_data(
        self,
        tenant_db_id: int,
        input_data: ProvisionTenantInput,
        provisioning_result: dict[str, Any],
        correlation_id: str,
    ) -> ProvisionTenantOutput:
        """Create the use case output data"""

        base_domain = "dotmac.com"  # Would come from config
        domain = f"{input_data.subdomain}.{base_domain}"

        return ProvisionTenantOutput(
            tenant_db_id=tenant_db_id,
            tenant_id=input_data.tenant_id,
            status=TenantStatus.PROVISIONING,
            domain=domain,
            admin_portal_url=f"https://{domain}/admin",
            customer_portal_url=f"https://{domain}",
            admin_credentials={
                "username": input_data.admin_email,
                "password": "temporary_password",  # Would be securely generated
                "must_change_password": True,
            },
            provisioning_summary={
                "correlation_id": correlation_id,
                "workflow_id": provisioning_result.get("workflow_id"),
                "started_at": datetime.utcnow().isoformat(),
                "steps_total": 10,
                "steps_completed": 1,
                "current_step": "infrastructure_provisioning",
            },
            estimated_ready_time=datetime.utcnow().isoformat(),
        )

    async def _rollback_tenant_record(self, tenant_db_id: int):
        """Rollback tenant record creation"""
        try:
            with get_db_session() as db:
                tenant = db.query(CustomerTenant).filter_by(id=tenant_db_id).first()
                if tenant:
                    tenant.status = TenantStatus.FAILED
                    tenant.settings = tenant.settings or {}
                    tenant.settings["rollback_performed"] = True
                    tenant.settings["rollback_at"] = datetime.utcnow().isoformat()
                    db.commit()

                    self.logger.info(
                        "Rolled back tenant record",
                        extra={"tenant_db_id": tenant_db_id},
                    )

        except (SQLAlchemyError, ExceptionContext.LIFECYCLE_EXCEPTIONS) as e:
            self.logger.error(f"Failed to rollback tenant record: {e}")

    async def _create_infrastructure_resources(self, tenant: CustomerTenant, correlation_id: str):
        """Create database and cache resources using infrastructure layer"""

        # Create PostgreSQL database
        db_config = ServiceConfig(
            name=f"{tenant.subdomain}-postgres",
            service_type="postgresql",
            version="15",
            configuration={
                "database": f"tenant_{tenant.subdomain}",
                "username": f"tenant_{tenant.subdomain}",
                "password": secrets.token_urlsafe(24),
            },
        )

        deployment_adapter = await self.adapter_factory.get_deployment_adapter()
        db_result = await deployment_adapter.deploy_service(db_config)

        # Store database URL
        if db_result.success:
            tenant.database_url = await self.secrets_manager.encrypt(db_result.metadata.get("connection_url", ""))

        # Create Redis cache
        redis_config = ServiceConfig(
            name=f"{tenant.subdomain}-redis",
            service_type="redis",
            version="7",
            configuration={"password": secrets.token_urlsafe(24)},
        )

        redis_result = await deployment_adapter.deploy_service(redis_config)

        # Store Redis URL
        if redis_result.success:
            tenant.redis_url = await self.secrets_manager.encrypt(redis_result.metadata.get("connection_url", ""))

    async def _wait_for_deployment_ready(self, deployment_id: str):
        """Wait for deployment to be ready"""
        import asyncio
        import time

        max_wait_time = 600  # 10 minutes
        poll_interval = 15  # 15 seconds
        start_time = time.time()

        deployment_adapter = await self.adapter_factory.get_deployment_adapter()

        while time.time() - start_time < max_wait_time:
            status = await deployment_adapter.get_deployment_status(deployment_id)

            if status.get("status") == "running":
                self.logger.info(f"✅ Deployment ready: {deployment_id}")
                return True
            elif status.get("status") == "failed":
                raise Exception(f"Deployment failed: {deployment_id}")

            self.logger.info(f"⏳ Waiting for deployment: {deployment_id}")
            await asyncio.sleep(poll_interval)

        raise Exception(f"Deployment timeout: {deployment_id}")

    async def _provision_core(self, input_data: ProvisionTenantInput, correlation_id: str) -> ProvisionTenantOutput:
        """Core provisioning steps shared by idempotent and direct execution paths."""
        # Step 1: Validate subdomain availability
        dns_adapter = await self.adapter_factory.get_dns_adapter()
        subdomain_result = await dns_adapter.validate_subdomain_available(input_data.subdomain)
        if not subdomain_result.available:
            raise Exception(f"Subdomain {input_data.subdomain} is not available")

        # Step 2: Create tenant database record
        tenant_db_id = await self._create_tenant_record(input_data, correlation_id)
        self.add_rollback_action(lambda: self._rollback_tenant_record(tenant_db_id))

        # Step 3: Start background provisioning workflow
        provisioning_result = await self._start_provisioning_workflow(tenant_db_id, correlation_id)
        if not provisioning_result["success"]:
            raise Exception(f"Provisioning failed: {provisioning_result['error']}")

        # Step 4: Generate response data
        output_data = await self._create_output_data(tenant_db_id, input_data, provisioning_result, correlation_id)

        self.logger.info(
            "Tenant provisioning initiated successfully",
            extra={
                "tenant_id": input_data.tenant_id,
                "tenant_db_id": tenant_db_id,
                "correlation_id": correlation_id,
            },
        )

        return output_data

    async def _execute_with_saga_coordinator(
        self, input_data: ProvisionTenantInput, context: Optional[UseCaseContext], correlation_id: str
    ) -> UseCaseResult[ProvisionTenantOutput]:
        """Execute tenant provisioning using the Saga Coordinator from Phase 2"""
        try:
            # Import saga components
            from dotmac_shared.business_logic.sagas import SagaContext
            
            # Try to get the saga coordinator from the current application context
            # This would be injected from the service layer that calls this use case
            saga_coordinator = getattr(self, '_saga_coordinator', None)
            
            if not saga_coordinator:
                # Fallback to creating a local instance if not provided
                from dotmac_shared.business_logic.sagas import SagaCoordinator
                from dotmac.database.base import get_db_session
                
                def _db_session_factory():
                    return get_db_session()
                
                saga_coordinator = SagaCoordinator(db_session_factory=_db_session_factory)
                self.logger.warning("Using local SagaCoordinator instance - consider injecting from service layer")
            
            # Create saga context
            saga_context = SagaContext(
                saga_id="",  # Will be generated by coordinator
                tenant_id=input_data.tenant_id,
                user_id=context.user_id if context else None
            )
            
            # Prepare initial data for the saga
            initial_data = {
                "tenant_request": {
                    "tenant_id": input_data.tenant_id,
                    "company_name": input_data.company_name,
                    "admin_email": input_data.admin_email,
                    "admin_name": input_data.admin_name,
                    "subdomain": input_data.subdomain,
                    "plan": input_data.plan,
                    "region": input_data.region,
                    "billing_info": input_data.billing_info,
                    "notification_preferences": input_data.notification_preferences,
                    "custom_configuration": input_data.custom_configuration,
                },
                "correlation_id": correlation_id,
                "use_case_source": "ProvisionTenantUseCase"
            }
            
            # Execute the tenant provisioning saga
            saga_result = await saga_coordinator.execute_saga(
                "tenant_provisioning", 
                saga_context, 
                initial_data=initial_data
            )
            
            if not saga_result or not saga_result.get("success", False):
                error_msg = saga_result.get("error", "Saga execution failed") if saga_result else "Unknown saga error"
                return self._create_error_result(
                    error_msg, 
                    error_code="SAGA_EXECUTION_FAILED"
                )
            
            # Extract saga execution details
            saga_id = saga_result.get("saga_id")
            saga_status = saga_result.get("status", "unknown")
            
            # Create output data based on saga result
            # Note: For async sagas, this might be in a "running" state initially
            output_data = ProvisionTenantOutput(
                tenant_db_id=0,  # Will be populated when saga completes
                tenant_id=input_data.tenant_id,
                status=TenantStatus.PROVISIONING,
                domain=f"{input_data.subdomain}.{os.getenv('BASE_DOMAIN', 'dotmac.com')}",
                admin_portal_url=f"https://{input_data.subdomain}.{os.getenv('BASE_DOMAIN', 'dotmac.com')}/admin",
                customer_portal_url=f"https://{input_data.subdomain}.{os.getenv('BASE_DOMAIN', 'dotmac.com')}",
                admin_credentials={
                    "username": input_data.admin_email,
                    "password": "will_be_generated",
                    "must_change_password": True,
                },
                provisioning_summary={
                    "correlation_id": correlation_id,
                    "saga_id": saga_id,
                    "saga_status": saga_status,
                    "started_at": datetime.utcnow().isoformat(),
                    "orchestration_type": "saga_coordinator",
                    "current_step": "initializing",
                },
                estimated_ready_time=(datetime.utcnow() + timedelta(minutes=20)).isoformat(),
            )
            
            return self._create_success_result(
                output_data,
                metadata={
                    "correlation_id": correlation_id,
                    "saga_id": saga_id,
                    "orchestration_method": "saga_coordinator",
                    "provisioning_started": True,
                    "estimated_completion_minutes": 20,
                }
            )
            
        except Exception as e:
            self.logger.error(f"Saga coordinator execution failed: {e}")
            return self._create_error_result(
                f"Failed to execute saga: {str(e)}", 
                error_code="SAGA_COORDINATOR_ERROR"
            )
    
    def inject_saga_coordinator(self, saga_coordinator):
        """Inject saga coordinator for workflow orchestration (Phase 3)"""
        self._saga_coordinator = saga_coordinator
