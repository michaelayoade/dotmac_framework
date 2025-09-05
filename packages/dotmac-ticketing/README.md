# DotMac Ticketing System

Comprehensive support ticket management system for the DotMac Framework.

## Overview

The DotMac Ticketing System provides a complete solution for managing customer support tickets, technical issues, and service requests across the entire DotMac platform. It includes automated workflows, SLA monitoring, escalation rules, and integrations with communication systems.

## Features

- **Complete Ticket Lifecycle Management**: Create, update, assign, escalate, resolve, and close tickets
- **Automated Workflows**: Customizable workflows for different ticket types (technical support, billing, etc.)
- **SLA Monitoring**: Automatic tracking of response and resolution times
- **Escalation Engine**: Rule-based escalation with approval workflows
- **Multi-tenant Support**: Complete tenant isolation and customization
- **Communication Integration**: Email, SMS, and in-app notifications
- **REST API**: Full REST API for integration with external systems
- **Analytics**: Comprehensive reporting and dashboard metrics

## Architecture

The package is organized into four main modules:

### Core (`dotmac.ticketing.core`)
- **Models**: SQLAlchemy models and Pydantic schemas for tickets, comments, attachments
- **Manager**: Low-level ticket management operations
- **Service**: High-level business logic and workflow orchestration

### Workflows (`dotmac.ticketing.workflows`)
- **Base**: Abstract workflow classes and execution engine
- **Implementations**: Specific workflows for different ticket types
- **Automation**: Auto-assignment rules, escalation logic, and SLA monitoring

### API (`dotmac.ticketing.api`)
- **Routes**: FastAPI router implementations
- **Schemas**: API request/response models

### Integrations (`dotmac.ticketing.integrations`)
- **Notifications**: Communication system integration
- **External Systems**: Hooks for CRM, monitoring tools, etc.

## Quick Start

### Installation

```bash
pip install dotmac-ticketing
```

### Basic Usage

```python
from dotmac.ticketing import (
    TicketManager, 
    TicketService, 
    initialize_ticketing,
    TicketCreate,
    TicketCategory,
    TicketPriority
)

# Initialize the ticketing system
ticket_manager = initialize_ticketing({
    "database_url": "postgresql://...",
    "sla_config": {...}
})

# Create a ticket service
ticket_service = TicketService(ticket_manager)

# Create a new ticket
ticket_data = TicketCreate(
    title="Customer experiencing slow internet",
    description="Customer reports slow speeds since yesterday",
    category=TicketCategory.TECHNICAL_SUPPORT,
    priority=TicketPriority.NORMAL,
    customer_email="customer@example.com"
)

ticket = await ticket_service.create_customer_ticket(
    db=db_session,
    tenant_id="tenant-123",
    customer_id="customer-456",
    **ticket_data.dict()
)
```

### FastAPI Integration

```python
from fastapi import FastAPI
from dotmac.ticketing.api import create_ticket_router

app = FastAPI()

# Add ticket router
ticket_router = create_ticket_router(
    ticket_service=ticket_service,
    get_db=get_database_session,
    get_current_tenant=get_tenant_from_request,
    get_current_user=get_authenticated_user
)
app.include_router(ticket_router, prefix="/api/v1")
```

## Workflows

The system includes pre-built workflows for common scenarios:

### Customer Support Workflow
- Validates ticket information
- Auto-categorizes based on content
- Assigns to appropriate team
- Sends acknowledgment email
- Sets up SLA monitoring

### Technical Support Workflow  
- Collects diagnostic information
- Analyzes the issue
- Escalates complex problems
- Provides solutions
- Verifies resolution

### Billing Issue Workflow
- Verifies customer account
- Reviews billing history  
- Calculates adjustments
- Applies resolution
- Confirms with customer

### Custom Workflows

You can create custom workflows by extending the base `TicketWorkflow` class:

```python
from dotmac.ticketing.workflows import TicketWorkflow, WorkflowResult

class CustomWorkflow(TicketWorkflow):
    def __init__(self):
        super().__init__(
            workflow_type="custom_workflow",
            steps=["step1", "step2", "step3"]
        )
    
    async def execute_step(self, step_name: str) -> WorkflowResult:
        if step_name == "step1":
            # Custom logic here
            return WorkflowResult(success=True, step_name=step_name)
        # ... implement other steps
```

## Configuration

The ticketing system supports extensive configuration:

```python
config = {
    # SLA Configuration (in minutes)
    "sla_config": {
        "critical": {"response": 15, "resolution": 240},
        "urgent": {"response": 60, "resolution": 480},
        "high": {"response": 240, "resolution": 1440},
        "normal": {"response": 1440, "resolution": 4320},
        "low": {"response": 2880, "resolution": 10080}
    },
    
    # Auto-assignment rules
    "assignment_rules": [
        {
            "name": "technical_issues",
            "conditions": {"category": "technical_support"},
            "assigned_team": "Technical Support",
            "priority": 10
        }
    ],
    
    # Escalation rules
    "escalation_rules": [
        {
            "name": "critical_escalation", 
            "conditions": {"priority": "critical"},
            "escalation_time_hours": 1,
            "escalate_to_team": "Engineering"
        }
    ]
}

initialize_ticketing(config)
```

## Testing

Run the test suite:

```bash
# Install test dependencies
pip install -e ".[test]"

# Run tests
pytest packages/dotmac-ticketing/tests/

# Run with coverage
pytest --cov=dotmac.ticketing packages/dotmac-ticketing/tests/
```

## API Documentation

When integrated with FastAPI, the system automatically generates OpenAPI documentation at `/docs` with full API specifications.

### Key Endpoints

- `POST /tickets/` - Create new ticket
- `GET /tickets/{ticket_id}` - Get ticket details
- `PUT /tickets/{ticket_id}` - Update ticket
- `POST /tickets/{ticket_id}/assign` - Assign ticket
- `POST /tickets/{ticket_id}/escalate` - Escalate ticket
- `POST /tickets/{ticket_id}/resolve` - Resolve ticket
- `POST /tickets/{ticket_id}/comments` - Add comment
- `GET /tickets/analytics/dashboard` - Get analytics

## Dependencies

### Core Dependencies
- `sqlalchemy>=2.0.0` - Database ORM
- `pydantic>=2.0.0` - Data validation
- `fastapi>=0.104.0` - Web framework
- `structlog>=23.0.0` - Structured logging

### Optional Dependencies
- `redis>=5.0.0` - Caching and task queues
- `celery>=5.3.0` - Background task processing

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This package is part of the DotMac Framework and is licensed under the MIT License.