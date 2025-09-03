# Changelog

All notable changes to the dotmac-tasks package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-09-03

### Added

#### Core Features
- **Idempotent Operations**: Complete idempotency system with deterministic key generation
- **Saga Workflows**: Distributed transaction pattern with automatic compensation on failure
- **HTTP Middleware**: FastAPI middleware for automatic idempotency enforcement
- **Pluggable Storage**: Abstract storage interface with memory and Redis implementations
- **Distributed Locking**: SETNX-based distributed locks with automatic timeout

#### Storage Backends
- **MemoryStorage**: In-memory storage backend for development and testing
- **RedisStorage**: Production-ready Redis backend with:
  - HASH-based idempotency key storage
  - JSON-based saga workflow persistence  
  - ZSET-based indexing for cleanup operations
  - LIST-based saga history tracking
  - Pipeline operations for atomic updates

#### Models and Data Structures
- `IdempotencyKey`: Represents idempotent operations with status tracking
- `SagaWorkflow`: Multi-step distributed transaction workflows
- `SagaStep`: Individual steps within saga workflows with retry logic
- `BackgroundOperation`: General background operation tracking
- `OperationStatus` and `SagaStepStatus` enums for status management

#### Manager and Orchestration
- `BackgroundOperationsManager`: Central orchestrator for all background operations
  - Operation handler registration system
  - Compensation handler registration for saga rollbacks
  - Deterministic idempotency key generation using SHA256
  - Saga workflow creation and execution
  - Background cleanup of expired data

#### HTTP Integration
- `BackgroundOperationsMiddleware`: FastAPI middleware for automatic idempotency
  - Processes `Idempotency-Key` headers
  - Returns cached results for completed operations (200 + `X-Cache-Hit: true`)
  - Returns 202 status for in-progress operations
  - Configurable exempt paths and header names
- Helper functions: `get_idempotency_key()`, `set_operation_result()`, `is_idempotent_request()`
- `add_background_operations_middleware()` convenience function

#### Error Handling and Resilience
- Graceful degradation when storage backends are unavailable
- Automatic retry logic for saga steps with configurable max retries
- Comprehensive error logging and debugging information
- Exception handling that doesn't break request processing

#### Testing Infrastructure
- Comprehensive test suite with 100% coverage
- Separate test files for each component:
  - `test_idempotency.py`: Idempotency operations testing
  - `test_saga.py`: Saga workflow testing with compensation scenarios
  - `test_middleware.py`: HTTP middleware integration testing
  - `test_storage_memory.py`: In-memory storage backend testing
  - `test_storage_redis.py`: Redis storage backend testing (requires Redis server)
- Redis tests properly marked with `@pytest.mark.redis` for conditional execution
- Concurrent operation testing to ensure thread safety

#### Observability and Metrics
- Metrics hooks system for integration with observability platforms
- Health check endpoints for storage backends
- Storage statistics and monitoring capabilities
- Structured logging throughout the codebase

#### Configuration and Deployment
- Environment variable configuration support
- Optional Redis dependency with `pip install dotmac-tasks[redis]`
- Configurable timeouts, TTLs, and cleanup intervals
- Production-ready defaults with development-friendly fallbacks

### Migration from dotmac_shared

#### Deprecation Support
- Created deprecation shims in `dotmac_shared.middleware.background_operations`
- Automatic import forwarding with deprecation warnings
- Graceful fallback when new package is not installed
- Clear migration instructions in deprecation warnings

#### API Compatibility
- Maintained backward compatibility for existing API surface
- Enhanced functionality while preserving familiar interfaces
- Improved error handling and type safety
- Better documentation and examples

### Technical Implementation Details

#### Redis Schema Design
```
bgops:idempo:{key}        -> HASH (idempotency key data)
bgops:idempo:index        -> ZSET (timestamp-based cleanup index)
bgops:saga:{saga_id}      -> JSON (saga workflow state)
bgops:saga:history:{id}   -> LIST (saga execution history)
bgops:lock:{key}          -> STRING (distributed lock with TTL)
```

#### Key Generation Algorithm
- Deterministic SHA256-based key generation
- Input: `tenant_id:user_id:operation_type:parameters_json`
- Ensures identical inputs always produce identical keys
- Truncated to 32 characters for practical use

#### Saga Compensation Logic
- Compensation executes in reverse order of completed steps
- Failed steps do not trigger their own compensation
- Individual compensation failures do not stop the process
- Final saga status indicates compensation success/failure

#### Distributed Locking
- Uses Redis SETNX for atomic lock acquisition
- Automatic expiration prevents deadlocks
- Lock release uses Lua script for atomicity
- Handles Redis connection failures gracefully

### Performance Characteristics

- **Idempotency lookups**: O(1) with Redis HASH operations
- **Saga execution**: Sequential step processing with atomic state updates
- **Background cleanup**: Efficient ZSET-based expired key retrieval
- **Concurrent operations**: Safe for multiple application instances
- **Memory usage**: Configurable TTLs prevent unbounded growth

### Security Considerations

- **Tenant isolation**: All operations scoped by tenant_id
- **Parameter validation**: Input sanitization and type checking
- **Error disclosure**: Careful error message handling to prevent information leakage
- **Redis security**: Supports Redis AUTH and TLS connections

### Known Limitations

- **Saga step parallelism**: Current implementation executes steps sequentially
- **Cross-saga dependencies**: No built-in support for saga orchestration
- **Storage backend switching**: Requires application restart to change backends
- **Large parameter sets**: Very large operation parameters may impact performance

### Future Roadmap

- Parallel saga step execution
- Cross-saga workflow orchestration
- Additional storage backends (PostgreSQL, DynamoDB)
- Real-time saga execution monitoring
- Saga workflow templating system
- Performance optimizations for high-throughput scenarios

---

## Release Notes

This initial 1.0.0 release represents a complete rewrite and enhancement of the background operations functionality previously found in `dotmac_shared.middleware.background_operations`. 

### Migration Timeline
- **Immediate**: New projects should use `dotmac.tasks`
- **Phase 1** (Next 30 days): Existing projects should begin migration
- **Phase 2** (60 days): Deprecation warnings will be upgraded to errors
- **Phase 3** (90 days): Legacy code will be removed from `dotmac_shared`

### Installation Instructions
```bash
# For new projects
pip install dotmac-tasks[redis]

# For existing projects (migration period)
pip install dotmac-tasks[redis]  # Add new package
# Update imports gradually
# Remove old imports
```

This release establishes a solid foundation for background operations in the DotMac platform with significantly improved reliability, observability, and maintainability.