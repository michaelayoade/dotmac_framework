"""
Test cases for DotMac Core exceptions.
"""

from dotmac.core.exceptions import (
    AlreadyExistsError,
    AuthenticationError,
    AuthorizationError,
    BusinessRuleError,
    CacheConnectionError,
    CacheError,
    CacheSerializationError,
    CircuitBreakerError,
    ConfigurationError,
    ConnectionError,
    DatabaseConnectionError,
    DatabaseError,
    DatabaseMigrationError,
    DatabaseTransactionError,
    DotMacError,
    EntityNotFoundError,
    ExternalServiceError,
    IntegrityError,
    MultiTenantError,
    NotFoundError,
    PermissionError,
    PluginError,
    PluginLoadError,
    PluginValidationError,
    QueryError,
    RateLimitError,
    SDKError,
    ServiceConfigurationError,
    ServiceError,
    ServiceUnavailableError,
    TenantConfigurationError,
    TenantError,
    TenantNotFoundError,
    TimeoutError,
    TransactionError,
    ValidationError,
)


class TestDotMacError:
    """Test base DotMacError class."""

    def test_basic_error_creation(self):
        """Test basic error creation with message only."""
        error = DotMacError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"
        assert error.error_code is None
        assert error.details == {}

    def test_error_with_code(self):
        """Test error creation with error code."""
        error = DotMacError("Database connection failed", error_code="DB001")
        assert str(error) == "[DB001] Database connection failed"
        assert error.error_code == "DB001"

    def test_error_with_details(self):
        """Test error creation with details."""
        details = {"host": "localhost", "port": 5432}
        error = DotMacError("Connection failed", details=details)
        assert error.details == details

    def test_error_to_dict(self):
        """Test error serialization to dict."""
        details = {"field": "value"}
        error = DotMacError("Test error", error_code="TEST001", details=details)
        result = error.to_dict()

        expected = {
            "error": "DotMacError",
            "message": "Test error",
            "error_code": "TEST001",
            "details": details,
        }
        assert result == expected

    def test_error_inheritance(self):
        """Test that DotMacError inherits from Exception."""
        error = DotMacError("Test")
        assert isinstance(error, Exception)


class TestSpecificErrors:
    """Test specific error types."""

    def test_validation_error(self):
        """Test ValidationError."""
        error = ValidationError("Invalid input", error_code="VAL001")
        assert isinstance(error, DotMacError)
        assert str(error) == "[VAL001] Invalid input"

    def test_authentication_error(self):
        """Test AuthenticationError."""
        error = AuthenticationError("Invalid credentials")
        assert isinstance(error, DotMacError)
        assert str(error) == "Invalid credentials"

    def test_authorization_error(self):
        """Test AuthorizationError."""
        error = AuthorizationError("Access denied")
        assert isinstance(error, DotMacError)

    def test_configuration_error(self):
        """Test ConfigurationError."""
        error = ConfigurationError("Missing config")
        assert isinstance(error, DotMacError)

    def test_connection_error(self):
        """Test ConnectionError."""
        error = ConnectionError("Cannot connect")
        assert isinstance(error, DotMacError)

    def test_timeout_error(self):
        """Test TimeoutError."""
        error = TimeoutError("Operation timed out")
        assert isinstance(error, DotMacError)

    def test_rate_limit_error(self):
        """Test RateLimitError."""
        error = RateLimitError("Rate limit exceeded")
        assert isinstance(error, DotMacError)

    def test_circuit_breaker_error(self):
        """Test CircuitBreakerError."""
        error = CircuitBreakerError("Circuit breaker open")
        assert isinstance(error, DotMacError)

    def test_sdk_error(self):
        """Test SDKError."""
        error = SDKError("SDK error")
        assert isinstance(error, DotMacError)


