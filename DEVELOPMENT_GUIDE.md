# DotMac Platform Development Guide

## Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Git

### Setup Development Environment
```bash
# Clone and setup
git clone https://github.com/michaelayoade/dotmac-framework
cd dotmac-framework

# Automated setup
python scripts/automation/development_workflow.py setup
```

## Development Workflow

### Daily Development Workflow
```bash
# Run complete development workflow
python scripts/automation/development_workflow.py workflow

# Run for specific services
python scripts/automation/development_workflow.py workflow --services dotmac_platform dotmac_api_gateway

# Auto-fix issues where possible
python scripts/automation/development_workflow.py workflow --auto-fix
```

### Code Quality Standards

#### 1. Formatting (Black)
```bash
# Check formatting
black --check --line-length 88 .

# Auto-format
black --line-length 88 .
```

#### 2. Linting (Ruff)
```bash
# Check linting
ruff check .

# Auto-fix linting issues
ruff check --fix .
```

#### 3. Type Checking (MyPy)
```bash
# Check types
mypy . --ignore-missing-imports
```

#### 4. Security Scanning (Bandit)
```bash
# Security scan
bandit -r . -f json
```

#### 5. Testing (Pytest)
```bash
# Run all tests
python scripts/run_tests.py

# Run tests with coverage
python scripts/run_tests.py --coverage

# Run specific service tests
python scripts/run_tests.py --service dotmac_platform
```

### Pre-commit Hooks

Pre-commit hooks are automatically configured to run:
- Black formatting
- Ruff linting
- MyPy type checking
- Bandit security scanning

```bash
# Install hooks (done automatically in setup)
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

## Service Development

### Creating a New Service

1. **Create Service Directory**
```bash
mkdir dotmac_new_service
cd dotmac_new_service
```

2. **Create Basic Structure**
```
dotmac_new_service/
├── dotmac_new_service/
│   ├── __init__.py
│   ├── main.py
│   ├── models/
│   ├── services/
│   └── api/
├── tests/
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
└── README.md
```

3. **Generate Docker Configuration**
```bash
# Update service list in generate_docker_configs.py
python scripts/generate_docker_configs.py --service dotmac_new_service
```

### Service Architecture

Each service follows this architecture:

```
dotmac_service/
├── dotmac_service/
│   ├── __init__.py          # Package initialization
│   ├── main.py              # Service entry point
│   ├── config.py            # Configuration management
│   ├── models/              # Data models
│   │   ├── __init__.py
│   │   └── entities.py
│   ├── services/            # Business logic
│   │   ├── __init__.py
│   │   └── service_logic.py
│   ├── repositories/        # Data access layer
│   │   ├── __init__.py
│   │   └── repository.py
│   └── api/                 # API endpoints
│       ├── __init__.py
│       ├── routes.py
│       └── schemas.py
├── tests/                   # Test suite
├── requirements.txt         # Production dependencies
├── requirements-dev.txt     # Development dependencies
└── Dockerfile              # Container configuration
```

### Database Development

#### Migrations
```bash
# Create migration
alembic revision --autogenerate -m "Add new table"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

#### Testing with Database
```bash
# Start test database
docker-compose -f docker-compose.development.yml up -d postgres

# Run database tests
python scripts/run_tests.py --category database
```

### API Development

#### FastAPI Standards
```python
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="DotMac Service", version="1.0.0")

class EntityCreate(BaseModel):
    name: str
    description: Optional[str] = None

class EntityResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime

@app.post("/entities", response_model=EntityResponse)
async def create_entity(entity: EntityCreate, db: Session = Depends(get_db)):
    """Create a new entity."""
    # Implementation
    pass
```

#### API Documentation
- All endpoints must have docstrings
- Use Pydantic models for request/response schemas
- Include proper HTTP status codes
- Implement error handling

### Testing Guidelines

#### Test Structure
```
tests/
├── unit/                    # Unit tests
│   ├── test_models.py
│   ├── test_services.py
│   └── test_repositories.py
├── integration/             # Integration tests
│   ├── test_api.py
│   └── test_database.py
├── e2e/                    # End-to-end tests
│   └── test_workflows.py
└── conftest.py             # Test configuration
```

#### Test Categories
- **Unit**: Test individual functions/methods
- **Integration**: Test component interactions
- **E2E**: Test complete workflows
- **Performance**: Test performance characteristics
- **Security**: Test security measures

#### Writing Tests
```python
import pytest
from fastapi.testclient import TestClient
from dotmac_service.main import app

client = TestClient(app)

def test_create_entity():
    """Test entity creation."""
    response = client.post("/entities", json={
        "name": "Test Entity",
        "description": "Test Description"
    })
    assert response.status_code == 201
    assert response.json()["name"] == "Test Entity"

@pytest.mark.asyncio
async def test_async_function():
    """Test async functionality."""
    result = await some_async_function()
    assert result is not None
```

## Security Development

### Security Guidelines

1. **Input Validation**
   - Validate all input data
   - Use Pydantic models for validation
   - Sanitize user input

2. **Authentication & Authorization**
   - Implement JWT-based authentication
   - Use RBAC for authorization
   - Validate all API requests

3. **Data Protection**
   - Encrypt sensitive data at rest
   - Use HTTPS for all communications
   - Implement proper logging (no secrets)

4. **Security Testing**
   - Run Bandit security scans
   - Test for common vulnerabilities
   - Validate security controls

