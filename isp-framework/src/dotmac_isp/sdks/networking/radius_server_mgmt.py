"""
RADIUS Server Management SDK - FreeRADIUS config, dictionaries, policies
"""

from datetime import datetime
from dotmac_isp.sdks.core.datetime_utils import utc_now, utc_now_iso
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..core.exceptions import RADIUSError


class RADIUSServerMgmtService:
    """In-memory service for RADIUS server management operations."""

    def __init__(self):
        self._clients: Dict[str, Dict[str, Any]] = {}
        self._policies: Dict[str, Dict[str, Any]] = {}
        self._dictionaries: Dict[str, Dict[str, Any]] = {}
        self._user_groups: Dict[str, Dict[str, Any]] = {}
        self._config_templates: Dict[str, str] = {}

    async def add_client(self, **kwargs) -> Dict[str, Any]:
        """Add RADIUS client (NAS)."""
        client_id = kwargs.get("client_id") or str(uuid4())

        if client_id in self._clients:
            raise RADIUSError(f"Client already exists: {client_id}")

        client = {
            "client_id": client_id,
            "client_name": kwargs.get("client_name", ""),
            "ip_address": kwargs["ip_address"],
            "shared_secret": kwargs["shared_secret"],
            "nas_type": kwargs.get("nas_type", "other"),
            "shortname": kwargs.get("shortname", ""),
            "description": kwargs.get("description", ""),
            "require_message_authenticator": kwargs.get(
                "require_message_authenticator", True
            ),
            "status": kwargs.get("status", "active"),
            "created_at": utc_now().isoformat(),
            "updated_at": utc_now().isoformat(),
        }

        self._clients[client_id] = client
        return client

    async def create_policy(self, **kwargs) -> Dict[str, Any]:
        """Create RADIUS policy."""
        policy_id = kwargs.get("policy_id") or str(uuid4())

        if policy_id in self._policies:
            raise RADIUSError(f"Policy already exists: {policy_id}")

        policy = {
            "policy_id": policy_id,
            "policy_name": kwargs["policy_name"],
            "policy_type": kwargs.get("policy_type", "authorization"),
            "conditions": kwargs.get("conditions", []),
            "actions": kwargs.get("actions", []),
            "priority": kwargs.get("priority", 100),
            "description": kwargs.get("description", ""),
            "status": kwargs.get("status", "active"),
            "created_at": utc_now().isoformat(),
            "updated_at": utc_now().isoformat(),
        }

        self._policies[policy_id] = policy
        return policy

    async def add_dictionary(self, **kwargs) -> Dict[str, Any]:
        """Add custom RADIUS dictionary."""
        dict_id = kwargs.get("dict_id") or str(uuid4())

        dictionary = {
            "dict_id": dict_id,
            "dict_name": kwargs["dict_name"],
            "vendor_id": kwargs.get("vendor_id"),
            "attributes": kwargs.get("attributes", []),
            "values": kwargs.get("values", []),
            "description": kwargs.get("description", ""),
            "status": kwargs.get("status", "active"),
            "created_at": utc_now().isoformat(),
        }

        self._dictionaries[dict_id] = dictionary
        return dictionary

    async def generate_config(self, config_type: str) -> str:
        """Generate RADIUS configuration files."""
        if config_type == "clients":
            return self._generate_clients_config()
        elif config_type == "policies":
            return self._generate_policies_config()
        elif config_type == "dictionary":
            return self._generate_dictionary_config()
        else:
            raise RADIUSError(f"Unknown config type: {config_type}")

    def _generate_clients_config(self) -> str:
        """Generate clients.conf configuration."""
        config_lines = [
            "# RADIUS Clients Configuration",
            "# Generated automatically",
            "",
        ]

        for client in self._clients.values():
            if client["status"] == "active":
                config_lines.extend(
                    [
                        f"client {client['shortname'] or client['client_name']} {{",
                        f"    ipaddr = {client['ip_address']}",
                        f"    secret = {client['shared_secret']}",
                        f"    nastype = {client['nas_type']}",
                        f"    shortname = {client['shortname'] or client['client_name']}",
                    ]
                )

                if client["require_message_authenticator"]:
                    config_lines.append("    require_message_authenticator = yes")

                config_lines.extend(["}", ""])

        return "\n".join(config_lines)

    def _generate_policies_config(self) -> str:
        """Generate policy configuration."""
        config_lines = [
            "# RADIUS Policies Configuration",
            "# Generated automatically",
            "",
        ]

        # Sort policies by priority
        sorted_policies = sorted(self._policies.values(), key=lambda p: p["priority"])

        for policy in sorted_policies:
            if policy["status"] == "active":
                config_lines.extend(
                    [
                        f"# Policy: {policy['policy_name']}",
                        f"# Type: {policy['policy_type']}",
                        f"# Priority: {policy['priority']}",
                    ]
                )

                for condition in policy["conditions"]:
                    config_lines.append(f"if ({condition}) {{")

                for action in policy["actions"]:
                    config_lines.append(f"    {action}")

                for _ in policy["conditions"]:
                    config_lines.append("}")

                config_lines.append("")

        return "\n".join(config_lines)

    def _generate_dictionary_config(self) -> str:
        """Generate dictionary configuration."""
        config_lines = ["# Custom RADIUS Dictionary", "# Generated automatically", ""]

        for dictionary in self._dictionaries.values():
            if dictionary["status"] == "active":
                config_lines.extend(
                    [
                        f"# Dictionary: {dictionary['dict_name']}",
                    ]
                )

                if dictionary["vendor_id"]:
                    config_lines.append(
                        f"VENDOR {dictionary['dict_name']} {dictionary['vendor_id']}"
                    )

                for attr in dictionary["attributes"]:
                    config_lines.append(
                        f"ATTRIBUTE {attr['name']} {attr['id']} {attr['type']}"
                    )

                for value in dictionary["values"]:
                    config_lines.append(
                        f"VALUE {value['attribute']} {value['name']} {value['value']}"
                    )

                config_lines.append("")

        return "\n".join(config_lines)


