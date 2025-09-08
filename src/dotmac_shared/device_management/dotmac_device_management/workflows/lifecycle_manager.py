"""
Device Lifecycle Management workflows.

Handles complete device lifecycle from provisioning to decommissioning.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from sqlalchemy.orm import Session

from ..core.device_inventory import DeviceInventoryService
from ..core.device_monitoring import DeviceMonitoringService
from ..core.mac_registry import MacRegistryService
from ..core.models import DeviceStatus, DeviceType
from ..core.network_topology import NetworkTopologyService
from ..exceptions import DeviceLifecycleError


class LifecycleStage(str, Enum):
    """Device lifecycle stages."""

    PLANNING = "planning"
    PROVISIONING = "provisioning"
    DEPLOYMENT = "deployment"
    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    UPGRADE = "upgrade"
    MIGRATION = "migration"
    DECOMMISSIONING = "decommissioning"
    RETIRED = "retired"


class LifecycleAction(str, Enum):
    """Lifecycle actions."""

    PROVISION = "provision"
    DEPLOY = "deploy"
    ACTIVATE = "activate"
    MAINTAIN = "maintain"
    UPGRADE = "upgrade"
    MIGRATE = "migrate"
    DECOMMISSION = "decommission"
    RETIRE = "retire"


class DeviceLifecycleManager:
    """Manages complete device lifecycle workflows."""

    def __init__(self, session: Session, tenant_id: str):
        """Initialize lifecycle manager."""
        self.session = session
        self.tenant_id = tenant_id

        # Initialize service dependencies
        self.inventory_service = DeviceInventoryService(session, tenant_id)
        self.monitoring_service = DeviceMonitoringService(session, tenant_id)
        self.mac_service = MacRegistryService(session, tenant_id)
        self.topology_service = NetworkTopologyService(session, tenant_id)

        # Lifecycle workflows
        self.lifecycle_workflows = {
            LifecycleStage.PLANNING: self._handle_planning,
            LifecycleStage.PROVISIONING: self._handle_provisioning,
            LifecycleStage.DEPLOYMENT: self._handle_deployment,
            LifecycleStage.ACTIVE: self._handle_active,
            LifecycleStage.MAINTENANCE: self._handle_maintenance,
            LifecycleStage.UPGRADE: self._handle_upgrade,
            LifecycleStage.MIGRATION: self._handle_migration,
            LifecycleStage.DECOMMISSIONING: self._handle_decommissioning,
            LifecycleStage.RETIRED: self._handle_retired,
        }

    async def execute_lifecycle_action(
        self, device_id: str, action: str, parameters: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Execute a lifecycle action on a device."""
        try:
            action_enum = LifecycleAction(action)
        except ValueError as e:
            raise DeviceLifecycleError(f"Invalid lifecycle action: {action}") from e

        parameters = parameters or {}

        # Get current device state
        device = await self.inventory_service.manager.get_device(device_id)
        if not device:
            raise DeviceLifecycleError(f"Device not found: {device_id}")

        # Execute action based on type
        if action_enum == LifecycleAction.PROVISION:
            return await self._execute_provision(device_id, parameters)
        elif action_enum == LifecycleAction.DEPLOY:
            return await self._execute_deploy(device_id, parameters)
        elif action_enum == LifecycleAction.ACTIVATE:
            return await self._execute_activate(device_id, parameters)
        elif action_enum == LifecycleAction.MAINTAIN:
            return await self._execute_maintenance(device_id, parameters)
        elif action_enum == LifecycleAction.UPGRADE:
            return await self._execute_upgrade(device_id, parameters)
        elif action_enum == LifecycleAction.MIGRATE:
            return await self._execute_migrate(device_id, parameters)
        elif action_enum == LifecycleAction.DECOMMISSION:
            return await self._execute_decommission(device_id, parameters)
        elif action_enum == LifecycleAction.RETIRE:
            return await self._execute_retire(device_id, parameters)
        else:
            raise DeviceLifecycleError(f"Action not implemented: {action}")

    async def _execute_provision(self, device_id: str, parameters: dict[str, Any]) -> dict[str, Any]:
        """Execute device provisioning workflow."""
        workflow_id = str(uuid.uuid4())
        start_time = datetime.now(timezone.utc)

        try:
            # Create device record
            device_result = await self.inventory_service.provision_device(
                device_id=device_id,
                hostname=parameters["hostname"],
                device_type=parameters.get("device_type", DeviceType.UNKNOWN),
                site_id=parameters["site_id"],
                vendor=parameters.get("vendor"),
                model=parameters.get("model"),
                serial_number=parameters.get("serial_number"),
                management_ip=parameters.get("management_ip"),
                interfaces=parameters.get("interfaces", []),
                modules=parameters.get("modules", []),
            )

            # Register device in topology if location provided
            if parameters.get("x_coordinate") and parameters.get("y_coordinate"):
                await self.topology_service.manager.create_node(
                    node_id=device_id,
                    node_type="device",
                    name=parameters["hostname"],
                    device_id=device_id,
                    site_id=parameters["site_id"],
                    x_coordinate=parameters.get("x_coordinate"),
                    y_coordinate=parameters.get("y_coordinate"),
                )

            # Set up basic monitoring if monitoring config provided
            if parameters.get("enable_monitoring", True):
                await self.monitoring_service.create_snmp_monitor(
                    device_id=device_id,
                    metrics=parameters.get("monitoring_metrics", ["system", "interfaces"]),
                    collection_interval=parameters.get("monitoring_interval", 60),
                    snmp_community=parameters.get("snmp_community", "public"),
                )

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()

            return {
                "workflow_id": workflow_id,
                "action": "provision",
                "device_id": device_id,
                "status": "completed",
                "duration_seconds": duration,
                "result": device_result,
                "next_recommended_action": "deploy",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            # Update device status to failed
            await self.inventory_service.manager.update_device(device_id, {"status": DeviceStatus.FAILED})

            return {
                "workflow_id": workflow_id,
                "action": "provision",
                "device_id": device_id,
                "status": "failed",
                "error": str(e),
                "duration_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
                "failed_at": datetime.now(timezone.utc).isoformat(),
            }

    async def _execute_deploy(self, device_id: str, parameters: dict[str, Any]) -> dict[str, Any]:
        """Execute device deployment workflow."""
        workflow_id = str(uuid.uuid4())
        start_time = datetime.now(timezone.utc)

        try:
            # Update device status
            await self.inventory_service.manager.update_device(device_id, {"status": DeviceStatus.PROVISIONING})

            # Discover and register MAC addresses if interfaces provided
            if parameters.get("interface_macs"):
                await self.mac_service.discover_device_macs(
                    device_id=device_id, interface_macs=parameters["interface_macs"]
                )

            # Create topology connections if specified
            connections = parameters.get("connections", [])
            topology_results = []
            for connection in connections:
                try:
                    link_result = await self.topology_service.manager.create_link(
                        link_id=f"{device_id}_{connection['target_device']}_{uuid.uuid4().hex[:8]}",
                        source_node_id=device_id,
                        target_node_id=connection["target_device"],
                        source_port=connection.get("source_port"),
                        target_port=connection.get("target_port"),
                        link_type=connection.get("link_type", "physical"),
                        bandwidth=connection.get("bandwidth"),
                    )
                    topology_results.append(link_result.link_id)
                except Exception as e:
                    topology_results.append({"error": str(e)})

            # Run deployment validation
            validation_results = await self._validate_deployment(device_id, parameters)

            if validation_results["valid"]:
                # Update status to active
                await self.inventory_service.manager.update_device(device_id, {"status": DeviceStatus.ACTIVE})
                final_status = "completed"
                next_action = "activate"
            else:
                final_status = "validation_failed"
                next_action = "troubleshoot"

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()

            return {
                "workflow_id": workflow_id,
                "action": "deploy",
                "device_id": device_id,
                "status": final_status,
                "duration_seconds": duration,
                "validation_results": validation_results,
                "topology_connections": len(topology_results),
                "next_recommended_action": next_action,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            await self.inventory_service.manager.update_device(device_id, {"status": DeviceStatus.FAILED})

            return {
                "workflow_id": workflow_id,
                "action": "deploy",
                "device_id": device_id,
                "status": "failed",
                "error": str(e),
                "duration_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
                "failed_at": datetime.now(timezone.utc).isoformat(),
            }

    async def _execute_activate(self, device_id: str, parameters: dict[str, Any]) -> dict[str, Any]:
        """Execute device activation workflow."""
        workflow_id = str(uuid.uuid4())
        start_time = datetime.now(timezone.utc)

        try:
            # Verify device is ready for activation
            device = await self.inventory_service.manager.get_device(device_id)
            if device.status not in [DeviceStatus.PROVISIONING, DeviceStatus.ACTIVE]:
                raise DeviceLifecycleError(f"Device not ready for activation: {device.status}")

            # Start monitoring
            if parameters.get("start_monitoring", True):
                await self.monitoring_service.create_health_check(
                    device_id=device_id,
                    check_type="ping",
                    target=device.management_ip or device_id,
                )

            # Run connectivity tests
            connectivity_results = await self._test_device_connectivity(device_id, parameters)

            # Update device status
            if connectivity_results["reachable"]:
                await self.inventory_service.manager.update_device(
                    device_id,
                    {
                        "status": DeviceStatus.ACTIVE,
                        "install_date": datetime.now(timezone.utc),
                    },
                )
                final_status = "completed"
                next_action = "monitor"
            else:
                final_status = "connectivity_failed"
                next_action = "troubleshoot"

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()

            return {
                "workflow_id": workflow_id,
                "action": "activate",
                "device_id": device_id,
                "status": final_status,
                "duration_seconds": duration,
                "connectivity_results": connectivity_results,
                "next_recommended_action": next_action,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            return {
                "workflow_id": workflow_id,
                "action": "activate",
                "device_id": device_id,
                "status": "failed",
                "error": str(e),
                "duration_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
                "failed_at": datetime.now(timezone.utc).isoformat(),
            }

    async def _execute_maintenance(self, device_id: str, parameters: dict[str, Any]) -> dict[str, Any]:
        """Execute device maintenance workflow."""
        workflow_id = str(uuid.uuid4())
        start_time = datetime.now(timezone.utc)

        try:
            # Update status to maintenance
            await self.inventory_service.manager.update_device(device_id, {"status": DeviceStatus.MAINTENANCE})

            maintenance_type = parameters.get("maintenance_type", "routine")
            maintenance_tasks = parameters.get("tasks", [])

            # Execute maintenance tasks
            task_results = []
            for task in maintenance_tasks:
                task_result = await self._execute_maintenance_task(device_id, task)
                task_results.append(task_result)

            # Post-maintenance validation
            validation_results = await self._validate_device_health(device_id)

            # Update status based on validation
            if validation_results["healthy"]:
                await self.inventory_service.manager.update_device(device_id, {"status": DeviceStatus.ACTIVE})
                final_status = "completed"
            else:
                final_status = "validation_failed"

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()

            return {
                "workflow_id": workflow_id,
                "action": "maintain",
                "device_id": device_id,
                "status": final_status,
                "maintenance_type": maintenance_type,
                "tasks_completed": len([r for r in task_results if r.get("status") == "success"]),
                "tasks_failed": len([r for r in task_results if r.get("status") == "failed"]),
                "validation_results": validation_results,
                "duration_seconds": duration,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            # Restore device status
            await self.inventory_service.manager.update_device(device_id, {"status": DeviceStatus.ACTIVE})

            return {
                "workflow_id": workflow_id,
                "action": "maintain",
                "device_id": device_id,
                "status": "failed",
                "error": str(e),
                "duration_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
                "failed_at": datetime.now(timezone.utc).isoformat(),
            }

    async def _execute_decommission(self, device_id: str, parameters: dict[str, Any]) -> dict[str, Any]:
        """Execute device decommissioning workflow."""
        workflow_id = str(uuid.uuid4())
        start_time = datetime.now(timezone.utc)

        try:
            # Update status to decommissioning
            await self.inventory_service.manager.update_device(device_id, {"status": DeviceStatus.DECOMMISSIONING})

            # Remove from monitoring
            # Note: In a real implementation, this would disable monitoring

            # Remove topology connections
            topology_node = await self.topology_service.manager.get_node(device_id)
            if topology_node:
                removed_links = await self.topology_service.manager.get_node_links(device_id)
                await self.topology_service.manager.delete_node(device_id)

            # Clean up MAC address registrations if requested
            if parameters.get("cleanup_mac_addresses", True):
                device_macs = await self.mac_service.manager.get_device_mac_addresses(device_id)
                for mac_record in device_macs:
                    await self.mac_service.manager.update_mac_address(
                        mac_record.mac_address,
                        {
                            "device_id": None,
                            "interface_name": None,
                            "status": "inactive",
                        },
                    )

            # Final status update
            if parameters.get("archive_device", True):
                await self.inventory_service.manager.update_device(device_id, {"status": DeviceStatus.DECOMMISSIONED})
                final_status = "decommissioned"
            else:
                await self.inventory_service.manager.delete_device(device_id)
                final_status = "deleted"

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()

            return {
                "workflow_id": workflow_id,
                "action": "decommission",
                "device_id": device_id,
                "status": final_status,
                "removed_topology_links": (len(removed_links) if "removed_links" in locals() else 0),
                "duration_seconds": duration,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            return {
                "workflow_id": workflow_id,
                "action": "decommission",
                "device_id": device_id,
                "status": "failed",
                "error": str(e),
                "duration_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
                "failed_at": datetime.now(timezone.utc).isoformat(),
            }

    async def _execute_upgrade(self, device_id: str, parameters: dict[str, Any]) -> dict[str, Any]:
        """Execute device upgrade workflow."""
        # Implementation would handle firmware upgrades, configuration updates, etc.
        return {
            "workflow_id": str(uuid.uuid4()),
            "action": "upgrade",
            "device_id": device_id,
            "status": "not_implemented",
            "message": "Upgrade workflow not yet implemented",
        }

    async def _execute_migrate(self, device_id: str, parameters: dict[str, Any]) -> dict[str, Any]:
        """Execute device migration workflow."""
        # Implementation would handle device migrations between sites/racks
        return {
            "workflow_id": str(uuid.uuid4()),
            "action": "migrate",
            "device_id": device_id,
            "status": "not_implemented",
            "message": "Migration workflow not yet implemented",
        }

    async def _execute_retire(self, device_id: str, parameters: dict[str, Any]) -> dict[str, Any]:
        """Execute device retirement workflow."""
        # Implementation would handle final retirement and archival
        return {
            "workflow_id": str(uuid.uuid4()),
            "action": "retire",
            "device_id": device_id,
            "status": "not_implemented",
            "message": "Retirement workflow not yet implemented",
        }

    # Helper methods
    async def _validate_deployment(self, device_id: str, parameters: dict[str, Any]) -> dict[str, Any]:
        """Validate device deployment."""
        validation_results = {"valid": True, "checks": {}, "errors": []}

        # Check device exists
        device = await self.inventory_service.manager.get_device(device_id)
        validation_results["checks"]["device_exists"] = device is not None

        if not device:
            validation_results["valid"] = False
            validation_results["errors"].append("Device not found")
            return validation_results

        # Check required fields
        required_fields = ["hostname", "device_type", "site_id"]
        for field in required_fields:
            has_field = getattr(device, field) is not None
            validation_results["checks"][f"has_{field}"] = has_field
            if not has_field:
                validation_results["valid"] = False
                validation_results["errors"].append(f"Missing required field: {field}")

        # Check interfaces if specified
        if parameters.get("required_interfaces"):
            interfaces = await self.inventory_service.manager.get_device_interfaces(device_id)
            interface_count = len(interfaces)
            required_count = parameters["required_interfaces"]

            validation_results["checks"]["sufficient_interfaces"] = interface_count >= required_count
            if interface_count < required_count:
                validation_results["valid"] = False
                validation_results["errors"].append(f"Insufficient interfaces: {interface_count} < {required_count}")

        return validation_results

    async def _test_device_connectivity(self, device_id: str, parameters: dict[str, Any]) -> dict[str, Any]:
        """Test device connectivity."""
        device = await self.inventory_service.manager.get_device(device_id)

        connectivity_results = {
            "reachable": False,
            "tests": {},
            "response_time_ms": None,
        }

        # Simulate connectivity test
        # In real implementation, this would ping the device, test SNMP, etc.
        if device and device.management_ip:
            # Mock positive result for devices with management IP
            connectivity_results["reachable"] = True
            connectivity_results["tests"]["ping"] = {
                "status": "success",
                "response_time_ms": 5.2,
            }
            connectivity_results["tests"]["snmp"] = {
                "status": "success",
                "community": "public",
            }
            connectivity_results["response_time_ms"] = 5.2
        else:
            connectivity_results["tests"]["ping"] = {
                "status": "failed",
                "error": "No management IP",
            }

        return connectivity_results

    async def _validate_device_health(self, device_id: str) -> dict[str, Any]:
        """Validate device health after maintenance."""
        health_status = await self.monitoring_service.manager.get_device_health_status(device_id)

        return {
            "healthy": health_status.get("health_status") in ["healthy", "warning"],
            "health_score": health_status.get("health_score", 0),
            "issues": health_status.get("issues", []),
            "last_check": health_status.get("last_check"),
        }

    async def _execute_maintenance_task(self, device_id: str, task: dict[str, Any]) -> dict[str, Any]:
        """Execute individual maintenance task."""
        task_type = task.get("type", "generic")
        task_id = str(uuid.uuid4())

        # Mock task execution
        # In real implementation, this would execute actual maintenance tasks
        if task_type in [
            "firmware_update",
            "config_backup",
            "health_check",
            "interface_test",
        ]:
            return {
                "task_id": task_id,
                "type": task_type,
                "status": "success",
                "duration_seconds": 30,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        else:
            return {
                "task_id": task_id,
                "type": task_type,
                "status": "failed",
                "error": f"Unknown task type: {task_type}",
                "failed_at": datetime.now(timezone.utc).isoformat(),
            }

    # Workflow handlers (called by lifecycle stage transitions)
    async def _handle_planning(self, device_id: str, context: dict[str, Any]):
        """Handle planning stage."""
        pass

    async def _handle_provisioning(self, device_id: str, context: dict[str, Any]):
        """Handle provisioning stage."""
        pass

    async def _handle_deployment(self, device_id: str, context: dict[str, Any]):
        """Handle deployment stage."""
        pass

    async def _handle_active(self, device_id: str, context: dict[str, Any]):
        """Handle active stage."""
        pass

    async def _handle_maintenance(self, device_id: str, context: dict[str, Any]):
        """Handle maintenance stage."""
        pass

    async def _handle_upgrade(self, device_id: str, context: dict[str, Any]):
        """Handle upgrade stage."""
        pass

    async def _handle_migration(self, device_id: str, context: dict[str, Any]):
        """Handle migration stage."""
        pass

    async def _handle_decommissioning(self, device_id: str, context: dict[str, Any]):
        """Handle decommissioning stage."""
        pass

    async def _handle_retired(self, device_id: str, context: dict[str, Any]):
        """Handle retired stage."""
        pass
