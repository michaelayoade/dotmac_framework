# Contributing to DotMac Core

Thank you for your interest in contributing to the DotMac Core package! This document provides guidelines and information for contributors.

## Development Setup

### Prerequisites

- Python 3.9 or higher
- Git
- Poetry (recommended) or pip

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/dotmac-framework/dotmac-core.git
   cd dotmac-core
   ```

2. **Install development dependencies**:
   ```bash
   # Using pip
   pip install -e ".[dev]"
   
   # Using poetry (if available)
   poetry install --with dev
   ```

3. **Set up pre-commit hooks** (optional but recommended):
   ```bash
   pre-commit install
   ```

## Development Workflow

### Code Style

We use several tools to maintain consistent code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **Ruff**: Fast Python linting
- **MyPy**: Static type checking

Run all formatting and linting:

```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint code
ruff check src/ tests/

# Type check
mypy src/
```

### Testing

We maintain comprehensive test coverage with multiple test categories:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=dotmac.core --cov-report=html

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests
pytest -m database      # Database tests (requires database)
pytest -m redis         # Redis tests (requires Redis)
pytest -m slow          # Slow running tests
```

### Test Requirements

- **Minimum coverage**: 90% (enforced by CI)
- **All tests must pass**: No failing tests in pull requests
- **New features require tests**: Add tests for any new functionality
- **Async support**: Use `pytest.mark.asyncio` for async tests

## Contribution Guidelines

### Pull Request Process

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**:
   - Follow the existing code style
   - Add tests for new functionality
   - Update documentation as needed

3. **Run quality checks**:
   ```bash
   # Run all checks
   make check  # or run individual tools
   
   black src/ tests/
   ruff check src/ tests/
   mypy src/
   pytest
   ```

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

5. **Push and create pull request**:
   ```bash
   git push origin feature/your-feature-name
   ```

### Commit Message Format

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples**:
```
feat(tenant): add subdomain resolution support
fix(cache): resolve redis connection timeout issue
docs: update installation instructions
test(decorators): add retry decorator test cases
```

## Code Organization

### Package Structure

```
src/dotmac/core/
├── __init__.py          # Main package exports
├── exceptions.py        # Exception hierarchy
├── tenant.py           # Tenant management
├── config.py           # Configuration classes
├── decorators.py       # Common decorators
├── types.py            # Core types
├── logging.py          # Logging utilities
├── database.py         # Database compatibility
├── cache/              # Cache services
├── schemas/            # Pydantic schemas
└── db_toolkit/         # Database utilities
```

### Coding Standards

1. **Type Annotations**: All public functions must have type annotations
2. **Docstrings**: All public functions and classes must have docstrings
3. **Error Handling**: Use appropriate exceptions from the exception hierarchy
4. **Testing**: Follow the Arrange-Act-Assert pattern
5. **Async Support**: Use async/await for I/O operations

### Documentation Standards

- **Docstrings**: Use Google-style docstrings
- **README**: Update README.md for significant changes
- **CHANGELOG**: Add entries to CHANGELOG.md for all changes
- **Type Hints**: All public APIs must be fully typed

## Issue Reporting

### Bug Reports

When reporting bugs, please include:

- **Python version**
- **Package version**
- **Minimal reproduction case**
- **Expected behavior**
- **Actual behavior**
- **Error messages/tracebacks**

### Feature Requests

When requesting features, please include:

- **Use case description**
- **Proposed API design**
- **Example usage**
- **Backward compatibility considerations**

## Architecture Guidelines

### Design Principles

1. **DRY Compliance**: Eliminate code duplication across the framework
2. **Production Ready**: All code must be production-ready
3. **Type Safety**: Comprehensive typing support
4. **Error Resilience**: Proper error handling and recovery
5. **Performance**: Optimize for high-performance applications

### Dependencies

- **Core Dependencies**: Keep to minimum essential packages
- **Optional Dependencies**: Use optional extras for specialized features
- **Version Constraints**: Use compatible version ranges
- **Security**: Regular dependency security audits

### Backward Compatibility

- **Semantic Versioning**: Follow semver strictly
- **Deprecation Warnings**: Provide warnings before breaking changes
- **Migration Guides**: Document migration paths for breaking changes
- **Legacy Support**: Maintain compatibility layers when possible

## Release Process

### Versioning

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Checklist

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Run full test suite
4. Create release PR
5. Tag release after merge
6. Publish to PyPI

## Getting Help

- **Documentation**: Check the README and docstrings
- **Issues**: Search existing issues before creating new ones
- **Discussions**: Use GitHub Discussions for questions
- **Code Review**: Ask for code review help in PR comments

## Recognition

Contributors will be recognized in:

- **CONTRIBUTORS.md**: List of all contributors
- **Release Notes**: Notable contributions mentioned
- **Git History**: All contributions tracked in git

Thank you for contributing to DotMac Core!