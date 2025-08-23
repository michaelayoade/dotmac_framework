# Contributing to DotMac ISP Framework

Thank you for your interest in contributing to the DotMac ISP Framework! This document provides guidelines and procedures for contributing to this project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Commit Guidelines](#commit-guidelines)
- [Testing](#testing)
- [Security](#security)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

This project adheres to a code of conduct adapted from the [Contributor Covenant](https://www.contributor-covenant.org/). By participating, you are expected to uphold this code.

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend development)
- Docker and Docker Compose
- Git
- Make

### Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/YOUR_USERNAME/dotmac_isp_framework.git
   cd dotmac_isp_framework
   ```

2. **Set up Development Environment**
   ```bash
   make install-dev
   ```

3. **Install Pre-commit Hooks**
   ```bash
   pre-commit install
   pre-commit install --hook-type commit-msg
   ```

4. **Verify Setup**
   ```bash
   make check
   ```

## Development Workflow

We use **GitFlow** branching strategy with the following branches:

### Branch Types

- **main**: Production-ready code
- **develop**: Integration branch for features
- **feature/**: New features (`feature/add-billing-integration`)
- **hotfix/**: Critical fixes for production (`hotfix/fix-security-vulnerability`)
- **release/**: Prepare releases (`release/v1.2.0`)

### Workflow Steps

1. **Create Feature Branch**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature-name
   ```

2. **Develop and Test**
   ```bash
   # Make your changes
   make lint          # Check code quality
   make test          # Run tests
   make security      # Security scan
   ```

3. **Commit Changes**
   ```bash
   git add .
   git commit         # This will open the commit template
   ```

4. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   # Create PR via GitHub UI
   ```

## Coding Standards

### Python Standards

- **Line Length**: 88 characters (Black formatter)
- **Complexity**: Maximum 10 (McCabe complexity)
- **Type Hints**: Required for all public functions
- **Docstrings**: Required for all modules, classes, and public functions

### Code Quality Tools

All code must pass:
- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting with complexity checks
- **mypy**: Type checking
- **bandit**: Security scanning

### Architecture Patterns

- **Repository Pattern**: For data access
- **Dependency Injection**: Use FastAPI's Depends()
- **Service Layer**: Business logic separation
- **Event Sourcing**: For critical business entities
- **CQRS**: Command Query Responsibility Separation

### File Organization

```
src/dotmac_isp/modules/[domain]/
├── __init__.py
├── models/          # Data models
├── repositories/    # Data access layer
├── services/        # Business logic
├── routers/         # API endpoints
├── schemas/         # Pydantic schemas
└── exceptions.py    # Domain exceptions
```

## Commit Guidelines

We use **Conventional Commits** format:

```
<type>(<scope>): <description>

<body>

<footer>
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, etc.)
- **refactor**: Code refactoring
- **perf**: Performance improvements
- **test**: Adding/updating tests
- **build**: Build system changes
- **ci**: CI/CD changes
- **chore**: Maintenance tasks

### Examples

```bash
feat(billing): add subscription management API

Implement subscription creation, modification, and cancellation
endpoints with proper validation and error handling.

Closes #123
```

```bash
fix(identity): resolve JWT token validation issue

Fixed issue where expired tokens were being accepted due to
incorrect timezone handling in token validation.

Breaking Change: Token validation now strictly enforces UTC timezone
```

## Testing

### Test Strategy

- **70% Unit Tests**: Fast, isolated tests
- **20% Integration Tests**: Cross-service testing  
- **10% E2E Tests**: Full workflow testing

### Test Markers

```python
import pytest

@pytest.mark.unit
def test_user_creation():
    """Unit test for user creation logic."""
    pass

@pytest.mark.integration
def test_billing_service_integration():
    """Integration test with billing service."""
    pass

@pytest.mark.e2e
def test_complete_user_workflow():
    """End-to-end test of user workflow."""
    pass
```

### Running Tests

```bash
# All tests
make test

# Specific test types
make test-unit
make test-integration

# Docker-based testing (recommended)
make test-docker

# Specific service
make test-package PACKAGE=dotmac_identity
```

### Test Coverage

- **Minimum**: 80% coverage required
- **Target**: 90%+ coverage preferred
- **Coverage Report**: Generated automatically

## Security

### Security Requirements

- **No hardcoded secrets**: Use environment variables
- **Input validation**: Validate all inputs
- **SQL injection prevention**: Use parameterized queries
- **XSS prevention**: Sanitize outputs
- **Authentication**: JWT-based with proper expiration
- **Authorization**: Role-based access control (RBAC)

### Security Scanning

All contributions must pass:

```bash
make security        # Standard security scan
make security-strict # Strict security scan (fails on issues)
```

### Reporting Security Issues

Please report security vulnerabilities privately via email to security@dotmac.ng.

## Pull Request Process

### PR Checklist

Before submitting a PR, ensure:

- [ ] Code passes all quality checks (`make check`)
- [ ] Tests are added/updated and passing
- [ ] Documentation is updated
- [ ] Security scan passes
- [ ] Feature is covered by appropriate tests
- [ ] Breaking changes are documented
- [ ] Commit messages follow conventional format

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature  
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
```

### Review Process

1. **Automated Checks**: CI/CD pipeline runs automatically
2. **Code Review**: At least one maintainer review required
3. **Testing**: All tests must pass
4. **Security**: Security scans must pass
5. **Approval**: Maintainer approval required
6. **Merge**: Squash and merge to maintain clean history

### Branch Protection

- **main**: Requires PR, reviews, passing status checks
- **develop**: Requires PR, passing status checks
- **No direct pushes**: All changes via PRs

## Development Guidelines

### Service Development

1. **Start with Tests**: Write tests first (TDD approach)
2. **Repository Pattern**: Implement data access layer
3. **Service Layer**: Business logic implementation
4. **API Layer**: FastAPI routers and endpoints
5. **Documentation**: OpenAPI/Swagger documentation

### Database Changes

1. **Migrations**: Use Alembic for database migrations
2. **Backward Compatibility**: Ensure migrations are reversible
3. **Testing**: Test migrations in development environment
4. **Documentation**: Document schema changes

### API Development

1. **OpenAPI**: Comprehensive API documentation
2. **Versioning**: Use semantic versioning for APIs
3. **Error Handling**: Consistent error response format
4. **Rate Limiting**: Implement appropriate rate limits
5. **Authentication**: Secure all endpoints appropriately

## Getting Help

- **Documentation**: Check existing documentation first
- **Issues**: Search existing issues on GitHub
- **Discussions**: Use GitHub Discussions for questions
- **Contact**: Reach out to maintainers for guidance

## Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes for significant contributions
- Annual contributor recognition

Thank you for contributing to the DotMac ISP Framework!