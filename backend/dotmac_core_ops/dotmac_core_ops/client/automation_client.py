"""
Automation client for interacting with automation APIs.
"""

from typing import Dict, Any, List, Optional
import httpx
import structlog

from ..contracts.common_schemas import ExecutionStatus

logger = structlog.get_logger(__name__)


class AutomationClient:
    """Client for automation operations."""

    def __init__(self, http_client: httpx.AsyncClient):
        self.client = http_client

    async def create_rule(
        self,
        name: str,
        triggers: List[Dict[str, Any]],
        actions: List[Dict[str, Any]],
        description: Optional[str] = None,
        enabled: bool = True,
        conditions: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Create a new automation rule.

        Args:
            name: Rule name
            triggers: Rule triggers
            actions: Rule actions
            description: Rule description
            enabled: Rule enabled status
            conditions: Rule conditions

        Returns:
            Rule ID
        """
        payload = {
            "name": name,
            "description": description,
            "enabled": enabled,
            "triggers": triggers,
            "conditions": conditions or [],
            "actions": actions
        }

        response = await self.client.post("/automation/rules", json=payload)
        response.raise_for_status()

        result = response.json()
        return result["data"]["rule_id"]

    async def list_rules(
        self,
        page: int = 1,
        page_size: int = 50,
        enabled_only: bool = False
    ) -> Dict[str, Any]:
        """
        List automation rules.

        Args:
            page: Page number
            page_size: Items per page
            enabled_only: Show only enabled rules

        Returns:
            List of rules with pagination info
        """
        params = {"page": page, "page_size": page_size, "enabled_only": enabled_only}

        response = await self.client.get("/automation/rules", params=params)
        response.raise_for_status()

        return response.json()

    async def get_rule(self, rule_id: str) -> Dict[str, Any]:
        """
        Get automation rule by ID.

        Args:
            rule_id: Rule ID

        Returns:
            Rule details
        """
        response = await self.client.get(f"/automation/rules/{rule_id}")
        response.raise_for_status()

        return response.json()

    async def update_rule(
        self,
        rule_id: str,
        name: str,
        triggers: List[Dict[str, Any]],
        actions: List[Dict[str, Any]],
        description: Optional[str] = None,
        enabled: bool = True,
        conditions: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Update an automation rule.

        Args:
            rule_id: Rule ID
            name: Rule name
            triggers: Rule triggers
            actions: Rule actions
            description: Rule description
            enabled: Rule enabled status
            conditions: Rule conditions

        Returns:
            True if updated successfully
        """
        payload = {
            "name": name,
            "description": description,
            "enabled": enabled,
            "triggers": triggers,
            "conditions": conditions or [],
            "actions": actions
        }

        response = await self.client.put(f"/automation/rules/{rule_id}", json=payload)
        response.raise_for_status()

        result = response.json()
        return result["success"]

    async def enable_rule(self, rule_id: str) -> bool:
        """
        Enable an automation rule.

        Args:
            rule_id: Rule ID

        Returns:
            True if enabled successfully
        """
        response = await self.client.post(f"/automation/rules/{rule_id}/enable")
        response.raise_for_status()

        result = response.json()
        return result["success"]

    async def disable_rule(self, rule_id: str) -> bool:
        """
        Disable an automation rule.

        Args:
            rule_id: Rule ID

        Returns:
            True if disabled successfully
        """
        response = await self.client.post(f"/automation/rules/{rule_id}/disable")
        response.raise_for_status()

        result = response.json()
        return result["success"]

    async def delete_rule(self, rule_id: str) -> bool:
        """
        Delete an automation rule.

        Args:
            rule_id: Rule ID

        Returns:
            True if deleted successfully
        """
        response = await self.client.delete(f"/automation/rules/{rule_id}")
        response.raise_for_status()

        result = response.json()
        return result["success"]

    async def trigger_automation(
        self,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> bool:
        """
        Manually trigger automation rules for an event.

        Args:
            event_type: Event type
            event_data: Event data

        Returns:
            True if triggered successfully
        """
        payload = {"event_type": event_type, "event_data": event_data}

        response = await self.client.post("/automation/trigger", json=payload)
        response.raise_for_status()

        result = response.json()
        return result["success"]

    async def list_executions(
        self,
        page: int = 1,
        page_size: int = 50,
        rule_id: Optional[str] = None,
        status_filter: Optional[ExecutionStatus] = None
    ) -> Dict[str, Any]:
        """
        List automation executions.

        Args:
            page: Page number
            page_size: Items per page
            rule_id: Filter by rule ID
            status_filter: Filter by execution status

        Returns:
            List of executions with pagination info
        """
        params = {"page": page, "page_size": page_size}
        if rule_id:
            params["rule_id"] = rule_id
        if status_filter:
            params["status_filter"] = status_filter.value

        response = await self.client.get("/automation/executions", params=params)
        response.raise_for_status()

        return response.json()
