"""Tests for memory event bus adapter."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from dotmac.events import Event, MemoryConfig, MemoryEventBus, PublishError, create_memory_bus


class TestMemoryEventBus:
    """Test memory event bus functionality."""
    
    @pytest.fixture
    def bus(self):
        """Create a memory event bus for testing."""
        return create_memory_bus()
    
    @pytest.mark.asyncio
    async def test_create_bus(self):
        """Test bus creation and metadata."""
        bus = create_memory_bus()
        
        assert bus.metadata.name == "memory"
        assert "publish" in bus.metadata.supported_features
        assert "subscribe" in bus.metadata.supported_features
        assert not bus.is_closed
    
    @pytest.mark.asyncio
    async def test_publish_event(self, bus):
        """Test publishing an event."""
        event = Event(
            topic="test.topic",
            payload={"message": "hello world"},
            key="test-key",
        )
        
        await bus.publish(event)
        
        # Check queue size
        assert bus.get_queue_size("test.topic") == 1
        
        # Check stats
        stats = bus.get_stats()
        assert stats["published_count"] == 1
        assert stats["active_topics"] == 1
    
    @pytest.mark.asyncio
    async def test_publish_with_additional_headers(self, bus):
        """Test publishing with additional headers."""
        event = Event(topic="test.topic", payload={"key": "value"})
        
        await bus.publish(event, headers={"x-custom": "header"})
        
        # Event should have been modified with additional headers
        assert bus.get_queue_size("test.topic") == 1
    
    @pytest.mark.asyncio
    async def test_subscribe_and_consume(self, bus):
        """Test subscribing and consuming events."""
        received_events = []
        
        async def handler(event: Event) -> None:
            received_events.append(event)
        
        # Subscribe
        await bus.subscribe("test.topic", handler)
        
        # Publish event
        event = Event(topic="test.topic", payload={"message": "test"})
        await bus.publish(event)
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Check event was received
        assert len(received_events) == 1
        assert received_events[0].topic == "test.topic"
        assert received_events[0].payload["message"] == "test"
    
    @pytest.mark.asyncio
    async def test_consumer_groups(self, bus):
        """Test consumer group functionality."""
        group1_events = []
        group2_events = []
        
        async def group1_handler(event: Event) -> None:
            group1_events.append(event)
        
        async def group2_handler(event: Event) -> None:
            group2_events.append(event)
        
        # Subscribe with different groups
        await bus.subscribe("test.topic", group1_handler, group="group1")
        await bus.subscribe("test.topic", group2_handler, group="group2")
        
        # Publish event
        event = Event(topic="test.topic", payload={"message": "test"})
        await bus.publish(event)
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Both groups should receive the event
        assert len(group1_events) == 1
        assert len(group2_events) == 1
    
    @pytest.mark.asyncio
    async def test_concurrency(self, bus):
        """Test concurrent event handling."""
        processed_events = []
        processing_times = []
        
        async def handler(event: Event) -> None:
            start_time = asyncio.get_event_loop().time()
            await asyncio.sleep(0.05)  # Simulate processing time
            end_time = asyncio.get_event_loop().time()
            
            processed_events.append(event)
            processing_times.append(end_time - start_time)
        
        # Subscribe with concurrency
        await bus.subscribe("test.topic", handler, concurrency=3)
        
        # Publish multiple events
        start_time = asyncio.get_event_loop().time()
        for i in range(5):
            event = Event(topic="test.topic", payload={"index": i})
            await bus.publish(event)
        
        # Wait for all events to be processed
        await asyncio.sleep(0.5)
        
        total_time = asyncio.get_event_loop().time() - start_time
        
        # All events should be processed
        assert len(processed_events) == 5
        
        # With concurrency=3, processing should be faster than sequential
        # Sequential would take ~0.25s (5 * 0.05), concurrent should be faster
        assert total_time < 0.2
    
    @pytest.mark.asyncio
    async def test_request_reply(self, bus):
        """Test request-reply pattern."""
        # Set up reply handler
        async def reply_handler(event: Event) -> None:
            if event.headers and event.headers.get("reply_required") == "true":
                correlation_id = event.headers.get("correlation_id")
                
                reply_event = Event(
                    topic="test.request.reply",
                    payload={"result": event.payload["value"] * 2},
                    headers={"correlation_id": correlation_id},
                )
                await bus.publish(reply_event)
        
        await bus.subscribe("test.request", reply_handler)
        
        # Send request
        response = await bus.request(
            "test.request",
            {"value": 21},
            timeout=1.0
        )
        
        assert response["result"] == 42
    
    @pytest.mark.asyncio
    async def test_queue_full_error(self):
        """Test queue full error handling."""
        config = MemoryConfig(max_queue_size=2)
        bus = MemoryEventBus(config)
        
        # Fill queue
        for i in range(2):
            event = Event(topic="test.topic", payload={"index": i})
            await bus.publish(event)
        
        # Next publish should fail
        with pytest.raises(PublishError, match="queue is full"):
            event = Event(topic="test.topic", payload={"index": 3})
            await bus.publish(event)
    
    @pytest.mark.asyncio
    async def test_event_persistence(self):
        """Test event persistence when enabled."""
        config = MemoryConfig(enable_persistence=True)
        bus = MemoryEventBus(config)
        
        # Publish events
        events = [
            Event(topic="topic1", payload={"index": 1}),
            Event(topic="topic2", payload={"index": 2}),
        ]
        
        for event in events:
            await bus.publish(event)
        
        # Check history
        history = bus.get_event_history()
        assert len(history) == 2
        assert history[0].topic == "topic1"
        assert history[1].topic == "topic2"
    
    @pytest.mark.asyncio
    async def test_handler_error_handling(self, bus):
        """Test error handling in event handlers."""
        processed_events = []
        
        async def failing_handler(event: Event) -> None:
            processed_events.append(event)
            if event.payload.get("should_fail"):
                raise ValueError("Handler error")
        
        await bus.subscribe("test.topic", failing_handler)
        
        # Publish successful event
        success_event = Event(topic="test.topic", payload={"should_fail": False})
        await bus.publish(success_event)
        
        # Publish failing event
        fail_event = Event(topic="test.topic", payload={"should_fail": True})
        await bus.publish(fail_event)
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Both events should be processed (errors are caught)
        assert len(processed_events) == 2
    
    @pytest.mark.asyncio
    async def test_close_bus(self, bus):
        """Test closing the bus."""
        # Subscribe to something
        handler = AsyncMock()
        await bus.subscribe("test.topic", handler)
        
        # Close bus
        await bus.close()
        
        assert bus.is_closed
        
        # Publishing after close should fail
        with pytest.raises(RuntimeError, match="adapter is closed"):
            event = Event(topic="test.topic", payload={"key": "value"})
            await bus.publish(event)
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test using bus as async context manager."""
        async with create_memory_bus() as bus:
            assert not bus.is_closed
            
            event = Event(topic="test.topic", payload={"key": "value"})
            await bus.publish(event)
        
        assert bus.is_closed
    
    @pytest.mark.asyncio
    async def test_multiple_subscriptions_same_topic(self, bus):
        """Test multiple subscriptions to the same topic."""
        events1 = []
        events2 = []
        
        async def handler1(event: Event) -> None:
            events1.append(event)
        
        async def handler2(event: Event) -> None:
            events2.append(event)
        
        # Subscribe with same group - only one should receive
        await bus.subscribe("test.topic", handler1, group="same")
        await bus.subscribe("test.topic", handler2, group="same")
        
        # Publish event
        event = Event(topic="test.topic", payload={"key": "value"})
        await bus.publish(event)
        
        await asyncio.sleep(0.1)
        
        # Only one handler should receive the event (due to same group)
        total_received = len(events1) + len(events2)
        assert total_received == 1
    
    def test_config_to_dict(self):
        """Test configuration serialization."""
        config = MemoryConfig(
            max_queue_size=500,
            enable_persistence=True,
            max_connections=5,
        )
        
        config_dict = config.to_dict()
        
        assert config_dict["max_connections"] == 5
        assert config_dict["enable_metrics"] is True  # Default value
        assert config_dict["enable_tracing"] is True  # Default value