"""
Device Provisioning SDK - thin orchestration activities used by Ops workflows
"""

from datetime import datetime
from dotmac_networking.core.datetime_utils import utc_now, utc_now_iso
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..core.exceptions import NetworkingError


class DeviceProvisioningService:
    """In-memory service for device provisioning operations."""

    def __init__(self):
        self._provisioning_tasks: Dict[str, Dict[str, Any]] = {}
        self._workflows: Dict[str, Dict[str, Any]] = {}
        self._activities: Dict[str, Dict[str, Any]] = {}
        self._device_states: Dict[str, Dict[str, Any]] = {}

    async def create_provisioning_workflow(self, **kwargs) -> Dict[str, Any]:
        """Create device provisioning workflow."""
        workflow_id = kwargs.get("workflow_id") or str(uuid4())

        workflow = {
            "workflow_id": workflow_id,
            "workflow_name": kwargs["workflow_name"],
            "workflow_type": kwargs.get("workflow_type", "device_provisioning"),
            "device_id": kwargs.get("device_id"),
            "customer_id": kwargs.get("customer_id"),
            "service_profile": kwargs.get("service_profile", {}),
            "activities": kwargs.get("activities", []),
            "status": "pending",
            "created_at": utc_now().isoformat(),
            "created_by": kwargs.get("created_by", "system"),
            "current_activity": 0,
            "retry_count": 0,
            "max_retries": kwargs.get("max_retries", 3),
        }

        self._workflows[workflow_id] = workflow
        return workflow

    async def execute_activity(self, workflow_id: str, activity_name: str, **kwargs) -> Dict[str, Any]:
        """Execute provisioning activity."""
        if workflow_id not in self._workflows:
            raise NetworkingError(f"Workflow not found: {workflow_id}")

        activity_id = str(uuid4())
        activity = {
            "activity_id": activity_id,
            "workflow_id": workflow_id,
            "activity_name": activity_name,
            "activity_type": kwargs.get("activity_type", "generic"),
            "parameters": kwargs.get("parameters", {}),
            "status": "running",
            "started_at": utc_now().isoformat(),
            "output": {},
            "error": None,
        }

        self._activities[activity_id] = activity

        # Simulate activity execution based on type
        try:
            if activity_name == "allocate_ip":
                activity["output"] = await self._allocate_ip_activity(**kwargs.get("parameters", {}))
            elif activity_name == "assign_vlan":
                activity["output"] = await self._assign_vlan_activity(**kwargs.get("parameters", {}))
            elif activity_name == "configure_device":
                activity["output"] = await self._configure_device_activity(**kwargs.get("parameters", {}))
            elif activity_name == "update_radius":
                activity["output"] = await self._update_radius_activity(**kwargs.get("parameters", {}))
            elif activity_name == "validate_connectivity":
                activity["output"] = await self._validate_connectivity_activity(**kwargs.get("parameters", {}))
            else:
                activity["output"] = {"message": f"Activity {activity_name} completed"}

            activity["status"] = "completed"
            activity["finished_at"] = utc_now().isoformat()

        except Exception as e:
            activity["status"] = "failed"
            activity["error"] = str(e)
            activity["finished_at"] = utc_now().isoformat()

        return activity

    async def _allocate_ip_activity(self, **params) -> Dict[str, Any]:
        """Simulate IP allocation activity."""
        network_id = params.get("network_id", "default")
        return {
            "ip_address": "192.168.1.100",
            "network_id": network_id,
            "allocation_id": str(uuid4()),
        }

    async def _assign_vlan_activity(self, **params) -> Dict[str, Any]:
        """Simulate VLAN assignment activity."""
        vlan_id = params.get("vlan_id", 100)
        port_id = params.get("port_id", "unknown")
        return {
            "vlan_id": vlan_id,
            "port_id": port_id,
            "assignment_id": str(uuid4()),
        }

    async def _configure_device_activity(self, **params) -> Dict[str, Any]:
        """Simulate device configuration activity."""
        device_id = params.get("device_id", "unknown")
        config_template = params.get("config_template", "default")
        return {
            "device_id": device_id,
            "config_template": config_template,
            "config_id": str(uuid4()),
        }

    async def _update_radius_activity(self, **params) -> Dict[str, Any]:
        """Simulate RADIUS update activity."""
        username = params.get("username", "user")
        return {
            "username": username,
            "radius_updated": True,
            "policy_id": str(uuid4()),
        }

    async def _validate_connectivity_activity(self, **params) -> Dict[str, Any]:
        """Simulate connectivity validation activity."""
        device_id = params.get("device_id", "unknown")
        return {
            "device_id": device_id,
            "connectivity_status": "validated",
            "ping_result": True,
        }

    async def execute_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Execute complete provisioning workflow."""
        if workflow_id not in self._workflows:
            raise NetworkingError(f"Workflow not found: {workflow_id}")

        workflow = self._workflows[workflow_id]
        workflow["status"] = "running"
        workflow["started_at"] = utc_now().isoformat()

        results = []

        try:
            for activity_config in workflow["activities"]:
                activity_result = await self.execute_activity(
                    workflow_id=workflow_id,
                    activity_name=activity_config["name"],
                    activity_type=activity_config.get("type", "generic"),
                    parameters=activity_config.get("parameters", {})
                )

                results.append(activity_result)

                if activity_result["status"] == "failed":
                    workflow["status"] = "failed"
                    workflow["error"] = f"Activity {activity_config['name']} failed: {activity_result['error']}"
                    break

            if workflow["status"] != "failed":
                workflow["status"] = "completed"

            workflow["finished_at"] = utc_now().isoformat()
            workflow["results"] = results

        except Exception as e:
            workflow["status"] = "failed"
            workflow["error"] = str(e)
            workflow["finished_at"] = utc_now().isoformat()

        return workflow


class DeviceProvisioningSDK:
    """Minimal, reusable SDK for device provisioning orchestration."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._service = DeviceProvisioningService()

    async def create_device_provisioning_workflow(
        self,
        workflow_name: str,
        device_id: str,
        customer_id: Optional[str] = None,
        service_profile: Optional[Dict[str, Any]] = None,
        activities: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create device provisioning workflow."""
        default_activities = [
            {"name": "allocate_ip", "type": "ipam", "parameters": {"network_id": "customer_network"}},
            {"name": "assign_vlan", "type": "vlan", "parameters": {"vlan_id": 100}},
            {"name": "configure_device", "type": "config", "parameters": {"device_id": device_id}},
            {"name": "update_radius", "type": "radius", "parameters": {"username": customer_id}},
            {"name": "validate_connectivity", "type": "validation", "parameters": {"device_id": device_id}},
        ]

        workflow = await self._service.create_provisioning_workflow(
            workflow_name=workflow_name,
            device_id=device_id,
            customer_id=customer_id,
            service_profile=service_profile or {},
            activities=activities or default_activities,
            tenant_id=self.tenant_id,
            **kwargs
        )

        return {
            "workflow_id": workflow["workflow_id"],
            "workflow_name": workflow["workflow_name"],
            "workflow_type": workflow["workflow_type"],
            "device_id": workflow["device_id"],
            "customer_id": workflow["customer_id"],
            "service_profile": workflow["service_profile"],
            "activities": workflow["activities"],
            "status": workflow["status"],
            "created_at": workflow["created_at"],
            "created_by": workflow["created_by"],
        }

    async def execute_provisioning_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Execute complete provisioning workflow."""
        workflow = await self._service.execute_workflow(workflow_id)

        return {
            "workflow_id": workflow["workflow_id"],
            "workflow_name": workflow["workflow_name"],
            "device_id": workflow["device_id"],
            "customer_id": workflow["customer_id"],
            "status": workflow["status"],
            "started_at": workflow.get("started_at"),
            "finished_at": workflow.get("finished_at"),
            "results": workflow.get("results", []),
            "error": workflow.get("error"),
        }

    async def execute_single_activity(
        self,
        workflow_id: str,
        activity_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute single provisioning activity."""
        activity = await self._service.execute_activity(
            workflow_id=workflow_id,
            activity_name=activity_name,
            parameters=parameters or {},
            **kwargs
        )

        return {
            "activity_id": activity["activity_id"],
            "workflow_id": activity["workflow_id"],
            "activity_name": activity["activity_name"],
            "activity_type": activity["activity_type"],
            "status": activity["status"],
            "started_at": activity["started_at"],
            "finished_at": activity.get("finished_at"),
            "output": activity["output"],
            "error": activity["error"],
        }

    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get provisioning workflow status."""
        workflow = self._service._workflows.get(workflow_id)
        if not workflow:
            raise NetworkingError(f"Workflow not found: {workflow_id}")

        return {
            "workflow_id": workflow["workflow_id"],
            "workflow_name": workflow["workflow_name"],
            "device_id": workflow["device_id"],
            "customer_id": workflow["customer_id"],
            "status": workflow["status"],
            "current_activity": workflow["current_activity"],
            "retry_count": workflow["retry_count"],
            "created_at": workflow["created_at"],
            "started_at": workflow.get("started_at"),
            "finished_at": workflow.get("finished_at"),
            "error": workflow.get("error"),
        }

    async def retry_failed_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Retry failed provisioning workflow."""
        workflow = self._service._workflows.get(workflow_id)
        if not workflow:
            raise NetworkingError(f"Workflow not found: {workflow_id}")

        if workflow["status"] != "failed":
            raise NetworkingError(f"Cannot retry workflow in status: {workflow['status']}")

        if workflow["retry_count"] >= workflow["max_retries"]:
            raise NetworkingError(f"Maximum retries exceeded for workflow: {workflow_id}")

        workflow["retry_count"] += 1
        workflow["status"] = "pending"
        workflow["error"] = None

        return await self.execute_provisioning_workflow(workflow_id)

    async def cancel_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Cancel running provisioning workflow."""
        workflow = self._service._workflows.get(workflow_id)
        if not workflow:
            raise NetworkingError(f"Workflow not found: {workflow_id}")

        if workflow["status"] not in ["running", "pending"]:
            raise NetworkingError(f"Cannot cancel workflow in status: {workflow['status']}")

        workflow["status"] = "cancelled"
        workflow["finished_at"] = utc_now().isoformat()

        return {
            "workflow_id": workflow_id,
            "status": "cancelled",
            "cancelled_at": workflow["finished_at"],
        }

    async def list_workflows(
        self,
        device_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List provisioning workflows."""
        workflows = list(self._service._workflows.values())

        if device_id:
            workflows = [w for w in workflows if w.get("device_id") == device_id]

        if customer_id:
            workflows = [w for w in workflows if w.get("customer_id") == customer_id]

        if status:
            workflows = [w for w in workflows if w["status"] == status]

        return [
            {
                "workflow_id": workflow["workflow_id"],
                "workflow_name": workflow["workflow_name"],
                "device_id": workflow["device_id"],
                "customer_id": workflow["customer_id"],
                "status": workflow["status"],
                "created_at": workflow["created_at"],
                "finished_at": workflow.get("finished_at"),
            }
            for workflow in sorted(workflows, key=lambda w: w["created_at"], reverse=True)
        ]

    async def create_service_activation_workflow(
        self,
        customer_id: str,
        service_type: str,
        device_id: str,
        service_parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create service activation workflow."""
        activities = [
            {
                "name": "allocate_ip",
                "type": "ipam",
                "parameters": {
                    "network_id": service_parameters.get("network_id", "customer_network"),
                    "customer_id": customer_id
                }
            },
            {
                "name": "assign_vlan",
                "type": "vlan",
                "parameters": {
                    "vlan_id": service_parameters.get("vlan_id"),
                    "port_id": service_parameters.get("port_id")
                }
            },
            {
                "name": "configure_device",
                "type": "config",
                "parameters": {
                    "device_id": device_id,
                    "service_profile": service_parameters.get("service_profile", {}),
                    "bandwidth": service_parameters.get("bandwidth")
                }
            },
            {
                "name": "update_radius",
                "type": "radius",
                "parameters": {
                    "username": customer_id,
                    "service_type": service_type,
                    "bandwidth_profile": service_parameters.get("bandwidth_profile")
                }
            },
            {
                "name": "validate_connectivity",
                "type": "validation",
                "parameters": {
                    "device_id": device_id,
                    "customer_id": customer_id,
                    "service_type": service_type
                }
            }
        ]

        return await self.create_device_provisioning_workflow(
            workflow_name=f"Service Activation - {customer_id}",
            device_id=device_id,
            customer_id=customer_id,
            service_profile=service_parameters,
            activities=activities
        )
