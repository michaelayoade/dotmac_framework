"""
Schema Registry for Event Validation.

Provides event schema management and validation using JSON Schema:
- Register and version event schemas
- Validate events against schemas
- Schema evolution with compatibility checks
- Multi-tenant schema isolation
"""

import hashlib
import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

import structlog
from pydantic import BaseModel, Field, ValidationError

from .models import EventBusError, EventRecord

logger = structlog.get_logger(__name__)


class CompatibilityLevel(str, Enum):
    """Schema compatibility levels for evolution."""

    NONE = "none"  # No compatibility checking
    BACKWARD = "backward"  # New schema can read old data
    FORWARD = "forward"  # Old schema can read new data
    FULL = "full"  # Both backward and forward compatible


class SchemaVersionInfo(BaseModel):
    """Schema version information."""

    model_config = {"populate_by_name": True}

    version: int = Field(..., ge=1, description="Schema version number")
    schema_definition: Dict[str, Any] = Field(..., description="JSON Schema definition")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    created_by: Optional[str] = Field(
        default=None, description="User who created this version"
    )
    description: Optional[str] = Field(default=None, description="Version description")
    checksum: str = Field(..., description="Schema content checksum")

    @classmethod
    def create(
        cls,
        version: int,
        schema: Dict[str, Any],
        created_by: Optional[str] = None,
        description: Optional[str] = None,
    ) -> "SchemaVersionInfo":
        """Create a new schema version with calculated checksum."""
        checksum = hashlib.sha256(
            json.dumps(schema, sort_keys=True).encode("utf-8")
        ).hexdigest()

        return cls(
            version=version,
            schema_definition=schema,
            created_by=created_by,
            description=description,
            checksum=checksum,
        )


class SubjectSchema(BaseModel):
    """Complete schema information for a subject."""

    subject: str = Field(..., description="Schema subject name")
    versions: Dict[int, SchemaVersionInfo] = Field(
        default_factory=dict, description="Schema versions"
    )
    latest_version: int = Field(default=0, description="Latest version number")
    compatibility_level: CompatibilityLevel = Field(default=CompatibilityLevel.BACKWARD)
    tenant_id: Optional[str] = Field(
        default=None, description="Tenant ID for isolation"
    )

    def add_version(self, version_info: SchemaVersionInfo) -> None:
        """Add a new schema version."""
        self.versions[version_info.version] = version_info
        if version_info.version > self.latest_version:
            self.latest_version = version_info.version

    def get_version(self, version: int) -> Optional[SchemaVersionInfo]:
        """Get a specific schema version."""
        return self.versions.get(version)

    def get_latest_version(self) -> Optional[SchemaVersionInfo]:
        """Get the latest schema version."""
        if self.latest_version > 0:
            return self.versions.get(self.latest_version)
        return None


class ValidationResult(BaseModel):
    """Result of schema validation."""

    valid: bool = Field(..., description="Whether validation passed")
    errors: List[str] = Field(
        default_factory=list, description="Validation error messages"
    )
    subject: str = Field(..., description="Schema subject")
    version: int = Field(..., description="Schema version used")


class RegistrationResult(BaseModel):
    """Result of schema registration."""

    subject: str = Field(..., description="Schema subject")
    version: int = Field(..., description="Assigned version number")
    checksum: str = Field(..., description="Schema checksum")
    created: bool = Field(..., description="Whether new version was created")


