"""Tests for retry and DLQ functionality."""

import asyncio

import pytest

from dotmac.events import (
    ConsumerOptions,
    DLQEntry,
    Event,
    SimpleDLQ,
    create_exponential_retry_options,
    create_memory_bus,
    create_retry_wrapper,
    create_simple_retry_options,
    run_consumer,
)


class TestRetryAndDLQ:
    """Test retry and Dead Letter Queue functionality."""
    
    @pytest.mark.asyncio
    async def test_retry_wrapper_success(self):
        """Test retry wrapper with successful handler."""
        bus = create_memory_bus()
        processed_events = []
        
        async def handler(event: Event) -> None:
            processed_events.append(event)
        
        options = ConsumerOptions(max_retries=3)
        wrapper = create_retry_wrapper(handler, bus, options)
        
        event = Event(topic="test.topic", payload={"key": "value"})
        await wrapper(event)
        
        # Should process successfully without retries
        assert len(processed_events) == 1
        assert processed_events[0] == event
    
    @pytest.mark.asyncio
    async def test_retry_wrapper_with_retries(self):
        """Test retry wrapper with failing handler that eventually succeeds."""
        bus = create_memory_bus()
        call_count = 0
        
        async def failing_handler(event: Event) -> None:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError(f"Failure {call_count}")
        
        options = ConsumerOptions(max_retries=5, backoff_base_ms=10)  # Fast retries
        wrapper = create_retry_wrapper(failing_handler, bus, options)
        
        event = Event(topic="test.topic", payload={"key": "value"})
        await wrapper(event)
        
        # Should have been called 3 times (2 failures + 1 success)
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_wrapper_dlq_after_max_retries(self):
        """Test retry wrapper sends to DLQ after max retries."""
        bus = create_memory_bus()
        
        async def always_failing_handler(event: Event) -> None:
            raise ValueError("Always fails")
        
        options = ConsumerOptions(max_retries=2, backoff_base_ms=10)
        wrapper = create_retry_wrapper(always_failing_handler, bus, options)
        
        event = Event(topic="test.topic", payload={"key": "value"})
        await wrapper(event)
        
        # Should have sent to DLQ
        dlq_queue_size = bus.get_queue_size("test.topic.DLQ")
        assert dlq_queue_size == 1
    
    @pytest.mark.asyncio
    async def test_dlq_event_structure(self):
        """Test structure of DLQ events."""
        bus = create_memory_bus(config=None)
        dlq_events = []
        
        # Subscribe to DLQ topic
        async def dlq_handler(event: Event) -> None:
            dlq_events.append(event)
        
        await bus.subscribe("test.topic.DLQ", dlq_handler)
        
        # Set up failing handler
        async def failing_handler(event: Event) -> None:
            raise ValueError("Test error")
        
        options = ConsumerOptions(max_retries=1, backoff_base_ms=10)
        wrapper = create_retry_wrapper(failing_handler, bus, options)
        
        # Process failing event
        original_event = Event(
            topic="test.topic",
            payload={"key": "value"},
            key="test-key",
            headers={"x-custom": "header"},
            tenant_id="tenant-123",
        )
        await wrapper(original_event)
        
        # Wait for DLQ processing
        await asyncio.sleep(0.1)
        
        # Check DLQ event
        assert len(dlq_events) == 1
        dlq_event = dlq_events[0]
        
        assert dlq_event.topic == "test.topic.DLQ"
        assert dlq_event.payload == original_event.payload
        assert dlq_event.key == original_event.key
        assert dlq_event.tenant_id == original_event.tenant_id
        
        # Check DLQ headers
        assert dlq_event.headers["x-original-topic"] == "test.topic"
        assert dlq_event.headers["x-retry-count"] == "1"
        assert dlq_event.headers["x-error"] == "Test error"
        assert dlq_event.headers["x-error-type"] == "ValueError"
        assert "x-dlq-timestamp" in dlq_event.headers
        # Original headers should be preserved
        assert dlq_event.headers["x-custom"] == "header"
    
    @pytest.mark.asyncio
    async def test_run_consumer_with_retries(self):
        """Test run_consumer with retry options."""
        bus = create_memory_bus()
        processed_events = []
        call_counts = {}
        
        async def handler(event: Event) -> None:
            event_id = str(event.id)
            call_counts[event_id] = call_counts.get(event_id, 0) + 1
            
            # Fail first two attempts
            if call_counts[event_id] <= 2:
                raise ValueError(f"Attempt {call_counts[event_id]} failed")
            
            processed_events.append(event)
        
        options = ConsumerOptions(max_retries=5, backoff_base_ms=10)
        
        # Start consumer (this would normally run indefinitely)
        await run_consumer(bus, "test.topic", handler, options, group="test-group")
        
        # Publish event
        event = Event(topic="test.topic", payload={"key": "value"})
        await bus.publish(event)
        
        # Wait for processing
        await asyncio.sleep(0.2)
        
        # Event should be processed after retries
        assert len(processed_events) == 1
        assert call_counts[str(event.id)] == 3  # 2 failures + 1 success
    
    @pytest.mark.asyncio
    async def test_callback_hooks(self):
        """Test retry and DLQ callback hooks."""
        bus = create_memory_bus()
        retry_calls = []
        dlq_calls = []
        success_calls = []
        
        async def on_retry(event: Event, retry_count: int, error: Exception) -> None:
            retry_calls.append((event, retry_count, str(error)))
        
        async def on_dlq(event: Event, error: Exception) -> None:
            dlq_calls.append((event, str(error)))
        
        async def on_success(event: Event) -> None:
            success_calls.append(event)
        
        # Handler that fails twice then succeeds
        call_count = 0
        
        async def handler(event: Event) -> None:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ValueError(f"Failure {call_count}")
        
        options = ConsumerOptions(
            max_retries=5,
            backoff_base_ms=10,
            on_retry=on_retry,
            on_dlq=on_dlq,
            on_success=on_success,
        )
        
        wrapper = create_retry_wrapper(handler, bus, options)
        event = Event(topic="test.topic", payload={"key": "value"})
        await wrapper(event)
        
        # Check callbacks
        assert len(retry_calls) == 2  # Two retries
        assert len(success_calls) == 1  # Final success
        assert len(dlq_calls) == 0  # No DLQ since it succeeded
        
        assert retry_calls[0][1] == 1  # First retry
        assert retry_calls[1][1] == 2  # Second retry
        assert "Failure" in retry_calls[0][2]  # Error message
    
    @pytest.mark.asyncio
    async def test_simple_dlq_operations(self):
        """Test SimpleDLQ operations."""
        bus = create_memory_bus()
        dlq = SimpleDLQ(bus)
        
        # Send event to DLQ
        original_event = Event(
            topic="test.topic",
            payload={"key": "value"},
            tenant_id="tenant-123",
        )
        error = ValueError("Test error")
        
        await dlq.send_to_dlq(original_event, error, retry_count=3)
        
        # Check DLQ topic has event
        assert bus.get_queue_size("test.topic.DLQ") == 1
    
    @pytest.mark.asyncio
    async def test_dlq_entry_from_event(self):
        """Test creating DLQEntry from DLQ event."""
        # Create DLQ event manually
        original_event = Event(
            topic="original.topic",
            payload={"data": "test"},
            key="test-key",
        )
        
        dlq_event = Event(
            topic="original.topic.DLQ",
            payload=original_event.payload,
            key=original_event.key,
            headers={
                "x-original-topic": "original.topic",
                "x-retry-count": "3",
                "x-error": "Test error",
                "x-error-type": "ValueError",
                "x-dlq-timestamp": "1234567890",
            },
        )
        
        # Create DLQ entry
        dlq_entry = DLQEntry.from_event(dlq_event)
        
        assert dlq_entry.original_topic == "original.topic"
        assert dlq_entry.retry_count == 3
        assert dlq_entry.error == "Test error"
        assert dlq_entry.error_type == "ValueError"
        assert dlq_entry.original_event.topic == "original.topic"
        assert dlq_entry.original_event.payload == {"data": "test"}
    
    @pytest.mark.asyncio
    async def test_dlq_entry_to_event_reprocessing(self):
        """Test converting DLQ entry back to event for reprocessing."""
        original_event = Event(
            topic="original.topic",
            payload={"data": "test"},
        )
        
        # Create DLQ entry
        import time
        from datetime import datetime
        
        dlq_entry = DLQEntry(
            original_event=original_event,
            original_topic="original.topic",
            error="Test error",
            error_type="ValueError",
            retry_count=3,
            first_failure_time=datetime.utcnow(),
            last_failure_time=datetime.utcnow(),
            dlq_topic="original.topic.DLQ",
        )
        
        # Convert back to event
        reprocess_event = dlq_entry.to_event()
        
        assert reprocess_event.topic == "original.topic"
        assert reprocess_event.payload == {"data": "test"}
        assert reprocess_event.headers["x-dlq-reprocessing"] == "true"
        assert reprocess_event.headers["x-original-retry-count"] == "3"
        assert "x-dlq-reprocess-timestamp" in reprocess_event.headers
    
    def test_simple_retry_options(self):
        """Test simple retry options creation."""
        options = create_simple_retry_options(max_retries=5, base_delay_ms=500)
        
        assert options.max_retries == 5
        assert options.backoff_base_ms == 500
        assert options.backoff_multiplier == 1.0  # Fixed delay
        assert options.backoff_jitter_ms == 0
    
    def test_exponential_retry_options(self):
        """Test exponential backoff retry options."""
        options = create_exponential_retry_options(max_retries=3, base_delay_ms=100)
        
        assert options.max_retries == 3
        assert options.backoff_base_ms == 100
        assert options.backoff_multiplier == 2.0
        assert options.backoff_jitter_ms == 50
    
    def test_backoff_calculation(self):
        """Test backoff delay calculation."""
        from dotmac.events.consumer import BackoffPolicy
        
        policy = BackoffPolicy(base_ms=100, multiplier=2.0, jitter_ms=0)
        
        # Test exponential backoff
        assert policy.calculate_delay(0) == 0.1  # 100ms -> 0.1s
        assert policy.calculate_delay(1) == 0.2  # 200ms -> 0.2s  
        assert policy.calculate_delay(2) == 0.4  # 400ms -> 0.4s
        
        # Test maximum delay
        policy_with_max = BackoffPolicy(base_ms=100, multiplier=2.0, max_delay_ms=300, jitter_ms=0)
        assert policy_with_max.calculate_delay(5) == 0.3  # Capped at 300ms
    
    def test_custom_dlq_topic(self):
        """Test custom DLQ topic naming."""
        options = ConsumerOptions(dlq_topic="custom.dlq", max_retries=1)
        
        assert options.get_dlq_topic("any.topic") == "custom.dlq"
        
        # Default naming
        default_options = ConsumerOptions(max_retries=1)
        assert default_options.get_dlq_topic("test.topic") == "test.topic.DLQ"