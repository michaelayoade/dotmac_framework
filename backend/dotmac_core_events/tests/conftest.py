"""
Pytest configuration and shared fixtures.
"""

import asyncio
from typing import AsyncGenerator

import pytest

from dotmac_core_events.adapters.memory_adapter import MemoryAdapter, MemoryConfig
from dotmac_core_events.sdks.event_bus import EventBusSDK
from dotmac_core_events.sdks.schema_registry import SchemaRegistrySDK


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def memory_adapter() -> AsyncGenerator[MemoryAdapter, None]:
    """Create a memory adapter for testing."""
    config = MemoryConfig()
    adapter = MemoryAdapter(config)
    await adapter.connect()

    yield adapter

    await adapter.disconnect()


@pytest.fixture
async def event_bus(memory_adapter: MemoryAdapter) -> EventBusSDK:
    """Create an EventBusSDK with memory adapter."""
    return EventBusSDK(adapter=memory_adapter)


@pytest.fixture
async def schema_registry() -> SchemaRegistrySDK:
    """Create a SchemaRegistrySDK."""
    return SchemaRegistrySDK()


@pytest.fixture
def sample_event_data():
    """Sample event data for testing."""
    return {
        "user_id": "123",
        "email": "test@example.com",
        "name": "Test User"
    }


@pytest.fixture
def sample_schema():
    """Sample JSON schema for testing."""
    return {
        "type": "object",
        "properties": {
            "user_id": {"type": "string"},
            "email": {"type": "string", "format": "email"},
            "name": {"type": "string"}
        },
        "required": ["user_id", "email"]
    }


@pytest.fixture
def tenant_id():
    """Sample tenant ID for testing."""
    return "test-tenant-123"
