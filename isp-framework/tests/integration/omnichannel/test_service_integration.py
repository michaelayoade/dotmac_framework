"""
Integration Tests for Omnichannel Services

TESTING IMPROVEMENT: Integration tests for decomposed omnichannel services
to ensure they work together correctly and maintain the same functionality
as the original monolithic service.
"""

import pytest
from unittest.mock import Mock
from uuid import uuid4
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from dotmac_isp.modules.omnichannel.services import (
    ContactService,
    InteractionService,
    AgentService,
    RoutingService,
    AnalyticsService,
    OmnichannelOrchestrator
)
from dotmac_isp.modules.omnichannel.models import (
    CustomerContact,
    ContactType,
    CommunicationInteraction,
    InteractionType,
    InteractionStatus,
    OmnichannelAgent,
    AgentStatus
)
from dotmac_isp.modules.omnichannel.schemas import (
    CustomerContactCreate,
    CommunicationInteractionCreate,
    OmnichannelAgentCreate
)


class TestOmnichannelServiceIntegration:
    """Integration tests for omnichannel services working together."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def orchestrator(self, mock_db):
        """Create omnichannel orchestrator with all services."""
        return OmnichannelOrchestrator(mock_db, tenant_id="tenant_123")
    
    @pytest.fixture
    def sample_customer_id(self):
        """Sample customer ID."""
        return uuid4()
    
    @pytest.fixture
    def sample_agent_data(self):
        """Sample agent creation data."""
        return OmnichannelAgentCreate(
            user_id=uuid4(),
            employee_id="EMP001",
            display_name="Agent Smith",
            skills=["email", "chat", "phone"],
            max_concurrent_interactions=5
        )
    
    @pytest.mark.asyncio
    async def test_complete_customer_interaction_workflow(self, orchestrator, sample_customer_id):
        """Test complete workflow from contact creation to interaction resolution."""
        # Mock all repository methods to avoid database calls
        orchestrator.contact_service.contact_repository = Mock()
        orchestrator.interaction_service.interaction_repository = Mock()
        orchestrator.agent_service.agent_repository = Mock()
        orchestrator.routing_service.routing_repository = Mock()
        
        # Step 1: Create customer contact
        contact_data = CustomerContactCreate(
            customer_id=sample_customer_id,
            contact_type=ContactType.PRIMARY,
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com"
        )
        
        mock_contact = CustomerContact(
            id=uuid4(),
            **contact_data.dict(),
            tenant_id="tenant_123"
        )
        orchestrator.contact_service.contact_repository.create.return_value = mock_contact
        
        contact_id = await orchestrator.create_customer_contact(contact_data)
        assert contact_id == mock_contact.id
        
        # Step 2: Create agent
        agent_data = OmnichannelAgentCreate(
            user_id=uuid4(),
            employee_id="EMP001",
            display_name="Agent Smith",
            skills=["email", "chat"],
            max_concurrent_interactions=5
        )
        
        mock_agent = OmnichannelAgent(
            id=uuid4(),
            **agent_data.dict(),
            status=AgentStatus.AVAILABLE,
            tenant_id="tenant_123"
        )
        orchestrator.agent_service.agent_repository.create.return_value = mock_agent
        
        agent_id = await orchestrator.create_agent(agent_data)
        assert agent_id == mock_agent.id
        
        # Step 3: Create interaction
        interaction_data = CommunicationInteractionCreate(
            customer_id=sample_customer_id,
            contact_id=contact_id,
            interaction_type=InteractionType.EMAIL,
            subject="Support Request",
            content="I need help with my account",
            metadata={"priority": "high"}
        )
        
        mock_interaction = CommunicationInteraction(
            id=uuid4(),
            **interaction_data.dict(),
            status=InteractionStatus.OPEN,
            tenant_id="tenant_123"
        )
        orchestrator.interaction_service.interaction_repository.create.return_value = mock_interaction
        orchestrator.routing_service._route_interaction = Mock(return_value=mock_agent.id)
        
        interaction_id = await orchestrator.create_interaction(interaction_data)
        assert interaction_id == mock_interaction.id
        
        # Verify routing was called
        orchestrator.routing_service._route_interaction.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_agent_workload_management_integration(self, orchestrator):
        """Test agent workload management across services."""
        # Mock repositories
        orchestrator.agent_service.agent_repository = Mock()
        orchestrator.analytics_service.metrics_repository = Mock()
        
        agent_id = uuid4()
        
        # Mock agent data
        mock_agent = OmnichannelAgent(
            id=agent_id,
            user_id=uuid4(),
            employee_id="EMP001",
            display_name="Agent Smith",
            status=AgentStatus.AVAILABLE,
            current_workload=2,
            max_concurrent_interactions=5
        )
        
        orchestrator.agent_service.agent_repository.get_by_id.return_value = mock_agent
        orchestrator.agent_service.agent_repository.update.return_value = mock_agent
        
        # Test workload increase
        result = await orchestrator.agent_service.update_agent_workload(agent_id, 1)
        
        # Verify update was called
        orchestrator.agent_service.agent_repository.update.assert_called_once()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_analytics_data_aggregation(self, orchestrator):
        """Test analytics service aggregating data from other services."""
        # Mock repositories for analytics
        orchestrator.analytics_service.interaction_repository = Mock()
        orchestrator.analytics_service.agent_repository = Mock()
        
        # Mock interaction data for analytics
        mock_interactions = [
            CommunicationInteraction(
                id=uuid4(),
                customer_id=uuid4(),
                interaction_type=InteractionType.EMAIL,
                status=InteractionStatus.RESOLVED,
                created_at=datetime.utcnow() - timedelta(days=1),
                resolved_at=datetime.utcnow()
            ),
            CommunicationInteraction(
                id=uuid4(),
                customer_id=uuid4(),
                interaction_type=InteractionType.CHAT,
                status=InteractionStatus.RESOLVED,
                created_at=datetime.utcnow() - timedelta(hours=2),
                resolved_at=datetime.utcnow() - timedelta(hours=1)
            )
        ]
        
        orchestrator.analytics_service.interaction_repository.list.return_value = mock_interactions
        
        # Test dashboard stats generation
        stats = await orchestrator.get_dashboard_stats()
        
        # Verify analytics aggregation
        orchestrator.analytics_service.interaction_repository.list.assert_called()
        assert isinstance(stats, dict)
        # Stats would contain aggregated data from multiple interactions
    
    @pytest.mark.asyncio
    async def test_cross_service_error_handling(self, orchestrator):
        """Test error handling when services depend on each other."""
        # Mock a failure in contact service
        orchestrator.contact_service.contact_repository = Mock()
        orchestrator.contact_service.contact_repository.create.side_effect = Exception("Database error")
        
        contact_data = CustomerContactCreate(
            customer_id=uuid4(),
            contact_type=ContactType.PRIMARY,
            first_name="John",
            last_name="Doe",
            email="john@example.com"
        )
        
        # Verify error propagation
        with pytest.raises(Exception, match="Database error"):
            await orchestrator.create_customer_contact(contact_data)
    
    @pytest.mark.asyncio
    async def test_tenant_isolation_across_services(self, mock_db):
        """Test that tenant isolation works across all services."""
        # Create orchestrators for different tenants
        orchestrator1 = OmnichannelOrchestrator(mock_db, tenant_id="tenant_1")
        orchestrator2 = OmnichannelOrchestrator(mock_db, tenant_id="tenant_2")
        
        # Verify tenant IDs are properly set
        assert orchestrator1.tenant_id == "tenant_1"
        assert orchestrator2.tenant_id == "tenant_2"
        
        # Verify all services inherit correct tenant IDs
        assert orchestrator1.contact_service.tenant_id == "tenant_1"
        assert orchestrator1.interaction_service.tenant_id == "tenant_1"
        assert orchestrator1.agent_service.tenant_id == "tenant_1"
        
        assert orchestrator2.contact_service.tenant_id == "tenant_2"
        assert orchestrator2.interaction_service.tenant_id == "tenant_2"
        assert orchestrator2.agent_service.tenant_id == "tenant_2"
    
    @pytest.mark.asyncio
    async def test_service_coordination_through_orchestrator(self, orchestrator):
        """Test that orchestrator properly coordinates between services."""
        # Mock all service methods
        orchestrator.contact_service.create_customer_contact = Mock(return_value=uuid4())
        orchestrator.agent_service.get_available_agents = Mock(return_value=[])
        orchestrator.routing_service.create_routing_rule = Mock(return_value=uuid4())
        orchestrator.analytics_service.calculate_agent_performance = Mock(return_value={})
        
        # Test coordinated operations
        contact_data = CustomerContactCreate(
            customer_id=uuid4(),
            contact_type=ContactType.PRIMARY,
            first_name="Test",
            last_name="User",
            email="test@example.com"
        )
        
        # Create contact through orchestrator
        contact_id = await orchestrator.create_customer_contact(contact_data)
        
        # Verify service was called
        orchestrator.contact_service.create_customer_contact.assert_called_once_with(contact_data)
        assert contact_id is not None


class TestServiceInteroperability:
    """Test that decomposed services maintain interoperability."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)
    
    @pytest.mark.asyncio
    async def test_contact_service_with_interaction_service(self, mock_db):
        """Test contact service working with interaction service."""
        contact_service = ContactService(mock_db, tenant_id="tenant_123")
        interaction_service = InteractionService(mock_db, tenant_id="tenant_123")
        
        # Mock repositories
        contact_service.contact_repository = Mock()
        interaction_service.interaction_repository = Mock()
        
        contact_id = uuid4()
        customer_id = uuid4()
        
        # Mock contact exists
        mock_contact = CustomerContact(
            id=contact_id,
            customer_id=customer_id,
            contact_type=ContactType.PRIMARY,
            first_name="John",
            last_name="Doe"
        )
        contact_service.contact_repository.get_by_id.return_value = mock_contact
        
        # Create interaction for this contact
        interaction_data = CommunicationInteractionCreate(
            customer_id=customer_id,
            contact_id=contact_id,
            interaction_type=InteractionType.EMAIL,
            subject="Test",
            content="Test interaction"
        )
        
        mock_interaction = CommunicationInteraction(
            id=uuid4(),
            **interaction_data.dict(),
            status=InteractionStatus.OPEN
        )
        interaction_service.interaction_repository.create.return_value = mock_interaction
        
        # Test that interaction can be created for existing contact
        interaction_id = await interaction_service.create_interaction(interaction_data)
        
        assert interaction_id == mock_interaction.id
        interaction_service.interaction_repository.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_backward_compatibility_with_original_interface(self, mock_db):
        """Test that orchestrator maintains backward compatibility."""
        # The orchestrator should provide the same interface as the original service
        orchestrator = OmnichannelOrchestrator(mock_db, tenant_id="tenant_123")
        
        # Verify it has all the expected methods from original service
        expected_methods = [
            'create_customer_contact',
            'update_customer_contact', 
            'create_interaction',
            'create_agent',
            'get_dashboard_stats'
        ]
        
        for method_name in expected_methods:
            assert hasattr(orchestrator, method_name)
            assert callable(getattr(orchestrator, method_name))
    
    def test_service_dependency_injection(self, mock_db):
        """Test that services are properly injected into orchestrator."""
        orchestrator = OmnichannelOrchestrator(mock_db, tenant_id="tenant_123")
        
        # Verify all services are initialized
        assert hasattr(orchestrator, 'contact_service')
        assert hasattr(orchestrator, 'interaction_service')
        assert hasattr(orchestrator, 'agent_service')
        assert hasattr(orchestrator, 'routing_service')
        assert hasattr(orchestrator, 'analytics_service')
        
        # Verify services are of correct types
        assert isinstance(orchestrator.contact_service, ContactService)
        assert isinstance(orchestrator.interaction_service, InteractionService)
        assert isinstance(orchestrator.agent_service, AgentService)
        assert isinstance(orchestrator.routing_service, RoutingService)
        assert isinstance(orchestrator.analytics_service, AnalyticsService)