"""
Tests for DotMac Events package.

Comprehensive test suite covering:
- Event models and validation
- Event bus operations
- Adapter implementations (memory, Redis, Kafka)
- Outbox pattern functionality
- Schema registry operations
- SDK layer convenience APIs
"""

import asyncio
from typing import AsyncGenerator

# Test configuration
import pytest

# Make test fixtures available
from .conftest import (
    event_loop,
    memory_event_bus,
    test_event_data,
    test_metadata,
    test_schema,
)

__all__ = [
    "event_loop",
    "memory_event_bus",
    "test_event_data",
    "test_metadata",
    "test_schema",
]
