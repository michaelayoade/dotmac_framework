# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-01-XX

### Added

#### Core Infrastructure
- Initial release of dotmac-shared-core package
- Zero-dependency foundational utilities for the DotMac framework
- Complete type annotations with modern Python 3.9+ syntax
- Comprehensive test suite with >95% coverage requirement

#### Exception System (`dotmac_shared_core.exceptions`)
- `CoreError` - Base exception class with JSON serialization support
- `ValidationError` - Input validation failure exceptions  
- `NotFoundError` - Resource not found exceptions
- `ConflictError` - Resource conflict exceptions
- `UnauthorizedError` - Authentication required exceptions
- `ForbiddenError` - Authorization denied exceptions
- `ExternalServiceError` - External service failure exceptions
- `TimeoutError` - Operation timeout exceptions
- `to_dict()` function for converting any exception to JSON-serializable dict
- All exceptions include message, error_code, and optional details fields

#### Validation System (`dotmac_shared_core.validation`)
- `is_email()` - Email format validation using regex
- `is_uuid()` - UUID format validation  
- `ensure_in()` - Constraint validation for allowed values
- `ensure_range()` - Numeric range validation with min/max bounds
- `sanitize_text()` - Control character removal for text cleaning
- All validation functions designed for security and reliability

#### Common Utilities (`dotmac_shared_core.common`)
- **IDs module** (`ids`):
  - `new_uuid()` - Generate cryptographically secure UUID4
  - `new_ulid()` - Generate ULID (stub implementation returning UUID4 string)
- **Time module** (`time`):
  - `utcnow()` - Current UTC time with timezone awareness
  - `to_utc()` - Convert any datetime to UTC timezone
  - `isoformat()` - ISO 8601 formatting with UTC normalization
- **Paths module** (`paths`):  
  - `safe_join()` - Secure path joining with traversal attack prevention
  - Path resolution and validation to prevent directory escapes
  - Protection against symlink-based attacks

#### Type System (`dotmac_shared_core.types`)
- `JSON` - Type alias for JSON-serializable values
- `Result[T]` - Generic container for functional error handling
  - `Result.success()` - Create successful result
  - `Result.failure()` / `Result.error()` - Create error result  
  - `unwrap()` - Extract value or raise error
  - `unwrap_or()` - Extract value or return default
- Support for modern Python 3.9+ generic syntax

#### Package Features
- **Security-focused design**: Path traversal protection, safe text sanitization
- **JSON serialization**: All exceptions and data structures are JSON-compatible
- **UTC-first datetime handling**: All time operations normalize to UTC
- **Functional error handling**: Result container pattern for clean error management
- **Zero runtime dependencies**: Uses only Python standard library
- **Type safety**: Complete type annotations for IDE support and error catching

### Development Infrastructure
- Comprehensive pyproject.toml configuration
- pytest test suite with unit and integration tests
- Coverage reporting with 95% minimum threshold
- Code quality tools: ruff for linting and formatting, mypy for type checking
- Support for Python 3.9, 3.10, 3.11, 3.12

### Testing
- **Unit tests**: Complete coverage of all modules and functions
- **Integration tests**: Real-world usage scenarios and workflows
- **Property-based testing**: Edge case validation with hypothesis
- **Security testing**: Path traversal protection verification
- **Concurrency testing**: Thread-safety validation for ID generation
- **Error handling**: Comprehensive exception and Result container testing

[1.0.0]: https://github.com/dotmac-framework/dotmac/releases/tag/dotmac-shared-core-v1.0.0