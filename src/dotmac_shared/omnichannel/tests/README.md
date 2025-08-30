# Omnichannel Service Tests

Comprehensive test suite for the DotMac Omnichannel Service package.

## Test Structure

```
tests/
├── __init__.py                 # Test package initialization
├── conftest.py                 # Test configuration and shared fixtures
├── pytest.ini                 # Pytest configuration
├── README.md                   # This file
├── test_interaction_manager.py # Tests for InteractionManager
├── test_routing_engine.py      # Tests for RoutingEngine
├── test_agent_manager.py       # Tests for AgentManager
├── test_channel_orchestrator.py # Tests for ChannelOrchestrator
├── test_plugin_integration.py # Tests for plugin system integration
├── test_models.py             # Tests for data models
├── test_integration.py        # Integration tests
└── test_plugins.py            # Tests for communication plugins
```

## Test Categories

### Unit Tests

- **test_interaction_manager.py**: Tests for interaction lifecycle management
- **test_routing_engine.py**: Tests for intelligent routing algorithms
- **test_agent_manager.py**: Tests for agent workforce management
- **test_channel_orchestrator.py**: Tests for multi-channel message coordination
- **test_models.py**: Tests for Pydantic data models and validation

### Integration Tests

- **test_integration.py**: End-to-end workflow tests
- **test_plugin_integration.py**: Plugin system integration tests

### Plugin Tests

- **test_plugins.py**: Tests for communication plugins (Twilio SMS, etc.)

## Running Tests

### Run All Tests

```bash
cd /home/dotmac_framework/src/dotmac_shared/omnichannel
pytest
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Plugin tests only
pytest -m plugin

# Slow tests (excluded by default)
pytest -m slow
```

### Run Specific Test Files

```bash
# Test interaction manager
pytest tests/test_interaction_manager.py

# Test routing engine
pytest tests/test_routing_engine.py

# Test with verbose output
pytest -v tests/test_agent_manager.py
```

### Coverage Reports

```bash
# Run with coverage
pytest --cov=dotmac_shared.omnichannel

# Generate HTML coverage report
pytest --cov=dotmac_shared.omnichannel --cov-report=html

# View HTML report
open htmlcov/index.html
```

## Test Markers

Tests are marked with the following categories:

- `@pytest.mark.unit`: Unit tests for individual components
- `@pytest.mark.integration`: Integration tests between components
- `@pytest.mark.plugin`: Tests for communication plugins
- `@pytest.mark.slow`: Slow running tests (performance, load testing)
- `@pytest.mark.requires_db`: Tests requiring database connection
- `@pytest.mark.requires_redis`: Tests requiring Redis connection

## Test Fixtures

### Core Fixtures (conftest.py)

- `tenant_id`: Sample tenant UUID
- `customer_id`: Sample customer UUID
- `agent_id`: Sample agent UUID
- `mock_db_session`: Mock database session
- `sample_interaction`: Sample interaction model
- `sample_agent`: Sample agent model
- `mock_communication_plugin`: Mock communication plugin

### Component Fixtures

- `interaction_manager`: InteractionManager instance
- `routing_engine`: RoutingEngine instance
- `agent_manager`: AgentManager instance
- `channel_orchestrator`: ChannelOrchestrator instance

## Mock Strategy

Tests use extensive mocking to isolate components:

1. **Database Operations**: Mocked using `AsyncMock` for database sessions
2. **Plugin System**: Mocked plugin manager and registry interactions
3. **External APIs**: Mocked third-party service calls (Twilio, SendGrid, etc.)
4. **Network Calls**: Mocked HTTP requests and responses

## Test Data

### Sample Data Generation

Tests use factory patterns for generating test data:

```python
# Sample interaction
sample_interaction = InteractionModel(
    tenant_id=tenant_id,
    customer_id=customer_id,
    channel="email",
    subject="Test Issue",
    content="Test content",
    priority=InteractionPriority.HIGH
)

# Sample agent
sample_agent = AgentModel(
    tenant_id=tenant_id,
    full_name="Test Agent",
    email="agent@test.com",
    skills=[AgentSkill(name="email", level=5, certified=True)],
    channels=["email"]
)
```

## Async Testing

Tests use `pytest-asyncio` for async/await support:

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

## Integration Test Scenarios

### Complete Workflow Tests

1. **Customer Interaction Flow**: Create interaction → Route to agent → Send response → Close
2. **Multi-channel Messaging**: Send messages across email, SMS, WhatsApp
3. **Agent Workload Management**: Assign interactions within capacity limits
4. **Escalation Workflow**: Escalate complex interactions to senior agents

### Plugin Integration Tests

1. **Plugin Registration**: Register and configure communication plugins
2. **Plugin Failover**: Primary plugin fails, fallback succeeds
3. **Plugin Health Monitoring**: Monitor plugin health across channels
4. **Configuration Hot Reload**: Update plugin configuration without restart

## Performance Testing

Performance tests are marked with `@pytest.mark.slow`:

```python
@pytest.mark.slow
@pytest.mark.asyncio
async def test_concurrent_message_processing():
    # Test processing 1000+ concurrent messages
    messages = [create_message() for _ in range(1000)]
    results = await process_messages_concurrently(messages)
    assert len(results) == 1000
```

## Error Testing

Tests cover various error scenarios:

1. **Database Errors**: Connection failures, timeout, rollback
2. **Network Errors**: API timeouts, connection errors, rate limiting
3. **Validation Errors**: Invalid input data, schema violations
4. **Plugin Errors**: Plugin failures, configuration errors
5. **Capacity Errors**: Agent at capacity, rate limits exceeded

## Test Environment

### Required Dependencies

```bash
pip install pytest>=6.0
pip install pytest-asyncio>=0.21.0
pip install pytest-cov>=4.0.0
pip install pytest-mock>=3.10.0
```

### Environment Variables

```bash
# Test database URL (if using real DB)
export TEST_DATABASE_URL="sqlite:///test_omnichannel.db"

# Redis URL for testing (if using real Redis)
export TEST_REDIS_URL="redis://localhost:6379/15"

# Disable external API calls in tests
export TESTING=true
```

## Continuous Integration

Tests are designed to run in CI/CD environments:

```yaml
# Example GitHub Actions
- name: Run Tests
  run: |
    cd src/dotmac_shared/omnichannel
    pytest --cov=dotmac_shared.omnichannel --cov-report=xml

- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

## Best Practices

1. **Isolation**: Each test is independent and can run in any order
2. **Mocking**: External dependencies are mocked to ensure reliability
3. **Coverage**: Maintain minimum 85% test coverage
4. **Performance**: Mark slow tests to allow fast test runs during development
5. **Documentation**: Each test clearly describes what it's testing

## Debugging Tests

### Run Single Test with Debug Output

```bash
pytest -v -s tests/test_interaction_manager.py::TestInteractionManager::test_create_interaction_success
```

### Debug with pdb

```python
import pytest
import pdb; pdb.set_trace()  # Add breakpoint
pytest.set_trace()  # Pytest built-in breakpoint
```

### Capture Print Statements

```bash
pytest -s  # Don't capture stdout
```

## Contributing

When adding new tests:

1. Follow naming conventions: `test_feature_scenario`
2. Use appropriate markers for test categorization
3. Mock external dependencies appropriately
4. Include both success and failure scenarios
5. Update this README if adding new test categories
