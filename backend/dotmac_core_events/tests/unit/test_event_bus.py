"""
Unit tests for EventBusSDK.
"""

from datetime import datetime

import pytest

from dotmac_core_events.sdks import EventBusSDK


class TestEventBusSDK:
    """Test cases for EventBusSDK."""

    @pytest.mark.asyncio
    async def test_publish_event(self, event_bus: EventBusSDK, sample_event_data, tenant_id):
        """Test publishing an event."""
        result = await event_bus.publish(
            event_type="user.created",
            data=sample_event_data,
            tenant_id=tenant_id
        )

        assert result.event_id is not None
        assert result.timestamp is not None
        assert isinstance(result.timestamp, datetime)

    @pytest.mark.asyncio
    async def test_publish_with_partition_key(self, event_bus: EventBusSDK, sample_event_data, tenant_id):
        """Test publishing with partition key."""
        result = await event_bus.publish(
            event_type="user.created",
            data=sample_event_data,
            partition_key="user-123",
            tenant_id=tenant_id
        )

        assert result.event_id is not None
        assert result.partition is not None

    @pytest.mark.asyncio
    async def test_publish_with_idempotency_key(self, event_bus: EventBusSDK, sample_event_data, tenant_id):
        """Test publishing with idempotency key."""
        idempotency_key = "unique-key-123"

        # First publish
        result1 = await event_bus.publish(
            event_type="user.created",
            data=sample_event_data,
            tenant_id=tenant_id,
            idempotency_key=idempotency_key
        )

        # Second publish with same key should return same result
        result2 = await event_bus.publish(
            event_type="user.created",
            data=sample_event_data,
            tenant_id=tenant_id,
            idempotency_key=idempotency_key
        )

        assert result1.event_id == result2.event_id

    @pytest.mark.asyncio
    async def test_subscribe_to_events(self, event_bus: EventBusSDK, sample_event_data, tenant_id):
        """Test subscribing to events."""
        # Publish an event first
        await event_bus.publish(
            event_type="user.created",
            data=sample_event_data,
            tenant_id=tenant_id
        )

        # Subscribe and consume
        events_received = []
        async for event in event_bus.subscribe(
            event_types=["user.created"],
            consumer_group="test-group",
            tenant_id=tenant_id
        ):
            events_received.append(event)
            if len(events_received) >= 1:
                break

        assert len(events_received) == 1
        assert events_received[0].event_type == "user.created"
        assert events_received[0].data == sample_event_data

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, event_bus: EventBusSDK, sample_event_data):
        """Test that events are isolated by tenant."""
        tenant1 = "tenant-1"
        tenant2 = "tenant-2"

        # Publish event for tenant 1
        await event_bus.publish(
            event_type="user.created",
            data=sample_event_data,
            tenant_id=tenant1
        )

        # Subscribe as tenant 2 - should not receive tenant 1's events
        events_received = []
        subscription = event_bus.subscribe(
            event_types=["user.created"],
            consumer_group="test-group",
            tenant_id=tenant2
        )

        # Try to consume (should timeout/not receive anything)
        try:
            async for event in subscription:
                events_received.append(event)
                break
        except:
            pass  # Expected to not receive events

        assert len(events_received) == 0

    @pytest.mark.asyncio
    async def test_create_topic(self, event_bus: EventBusSDK, tenant_id):
        """Test creating a topic."""
        await event_bus.create_topic(
            event_type="order.created",
            partitions=5,
            tenant_id=tenant_id
        )

        # Verify topic exists by publishing to it
        result = await event_bus.publish(
            event_type="order.created",
            data={"order_id": "123"},
            tenant_id=tenant_id
        )

        assert result.event_id is not None

    @pytest.mark.asyncio
    async def test_get_topic_info(self, event_bus: EventBusSDK, tenant_id):
        """Test getting topic information."""
        # Create and publish to a topic
        await event_bus.create_topic(
            event_type="product.updated",
            partitions=3,
            tenant_id=tenant_id
        )

        await event_bus.publish(
            event_type="product.updated",
            data={"product_id": "456"},
            tenant_id=tenant_id
        )

        # Get topic info
        info = await event_bus.get_topic_info(
            event_type="product.updated",
            tenant_id=tenant_id
        )

        assert "topic" in info
        assert "partitions" in info or "message_count" in info

    @pytest.mark.asyncio
    async def test_invalid_tenant_id(self, event_bus: EventBusSDK, sample_event_data):
        """Test that invalid tenant ID raises error."""
        with pytest.raises(ValueError, match="Tenant ID cannot be empty"):
            await event_bus.publish(
                event_type="user.created",
                data=sample_event_data,
                tenant_id=""
            )

    @pytest.mark.asyncio
    async def test_invalid_event_type(self, event_bus: EventBusSDK, sample_event_data, tenant_id):
        """Test that invalid event type raises error."""
        with pytest.raises(ValueError, match="Event type cannot be empty"):
            await event_bus.publish(
                event_type="",
                data=sample_event_data,
                tenant_id=tenant_id
            )