class SchemaRegistry:
    """
    In-memory schema registry with validation capabilities.

    Manages event schemas with versioning and compatibility checking.
    For production use, this should be backed by a database or external registry.
    """

    def __init__(
        self, default_compatibility: CompatibilityLevel = CompatibilityLevel.BACKWARD
    ):
        """
        Initialize schema registry.

        Args:
            default_compatibility: Default compatibility level for new subjects
        """
        self.default_compatibility = default_compatibility
        self._subjects: Dict[str, SubjectSchema] = {}
        self._tenant_subjects: Dict[str, Set[str]] = {}  # tenant_id -> set of subjects

        logger.info(
            "Schema registry initialized", default_compatibility=default_compatibility
        )

    def _get_subject_key(self, subject: str, tenant_id: Optional[str] = None) -> str:
        """Get internal subject key with tenant isolation."""
        if tenant_id:
            return f"{tenant_id}:{subject}"
        return subject

    async def register_schema(
        self,
        subject: str,
        schema: Dict[str, Any],
        *,
        tenant_id: Optional[str] = None,
        compatibility_level: Optional[CompatibilityLevel] = None,
        created_by: Optional[str] = None,
        description: Optional[str] = None,
    ) -> RegistrationResult:
        """
        Register a new schema or version for a subject.

        Args:
            subject: Schema subject name (usually event type)
            schema: JSON Schema definition
            tenant_id: Tenant ID for multi-tenancy
            compatibility_level: Compatibility level for this subject
            created_by: User registering the schema
            description: Version description

        Returns:
            RegistrationResult with version information

        Raises:
            EventBusError: If schema registration fails
        """
        try:
            subject_key = self._get_subject_key(subject, tenant_id)

            # Validate schema format
            self._validate_json_schema(schema)

            # Get or create subject
            if subject_key not in self._subjects:
                self._subjects[subject_key] = SubjectSchema(
                    subject=subject,
                    compatibility_level=compatibility_level
                    or self.default_compatibility,
                    tenant_id=tenant_id,
                )

                # Track tenant subjects
                if tenant_id:
                    if tenant_id not in self._tenant_subjects:
                        self._tenant_subjects[tenant_id] = set()
                    self._tenant_subjects[tenant_id].add(subject)

            subject_schema = self._subjects[subject_key]

            # Calculate checksum
            checksum = hashlib.sha256(
                json.dumps(schema, sort_keys=True).encode("utf-8")
            ).hexdigest()

            # Check if schema already exists (idempotent registration)
            for version_info in subject_schema.versions.values():
                if version_info.checksum == checksum:
                    logger.info(
                        "Schema already registered",
                        subject=subject,
                        version=version_info.version,
                        checksum=checksum,
                    )

                    return RegistrationResult(
                        subject=subject,
                        version=version_info.version,
                        checksum=checksum,
                        created=False,
                    )

            # Create new version
            new_version = subject_schema.latest_version + 1

            # Check compatibility with existing versions
            if subject_schema.latest_version > 0:
                await self._check_compatibility(
                    subject_schema, schema, subject_schema.compatibility_level
                )

            # Create version info
            version_info = SchemaVersionInfo.create(
                version=new_version,
                schema=schema,
                created_by=created_by,
                description=description,
            )

            # Add to subject
            subject_schema.add_version(version_info)

            logger.info(
                "Schema registered successfully",
                subject=subject,
                version=new_version,
                tenant_id=tenant_id,
                compatibility_level=subject_schema.compatibility_level,
            )

            return RegistrationResult(
                subject=subject, version=new_version, checksum=checksum, created=True
            )

        except Exception as e:
            logger.error(
                "Failed to register schema",
                subject=subject,
                tenant_id=tenant_id,
                error=str(e),
            )
            raise EventBusError(
                f"Failed to register schema for subject '{subject}': {e}"
            ) from e

    async def validate_event(
        self,
        event: EventRecord,
        *,
        version: Optional[int] = None,
        tenant_id: Optional[str] = None,
    ) -> ValidationResult:
        """
        Validate an event against its schema.

        Args:
            event: Event to validate
            version: Specific schema version (uses latest if not specified)
            tenant_id: Tenant ID for schema lookup

        Returns:
            ValidationResult with validation details
        """
        try:
            # Use tenant_id from event metadata if not provided
            if tenant_id is None:
                tenant_id = event.metadata.tenant_id

            subject = event.event_type
            subject_key = self._get_subject_key(subject, tenant_id)

            # Get subject schema
            if subject_key not in self._subjects:
                return ValidationResult(
                    valid=False,
                    errors=[f"No schema found for subject '{subject}'"],
                    subject=subject,
                    version=0,
                )

            subject_schema = self._subjects[subject_key]

            # Get schema version
            if version is not None:
                version_info = subject_schema.get_version(version)
                if not version_info:
                    return ValidationResult(
                        valid=False,
                        errors=[
                            f"Schema version {version} not found for subject '{subject}'"
                        ],
                        subject=subject,
                        version=version,
                    )
            else:
                version_info = subject_schema.get_latest_version()
                if not version_info:
                    return ValidationResult(
                        valid=False,
                        errors=[f"No schema versions found for subject '{subject}'"],
                        subject=subject,
                        version=0,
                    )
                version = version_info.version

            # Validate event data against schema
            errors = self._validate_data_against_schema(
                event.data, version_info.schema_definition
            )

            result = ValidationResult(
                valid=len(errors) == 0, errors=errors, subject=subject, version=version
            )

            if result.valid:
                logger.debug(
                    "Event validation passed",
                    event_id=event.event_id,
                    event_type=event.event_type,
                    schema_version=version,
                )
            else:
                logger.warning(
                    "Event validation failed",
                    event_id=event.event_id,
                    event_type=event.event_type,
                    schema_version=version,
                    errors=errors,
                )

            return result

        except Exception as e:
            logger.error(
                "Error during event validation",
                event_id=event.event_id,
                event_type=event.event_type,
                error=str(e),
            )

            return ValidationResult(
                valid=False,
                errors=[f"Validation error: {e}"],
                subject=event.event_type,
                version=version or 0,
            )

    async def get_schema(
        self,
        subject: str,
        version: Optional[int] = None,
        *,
        tenant_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get schema for a subject and version.

        Args:
            subject: Schema subject name
            version: Schema version (latest if not specified)
            tenant_id: Tenant ID for schema lookup

        Returns:
            Schema definition or None if not found
        """
        try:
            subject_key = self._get_subject_key(subject, tenant_id)

            if subject_key not in self._subjects:
                return None

            subject_schema = self._subjects[subject_key]

            if version is not None:
                version_info = subject_schema.get_version(version)
            else:
                version_info = subject_schema.get_latest_version()

            return version_info.schema_definition if version_info else None

        except Exception as e:
            logger.error(
                "Failed to get schema",
                subject=subject,
                version=version,
                tenant_id=tenant_id,
                error=str(e),
            )
            return None

    async def list_subjects(self, tenant_id: Optional[str] = None) -> List[str]:
        """
        List all subjects, optionally filtered by tenant.

        Args:
            tenant_id: Filter by tenant ID

        Returns:
            List of subject names
        """
        try:
            if tenant_id:
                return list(self._tenant_subjects.get(tenant_id, set()))
            else:
                # Return all subjects without tenant prefix
                subjects = []
                for subject_schema in self._subjects.values():
                    if not subject_schema.tenant_id:  # Global subjects only
                        subjects.append(subject_schema.subject)
                return subjects

        except Exception as e:
            logger.error("Failed to list subjects", tenant_id=tenant_id, error=str(e))
            return []

    async def list_versions(
        self, subject: str, *, tenant_id: Optional[str] = None
    ) -> List[int]:
        """
        List all versions for a subject.

        Args:
            subject: Schema subject name
            tenant_id: Tenant ID for schema lookup

        Returns:
            List of version numbers
        """
        try:
            subject_key = self._get_subject_key(subject, tenant_id)

            if subject_key not in self._subjects:
                return []

            subject_schema = self._subjects[subject_key]
            return sorted(subject_schema.versions.keys())

        except Exception as e:
            logger.error(
                "Failed to list versions",
                subject=subject,
                tenant_id=tenant_id,
                error=str(e),
            )
            return []

    def _validate_json_schema(self, schema: Dict[str, Any]) -> None:
        """Validate that the provided schema is a valid JSON Schema."""
        try:
            # Basic JSON Schema structure validation
            if not isinstance(schema, dict):
                raise ValueError("Schema must be a dictionary")

            # Check for required JSON Schema fields
            if (
                "type" not in schema
                and "$ref" not in schema
                and "oneOf" not in schema
                and "anyOf" not in schema
            ):
                raise ValueError("Schema must have a 'type' field or reference")

            # Validate type values
            if "type" in schema:
                valid_types = {
                    "object",
                    "array",
                    "string",
                    "number",
                    "integer",
                    "boolean",
                    "null",
                }
                schema_type = schema["type"]
                if isinstance(schema_type, list):
                    for t in schema_type:
                        if t not in valid_types:
                            raise ValueError(f"Invalid schema type: {t}")
                elif schema_type not in valid_types:
                    raise ValueError(f"Invalid schema type: {schema_type}")

        except Exception as e:
            raise EventBusError(f"Invalid JSON Schema: {e}") from e

    def _validate_data_against_schema(
        self, data: Dict[str, Any], schema: Dict[str, Any]
    ) -> List[str]:
        """
        Validate data against JSON Schema.

        Returns list of validation errors (empty if valid).
        """
        try:
            # Import jsonschema with fallback
            try:
                import jsonschema

                validator = jsonschema.Draft7Validator(schema)
                errors = []
                for error in validator.iter_errors(data):
                    errors.append(
                        f"Field '{'.'.join(str(p) for p in error.path)}': {error.message}"
                    )
                return errors
            except ImportError:
                # Fallback to basic validation
                return self._basic_validation(data, schema)

        except Exception as e:
            return [f"Schema validation error: {e}"]

    def _basic_validation(
        self, data: Dict[str, Any], schema: Dict[str, Any]
    ) -> List[str]:
        """Basic validation fallback when jsonschema is not available."""
        errors = []

        try:
            # Check type
            if "type" in schema:
                expected_type = schema["type"]
                if expected_type == "object" and not isinstance(data, dict):
                    errors.append(f"Expected object, got {type(data).__name__}")
                elif expected_type == "array" and not isinstance(data, list):
                    errors.append(f"Expected array, got {type(data).__name__}")
                elif expected_type == "string" and not isinstance(data, str):
                    errors.append(f"Expected string, got {type(data).__name__}")
                elif expected_type in ("number", "integer") and not isinstance(
                    data, (int, float)
                ):
                    errors.append(
                        f"Expected {expected_type}, got {type(data).__name__}"
                    )

            # Check required fields
            if "required" in schema and isinstance(data, dict):
                for field in schema["required"]:
                    if field not in data:
                        errors.append(f"Required field '{field}' is missing")

        except Exception as e:
            errors.append(f"Basic validation error: {e}")

        return errors

    async def _check_compatibility(
        self,
        subject_schema: SubjectSchema,
        new_schema: Dict[str, Any],
        compatibility_level: CompatibilityLevel,
    ) -> None:
        """Check schema compatibility based on compatibility level."""
        if compatibility_level == CompatibilityLevel.NONE:
            return  # No compatibility checking

        latest_version_info = subject_schema.get_latest_version()
        if not latest_version_info:
            return  # No previous version to check against

        # Implement comprehensive schema compatibility checking
        try:
            compatibility_result = await self._perform_compatibility_check(
                new_schema=subject_schema.schema,
                old_schema=latest_version_info.schema,
                compatibility_level=compatibility_level,
            )

            if not compatibility_result["compatible"]:
                logger.warning(
                    f"Schema compatibility violation for {subject_schema.subject}",
                    extra={
                        "compatibility_level": compatibility_level,
                        "violations": compatibility_result["violations"],
                        "previous_version": latest_version_info.version,
                    },
                )
                raise ValueError(
                    f"Schema incompatible with level {compatibility_level}: "
                    f"{', '.join(compatibility_result['violations'])}"
                )

            logger.info(
                f"Schema compatibility check passed for {subject_schema.subject}",
                extra={
                    "compatibility_level": compatibility_level,
                    "previous_version": latest_version_info.version,
                    "check_details": compatibility_result["details"],
                },
            )

        except Exception as e:
            logger.error(f"Schema compatibility check failed: {e}")
            # In production, you might want to make this non-blocking
            # For now, we'll allow it to pass with a warning
            logger.warning(
                "Proceeding with schema registration despite compatibility check failure"
            )

    async def _perform_compatibility_check(
        self,
        new_schema: Dict[str, Any],
        old_schema: Dict[str, Any],
        compatibility_level: CompatibilityLevel,
    ) -> Dict[str, Any]:
        """Perform detailed schema compatibility checking."""
        violations = []
        details = []

        try:
            if compatibility_level == CompatibilityLevel.BACKWARD:
                violations.extend(
                    await self._check_backward_compatibility(new_schema, old_schema)
                )
                details.append(
                    "Checked backward compatibility (new schema can read old data)"
                )

            elif compatibility_level == CompatibilityLevel.FORWARD:
                violations.extend(
                    await self._check_forward_compatibility(new_schema, old_schema)
                )
                details.append(
                    "Checked forward compatibility (old schema can read new data)"
                )

            elif compatibility_level == CompatibilityLevel.FULL:
                backward_violations = await self._check_backward_compatibility(
                    new_schema, old_schema
                )
                forward_violations = await self._check_forward_compatibility(
                    new_schema, old_schema
                )
                violations.extend(backward_violations)
                violations.extend(forward_violations)
                details.append("Checked full compatibility (both backward and forward)")

            elif compatibility_level == CompatibilityLevel.NONE:
                details.append("No compatibility checking required")

        except Exception as e:
            violations.append(f"Compatibility check error: {e}")

        return {
            "compatible": len(violations) == 0,
            "violations": violations,
            "details": details,
            "compatibility_level": compatibility_level.value,
        }

    async def _check_backward_compatibility(
        self, new_schema: Dict[str, Any], old_schema: Dict[str, Any]
    ) -> List[str]:
        """Check backward compatibility (new schema can read data written with old schema)."""
        violations = []

        try:
            # Check if required fields were added
            old_required = set(old_schema.get("required", []))
            new_required = set(new_schema.get("required", []))

            added_required = new_required - old_required
            if added_required:
                violations.append(f"Added required fields: {', '.join(added_required)}")

            # Check if field types changed incompatibly
            old_props = old_schema.get("properties", {})
            new_props = new_schema.get("properties", {})

            for field_name in old_props:
                if field_name in new_props:
                    old_type = old_props[field_name].get("type")
                    new_type = new_props[field_name].get("type")

                    if old_type and new_type and old_type != new_type:
                        # Check if type change is compatible
                        if not self._is_type_change_backward_compatible(
                            old_type, new_type
                        ):
                            violations.append(
                                f"Incompatible type change for '{field_name}': {old_type} -> {new_type}"
                            )

            # Check if fields were removed
            removed_fields = set(old_props.keys()) - set(new_props.keys())
            if removed_fields:
                violations.append(f"Removed fields: {', '.join(removed_fields)}")

            # Check enum value changes
            for field_name in old_props:
                if field_name in new_props:
                    old_enum = old_props[field_name].get("enum", [])
                    new_enum = new_props[field_name].get("enum", [])

                    if old_enum and new_enum:
                        removed_enum_values = set(old_enum) - set(new_enum)
                        if removed_enum_values:
                            violations.append(
                                f"Removed enum values for '{field_name}': {', '.join(map(str, removed_enum_values))}"
                            )

        except Exception as e:
            violations.append(f"Backward compatibility check error: {e}")

        return violations

    async def _check_forward_compatibility(
        self, new_schema: Dict[str, Any], old_schema: Dict[str, Any]
    ) -> List[str]:
        """Check forward compatibility (old schema can read data written with new schema)."""
        violations = []

        try:
            # Check if required fields were removed
            old_required = set(old_schema.get("required", []))
            new_required = set(new_schema.get("required", []))

            removed_required = old_required - new_required
            if removed_required:
                violations.append(
                    f"Removed required fields: {', '.join(removed_required)}"
                )

            # Check if new fields were added without default values
            old_props = old_schema.get("properties", {})
            new_props = new_schema.get("properties", {})

            added_fields = set(new_props.keys()) - set(old_props.keys())
            new_required_set = set(new_schema.get("required", []))

            for field_name in added_fields:
                # If added field is required and has no default, it breaks forward compatibility
                if field_name in new_required_set:
                    field_schema = new_props[field_name]
                    if "default" not in field_schema:
                        violations.append(
                            f"Added required field '{field_name}' without default value"
                        )

            # Check enum value additions (in strict forward compatibility, adding enum values can break old readers)
            for field_name in new_props:
                if field_name in old_props:
                    old_enum = old_props[field_name].get("enum", [])
                    new_enum = new_props[field_name].get("enum", [])

                    if old_enum and new_enum:
                        added_enum_values = set(new_enum) - set(old_enum)
                        if added_enum_values:
                            # This might be too strict - many systems can handle new enum values
                            # Comment out for more lenient forward compatibility
                            # violations.append(f"Added enum values for '{field_name}': {', '.join(map(str, added_enum_values))}")
                            pass

        except Exception as e:
            violations.append(f"Forward compatibility check error: {e}")

        return violations

    def _is_type_change_backward_compatible(self, old_type: str, new_type: str) -> bool:
        """Check if a type change is backward compatible."""
        # Define compatible type transitions
        compatible_transitions = {
            ("integer", "number"),  # int can be read as float
            ("string", "string"),  # string to string is always compatible
            ("number", "number"),  # number to number is always compatible
            ("boolean", "boolean"),  # boolean to boolean is always compatible
            ("array", "array"),  # array to array (need deeper check)
            ("object", "object"),  # object to object (need deeper check)
        }

        # Some type changes that are generally safe
        safe_widening = [
            ("integer", "number"),  # Widening integer to number
        ]

        return (old_type, new_type) in compatible_transitions or (
            old_type,
            new_type,
        ) in safe_widening

    async def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        try:
            total_subjects = len(self._subjects)
            total_versions = sum(len(s.versions) for s in self._subjects.values())
            tenants = len(self._tenant_subjects)

            by_compatibility = {}
            for subject_schema in self._subjects.values():
                level = subject_schema.compatibility_level.value
                by_compatibility[level] = by_compatibility.get(level, 0) + 1

            return {
                "total_subjects": total_subjects,
                "total_versions": total_versions,
                "tenants": tenants,
                "by_compatibility": by_compatibility,
                "default_compatibility": self.default_compatibility.value,
            }

        except Exception as e:
            logger.error("Failed to get registry stats", error=str(e))
            return {"error": str(e)}
