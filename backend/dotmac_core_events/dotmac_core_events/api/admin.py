"""
Admin API endpoints for administrative operations.

Provides REST API for:
- Topic management
- Consumer group management
- Dead letter queue operations
- System maintenance
- Configuration management
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from ..core.dependencies import (
    get_event_bus,
    get_outbox,
    get_schema_registry,
    get_tenant_id,
)
from ..sdks.event_bus import EventBusSDK
from ..sdks.outbox import OutboxSDK
from ..sdks.schema_registry import SchemaRegistrySDK


class CreateTopicRequest(BaseModel):
    """Request model for topic creation."""

    event_type: str = Field(..., description="Event type for the topic")
    partitions: int = Field(3, ge=1, le=100, description="Number of partitions")
    replication_factor: int = Field(2, ge=1, le=10, description="Replication factor")
    retention_hours: int = Field(168, ge=1, description="Message retention in hours")
    cleanup_policy: str = Field("delete", description="Cleanup policy")


class TopicInfo(BaseModel):
    """Topic information model."""

    topic: str = Field(..., description="Topic name")
    event_type: str = Field(..., description="Event type")
    partitions: int = Field(..., description="Number of partitions")
    replication_factor: Optional[int] = Field(None, description="Replication factor")
    retention_hours: Optional[int] = Field(None, description="Retention in hours")
    message_count: Optional[int] = Field(None, description="Total message count")
    size_bytes: Optional[int] = Field(None, description="Topic size in bytes")


class ConsumerGroupInfo(BaseModel):
    """Consumer group information model."""

    group_id: str = Field(..., description="Consumer group ID")
    state: str = Field(..., description="Group state")
    members: int = Field(..., description="Number of members")
    lag: int = Field(..., description="Total lag across all partitions")
    topics: List[str] = Field(..., description="Subscribed topics")


class DLQMessage(BaseModel):
    """Dead letter queue message model."""

    message_id: str = Field(..., description="Message identifier")
    original_topic: str = Field(..., description="Original topic")
    error_reason: str = Field(..., description="Error reason")
    retry_count: int = Field(..., description="Number of retries")
    timestamp: datetime = Field(..., description="Message timestamp")
    payload: Dict[str, Any] = Field(..., description="Message payload")


class AdminAPI:
    """Administrative API endpoints."""

    def __init__(self):
        self.router = APIRouter(prefix="/admin", tags=["admin"])
        self._setup_routes()

    def _setup_routes(self):  # noqa: PLR0915, C901
        """Set up API routes."""

        # Topic Management
        @self.router.post(
            "/topics",
            response_model=TopicInfo,
            status_code=status.HTTP_201_CREATED,
            summary="Create topic",
            description="Create a new event topic"
        )
        async def create_topic(
            request: CreateTopicRequest,
            event_bus: EventBusSDK = Depends(get_event_bus),
            tenant_id: str = Depends(get_tenant_id)
        ) -> TopicInfo:
            """Create a new topic."""
            try:
                await event_bus.create_topic(
                    event_type=request.event_type,
                    partitions=request.partitions,
                    replication_factor=request.replication_factor,
                    retention_hours=request.retention_hours,
                    cleanup_policy=request.cleanup_policy
                )

                topic_name = event_bus._event_type_to_topic(request.event_type)

                return TopicInfo(
                    topic=topic_name,
                    event_type=request.event_type,
                    partitions=request.partitions,
                    replication_factor=request.replication_factor,
                    retention_hours=request.retention_hours
                )

            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create topic"
                )

        @self.router.get(
            "/topics",
            response_model=List[TopicInfo],
            summary="List topics",
            description="List all topics for the tenant"
        )
        async def list_topics(
            event_bus: EventBusSDK = Depends(get_event_bus),
            tenant_id: str = Depends(get_tenant_id)
        ) -> List[TopicInfo]:
            """List all topics."""
            try:
                topics = await event_bus.list_topics()

                topic_infos = []
                for topic in topics:
                    try:
                        info = await event_bus.get_topic_info(topic)
                        topic_infos.append(TopicInfo(
                            topic=topic,
                            event_type=info.get("event_type", "unknown"),
                            partitions=info.get("partitions", 0),
                            replication_factor=info.get("replication_factor"),
                            retention_hours=info.get("retention_hours"),
                            message_count=info.get("message_count"),
                            size_bytes=info.get("size_bytes")
                        ))
                    except Exception:
                        # If we can't get info, just include basic info
                        topic_infos.append(TopicInfo(
                            topic=topic,
                            event_type="unknown",
                            partitions=0
                        ))

                return topic_infos

            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to list topics"
                )

        @self.router.delete(
            "/topics/{topic}",
            status_code=status.HTTP_204_NO_CONTENT,
            summary="Delete topic",
            description="Delete a topic and all its messages"
        )
        async def delete_topic(
            topic: str,
            event_bus: EventBusSDK = Depends(get_event_bus),
            tenant_id: str = Depends(get_tenant_id)
        ):
            """Delete a topic."""
            try:
                await event_bus.delete_topic(topic)
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to delete topic"
                )

        # Consumer Group Management
        @self.router.get(
            "/consumer-groups",
            response_model=List[ConsumerGroupInfo],
            summary="List consumer groups",
            description="List all consumer groups for the tenant"
        )
        async def list_consumer_groups(
            event_bus: EventBusSDK = Depends(get_event_bus),
            tenant_id: str = Depends(get_tenant_id)
        ) -> List[ConsumerGroupInfo]:
            """List consumer groups."""
            try:
                # This would need to be implemented in the EventBusSDK
                # For now, return empty list
                return []

            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to list consumer groups"
                )

        @self.router.delete(
            "/consumer-groups/{group_id}",
            status_code=status.HTTP_204_NO_CONTENT,
            summary="Delete consumer group",
            description="Delete a consumer group and reset its offsets"
        )
        async def delete_consumer_group(
            group_id: str,
            event_bus: EventBusSDK = Depends(get_event_bus),
            tenant_id: str = Depends(get_tenant_id)
        ):
            """Delete a consumer group."""
            try:
                # This would need to be implemented in the EventBusSDK
                pass
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to delete consumer group"
                )

        # Dead Letter Queue Management
        @self.router.get(
            "/dlq/messages",
            response_model=List[DLQMessage],
            summary="List DLQ messages",
            description="List messages in the dead letter queue"
        )
        async def list_dlq_messages(
            limit: int = Query(100, ge=1, le=1000, description="Maximum number of messages"),
            offset: int = Query(0, ge=0, description="Offset for pagination"),
            topic: Optional[str] = Query(None, description="Filter by original topic"),
            tenant_id: str = Depends(get_tenant_id)
        ) -> List[DLQMessage]:
            """List DLQ messages."""
            try:
                # This would integrate with the DLQ handler
                # For now, return empty list
                return []

            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to list DLQ messages: {str(e)}"
                )

        @self.router.post(
            "/dlq/messages/{message_id}/retry",
            status_code=status.HTTP_202_ACCEPTED,
            summary="Retry DLQ message",
            description="Retry a message from the dead letter queue"
        )
        async def retry_dlq_message(
            message_id: str,
            tenant_id: str = Depends(get_tenant_id)
        ) -> Dict[str, str]:
            """Retry a DLQ message."""
            try:
                # This would integrate with the DLQ handler
                return {"status": "accepted", "message_id": message_id}

            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to retry DLQ message: {str(e)}"
                )

        @self.router.delete(
            "/dlq/messages/{message_id}",
            status_code=status.HTTP_204_NO_CONTENT,
            summary="Delete DLQ message",
            description="Permanently delete a message from the dead letter queue"
        )
        async def delete_dlq_message(
            message_id: str,
            tenant_id: str = Depends(get_tenant_id)
        ):
            """Delete a DLQ message."""
            try:
                # This would integrate with the DLQ handler
                pass
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to delete DLQ message: {str(e)}"
                )

        # System Maintenance
        @self.router.post(
            "/maintenance/cleanup",
            summary="Run cleanup",
            description="Run system cleanup tasks"
        )
        async def run_cleanup(
            tenant_id: str = Depends(get_tenant_id),
            outbox: Optional[OutboxSDK] = Depends(get_outbox)
        ) -> Dict[str, Any]:
            """Run system cleanup tasks."""
            try:
                results = {}

                # Cleanup outbox
                if outbox:
                    cleanup_result = await outbox.cleanup_expired_events()
                    results["outbox_cleanup"] = {
                        "cleaned_events": cleanup_result.get("cleaned_count", 0)
                    }

                # Other cleanup tasks would go here

                return {
                    "status": "completed",
                    "timestamp": datetime.now().isoformat(),
                    "results": results
                }

            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to run cleanup: {str(e)}"
                )

        @self.router.post(
            "/maintenance/reset-cache",
            summary="Reset cache",
            description="Reset all caches"
        )
        async def reset_cache(
            tenant_id: str = Depends(get_tenant_id),
            schema_registry: Optional[SchemaRegistrySDK] = Depends(get_schema_registry)
        ) -> Dict[str, str]:
            """Reset all caches."""
            try:
                # Reset schema registry cache
                if schema_registry:
                    await schema_registry.cache.clear()

                return {
                    "status": "completed",
                    "timestamp": datetime.now().isoformat()
                }

            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to reset cache: {str(e)}"
                )

        # Configuration Management
        @self.router.get(
            "/config",
            summary="Get configuration",
            description="Get current system configuration"
        )
        async def get_config(
            tenant_id: str = Depends(get_tenant_id)
        ) -> Dict[str, Any]:
            """Get system configuration."""
            try:
                # This would return current configuration
                return {
                    "tenant_id": tenant_id,
                    "version": "1.0.0",
                    "features": {
                        "event_bus": True,
                        "schema_registry": True,
                        "outbox": True,
                        "dlq": True
                    },
                    "limits": {
                        "max_message_size": 1024 * 1024,  # 1MB
                        "max_batch_size": 100,
                        "max_retention_hours": 168 * 4  # 4 weeks
                    }
                }

            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to get configuration: {str(e)}"
                )
