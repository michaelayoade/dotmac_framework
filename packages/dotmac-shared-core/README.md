# DotMac Shared Core

Foundational utilities for the DotMac framework providing lightweight, dependency-free utilities for exceptions, validation, common operations, and type definitions that are used across all services.

## Features

- **Zero runtime dependencies** - Uses only Python standard library
- **Type-safe** - Full type annotations with modern Python 3.9+ syntax
- **Security-focused** - Path traversal protection, safe text sanitization
- **JSON-serializable exceptions** - Perfect for API error responses
- **Functional error handling** - Result container pattern for clean error management
- **Timezone-aware datetime utilities** - Always UTC, always correct

## Installation

```bash
# Install from local development
pip install -e .

# Or install development dependencies
pip install -e ".[dev]"
```

## Quick Start

```python
from dotmac_shared_core import (
    ValidationError, 
    ensure_range, 
    is_email,
    Result,
    common
)

# Generate unique IDs
user_id = common.ids.new_uuid()
timestamp = common.time.utcnow()

# Validate input
try:
    ensure_range(age, min_val=18, max_val=120, field="age")
    if not is_email(email):
        raise ValidationError("Invalid email format", "INVALID_EMAIL")
except ValidationError as e:
    return Result.failure(e)

# Handle results functionally
result = Result.success({"user_id": str(user_id), "age": age})
if result.ok:
    print(f"Created user: {result.value}")
```

## API Reference

### Exceptions

All exceptions inherit from `CoreError` and are JSON-serializable:

```python
from dotmac_shared_core import ValidationError, to_dict

try:
    raise ValidationError("Invalid input", "INVALID_INPUT", {"field": "email"})
except ValidationError as e:
    error_dict = to_dict(e)  # Perfect for API responses
    # {"message": "Invalid input", "error_code": "INVALID_INPUT", "details": {...}}
```

Available exceptions:
- `CoreError` - Base exception class
- `ValidationError` - Input validation failures
- `NotFoundError` - Resource not found
- `ConflictError` - Resource conflicts
- `UnauthorizedError` - Authentication required
- `ForbiddenError` - Authorization denied
- `ExternalServiceError` - External service failures  
- `TimeoutError` - Operation timeouts

### Validation

```python
from dotmac_shared_core import is_email, is_uuid, ensure_in, ensure_range, sanitize_text

# Format validation
assert is_email("user@example.com")
assert is_uuid("550e8400-e29b-41d4-a716-446655440000")

# Constraint validation (raises ValidationError on failure)
ensure_range(25, min_val=18, max_val=120, field="age")
ensure_in("admin", ["admin", "user", "guest"], "role")

# Text sanitization (removes control characters)
clean = sanitize_text("Hello\\x00World\\x01")  # -> "HelloWorld"
```

### Common Utilities

#### IDs
```python
from dotmac_shared_core.common import ids

user_id = ids.new_uuid()  # UUID4 object
correlation_id = ids.new_ulid()  # String (currently UUID4 stub)
```

#### Time (Always UTC)
```python
from dotmac_shared_core.common import time

now = time.utcnow()  # Current UTC time with timezone
utc_dt = time.to_utc(local_dt)  # Convert any datetime to UTC
iso_string = time.isoformat(dt)  # ISO format with UTC timezone
```

#### Paths (Security-focused)
```python
from dotmac_shared_core.common import paths
from pathlib import Path

# Safe path joining with traversal protection
safe_path = paths.safe_join(Path("/var/data"), "user", "file.txt")
# Raises ValidationError if path escapes root directory
```

### Result Container

Functional error handling without exceptions:

```python
from dotmac_shared_core import Result, ValidationError

def process_data(value: str) -> Result[str]:
    if not value:
        return Result.failure(ValidationError("Empty value", "EMPTY"))
    return Result.success(value.upper())

result = process_data("hello")
if result.ok:
    print(result.value)  # "HELLO"
else:
    print(result.error.message)  # Error handling
    
# Convenient unwrapping
processed = result.unwrap_or("default")  # Returns value or default
```

### Type Definitions

```python
from dotmac_shared_core import JSON, Result

# JSON-serializable type hint
def api_response(data: JSON) -> dict:
    return {"success": True, "data": data}

# Generic Result container
def fetch_user(id: str) -> Result[dict]:
    # ... implementation
    pass
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# With coverage
pytest --cov=dotmac_shared_core --cov-report=html

# Run specific test types
pytest tests/unit/
pytest tests/integration/
```

### Code Quality

```bash
# Format code
ruff format .

# Lint and fix
ruff check --fix .

# Type checking
mypy src/dotmac_shared_core
```

## Design Principles

1. **Zero Dependencies** - Only uses Python standard library to avoid dependency conflicts
2. **Security First** - All file operations include path traversal protection
3. **Type Safety** - Comprehensive type annotations for better IDE support and error catching
4. **JSON Compatibility** - All exceptions and data structures are JSON-serializable
5. **UTC Always** - All datetime operations assume and return UTC to avoid timezone bugs
6. **Fail Fast** - Validation functions raise exceptions immediately rather than returning booleans

## License

MIT License - see LICENSE file for details.