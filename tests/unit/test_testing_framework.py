"""
Unit tests for the testing framework components
"""
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from dotmac.communications.events.message import Event as EventType
from dotmac_shared.models.customer import Customer, CustomerTier
from dotmac_shared.testing.event_simulator import EventSimulator
from dotmac_shared.testing.event_tracer import EventTracer
from dotmac_shared.testing.integration_base import IntegrationTestBase
from dotmac_shared.testing.service_clients import ServiceClientManager


@pytest.mark.unit
class TestEventSimulator:
    """Test event simulator functionality"""
    
    @pytest.fixture
    def event_simulator(self):
        return EventSimulator()
    
    @pytest.mark.asyncio
    async def test_publish_event(self, event_simulator):
        """Test basic event publishing"""
        correlation_id = str(uuid.uuid4())
        payload = {"customer_id": "test_customer", "email": "test@example.com"}
        
        event_id = await event_simulator.publish_event(
            EventType.CUSTOMER_CREATED.value,
            payload,
            correlation_id
        )
        
        assert event_id is not None
        assert isinstance(event_id, str)
        
        # Check event was stored
        events = event_simulator.get_published_events(correlation_id)
        assert len(events) == 1
        assert events[0]["type"] == EventType.CUSTOMER_CREATED.value
        assert events[0]["payload"] == payload
        assert events[0]["correlation_id"] == correlation_id
    
    @pytest.mark.asyncio
    async def test_saga_creation(self, event_simulator):
        """Test saga creation and state management"""
        payload = {"customer_email": "test@example.com"}
        
        saga_id = await event_simulator.start_saga("customer_onboarding_saga", payload)
        
        assert saga_id is not None
        saga_state = event_simulator.get_saga_state(saga_id)
        
        assert saga_state["id"] == saga_id
        assert saga_state["type"] == "customer_onboarding_saga"
        assert saga_state["payload"] == payload
        assert saga_state["status"] in ["started", "completed", "failed"]


@pytest.mark.unit
class TestEventTracer:
    """Test event tracing functionality"""
    
    @pytest.fixture
    def event_tracer(self):
        return EventTracer()
    
    @pytest.mark.asyncio
    async def test_event_tracing(self, event_tracer):
        """Test basic event tracing"""
        await event_tracer.start_tracing()
        
        journey_id = str(uuid.uuid4())
        
        await event_tracer.trace_event(
            "customer.created",
            {"customer_id": "test_customer"},
            journey_id=journey_id,
            service_name="customer_service"
        )
        
        await event_tracer.trace_event(
            "billing.account_created",
            {"customer_id": "test_customer", "account_id": "test_account"},
            journey_id=journey_id,
            service_name="billing_service"
        )
        
        # Get events by journey
        journey_events = await event_tracer.get_events_by_journey(journey_id)
        assert len(journey_events) == 2
        assert journey_events[0]["type"] == "customer.created"
        assert journey_events[1]["type"] == "billing.account_created"
        
        await event_tracer.stop_tracing()
    
    @pytest.mark.asyncio
    async def test_event_sequence_validation(self, event_tracer):
        """Test event sequence validation"""
        await event_tracer.start_tracing()
        
        journey_id = str(uuid.uuid4())
        
        # Trace events in sequence
        await event_tracer.trace_event("customer.created", {}, journey_id=journey_id)
        await event_tracer.trace_event("billing.account_created", {}, journey_id=journey_id)
        await event_tracer.trace_event("service.provisioned", {}, journey_id=journey_id)
        
        # This should pass - events are in correct order
        await event_tracer.assert_event_sequence(
            ["customer.created", "billing.account_created", "service.provisioned"],
            journey_id
        )
        
        await event_tracer.stop_tracing()


@pytest.mark.unit 
class TestServiceClientManager:
    """Test service client management"""
    
    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Test service client initialization"""
        manager = ServiceClientManager()
        
        # Mock the HTTP client initialization
        with patch('dotmac_shared.testing.service_clients.httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value = mock_instance
            
            await manager.initialize_clients(['isp_service', 'billing_service'])
            
            assert 'isp_service' in manager.clients
            assert 'billing_service' in manager.clients
            assert manager.isp_service is not None
            assert manager.billing_service is not None
        
        await manager.cleanup()


@pytest.mark.unit
class TestModels:
    """Test model definitions"""
    
    def test_customer_model_creation(self):
        """Test customer model instantiation"""
        customer = Customer(
            id="test_customer_123",
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            tier=CustomerTier.PREMIUM
        )
        
        assert customer.id == "test_customer_123"
        assert customer.email == "test@example.com"
        assert customer.tier == CustomerTier.PREMIUM
        assert customer.status.value == "pending_verification"
    
    def test_event_types_definition(self):
        """Test event type enumeration"""
        # Verify we have the expected event types
        assert EventType.CUSTOMER_CREATED.value == "customer.created"
        assert EventType.BILLING_ACCOUNT_CREATED.value == "billing_account.created"
        assert EventType.SERVICE_PROVISIONING_STARTED.value == "service.provisioning_started"
        
        # Count available event types
        event_types = list(EventType)
        assert len(event_types) >= 30  # We expect a good number of event types


@pytest.mark.unit
class TestIntegrationBase:
    """Test integration test base class"""
    
    @pytest.mark.asyncio
    async def test_test_customer_creation(self):
        """Test test customer creation utility"""
        base = IntegrationTestBase()
        
        customer = await base.create_test_customer(
            email="specific@example.com",
            first_name="Jane"
        )
        
        assert customer["email"] == "specific@example.com"
        assert customer["first_name"] == "Jane"
        assert customer["last_name"] == "Customer"  # Default value
        assert "id" in customer
        assert "created_at" in customer