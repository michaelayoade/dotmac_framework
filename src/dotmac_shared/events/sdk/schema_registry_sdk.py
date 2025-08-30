"""
Schema Registry SDK - Simplified schema management API.

Provides a high-level interface for event schema management
with automatic validation and simplified usage patterns.
"""

from typing import Any, Dict, List, Optional

import structlog

from ..core.models import EventBusError, EventRecord
from ..core.schema_registry import (
    CompatibilityLevel,
    RegistrationResult,
    SchemaRegistry,
    ValidationResult,
)

logger = structlog.get_logger(__name__)


class SchemaRegistrySDK:
    """
    High-level Schema Registry SDK.

    Provides simplified schema management operations with:
    - Automatic schema validation
    - Simplified registration APIs
    - Built-in compatibility checking
    - Multi-tenant schema isolation
    """

    def __init__(
        self,
        schema_registry: Optional[SchemaRegistry] = None,
        default_compatibility: CompatibilityLevel = CompatibilityLevel.BACKWARD,
    ):
        """
        Initialize Schema Registry SDK.

        Args:
            schema_registry: Schema registry instance (creates new if None)
            default_compatibility: Default compatibility level
        """
        self.schema_registry = schema_registry or SchemaRegistry(default_compatibility)

        logger.info(
            "Schema Registry SDK initialized",
            default_compatibility=default_compatibility,
        )

    async def register_event_schema(
        self,
        event_type: str,
        schema: Dict[str, Any],
        *,
        tenant_id: Optional[str] = None,
        description: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> RegistrationResult:
        """
        Register schema for an event type.

        Args:
            event_type: Event type (e.g., 'user.created')
            schema: JSON Schema definition
            tenant_id: Tenant ID for multi-tenancy
            description: Schema version description
            created_by: User registering the schema

        Returns:
            RegistrationResult with version information
        """
        try:
            result = await self.schema_registry.register_schema(
                subject=event_type,
                schema=schema,
                tenant_id=tenant_id,
                description=description,
                created_by=created_by,
            )

            logger.info(
                "Event schema registered via SDK",
                event_type=event_type,
                version=result.version,
                created=result.created,
                tenant_id=tenant_id,
            )

            return result

        except Exception as e:
            logger.error(
                "Failed to register event schema via SDK",
                event_type=event_type,
                tenant_id=tenant_id,
                error=str(e),
            )
            raise EventBusError(
                f"Failed to register schema for '{event_type}': {e}"
            ) from e

    async def validate_event_data(
        self,
        event_type: str,
        data: Dict[str, Any],
        *,
        tenant_id: Optional[str] = None,
        version: Optional[int] = None,
    ) -> ValidationResult:
        """
        Validate event data against its schema.

        Args:
            event_type: Event type
            data: Event data to validate
            tenant_id: Tenant ID
            version: Specific schema version (uses latest if None)

        Returns:
            ValidationResult with validation details
        """
        try:
            # Create a minimal event record for validation
            from ..core.models import EventMetadata

            metadata = EventMetadata(tenant_id=tenant_id)

            event = EventRecord(event_type=event_type, data=data, metadata=metadata)

            result = await self.schema_registry.validate_event(
                event=event, version=version, tenant_id=tenant_id
            )

            if result.valid:
                logger.debug(
                    "Event data validation passed via SDK",
                    event_type=event_type,
                    version=result.version,
                )
            else:
                logger.warning(
                    "Event data validation failed via SDK",
                    event_type=event_type,
                    version=result.version,
                    errors=result.errors,
                )

            return result

        except Exception as e:
            logger.error(
                "Failed to validate event data via SDK",
                event_type=event_type,
                tenant_id=tenant_id,
                error=str(e),
            )

            return ValidationResult(
                valid=False,
                errors=[f"Validation error: {e}"],
                subject=event_type,
                version=version or 0,
            )

    async def get_event_schema(
        self,
        event_type: str,
        *,
        tenant_id: Optional[str] = None,
        version: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get schema for an event type.

        Args:
            event_type: Event type
            tenant_id: Tenant ID
            version: Schema version (latest if None)

        Returns:
            Schema definition or None if not found
        """
        try:
            schema = await self.schema_registry.get_schema(
                subject=event_type, version=version, tenant_id=tenant_id
            )

            if schema:
                logger.debug(
                    "Event schema retrieved via SDK",
                    event_type=event_type,
                    version=version,
                    tenant_id=tenant_id,
                )
            else:
                logger.warning(
                    "Event schema not found via SDK",
                    event_type=event_type,
                    version=version,
                    tenant_id=tenant_id,
                )

            return schema

        except Exception as e:
            logger.error(
                "Failed to get event schema via SDK",
                event_type=event_type,
                tenant_id=tenant_id,
                error=str(e),
            )
            return None

    async def list_event_types(self, tenant_id: Optional[str] = None) -> List[str]:
        """
        List all registered event types.

        Args:
            tenant_id: Filter by tenant ID

        Returns:
            List of event type names
        """
        try:
            event_types = await self.schema_registry.list_subjects(tenant_id=tenant_id)

            logger.debug(
                "Listed event types via SDK",
                count=len(event_types),
                tenant_id=tenant_id,
            )

            return event_types

        except Exception as e:
            logger.error(
                "Failed to list event types via SDK", tenant_id=tenant_id, error=str(e)
            )
            return []

    async def list_schema_versions(
        self, event_type: str, *, tenant_id: Optional[str] = None
    ) -> List[int]:
        """
        List all versions for an event type schema.

        Args:
            event_type: Event type
            tenant_id: Tenant ID

        Returns:
            List of version numbers
        """
        try:
            versions = await self.schema_registry.list_versions(
                subject=event_type, tenant_id=tenant_id
            )

            logger.debug(
                "Listed schema versions via SDK",
                event_type=event_type,
                versions=versions,
                tenant_id=tenant_id,
            )

            return versions

        except Exception as e:
            logger.error(
                "Failed to list schema versions via SDK",
                event_type=event_type,
                tenant_id=tenant_id,
                error=str(e),
            )
            return []

    async def register_common_schemas(
        self, tenant_id: Optional[str] = None
    ) -> Dict[str, RegistrationResult]:
        """
        Register common event schemas for typical use cases.

        Args:
            tenant_id: Tenant ID

        Returns:
            Dictionary mapping event type to registration result
        """
        try:
            # Define common schemas
            common_schemas = {
                "user.created": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "email": {"type": "string", "format": "email"},
                        "name": {"type": "string"},
                        "created_at": {"type": "string", "format": "date-time"},
                    },
                    "required": ["user_id", "email", "name", "created_at"],
                },
                "user.updated": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "changes": {"type": "object", "additionalProperties": True},
                        "updated_at": {"type": "string", "format": "date-time"},
                    },
                    "required": ["user_id", "changes", "updated_at"],
                },
                "user.deleted": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "deleted_at": {"type": "string", "format": "date-time"},
                    },
                    "required": ["user_id", "deleted_at"],
                },
                "order.created": {
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "string"},
                        "customer_id": {"type": "string"},
                        "total_amount": {"type": "number"},
                        "currency": {"type": "string"},
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "product_id": {"type": "string"},
                                    "quantity": {"type": "integer"},
                                    "price": {"type": "number"},
                                },
                                "required": ["product_id", "quantity", "price"],
                            },
                        },
                        "created_at": {"type": "string", "format": "date-time"},
                    },
                    "required": [
                        "order_id",
                        "customer_id",
                        "total_amount",
                        "currency",
                        "items",
                        "created_at",
                    ],
                },
            }

            # Register all schemas
            results = {}
            for event_type, schema in common_schemas.items():
                try:
                    result = await self.register_event_schema(
                        event_type=event_type,
                        schema=schema,
                        tenant_id=tenant_id,
                        description=f"Common schema for {event_type} events",
                        created_by="system",
                    )
                    results[event_type] = result

                except Exception as e:
                    logger.error(
                        "Failed to register common schema",
                        event_type=event_type,
                        error=str(e),
                    )
                    # Continue with other schemas

            logger.info(
                "Registered common schemas via SDK",
                registered_count=len(results),
                tenant_id=tenant_id,
            )

            return results

        except Exception as e:
            logger.error(
                "Failed to register common schemas via SDK",
                tenant_id=tenant_id,
                error=str(e),
            )
            return {}

    async def get_registry_stats(self) -> Dict[str, Any]:
        """Get schema registry statistics."""
        try:
            return await self.schema_registry.get_registry_stats()
        except Exception as e:
            logger.error("Failed to get schema registry stats", error=str(e))
            return {"error": str(e)}

    def create_basic_schema(
        self,
        properties: Dict[str, Dict[str, Any]],
        required: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a basic JSON Schema from properties.

        Args:
            properties: Property definitions
            required: List of required property names

        Returns:
            JSON Schema definition
        """
        schema = {"type": "object", "properties": properties}

        if required:
            schema["required"] = required

        return schema

    @classmethod
    def create_in_memory_registry(
        cls, default_compatibility: CompatibilityLevel = CompatibilityLevel.BACKWARD
    ) -> "SchemaRegistrySDK":
        """Create an in-memory schema registry for testing."""
        return cls(default_compatibility=default_compatibility)
