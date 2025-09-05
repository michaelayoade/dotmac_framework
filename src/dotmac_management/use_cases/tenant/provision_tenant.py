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


class ProvisionTenantUseCase(
    TransactionalUseCase[ProvisionTenantInput, ProvisionTenantOutput]
):
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
                self.logger.warning(
                    "Infrastructure not healthy for tenant provisioning"
                )
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
            correlation_id = (
                context.correlation_id
                if context
                else f"provision-{secrets.token_hex(8)}"
            )

            self.logger.info(
                "Starting tenant provisioning",
                extra={
                    "tenant_id": input_data.tenant_id,
                    "correlation_id": correlation_id,
                },
            )

            # Step 1: Validate subdomain availability
            dns_adapter = await self.adapter_factory.get_dns_adapter()
            subdomain_result = await dns_adapter.validate_subdomain_available(
                input_data.subdomain
            )

            if not subdomain_result.available:
                return self._create_error_result(
                    f"Subdomain {input_data.subdomain} is not available",
                    error_code="SUBDOMAIN_UNAVAILABLE",
                )

            # Step 2: Create tenant database record
            tenant_db_id = await self._create_tenant_record(input_data, correlation_id)
            self.add_rollback_action(lambda: self._rollback_tenant_record(tenant_db_id))

            # Step 3: Start background provisioning workflow
            provisioning_result = await self._start_provisioning_workflow(
                tenant_db_id, correlation_id
            )

            if not provisioning_result["success"]:
                return self._create_error_result(
                    provisioning_result["error"], error_code="PROVISIONING_FAILED"
                )

            # Step 4: Generate response data
            output_data = await self._create_output_data(
                tenant_db_id, input_data, provisioning_result, correlation_id
            )

            self.logger.info(
                "Tenant provisioning initiated successfully",
                extra={
                    "tenant_id": input_data.tenant_id,
                    "tenant_db_id": tenant_db_id,
                    "correlation_id": correlation_id,
                },
            )

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

    async def _create_tenant_record(
        self, input_data: ProvisionTenantInput, correlation_id: str
    ) -> int:
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

    async def _start_provisioning_workflow(
        self, tenant_db_id: int, correlation_id: str
    ) -> dict[str, Any]:
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
                validation_result = (
                    await self.provisioning_service.validate_tenant_configuration(
                        tenant, correlation_id
                    )
                )
                if not validation_result.get("success", True):
                    return {
                        "success": False,
                        "workflow_id": correlation_id,
                        "error": f"Configuration validation failed: {validation_result.get('error')}",
                    }

                # Step 2: Generate tenant secrets
                tenant_secrets = (
                    await self.provisioning_service.generate_tenant_secrets(
                        tenant, correlation_id
                    )
                )

                # Store encrypted secrets
                tenant.environment_vars = await self.secrets_manager.encrypt(
                    json.dumps(tenant_secrets)
                )

                # Step 3: Create database and Redis resources using infrastructure
                await self._create_infrastructure_resources(tenant, correlation_id)

                # Step 4: Deploy container stack
                deployment_adapter = await self.adapter_factory.get_deployment_adapter()
                compose_content = (
                    await self.provisioning_service.generate_docker_compose(tenant)
                )

                # Create application config
                app_config = ApplicationConfig(
                    name=f"tenant-{tenant.subdomain}",
                    description=f"DotMac ISP tenant for {tenant.company_name}",
                    docker_compose=compose_content,
                    domains=[
                        f"{tenant.subdomain}.{os.getenv('BASE_DOMAIN', 'example.com')}"
                    ],
                    environment=tenant_secrets,
                )

                deployment_result = await deployment_adapter.deploy_application(
                    app_config
                )

                if not deployment_result.success:
                    return {
                        "success": False,
                        "workflow_id": correlation_id,
                        "error": f"Deployment failed: {deployment_result.error}",
                    }

                # Store deployment info
                tenant.container_id = deployment_result.deployment_id
                tenant.domain = (
                    f"{tenant.subdomain}.{os.getenv('BASE_DOMAIN', 'example.com')}"
                )

                # Step 5: Wait for deployment to be ready and run health checks
                await self._wait_for_deployment_ready(deployment_result.deployment_id)

                health_check_passed = (
                    await self.provisioning_service.perform_health_checks(
                        tenant, correlation_id
                    )
                )

                if not health_check_passed:
                    return {
                        "success": False,
                        "workflow_id": correlation_id,
                        "error": "Health checks failed",
                    }

                # Step 6: Create admin user and provision license
                admin_info = await self.provisioning_service.create_tenant_admin_user(
                    tenant, correlation_id
                )

                license_info = await self.provisioning_service.provision_tenant_license(
                    tenant, correlation_id
                )

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

    async def _create_infrastructure_resources(
        self, tenant: CustomerTenant, correlation_id: str
    ):
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
            tenant.database_url = await self.secrets_manager.encrypt(
                db_result.metadata.get("connection_url", "")
            )

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
            tenant.redis_url = await self.secrets_manager.encrypt(
                redis_result.metadata.get("connection_url", "")
            )

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
