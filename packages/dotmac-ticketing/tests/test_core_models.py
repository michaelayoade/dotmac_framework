"""
Tests for ticketing core models.
"""


import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from dotmac.ticketing.core.models import (
    Base,
    Ticket,
    TicketAttachment,
    TicketCategory,
    TicketComment,
    TicketCreate,
    TicketPriority,
    TicketResponse,
    TicketSource,
    TicketStatus,
    TicketUpdate,
)


@pytest.fixture
def db_engine():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(db_engine):
    """Create database session."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


class TestTicketModels:
    """Test ticket model functionality."""

    def test_ticket_creation(self, db_session):
        """Test creating a ticket."""
        ticket = Ticket(
            tenant_id="test-tenant",
            ticket_number="TST-12345",
            title="Test Ticket",
            description="This is a test ticket",
            category=TicketCategory.TECHNICAL_SUPPORT,
            priority=TicketPriority.NORMAL,
            source=TicketSource.CUSTOMER_PORTAL,
            customer_email="test@example.com",
        )

        db_session.add(ticket)
        db_session.commit()

        assert ticket.id is not None
        assert ticket.status == TicketStatus.OPEN
        assert ticket.created_at is not None

    def test_ticket_relationships(self, db_session):
        """Test ticket relationships with comments and attachments."""
        # Create ticket
        ticket = Ticket(
            tenant_id="test-tenant",
            ticket_number="TST-12346",
            title="Test Ticket with Relations",
            description="Testing relationships",
            category=TicketCategory.TECHNICAL_SUPPORT,
        )
        db_session.add(ticket)
        db_session.flush()  # Get ticket ID

        # Add comment
        comment = TicketComment(
            ticket_id=ticket.id,
            tenant_id="test-tenant",
            content="Test comment",
            author_name="Test User",
            author_type="staff",
        )
        db_session.add(comment)

        # Add attachment
        attachment = TicketAttachment(
            ticket_id=ticket.id,
            tenant_id="test-tenant",
            filename="test.txt",
            original_filename="test.txt",
            content_type="text/plain",
            file_size=100,
            file_path="/tmp/test.txt",
            uploaded_by_name="Test User",
        )
        db_session.add(attachment)

        db_session.commit()

        # Verify relationships
        assert len(ticket.comments) == 1
        assert len(ticket.attachments) == 1
        assert ticket.comments[0].content == "Test comment"
        assert ticket.attachments[0].filename == "test.txt"


class TestTicketSchemas:
    """Test Pydantic schemas for API serialization."""

    def test_ticket_create_schema(self):
        """Test ticket creation schema."""
        ticket_data = TicketCreate(
            title="Test Ticket",
            description="Test description",
            category=TicketCategory.BILLING_INQUIRY,
            priority=TicketPriority.HIGH,
            customer_email="customer@example.com",
            tags=["billing", "urgent"],
            extra_data={"source_system": "web_portal"},
        )

        assert ticket_data.title == "Test Ticket"
        assert ticket_data.category == TicketCategory.BILLING_INQUIRY
        assert ticket_data.priority == TicketPriority.HIGH
        assert "billing" in ticket_data.tags
        assert ticket_data.extra_data["source_system"] == "web_portal"

    def test_ticket_update_schema(self):
        """Test ticket update schema."""
        update_data = TicketUpdate(
            status=TicketStatus.IN_PROGRESS,
            priority=TicketPriority.URGENT,
            assigned_to_id="agent-123",
            assigned_team="Support Team",
        )

        assert update_data.status == TicketStatus.IN_PROGRESS
        assert update_data.priority == TicketPriority.URGENT
        assert update_data.assigned_to_id == "agent-123"

    def test_ticket_response_schema(self, db_session):
        """Test ticket response schema."""
        # Create ticket in database
        ticket = Ticket(
            tenant_id="test-tenant",
            ticket_number="TST-12347",
            title="Response Test",
            description="Testing response schema",
            category=TicketCategory.SERVICE_REQUEST,
            priority=TicketPriority.LOW,
        )
        db_session.add(ticket)
        db_session.commit()

        # Convert to response schema
        response = TicketResponse.model_validate(ticket)

        assert response.id == ticket.id
        assert response.ticket_number == "TST-12347"
        assert response.title == "Response Test"
        assert response.status == TicketStatus.OPEN
        assert response.priority == TicketPriority.LOW
        assert response.category == TicketCategory.SERVICE_REQUEST


class TestTicketEnums:
    """Test ticket enumeration values."""

    def test_ticket_status_enum(self):
        """Test ticket status enumeration."""
        assert TicketStatus.OPEN == "open"
        assert TicketStatus.IN_PROGRESS == "in_progress"
        assert TicketStatus.RESOLVED == "resolved"
        assert TicketStatus.CLOSED == "closed"

    def test_ticket_priority_enum(self):
        """Test ticket priority enumeration."""
        assert TicketPriority.LOW == "low"
        assert TicketPriority.NORMAL == "normal"
        assert TicketPriority.HIGH == "high"
        assert TicketPriority.URGENT == "urgent"
        assert TicketPriority.CRITICAL == "critical"

    def test_ticket_category_enum(self):
        """Test ticket category enumeration."""
        assert TicketCategory.TECHNICAL_SUPPORT == "technical_support"
        assert TicketCategory.BILLING_INQUIRY == "billing_inquiry"
        assert TicketCategory.NETWORK_ISSUE == "network_issue"

    def test_ticket_source_enum(self):
        """Test ticket source enumeration."""
        assert TicketSource.CUSTOMER_PORTAL == "customer_portal"
        assert TicketSource.EMAIL == "email"
        assert TicketSource.API == "api"