class TestDatabaseErrors:
    """Test database-specific errors."""

    def test_database_error(self):
        """Test base DatabaseError."""
        error = DatabaseError("Database error")
        assert isinstance(error, DotMacError)

    def test_transaction_error(self):
        """Test TransactionError."""
        error = TransactionError("Transaction failed")
        assert isinstance(error, DatabaseError)

    def test_database_connection_error(self):
        """Test DatabaseConnectionError."""
        error = DatabaseConnectionError("Cannot connect to database")
        assert isinstance(error, DatabaseError)
        assert isinstance(error, ConnectionError)

    def test_database_transaction_error(self):
        """Test DatabaseTransactionError."""
        error = DatabaseTransactionError("Transaction rollback")
        assert isinstance(error, DatabaseError)

    def test_database_migration_error(self):
        """Test DatabaseMigrationError."""
        error = DatabaseMigrationError("Migration failed")
        assert isinstance(error, DatabaseError)

    def test_query_error(self):
        """Test QueryError."""
        error = QueryError("Query failed")
        assert isinstance(error, DatabaseError)

    def test_integrity_error(self):
        """Test IntegrityError."""
        error = IntegrityError("Constraint violation")
        assert isinstance(error, DatabaseError)


class TestTenantErrors:
    """Test tenant-specific errors."""

    def test_tenant_error(self):
        """Test base TenantError."""
        error = TenantError("Tenant error")
        assert isinstance(error, DotMacError)

    def test_tenant_not_found_error(self):
        """Test TenantNotFoundError."""
        error = TenantNotFoundError("Tenant not found")
        assert isinstance(error, TenantError)

    def test_tenant_configuration_error(self):
        """Test TenantConfigurationError."""
        error = TenantConfigurationError("Invalid tenant config")
        assert isinstance(error, TenantError)

    def test_multi_tenant_error(self):
        """Test MultiTenantError."""
        error = MultiTenantError("Multiple tenants found")
        assert isinstance(error, TenantError)


class TestCacheErrors:
    """Test cache-specific errors."""

    def test_cache_error(self):
        """Test base CacheError."""
        error = CacheError("Cache error")
        assert isinstance(error, DotMacError)

    def test_cache_connection_error(self):
        """Test CacheConnectionError."""
        error = CacheConnectionError("Cannot connect to cache")
        assert isinstance(error, CacheError)
        assert isinstance(error, ConnectionError)

    def test_cache_serialization_error(self):
        """Test CacheSerializationError."""
        error = CacheSerializationError("Cannot serialize data")
        assert isinstance(error, CacheError)


class TestPluginErrors:
    """Test plugin-specific errors."""

    def test_plugin_error(self):
        """Test base PluginError."""
        error = PluginError("Plugin error")
        assert isinstance(error, DotMacError)

    def test_plugin_load_error(self):
        """Test PluginLoadError."""
        error = PluginLoadError("Cannot load plugin")
        assert isinstance(error, PluginError)

    def test_plugin_validation_error(self):
        """Test PluginValidationError."""
        error = PluginValidationError("Plugin validation failed")
        assert isinstance(error, PluginError)
        assert isinstance(error, ValidationError)


class TestServiceErrors:
    """Test service-specific errors."""

    def test_service_error(self):
        """Test base ServiceError."""
        error = ServiceError("Service error")
        assert isinstance(error, DotMacError)

    def test_service_unavailable_error(self):
        """Test ServiceUnavailableError."""
        error = ServiceUnavailableError("Service unavailable")
        assert isinstance(error, ServiceError)

    def test_service_configuration_error(self):
        """Test ServiceConfigurationError."""
        error = ServiceConfigurationError("Invalid service config")
        assert isinstance(error, ServiceError)
        assert isinstance(error, ConfigurationError)

    def test_business_rule_error(self):
        """Test BusinessRuleError."""
        error = BusinessRuleError("Business rule violation")
        assert isinstance(error, DotMacError)

    def test_not_found_error(self):
        """Test NotFoundError."""
        error = NotFoundError("Resource not found")
        assert isinstance(error, DotMacError)

    def test_already_exists_error(self):
        """Test AlreadyExistsError."""
        error = AlreadyExistsError("Resource already exists")
        assert isinstance(error, DotMacError)

    def test_entity_not_found_error(self):
        """Test EntityNotFoundError alias."""
        error = EntityNotFoundError("Entity not found")
        assert isinstance(error, NotFoundError)

    def test_external_service_error(self):
        """Test ExternalServiceError."""
        error = ExternalServiceError("External service failed")
        assert isinstance(error, ServiceError)

    def test_permission_error(self):
        """Test PermissionError alias."""
        error = PermissionError("Permission denied")
        assert isinstance(error, AuthorizationError)
