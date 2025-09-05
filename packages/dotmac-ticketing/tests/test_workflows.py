"""
Tests for ticketing workflows.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from dotmac.ticketing.core.models import (
    Ticket,
    TicketCategory,
    TicketPriority,
    TicketStatus,
)
from dotmac.ticketing.workflows import (
    BillingIssueWorkflow,
    CustomerSupportWorkflow,
    TechnicalSupportWorkflow,
    WorkflowStatus,
)


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def sample_ticket():
    """Create sample ticket for testing."""
    return Ticket(
        id="ticket-123",
        tenant_id="test-tenant",
        ticket_number="TST-001",
        title="Test Issue",
        description="Customer experiencing slow internet speeds",
        category=TicketCategory.TECHNICAL_SUPPORT,
        priority=TicketPriority.NORMAL,
        status=TicketStatus.OPEN,
        customer_email="customer@example.com",
        created_at=datetime.now(timezone.utc),
    )


class TestCustomerSupportWorkflow:
    """Test customer support workflow."""

    @pytest.mark.asyncio
    async def test_workflow_triggering(self, sample_ticket):
        """Test workflow trigger conditions."""
        workflow = CustomerSupportWorkflow()

        # Should trigger for technical support
        sample_ticket.category = TicketCategory.TECHNICAL_SUPPORT
        assert await workflow.should_trigger(sample_ticket) is True

        # Should trigger for account management
        sample_ticket.category = TicketCategory.ACCOUNT_MANAGEMENT
        assert await workflow.should_trigger(sample_ticket) is True

        # Should not trigger for billing
        sample_ticket.category = TicketCategory.BILLING_INQUIRY
        assert await workflow.should_trigger(sample_ticket) is False

    @pytest.mark.asyncio
    async def test_validate_ticket_step(self, sample_ticket, mock_db_session):
        """Test ticket validation step."""
        workflow = CustomerSupportWorkflow()
        workflow.set_ticket_context(sample_ticket, "test-tenant", mock_db_session)

        result = await workflow._validate_ticket()

        assert result.success is True
        assert result.step_name == "validate_ticket"
        assert result.data["validated"] is True

    @pytest.mark.asyncio
    async def test_validate_ticket_missing_info(self, mock_db_session):
        """Test validation with missing information."""
        # Ticket missing customer email and ID
        invalid_ticket = Ticket(
            id="ticket-invalid",
            tenant_id="test-tenant",
            ticket_number="TST-002",
            title="Invalid Ticket",
            description="Missing customer info",
            category=TicketCategory.TECHNICAL_SUPPORT,
        )

        workflow = CustomerSupportWorkflow()
        workflow.set_ticket_context(invalid_ticket, "test-tenant", mock_db_session)

        result = await workflow._validate_ticket()

        assert result.success is False
        assert "customer identification" in result.error

    @pytest.mark.asyncio
    async def test_categorize_issue_step(self, sample_ticket, mock_db_session):
        """Test issue categorization step."""
        workflow = CustomerSupportWorkflow()
        workflow.set_ticket_context(sample_ticket, "test-tenant", mock_db_session)

        # Test network issue detection
        sample_ticket.title = "Internet connection is very slow"
        sample_ticket.description = "My internet has been slow all day"

        result = await workflow._categorize_issue()

        assert result.success is True
        assert result.data["suggested_category"] == TicketCategory.NETWORK_ISSUE

    @pytest.mark.asyncio
    async def test_assign_to_team_step(self, sample_ticket, mock_db_session):
        """Test team assignment step."""
        workflow = CustomerSupportWorkflow()
        workflow.set_ticket_context(sample_ticket, "test-tenant", mock_db_session)

        sample_ticket.category = TicketCategory.TECHNICAL_SUPPORT

        result = await workflow._assign_to_team()

        assert result.success is True
        assert result.data["assigned_team"] == "Technical Support"
        assert sample_ticket.assigned_team == "Technical Support"
        assert sample_ticket.status == TicketStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_full_workflow_execution(self, sample_ticket, mock_db_session):
        """Test complete workflow execution."""
        workflow = CustomerSupportWorkflow()
        workflow.set_ticket_context(sample_ticket, "test-tenant", mock_db_session)

        results = await workflow.execute()

        assert len(results) == 5  # All 5 steps
        assert all(result.success for result in results)
        assert workflow.status == WorkflowStatus.COMPLETED


class TestTechnicalSupportWorkflow:
    """Test technical support workflow."""

    @pytest.mark.asyncio
    async def test_workflow_triggering(self, sample_ticket):
        """Test workflow trigger conditions."""
        workflow = TechnicalSupportWorkflow()

        # Should trigger only for technical support
        sample_ticket.category = TicketCategory.TECHNICAL_SUPPORT
        assert await workflow.should_trigger(sample_ticket) is True

        sample_ticket.category = TicketCategory.BILLING_INQUIRY
        assert await workflow.should_trigger(sample_ticket) is False

    @pytest.mark.asyncio
    async def test_collect_diagnostics_step(self, sample_ticket, mock_db_session):
        """Test diagnostic collection step."""
        workflow = TechnicalSupportWorkflow()
        workflow.set_ticket_context(sample_ticket, "test-tenant", mock_db_session)

        result = await workflow._collect_diagnostics()

        assert result.success is True
        assert result.step_name == "collect_diagnostics"
        assert result.data["diagnostics_collected"] is True

    @pytest.mark.asyncio
    async def test_escalation_check(self, sample_ticket, mock_db_session):
        """Test escalation logic."""
        workflow = TechnicalSupportWorkflow()
        workflow.set_ticket_context(sample_ticket, "test-tenant", mock_db_session)

        # Test with critical priority
        sample_ticket.priority = TicketPriority.CRITICAL

        result = await workflow._escalate_if_needed()

        assert result.success is True
        assert result.data["escalated"] is True
        assert sample_ticket.status == TicketStatus.ESCALATED
        assert sample_ticket.assigned_team == "Engineering"


class TestBillingIssueWorkflow:
    """Test billing issue workflow."""

    @pytest.mark.asyncio
    async def test_workflow_triggering(self, sample_ticket):
        """Test workflow trigger conditions."""
        workflow = BillingIssueWorkflow()

        # Should trigger only for billing inquiries
        sample_ticket.category = TicketCategory.BILLING_INQUIRY
        assert await workflow.should_trigger(sample_ticket) is True

        sample_ticket.category = TicketCategory.TECHNICAL_SUPPORT
        assert await workflow.should_trigger(sample_ticket) is False

    @pytest.mark.asyncio
    async def test_verify_account_step(self, sample_ticket, mock_db_session):
        """Test account verification step."""
        workflow = BillingIssueWorkflow()
        workflow.set_ticket_context(sample_ticket, "test-tenant", mock_db_session)

        sample_ticket.category = TicketCategory.BILLING_INQUIRY

        result = await workflow._verify_account()

        assert result.success is True
        assert result.step_name == "verify_account"
        assert result.data["account_verified"] is True

    @pytest.mark.asyncio
    async def test_full_billing_workflow(self, sample_ticket, mock_db_session):
        """Test complete billing workflow."""
        workflow = BillingIssueWorkflow()
        workflow.set_ticket_context(sample_ticket, "test-tenant", mock_db_session)

        sample_ticket.category = TicketCategory.BILLING_INQUIRY

        results = await workflow.execute()

        assert len(results) == 5  # All 5 steps
        assert all(result.success for result in results)
        assert workflow.status == WorkflowStatus.COMPLETED
        assert sample_ticket.status == TicketStatus.RESOLVED


class TestWorkflowBase:
    """Test base workflow functionality."""

    @pytest.mark.asyncio
    async def test_workflow_context_setting(self, sample_ticket, mock_db_session):
        """Test setting workflow context."""
        workflow = CustomerSupportWorkflow()

        # Initially no context
        assert workflow.ticket is None
        assert workflow.tenant_id is None
        assert workflow.db_session is None

        # Set context
        workflow.set_ticket_context(sample_ticket, "test-tenant", mock_db_session)

        assert workflow.ticket == sample_ticket
        assert workflow.tenant_id == "test-tenant"
        assert workflow.db_session == mock_db_session

    @pytest.mark.asyncio
    async def test_workflow_without_context_fails(self):
        """Test that workflow fails without context."""
        workflow = CustomerSupportWorkflow()

        with pytest.raises(ValueError, match="Ticket context must be set"):
            await workflow.execute()

    def test_workflow_to_dict(self, sample_ticket, mock_db_session):
        """Test workflow serialization to dictionary."""
        workflow = CustomerSupportWorkflow()
        workflow.set_ticket_context(sample_ticket, "test-tenant", mock_db_session)

        workflow_dict = workflow.to_dict()

        assert workflow_dict["workflow_type"] == "customer_support"
        assert workflow_dict["ticket_id"] == sample_ticket.id
        assert workflow_dict["ticket_number"] == sample_ticket.ticket_number
        assert workflow_dict["status"] == WorkflowStatus.PENDING.value