class RADIUSServerMgmtSDK:
    """Minimal, reusable SDK for RADIUS server management."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._service = RADIUSServerMgmtService()

    async def add_radius_client(
        self,
        client_name: str,
        ip_address: str,
        shared_secret: str,
        nas_type: str = "other",
        shortname: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Add RADIUS client (NAS)."""
        client = await self._service.add_client(
            client_name=client_name,
            ip_address=ip_address,
            shared_secret=shared_secret,
            nas_type=nas_type,
            shortname=shortname or client_name.lower().replace(" ", "_"),
            tenant_id=self.tenant_id,
            **kwargs,
        )

        return {
            "client_id": client["client_id"],
            "client_name": client["client_name"],
            "ip_address": client["ip_address"],
            "nas_type": client["nas_type"],
            "shortname": client["shortname"],
            "description": client["description"],
            "status": client["status"],
            "created_at": client["created_at"],
        }

    async def create_authorization_policy(
        self,
        policy_name: str,
        conditions: List[str],
        actions: List[str],
        priority: int = 100,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create RADIUS authorization policy."""
        policy = await self._service.create_policy(
            policy_name=policy_name,
            policy_type="authorization",
            conditions=conditions,
            actions=actions,
            priority=priority,
            description=description,
        )

        return {
            "policy_id": policy["policy_id"],
            "policy_name": policy["policy_name"],
            "policy_type": policy["policy_type"],
            "conditions": policy["conditions"],
            "actions": policy["actions"],
            "priority": policy["priority"],
            "status": policy["status"],
            "created_at": policy["created_at"],
        }

    async def add_custom_dictionary(
        self,
        dict_name: str,
        vendor_id: Optional[int] = None,
        attributes: Optional[List[Dict[str, Any]]] = None,
        values: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Add custom RADIUS dictionary."""
        dictionary = await self._service.add_dictionary(
            dict_name=dict_name,
            vendor_id=vendor_id,
            attributes=attributes or [],
            values=values or [],
            **kwargs,
        )

        return {
            "dict_id": dictionary["dict_id"],
            "dict_name": dictionary["dict_name"],
            "vendor_id": dictionary["vendor_id"],
            "attributes": dictionary["attributes"],
            "values": dictionary["values"],
            "status": dictionary["status"],
            "created_at": dictionary["created_at"],
        }

    async def generate_clients_config(self) -> str:
        """Generate FreeRADIUS clients.conf file."""
        return await self._service.generate_config("clients")

    async def generate_policies_config(self) -> str:
        """Generate FreeRADIUS policies configuration."""
        return await self._service.generate_config("policies")

    async def generate_dictionary_config(self) -> str:
        """Generate custom dictionary configuration."""
        return await self._service.generate_config("dictionary")

    async def get_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get RADIUS client by ID."""
        client = self._service._clients.get(client_id)
        if not client:
            return None

        return {
            "client_id": client["client_id"],
            "client_name": client["client_name"],
            "ip_address": client["ip_address"],
            "nas_type": client["nas_type"],
            "shortname": client["shortname"],
            "description": client["description"],
            "require_message_authenticator": client["require_message_authenticator"],
            "status": client["status"],
            "created_at": client["created_at"],
            "updated_at": client["updated_at"],
        }

    async def list_clients(self) -> List[Dict[str, Any]]:
        """List all RADIUS clients."""
        return [
            {
                "client_id": client["client_id"],
                "client_name": client["client_name"],
                "ip_address": client["ip_address"],
                "nas_type": client["nas_type"],
                "shortname": client["shortname"],
                "status": client["status"],
            }
            for client in self._service._clients.values()
        ]

    async def list_policies(self) -> List[Dict[str, Any]]:
        """List all RADIUS policies."""
        return [
            {
                "policy_id": policy["policy_id"],
                "policy_name": policy["policy_name"],
                "policy_type": policy["policy_type"],
                "priority": policy["priority"],
                "status": policy["status"],
                "created_at": policy["created_at"],
            }
            for policy in sorted(
                self._service._policies.values(), key=lambda p: p["priority"]
            )
        ]

    async def update_client_secret(
        self, client_id: str, new_secret: str
    ) -> Dict[str, Any]:
        """Update RADIUS client shared secret."""
        if client_id not in self._service._clients:
            raise RADIUSError(f"Client not found: {client_id}")

        self._service._clients[client_id]["shared_secret"] = new_secret
        self._service._clients[client_id]["updated_at"] = utc_now().isoformat()

        return {
            "client_id": client_id,
            "status": "secret_updated",
            "updated_at": self._service._clients[client_id]["updated_at"],
        }
