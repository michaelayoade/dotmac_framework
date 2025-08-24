"""
Provisioning Bindings SDK - which resources a service needs (e.g., IP/VLAN for data; DID/SIP account for voice)
"""

from datetime import datetime
from dotmac_isp.sdks.core.datetime_utils import utc_now, utc_now_iso
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..core.exceptions import (
    ResourceAllocationError,
    ResourceBindingError,
)


class ResourceType(Enum):
    """Resource types."""

    IP_ADDRESS = "ip_address"
    VLAN = "vlan"
    DID = "did"
    SIP_ACCOUNT = "sip_account"
    BANDWIDTH = "bandwidth"
    PORT = "port"
    DEVICE = "device"
    CERTIFICATE = "certificate"
    DNS_RECORD = "dns_record"
    FIREWALL_RULE = "firewall_rule"


class ProvisioningBindingsService:
    """In-memory service for provisioning bindings operations."""

    def __init__(self):
        """  Init   operation."""
        self._service_bindings: Dict[str, Dict[str, Any]] = {}
        self._resource_templates: Dict[str, Dict[str, Any]] = {}
        self._resource_allocations: Dict[str, Dict[str, Any]] = {}
        self._dependency_rules: Dict[str, Dict[str, Any]] = {}

    async def create_service_binding(self, **kwargs) -> Dict[str, Any]:
        """Create service provisioning binding."""
        binding_id = kwargs.get("binding_id") or str(uuid4())

        binding = {
            "binding_id": binding_id,
            "service_definition_id": kwargs["service_definition_id"],
            "service_type": kwargs["service_type"],
            "name": kwargs["name"],
            "description": kwargs.get("description", ""),
            "required_resources": kwargs.get("required_resources", []),
            "optional_resources": kwargs.get("optional_resources", []),
            "resource_dependencies": kwargs.get("resource_dependencies", {}),
            "provisioning_order": kwargs.get("provisioning_order", []),
            "rollback_order": kwargs.get("rollback_order", []),
            "validation_rules": kwargs.get("validation_rules", {}),
            "metadata": kwargs.get("metadata", {}),
            "status": kwargs.get("status", "active"),
            "version": kwargs.get("version", "1.0.0"),
            "created_at": utc_now().isoformat(),
            "updated_at": utc_now().isoformat(),
        }

        # Validate service binding
        self._validate_service_binding(binding)

        self._service_bindings[binding_id] = binding
        return binding

    def _validate_service_binding(self, binding: Dict[str, Any]):
        """Validate service binding."""
        if not binding.get("service_definition_id"):
            raise ResourceBindingError("Service definition ID is required")

        if not binding.get("name"):
            raise ResourceBindingError("Binding name is required")

        # Validate required resources
        for resource in binding.get("required_resources", []):
            if not resource.get("resource_type"):
                raise ResourceBindingError(
                    "Resource type is required for all resources"
                )

    async def create_resource_template(self, **kwargs) -> Dict[str, Any]:
        """Create resource template."""
        template_id = kwargs.get("template_id") or str(uuid4())

        template = {
            "template_id": template_id,
            "resource_type": kwargs["resource_type"],
            "name": kwargs["name"],
            "description": kwargs.get("description", ""),
            "allocation_strategy": kwargs.get("allocation_strategy", "automatic"),
            "parameters": kwargs.get("parameters", {}),
            "constraints": kwargs.get("constraints", {}),
            "validation_rules": kwargs.get("validation_rules", {}),
            "provider_config": kwargs.get("provider_config", {}),
            "lifecycle_hooks": kwargs.get("lifecycle_hooks", {}),
            "cleanup_policy": kwargs.get("cleanup_policy", "retain"),
            "status": kwargs.get("status", "active"),
            "created_at": utc_now().isoformat(),
            "updated_at": utc_now().isoformat(),
        }

        self._resource_templates[template_id] = template
        return template

    async def allocate_resources(
        self,
        service_instance_id: str,
        binding_id: str,
        customer_requirements: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Allocate resources for service instance."""
        if binding_id not in self._service_bindings:
            raise ResourceBindingError(f"Service binding not found: {binding_id}")

        binding = self._service_bindings[binding_id]
        allocation_id = str(uuid4())

        allocation = {
            "allocation_id": allocation_id,
            "service_instance_id": service_instance_id,
            "binding_id": binding_id,
            "customer_requirements": customer_requirements or {},
            "allocated_resources": [],
            "failed_resources": [],
            "status": "in_progress",
            "started_at": utc_now().isoformat(),
            "completed_at": None,
            "error_message": None,
        }

        # Process required resources
        for resource_spec in binding["required_resources"]:
            try:
                resource_allocation = await self._allocate_single_resource(
                    service_instance_id, resource_spec, customer_requirements
                )
                allocation["allocated_resources"].append(resource_allocation)
            except Exception as e:
                allocation["failed_resources"].append(
                    {
                        "resource_spec": resource_spec,
                        "error": str(e),
                    }
                )

        # Process optional resources if requested
        for resource_spec in binding.get("optional_resources", []):
            if self._should_allocate_optional_resource(
                resource_spec, customer_requirements
            ):
                try:
                    resource_allocation = await self._allocate_single_resource(
                        service_instance_id, resource_spec, customer_requirements
                    )
                    allocation["allocated_resources"].append(resource_allocation)
                except Exception as e:
                    # Optional resource failures are not critical
                    allocation["failed_resources"].append(
                        {
                            "resource_spec": resource_spec,
                            "error": str(e),
                            "optional": True,
                        }
                    )

        # Update allocation status
        if allocation["failed_resources"] and not any(
            not r.get("optional", False) for r in allocation["failed_resources"]
        ):
            allocation["status"] = "completed_with_warnings"
        elif allocation["failed_resources"]:
            allocation["status"] = "failed"
        else:
            allocation["status"] = "completed"

        allocation["completed_at"] = utc_now().isoformat()

        self._resource_allocations[allocation_id] = allocation
        return allocation

    async def _allocate_single_resource(
        self,
        service_instance_id: str,
        resource_spec: Dict[str, Any],
        customer_requirements: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Allocate single resource."""
        resource_type = resource_spec["resource_type"]
        resource_id = str(uuid4())

        # Simulate resource allocation based on type
        if resource_type == ResourceType.IP_ADDRESS.value:
            allocated_resource = await self._allocate_ip_address(
                resource_spec, customer_requirements
            )
        elif resource_type == ResourceType.VLAN.value:
            allocated_resource = await self._allocate_vlan(
                resource_spec, customer_requirements
            )
        elif resource_type == ResourceType.DID.value:
            allocated_resource = await self._allocate_did(
                resource_spec, customer_requirements
            )
        elif resource_type == ResourceType.SIP_ACCOUNT.value:
            allocated_resource = await self._allocate_sip_account(
                resource_spec, customer_requirements
            )
        elif resource_type == ResourceType.BANDWIDTH.value:
            allocated_resource = await self._allocate_bandwidth(
                resource_spec, customer_requirements
            )
        else:
            allocated_resource = await self._allocate_generic_resource(
                resource_spec, customer_requirements
            )

        return {
            "resource_id": resource_id,
            "resource_type": resource_type,
            "service_instance_id": service_instance_id,
            "allocation_details": allocated_resource,
            "allocated_at": utc_now().isoformat(),
            "status": "allocated",
        }

    async def _allocate_ip_address(
        self, resource_spec: Dict[str, Any], requirements: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Allocate IP address."""
        # Simulate IP allocation
        network = (
            requirements.get("network", "192.168.1.0/24")
            if requirements
            else "192.168.1.0/24"
        )
        allocated_ip = "192.168.1.100"  # Simulated allocation

        return {
            "ip_address": allocated_ip,
            "network": network,
            "subnet_mask": "255.255.255.0",
            "gateway": "192.168.1.1",
            "dns_servers": ["8.8.8.8", "8.8.4.4"],
            "allocation_method": "static",
        }

    async def _allocate_vlan(
        self, resource_spec: Dict[str, Any], requirements: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Allocate VLAN."""
        # Simulate VLAN allocation
        vlan_id = 100  # Simulated allocation

        return {
            "vlan_id": vlan_id,
            "vlan_name": f"customer-vlan-{vlan_id}",
            "description": "Customer service VLAN",
            "ports": [],
        }

    async def _allocate_did(
        self, resource_spec: Dict[str, Any], requirements: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Allocate DID (Direct Inward Dialing) number."""
        # Simulate DID allocation
        did_number = "+1234567890"  # Simulated allocation

        return {
            "did_number": did_number,
            "country_code": "+1",
            "area_code": "234",
            "number": "567890",
            "number_type": "local",
            "carrier": "primary",
        }

    async def _allocate_sip_account(
        self, resource_spec: Dict[str, Any], requirements: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Allocate SIP account."""
        # Simulate SIP account allocation
        username = f"user_{str(uuid4())[:8]}"

        return {
            "username": username,
            "domain": "sip.example.com",
            "password": "generated_password",
            "display_name": (
                requirements.get("display_name", "Customer")
                if requirements
                else "Customer"
            ),
            "codec_preferences": ["G.711", "G.729"],
            "max_concurrent_calls": 5,
        }

    async def _allocate_bandwidth(
        self, resource_spec: Dict[str, Any], requirements: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Allocate bandwidth."""
        # Simulate bandwidth allocation
        download_speed = (
            requirements.get("download_speed", 100) if requirements else 100
        )
        upload_speed = requirements.get("upload_speed", 10) if requirements else 10

        return {
            "download_speed_mbps": download_speed,
            "upload_speed_mbps": upload_speed,
            "burst_allowance": download_speed * 1.2,
            "traffic_shaping": "enabled",
            "qos_class": "standard",
        }

    async def _allocate_generic_resource(
        self, resource_spec: Dict[str, Any], requirements: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Allocate generic resource."""
        return {
            "resource_type": resource_spec["resource_type"],
            "parameters": resource_spec.get("parameters", {}),
            "allocated_value": f"allocated_{str(uuid4())[:8]}",
        }

    def _should_allocate_optional_resource(
        self, resource_spec: Dict[str, Any], requirements: Optional[Dict[str, Any]]
    ) -> bool:
        """Determine if optional resource should be allocated."""
        if not requirements:
            return False

        resource_type = resource_spec["resource_type"]
        return requirements.get(f"include_{resource_type}", False)

    async def deallocate_resources(self, allocation_id: str) -> Dict[str, Any]:
        """Deallocate resources."""
        if allocation_id not in self._resource_allocations:
            raise ResourceAllocationError(
                f"Resource allocation not found: {allocation_id}"
            )

        allocation = self._resource_allocations[allocation_id]

        deallocation_results = []

        # Deallocate in reverse order
        for resource in reversed(allocation["allocated_resources"]):
            try:
                deallocation_result = await self._deallocate_single_resource(resource)
                deallocation_results.append(deallocation_result)
            except Exception as e:
                deallocation_results.append(
                    {
                        "resource_id": resource["resource_id"],
                        "status": "failed",
                        "error": str(e),
                    }
                )

        # Update allocation status
        allocation["status"] = "deallocated"
        allocation["deallocated_at"] = utc_now().isoformat()

        return {
            "allocation_id": allocation_id,
            "deallocation_results": deallocation_results,
            "deallocated_at": allocation["deallocated_at"],
        }

    async def _deallocate_single_resource(
        self, resource: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deallocate single resource."""
        # Simulate resource deallocation
        return {
            "resource_id": resource["resource_id"],
            "resource_type": resource["resource_type"],
            "status": "deallocated",
            "deallocated_at": utc_now().isoformat(),
        }


class ProvisioningBindingsSDK:
    """Minimal, reusable SDK for provisioning bindings management."""

    def __init__(self, tenant_id: str):
        """  Init   operation."""
        self.tenant_id = tenant_id
        self._service = ProvisioningBindingsService()

    async def create_service_binding(
        self,
        service_definition_id: str,
        service_type: str,
        name: str,
        required_resources: List[Dict[str, Any]],
        **kwargs,
    ) -> Dict[str, Any]:
        """Create service provisioning binding."""
        binding = await self._service.create_service_binding(
            service_definition_id=service_definition_id,
            service_type=service_type,
            name=name,
            required_resources=required_resources,
            tenant_id=self.tenant_id,
            **kwargs,
        )

        return {
            "binding_id": binding["binding_id"],
            "service_definition_id": binding["service_definition_id"],
            "service_type": binding["service_type"],
            "name": binding["name"],
            "description": binding["description"],
            "required_resources": binding["required_resources"],
            "optional_resources": binding["optional_resources"],
            "provisioning_order": binding["provisioning_order"],
            "status": binding["status"],
            "version": binding["version"],
            "created_at": binding["created_at"],
        }

    async def create_data_service_binding(
        self,
        service_definition_id: str,
        name: str,
        bandwidth_mbps: int = 100,
        include_static_ip: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create data service binding with typical resources."""
        required_resources = [
            {
                "resource_type": ResourceType.BANDWIDTH.value,
                "name": "internet_bandwidth",
                "parameters": {
                    "download_speed": bandwidth_mbps,
                    "upload_speed": bandwidth_mbps // 10,
                },
            },
            {
                "resource_type": ResourceType.VLAN.value,
                "name": "customer_vlan",
                "parameters": {},
            },
        ]

        if include_static_ip:
            required_resources.append(
                {
                    "resource_type": ResourceType.IP_ADDRESS.value,
                    "name": "static_ip",
                    "parameters": {"type": "static"},
                }
            )

        return await self.create_service_binding(
            service_definition_id=service_definition_id,
            service_type="data",
            name=name,
            required_resources=required_resources,
            **kwargs,
        )

    async def create_voice_service_binding(
        self,
        service_definition_id: str,
        name: str,
        did_count: int = 1,
        sip_accounts: int = 1,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create voice service binding with typical resources."""
        required_resources = []

        # Add DID numbers
        for i in range(did_count):
            required_resources.append(
                {
                    "resource_type": ResourceType.DID.value,
                    "name": f"did_number_{i+1}",
                    "parameters": {"number_type": "local"},
                }
            )

        # Add SIP accounts
        for i in range(sip_accounts):
            required_resources.append(
                {
                    "resource_type": ResourceType.SIP_ACCOUNT.value,
                    "name": f"sip_account_{i+1}",
                    "parameters": {"max_concurrent_calls": 5},
                }
            )

        return await self.create_service_binding(
            service_definition_id=service_definition_id,
            service_type="voice",
            name=name,
            required_resources=required_resources,
            **kwargs,
        )

    async def allocate_service_resources(
        self,
        service_instance_id: str,
        binding_id: str,
        customer_requirements: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Allocate resources for service instance."""
        allocation = await self._service.allocate_resources(
            service_instance_id=service_instance_id,
            binding_id=binding_id,
            customer_requirements=customer_requirements,
        )

        return {
            "allocation_id": allocation["allocation_id"],
            "service_instance_id": allocation["service_instance_id"],
            "binding_id": allocation["binding_id"],
            "status": allocation["status"],
            "allocated_resources": [
                {
                    "resource_id": r["resource_id"],
                    "resource_type": r["resource_type"],
                    "allocation_details": r["allocation_details"],
                    "allocated_at": r["allocated_at"],
                }
                for r in allocation["allocated_resources"]
            ],
            "failed_resources": allocation["failed_resources"],
            "started_at": allocation["started_at"],
            "completed_at": allocation["completed_at"],
        }

    async def deallocate_service_resources(self, allocation_id: str) -> Dict[str, Any]:
        """Deallocate service resources."""
        result = await self._service.deallocate_resources(allocation_id)

        return {
            "allocation_id": result["allocation_id"],
            "deallocation_results": result["deallocation_results"],
            "deallocated_at": result["deallocated_at"],
        }

    async def get_resource_allocation(self, allocation_id: str) -> Dict[str, Any]:
        """Get resource allocation details."""
        if allocation_id not in self._service._resource_allocations:
            raise ResourceAllocationError(
                f"Resource allocation not found: {allocation_id}"
            )

        allocation = self._service._resource_allocations[allocation_id]

        return {
            "allocation_id": allocation["allocation_id"],
            "service_instance_id": allocation["service_instance_id"],
            "binding_id": allocation["binding_id"],
            "status": allocation["status"],
            "allocated_resources": allocation["allocated_resources"],
            "failed_resources": allocation["failed_resources"],
            "customer_requirements": allocation["customer_requirements"],
            "started_at": allocation["started_at"],
            "completed_at": allocation["completed_at"],
        }

    async def list_service_bindings(
        self, service_type: Optional[str] = None, status: str = "active"
    ) -> List[Dict[str, Any]]:
        """List service bindings."""
        bindings = list(self._service._service_bindings.values())

        if service_type:
            bindings = [b for b in bindings if b["service_type"] == service_type]

        if status:
            bindings = [b for b in bindings if b["status"] == status]

        return [
            {
                "binding_id": binding["binding_id"],
                "service_definition_id": binding["service_definition_id"],
                "service_type": binding["service_type"],
                "name": binding["name"],
                "required_resources": len(binding["required_resources"]),
                "optional_resources": len(binding["optional_resources"]),
                "status": binding["status"],
                "version": binding["version"],
                "created_at": binding["created_at"],
            }
            for binding in bindings
        ]

    async def validate_resource_requirements(
        self, binding_id: str, customer_requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate resource requirements."""
        if binding_id not in self._service._service_bindings:
            raise ResourceBindingError(f"Service binding not found: {binding_id}")

        binding = self._service._service_bindings[binding_id]

        validation_result = {
            "binding_id": binding_id,
            "valid": True,
            "errors": [],
            "warnings": [],
            "resource_validation": [],
        }

        # Validate each required resource
        for resource_spec in binding["required_resources"]:
            resource_validation = {
                "resource_type": resource_spec["resource_type"],
                "name": resource_spec["name"],
                "valid": True,
                "errors": [],
                "warnings": [],
            }

            # Check if customer requirements provide necessary parameters
            resource_type = resource_spec["resource_type"]
            if resource_type == ResourceType.BANDWIDTH.value:
                if "download_speed" not in customer_requirements:
                    resource_validation["warnings"].append(
                        "Download speed not specified, using default"
                    )

            validation_result["resource_validation"].append(resource_validation)

        return validation_result
