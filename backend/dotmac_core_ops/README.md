# DotMac Core Operations

A comprehensive operations plane Python package for workflow orchestration, task management, automation, scheduling, state machines, saga pattern, and job queue orchestration.

## Features

### Core SDKs

- **Workflow SDK**: Define and execute complex workflows with steps, dependencies, conditions, and parallel execution
- **Task SDK**: Manage task queues, dependencies, priorities, and distributed execution
- **Automation SDK**: Rule-based automation with triggers, conditions, and actions
- **Scheduler SDK**: Cron-based and interval scheduling with job management
- **State Machine SDK**: Event-driven state machines with transitions and guards
- **Saga SDK**: Distributed transaction management with compensation patterns
- **Job Queue SDK**: Priority queues, workers, and dead letter queue handling

### API Layer

- RESTful APIs for all operations with OpenAPI documentation
- Health checks and monitoring endpoints
- Tenant isolation and multi-tenancy support
- Authentication and authorization

### Client SDKs

- Python client SDKs for remote API interaction
- Async/await support with httpx
- Comprehensive error handling and retry logic

### Runtime

- FastAPI-based web application
- Background services for health monitoring and cleanup
- Configurable middleware for security, logging, and metrics
- Environment-based configuration

## Installation

```bash
# Install from source
cd dotmac_core_ops
pip install -e .

# Install with optional dependencies
pip install -e ".[redis,postgres,kafka]"
```

## Quick Start

### Running the Operations Platform

```bash
# Set environment variables
export OPS_SECRET_KEY="your-secret-key"
export OPS_API_KEYS="api-key-1,api-key-2"

# Run the application
python main.py
```

### Using the Client SDK

```python
import asyncio
from dotmac_core_ops.client import OperationsClient

async def main():
    async with OperationsClient(
        base_url="http://localhost:8000",
        api_key="your-api-key",
        tenant_id="my-tenant"
    ) as client:
        # Check platform health
        health = await client.health_check()
        print(f"Platform status: {health['status']}")
        
        # Create a workflow
        workflow_id = await client.workflows.create_workflow(
            name="data-processing",
            definition={
                "steps": [
                    {"id": "extract", "type": "action", "action": "extract_data"},
                    {"id": "transform", "type": "action", "action": "transform_data", "depends_on": ["extract"]},
                    {"id": "load", "type": "action", "action": "load_data", "depends_on": ["transform"]}
                ]
            }
        )
        
        # Execute the workflow
        execution_id = await client.workflows.execute_workflow(
            workflow_id=workflow_id,
            input_data={"source": "database", "target": "warehouse"}
        )
        
        print(f"Workflow execution started: {execution_id}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Using SDKs Directly

```python
import asyncio
from dotmac_core_ops.sdks import WorkflowSDK, TaskSDK

async def main():
    # Initialize SDKs
    workflow_sdk = WorkflowSDK()
    task_sdk = TaskSDK()
    
    await workflow_sdk.start()
    await task_sdk.start()
    
    try:
        # Create and execute a workflow
        from dotmac_core_ops.sdks.workflow import WorkflowDefinition, WorkflowStep
        
        workflow = WorkflowDefinition(
            id="example-workflow",
            name="Example Workflow",
            steps=[
                WorkflowStep(id="step1", type="action", action="process_data"),
                WorkflowStep(id="step2", type="action", action="send_notification", depends_on=["step1"])
            ]
        )
        
        workflow_id = await workflow_sdk.create_workflow(workflow)
        execution_id = await workflow_sdk.execute_workflow(workflow_id, {"data": "example"})
        
        print(f"Workflow {workflow_id} execution {execution_id} started")
        
    finally:
        await workflow_sdk.stop()
        await task_sdk.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

## Configuration

The platform supports configuration via environment variables:

### Basic Settings
- `OPS_APP_NAME`: Application name (default: "DotMac Operations")
- `OPS_HOST`: Server host (default: "0.0.0.0")
- `OPS_PORT`: Server port (default: 8000)
- `OPS_DEBUG`: Debug mode (default: false)

### Security
- `OPS_SECRET_KEY`: Secret key for JWT signing
- `OPS_API_KEYS`: Comma-separated list of valid API keys
- `OPS_CORS_ORIGINS`: Comma-separated list of CORS origins

### Storage Adapters
- `OPS_STORAGE_ADAPTER`: Storage adapter type (memory, redis, postgres, mongodb)
- `OPS_MESSAGE_ADAPTER`: Message adapter type (memory, redis, kafka)

