"""
VLAN SDK - VLAN assignment and management with conflict detection
"""

from datetime import datetime
from dotmac_isp.sdks.core.datetime_utils import utc_now, utc_now_iso
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..core.exceptions import VLANConflictError, VLANError


class VLANService:
    """In-memory service for VLAN operations."""

    def __init__(self):
        """  Init   operation."""
        self._vlans: Dict[int, Dict[str, Any]] = {}
        self._assignments: Dict[str, Dict[str, Any]] = {}
        self._site_vlans: Dict[str, List[int]] = {}

    async def create_vlan(self, **kwargs) -> Dict[str, Any]:
        """Create VLAN."""
        vlan_id = kwargs["vlan_id"]

        if not (1 <= vlan_id <= 4094):
            raise VLANError(f"Invalid VLAN ID: {vlan_id}. Must be between 1 and 4094")

        if vlan_id in self._vlans:
            raise VLANConflictError(vlan_id)

        vlan = {
            "vlan_id": vlan_id,
            "vlan_name": kwargs.get("vlan_name", f"VLAN-{vlan_id}"),
            "description": kwargs.get("description", ""),
            "site_id": kwargs.get("site_id"),
            "network_id": kwargs.get("network_id"),
            "vlan_type": kwargs.get(
                "vlan_type", "customer"
            ),  # customer, management, trunk
            "status": kwargs.get("status", "active"),
            "created_at": utc_now().isoformat(),
            "updated_at": utc_now().isoformat(),
        }

        self._vlans[vlan_id] = vlan

        # Index by site
        site_id = vlan.get("site_id")
        if site_id:
            if site_id not in self._site_vlans:
                self._site_vlans[site_id] = []
            self._site_vlans[site_id].append(vlan_id)

        return vlan

    async def assign_vlan(self, **kwargs) -> Dict[str, Any]:
        """Assign VLAN to port/interface."""
        vlan_id = kwargs["vlan_id"]
        port_id = kwargs["port_id"]

        if vlan_id not in self._vlans:
            raise VLANError(f"VLAN not found: {vlan_id}")

        assignment_id = str(uuid4())
        assignment = {
            "assignment_id": assignment_id,
            "vlan_id": vlan_id,
            "port_id": port_id,
            "assignment_type": kwargs.get("assignment_type", "access"),  # access, trunk
            "native_vlan": kwargs.get("native_vlan", False),
            "allowed_vlans": kwargs.get("allowed_vlans", []),
            "status": "assigned",
            "created_at": utc_now().isoformat(),
        }

        self._assignments[assignment_id] = assignment
        return assignment

    async def auto_assign_vlan(self, **kwargs) -> Dict[str, Any]:
        """Auto-assign next available VLAN."""
        site_id = kwargs.get("site_id")
        vlan_range_start = kwargs.get("vlan_range_start", 100)
        vlan_range_end = kwargs.get("vlan_range_end", 4094)
        reserved_vlans = kwargs.get("reserved_vlans", [1, 1002, 1003, 1004, 1005])

        for vlan_id in range(vlan_range_start, vlan_range_end + 1):
            if vlan_id not in self._vlans and vlan_id not in reserved_vlans:
                return await self.create_vlan(
                    vlan_id=vlan_id, site_id=site_id, **kwargs
                )

        raise VLANError(
            f"No available VLANs in range {vlan_range_start}-{vlan_range_end}"
        )


