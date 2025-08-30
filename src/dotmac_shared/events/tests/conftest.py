"""
Test configuration and fixtures for events package.
"""

import asyncio
from datetime import datetime
from typing import Any, AsyncGenerator, Dict

import pytest

from ..adapters.memory_adapter import MemoryConfig, MemoryEventAdapter
from ..core.event_bus import EventBus
from ..core.models import EventMetadata, EventRecord
from ..sdk.event_bus_sdk import EventBusSDK


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_event_data() -> Dict[str, Any]:
    """Sample event data for testing."""
    return {
        "user_id": "12345",
        "email": "test@example.com",
        "name": "Test User",
        "action": "create",
        "timestamp": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def test_metadata() -> EventMetadata:
    """Sample event metadata for testing."""
    return EventMetadata(
        tenant_id="test-tenant",
        user_id="admin-123",
        source="test-service",
        correlation_id="corr-456",
    )


@pytest.fixture
def test_event_record(test_event_data, test_metadata) -> EventRecord:
    """Sample event record for testing."""
    return EventRecord(
        event_type="user.created",
        data=test_event_data,
        metadata=test_metadata,
        topic="test-events",
    )


@pytest.fixture
async def memory_event_bus() -> AsyncGenerator[EventBus, None]:
    """Create a memory-based event bus for testing."""
    config = MemoryConfig()
    adapter = MemoryEventAdapter(config)
    event_bus = EventBus(adapter)

    await event_bus.start()
    try:
        yield event_bus
    finally:
        await event_bus.stop()


@pytest.fixture
async def event_bus_sdk() -> AsyncGenerator[EventBusSDK, None]:
    """Create an Event Bus SDK for testing."""
    sdk = EventBusSDK.create_memory_bus()

    await sdk.start()
    try:
        yield sdk
    finally:
        await sdk.stop()


@pytest.fixture
def test_schema() -> Dict[str, Any]:
    """Sample JSON Schema for testing."""
    return {
        "type": "object",
        "properties": {
            "user_id": {"type": "string"},
            "email": {"type": "string", "format": "email"},
            "name": {"type": "string"},
            "action": {"type": "string", "enum": ["create", "update", "delete"]},
            "timestamp": {"type": "string", "format": "date-time"},
        },
        "required": ["user_id", "email", "name", "action", "timestamp"],
    }