### Database
- `OPS_DATABASE_URL`: Database connection URL
- `OPS_REDIS_URL`: Redis connection URL
- `OPS_KAFKA_BOOTSTRAP_SERVERS`: Kafka bootstrap servers
- `OPS_MONGODB_URL`: MongoDB connection URL

### Observability
- `OPS_ENABLE_METRICS`: Enable metrics collection (default: true)
- `OPS_LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `OPS_ENABLE_TRACING`: Enable distributed tracing (default: false)

## API Documentation

When running the application, API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

### Health Endpoints

- `GET /health` - Comprehensive health check
- `GET /ready` - Readiness check
- `GET /live` - Liveness check

### API Endpoints

- `POST /api/v1/workflows/` - Create workflow
- `GET /api/v1/workflows/` - List workflows
- `POST /api/v1/workflows/{id}/execute` - Execute workflow
- `POST /api/v1/tasks/` - Create task
- `GET /api/v1/tasks/` - List tasks
- `POST /api/v1/automation/rules` - Create automation rule
- `POST /api/v1/scheduler/schedules` - Create schedule
- `POST /api/v1/state-machines/` - Create state machine
- `POST /api/v1/sagas/` - Create saga
- `POST /api/v1/job-queues/jobs` - Submit job

## Architecture

### Package Structure

```
dotmac_core_ops/
├── dotmac_core_ops/
│   ├── __init__.py              # Main package exports
│   ├── adapters/                # Storage and message adapters
│   ├── api/                     # REST API endpoints
│   ├── client/                  # Client SDKs
│   ├── contracts/               # Data contracts and schemas
│   ├── runtime/                 # Application runtime
│   └── sdks/                    # Core operation SDKs
├── tests/                       # Test suite
├── main.py                      # Application entry point
├── pyproject.toml              # Package configuration
└── README.md                   # This file
```

### Core Components

1. **SDKs**: Core business logic for each operation type
2. **Contracts**: Pydantic models for data validation and serialization
3. **API Layer**: FastAPI-based REST APIs with OpenAPI documentation
4. **Client SDKs**: Remote API interaction libraries
5. **Runtime**: Application factory, configuration, and middleware
6. **Adapters**: Pluggable storage and messaging backends

### Design Principles

- **Modularity**: Each SDK is independent and can be used standalone
- **Async-First**: Built with asyncio for high concurrency
- **Type Safety**: Comprehensive type hints and Pydantic validation
- **Observability**: Built-in logging, metrics, and tracing support
- **Extensibility**: Plugin architecture for custom adapters
- **Multi-Tenancy**: Tenant isolation at all levels

## Examples

### Workflow Orchestration

```python
# Define a complex workflow with parallel steps
workflow_def = {
    "steps": [
        {"id": "validate", "type": "action", "action": "validate_input"},
        {"id": "process_a", "type": "action", "action": "process_branch_a", "depends_on": ["validate"]},
        {"id": "process_b", "type": "action", "action": "process_branch_b", "depends_on": ["validate"]},
        {"id": "merge", "type": "action", "action": "merge_results", "depends_on": ["process_a", "process_b"]},
        {"id": "notify", "type": "condition", "condition": "success", "depends_on": ["merge"]}
    ]
}
```

### Automation Rules

```python
# Create an automation rule
rule = {
    "name": "Auto-scale on high load",
    "triggers": [{"type": "metric", "metric": "cpu_usage", "threshold": 80}],
    "conditions": [{"type": "time", "between": ["09:00", "17:00"]}],
    "actions": [{"type": "scale", "service": "web-app", "instances": "+2"}]
}
```

### State Machine

```python
# Define a state machine for order processing
state_machine = {
    "name": "Order Processing",
    "initial_state": "pending",
    "states": [
        {"name": "pending", "type": "initial"},
        {"name": "processing", "type": "intermediate"},
        {"name": "completed", "type": "final"},
        {"name": "cancelled", "type": "final"}
    ],
    "transitions": [
        {"from": "pending", "to": "processing", "event": "start_processing"},
        {"from": "processing", "to": "completed", "event": "finish"},
        {"from": "pending", "to": "cancelled", "event": "cancel"},
        {"from": "processing", "to": "cancelled", "event": "cancel"}
    ]
}
```

## Development

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=dotmac_core_ops
```

### Code Quality

```bash
# Format code
black dotmac_core_ops/
isort dotmac_core_ops/

# Lint code
ruff check dotmac_core_ops/
mypy dotmac_core_ops/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions, issues, or contributions, please refer to the project repository or contact the development team.
