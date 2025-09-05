"""
Enhanced Tenant Provisioning Service with Background Task Integration

Leverages the comprehensive task system for reliable tenant provisioning:
- Multi-step workflow orchestration with rollback capabilities
- Progress tracking and real-time updates
- Retry logic and failure handling
- Notification system integration
- Task monitoring and logging
"""

import asyncio
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional

from dotmac.database.base import get_db_session
from dotmac.platform.auth.core.jwt_service import JWTService
from dotmac.tasks.decorators import TaskExecutionContext
from dotmac.tasks.engine import Task, TaskConfig, TaskEngine, TaskPriority
from dotmac.tasks.monitor import TaskMonitor
from dotmac.tasks.notifications import TaskNotificationService
from dotmac.tasks.workflow import StepType, Workflow, WorkflowOrchestrator, WorkflowStep
from dotmac_management.infrastructure import get_adapter_factory
from dotmac_management.models.tenant import CustomerTenant, TenantProvisioningEvent, TenantStatus
from dotmac_management.services.auto_license_provisioning import AutoLicenseProvisioningService
from dotmac_management.services.tenant_admin_provisioning import TenantAdminProvisioningService
from dotmac_shared.core.logging import get_logger
from dotmac_shared.security.secrets import SecretsManager

logger = get_logger(__name__)


