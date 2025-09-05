"""
Base adapter interface for event streaming backends.

Defines the abstract interface that all event adapters must implement:
- Event publishing and consumption
- Topic management
- Consumer group management
- Offset management
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class AdapterConfig(BaseModel):
    """Base configuration for event adapters."""

    connection_string: str
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0

    model_config = ConfigDict(extra="allow")


class EventRecord(BaseModel):
    """Event record model for adapter interface."""

    event_id: str
    event_type: str
    data: dict[str, Any]
    partition_key: Optional[str] = None
    timestamp: datetime
    offset: Optional[str] = None
    partition: Optional[int] = None
    headers: Optional[dict[str, str]] = None


class PublishResult(BaseModel):
    """Result of publishing an event."""

    event_id: str
    partition: Optional[int] = None
    offset: Optional[str] = None
    timestamp: datetime


class ConsumerRecord(BaseModel):
    """Consumer record with offset information."""

    event: EventRecord
    offset: str
    partition: int
    topic: str


class EventAdapter(ABC):
    """
    Abstract base class for event streaming adapters.

    All event adapters must implement this interface to provide
    consistent event streaming capabilities across different backends.
    """

    def __init__(self, config: AdapterConfig):
        """Initialize the adapter with configuration."""
        self.config = config

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the event streaming backend."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the event streaming backend."""
        pass

    @abstractmethod
    async def publish(
        self, topic: str, event: EventRecord, partition_key: Optional[str] = None
    ) -> PublishResult:
        """
        Publish an event to a topic.

        Args:
            topic: Target topic name
            event: Event to publish
            partition_key: Optional partition key for routing

        Returns:
            Publish result with metadata
        """
        pass

    @abstractmethod
    async def subscribe(
        self, topics: list[str], consumer_group: str, auto_commit: bool = True
    ) -> AsyncIterator[ConsumerRecord]:
        """
        Subscribe to topics and yield consumed events.

        Args:
            topics: List of topic names to subscribe to
            consumer_group: Consumer group identifier
            auto_commit: Whether to auto-commit offsets

        Yields:
            Consumer records with events and offset information
        """
        pass

    @abstractmethod
    async def commit_offset(
        self, consumer_group: str, topic: str, partition: int, offset: str
    ) -> None:
        """
        Manually commit an offset for a consumer group.

        Args:
            consumer_group: Consumer group identifier
            topic: Topic name
            partition: Partition number
            offset: Offset to commit
        """
        pass

    @abstractmethod
    async def create_topic(
        self,
        topic: str,
        partitions: int = 3,
        replication_factor: int = 2,
        config: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Create a new topic.

        Args:
            topic: Topic name
            partitions: Number of partitions
            replication_factor: Replication factor
            config: Additional topic configuration
        """
        pass

    @abstractmethod
    async def delete_topic(self, topic: str) -> None:
        """
        Delete a topic.

        Args:
            topic: Topic name to delete
        """
        pass

    @abstractmethod
    async def list_topics(self) -> list[str]:
        """
        List all available topics.

        Returns:
            List of topic names
        """
        pass

    @abstractmethod
    async def get_topic_info(self, topic: str) -> dict[str, Any]:
        """
        Get information about a topic.

        Args:
            topic: Topic name

        Returns:
            Topic information dictionary
        """
        pass

    @abstractmethod
    async def list_consumer_groups(self) -> list[dict[str, Any]]:
        """
        List all consumer groups.

        Returns:
            List of consumer group information
        """
        pass

    @abstractmethod
    async def delete_consumer_group(self, group_id: str) -> None:
        """
        Delete a consumer group.

        Args:
            group_id: Consumer group ID to delete
        """
        pass

    @abstractmethod
    async def get_consumer_group_info(self, group_id: str) -> dict[str, Any]:
        """
        Get information about a consumer group.

        Args:
            group_id: Consumer group ID

        Returns:
            Consumer group information
        """
        pass

    @abstractmethod
    async def seek_to_beginning(
        self, consumer_group: str, topic: str, partition: Optional[int] = None
    ) -> None:
        """
        Seek consumer group to the beginning of a topic/partition.

        Args:
            consumer_group: Consumer group identifier
            topic: Topic name
            partition: Partition number (all partitions if None)
        """
        pass

    @abstractmethod
    async def seek_to_end(
        self, consumer_group: str, topic: str, partition: Optional[int] = None
    ) -> None:
        """
        Seek consumer group to the end of a topic/partition.

        Args:
            consumer_group: Consumer group identifier
            topic: Topic name
            partition: Partition number (all partitions if None)
        """
        pass

    @abstractmethod
    async def seek_to_offset(
        self, consumer_group: str, topic: str, partition: int, offset: str
    ) -> None:
        """
        Seek consumer group to a specific offset.

        Args:
            consumer_group: Consumer group identifier
            topic: Topic name
            partition: Partition number
            offset: Target offset
        """
        pass

    @abstractmethod
    async def get_latest_offset(self, topic: str, partition: int) -> str:
        """
        Get the latest offset for a topic partition.

        Args:
            topic: Topic name
            partition: Partition number

        Returns:
            Latest offset
        """
        pass

    @abstractmethod
    async def get_earliest_offset(self, topic: str, partition: int) -> str:
        """
        Get the earliest offset for a topic partition.

        Args:
            topic: Topic name
            partition: Partition number

        Returns:
            Earliest offset
        """
        pass

    async def health_check(self) -> dict[str, Any]:
        """
        Perform a health check on the adapter.

        Returns:
            Health check result
        """
        try:
            # Try to list topics as a basic connectivity test
            topics = await self.list_topics()
            return {
                "status": "healthy",
                "message": "Adapter is connected and responsive",
                "topics_count": len(topics),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Adapter health check failed: {str(e)}",
            }