class VLANSDK:
    """Minimal, reusable SDK for VLAN management."""

    def __init__(self, tenant_id: str):
        """  Init   operation."""
        self.tenant_id = tenant_id
        self._service = VLANService()

    async def create_vlan(
        self,
        vlan_id: int,
        vlan_name: Optional[str] = None,
        description: Optional[str] = None,
        site_id: Optional[str] = None,
        vlan_type: str = "customer",
        **kwargs,
    ) -> Dict[str, Any]:
        """Create VLAN."""
        vlan = await self._service.create_vlan(
            vlan_id=vlan_id,
            vlan_name=vlan_name or f"VLAN-{vlan_id}",
            description=description,
            site_id=site_id,
            vlan_type=vlan_type,
            tenant_id=self.tenant_id,
            **kwargs,
        )

        return {
            "vlan_id": vlan["vlan_id"],
            "vlan_name": vlan["vlan_name"],
            "description": vlan["description"],
            "site_id": vlan["site_id"],
            "network_id": vlan["network_id"],
            "vlan_type": vlan["vlan_type"],
            "status": vlan["status"],
            "created_at": vlan["created_at"],
        }

    async def assign_vlan_to_port(
        self,
        vlan_id: int,
        port_id: str,
        assignment_type: str = "access",
        native_vlan: bool = False,
        allowed_vlans: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """Assign VLAN to port/interface."""
        assignment = await self._service.assign_vlan(
            vlan_id=vlan_id,
            port_id=port_id,
            assignment_type=assignment_type,
            native_vlan=native_vlan,
            allowed_vlans=allowed_vlans or [],
        )

        return {
            "assignment_id": assignment["assignment_id"],
            "vlan_id": assignment["vlan_id"],
            "port_id": assignment["port_id"],
            "assignment_type": assignment["assignment_type"],
            "native_vlan": assignment["native_vlan"],
            "allowed_vlans": assignment["allowed_vlans"],
            "status": assignment["status"],
            "created_at": assignment["created_at"],
        }

    async def auto_assign_vlan(
        self,
        site_id: Optional[str] = None,
        vlan_name: Optional[str] = None,
        description: Optional[str] = None,
        vlan_type: str = "customer",
    ) -> Dict[str, Any]:
        """Auto-assign next available VLAN."""
        vlan = await self._service.auto_assign_vlan(
            site_id=site_id,
            vlan_name=vlan_name,
            description=description,
            vlan_type=vlan_type,
        )

        return {
            "vlan_id": vlan["vlan_id"],
            "vlan_name": vlan["vlan_name"],
            "description": vlan["description"],
            "site_id": vlan["site_id"],
            "vlan_type": vlan["vlan_type"],
            "status": vlan["status"],
            "created_at": vlan["created_at"],
        }

    async def get_vlan(self, vlan_id: int) -> Optional[Dict[str, Any]]:
        """Get VLAN by ID."""
        vlan = self._service._vlans.get(vlan_id)
        if not vlan:
            return None

        return {
            "vlan_id": vlan["vlan_id"],
            "vlan_name": vlan["vlan_name"],
            "description": vlan["description"],
            "site_id": vlan["site_id"],
            "network_id": vlan["network_id"],
            "vlan_type": vlan["vlan_type"],
            "status": vlan["status"],
            "created_at": vlan["created_at"],
            "updated_at": vlan["updated_at"],
        }

    async def unassign_vlan_from_port(self, assignment_id: str) -> Dict[str, Any]:
        """Unassign VLAN from port."""
        if assignment_id not in self._service._assignments:
            raise VLANError(f"Assignment not found: {assignment_id}")

        assignment = self._service._assignments[assignment_id]
        del self._service._assignments[assignment_id]

        return {
            "assignment_id": assignment_id,
            "vlan_id": assignment["vlan_id"],
            "port_id": assignment["port_id"],
            "status": "unassigned",
            "unassigned_at": utc_now().isoformat(),
        }

    async def get_port_vlans(self, port_id: str) -> List[Dict[str, Any]]:
        """Get all VLAN assignments for a port."""
        assignments = [
            assign
            for assign in self._service._assignments.values()
            if assign["port_id"] == port_id and assign["status"] == "assigned"
        ]

        return [
            {
                "assignment_id": assign["assignment_id"],
                "vlan_id": assign["vlan_id"],
                "assignment_type": assign["assignment_type"],
                "native_vlan": assign["native_vlan"],
                "allowed_vlans": assign["allowed_vlans"],
                "created_at": assign["created_at"],
            }
            for assign in assignments
        ]

    async def get_site_vlans(self, site_id: str) -> List[Dict[str, Any]]:
        """Get all VLANs for a site."""
        vlan_ids = self._service._site_vlans.get(site_id, [])

        return [
            {
                "vlan_id": vlan_id,
                "vlan_name": self._service._vlans[vlan_id]["vlan_name"],
                "description": self._service._vlans[vlan_id]["description"],
                "vlan_type": self._service._vlans[vlan_id]["vlan_type"],
                "status": self._service._vlans[vlan_id]["status"],
            }
            for vlan_id in vlan_ids
            if vlan_id in self._service._vlans
        ]
