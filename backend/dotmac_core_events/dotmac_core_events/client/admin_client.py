"""
Admin Client SDK for administrative operations.

Provides a high-level async client for:
- Topic management
- Consumer group management
- Dead letter queue operations
- System maintenance
- Configuration management
"""

from typing import Any, Dict, List, Optional

from .http_client import HTTPClient


class AdminClient:
    """High-level client for administrative operations."""

    def __init__(
        self,
        base_url: str,
        tenant_id: str,
        api_key: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize the admin client.

        Args:
            base_url: Base URL of the API server
            tenant_id: Tenant identifier
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.tenant_id = tenant_id
        self.http_client = HTTPClient(
            base_url=f"{self.base_url}/api/v1/admin",
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

    # Topic Management
    async def create_topic(
        self,
        event_type: str,
        partitions: int = 3,
        replication_factor: int = 2,
        retention_hours: int = 168,
        cleanup_policy: str = "delete"
    ) -> Dict[str, Any]:
        """
        Create a new topic.

        Args:
            event_type: Event type for the topic
            partitions: Number of partitions
            replication_factor: Replication factor
            retention_hours: Message retention in hours
            cleanup_policy: Cleanup policy

        Returns:
            Topic information
        """
        data = {
            "event_type": event_type,
            "partitions": partitions,
            "replication_factor": replication_factor,
            "retention_hours": retention_hours,
            "cleanup_policy": cleanup_policy
        }

        response = await self.http_client.post("/topics", json=data)
        return response

    async def list_topics(self) -> List[Dict[str, Any]]:
        """
        List all topics.

        Returns:
            List of topic information
        """
        response = await self.http_client.get("/topics")
        return response

    async def delete_topic(self, topic: str) -> None:
        """
        Delete a topic.

        Args:
            topic: Topic name to delete
        """
        await self.http_client.delete(f"/topics/{topic}")

    # Consumer Group Management
    async def list_consumer_groups(self) -> List[Dict[str, Any]]:
        """
        List all consumer groups.

        Returns:
            List of consumer group information
        """
        response = await self.http_client.get("/consumer-groups")
        return response

    async def delete_consumer_group(self, group_id: str) -> None:
        """
        Delete a consumer group.

        Args:
            group_id: Consumer group ID to delete
        """
        await self.http_client.delete(f"/consumer-groups/{group_id}")

    # Dead Letter Queue Management
    async def list_dlq_messages(
        self,
        limit: int = 100,
        offset: int = 0,
        topic: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List messages in the dead letter queue.

        Args:
            limit: Maximum number of messages
            offset: Offset for pagination
            topic: Filter by original topic

        Returns:
            List of DLQ messages
        """
        params = {
            "limit": limit,
            "offset": offset
        }
        if topic:
            params["topic"] = topic

        response = await self.http_client.get("/dlq/messages", params=params)
        return response

    async def retry_dlq_message(self, message_id: str) -> Dict[str, str]:
        """
        Retry a message from the dead letter queue.

        Args:
            message_id: Message ID to retry

        Returns:
            Retry status
        """
        response = await self.http_client.post(f"/dlq/messages/{message_id}/retry")
        return response

    async def delete_dlq_message(self, message_id: str) -> None:
        """
        Delete a message from the dead letter queue.

        Args:
            message_id: Message ID to delete
        """
        await self.http_client.delete(f"/dlq/messages/{message_id}")

    # System Maintenance
    async def run_cleanup(self) -> Dict[str, Any]:
        """
        Run system cleanup tasks.

        Returns:
            Cleanup results
        """
        response = await self.http_client.post("/maintenance/cleanup")
        return response

    async def reset_cache(self) -> Dict[str, str]:
        """
        Reset all caches.

        Returns:
            Reset status
        """
        response = await self.http_client.post("/maintenance/reset-cache")
        return response

    # Configuration Management
    async def get_config(self) -> Dict[str, Any]:
        """
        Get current system configuration.

        Returns:
            System configuration
        """
        response = await self.http_client.get("/config")
        return response

    # Bulk Operations
    async def bulk_create_topics(
        self,
        topics: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Create multiple topics in bulk.

        Args:
            topics: List of topic configurations

        Returns:
            List of creation results
        """
        results = []
        for topic_config in topics:
            try:
                result = await self.create_topic(**topic_config)
                results.append({"success": True, "topic": result})
            except Exception as e:
                results.append({
                    "success": False,
                    "error": str(e),
                    "event_type": topic_config.get("event_type")
                })

        return results

    async def bulk_delete_topics(self, topics: List[str]) -> List[Dict[str, Any]]:
        """
        Delete multiple topics in bulk.

        Args:
            topics: List of topic names to delete

        Returns:
            List of deletion results
        """
        results = []
        for topic in topics:
            try:
                await self.delete_topic(topic)
                results.append({"success": True, "topic": topic})
            except Exception as e:
                results.append({
                    "success": False,
                    "error": str(e),
                    "topic": topic
                })

        return results


# Convenience functions
async def create_topic(
    base_url: str,
    tenant_id: str,
    event_type: str,
    partitions: int = 3,
    replication_factor: int = 2,
    retention_hours: int = 168,
    cleanup_policy: str = "delete",
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to create a topic.

    Args:
        base_url: Base URL of the API server
        tenant_id: Tenant identifier
        event_type: Event type for the topic
        partitions: Number of partitions
        replication_factor: Replication factor
        retention_hours: Message retention in hours
        cleanup_policy: Cleanup policy
        api_key: Optional API key for authentication

    Returns:
        Topic information
    """
    async with AdminClient(base_url, tenant_id, api_key) as client:
        return await client.create_topic(
            event_type, partitions, replication_factor, retention_hours, cleanup_policy
        )


async def list_topics(
    base_url: str,
    tenant_id: str,
    api_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Convenience function to list topics.

    Args:
        base_url: Base URL of the API server
        tenant_id: Tenant identifier
        api_key: Optional API key for authentication

    Returns:
        List of topic information
    """
    async with AdminClient(base_url, tenant_id, api_key) as client:
        return await client.list_topics()


async def run_cleanup(
    base_url: str,
    tenant_id: str,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to run system cleanup.

    Args:
        base_url: Base URL of the API server
        tenant_id: Tenant identifier
        api_key: Optional API key for authentication

    Returns:
        Cleanup results
    """
    async with AdminClient(base_url, tenant_id, api_key) as client:
        return await client.run_cleanup()
