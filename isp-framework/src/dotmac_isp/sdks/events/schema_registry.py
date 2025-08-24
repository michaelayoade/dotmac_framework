"""
Schema Registry SDK for dotmac_core_events.

Provides schema management with:
- JSON Schema validation and storage
- Schema versioning and evolution
- Compatibility checking between versions
- In-memory and persistent caching
- Multi-tenant schema isolation
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import jsonschema
import structlog

logger = structlog.get_logger(__name__)


class SchemaRegistryError(Exception):
    """Base exception for Schema Registry operations."""

    pass


class SchemaValidationError(SchemaRegistryError):
    """Exception raised when schema validation fails."""

    pass


class SchemaNotFoundError(SchemaRegistryError):
    """Exception raised when schema is not found."""

    pass


class CompatibilityError(SchemaRegistryError):
    """Exception raised when schemas are incompatible."""

    pass


class CompatibilityLevel(Enum):
    """Schema compatibility levels."""

    BACKWARD = "BACKWARD"  # New schema can read old data
    FORWARD = "FORWARD"  # Old schema can read new data
    FULL = "FULL"  # Both backward and forward compatible
    NONE = "NONE"  # No compatibility checking


@dataclass
class SchemaVersion:
    """Schema version information."""

    event_type: str
    version: str
    schema: Dict[str, Any]
    compatibility_level: CompatibilityLevel
    created_at: datetime
    created_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_type": self.event_type,
            "version": self.version,
            "schema": self.schema,
            "compatibility_level": self.compatibility_level.value,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SchemaVersion":
        """Create from dictionary."""
        return cls(
            event_type=data["event_type"],
            version=data["version"],
            schema=data["schema"],
            compatibility_level=CompatibilityLevel(data["compatibility_level"]),
            created_at=datetime.fromisoformat(
                data["created_at"].replace("Z", "+00:00")
            ),
            created_by=data.get("created_by"),
        )


@dataclass
class RegistrationResult:
    """Result of schema registration."""

    schema_id: str
    event_type: str
    version: str
    compatibility_level: CompatibilityLevel

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "schema_id": self.schema_id,
            "event_type": self.event_type,
            "version": self.version,
            "compatibility_level": self.compatibility_level.value,
        }


@dataclass
class ValidationResult:
    """Result of schema validation."""

    valid: bool
    errors: List[Dict[str, Any]]
    schema_version: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "valid": self.valid,
            "errors": self.errors,
            "schema_version": self.schema_version,
        }


class SchemaStore(ABC):
    """Abstract interface for schema storage."""

    @abstractmethod
    async def store_schema(self, schema_version: SchemaVersion) -> str:
        """Store a schema version and return its ID."""
        pass

    @abstractmethod
    async def get_schema(
        self, event_type: str, version: Optional[str] = None
    ) -> Optional[SchemaVersion]:
        """Get a schema by event type and version."""
        pass

    @abstractmethod
    async def list_versions(self, event_type: str) -> List[str]:
        """List all versions for an event type."""
        pass

    @abstractmethod
    async def delete_schema(
        self, event_type: str, version: Optional[str] = None
    ) -> None:
        """Delete a schema version or all versions."""
        pass

    @abstractmethod
    async def list_event_types(self) -> List[str]:
        """List all event types with schemas."""
        pass


class InMemorySchemaStore(SchemaStore):
    """In-memory schema store for development and testing."""

    def __init__(self):
        """  Init   operation."""
        self._schemas: Dict[str, Dict[str, SchemaVersion]] = {}
        self._latest_versions: Dict[str, str] = {}

    def _get_schema_id(self, event_type: str, version: str) -> str:
        """Generate schema ID."""
        return f"{event_type}:{version}"

    async def store_schema(self, schema_version: SchemaVersion) -> str:
        """Store a schema version."""
        event_type = schema_version.event_type
        version = schema_version.version

        if event_type not in self._schemas:
            self._schemas[event_type] = {}

        self._schemas[event_type][version] = schema_version
        self._latest_versions[event_type] = version

        return self._get_schema_id(event_type, version)

    async def get_schema(
        self, event_type: str, version: Optional[str] = None
    ) -> Optional[SchemaVersion]:
        """Get a schema by event type and version."""
        if event_type not in self._schemas:
            return None

        if version is None:
            version = self._latest_versions.get(event_type)
            if version is None:
                return None

        return self._schemas[event_type].get(version)

    async def list_versions(self, event_type: str) -> List[str]:
        """List all versions for an event type."""
        if event_type not in self._schemas:
            return []
        return list(self._schemas[event_type].keys())

    async def delete_schema(
        self, event_type: str, version: Optional[str] = None
    ) -> None:
        """Delete a schema version or all versions."""
        if event_type not in self._schemas:
            return

        if version is None:
            # Delete all versions
            del self._schemas[event_type]
            self._latest_versions.pop(event_type, None)
        else:
            # Delete specific version
            self._schemas[event_type].pop(version, None)
            if not self._schemas[event_type]:
                del self._schemas[event_type]
                self._latest_versions.pop(event_type, None)
            elif self._latest_versions.get(event_type) == version:
                # Update latest version
                remaining_versions = list(self._schemas[event_type].keys())
                if remaining_versions:
                    self._latest_versions[event_type] = max(remaining_versions)

    async def list_event_types(self) -> List[str]:
        """List all event types with schemas."""
        return list(self._schemas.keys())


class SchemaCache:
    """In-memory cache for schemas."""

    def __init__(self, max_size: int = 1000):
        """  Init   operation."""
        self.max_size = max_size
        self._cache: Dict[str, SchemaVersion] = {}
        self._access_order: List[str] = []

    def _make_key(self, event_type: str, version: Optional[str] = None) -> str:
        """Make cache key."""
        return f"{event_type}:{version or 'latest'}"

    def get(
        self, event_type: str, version: Optional[str] = None
    ) -> Optional[SchemaVersion]:
        """Get schema from cache."""
        key = self._make_key(event_type, version)

        if key in self._cache:
            # Move to end (most recently used)
            self._access_order.remove(key)
            self._access_order.append(key)
            return self._cache[key]

        return None

    def put(self, schema_version: SchemaVersion, version: Optional[str] = None) -> None:
        """Put schema in cache."""
        key = self._make_key(
            schema_version.event_type, version or schema_version.version
        )

        # Remove if already exists
        if key in self._cache:
            self._access_order.remove(key)

        # Add to cache
        self._cache[key] = schema_version
        self._access_order.append(key)

        # Evict if over size limit
        while len(self._cache) > self.max_size:
            oldest_key = self._access_order.pop(0)
            del self._cache[oldest_key]

    def invalidate(self, event_type: str, version: Optional[str] = None) -> None:
        """Invalidate cache entry."""
        key = self._make_key(event_type, version)

        if key in self._cache:
            del self._cache[key]
            self._access_order.remove(key)

    async def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._access_order.clear()


class SchemaRegistrySDK:
    """
    Schema Registry SDK with JSON Schema validation and versioning.

    Provides:
    - Schema registration and retrieval
    - JSON Schema validation
    - Schema versioning and compatibility checking
    - Caching for performance
    - Multi-tenant isolation
    """

    def __init__(
        self,
        tenant_id: str,
        store: Optional[SchemaStore] = None,
        cache_size: int = 1000,
    ):
        """
        Initialize the Schema Registry SDK.

        Args:
            tenant_id: Tenant identifier for isolation
            store: Schema store implementation (defaults to in-memory)
            cache_size: Maximum number of schemas to cache
        """
        self.tenant_id = tenant_id
        self.store = store or InMemorySchemaStore()
        self.cache = SchemaCache(cache_size)

        # Metrics
        self._registration_count = 0
        self._validation_count = 0
        self._cache_hits = 0
        self._cache_misses = 0

    def _get_tenant_event_type(self, event_type: str) -> str:
        """Add tenant prefix to event type."""
        return f"tenant-{self.tenant_id}.{event_type}"

    def _remove_tenant_prefix(self, tenant_event_type: str) -> str:
        """Remove tenant prefix from event type."""
        prefix = f"tenant-{self.tenant_id}."
        if tenant_event_type.startswith(prefix):
            return tenant_event_type[len(prefix) :]
        return tenant_event_type

    async def register_schema(
        self,
        event_type: str,
        version: str,
        schema: Dict[str, Any],
        compatibility_level: CompatibilityLevel = CompatibilityLevel.BACKWARD,
        created_by: Optional[str] = None,
    ) -> RegistrationResult:
        """
        Register a new schema version.

        Args:
            event_type: Event type identifier
            version: Schema version
            schema: JSON schema definition
            compatibility_level: Compatibility level for this schema
            created_by: Optional creator identifier

        Returns:
            RegistrationResult with schema details

        Raises:
            SchemaValidationError: If schema is invalid
            CompatibilityError: If schema is incompatible with existing versions
        """
        try:
            # Validate the schema itself
            jsonschema.Draft7Validator.check_schema(schema)

            # Check compatibility with existing schemas
            tenant_event_type = self._get_tenant_event_type(event_type)
            await self._check_compatibility(
                tenant_event_type, schema, compatibility_level
            )

            # Create schema version
            schema_version = SchemaVersion(
                event_type=tenant_event_type,
                version=version,
                schema=schema,
                compatibility_level=compatibility_level,
                created_at=datetime.now(timezone.utc),
                created_by=created_by,
            )

            # Store schema
            schema_id = await self.store.store_schema(schema_version)

            # Update cache
            self.cache.put(schema_version)
            self.cache.put(schema_version, None)  # Also cache as latest

            # Update metrics
            self._registration_count += 1

            logger.info(
                "Schema registered",
                event_type=event_type,
                version=version,
                schema_id=schema_id,
                tenant_id=self.tenant_id,
            )

            return RegistrationResult(
                schema_id=schema_id,
                event_type=event_type,
                version=version,
                compatibility_level=compatibility_level,
            )

        except jsonschema.SchemaError as e:
            raise SchemaValidationError(f"Invalid schema: {e}") from e
        except Exception as e:
            logger.error(
                "Failed to register schema",
                event_type=event_type,
                version=version,
                error=str(e),
            )
            raise SchemaRegistryError(f"Failed to register schema: {e}") from e

    async def get_schema(
        self,
        event_type: str,
        version: Optional[str] = None,
    ) -> Optional[SchemaVersion]:
        """
        Get a schema by event type and version.

        Args:
            event_type: Event type identifier
            version: Schema version (latest if not specified)

        Returns:
            SchemaVersion if found, None otherwise
        """
        tenant_event_type = self._get_tenant_event_type(event_type)

        # Try cache first
        cached_schema = self.cache.get(tenant_event_type, version)
        if cached_schema:
            self._cache_hits += 1
            return cached_schema

        self._cache_misses += 1

        # Get from store
        schema_version = await self.store.get_schema(tenant_event_type, version)

        if schema_version:
            # Cache the result
            self.cache.put(schema_version, version)

            # Remove tenant prefix from result
            schema_version.event_type = self._remove_tenant_prefix(
                schema_version.event_type
            )

        return schema_version

    async def validate_data(
        self,
        event_type: str,
        data: Dict[str, Any],
        version: Optional[str] = None,
    ) -> ValidationResult:
        """
        Validate data against a schema.

        Args:
            event_type: Event type identifier
            data: Data to validate
            version: Schema version (latest if not specified)

        Returns:
            ValidationResult with validation status and errors
        """
        try:
            # Get schema
            schema_version = await self.get_schema(event_type, version)
            if not schema_version:
                return ValidationResult(
                    valid=False,
                    errors=[
                        {"message": f"Schema not found for event type: {event_type}"}
                    ],
                )

            # Validate data
            validator = jsonschema.Draft7Validator(schema_version.schema)
            errors = []

            for error in validator.iter_errors(data):
                errors.append(
                    {
                        "path": ".".join(str(p) for p in error.absolute_path),
                        "message": error.message,
                        "code": error.validator,
                    }
                )

            # Update metrics
            self._validation_count += 1

            result = ValidationResult(
                valid=len(errors) == 0,
                errors=errors,
                schema_version=schema_version.version,
            )

            if not result.valid:
                logger.debug(
                    "Data validation failed",
                    event_type=event_type,
                    version=schema_version.version,
                    error_count=len(errors),
                )

            return result

        except Exception as e:
            logger.error(
                "Validation error",
                event_type=event_type,
                version=version,
                error=str(e),
            )
            return ValidationResult(
                valid=False,
                errors=[{"message": f"Validation error: {e}"}],
            )

    async def check_compatibility(
        self,
        event_type: str,
        schema: Dict[str, Any],
        version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Check if a schema is compatible with existing versions.

        Args:
            event_type: Event type identifier
            schema: Schema to check
            version: Version to check against (latest if not specified)

        Returns:
            Compatibility result dictionary
        """
        tenant_event_type = self._get_tenant_event_type(event_type)

        try:
            existing_schema = await self.store.get_schema(tenant_event_type, version)
            if not existing_schema:
                return {
                    "compatible": True,
                    "message": "No existing schema to compare against",
                }

            # Simple compatibility check (can be enhanced)
            compatible = self._schemas_compatible(
                existing_schema.schema,
                schema,
                existing_schema.compatibility_level,
            )

            return {
                "compatible": compatible,
                "compatibility_level": existing_schema.compatibility_level.value,
                "compared_version": existing_schema.version,
            }

        except Exception as e:
            logger.error(
                "Compatibility check failed",
                event_type=event_type,
                error=str(e),
            )
            return {
                "compatible": False,
                "error": str(e),
            }

    async def list_versions(self, event_type: str) -> List[str]:
        """
        List all versions for an event type.

        Args:
            event_type: Event type identifier

        Returns:
            List of version strings
        """
        tenant_event_type = self._get_tenant_event_type(event_type)
        return await self.store.list_versions(tenant_event_type)

    async def delete_schema(
        self,
        event_type: str,
        version: Optional[str] = None,
    ) -> None:
        """
        Delete a schema version or all versions for an event type.

        Args:
            event_type: Event type identifier
            version: Version to delete (all if not specified)
        """
        tenant_event_type = self._get_tenant_event_type(event_type)

        # Invalidate cache
        self.cache.invalidate(tenant_event_type, version)
        if version is None:
            # Invalidate all versions
            versions = await self.store.list_versions(tenant_event_type)
            for v in versions:
                self.cache.invalidate(tenant_event_type, v)

        # Delete from store
        await self.store.delete_schema(tenant_event_type, version)

        logger.info(
            "Schema deleted",
            event_type=event_type,
            version=version or "all",
            tenant_id=self.tenant_id,
        )

    async def list_event_types(self) -> List[str]:
        """
        List all event types with schemas for this tenant.

        Returns:
            List of event type identifiers
        """
        all_event_types = await self.store.list_event_types()

        # Filter by tenant and remove prefix
        tenant_prefix = f"tenant-{self.tenant_id}."
        tenant_event_types = [
            self._remove_tenant_prefix(et)
            for et in all_event_types
            if et.startswith(tenant_prefix)
        ]

        return tenant_event_types

    async def _check_compatibility(
        self,
        event_type: str,
        new_schema: Dict[str, Any],
        compatibility_level: CompatibilityLevel,
    ) -> None:
        """Check compatibility with existing schemas."""
        if compatibility_level == CompatibilityLevel.NONE:
            return

        existing_schema = await self.store.get_schema(event_type)
        if not existing_schema:
            return  # No existing schema to check against

        if not self._schemas_compatible(
            existing_schema.schema,
            new_schema,
            compatibility_level,
        ):
            raise CompatibilityError(
                f"Schema is not {compatibility_level.value} compatible"
            )

    def _schemas_compatible(
        self,
        old_schema: Dict[str, Any],
        new_schema: Dict[str, Any],
        compatibility_level: CompatibilityLevel,
    ) -> bool:
        """
        Check if two schemas are compatible.

        This is a simplified implementation. In production, you would want
        more sophisticated compatibility checking.
        """
        if compatibility_level == CompatibilityLevel.NONE:
            return True

        # Simple check: ensure required fields are not removed
        old_required = set(old_schema.get("required", []))
        new_required = set(new_schema.get("required", []))

        if compatibility_level in [
            CompatibilityLevel.BACKWARD,
            CompatibilityLevel.FULL,
        ]:
            # Backward compatibility: new schema can't add required fields
            if not old_required.issuperset(new_required):
                return False

        if compatibility_level in [CompatibilityLevel.FORWARD, CompatibilityLevel.FULL]:
            # Forward compatibility: new schema can't remove required fields
            if not new_required.issuperset(old_required):
                return False

        return True

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get SDK metrics.

        Returns:
            Dictionary of metrics
        """
        return {
            "tenant_id": self.tenant_id,
            "registration_count": self._registration_count,
            "validation_count": self._validation_count,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_hit_rate": (
                self._cache_hits / (self._cache_hits + self._cache_misses)
                if (self._cache_hits + self._cache_misses) > 0
                else 0
            ),
        }
