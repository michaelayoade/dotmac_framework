"""
Schema validator for workflow events using schema registry integration.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

import structlog
from pydantic import ValidationError

from ..contracts.workflow_events import WorkflowEventType, EVENT_TYPE_MAPPING

logger = structlog.get_logger(__name__)


class SchemaValidationError(Exception):
    """Exception raised when schema validation fails."""
    pass


class SchemaValidator:
    """
    Schema validator for workflow events with schema registry integration.

    Integrates with dotmac_core_events SchemaRegistrySDK for centralized schema management.
    """

    def __init__(
        self,
        schema_registry_sdk,  # From dotmac_core_events
        cache_ttl_seconds: int = 3600,
        enable_strict_validation: bool = True
    ):
        self.schema_registry = schema_registry_sdk
        self.cache_ttl_seconds = cache_ttl_seconds
        self.enable_strict_validation = enable_strict_validation
        self._schema_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamps: Dict[str, datetime] = {}

    async def validate_event(
        self,
        event_type: WorkflowEventType,
        event_data: Dict[str, Any],
        schema_version: Optional[str] = None
    ) -> bool:
        """
        Validate an event against its schema.

        Args:
            event_type: Type of workflow event
            event_data: Event data to validate
            schema_version: Optional specific schema version to use

        Returns:
            True if validation passes

        Raises:
            SchemaValidationError: If validation fails
        """
        try:
            # Get schema for event type
            schema = await self._get_schema(event_type, schema_version)

            if not schema:
                if self.enable_strict_validation:
                    raise SchemaValidationError(f"No schema found for event type: {event_type.value}")
                else:
                    logger.warning("No schema found, skipping validation", event_type=event_type.value)
                    return True

            # Validate using Pydantic model if available
            event_class = EVENT_TYPE_MAPPING.get(event_type)
            if event_class:
                try:
                    # Validate using Pydantic model
                    event_class(**event_data)
                    logger.debug("Event validation passed", event_type=event_type.value)
                    return True
                except ValidationError as e:
                    raise SchemaValidationError(f"Pydantic validation failed: {e}")

            # Fallback to JSON schema validation via schema registry
            validation_result = await self.schema_registry.validate_data(
                subject=f"ops.workflow.{event_type.value}",
                data=event_data,
                version=schema_version
            )

            if not validation_result.is_valid:
                raise SchemaValidationError(
                    f"Schema validation failed: {validation_result.errors}"
                )

            logger.debug("Event validation passed", event_type=event_type.value)
            return True

        except ValidationError as e:
            logger.error(
                "Event validation failed",
                event_type=event_type.value,
                validation_errors=e.errors() if hasattr(e, 'errors') else str(e)
            )
            raise SchemaValidationError(f"Validation failed: {e}")

        except Exception as e:
            logger.error(
                "Unexpected error during validation",
                event_type=event_type.value,
                error=str(e)
            )
            if self.enable_strict_validation:
                raise SchemaValidationError(f"Validation error: {e}")
            else:
                logger.warning("Validation error ignored due to non-strict mode")
                return True

    async def _get_schema(
        self,
        event_type: WorkflowEventType,
        version: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get schema for event type from cache or schema registry."""
        cache_key = f"{event_type.value}:{version or 'latest'}"

        # Check cache first
        if cache_key in self._schema_cache:
            cache_time = self._cache_timestamps.get(cache_key)
            if cache_time and (datetime.now(timezone.utc) - cache_time).total_seconds() < self.cache_ttl_seconds:
                return self._schema_cache[cache_key]

        try:
            # Fetch from schema registry
            subject = f"ops.workflow.{event_type.value}"

            if version:
                schema_result = await self.schema_registry.get_schema(subject, version)
            else:
                schema_result = await self.schema_registry.get_latest_schema(subject)

            if schema_result and schema_result.schema:
                # Cache the schema
                self._schema_cache[cache_key] = schema_result.schema
                self._cache_timestamps[cache_key] = datetime.now(timezone.utc)
                return schema_result.schema

        except Exception as e:
            logger.error(
                "Failed to fetch schema from registry",
                event_type=event_type.value,
                version=version,
                error=str(e)
            )

        return None

    async def register_event_schemas(self) -> bool:
        """
        Register all workflow event schemas with the schema registry.

        Returns:
            True if all schemas were registered successfully
        """
        success_count = 0
        total_count = len(EVENT_TYPE_MAPPING)

        for event_type, event_class in EVENT_TYPE_MAPPING.items():
            try:
                # Generate JSON schema from Pydantic model
                json_schema = event_class.schema()

                # Register schema with registry
                subject = f"ops.workflow.{event_type.value}"

                result = await self.schema_registry.register_schema(
                    subject=subject,
                    schema=json_schema,
                    schema_type="JSON"
                )

                if result.success:
                    success_count += 1
                    logger.info(
                        "Registered event schema",
                        event_type=event_type.value,
                        subject=subject,
                        version=result.version
                    )
                else:
                    logger.error(
                        "Failed to register event schema",
                        event_type=event_type.value,
                        subject=subject,
                        error=result.error
                    )

            except Exception as e:
                logger.error(
                    "Error registering event schema",
                    event_type=event_type.value,
                    error=str(e)
                )

        logger.info(
            "Schema registration completed",
            success_count=success_count,
            total_count=total_count
        )

        return success_count == total_count

    async def validate_schema_compatibility(
        self,
        event_type: WorkflowEventType,
        new_schema: Dict[str, Any]
    ) -> bool:
        """
        Check if a new schema is compatible with existing schemas.

        Args:
            event_type: Type of workflow event
            new_schema: New schema to check compatibility

        Returns:
            True if compatible
        """
        try:
            subject = f"ops.workflow.{event_type.value}"

            compatibility_result = await self.schema_registry.check_compatibility(
                subject=subject,
                schema=new_schema
            )

            if compatibility_result.is_compatible:
                logger.info(
                    "Schema compatibility check passed",
                    event_type=event_type.value,
                    subject=subject
                )
                return True
            else:
                logger.warning(
                    "Schema compatibility check failed",
                    event_type=event_type.value,
                    subject=subject,
                    issues=compatibility_result.issues
                )
                return False

        except Exception as e:
            logger.error(
                "Error checking schema compatibility",
                event_type=event_type.value,
                error=str(e)
            )
            return False

    async def get_schema_evolution_history(
        self,
        event_type: WorkflowEventType
    ) -> List[Dict[str, Any]]:
        """Get schema evolution history for an event type."""
        try:
            subject = f"ops.workflow.{event_type.value}"

            versions = await self.schema_registry.get_schema_versions(subject)

            history = []
            for version in versions:
                schema_result = await self.schema_registry.get_schema(subject, str(version))
                if schema_result:
                    history.append({
                        "version": version,
                        "schema": schema_result.schema,
                        "registered_at": schema_result.registered_at
                    })

            return history

        except Exception as e:
            logger.error(
                "Error fetching schema evolution history",
                event_type=event_type.value,
                error=str(e)
            )
            return []

    async def clear_schema_cache(self):
        """Clear the schema cache."""
        self._schema_cache.clear()
        self._cache_timestamps.clear()
        logger.info("Schema cache cleared")

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        now = datetime.now(timezone.utc)

        valid_entries = 0
        expired_entries = 0

        for cache_key, cache_time in self._cache_timestamps.items():
            if (now - cache_time).total_seconds() < self.cache_ttl_seconds:
                valid_entries += 1
            else:
                expired_entries += 1

        return {
            "total_entries": len(self._schema_cache),
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "cache_ttl_seconds": self.cache_ttl_seconds
        }
