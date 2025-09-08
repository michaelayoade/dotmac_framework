"""
Event tracing utilities for testing event-driven architectures
"""
import asyncio
import logging
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


class EventTracer:
    """
    Traces events across services for integration testing
    """

    def __init__(self):
        self._traced_events = []
        self._active_traces = {}
        self._is_tracing = False

    async def start_tracing(self):
        """Start event tracing"""
        self._is_tracing = True
        self._traced_events.clear()
        logger.info("Started event tracing")

    async def stop_tracing(self):
        """Stop event tracing"""
        self._is_tracing = False
        logger.info(f"Stopped event tracing. Captured {len(self._traced_events)} events")

    async def trace_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        journey_id: Optional[str] = None,
        service_name: Optional[str] = None,
    ):
        """Trace an event"""
        if not self._is_tracing:
            return

        traced_event = {
            "type": event_type,
            "payload": payload.copy(),
            "journey_id": journey_id,
            "service_name": service_name,
            "timestamp": datetime.utcnow().isoformat(),
            "trace_id": len(self._traced_events),
        }

        self._traced_events.append(traced_event)
        logger.debug(f"Traced event: {event_type} from {service_name}")

    async def get_events_by_journey(self, journey_id: str) -> list[dict[str, Any]]:
        """Get all traced events for a specific journey"""
        journey_events = [event for event in self._traced_events if event.get("journey_id") == journey_id]

        # Sort by timestamp
        return sorted(journey_events, key=lambda x: x["timestamp"])

    async def get_events_by_type(self, event_type: str) -> list[dict[str, Any]]:
        """Get all traced events of a specific type"""
        return [event for event in self._traced_events if event["type"] == event_type]

    async def get_events_by_service(self, service_name: str) -> list[dict[str, Any]]:
        """Get all traced events from a specific service"""
        return [event for event in self._traced_events if event.get("service_name") == service_name]

    def get_all_events(self) -> list[dict[str, Any]]:
        """Get all traced events"""
        return self._traced_events.copy()

    async def wait_for_event(
        self, event_type: str, journey_id: Optional[str] = None, timeout: int = 30
    ) -> Optional[dict[str, Any]]:
        """Wait for a specific event to be traced"""
        start_time = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            matching_events = [
                event
                for event in self._traced_events
                if event["type"] == event_type and (journey_id is None or event.get("journey_id") == journey_id)
            ]

            if matching_events:
                return matching_events[-1]  # Return most recent

            await asyncio.sleep(0.1)

        return None

    async def assert_event_sequence(self, expected_sequence: list[str], journey_id: str, timeout: int = 30):
        """Assert that events occurred in the expected sequence"""
        start_time = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            journey_events = await self.get_events_by_journey(journey_id)
            event_types = [event["type"] for event in journey_events]

            # Check if we have all expected events in order
            sequence_matches = True
            for i, expected_type in enumerate(expected_sequence):
                if i >= len(event_types) or event_types[i] != expected_type:
                    sequence_matches = False
                    break

            if sequence_matches and len(event_types) >= len(expected_sequence):
                return True

            await asyncio.sleep(0.1)

        # If we get here, the sequence didn't match
        actual_events = await self.get_events_by_journey(journey_id)
        actual_sequence = [event["type"] for event in actual_events]

        raise AssertionError(
            f"Event sequence mismatch for journey {journey_id}. "
            f"Expected: {expected_sequence}, "
            f"Actual: {actual_sequence}"
        )

    def export_trace_data(self) -> dict[str, Any]:
        """Export trace data for analysis"""
        return {
            "total_events": len(self._traced_events),
            "events": self._traced_events.copy(),
            "export_timestamp": datetime.utcnow().isoformat(),
            "summary": self._generate_trace_summary(),
        }

    def _generate_trace_summary(self) -> dict[str, Any]:
        """Generate summary of traced events"""
        event_counts = {}
        service_counts = {}
        journey_counts = {}

        for event in self._traced_events:
            event_type = event["type"]
            service_name = event.get("service_name", "unknown")
            journey_id = event.get("journey_id", "no_journey")

            event_counts[event_type] = event_counts.get(event_type, 0) + 1
            service_counts[service_name] = service_counts.get(service_name, 0) + 1
            journey_counts[journey_id] = journey_counts.get(journey_id, 0) + 1

        return {
            "events_by_type": event_counts,
            "events_by_service": service_counts,
            "events_by_journey": journey_counts,
        }
