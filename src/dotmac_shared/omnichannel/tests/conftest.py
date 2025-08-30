"""
Test configuration and fixtures for omnichannel service tests.
"""

import asyncio
from datetime import datetime
from typing import Any, AsyncGenerator, Dict
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from dotmac_shared.omnichannel.core.agent_manager import AgentManager
from dotmac_shared.omnichannel.core.channel_orchestrator import ChannelOrchestrator
from dotmac_shared.omnichannel.core.interaction_manager import InteractionManager
from dotmac_shared.omnichannel.core.routing_engine import RoutingEngine
from dotmac_shared.omnichannel.models.agent import AgentModel, AgentSkill, AgentStatus
from dotmac_shared.omnichannel.models.interaction import (
    InteractionModel,
    InteractionPriority,
    InteractionStatus,
)
from dotmac_shared.omnichannel.models.routing import RoutingResult, RoutingStrategy
from dotmac_shared.plugins import PluginManager, PluginRegistry


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def mock_db_session():
    """Mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    session.close = AsyncMock()
    session.execute = AsyncMock()
    session.scalar = AsyncMock()
    return session


@pytest.fixture
def tenant_id() -> UUID:
    """Sample tenant ID."""
    return uuid4()


@pytest.fixture
def customer_id() -> UUID:
    """Sample customer ID."""
    return uuid4()


@pytest.fixture
def agent_id() -> UUID:
    """Sample agent ID."""
    return uuid4()


@pytest.fixture
def sample_interaction(tenant_id: UUID, customer_id: UUID) -> InteractionModel:
    """Sample interaction for testing."""
    return InteractionModel(
        tenant_id=tenant_id,
        customer_id=customer_id,
        channel="email",
        subject="Test Subject",
        content="Test interaction content",
        priority=InteractionPriority.MEDIUM,
        status=InteractionStatus.OPEN,
        source="customer_portal",
        thread_id=str(uuid4()),
        extra_data={"test_key": "test_value"},
    )


@pytest.fixture
def sample_agent(tenant_id: UUID, agent_id: UUID) -> AgentModel:
    """Sample agent for testing."""
    return AgentModel(
        id=agent_id,
        tenant_id=tenant_id,
        user_id=str(uuid4()),
        full_name="Test Agent",
        email="agent@test.com",
        phone="+1234567890",
        status=AgentStatus.AVAILABLE,
        skills=[
            AgentSkill(name="email", level=5, certified=True),
            AgentSkill(name="technical_support", level=4, certified=True),
        ],
        channels=["email", "chat"],
        max_concurrent_interactions=5,
        current_interaction_count=0,
        location="US",
        timezone="America/New_York",
        extra_data={},
    )


@pytest.fixture
def mock_plugin_manager():
    """Mock plugin manager."""
    manager = Mock(spec=PluginManager)
    manager.get_plugins = Mock(return_value=[])
    manager.get_plugin = Mock(return_value=None)
    manager.load_plugin = AsyncMock()
    manager.unload_plugin = AsyncMock()
    return manager


@pytest.fixture
def mock_plugin_registry():
    """Mock plugin registry."""
    registry = Mock(spec=PluginRegistry)
    registry.get_plugins_by_type = Mock(return_value=[])
    registry.get_plugin = Mock(return_value=None)
    registry.register_plugin = Mock()
    return registry


@pytest.fixture
async def interaction_manager(mock_db_session, tenant_id):
    """Interaction manager instance."""
    manager = InteractionManager(tenant_id=tenant_id)
    manager._db_session_factory = lambda: mock_db_session
    return manager


@pytest.fixture
async def routing_engine(tenant_id):
    """Routing engine instance."""
    return RoutingEngine(tenant_id=tenant_id)


@pytest.fixture
async def agent_manager(mock_db_session, tenant_id):
    """Agent manager instance."""
    manager = AgentManager(tenant_id=tenant_id)
    manager._db_session_factory = lambda: mock_db_session
    return manager


@pytest.fixture
async def channel_orchestrator(tenant_id, mock_plugin_manager, mock_plugin_registry):
    """Channel orchestrator instance."""
    orchestrator = ChannelOrchestrator(tenant_id=tenant_id)
    # Mock the plugin system components
    orchestrator.plugin_manager.plugin_manager = mock_plugin_manager
    orchestrator.plugin_manager.plugin_registry = mock_plugin_registry
    return orchestrator


@pytest.fixture
def mock_message():
    """Mock message for testing."""
    return {
        "id": str(uuid4()),
        "recipient": "test@example.com",
        "subject": "Test Message",
        "content": "Test message content",
        "channel": "email",
        "sender_id": str(uuid4()),
        "template_id": None,
        "metadata": {"test": "data"},
    }


@pytest.fixture
def mock_communication_plugin():
    """Mock communication plugin."""
    plugin = Mock()
    plugin.plugin_id = "test_email_plugin"
    plugin.channel_type = "email"
    plugin.send_message = AsyncMock()
    plugin.get_delivery_status = AsyncMock()
    plugin.validate_configuration = Mock(return_value=True)
    plugin.get_health_status = AsyncMock()
    return plugin


@pytest.fixture
def sample_routing_config():
    """Sample routing configuration."""
    return {
        "strategy": "skill_based",
        "rules": [
            {
                "condition": {"channel": "email", "priority": "high"},
                "action": {"assign_to_team": "senior_support"},
            }
        ],
        "fallback": {"strategy": "round_robin", "team": "general_support"},
    }
