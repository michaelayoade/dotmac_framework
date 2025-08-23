"""
Service Management SDK - lifecycle state machine: requested → provisioning → active → suspended → terminated
"""

from datetime import datetime, timedelta
from dotmac_isp.sdks.core.datetime_utils import utc_now, utc_now_iso
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..core.exceptions import (
    InvalidStateTransitionError,
    ProvisioningError,
    ServiceNotFoundError,
    ServiceStateError,
)


class ServiceState(Enum):
    """Service lifecycle states."""

    REQUESTED = "requested"
    PROVISIONING = "provisioning"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    FAILED = "failed"


class ServiceManagementService:
    """In-memory service for service management operations."""

    def __init__(self):
        self._service_instances: Dict[str, Dict[str, Any]] = {}
        self._state_transitions: Dict[str, List[Dict[str, Any]]] = {}
        self._provisioning_tasks: Dict[str, Dict[str, Any]] = {}

        # Define valid state transitions
        self._valid_transitions = {
            ServiceState.REQUESTED: [
                ServiceState.PROVISIONING,
                ServiceState.FAILED,
                ServiceState.TERMINATED,
            ],
            ServiceState.PROVISIONING: [
                ServiceState.ACTIVE,
                ServiceState.FAILED,
                ServiceState.TERMINATED,
            ],
            ServiceState.ACTIVE: [ServiceState.SUSPENDED, ServiceState.TERMINATED],
            ServiceState.SUSPENDED: [ServiceState.ACTIVE, ServiceState.TERMINATED],
            ServiceState.TERMINATED: [],  # Terminal state
            ServiceState.FAILED: [ServiceState.PROVISIONING, ServiceState.TERMINATED],
        }

    async def create_service_instance(self, **kwargs) -> Dict[str, Any]:
        """Create service instance."""
        instance_id = kwargs.get("instance_id") or str(uuid4())

        instance = {
            "instance_id": instance_id,
            "customer_id": kwargs["customer_id"],
            "service_plan_id": kwargs["service_plan_id"],
            "bundle_id": kwargs.get("bundle_id"),
            "addon_ids": kwargs.get("addon_ids", []),
            "service_name": kwargs.get("service_name", ""),
            "configuration": kwargs.get("configuration", {}),
            "metadata": kwargs.get("metadata", {}),
            "state": ServiceState.REQUESTED.value,
            "state_reason": "Service requested by customer",
            "created_at": utc_now().isoformat(),
            "updated_at": utc_now().isoformat(),
            "activated_at": None,
            "suspended_at": None,
            "terminated_at": None,
            "provisioning_started_at": None,
            "provisioning_completed_at": None,
            "last_state_change": utc_now().isoformat(),
            "retry_count": 0,
            "max_retries": kwargs.get("max_retries", 3),
            "auto_retry": kwargs.get("auto_retry", True),
            "scheduled_actions": kwargs.get("scheduled_actions", []),
        }

        self._service_instances[instance_id] = instance
        self._state_transitions[instance_id] = []

        # Record initial state transition
        await self._record_state_transition(
            instance_id,
            None,
            ServiceState.REQUESTED.value,
            "Service instance created",
            kwargs.get("created_by"),
        )

        return instance

    async def transition_service_state(  # noqa: C901
        self,
        instance_id: str,
        target_state: str,
        reason: Optional[str] = None,
        triggered_by: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Transition service to target state."""
        if instance_id not in self._service_instances:
            raise ServiceNotFoundError(f"Service instance not found: {instance_id}")

        instance = self._service_instances[instance_id]
        current_state = ServiceState(instance["state"])
        target_state_enum = ServiceState(target_state)

        # Validate transition
        if target_state_enum not in self._valid_transitions[current_state]:
            raise InvalidStateTransitionError(
                f"Invalid transition from {current_state.value} to {target_state}"
            )

        # Update instance
        old_state = instance["state"]
        instance["state"] = target_state
        instance["state_reason"] = reason or f"Transitioned to {target_state}"
        instance["updated_at"] = utc_now().isoformat()
        instance["last_state_change"] = utc_now().isoformat()

        # Set specific timestamps
        if target_state == ServiceState.PROVISIONING.value:
            instance["provisioning_started_at"] = utc_now().isoformat()
        elif target_state == ServiceState.ACTIVE.value:
            instance["activated_at"] = utc_now().isoformat()
            if instance["provisioning_started_at"]:
                instance["provisioning_completed_at"] = utc_now().isoformat()
        elif target_state == ServiceState.SUSPENDED.value:
            instance["suspended_at"] = utc_now().isoformat()
        elif target_state == ServiceState.TERMINATED.value:
            instance["terminated_at"] = utc_now().isoformat()

        # Record state transition
        await self._record_state_transition(
            instance_id, old_state, target_state, reason, triggered_by
        )

        # Handle state-specific actions
        if target_state == ServiceState.PROVISIONING.value:
            await self._start_provisioning(instance_id, **kwargs)
        elif target_state == ServiceState.ACTIVE.value:
            await self._activate_service(instance_id, **kwargs)
        elif target_state == ServiceState.SUSPENDED.value:
            await self._suspend_service(instance_id, **kwargs)
        elif target_state == ServiceState.TERMINATED.value:
            await self._terminate_service(instance_id, **kwargs)

        return {
            "instance_id": instance_id,
            "old_state": old_state,
            "new_state": target_state,
            "transition_time": instance["last_state_change"],
            "reason": instance["state_reason"],
        }

    async def _record_state_transition(
        self,
        instance_id: str,
        from_state: Optional[str],
        to_state: str,
        reason: Optional[str],
        triggered_by: Optional[str],
    ):
        """Record state transition history."""
        transition = {
            "transition_id": str(uuid4()),
            "from_state": from_state,
            "to_state": to_state,
            "reason": reason,
            "triggered_by": triggered_by,
            "timestamp": utc_now().isoformat(),
        }

        if instance_id not in self._state_transitions:
            self._state_transitions[instance_id] = []

        self._state_transitions[instance_id].append(transition)

    async def _start_provisioning(self, instance_id: str, **kwargs):
        """Start service provisioning."""
        task_id = str(uuid4())

        provisioning_task = {
            "task_id": task_id,
            "instance_id": instance_id,
            "status": "running",
            "started_at": utc_now().isoformat(),
            "estimated_completion": (utc_now() + timedelta(minutes=5)).isoformat(),
            "progress_percentage": 0,
            "current_step": "initializing",
            "steps": kwargs.get(
                "provisioning_steps",
                [
                    "validate_resources",
                    "allocate_resources",
                    "configure_service",
                    "test_connectivity",
                    "activate_service",
                ],
            ),
            "completed_steps": [],
            "failed_steps": [],
            "error_message": None,
        }

        self._provisioning_tasks[task_id] = provisioning_task

        # Update instance with task reference
        instance = self._service_instances[instance_id]
        instance["provisioning_task_id"] = task_id

    async def _activate_service(self, instance_id: str, **kwargs):
        """Activate service."""
        instance = self._service_instances[instance_id]

        # Mark provisioning task as completed if exists
        if "provisioning_task_id" in instance:
            task_id = instance["provisioning_task_id"]
            if task_id in self._provisioning_tasks:
                task = self._provisioning_tasks[task_id]
                task["status"] = "completed"
                task["completed_at"] = utc_now().isoformat()
                task["progress_percentage"] = 100

    async def _suspend_service(self, instance_id: str, **kwargs):
        """Suspend service."""
        instance = self._service_instances[instance_id]

        # Add suspension details
        instance["suspension_reason"] = kwargs.get(
            "suspension_reason", "Administrative action"
        )
        instance["suspension_type"] = kwargs.get(
            "suspension_type", "manual"
        )  # manual, automatic, billing
        instance["auto_resume_at"] = kwargs.get("auto_resume_at")

    async def _terminate_service(self, instance_id: str, **kwargs):
        """Terminate service."""
        instance = self._service_instances[instance_id]

        # Add termination details
        instance["termination_reason"] = kwargs.get(
            "termination_reason", "Customer request"
        )
        instance["termination_type"] = kwargs.get(
            "termination_type", "normal"
        )  # normal, forced, billing
        instance["data_retention_until"] = kwargs.get("data_retention_until")

    async def update_provisioning_progress(
        self,
        instance_id: str,
        progress_percentage: int,
        current_step: str,
        completed_steps: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Update provisioning progress."""
        if instance_id not in self._service_instances:
            raise ServiceNotFoundError(f"Service instance not found: {instance_id}")

        instance = self._service_instances[instance_id]

        if "provisioning_task_id" not in instance:
            raise ProvisioningError("No active provisioning task found")

        task_id = instance["provisioning_task_id"]
        if task_id not in self._provisioning_tasks:
            raise ProvisioningError("Provisioning task not found")

        task = self._provisioning_tasks[task_id]
        task["progress_percentage"] = progress_percentage
        task["current_step"] = current_step
        task["updated_at"] = utc_now().isoformat()

        if completed_steps:
            task["completed_steps"].extend(completed_steps)

        # Auto-transition to active if provisioning is complete
        if (
            progress_percentage >= 100
            and instance["state"] == ServiceState.PROVISIONING.value
        ):
            await self.transition_service_state(
                instance_id,
                ServiceState.ACTIVE.value,
                "Provisioning completed successfully",
                "system",
            )

        return {
            "task_id": task_id,
            "progress_percentage": progress_percentage,
            "current_step": current_step,
            "updated_at": task["updated_at"],
        }

    async def retry_failed_provisioning(self, instance_id: str) -> Dict[str, Any]:
        """Retry failed provisioning."""
        if instance_id not in self._service_instances:
            raise ServiceNotFoundError(f"Service instance not found: {instance_id}")

        instance = self._service_instances[instance_id]

        if instance["state"] != ServiceState.FAILED.value:
            raise ServiceStateError("Service is not in failed state")

        if instance["retry_count"] >= instance["max_retries"]:
            raise ProvisioningError("Maximum retry attempts exceeded")

        # Increment retry count
        instance["retry_count"] += 1

        # Transition back to provisioning
        await self.transition_service_state(
            instance_id,
            ServiceState.PROVISIONING.value,
            f"Retry attempt {instance['retry_count']}",
            "system",
        )

        return {
            "instance_id": instance_id,
            "retry_count": instance["retry_count"],
            "max_retries": instance["max_retries"],
            "new_state": ServiceState.PROVISIONING.value,
        }


class ServiceManagementSDK:
    """Minimal, reusable SDK for service lifecycle management."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._service = ServiceManagementService()

    async def create_service_instance(
        self,
        customer_id: str,
        service_plan_id: str,
        service_name: Optional[str] = None,
        configuration: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create service instance."""
        instance = await self._service.create_service_instance(
            customer_id=customer_id,
            service_plan_id=service_plan_id,
            service_name=service_name,
            configuration=configuration or {},
            tenant_id=self.tenant_id,
            **kwargs,
        )

        return {
            "instance_id": instance["instance_id"],
            "customer_id": instance["customer_id"],
            "service_plan_id": instance["service_plan_id"],
            "service_name": instance["service_name"],
            "state": instance["state"],
            "state_reason": instance["state_reason"],
            "created_at": instance["created_at"],
            "configuration": instance["configuration"],
        }

    async def start_provisioning(
        self,
        instance_id: str,
        provisioning_steps: Optional[List[str]] = None,
        triggered_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Start service provisioning."""
        result = await self._service.transition_service_state(
            instance_id=instance_id,
            target_state=ServiceState.PROVISIONING.value,
            reason="Starting service provisioning",
            triggered_by=triggered_by,
            provisioning_steps=provisioning_steps,
        )

        return {
            "instance_id": result["instance_id"],
            "state_transition": {
                "from": result["old_state"],
                "to": result["new_state"],
                "timestamp": result["transition_time"],
                "reason": result["reason"],
            },
        }

    async def activate_service(
        self, instance_id: str, triggered_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """Activate service."""
        result = await self._service.transition_service_state(
            instance_id=instance_id,
            target_state=ServiceState.ACTIVE.value,
            reason="Service activated",
            triggered_by=triggered_by,
        )

        return {
            "instance_id": result["instance_id"],
            "state_transition": {
                "from": result["old_state"],
                "to": result["new_state"],
                "timestamp": result["transition_time"],
                "reason": result["reason"],
            },
        }

    async def suspend_service(
        self,
        instance_id: str,
        suspension_reason: str,
        suspension_type: str = "manual",
        auto_resume_at: Optional[str] = None,
        triggered_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Suspend service."""
        result = await self._service.transition_service_state(
            instance_id=instance_id,
            target_state=ServiceState.SUSPENDED.value,
            reason=suspension_reason,
            triggered_by=triggered_by,
            suspension_reason=suspension_reason,
            suspension_type=suspension_type,
            auto_resume_at=auto_resume_at,
        )

        return {
            "instance_id": result["instance_id"],
            "state_transition": {
                "from": result["old_state"],
                "to": result["new_state"],
                "timestamp": result["transition_time"],
                "reason": result["reason"],
            },
            "suspension_details": {
                "reason": suspension_reason,
                "type": suspension_type,
                "auto_resume_at": auto_resume_at,
            },
        }

    async def resume_service(
        self, instance_id: str, triggered_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """Resume suspended service."""
        result = await self._service.transition_service_state(
            instance_id=instance_id,
            target_state=ServiceState.ACTIVE.value,
            reason="Service resumed",
            triggered_by=triggered_by,
        )

        return {
            "instance_id": result["instance_id"],
            "state_transition": {
                "from": result["old_state"],
                "to": result["new_state"],
                "timestamp": result["transition_time"],
                "reason": result["reason"],
            },
        }

    async def terminate_service(
        self,
        instance_id: str,
        termination_reason: str,
        termination_type: str = "normal",
        data_retention_until: Optional[str] = None,
        triggered_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Terminate service."""
        result = await self._service.transition_service_state(
            instance_id=instance_id,
            target_state=ServiceState.TERMINATED.value,
            reason=termination_reason,
            triggered_by=triggered_by,
            termination_reason=termination_reason,
            termination_type=termination_type,
            data_retention_until=data_retention_until,
        )

        return {
            "instance_id": result["instance_id"],
            "state_transition": {
                "from": result["old_state"],
                "to": result["new_state"],
                "timestamp": result["transition_time"],
                "reason": result["reason"],
            },
            "termination_details": {
                "reason": termination_reason,
                "type": termination_type,
                "data_retention_until": data_retention_until,
            },
        }

    async def update_provisioning_progress(
        self,
        instance_id: str,
        progress_percentage: int,
        current_step: str,
        completed_steps: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Update provisioning progress."""
        result = await self._service.update_provisioning_progress(
            instance_id=instance_id,
            progress_percentage=progress_percentage,
            current_step=current_step,
            completed_steps=completed_steps,
        )

        return {
            "instance_id": instance_id,
            "provisioning_progress": {
                "percentage": progress_percentage,
                "current_step": current_step,
                "completed_steps": completed_steps or [],
                "updated_at": result["updated_at"],
            },
        }

    async def get_service_instance(self, instance_id: str) -> Dict[str, Any]:
        """Get service instance details."""
        if instance_id not in self._service._service_instances:
            raise ServiceNotFoundError(f"Service instance not found: {instance_id}")

        instance = self._service._service_instances[instance_id]

        # Get provisioning task if exists
        provisioning_task = None
        if "provisioning_task_id" in instance:
            task_id = instance["provisioning_task_id"]
            if task_id in self._service._provisioning_tasks:
                task = self._service._provisioning_tasks[task_id]
                provisioning_task = {
                    "task_id": task["task_id"],
                    "status": task["status"],
                    "progress_percentage": task["progress_percentage"],
                    "current_step": task["current_step"],
                    "started_at": task["started_at"],
                    "estimated_completion": task["estimated_completion"],
                }

        return {
            "instance_id": instance["instance_id"],
            "customer_id": instance["customer_id"],
            "service_plan_id": instance["service_plan_id"],
            "bundle_id": instance["bundle_id"],
            "addon_ids": instance["addon_ids"],
            "service_name": instance["service_name"],
            "state": instance["state"],
            "state_reason": instance["state_reason"],
            "configuration": instance["configuration"],
            "metadata": instance["metadata"],
            "timestamps": {
                "created_at": instance["created_at"],
                "updated_at": instance["updated_at"],
                "activated_at": instance["activated_at"],
                "suspended_at": instance["suspended_at"],
                "terminated_at": instance["terminated_at"],
                "last_state_change": instance["last_state_change"],
            },
            "provisioning_task": provisioning_task,
            "retry_info": {
                "retry_count": instance["retry_count"],
                "max_retries": instance["max_retries"],
                "auto_retry": instance["auto_retry"],
            },
        }

    async def get_state_history(self, instance_id: str) -> List[Dict[str, Any]]:
        """Get service state transition history."""
        if instance_id not in self._service._state_transitions:
            raise ServiceNotFoundError(f"Service instance not found: {instance_id}")

        transitions = self._service._state_transitions[instance_id]

        return [
            {
                "transition_id": t["transition_id"],
                "from_state": t["from_state"],
                "to_state": t["to_state"],
                "reason": t["reason"],
                "triggered_by": t["triggered_by"],
                "timestamp": t["timestamp"],
            }
            for t in transitions
        ]

    async def list_services_by_state(
        self, state: str, customer_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List services by state."""
        services = []

        for instance in self._service._service_instances.values():
            if instance["state"] != state:
                continue

            if customer_id and instance["customer_id"] != customer_id:
                continue

            services.append(
                {
                    "instance_id": instance["instance_id"],
                    "customer_id": instance["customer_id"],
                    "service_plan_id": instance["service_plan_id"],
                    "service_name": instance["service_name"],
                    "state": instance["state"],
                    "state_reason": instance["state_reason"],
                    "last_state_change": instance["last_state_change"],
                }
            )

        return sorted(services, key=lambda s: s["last_state_change"], reverse=True)

    async def retry_failed_service(self, instance_id: str) -> Dict[str, Any]:
        """Retry failed service provisioning."""
        result = await self._service.retry_failed_provisioning(instance_id)

        return {
            "instance_id": result["instance_id"],
            "retry_attempt": result["retry_count"],
            "max_retries": result["max_retries"],
            "new_state": result["new_state"],
            "retried_at": utc_now().isoformat(),
        }
