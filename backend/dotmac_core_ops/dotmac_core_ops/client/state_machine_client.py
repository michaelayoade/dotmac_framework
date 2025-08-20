"""
State Machine client for interacting with state machine APIs.
"""

from typing import Dict, Any, List, Optional
import httpx
import structlog

from ..contracts.common_schemas import ExecutionStatus

logger = structlog.get_logger(__name__)


class StateMachineClient:
    """Client for state machine operations."""

    def __init__(self, http_client: httpx.AsyncClient):
        self.client = http_client

    async def create_state_machine(
        self,
        name: str,
        initial_state: str,
        states: List[Dict[str, Any]],
        transitions: List[Dict[str, Any]],
        description: Optional[str] = None
    ) -> str:
        """
        Create a new state machine.

        Args:
            name: State machine name
            initial_state: Initial state
            states: State definitions
            transitions: Transition definitions
            description: State machine description

        Returns:
            State machine ID
        """
        payload = {
            "name": name,
            "description": description,
            "initial_state": initial_state,
            "states": states,
            "transitions": transitions
        }

        response = await self.client.post("/state-machines/", json=payload)
        response.raise_for_status()

        result = response.json()
        return result["data"]["state_machine_id"]

    async def list_state_machines(
        self,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """
        List state machines.

        Args:
            page: Page number
            page_size: Items per page

        Returns:
            List of state machines with pagination info
        """
        params = {"page": page, "page_size": page_size}

        response = await self.client.get("/state-machines/", params=params)
        response.raise_for_status()

        return response.json()

    async def get_state_machine(self, state_machine_id: str) -> Dict[str, Any]:
        """
        Get state machine by ID.

        Args:
            state_machine_id: State machine ID

        Returns:
            State machine details
        """
        response = await self.client.get(f"/state-machines/{state_machine_id}")
        response.raise_for_status()

        return response.json()

    async def execute_state_machine(
        self,
        state_machine_id: str,
        context_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Execute a state machine.

        Args:
            state_machine_id: State machine ID
            context_data: Context data

        Returns:
            Execution ID
        """
        payload = {"context_data": context_data or {}}

        response = await self.client.post(f"/state-machines/{state_machine_id}/execute", json=payload)
        response.raise_for_status()

        result = response.json()
        return result["data"]["execution_id"]

    async def list_executions(
        self,
        state_machine_id: str,
        page: int = 1,
        page_size: int = 50,
        status_filter: Optional[ExecutionStatus] = None
    ) -> Dict[str, Any]:
        """
        List state machine executions.

        Args:
            state_machine_id: State machine ID
            page: Page number
            page_size: Items per page
            status_filter: Filter by execution status

        Returns:
            List of executions with pagination info
        """
        params = {"page": page, "page_size": page_size}
        if status_filter:
            params["status_filter"] = status_filter.value

        response = await self.client.get(f"/state-machines/{state_machine_id}/executions", params=params)
        response.raise_for_status()

        return response.json()

    async def get_execution(self, execution_id: str) -> Dict[str, Any]:
        """
        Get state machine execution details.

        Args:
            execution_id: Execution ID

        Returns:
            Execution details
        """
        response = await self.client.get(f"/state-machines/executions/{execution_id}")
        response.raise_for_status()

        return response.json()

    async def send_event(
        self,
        execution_id: str,
        event_type: str,
        event_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send an event to a state machine execution.

        Args:
            execution_id: Execution ID
            event_type: Event type
            event_data: Event data

        Returns:
            True if event sent successfully
        """
        payload = {"event_type": event_type, "event_data": event_data or {}}

        response = await self.client.post(f"/state-machines/executions/{execution_id}/event", json=payload)
        response.raise_for_status()

        result = response.json()
        return result["success"]

    async def cancel_execution(self, execution_id: str) -> bool:
        """
        Cancel a state machine execution.

        Args:
            execution_id: Execution ID

        Returns:
            True if cancelled successfully
        """
        response = await self.client.post(f"/state-machines/executions/{execution_id}/cancel")
        response.raise_for_status()

        result = response.json()
        return result["success"]