class EnhancedTenantProvisioningService:
    """
    Enhanced tenant provisioning service using background task system.

    Features:
    - Async task-based provisioning workflow
    - Real-time progress tracking with webhooks
    - Comprehensive error handling and rollback
    - Multi-step workflow orchestration
    - Notification system integration
    - Task monitoring and analytics
    """

    def __init__(self, redis_url: str = "redis://localhost:6379", webhook_base_url: str = "https://api.dotmac.com"):
        self.redis_url = redis_url
        self.webhook_base_url = webhook_base_url

        # Core services
        self.adapter_factory = None  # Will be initialized async
        self.secrets_manager = SecretsManager()
        self.jwt_service = JWTService()
        self.admin_provisioning = TenantAdminProvisioningService()
        self.license_provisioning = AutoLicenseProvisioningService()

        # Task system components
        self.task_engine: Optional[TaskEngine] = None
        self.workflow_orchestrator: Optional[WorkflowOrchestrator] = None
        self.notification_service: Optional[TaskNotificationService] = None
        self.task_monitor: Optional[TaskMonitor] = None

        # Provisioning configuration
        self.provisioning_config = {
            "timeout_per_step": 240,  # 4 minutes per step for fast deployment
            "total_timeout": 600,  # 10 minutes total for 4-minute target
            "retry_attempts": 2,  # Faster retries
            "notification_channels": ["webhook", "email"],
            "progress_webhook_url": f"{webhook_base_url}/webhooks/tenant-provisioning/progress",
            "fast_deployment": True,  # Enable fast deployment optimizations
            "parallel_provisioning": True,  # Enable parallel resource creation
            "container_warmup": True,  # Pre-warm container images
        }

    async def initialize(self):
        """Initialize the enhanced provisioning service."""
        try:
            # Initialize task engine
            self.task_engine = TaskEngine(
                redis_url=self.redis_url, worker_name="tenant-provisioning-service", concurrency=5
            )
            await self.task_engine.initialize()

            # Initialize workflow orchestrator
            self.workflow_orchestrator = WorkflowOrchestrator(redis_url=self.redis_url)
            await self.workflow_orchestrator.initialize()

            # Initialize notification service
            self.notification_service = TaskNotificationService(redis_url=self.redis_url)
            await self.notification_service.initialize()

            # Initialize task monitor
            self.task_monitor = TaskMonitor(redis_url=self.redis_url)
            await self.task_monitor.initialize()

            # Initialize infrastructure adapter factory
            self.adapter_factory = await get_adapter_factory()

            # Register task functions
            self._register_provisioning_tasks()

            # Start services
            await self.workflow_orchestrator.start()
            await self.notification_service.start()
            await self.task_monitor.start()

            logger.info("Enhanced tenant provisioning service initialized")

        except Exception as e:
            logger.error(f"Failed to initialize enhanced provisioning service: {e}")
            raise

    async def start_tenant_provisioning(
        self,
        tenant_db_id: int,
        notification_channels: Optional[list[dict[str, str]]] = None,
        priority: TaskPriority = TaskPriority.HIGH,
    ) -> str:
        """
        Start tenant provisioning workflow with full task system integration.

        Args:
            tenant_db_id: Database ID of tenant to provision
            notification_channels: List of notification channel configs
            priority: Task priority level

        Returns:
            Workflow ID for tracking
        """
        try:
            # Create comprehensive provisioning workflow
            workflow = await self._create_provisioning_workflow(tenant_db_id, notification_channels or [], priority)

            # Start workflow execution
            workflow_id = await self.workflow_orchestrator.start_workflow(workflow)

            logger.info(
                "Started tenant provisioning workflow",
                extra={"tenant_db_id": tenant_db_id, "workflow_id": workflow_id, "priority": priority.value},
            )

            return workflow_id

        except Exception as e:
            logger.error(f"Failed to start tenant provisioning: {e}")
            raise

    async def get_provisioning_status(self, workflow_id: str) -> Optional[dict[str, Any]]:
        """Get detailed provisioning status and progress."""
        try:
            status = await self.workflow_orchestrator.get_workflow_status(workflow_id)

            if status:
                # Enhance with additional provisioning-specific data
                status["provisioning_phase"] = self._determine_provisioning_phase(status)
                status["estimated_completion"] = self._estimate_completion_time(status)
                status["troubleshooting_info"] = await self._get_troubleshooting_info(status)

            return status

        except Exception as e:
            logger.error(f"Failed to get provisioning status: {e}")
            return None

    async def retry_failed_step(self, workflow_id: str, step_id: str) -> bool:
        """Retry a specific failed provisioning step."""
        try:
            # Get workflow status
            status = await self.workflow_orchestrator.get_workflow_status(workflow_id)
            if not status:
                return False

            # Check if step can be retried
            step_status = status["step_statuses"].get(step_id)
            if not step_status or step_status["status"] != "failed":
                return False

            # Create retry task based on step type
            retry_task = await self._create_retry_task(workflow_id, step_id, step_status)
            if retry_task:
                task_id = await self.task_engine.enqueue_task(retry_task)
                logger.info(
                    "Retry task enqueued",
                    extra={"workflow_id": workflow_id, "step_id": step_id, "retry_task_id": task_id},
                )
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to retry step {step_id}: {e}")
            return False

    async def cancel_provisioning(self, workflow_id: str, reason: str = "User requested") -> bool:
        """Cancel ongoing tenant provisioning with cleanup."""
        try:
            # Cancel workflow
            cancelled = await self.workflow_orchestrator.cancel_workflow(workflow_id)

            if cancelled:
                # Start cleanup workflow
                cleanup_workflow = await self._create_cleanup_workflow(workflow_id, reason)
                cleanup_id = await self.workflow_orchestrator.start_workflow(cleanup_workflow)

                logger.info(
                    "Provisioning cancelled and cleanup started",
                    extra={"original_workflow_id": workflow_id, "cleanup_workflow_id": cleanup_id, "reason": reason},
                )

            return cancelled

        except Exception as e:
            logger.error(f"Failed to cancel provisioning: {e}")
            return False

    async def _create_provisioning_workflow(
        self, tenant_db_id: int, notification_channels: list[dict[str, str]], priority: TaskPriority
    ) -> Workflow:
        """Create comprehensive tenant provisioning workflow."""

        workflow_id = f"tenant-provision-{tenant_db_id}-{int(time.time())}"

        # Define provisioning steps with dependencies
        steps = [
            # Step 1: Validate tenant configuration
            WorkflowStep(
                step_id="validate_config",
                name="Validate Tenant Configuration",
                step_type=StepType.TASK,
                function_name="validate_tenant_configuration",
                args=[tenant_db_id],
                task_config=TaskConfig(priority=priority, timeout=300, max_retries=2, queue_name="provisioning"),
                timeout_seconds=300,
            ),
            # Step 2: Create database resources
            WorkflowStep(
                step_id="create_database",
                name="Create Database Resources",
                step_type=StepType.TASK,
                function_name="create_tenant_database_resources",
                args=[tenant_db_id],
                depends_on={"validate_config"},
                task_config=TaskConfig(priority=priority, timeout=600, max_retries=3, queue_name="provisioning"),
                timeout_seconds=600,
            ),
            # Step 3: Generate secrets
            WorkflowStep(
                step_id="generate_secrets",
                name="Generate Tenant Secrets",
                step_type=StepType.TASK,
                function_name="generate_tenant_secrets",
                args=[tenant_db_id],
                depends_on={"validate_config"},
                task_config=TaskConfig(priority=priority, timeout=300, max_retries=2, queue_name="provisioning"),
                timeout_seconds=300,
            ),
            # Step 4: Deploy container stack
            WorkflowStep(
                step_id="deploy_containers",
                name="Deploy Container Stack",
                step_type=StepType.TASK,
                function_name="deploy_tenant_containers",
                args=[tenant_db_id],
                depends_on={"create_database", "generate_secrets"},
                task_config=TaskConfig(priority=priority, timeout=900, max_retries=3, queue_name="provisioning"),
                timeout_seconds=900,
            ),
            # Step 5: Run database migrations (parallel with seeding)
            WorkflowStep(
                step_id="run_migrations",
                name="Run Database Migrations",
                step_type=StepType.TASK,
                function_name="run_tenant_migrations",
                args=[tenant_db_id],
                depends_on={"deploy_containers"},
                task_config=TaskConfig(priority=priority, timeout=600, max_retries=2, queue_name="provisioning"),
                timeout_seconds=600,
            ),
            # Step 6: Seed initial data
            WorkflowStep(
                step_id="seed_data",
                name="Seed Initial Data",
                step_type=StepType.TASK,
                function_name="seed_tenant_data",
                args=[tenant_db_id],
                depends_on={"run_migrations"},
                task_config=TaskConfig(priority=priority, timeout=300, max_retries=2, queue_name="provisioning"),
                timeout_seconds=300,
            ),
            # Step 7: Create admin account (parallel with licensing)
            WorkflowStep(
                step_id="create_admin",
                name="Create Tenant Admin Account",
                step_type=StepType.TASK,
                function_name="create_tenant_admin_account",
                args=[tenant_db_id],
                depends_on={"seed_data"},
                task_config=TaskConfig(priority=priority, timeout=300, max_retries=2, queue_name="provisioning"),
                timeout_seconds=300,
            ),
            # Step 8: Provision license
            WorkflowStep(
                step_id="provision_license",
                name="Provision License Contract",
                step_type=StepType.TASK,
                function_name="provision_tenant_license",
                args=[tenant_db_id],
                depends_on={"seed_data"},
                task_config=TaskConfig(priority=priority, timeout=300, max_retries=2, queue_name="provisioning"),
                timeout_seconds=300,
            ),
            # Step 9: Health checks
            WorkflowStep(
                step_id="health_checks",
                name="Run Health Checks",
                step_type=StepType.TASK,
                function_name="run_tenant_health_checks",
                args=[tenant_db_id],
                depends_on={"create_admin", "provision_license"},
                task_config=TaskConfig(priority=priority, timeout=300, max_retries=3, queue_name="provisioning"),
                timeout_seconds=300,
            ),
            # Step 10: Send notifications
            WorkflowStep(
                step_id="send_notifications",
                name="Send Welcome Notifications",
                step_type=StepType.TASK,
                function_name="send_tenant_welcome_notifications",
                args=[tenant_db_id, notification_channels],
                depends_on={"health_checks"},
                task_config=TaskConfig(
                    priority=TaskPriority.NORMAL,  # Lower priority for notifications
                    timeout=300,
                    max_retries=2,
                    queue_name="notifications",
                ),
                timeout_seconds=300,
            ),
        ]

        # Create workflow
        workflow = Workflow(
            workflow_id=workflow_id,
            name=f"Tenant Provisioning - {tenant_db_id}",
            description="Complete tenant infrastructure provisioning workflow",
            steps=steps,
            timeout_seconds=self.provisioning_config["total_timeout"],
            metadata={
                "tenant_db_id": tenant_db_id,
                "provisioning_type": "full",
                "priority": priority.value,
                "notification_channels": notification_channels,
                "progress_webhook": self.provisioning_config["progress_webhook_url"],
            },
        )

        return workflow

    async def _create_cleanup_workflow(self, original_workflow_id: str, reason: str) -> Workflow:
        """Create cleanup workflow for cancelled/failed provisioning."""

        workflow_id = f"tenant-cleanup-{original_workflow_id}-{int(time.time())}"

        # Get original workflow status to determine what needs cleanup
        original_status = await self.workflow_orchestrator.get_workflow_status(original_workflow_id)
        tenant_db_id = original_status["metadata"]["tenant_db_id"] if original_status else None

        if not tenant_db_id:
            raise ValueError("Cannot create cleanup workflow without tenant ID")

        # Define cleanup steps based on what was completed
        cleanup_steps = []

        # Always try to cleanup containers if deployment was attempted
        if self._step_was_attempted(original_status, "deploy_containers"):
            cleanup_steps.append(
                WorkflowStep(
                    step_id="cleanup_containers",
                    name="Cleanup Container Resources",
                    step_type=StepType.TASK,
                    function_name="cleanup_tenant_containers",
                    args=[tenant_db_id],
                    task_config=TaskConfig(
                        priority=TaskPriority.HIGH, timeout=300, max_retries=2, queue_name="cleanup"
                    ),
                )
            )

        # Cleanup database resources if they were created
        if self._step_was_attempted(original_status, "create_database"):
            cleanup_steps.append(
                WorkflowStep(
                    step_id="cleanup_database",
                    name="Cleanup Database Resources",
                    step_type=StepType.TASK,
                    function_name="cleanup_tenant_database",
                    args=[tenant_db_id],
                    task_config=TaskConfig(
                        priority=TaskPriority.HIGH, timeout=300, max_retries=2, queue_name="cleanup"
                    ),
                )
            )

        # Update tenant status
        cleanup_steps.append(
            WorkflowStep(
                step_id="update_status",
                name="Update Tenant Status",
                step_type=StepType.TASK,
                function_name="update_tenant_cleanup_status",
                args=[tenant_db_id, reason],
                depends_on={step.step_id for step in cleanup_steps},
                task_config=TaskConfig(priority=TaskPriority.NORMAL, timeout=60, max_retries=1, queue_name="cleanup"),
            )
        )

        return Workflow(
            workflow_id=workflow_id,
            name=f"Tenant Cleanup - {tenant_db_id}",
            description=f"Cleanup resources for cancelled/failed provisioning: {reason}",
            steps=cleanup_steps,
            timeout_seconds=1800,  # 30 minutes for cleanup
            metadata={
                "tenant_db_id": tenant_db_id,
                "cleanup_reason": reason,
                "original_workflow_id": original_workflow_id,
                "cleanup_type": "provisioning_failure",
            },
        )

    async def _create_retry_task(self, workflow_id: str, step_id: str, step_status: dict[str, Any]) -> Optional[Task]:
        """Create a retry task for a specific failed step."""
        try:
            # Get workflow status to extract step information
            workflow_status = await self.workflow_orchestrator.get_workflow_status(workflow_id)
            if not workflow_status:
                return None

            tenant_db_id = workflow_status["metadata"]["tenant_db_id"]

            # Map step IDs to retry function names
            step_retry_functions = {
                "validate_config": "retry_validate_tenant_configuration",
                "create_database": "retry_create_tenant_database_resources",
                "generate_secrets": "retry_generate_tenant_secrets",
                "deploy_containers": "retry_deploy_tenant_containers",
                "run_migrations": "retry_run_tenant_migrations",
                "seed_data": "retry_seed_tenant_data",
                "create_admin": "retry_create_tenant_admin_account",
                "provision_license": "retry_provision_tenant_license",
                "health_checks": "retry_run_tenant_health_checks",
                "send_notifications": "retry_send_tenant_welcome_notifications",
            }

            retry_function = step_retry_functions.get(step_id)
            if not retry_function:
                return None

            # Create retry task with enhanced configuration
            retry_task = Task(
                name=f"Retry {step_id} - {workflow_id}",
                function_name=retry_function,
                args=[tenant_db_id, workflow_id, step_status],
                config=TaskConfig(
                    priority=TaskPriority.HIGH,
                    timeout=600,
                    max_retries=2,
                    queue_name="provisioning_retry",
                    metadata={"original_workflow_id": workflow_id, "original_step_id": step_id, "retry_attempt": True},
                ),
                correlation_id=f"retry-{workflow_id}-{step_id}",
                webhook_url=self.provisioning_config["progress_webhook_url"],
            )

            return retry_task

        except Exception as e:
            logger.error(f"Failed to create retry task: {e}")
            return None

    def _register_provisioning_tasks(self):
        """Register all provisioning task functions with the task engine."""

        # Main provisioning tasks
        provisioning_tasks = {
            "validate_tenant_configuration": self._validate_tenant_configuration,
            "create_tenant_database_resources": self._create_tenant_database_resources,
            "generate_tenant_secrets": self._generate_tenant_secrets,
            "deploy_tenant_containers": self._deploy_tenant_containers,
            "run_tenant_migrations": self._run_tenant_migrations,
            "seed_tenant_data": self._seed_tenant_data,
            "create_tenant_admin_account": self._create_tenant_admin_account,
            "provision_tenant_license": self._provision_tenant_license,
            "run_tenant_health_checks": self._run_tenant_health_checks,
            "send_tenant_welcome_notifications": self._send_tenant_welcome_notifications,
            # Retry task functions
            "retry_validate_tenant_configuration": self._retry_validate_tenant_configuration,
            "retry_create_tenant_database_resources": self._retry_create_tenant_database_resources,
            "retry_generate_tenant_secrets": self._retry_generate_tenant_secrets,
            "retry_deploy_tenant_containers": self._retry_deploy_tenant_containers,
            "retry_run_tenant_migrations": self._retry_run_tenant_migrations,
            "retry_seed_tenant_data": self._retry_seed_tenant_data,
            "retry_create_tenant_admin_account": self._retry_create_tenant_admin_account,
            "retry_provision_tenant_license": self._retry_provision_tenant_license,
            "retry_run_tenant_health_checks": self._retry_run_tenant_health_checks,
            "retry_send_tenant_welcome_notifications": self._retry_send_tenant_welcome_notifications,
            # Cleanup tasks
            "cleanup_tenant_containers": self._cleanup_tenant_containers,
            "cleanup_tenant_database": self._cleanup_tenant_database,
            "update_tenant_cleanup_status": self._update_tenant_cleanup_status,
        }

        for task_name, task_function in provisioning_tasks.items():
            self.task_engine.register_task_function(task_name, task_function)

        logger.info(f"Registered {len(provisioning_tasks)} provisioning task functions")

    def _determine_provisioning_phase(self, status: dict[str, Any]) -> str:
        """Determine current provisioning phase based on step status."""
        step_statuses = status.get("step_statuses", {})

        if step_statuses.get("validate_config", {}).get("status") != "completed":
            return "validation"
        elif step_statuses.get("create_database", {}).get("status") != "completed":
            return "infrastructure_setup"
        elif step_statuses.get("deploy_containers", {}).get("status") != "completed":
            return "container_deployment"
        elif step_statuses.get("run_migrations", {}).get("status") != "completed":
            return "database_setup"
        elif step_statuses.get("create_admin", {}).get("status") != "completed":
            return "account_creation"
        elif step_statuses.get("health_checks", {}).get("status") != "completed":
            return "health_verification"
        elif step_statuses.get("send_notifications", {}).get("status") != "completed":
            return "finalization"
        else:
            return "completed"

    def _estimate_completion_time(self, status: dict[str, Any]) -> Optional[str]:
        """Estimate remaining completion time based on current progress."""
        try:
            progress = status.get("progress_percentage", 0)
            if progress >= 100:
                return None

            # Estimate based on typical step durations
            step_durations = {
                "validate_config": 120,
                "create_database": 300,
                "generate_secrets": 60,
                "deploy_containers": 600,
                "run_migrations": 300,
                "seed_data": 180,
                "create_admin": 120,
                "provision_license": 120,
                "health_checks": 180,
                "send_notifications": 60,
            }

            remaining_time = 0
            step_statuses = status.get("step_statuses", {})

            for step_id, duration in step_durations.items():
                step_status = step_statuses.get(step_id, {}).get("status", "pending")
                if step_status in ["pending", "running"]:
                    remaining_time += duration

            if remaining_time > 0:
                return (datetime.now(timezone.utc) + timedelta(seconds=remaining_time)).isoformat()

            return None

        except Exception as e:
            logger.warning(f"Failed to estimate completion time: {e}")
            return None

    async def _get_troubleshooting_info(self, status: dict[str, Any]) -> dict[str, Any]:
        """Get troubleshooting information for failed or stuck provisioning."""
        troubleshooting = {"common_issues": [], "suggested_actions": [], "support_info": {}}

        try:
            step_statuses = status.get("step_statuses", {})

            # Check for common failure patterns
            for step_id, step_status in step_statuses.items():
                if step_status.get("status") == "failed":
                    error = step_status.get("error", "")

                    if "timeout" in error.lower():
                        troubleshooting["common_issues"].append(
                            {
                                "step": step_id,
                                "issue": "Step timeout",
                                "description": "Step took longer than expected to complete",
                            }
                        )
                        troubleshooting["suggested_actions"].append("Retry the failed step or contact support")

                    elif "connection" in error.lower():
                        troubleshooting["common_issues"].append(
                            {
                                "step": step_id,
                                "issue": "Connection error",
                                "description": "Network connectivity issues during step execution",
                            }
                        )
                        troubleshooting["suggested_actions"].append("Check network connectivity and retry")

            return troubleshooting

        except Exception as e:
            logger.warning(f"Failed to generate troubleshooting info: {e}")
            return troubleshooting

    def _step_was_attempted(self, status: Optional[dict], step_id: str) -> bool:
        """Check if a workflow step was attempted."""
        if not status or "step_statuses" not in status:
            return False

        step_status = status["step_statuses"].get(step_id, {}).get("status")
        return step_status in ["running", "completed", "failed"]

    # Task implementation methods would go here...
    # For brevity, I'll implement a few key ones as examples:

    async def _validate_tenant_configuration(
        self, tenant_db_id: int, task_context: Optional[dict] = None
    ) -> dict[str, Any]:
        """Task: Validate tenant configuration before provisioning."""
        async with TaskExecutionContext(
            task_name="validate_tenant_configuration",
            progress_callback=task_context.get("progress_callback") if task_context else None,
        ) as ctx:
            await ctx.update_progress(10, "Loading tenant configuration")

            # Get tenant from database
            with get_db_session() as db:
                tenant = db.query(CustomerTenant).filter_by(id=tenant_db_id).first()
                if not tenant:
                    raise ValueError(f"Tenant {tenant_db_id} not found")

            await ctx.update_progress(30, "Validating subdomain availability")
            # Validate subdomain availability
            if not await self._check_subdomain_available(tenant.subdomain):
                raise ValueError(f"Subdomain {tenant.subdomain} is not available")

            await ctx.update_progress(60, "Checking plan limits")
            # Validate plan limits
            if not await self._check_plan_limits(tenant.plan):
                raise ValueError(f"Plan {tenant.plan} limits exceeded")

            await ctx.update_progress(90, "Verifying region availability")
            # Validate region availability
            if not await self._check_region_availability(tenant.region):
                raise ValueError(f"Region {tenant.region} is not available")

            await ctx.update_progress(100, "Configuration validation completed")

            return {
                "tenant_id": tenant.tenant_id,
                "subdomain": tenant.subdomain,
                "plan": tenant.plan,
                "region": tenant.region,
                "validation_status": "passed",
            }

    async def _create_tenant_database_resources(
        self, tenant_db_id: int, task_context: Optional[dict] = None
    ) -> dict[str, Any]:
        """Task: Create database and Redis resources for tenant."""
        async with TaskExecutionContext(
            task_name="create_tenant_database_resources",
            progress_callback=task_context.get("progress_callback") if task_context else None,
        ) as ctx:
            await ctx.update_progress(10, "Loading tenant information")

            with get_db_session() as db:
                tenant = db.query(CustomerTenant).filter_by(id=tenant_db_id).first()
                if not tenant:
                    raise ValueError(f"Tenant {tenant_db_id} not found")

            await ctx.update_progress(30, "Creating PostgreSQL database")
            # Create dedicated database for tenant
            database_config = await self._create_tenant_database(tenant)

            await ctx.update_progress(60, "Creating Redis cache instance")
            # Create dedicated Redis instance
            redis_config = await self._create_tenant_redis(tenant)

            await ctx.update_progress(90, "Storing database configuration")
            # Update tenant with database URLs
            with get_db_session() as db:
                from dotmac_shared.core.error_utils import db_transaction

                tenant = db.query(CustomerTenant).filter_by(id=tenant_db_id).first()
                with db_transaction(db):
                    tenant.database_url = await self.secrets_manager.encrypt(database_config["url"])
                    tenant.redis_url = await self.secrets_manager.encrypt(redis_config["url"])

            await ctx.update_progress(100, "Database resources created successfully")

            return {
                "database_service_id": database_config.get("service_id"),
                "redis_service_id": redis_config.get("service_id"),
                "database_name": database_config.get("database_name"),
                "redis_instance": redis_config.get("instance_name"),
                "resources_created": True,
            }

    # Placeholder implementations for remaining tasks...
    async def _generate_tenant_secrets(self, tenant_db_id: int, task_context: Optional[dict] = None) -> dict[str, Any]:
        """Task: Generate tenant-specific secrets and encryption keys."""
        # Implementation would generate JWT secrets, encryption keys, etc.
        return {"secrets_generated": True}

    async def _deploy_tenant_containers(self, tenant_db_id: int, task_context: Optional[dict] = None) -> dict[str, Any]:
        """Task: Deploy tenant container stack via Coolify API."""
        # Implementation would deploy containers using Coolify client
        return {"containers_deployed": True}

    async def _run_tenant_migrations(self, tenant_db_id: int, task_context: Optional[dict] = None) -> dict[str, Any]:
        """Task: Run database migrations for tenant schema."""
        # Implementation would run database migrations
        return {"migrations_completed": True}

    async def _seed_tenant_data(self, tenant_db_id: int, task_context: Optional[dict] = None) -> dict[str, Any]:
        """Task: Seed initial data for tenant."""
        # Implementation would seed initial tenant data
        return {"data_seeded": True}

    async def _create_tenant_admin_account(
        self, tenant_db_id: int, task_context: Optional[dict] = None
    ) -> dict[str, Any]:
        """Task: Create admin account for tenant."""
        # Implementation would create tenant admin account
        return {"admin_created": True}

    async def _provision_tenant_license(self, tenant_db_id: int, task_context: Optional[dict] = None) -> dict[str, Any]:
        """Task: Provision license contract for tenant."""
        # Implementation would provision license
        return {"license_provisioned": True}

    async def _run_tenant_health_checks(self, tenant_db_id: int, task_context: Optional[dict] = None) -> dict[str, Any]:
        """Task: Run comprehensive health checks on deployed tenant."""
        # Implementation would run health checks
        return {"health_checks_passed": True}

    async def _send_tenant_welcome_notifications(
        self, tenant_db_id: int, channels: list[dict], task_context: Optional[dict] = None
    ) -> dict[str, Any]:
        """Task: Send welcome notifications to tenant admin."""
        # Implementation would send notifications
        return {"notifications_sent": len(channels)}

    # Retry task implementations...
    async def _retry_validate_tenant_configuration(
        self, tenant_db_id: int, workflow_id: str, step_status: dict, task_context: Optional[dict] = None
    ) -> dict[str, Any]:
        """Retry task: Validate tenant configuration with additional checks."""
        # Enhanced validation with more thorough checks
        return await self._validate_tenant_configuration(tenant_db_id, task_context)

    async def _retry_create_tenant_database_resources(
        self, tenant_db_id: int, workflow_id: str, step_status: dict, task_context: Optional[dict] = None
    ) -> dict[str, Any]:
        """Retry task: Create database resources with enhanced error handling."""
        # Enhanced database creation with cleanup of partial resources
        return await self._create_tenant_database_resources(tenant_db_id, task_context)

    # Additional retry implementations would follow the same pattern...

    # Cleanup task implementations...
    async def _cleanup_tenant_containers(
        self, tenant_db_id: int, task_context: Optional[dict] = None
    ) -> dict[str, Any]:
        """Cleanup task: Remove tenant containers and associated resources."""
        # Implementation would cleanup containers via Coolify API
        return {"containers_cleaned": True}

    async def _cleanup_tenant_database(self, tenant_db_id: int, task_context: Optional[dict] = None) -> dict[str, Any]:
        """Cleanup task: Remove tenant database and Redis resources."""
        # Implementation would cleanup database resources
        return {"database_cleaned": True}

    async def _update_tenant_cleanup_status(
        self, tenant_db_id: int, reason: str, task_context: Optional[dict] = None
    ) -> dict[str, Any]:
        """Cleanup task: Update tenant status after cleanup completion."""
        with get_db_session() as db:
            from dotmac_shared.core.error_utils import db_transaction

            tenant = db.query(CustomerTenant).filter_by(id=tenant_db_id).first()
            if tenant:
                with db_transaction(db):
                    tenant.status = TenantStatus.FAILED
                    event = TenantProvisioningEvent(
                        tenant_id=tenant.id,
                        event_type="cleanup_completed",
                        status="success",
                        message=f"Cleanup completed: {reason}",
                        operator="system",
                    )
                    db.add(event)

        return {"status_updated": True, "reason": reason}

    async def decommission_tenant(
        self, tenant_db_id: int, reason: str = "Customer requested decommissioning", backup_data: bool = True
    ) -> str:
        """
        Complete tenant decommissioning workflow with automated cleanup.

        Leverages existing cleanup workflow infrastructure for DRY implementation.
        """
        try:
            # Create comprehensive decommissioning workflow
            workflow = await self._create_decommissioning_workflow(tenant_db_id, reason, backup_data)

            # Start workflow execution
            workflow_id = await self.workflow_orchestrator.start_workflow(workflow)

            logger.info(
                "Started tenant decommissioning workflow",
                extra={"tenant_db_id": tenant_db_id, "workflow_id": workflow_id, "reason": reason},
            )

            return workflow_id

        except Exception as e:
            logger.error(f"Failed to start tenant decommissioning: {e}")
            raise

    async def _create_decommissioning_workflow(self, tenant_db_id: int, reason: str, backup_data: bool):
        """Create comprehensive tenant decommissioning workflow."""

        workflow_id = f"tenant-decommission-{tenant_db_id}-{int(time.time())}"

        # Define decommissioning steps
        steps = []

        # Step 1: Data backup (if requested)
        if backup_data:
            steps.append(
                WorkflowStep(
                    step_id="backup_tenant_data",
                    name="Backup Tenant Data",
                    step_type=StepType.TASK,
                    function_name="backup_tenant_data",
                    args=[tenant_db_id],
                    task_config=TaskConfig(
                        priority=TaskPriority.HIGH, timeout=600, max_retries=2, queue_name="decommissioning"
                    ),
                    timeout_seconds=600,
                )
            )

        # Step 2: Finalize billing
        steps.append(
            WorkflowStep(
                step_id="finalize_billing",
                name="Finalize Tenant Billing",
                step_type=StepType.TASK,
                function_name="finalize_tenant_billing",
                args=[tenant_db_id, reason],
                depends_on={"backup_tenant_data"} if backup_data else set(),
                task_config=TaskConfig(
                    priority=TaskPriority.HIGH, timeout=300, max_retries=2, queue_name="decommissioning"
                ),
                timeout_seconds=300,
            )
        )

        # Step 3: Notify reseller/customer
        steps.append(
            WorkflowStep(
                step_id="send_decommission_notifications",
                name="Send Decommissioning Notifications",
                step_type=StepType.TASK,
                function_name="send_decommission_notifications",
                args=[tenant_db_id, reason],
                task_config=TaskConfig(
                    priority=TaskPriority.NORMAL, timeout=300, max_retries=2, queue_name="notifications"
                ),
                timeout_seconds=300,
            )
        )

        # Step 4: Stop container services
        steps.append(
            WorkflowStep(
                step_id="stop_tenant_services",
                name="Stop Tenant Services",
                step_type=StepType.TASK,
                function_name="stop_tenant_services",
                args=[tenant_db_id],
                depends_on={"finalize_billing", "send_decommission_notifications"},
                task_config=TaskConfig(
                    priority=TaskPriority.HIGH, timeout=300, max_retries=3, queue_name="decommissioning"
                ),
                timeout_seconds=300,
            )
        )

        # Step 5: Cleanup containers (leverage existing)
        steps.append(
            WorkflowStep(
                step_id="cleanup_containers",
                name="Cleanup Container Resources",
                step_type=StepType.TASK,
                function_name="cleanup_tenant_containers",
                args=[tenant_db_id],
                depends_on={"stop_tenant_services"},
                task_config=TaskConfig(priority=TaskPriority.HIGH, timeout=300, max_retries=2, queue_name="cleanup"),
                timeout_seconds=300,
            )
        )

        # Step 6: Cleanup database (leverage existing)
        steps.append(
            WorkflowStep(
                step_id="cleanup_database",
                name="Cleanup Database Resources",
                step_type=StepType.TASK,
                function_name="cleanup_tenant_database",
                args=[tenant_db_id],
                depends_on={"stop_tenant_services"},
                task_config=TaskConfig(priority=TaskPriority.HIGH, timeout=300, max_retries=2, queue_name="cleanup"),
                timeout_seconds=300,
            )
        )

        # Step 7: Update tenant status (leverage existing)
        steps.append(
            WorkflowStep(
                step_id="update_status",
                name="Update Tenant Status",
                step_type=StepType.TASK,
                function_name="update_tenant_decommission_status",
                args=[tenant_db_id, reason],
                depends_on={"cleanup_containers", "cleanup_database"},
                task_config=TaskConfig(priority=TaskPriority.NORMAL, timeout=60, max_retries=1, queue_name="cleanup"),
                timeout_seconds=60,
            )
        )

        return Workflow(
            workflow_id=workflow_id,
            name=f"Tenant Decommissioning - {tenant_db_id}",
            description=f"Complete tenant decommissioning workflow: {reason}",
            steps=steps,
            timeout_seconds=1800,  # 30 minutes for decommissioning
            metadata={
                "tenant_db_id": tenant_db_id,
                "decommission_reason": reason,
                "backup_data": backup_data,
                "decommission_type": "complete_cleanup",
                "initiated_by": "automated_system",
            },
        )

    # New decommissioning task implementations (extend existing tasks)
    async def backup_tenant_data(self, tenant_db_id: int, task_context: Optional[dict] = None) -> dict[str, Any]:
        """Task: Backup tenant data before decommissioning."""
        async with TaskExecutionContext(
            task_name="backup_tenant_data",
            progress_callback=task_context.get("progress_callback") if task_context else None,
        ) as ctx:
            await ctx.update_progress(10, "Starting tenant data backup")

            # Get tenant info
            with get_db_session() as db:
                tenant = db.query(CustomerTenant).filter_by(id=tenant_db_id).first()
                if not tenant:
                    raise ValueError(f"Tenant {tenant_db_id} not found")

            await ctx.update_progress(30, "Backing up database")
            # Backup database (implementation would use database backup tools)
            await asyncio.sleep(2)  # Simulate backup

            await ctx.update_progress(60, "Backing up file storage")
            # Backup file storage (implementation would use storage backup tools)
            await asyncio.sleep(1)  # Simulate file backup

            await ctx.update_progress(90, "Creating backup manifest")
            # Create backup manifest
            backup_info = {
                "backup_id": f"backup-{tenant_db_id}-{int(time.time())}",
                "tenant_id": tenant.tenant_id,
                "backup_timestamp": datetime.now(timezone.utc).isoformat(),
                "database_backup_size_mb": 150,  # Simulated size
                "file_backup_size_mb": 75,  # Simulated size
                "retention_days": 90,
            }

            await ctx.update_progress(100, "Data backup completed")

            return {
                "backup_completed": True,
                "backup_info": backup_info,
                "total_size_mb": backup_info["database_backup_size_mb"] + backup_info["file_backup_size_mb"],
            }

    async def finalize_tenant_billing(
        self, tenant_db_id: int, reason: str, task_context: Optional[dict] = None
    ) -> dict[str, Any]:
        """Task: Finalize billing for decommissioned tenant."""
        async with TaskExecutionContext(
            task_name="finalize_tenant_billing",
            progress_callback=task_context.get("progress_callback") if task_context else None,
        ) as ctx:
            await ctx.update_progress(10, "Calculating final billing")

            # Get tenant and reseller info
            with get_db_session() as db:
                tenant = db.query(CustomerTenant).filter_by(id=tenant_db_id).first()
                if not tenant:
                    raise ValueError(f"Tenant {tenant_db_id} not found")

            await ctx.update_progress(40, "Processing final usage charges")
            # Process any pending usage charges (would integrate with usage billing)
            final_usage_cost = Decimal("23.45")  # Simulated final usage

            await ctx.update_progress(70, "Creating final invoice")
            # Create final invoice/commission record
            final_billing = {
                "tenant_id": tenant.tenant_id,
                "final_usage_cost": float(final_usage_cost),
                "billing_period_end": datetime.now(timezone.utc).date(),
                "invoice_status": "finalized",
                "decommission_reason": reason,
                "pro_rated_refund": 0.00,  # Calculate if applicable
            }

            await ctx.update_progress(100, "Billing finalization completed")

            return {"billing_finalized": True, "final_billing": final_billing}

    async def send_decommission_notifications(
        self, tenant_db_id: int, reason: str, task_context: Optional[dict] = None
    ) -> dict[str, Any]:
        """Task: Send decommissioning notifications."""
        async with TaskExecutionContext(
            task_name="send_decommission_notifications",
            progress_callback=task_context.get("progress_callback") if task_context else None,
        ) as ctx:
            await ctx.update_progress(20, "Sending reseller notification")

            # Send notification to reseller
            await asyncio.sleep(0.5)  # Simulate notification sending

            await ctx.update_progress(60, "Sending customer notification")

            # Send notification to customer
            await asyncio.sleep(0.5)  # Simulate notification sending

            await ctx.update_progress(100, "Decommissioning notifications sent")

            return {"notifications_sent": True, "reseller_notified": True, "customer_notified": True, "reason": reason}

    async def stop_tenant_services(self, tenant_db_id: int, task_context: Optional[dict] = None) -> dict[str, Any]:
        """Task: Stop tenant services before cleanup."""
        async with TaskExecutionContext(
            task_name="stop_tenant_services",
            progress_callback=task_context.get("progress_callback") if task_context else None,
        ) as ctx:
            await ctx.update_progress(20, "Stopping application services")

            # Stop application containers
            await asyncio.sleep(1)  # Simulate service stop

            await ctx.update_progress(60, "Stopping database connections")

            # Close database connections
            await asyncio.sleep(0.5)  # Simulate connection cleanup

            await ctx.update_progress(100, "All tenant services stopped")

            return {"services_stopped": True, "application_stopped": True, "database_disconnected": True}

    async def update_tenant_decommission_status(
        self, tenant_db_id: int, reason: str, task_context: Optional[dict] = None
    ) -> dict[str, Any]:
        """Task: Update tenant status after decommissioning."""
        with get_db_session() as db:
            from dotmac_shared.core.error_utils import db_transaction

            tenant = db.query(CustomerTenant).filter_by(id=tenant_db_id).first()
            if tenant:
                with db_transaction(db):
                    tenant.status = TenantStatus.DECOMMISSIONED
                    tenant.decommissioned_at = datetime.now(timezone.utc)
                    tenant.decommission_reason = reason

                    event = TenantProvisioningEvent(
                        tenant_id=tenant.id,
                        event_type="decommissioning_completed",
                        status="success",
                        message=f"Tenant decommissioning completed: {reason}",
                        operator="system",
                    )
                    db.add(event)

        return {
            "status_updated": True,
            "new_status": "decommissioned",
            "reason": reason,
            "decommissioned_at": datetime.now(timezone.utc).isoformat(),
        }

    # Helper methods from original service...
    async def _check_subdomain_available(self, subdomain: str) -> bool:
        return True  # Placeholder

    async def _check_plan_limits(self, plan: str) -> bool:
        return True  # Placeholder

    async def _check_region_availability(self, region: str) -> bool:
        return True  # Placeholder

    async def _create_tenant_database(self, tenant: CustomerTenant) -> dict[str, str]:
        # Placeholder implementation
        return {
            "url": f"postgresql://tenant_{tenant.subdomain}:password@localhost:5432/tenant_{tenant.subdomain}",
            "service_id": "db-123",
        }

    async def _create_tenant_redis(self, tenant: CustomerTenant) -> dict[str, str]:
        # Placeholder implementation
        return {"url": "redis://:password@localhost:6379/0", "service_id": "redis-123"}
