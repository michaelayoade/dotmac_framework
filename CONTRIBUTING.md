# Contributing to DotMac ISP Framework

Thank you for your interest in contributing to the DotMac Framework! This document provides guidelines and information for contributors.

## 🤝 How to Contribute

### Reporting Issues

1. **Check existing issues** first to avoid duplicates
2. **Use issue templates** when available
3. **Provide clear reproduction steps** for bugs
4. **Include environment details** (OS, Python version, etc.)

### Suggesting Enhancements

1. **Check the roadmap** in discussions first
2. **Describe the use case** and why it's beneficial
3. **Consider backward compatibility** implications
4. **Provide implementation ideas** if possible

### Submitting Code Changes

1. **Fork the repository** and create a feature branch
2. **Follow development guidelines** (see below)
3. **Test your changes** thoroughly
4. **Submit a pull request** with clear description

## 🔧 Development Setup

### Prerequisites

- Python 3.9+
- PostgreSQL 12+
- Redis 6+
- Git

### Initial Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/dotmac-framework.git
cd dotmac-framework

# Set up development environment
make install-dev

# Configure environment
cp .env.example .env
# Edit .env with your local configuration

# Run tests to verify setup
make test
```

### Development Workflow

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and test frequently
make test-unit  # Fast unit tests during development

# Before committing, run full quality checks
make check

# Commit with conventional commit format
git commit -m "feat: add new authentication method"

# Push and create pull request
git push origin feature/your-feature-name
```

## 📝 Code Standards

### Python Code Style

We use **Black** and **Ruff** for code formatting:

```bash
# Format code automatically
make format

# Check formatting
make format-check
```

### Code Quality Requirements

- **Test Coverage**: Minimum 80% required
- **Type Hints**: Use type hints for all new code
- **Docstrings**: Document all public functions and classes
- **Complexity**: Max 10 cyclomatic complexity per function

### Complexity Rules

Our codebase enforces complexity limits:

```python
# ❌ Bad - Too complex (exceeds C901)
def complex_function(a, b, c, d, e, f, g, h, i):  # Too many args (PLR0913)
    if a:
        if b:
            if c:
                if d:
                    # ... many nested conditions
                    pass

# ✅ Good - Use classes and extracted methods
class ServiceProcessor:
    def __init__(self, config: ServiceConfig):
        self.config = config
    
    def process(self, request: ServiceRequest) -> ServiceResponse:
        # Clear, single responsibility
        pass
```

### Security Guidelines

- **Never commit secrets** - use environment variables
- **Validate all inputs** - use Pydantic models
- **Use parameterized queries** - prevent SQL injection
- **Log security events** - but not sensitive data
- **Follow OWASP guidelines** for web security

## 🧪 Testing

### Test Types

1. **Unit Tests** - Fast, isolated tests
   ```bash
   pytest -m unit
   ```

2. **Integration Tests** - Cross-service testing
   ```bash
   pytest -m integration
   ```

3. **Contract Tests** - API compatibility
   ```bash
   pytest -m contract
   ```

### Writing Tests

```python
# Unit test example
import pytest
from dotmac_services.models import Service

class TestServiceModel:
    def test_service_creation(self):
        service = Service(
            name="Fiber Internet",
            type="broadband",
            monthly_price=79.99
        )
        assert service.name == "Fiber Internet"
        assert service.is_active() is True

# Integration test example
class TestServiceAPI:
    @pytest.mark.integration
    async def test_create_service_endpoint(self, async_client):
        response = await async_client.post("/services", json={
            "name": "Fiber Internet",
            "type": "broadband",
            "monthly_price": 79.99
        })
        assert response.status_code == 201
        assert response.json()["name"] == "Fiber Internet"
```

### Test Fixtures

Use the global fixtures from `tests/conftest.py`:

```python
def test_customer_service(sample_customer_data, db_session):
    """Use shared fixtures for consistent testing."""
    # Test implementation
    pass
```

## 📦 Package Guidelines

### Adding New Packages

1. **Follow naming convention**: `dotmac_[domain]`
2. **Use package template**: Use `dotmac_devtools` to generate
3. **Include proper metadata**: pyproject.toml with dependencies
4. **Add to CI/CD**: Update GitHub Actions matrix

### Package Structure

```
dotmac_new_package/
├── dotmac_new_package/
│   ├── __init__.py
│   ├── api/           # FastAPI routes
│   ├── models/        # Data models
│   ├── services/      # Business logic
│   └── utils/         # Utilities
├── tests/
│   ├── __init__.py
│   ├── test_api.py
│   ├── test_models.py
│   └── test_services.py
├── pyproject.toml
└── README.md
```

### Dependencies

- **Pin exact versions** in requirements.lock
- **Use semantic versioning** for internal packages
- **Minimize dependencies** - avoid unnecessary packages
- **Security first** - regularly update vulnerable packages

## 🔄 Pull Request Process

### Before Submitting

1. **Run full test suite**
   ```bash
   make test
   ```

2. **Check code quality**
   ```bash
   make check
   ```

3. **Update documentation** if needed

4. **Add changelog entry** for user-facing changes

### PR Description Template

```markdown
## Description
Brief description of changes and motivation.

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that causes existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Added/updated unit tests
- [ ] Added/updated integration tests
- [ ] Manual testing performed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Tests pass locally
- [ ] Documentation updated
- [ ] No new security vulnerabilities

## Related Issues
Closes #123
```

### Review Process

1. **Automated checks** must pass (CI/CD pipeline)
2. **Code review** by maintainers
3. **Security review** for sensitive changes
4. **Manual testing** for significant features

## 🚀 Release Process

### Versioning

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Workflow

