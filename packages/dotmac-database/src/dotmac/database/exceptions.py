"""
Database-specific exceptions for dotmac-database package.

Provides a hierarchy of exceptions for different database error scenarios
to enable more precise error handling in applications.
"""


class DatabaseError(Exception):
    """
    Base exception for all database-related errors.
    
    This is the root exception class that all other database exceptions
    inherit from. Use this for general database error handling.
    """
    pass


class ConnectionError(DatabaseError):
    """
    Raised when database connection fails or is lost.
    
    This includes initial connection failures, connection timeouts,
    and unexpected connection drops during operations.
    """
    pass


class TransactionError(DatabaseError):
    """
    Raised when transaction operations fail.
    
    This includes transaction commit failures, rollback errors,
    deadlocks, and other transaction-specific issues.
    """
    pass


class ValidationError(DatabaseError):
    """
    Raised when data validation fails at the database level.
    
    This includes constraint violations, foreign key errors,
    unique constraint violations, and other data validation issues.
    """
    pass


class ConstraintViolationError(ValidationError):
    """
    Raised when database constraints are violated.
    
    More specific than ValidationError, this is for actual database
    constraint violations like NOT NULL, CHECK constraints, etc.
    """
    pass


class UniqueConstraintViolationError(ConstraintViolationError):
    """
    Raised when unique constraint violations occur.
    
    Specific exception for duplicate key/unique constraint errors,
    allowing applications to handle these specially (e.g., showing
    "email already exists" messages).
    """
    pass


class ForeignKeyConstraintViolationError(ConstraintViolationError):
    """
    Raised when foreign key constraints are violated.
    
    Occurs when trying to insert/update records that reference
    non-existent records in related tables.
    """
    pass


class MigrationError(DatabaseError):
    """
    Raised when database migration operations fail.
    
    This includes schema migration failures, version conflicts,
    and other migration-related issues.
    """
    pass


class ConfigurationError(DatabaseError):
    """
    Raised when database configuration is invalid.
    
    This includes invalid connection strings, missing required
    configuration parameters, and other setup issues.
    """
    pass


class SchemaError(DatabaseError):
    """
    Raised when database schema operations fail.
    
    This includes schema creation/deletion failures, table operations,
    and other schema management issues.
    """
    pass


class LockError(DatabaseError):
    """
    Base exception for locking-related errors.
    
    Used by coordination/locking modules for lock acquisition
    failures and other locking issues.
    """
    pass


class LockTimeout(LockError):
    """
    Raised when lock acquisition times out.
    
    Specific exception for when a lock cannot be acquired
    within the specified timeout period.
    """
    pass


class LockNotAcquired(LockError):
    """
    Raised when lock acquisition fails immediately.
    
    Used in non-blocking lock acquisition scenarios when
    the lock is not available.
    """
    pass


class CacheError(DatabaseError):
    """
    Base exception for caching-related errors.
    
    Used by caching modules for cache operation failures,
    connection issues, and other cache-related problems.
    """
    pass


class CacheConnectionError(CacheError):
    """
    Raised when cache backend connection fails.
    
    Specific exception for when the cache backend (Redis, etc.)
    is not available or connection fails.
    """
    pass


class CacheSerializationError(CacheError):
    """
    Raised when cache serialization/deserialization fails.
    
    Occurs when objects cannot be serialized for caching or
    when cached data cannot be deserialized properly.
    """
    pass