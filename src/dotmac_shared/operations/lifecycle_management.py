"""
Customer Lifecycle Management Scripts

Automated customer onboarding, provisioning, and lifecycle management.
Integrates with existing user management patterns and DRY principles.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from dotmac.application import standard_exception_handler
from dotmac.core.exceptions import BusinessRuleError
from dotmac_management.user_management.core.user_repository import UserRepository
from dotmac_management.user_management.schemas.lifecycle_schemas import (
    UserLifecycleEvent,
    UserRegistration,
)
from dotmac_management.user_management.schemas.user_schemas import UserStatus
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class CustomerLifecycleStage(str, Enum):
    """Customer lifecycle stages"""

    REGISTRATION = "registration"
    VERIFICATION = "verification"
    ONBOARDING = "onboarding"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CHURNING = "churning"
    INACTIVE = "inactive"
    DELETED = "deleted"


class ServiceStatus(str, Enum):
    """Service provisioning status"""

    PENDING = "pending"
    PROVISIONING = "provisioning"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEPROVISIONING = "deprovisioning"
    TERMINATED = "terminated"


@dataclass
class CustomerServiceConfig:
    """Customer service configuration"""

    service_id: UUID
    service_name: str
    service_type: str
    configuration: dict[str, Any]
    auto_provision: bool = True
    requires_approval: bool = False


@dataclass
class LifecycleAction:
    """Lifecycle management action"""

    action_id: UUID
    customer_id: UUID
    action_type: str
    stage_from: CustomerLifecycleStage
    stage_to: CustomerLifecycleStage
    parameters: dict[str, Any]
    scheduled_at: datetime
    executed_at: Optional[datetime] = None
    success: bool = False
    error_message: Optional[str] = None


class CustomerLifecycleManager:
    """
    Comprehensive customer lifecycle management automation.

    Handles the complete customer journey from registration to deletion
    with automated provisioning and service management.
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.user_repository = UserRepository(db_session)
        self.lifecycle_hooks: dict[str, list[callable]] = {}

    @standard_exception_handler
    async def register_lifecycle_hook(self, stage: CustomerLifecycleStage, hook_function: callable) -> None:
        """Register lifecycle hook for specific stage."""
        if stage not in self.lifecycle_hooks:
            self.lifecycle_hooks[stage] = []

        self.lifecycle_hooks[stage].append(hook_function)
        logger.info(f"Registered lifecycle hook for stage: {stage}")

    @standard_exception_handler
    async def execute_lifecycle_hooks(self, stage: CustomerLifecycleStage, customer_data: dict[str, Any]) -> None:
        """Execute all hooks for a lifecycle stage."""
        if stage not in self.lifecycle_hooks:
            return

        for hook in self.lifecycle_hooks[stage]:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(customer_data)
                else:
                    hook(customer_data)
                logger.debug(f"Executed lifecycle hook for {stage}")
            except Exception as e:
                logger.error(f"Lifecycle hook failed for {stage}: {e}")

    @standard_exception_handler
    async def process_new_registration(self, registration_data: UserRegistration) -> dict[str, Any]:
        """Process new customer registration with automated workflows."""

        # Create user account
        user_response = await self.user_repository.create_user(registration_data)

        # Create lifecycle event
        lifecycle_event = UserLifecycleEvent(
            event_id=uuid4(),
            user_id=user_response.id,
            event_type="customer_registration",
            event_data={
                "registration_source": registration_data.registration_source,
                "user_type": registration_data.user_type,
                "tenant_id": str(registration_data.tenant_id) if registration_data.tenant_id else None,
                "requires_approval": registration_data.requires_approval,
            },
            source_platform="lifecycle_manager",
            timestamp=datetime.now(timezone.utc),
        )

        await self.user_repository.create_lifecycle_event(lifecycle_event)

        # Execute registration hooks
        customer_data = {
            "user_id": user_response.id,
            "email": user_response.email,
            "user_type": user_response.user_type,
            "registration_data": registration_data,
        }

        await self.execute_lifecycle_hooks(CustomerLifecycleStage.REGISTRATION, customer_data)

        # Determine next steps based on configuration
        next_actions = []

        if registration_data.requires_approval:
            next_actions.append({"action": "require_approval", "message": "Account created, pending approval"})
        else:
            next_actions.append({"action": "send_verification", "message": "Verification email sent"})

        return {
            "user_id": user_response.id,
            "status": "registered",
            "lifecycle_stage": CustomerLifecycleStage.REGISTRATION,
            "next_actions": next_actions,
            "created_at": user_response.created_at.isoformat(),
        }

    @standard_exception_handler
    async def verify_customer_account(self, user_id: UUID, verification_data: dict[str, Any]) -> dict[str, Any]:
        """Verify customer account and advance lifecycle."""

        # Update user verification status
        success = await self.user_repository.activate_user(user_id, verification_data)

        if not success:
            raise BusinessRuleError(f"Failed to verify user account {user_id}")

        # Create lifecycle event
        lifecycle_event = UserLifecycleEvent(
            event_id=uuid4(),
            user_id=user_id,
            event_type="customer_verification",
            event_data=verification_data,
            source_platform="lifecycle_manager",
            timestamp=datetime.now(timezone.utc),
        )

        await self.user_repository.create_lifecycle_event(lifecycle_event)

        # Execute verification hooks
        user = await self.user_repository.get_user_by_id(user_id)
        customer_data = {
            "user_id": user_id,
            "user": user,
            "verification_data": verification_data,
        }

        await self.execute_lifecycle_hooks(CustomerLifecycleStage.VERIFICATION, customer_data)

        return {
            "user_id": user_id,
            "status": "verified",
            "lifecycle_stage": CustomerLifecycleStage.VERIFICATION,
            "next_actions": [{"action": "begin_onboarding", "message": "Account verified, starting onboarding"}],
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }

    @standard_exception_handler
    async def onboard_customer(self, user_id: UUID, onboarding_data: dict[str, Any]) -> dict[str, Any]:
        """Complete customer onboarding process."""

        user = await self.user_repository.get_user_by_id(user_id)
        if not user:
            raise BusinessRuleError(f"User {user_id} not found")

        if user.status != UserStatus.ACTIVE:
            raise BusinessRuleError(f"User {user_id} must be active to complete onboarding")

        # Create lifecycle event
        lifecycle_event = UserLifecycleEvent(
            event_id=uuid4(),
            user_id=user_id,
            event_type="customer_onboarding",
            event_data=onboarding_data,
            source_platform="lifecycle_manager",
            timestamp=datetime.now(timezone.utc),
        )

        await self.user_repository.create_lifecycle_event(lifecycle_event)

        # Execute onboarding hooks
        customer_data = {
            "user_id": user_id,
            "user": user,
            "onboarding_data": onboarding_data,
        }

        await self.execute_lifecycle_hooks(CustomerLifecycleStage.ONBOARDING, customer_data)

        return {
            "user_id": user_id,
            "status": "onboarded",
            "lifecycle_stage": CustomerLifecycleStage.ACTIVE,
            "onboarded_at": datetime.now(timezone.utc).isoformat(),
        }

    @standard_exception_handler
    async def suspend_customer(
        self, user_id: UUID, suspension_reason: str, suspension_data: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Suspend customer account and services."""

        # Deactivate user account
        success = await self.user_repository.deactivate_user(user_id, suspension_reason)

        if not success:
            raise BusinessRuleError(f"Failed to suspend user account {user_id}")

        # Create lifecycle event
        lifecycle_event = UserLifecycleEvent(
            event_id=uuid4(),
            user_id=user_id,
            event_type="customer_suspension",
            event_data={
                "reason": suspension_reason,
                "additional_data": suspension_data or {},
            },
            source_platform="lifecycle_manager",
            timestamp=datetime.now(timezone.utc),
        )

        await self.user_repository.create_lifecycle_event(lifecycle_event)

        # Execute suspension hooks
        user = await self.user_repository.get_user_by_id(user_id)
        customer_data = {
            "user_id": user_id,
            "user": user,
            "suspension_reason": suspension_reason,
            "suspension_data": suspension_data or {},
        }

        await self.execute_lifecycle_hooks(CustomerLifecycleStage.SUSPENDED, customer_data)

        return {
            "user_id": user_id,
            "status": "suspended",
            "lifecycle_stage": CustomerLifecycleStage.SUSPENDED,
            "suspension_reason": suspension_reason,
            "suspended_at": datetime.now(timezone.utc).isoformat(),
        }

    @standard_exception_handler
    async def reactivate_customer(
        self, user_id: UUID, reactivation_data: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Reactivate suspended customer account."""

        # Activate user account
        success = await self.user_repository.activate_user(user_id, reactivation_data or {})

        if not success:
            raise BusinessRuleError(f"Failed to reactivate user account {user_id}")

        # Create lifecycle event
        lifecycle_event = UserLifecycleEvent(
            event_id=uuid4(),
            user_id=user_id,
            event_type="customer_reactivation",
            event_data=reactivation_data or {},
            source_platform="lifecycle_manager",
            timestamp=datetime.now(timezone.utc),
        )

        await self.user_repository.create_lifecycle_event(lifecycle_event)

        # Execute reactivation hooks
        user = await self.user_repository.get_user_by_id(user_id)
        customer_data = {
            "user_id": user_id,
            "user": user,
            "reactivation_data": reactivation_data or {},
        }

        await self.execute_lifecycle_hooks(CustomerLifecycleStage.ACTIVE, customer_data)

        return {
            "user_id": user_id,
            "status": "reactivated",
            "lifecycle_stage": CustomerLifecycleStage.ACTIVE,
            "reactivated_at": datetime.now(timezone.utc).isoformat(),
        }

    @standard_exception_handler
    async def delete_customer(self, user_id: UUID, deletion_reason: str, hard_delete: bool = False) -> dict[str, Any]:
        """Delete customer account and data."""

        # Create lifecycle event before deletion
        lifecycle_event = UserLifecycleEvent(
            event_id=uuid4(),
            user_id=user_id,
            event_type="customer_deletion",
            event_data={
                "reason": deletion_reason,
                "hard_delete": hard_delete,
            },
            source_platform="lifecycle_manager",
            timestamp=datetime.now(timezone.utc),
        )

        await self.user_repository.create_lifecycle_event(lifecycle_event)

        # Execute deletion hooks before actual deletion
        user = await self.user_repository.get_user_by_id(user_id)
        customer_data = {
            "user_id": user_id,
            "user": user,
            "deletion_reason": deletion_reason,
            "hard_delete": hard_delete,
        }

        await self.execute_lifecycle_hooks(CustomerLifecycleStage.DELETED, customer_data)

        # Delete user account
        success = await self.user_repository.delete_user(user_id, not hard_delete)

        if not success:
            raise BusinessRuleError(f"Failed to delete user account {user_id}")

        return {
            "user_id": user_id,
            "status": "deleted",
            "lifecycle_stage": CustomerLifecycleStage.DELETED,
            "deletion_reason": deletion_reason,
            "hard_delete": hard_delete,
            "deleted_at": datetime.now(timezone.utc).isoformat(),
        }

    @standard_exception_handler
    async def get_customer_lifecycle_summary(self, user_id: UUID) -> dict[str, Any]:
        """Get comprehensive customer lifecycle summary."""

        user = await self.user_repository.get_user_by_id(user_id)
        if not user:
            raise BusinessRuleError(f"User {user_id} not found")

        # Get lifecycle events
        events = await self.user_repository.get_user_lifecycle_events(user_id, limit=50)

        # Determine current lifecycle stage
        current_stage = self._determine_lifecycle_stage(user, events)

        return {
            "user_id": user_id,
            "current_stage": current_stage,
            "user_status": user.status,
            "created_at": user.created_at.isoformat(),
            "last_activity": user.updated_at.isoformat(),
            "lifecycle_events": events,
            "stage_history": self._build_stage_history(events),
        }

    def _determine_lifecycle_stage(self, user, events) -> CustomerLifecycleStage:
        """Determine current lifecycle stage based on user status and events."""
        if user.status == UserStatus.DELETED:
            return CustomerLifecycleStage.DELETED
        elif user.status == UserStatus.INACTIVE:
            return CustomerLifecycleStage.SUSPENDED
        elif user.status == UserStatus.PENDING:
            return CustomerLifecycleStage.REGISTRATION
        elif user.status == UserStatus.ACTIVE:
            # Check if onboarding completed
            onboarding_events = [e for e in events if e.get("event_type") == "customer_onboarding"]
            if onboarding_events:
                return CustomerLifecycleStage.ACTIVE
            else:
                verification_events = [e for e in events if e.get("event_type") == "customer_verification"]
                if verification_events:
                    return CustomerLifecycleStage.ONBOARDING
                else:
                    return CustomerLifecycleStage.VERIFICATION

        return CustomerLifecycleStage.REGISTRATION

    def _build_stage_history(self, events) -> list[dict[str, Any]]:
        """Build stage transition history from events."""
        stage_history = []

        for event in reversed(events):  # Chronological order
            if event["event_type"].startswith("customer_"):
                stage_history.append(
                    {
                        "timestamp": event["timestamp"],
                        "event_type": event["event_type"],
                        "stage": event["event_type"].replace("customer_", ""),
                    }
                )

        return stage_history


class ServiceProvisioningAutomation:
    """
    Automated service provisioning and management.

    Handles provisioning, configuration, and lifecycle of customer services.
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.provisioning_queue: list[dict[str, Any]] = []
        self.service_templates: dict[str, CustomerServiceConfig] = {}

    @standard_exception_handler
    async def register_service_template(self, template: CustomerServiceConfig) -> None:
        """Register service template for automated provisioning."""
        self.service_templates[template.service_name] = template
        logger.info(f"Registered service template: {template.service_name}")

    @standard_exception_handler
    async def provision_service(
        self, customer_id: UUID, service_name: str, custom_config: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Provision service for customer."""

        if service_name not in self.service_templates:
            raise BusinessRuleError(f"Service template not found: {service_name}")

        template = self.service_templates[service_name]

        # Merge template config with custom config
        final_config = template.configuration.copy()
        if custom_config:
            final_config.update(custom_config)

        provisioning_request = {
            "request_id": uuid4(),
            "customer_id": customer_id,
            "service_id": template.service_id,
            "service_name": service_name,
            "service_type": template.service_type,
            "configuration": final_config,
            "status": ServiceStatus.PENDING,
            "created_at": datetime.now(timezone.utc),
            "requires_approval": template.requires_approval,
        }

        # Add to provisioning queue
        self.provisioning_queue.append(provisioning_request)

        # Auto-provision if enabled and no approval required
        if template.auto_provision and not template.requires_approval:
            return await self._execute_provisioning(provisioning_request)

        return {
            "request_id": str(provisioning_request["request_id"]),
            "status": ServiceStatus.PENDING,
            "message": "Service provisioning queued" + (" (approval required)" if template.requires_approval else ""),
        }

    @standard_exception_handler
    async def _execute_provisioning(self, provisioning_request: dict[str, Any]) -> dict[str, Any]:
        """Execute service provisioning."""

        try:
            # Update status
            provisioning_request["status"] = ServiceStatus.PROVISIONING
            provisioning_request["provisioning_started_at"] = datetime.now(timezone.utc)

            # Simulate provisioning steps
            await self._provision_infrastructure(provisioning_request)
            await self._configure_service(provisioning_request)
            await self._validate_provisioning(provisioning_request)

            # Mark as active
            provisioning_request["status"] = ServiceStatus.ACTIVE
            provisioning_request["provisioned_at"] = datetime.now(timezone.utc)

            logger.info(
                f"Successfully provisioned service {provisioning_request['service_name']} for customer {provisioning_request['customer_id']}"
            )

            return {
                "request_id": str(provisioning_request["request_id"]),
                "status": ServiceStatus.ACTIVE,
                "message": "Service provisioned successfully",
                "provisioned_at": provisioning_request["provisioned_at"].isoformat(),
            }

        except Exception as e:
            provisioning_request["status"] = ServiceStatus.TERMINATED
            provisioning_request["error"] = str(e)

            logger.error(f"Failed to provision service: {e}")

            return {
                "request_id": str(provisioning_request["request_id"]),
                "status": ServiceStatus.TERMINATED,
                "message": f"Provisioning failed: {str(e)}",
            }

    async def _provision_infrastructure(self, request: dict[str, Any]) -> None:
        """Provision infrastructure for service."""
        # Simulate infrastructure provisioning
        await asyncio.sleep(0.1)
        logger.debug(f"Infrastructure provisioned for {request['service_name']}")

    async def _configure_service(self, request: dict[str, Any]) -> None:
        """Configure provisioned service."""
        # Simulate service configuration
        await asyncio.sleep(0.1)
        logger.debug(f"Service configured for {request['service_name']}")

    async def _validate_provisioning(self, request: dict[str, Any]) -> None:
        """Validate provisioned service."""
        # Simulate validation
        await asyncio.sleep(0.1)
        logger.debug(f"Provisioning validated for {request['service_name']}")

    @standard_exception_handler
    async def get_provisioning_status(self, request_id: UUID) -> dict[str, Any]:
        """Get provisioning request status."""

        request = next((r for r in self.provisioning_queue if r["request_id"] == request_id), None)

        if not request:
            raise BusinessRuleError(f"Provisioning request not found: {request_id}")

        return {
            "request_id": str(request_id),
            "customer_id": str(request["customer_id"]),
            "service_name": request["service_name"],
            "status": request["status"],
            "created_at": request["created_at"].isoformat(),
            "provisioning_started_at": request.get("provisioning_started_at", {}).isoformat()
            if request.get("provisioning_started_at")
            else None,
            "provisioned_at": request.get("provisioned_at", {}).isoformat() if request.get("provisioned_at") else None,
            "error": request.get("error"),
        }

    @standard_exception_handler
    async def suspend_service(self, customer_id: UUID, service_name: str, reason: str) -> dict[str, Any]:
        """Suspend customer service."""

        # Find active provisioning request
        request = next(
            (
                r
                for r in self.provisioning_queue
                if r["customer_id"] == customer_id
                and r["service_name"] == service_name
                and r["status"] == ServiceStatus.ACTIVE
            ),
            None,
        )

        if not request:
            raise BusinessRuleError(f"Active service not found: {service_name} for customer {customer_id}")

        # Update status
        request["status"] = ServiceStatus.SUSPENDED
        request["suspended_at"] = datetime.now(timezone.utc)
        request["suspension_reason"] = reason

        logger.info(f"Suspended service {service_name} for customer {customer_id}: {reason}")

        return {
            "customer_id": str(customer_id),
            "service_name": service_name,
            "status": ServiceStatus.SUSPENDED,
            "reason": reason,
            "suspended_at": request["suspended_at"].isoformat(),
        }

    @standard_exception_handler
    async def terminate_service(self, customer_id: UUID, service_name: str, reason: str) -> dict[str, Any]:
        """Terminate customer service."""

        # Find provisioning request
        request = next(
            (
                r
                for r in self.provisioning_queue
                if r["customer_id"] == customer_id and r["service_name"] == service_name
            ),
            None,
        )

        if not request:
            raise BusinessRuleError(f"Service not found: {service_name} for customer {customer_id}")

        # Update status
        request["status"] = ServiceStatus.DEPROVISIONING
        request["termination_started_at"] = datetime.now(timezone.utc)
        request["termination_reason"] = reason

        # Simulate deprovisioning
        await asyncio.sleep(0.1)

        request["status"] = ServiceStatus.TERMINATED
        request["terminated_at"] = datetime.now(timezone.utc)

        logger.info(f"Terminated service {service_name} for customer {customer_id}: {reason}")

        return {
            "customer_id": str(customer_id),
            "service_name": service_name,
            "status": ServiceStatus.TERMINATED,
            "reason": reason,
            "terminated_at": request["terminated_at"].isoformat(),
        }
