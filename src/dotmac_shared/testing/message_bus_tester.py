"""
Message bus testing utilities for event-driven architecture validation
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class MessageBusTester:
    """
    Utilities for testing message bus functionality and event processing
    """

    def __init__(self):
        self._queue_connections = {}
        self._collected_events = {}
        self._event_processing_logs = []
        self._saga_states = {}
        self._system_state_snapshots = {}

    async def connect_to_all_queues(self, queue_names: list[str]):
        """Connect to all specified message queues"""
        for queue_name in queue_names:
            # In a real implementation, this would connect to RabbitMQ/Redis/etc.
            self._queue_connections[queue_name] = {
                "connected_at": datetime.utcnow().isoformat(),
                "queue_name": queue_name,
                "status": "connected",
            }
            logger.info(f"Connected to queue: {queue_name}")

    async def cleanup(self):
        """Cleanup all queue connections"""
        for queue_name in list(self._queue_connections.keys()):
            await self._disconnect_from_queue(queue_name)
        logger.info("Cleaned up all message bus connections")

    async def _disconnect_from_queue(self, queue_name: str):
        """Disconnect from a specific queue"""
        if queue_name in self._queue_connections:
            del self._queue_connections[queue_name]
            logger.info(f"Disconnected from queue: {queue_name}")

    async def collect_events_by_correlation(
        self, correlation_id: str, timeout: int = 30
    ) -> list[dict[str, Any]]:
        """Collect all events with a specific correlation ID"""
        events = []
        start_time = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            # Simulate collecting events from message queues
            # In real implementation, this would poll queues or use event listeners
            await asyncio.sleep(0.1)

            # For testing, return mock events
            if correlation_id not in self._collected_events:
                self._collected_events[correlation_id] = self._generate_mock_events(
                    correlation_id
                )

            events = self._collected_events[correlation_id]
            if len(events) > 0:
                break

        return events

    def _generate_mock_events(self, correlation_id: str) -> list[dict[str, Any]]:
        """Generate mock events for testing"""
        mock_events = [
            {
                "type": "billing_account_creation_requested",
                "correlation_id": correlation_id,
                "timestamp": (datetime.utcnow() + timedelta(seconds=1)).isoformat(),
                "payload": {"customer_id": f"cust_{correlation_id}"},
            },
            {
                "type": "welcome_email_queued",
                "correlation_id": correlation_id,
                "timestamp": (datetime.utcnow() + timedelta(seconds=2)).isoformat(),
                "payload": {"customer_id": f"cust_{correlation_id}"},
            },
        ]
        return mock_events

    async def query_downstream_state(
        self, service_name: str, query_params: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Query downstream service state"""
        # Mock implementation for testing
        if service_name == "customer_service":
            return [{"id": "customer_123", "email": query_params.get("email")}]
        elif service_name == "billing_service":
            return [
                {"id": "billing_123", "customer_id": query_params.get("customer_id")}
            ]
        return []

    async def get_event_processing_logs(
        self, correlation_id: str
    ) -> list[dict[str, Any]]:
        """Get event processing logs for debugging"""
        logs = [
            {
                "level": "INFO",
                "message": f"Processing event for correlation {correlation_id}",
                "timestamp": datetime.utcnow().isoformat(),
            },
            {
                "level": "WARN",
                "message": f"duplicate_event_detected for correlation {correlation_id}",
                "timestamp": datetime.utcnow().isoformat(),
            },
        ]
        return logs

    async def get_retry_logs(self, event_id: str) -> list[dict[str, Any]]:
        """Get retry logs for a specific event"""
        retry_logs = [
            {
                "event_id": event_id,
                "retry_attempt": 1,
                "error": "Connection timeout",
                "timestamp": datetime.utcnow().isoformat(),
            },
            {
                "event_id": event_id,
                "retry_attempt": 2,
                "error": "Service unavailable",
                "timestamp": (datetime.utcnow() + timedelta(seconds=5)).isoformat(),
            },
            {
                "event_id": event_id,
                "retry_attempt": 3,
                "error": "Validation failed",
                "timestamp": (datetime.utcnow() + timedelta(seconds=10)).isoformat(),
            },
        ]
        return retry_logs

    async def get_dead_letter_events(self, correlation_id: str) -> list[dict[str, Any]]:
        """Get events that ended up in dead letter queue"""
        dead_letter_events = [
            {
                "original_event_id": "event_123",
                "correlation_id": correlation_id,
                "failure_reason": "Max retries exceeded: Validation failed",
                "retry_count": 3,
                "dead_lettered_at": datetime.utcnow().isoformat(),
            }
        ]
        return dead_letter_events

    async def get_saga_state(self, saga_id: str) -> dict[str, Any]:
        """Get current state of a saga"""
        # Mock saga state for testing
        return {
            "id": saga_id,
            "status": "compensated",
            "steps_completed": ["customer_account_creation"],
            "compensation_steps": ["customer_account_rollback"],
            "updated_at": datetime.utcnow().isoformat(),
        }

    async def get_saga_compensation_events(self, saga_id: str) -> list[dict[str, Any]]:
        """Get compensation events for a saga"""
        compensation_events = [
            {
                "type": "service_provisioning_rollback",
                "saga_id": saga_id,
                "executed_at": datetime.utcnow().isoformat(),
            },
            {
                "type": "customer_account_rollback",
                "saga_id": saga_id,
                "executed_at": (datetime.utcnow() + timedelta(seconds=1)).isoformat(),
            },
        ]
        return compensation_events

    async def get_event_status(self, event_id: str) -> dict[str, Any]:
        """Get processing status of a specific event"""
        # Mock different statuses for testing
        if "rejected" in event_id:
            return {
                "event_id": event_id,
                "status": "rejected",
                "rejection_reason": "circuit_breaker_open",
                "rejected_at": datetime.utcnow().isoformat(),
            }
        else:
            return {
                "event_id": event_id,
                "status": "completed",
                "processed_at": datetime.utcnow().isoformat(),
            }

    async def capture_system_state(self, entity_id: str) -> dict[str, Any]:
        """Capture current system state for an entity"""
        # Mock system state capture
        state = {
            "customer": {"id": entity_id, "tier": "premium", "status": "active"},
            "service": {"status": "suspended", "bandwidth_allocated": 1000},
            "billing": {
                "last_payment": "2023-01-15T10:00:00Z",
                "outstanding_amount": 0.0,
            },
            "captured_at": datetime.utcnow().isoformat(),
        }

        self._system_state_snapshots[entity_id] = state
        return state
