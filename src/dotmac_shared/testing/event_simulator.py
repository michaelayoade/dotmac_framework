"""
Event simulation utilities for testing event-driven architecture
"""
import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


class EventSimulator:
    """
    Simulates events for testing event-driven architecture patterns
    """

    def __init__(self):
        self._published_events = {}
        self._saga_states = {}
        self._event_store = []
        self._failure_injections = {}

    async def publish_event(self, event_type: str, payload: dict[str, Any], correlation_id: str) -> str:
        """Publish an event for testing"""
        event_id = str(uuid.uuid4())
        event = {
            "id": event_id,
            "type": event_type,
            "payload": payload,
            "correlation_id": correlation_id,
            "timestamp": datetime.utcnow().isoformat(),
            "published_at": datetime.utcnow(),
        }

        self._published_events[event_id] = event
        logger.info(f"Published event {event_type} with ID {event_id}")

        # Simulate event processing delay
        await asyncio.sleep(0.05)

        return event_id

    async def publish_and_store_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        correlation_id: str,
        store_in_event_store: bool = False,
    ) -> str:
        """Publish event and optionally store in event store"""
        event_id = await self.publish_event(event_type, payload, correlation_id)

        if store_in_event_store:
            event = self._published_events[event_id]
            self._event_store.append(event.copy())
            logger.info(f"Stored event {event_id} in event store")

        return event_id

    async def start_saga(self, saga_type: str, payload: dict[str, Any]) -> str:
        """Start a saga for testing distributed transactions"""
        saga_id = str(uuid.uuid4())
        saga_state = {
            "id": saga_id,
            "type": saga_type,
            "status": "started",
            "payload": payload,
            "steps_completed": [],
            "compensation_events": [],
            "started_at": datetime.utcnow().isoformat(),
        }

        self._saga_states[saga_id] = saga_state
        logger.info(f"Started saga {saga_type} with ID {saga_id}")

        # Simulate saga progress
        await self._simulate_saga_progress(saga_id)

        return saga_id

    async def _simulate_saga_progress(self, saga_id: str):
        """Simulate saga execution steps"""
        saga = self._saga_states[saga_id]

        # Simulate typical saga steps
        steps = [
            "customer_account_creation",
            "billing_setup",
            "service_provisioning",
            "notification_dispatch",
        ]

        for step in steps:
            await asyncio.sleep(0.1)  # Simulate processing time

            # Check for failure injection
            if self._should_inject_failure(saga_id, step):
                logger.info(f"Injecting failure at step {step} for saga {saga_id}")
                saga["status"] = "failed"
                saga["failed_step"] = step
                await self._execute_compensation(saga_id, step)
                return

            saga["steps_completed"].append({"step": step, "completed_at": datetime.utcnow().isoformat()})

        saga["status"] = "completed"
        saga["completed_at"] = datetime.utcnow().isoformat()

    def _should_inject_failure(self, saga_id: str, step: str) -> bool:
        """Check if failure should be injected at this step"""
        failure_key = f"{saga_id}:{step}"
        return failure_key in self._failure_injections

    async def inject_saga_failure(self, saga_id: str, step: str, failure_type: str):
        """Inject a failure into saga execution"""
        failure_key = f"{saga_id}:{step}"
        self._failure_injections[failure_key] = {
            "type": failure_type,
            "injected_at": datetime.utcnow().isoformat(),
        }
        logger.info(f"Scheduled failure injection for saga {saga_id} at step {step}")

    async def _execute_compensation(self, saga_id: str, failed_step: str):
        """Execute compensation actions for failed saga"""
        saga = self._saga_states[saga_id]
        completed_steps = saga["steps_completed"]

        # Execute compensation in reverse order
        for step_info in reversed(completed_steps):
            compensation_event = {
                "type": f"{step_info['step']}_rollback",
                "saga_id": saga_id,
                "original_step": step_info["step"],
                "executed_at": datetime.utcnow().isoformat(),
            }
            saga["compensation_events"].append(compensation_event)
            await asyncio.sleep(0.05)  # Simulate compensation time

        saga["status"] = "compensated"
        saga["compensated_at"] = datetime.utcnow().isoformat()

    async def simulate_system_restart(self):
        """Simulate system restart for event replay testing"""
        logger.info("Simulating system restart")
        # Clear runtime state but preserve event store
        self._published_events.clear()
        self._saga_states.clear()
        await asyncio.sleep(0.1)

    async def replay_events_from_store(self, correlation_id: str, from_timestamp: datetime) -> list[dict]:
        """Replay events from event store"""
        replayed_events = []

        for event in self._event_store:
            if (
                event.get("correlation_id") == correlation_id
                and datetime.fromisoformat(event["timestamp"]) >= from_timestamp
            ):
                # Simulate replay processing
                replayed_event = event.copy()
                replayed_event["replayed_at"] = datetime.utcnow().isoformat()
                replayed_events.append(replayed_event)

                logger.info(f"Replayed event {event['type']} (ID: {event['id']})")
                await asyncio.sleep(0.02)  # Simulate processing time

        return replayed_events

    def get_published_events(self, correlation_id: Optional[str] = None) -> list[dict]:
        """Get published events, optionally filtered by correlation ID"""
        events = list(self._published_events.values())

        if correlation_id:
            events = [e for e in events if e.get("correlation_id") == correlation_id]

        return sorted(events, key=lambda x: x["published_at"])

    def get_saga_state(self, saga_id: str) -> Optional[dict]:
        """Get current state of a saga"""
        return self._saga_states.get(saga_id)