1. **Update version** in relevant pyproject.toml files
2. **Update CHANGELOG.md** with release notes
3. **Create release tag** following `v1.2.3` format
4. **GitHub Actions** automatically builds and publishes packages

## 🏷️ Commit Message Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

```bash
# Format
type(scope): description

# Examples
feat(billing): add automated invoice generation
fix(auth): resolve JWT token expiration issue
docs(api): update authentication endpoints
test(services): add integration tests for provisioning
refactor(networking): simplify device discovery logic
security(auth): patch authentication bypass vulnerability
```

### Types

- **feat**: New features
- **fix**: Bug fixes
- **docs**: Documentation changes
- **test**: Test additions/modifications
- **refactor**: Code refactoring
- **security**: Security improvements
- **perf**: Performance improvements
- **ci**: CI/CD changes

## 🏗️ Architecture Guidelines

### Service Design

- **Single Responsibility**: Each service has one clear purpose
- **Loose Coupling**: Minimal dependencies between services
- **Event-Driven**: Use events for service communication
- **API-First**: Design APIs before implementation

### Database Design

- **Normalized Schema**: Avoid data duplication
- **Migration Scripts**: Use Alembic for schema changes
- **Indexing Strategy**: Index frequently queried columns
- **Data Privacy**: Consider GDPR/privacy requirements

### Security Architecture

- **Defense in Depth**: Multiple security layers
- **Principle of Least Privilege**: Minimal required permissions
- **Input Validation**: Validate all external inputs
- **Audit Logging**: Log security-relevant events

## 📚 Documentation

### Code Documentation

```python
def calculate_monthly_bill(customer_id: str, billing_date: date) -> Decimal:
    """Calculate the monthly bill for a customer.
    
    Args:
        customer_id: Unique identifier for the customer
        billing_date: Date for which to calculate the bill
        
    Returns:
        Total amount due for the billing period
        
    Raises:
        CustomerNotFoundError: If customer doesn't exist
        BillingCalculationError: If calculation fails
        
    Example:
        >>> amount = calculate_monthly_bill("cust_123", date(2024, 1, 15))
        >>> print(f"Amount due: ${amount}")
        Amount due: $79.99
    """
```

### API Documentation

- **OpenAPI/Swagger** for all endpoints
- **Request/Response examples** with realistic data
- **Error code documentation** with explanations
- **Authentication requirements** clearly stated

## 🤖 Automation

### Pre-commit Hooks

Install pre-commit hooks for automatic code quality checks:

```bash
# Hooks are installed during make install-dev
# Manual installation:
pre-commit install
```

Our hooks run:
- Code formatting (Black, Ruff)
- Import sorting (isort)
- Type checking (MyPy)
- Security scanning (Bandit)
- Test execution (pytest)

### GitHub Actions

Our CI/CD pipeline includes:
- **Linting**: Code quality and complexity checks
- **Testing**: Comprehensive test suite across Python versions
- **Security**: Multiple security scanning tools
- **Package Validation**: Ensure packages build correctly
- **Documentation**: Auto-generate and deploy docs

## 🎯 Performance Guidelines

### Code Performance

- **Use async/await** for I/O operations
- **Implement caching** for expensive operations
- **Optimize database queries** - avoid N+1 problems
- **Profile critical paths** - measure before optimizing

### Database Performance

```python
# ❌ Bad - N+1 query problem
customers = session.query(Customer).all()
for customer in customers:
    services = customer.services  # Lazy loading - new query each time

# ✅ Good - Eager loading
customers = session.query(Customer).options(
    joinedload(Customer.services)
).all()
```

### API Performance

- **Implement pagination** for large datasets
- **Use HTTP caching** headers appropriately
- **Compress responses** when beneficial
- **Monitor response times** and set SLA targets

## 🔍 Debugging

### Local Development

```bash
# Enable debug mode
export DEBUG=true
export LOG_LEVEL=DEBUG

# Run with debugging
python -m pdb your_script.py

# Use debugger in tests
pytest --pdb
```

### Logging Best Practices

```python
import logging
from dotmac_core_ops.logging import get_logger

logger = get_logger(__name__)

def process_payment(payment_id: str) -> bool:
    logger.info(
        "Processing payment",
        extra={
            "payment_id": payment_id,
            "action": "payment_processing_started"
        }
    )
    
    try:
        # Process payment
        result = payment_processor.charge(payment_id)
        logger.info(
            "Payment processed successfully",
            extra={
                "payment_id": payment_id,
                "amount": result.amount,
                "action": "payment_processed"
            }
        )
        return True
    except PaymentError as e:
        logger.error(
            "Payment processing failed",
            extra={
                "payment_id": payment_id,
                "error": str(e),
                "action": "payment_failed"
            }
        )
        return False
```

## 📋 Checklist for New Contributors

- [ ] Read this contributing guide
- [ ] Set up development environment
- [ ] Run `make test` successfully
- [ ] Understand code quality standards
- [ ] Join project discussions
- [ ] Look for "good first issue" labels

## 🎉 Recognition

We value all contributions! Contributors are recognized in:

- **CONTRIBUTORS.md** file
- **Release notes** for significant contributions
- **GitHub repository** insights
- **Project documentation** credits

## 📞 Getting Help

- **GitHub Discussions** - General questions and ideas
- **GitHub Issues** - Bug reports and feature requests
- **Code Reviews** - Learning opportunity through PR feedback
- **Documentation** - Comprehensive guides and references

## 🔗 Resources

- [Python Style Guide (PEP 8)](https://pep8.org/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [pytest Documentation](https://docs.pytest.org/)
- [Git Workflow Guide](https://guides.github.com/introduction/flow/)

Thank you for contributing to DotMac Framework! 🚀