### Security Implementation Example
```python
from dotmac_platform.security.rbac import RBACManager
from dotmac_platform.security.encryption import EncryptionManager

# RBAC implementation
rbac = RBACManager()
if not await rbac.check_permission(user, "create:entity"):
    raise HTTPException(status_code=403, detail="Insufficient permissions")

# Encryption implementation
encryption = EncryptionManager()
encrypted_data = await encryption.encrypt(sensitive_data, "CONFIDENTIAL")
```

## Performance Development

### Performance Guidelines

1. **Database Optimization**
   - Use proper indexes
   - Optimize queries
   - Implement connection pooling

2. **Caching**
   - Use Redis for application caching
   - Cache frequently accessed data
   - Implement cache invalidation

3. **Async Programming**
   - Use async/await for I/O operations
   - Implement proper connection management
   - Use background tasks for heavy operations

### Performance Testing
```python
import pytest
from dotmac_platform.tests.performance import BenchmarkRunner

@pytest.mark.performance
def test_api_performance():
    """Test API endpoint performance."""
    runner = BenchmarkRunner()
    results = runner.benchmark_endpoint("/api/entities", iterations=1000)
    
    assert results.avg_response_time < 100  # ms
    assert results.p95_response_time < 200  # ms
```

## Monitoring & Observability

### Logging
```python
import structlog

logger = structlog.get_logger(__name__)

async def process_request(request_id: str):
    logger.info("Processing request", request_id=request_id)
    try:
        # Process request
        logger.info("Request completed", request_id=request_id)
    except Exception as e:
        logger.error("Request failed", request_id=request_id, error=str(e))
        raise
```

### Metrics
```python
from dotmac_platform.observability.metrics import MetricsCollector

metrics = MetricsCollector()

@metrics.track_duration("api.entity.create")
async def create_entity(entity_data):
    metrics.increment("api.entity.requests")
    # Implementation
    metrics.increment("api.entity.created")
```

### Distributed Tracing
```python
from dotmac_platform.observability.distributed_tracing import trace_async

@trace_async("entity_service.create_entity")
async def create_entity(entity_data):
    # Implementation with automatic tracing
    pass
```

## Deployment

### Development Deployment
```bash
# Build and deploy to development
python scripts/automation/deploy.py development --version latest

# Deploy specific services
python scripts/automation/deploy.py development --services dotmac_platform dotmac_api_gateway
```

### Production Deployment
```bash
# Deploy to production with full validation
python scripts/automation/deploy.py production --version v1.2.3

# Deploy with rollback disabled (not recommended)
python scripts/automation/deploy.py production --no-rollback
```

### Health Checks
Each service must implement health check endpoints:

```python
@app.get("/health")
async def health_check():
    """Service health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc),
        "version": "1.0.0",
        "dependencies": {
            "database": await check_database(),
            "redis": await check_redis()
        }
    }
```

## Common Development Tasks

### Adding a New API Endpoint
1. Define Pydantic schemas in `schemas.py`
2. Implement business logic in `services/`
3. Add database operations in `repositories/`
4. Create API route in `api/routes.py`
5. Write comprehensive tests
6. Update API documentation

### Adding a Database Table
1. Create SQLAlchemy model in `models/`
2. Generate migration with Alembic
3. Update repository classes
4. Add validation schemas
5. Write database tests
6. Update documentation

### Implementing New Security Feature
1. Add security logic to `dotmac_platform/security/`
2. Update RBAC policies if needed
3. Add security tests
4. Run security scans
5. Update security documentation

### Performance Optimization
1. Identify performance bottleneck
2. Add performance tests
3. Implement optimization
4. Validate improvement with benchmarks
5. Update monitoring and alerts

## Troubleshooting

### Common Issues

#### Import Errors
```bash
# Check dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Verify Python path
export PYTHONPATH=/path/to/dotmac_framework
```

#### Database Connection Issues
```bash
# Check database status
docker-compose -f docker-compose.development.yml ps postgres

# Check connection
docker exec -it postgres psql -U dotmac -d dotmac_platform
```

#### Test Failures
```bash
# Run tests with verbose output
python scripts/run_tests.py --verbose

# Run specific test
pytest tests/unit/test_specific.py::test_function -v

# Debug test
pytest tests/unit/test_specific.py::test_function -v --pdb
```

### Development Environment Issues

#### Docker Issues
```bash
# Reset development environment
docker-compose -f docker-compose.development.yml down -v
docker-compose -f docker-compose.development.yml up -d

# Clean Docker system
docker system prune -f
```

#### Code Quality Issues
```bash
# Fix formatting
black . --line-length 88

# Fix linting
ruff check --fix .

# Check security
bandit -r . -f json
```

## Best Practices

### Code Organization
- Follow service-oriented architecture
- Implement proper separation of concerns
- Use dependency injection
- Maintain consistent naming conventions

### Documentation
- Document all public APIs
- Include code examples
- Maintain up-to-date README files
- Use type hints consistently

### Testing
- Aim for 90%+ test coverage
- Write tests before implementation (TDD)
- Use meaningful test names
- Test edge cases and error conditions

### Security
- Never commit secrets
- Use environment variables for config
- Implement proper authentication
- Regular security audits

### Performance
- Profile before optimizing
- Use appropriate data structures
- Implement proper caching
- Monitor performance metrics

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Black Code Formatter](https://black.readthedocs.io/)
- [Ruff Linter](https://docs.astral.sh/ruff/)

## Getting Help

- Check existing documentation
- Review similar implementations
- Ask in team chat
- Create GitHub issue for bugs
- Submit PR for improvements