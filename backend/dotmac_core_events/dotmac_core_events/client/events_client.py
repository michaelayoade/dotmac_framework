"""
Events Client SDK for high-level event operations.

Provides a high-level async client for:
- Event publishing with metadata support
- Event subscription management
- Event history retrieval
- Event replay operations
- Topic information
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from .http_client import HTTPClient


class EventsClient:
    """High-level client for event operations."""

    def __init__(
        self,
        base_url: str,
        tenant_id: str,
        api_key: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize the events client.

        Args:
            base_url: Base URL of the API server
            tenant_id: Tenant identifier
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.tenant_id = tenant_id
        self.http_client = HTTPClient(
            base_url=f"{self.base_url}/api/v1/events",
            headers={
                "X-Tenant-ID": tenant_id,
                **({"Authorization": f"Bearer {api_key}"} if api_key else {})
            },
            timeout=timeout
        )

    async def __aenter__(self):
        """Async context manager entry."""
        await self.http_client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.http_client.__aexit__(exc_type, exc_val, exc_tb)

    async def publish_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        partition_key: Optional[str] = None,
        event_metadata: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Publish an event.

        Args:
            event_type: Event type identifier
            data: Event payload data
            partition_key: Optional partition key for routing
            event_metadata: Optional event metadata
            idempotency_key: Optional idempotency key

        Returns:
            Publish result with event details
        """
        payload = {
            "event_type": event_type,
            "data": data,
        }

        if partition_key:
            payload["partition_key"] = partition_key
        if event_metadata:
            payload["metadata"] = event_metadata
        if idempotency_key:
            payload["idempotency_key"] = idempotency_key

        response = await self.http_client.post("/publish", json=payload)
        return response

    async def subscribe_to_events(
        self,
        event_types: List[str],
        consumer_group: str,
        auto_commit: bool = True,
        max_poll_records: int = 100,
    ) -> Dict[str, Any]:
        """
        Subscribe to events.

        Args:
            event_types: List of event types to subscribe to
            consumer_group: Consumer group identifier
            auto_commit: Whether to auto-commit offsets
            max_poll_records: Maximum records per poll

        Returns:
            Subscription details
        """
        payload = {
            "event_types": event_types,
            "consumer_group": consumer_group,
            "auto_commit": auto_commit,
            "max_poll_records": max_poll_records,
        }

        response = await self.http_client.post("/subscribe", json=payload)
        return response

    async def unsubscribe_from_events(self, subscription_id: str) -> None:
        """
        Unsubscribe from events.

        Args:
            subscription_id: Subscription identifier to cancel
        """
        payload = {"subscription_id": subscription_id}
        await self.http_client.post("/unsubscribe", json=payload)

    async def get_event_history(
        self,
        event_type: str,
        limit: int = 100,
        offset: int = 0,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get event history.

        Args:
            event_type: Event type to retrieve
            limit: Maximum number of events
            offset: Offset for pagination
            start_time: Start time filter
            end_time: End time filter

        Returns:
            Event history with events and pagination info
        """
        params = {
            "event_type": event_type,
            "limit": limit,
            "offset": offset,
        }

        if start_time:
            params["start_time"] = start_time.isoformat()
        if end_time:
            params["end_time"] = end_time.isoformat()

        response = await self.http_client.get("/history", params=params)
        return response

    async def replay_events(
        self,
        event_type: str,
        start_time: datetime,
        end_time: datetime,
        target_topic: Optional[str] = None,
        speed_multiplier: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Replay historical events.

        Args:
            event_type: Event type to replay
            start_time: Replay start time
            end_time: Replay end time
            target_topic: Optional target topic for replayed events
            speed_multiplier: Replay speed multiplier

        Returns:
            Replay job details
        """
        payload = {
            "event_type": event_type,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "speed_multiplier": speed_multiplier,
        }

        if target_topic:
            payload["target_topic"] = target_topic

        response = await self.http_client.post("/replay", json=payload)
        return response

    async def get_topic_info(self, event_type: str) -> Dict[str, Any]:
        """
        Get topic information.

        Args:
            event_type: Event type to get info for

        Returns:
            Topic information
        """
        response = await self.http_client.get(f"/topics/{event_type}/info")
        return response

    async def batch_publish_events(
        self,
        events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Publish multiple events in batch.

        Args:
            events: List of event dictionaries with event_type, data, etc.

        Returns:
            List of publish results
        """
        results = []
        for event in events:
            try:
                result = await self.publish_event(**event)
                results.append({"success": True, "result": result})
            except Exception as e:
                results.append({
                    "success": False,
                    "error": str(e),
                    "event_type": event.get("event_type")
                })

        return results


# Convenience functions
async def publish_event(
    base_url: str,
    tenant_id: str,
    event_type: str,
    data: Dict[str, Any],
    partition_key: Optional[str] = None,
    event_metadata: Optional[Dict[str, Any]] = None,
    idempotency_key: Optional[str] = None,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to publish an event.

    Args:
        base_url: Base URL of the API server
        tenant_id: Tenant identifier
        event_type: Event type identifier
        data: Event payload data
        partition_key: Optional partition key
        event_metadata: Optional metadata
        idempotency_key: Optional idempotency key
        api_key: Optional API key for authentication

    Returns:
        Publish result
    """
    async with EventsClient(base_url, tenant_id, api_key) as client:
        return await client.publish_event(
            event_type, data, partition_key, event_metadata, idempotency_key
        )


async def subscribe_to_events(
    base_url: str,
    tenant_id: str,
    event_types: List[str],
    consumer_group: str,
    auto_commit: bool = True,
    max_poll_records: int = 100,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to subscribe to events.

    Args:
        base_url: Base URL of the API server
        tenant_id: Tenant identifier
        event_types: Event types to subscribe to
        consumer_group: Consumer group identifier
        auto_commit: Auto-commit offsets
        max_poll_records: Max records per poll
        api_key: Optional API key for authentication

    Returns:
        Subscription details
    """
    async with EventsClient(base_url, tenant_id, api_key) as client:
        return await client.subscribe_to_events(
            event_types, consumer_group, auto_commit, max_poll_records
        )


async def get_event_history(
    base_url: str,
    tenant_id: str,
    event_type: str,
    limit: int = 100,
    offset: int = 0,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to get event history.

    Args:
        base_url: Base URL of the API server
        tenant_id: Tenant identifier
        event_type: Event type to retrieve
        limit: Maximum number of events
        offset: Offset for pagination
        start_time: Start time filter
        end_time: End time filter
        api_key: Optional API key for authentication

    Returns:
        Event history
    """
    async with EventsClient(base_url, tenant_id, api_key) as client:
        return await client.get_event_history(
            event_type, limit, offset, start_time, end_time
        )
