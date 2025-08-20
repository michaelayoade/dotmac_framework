"""
Schema Registry API endpoints for dotmac_core_events.

Provides REST API for:
- Schema registration and retrieval
- Schema validation
- Compatibility checking
- Version management
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..core.dependencies import get_schema_registry, get_tenant_id
from ..sdks.schema_registry import CompatibilityLevel, SchemaRegistrySDK


class RegisterSchemaRequest(BaseModel):
    """Request model for schema registration."""

    version: str = Field(..., description="Schema version")
    schema: Dict[str, Any] = Field(..., description="JSON schema definition")
    compatibility_level: str = Field("BACKWARD", description="Compatibility level")


class RegisterSchemaResponse(BaseModel):
    """Response model for schema registration."""

    schema_id: str = Field(..., description="Generated schema ID")
    event_type: str = Field(..., description="Event type")
    version: str = Field(..., description="Schema version")
    compatibility_level: str = Field(..., description="Compatibility level")


class SchemaResponse(BaseModel):
    """Response model for schema retrieval."""

    event_type: str = Field(..., description="Event type")
    version: str = Field(..., description="Schema version")
    schema: Dict[str, Any] = Field(..., description="JSON schema definition")
    compatibility_level: str = Field(..., description="Compatibility level")
    created_at: str = Field(..., description="Creation timestamp")
    created_by: Optional[str] = Field(None, description="Creator")


class ValidateDataRequest(BaseModel):
    """Request model for data validation."""

    data: Dict[str, Any] = Field(..., description="Data to validate")
    version: Optional[str] = Field(None, description="Schema version")


class ValidateDataResponse(BaseModel):
    """Response model for data validation."""

    valid: bool = Field(..., description="Whether validation passed")
    errors: List[Dict[str, Any]] = Field(..., description="Validation errors")
    schema_version: Optional[str] = Field(None, description="Schema version used")


class CompatibilityRequest(BaseModel):
    """Request model for compatibility checking."""

    schema: Dict[str, Any] = Field(..., description="Schema to check")
    version: Optional[str] = Field(None, description="Version to check against")


class CompatibilityResponse(BaseModel):
    """Response model for compatibility checking."""

    compatible: bool = Field(..., description="Whether schemas are compatible")
    compatibility_level: Optional[str] = Field(None, description="Compatibility level")
    compared_version: Optional[str] = Field(None, description="Compared version")
    message: Optional[str] = Field(None, description="Compatibility message")


class SchemaVersionsResponse(BaseModel):
    """Response model for schema versions."""

    event_type: str = Field(..., description="Event type")
    versions: List[str] = Field(..., description="Available versions")


class EventTypesResponse(BaseModel):
    """Response model for event types."""

    event_types: List[str] = Field(..., description="Event types with schemas")


class SchemasAPI:
    """Schema Registry API endpoints."""

    def __init__(self):
        self.router = APIRouter(prefix="/schemas", tags=["schemas"])
        self._setup_routes()

    def _setup_routes(self):  # noqa: PLR0915, C901
        """Set up API routes."""

        @self.router.post(
            "/{event_type}",
            response_model=RegisterSchemaResponse,
            status_code=status.HTTP_201_CREATED,
            summary="Register schema",
            description="Register a new schema version"
        )
        async def register_schema(
            event_type: str,
            request: RegisterSchemaRequest,
            schema_registry: SchemaRegistrySDK = Depends(get_schema_registry),
            tenant_id: str = Depends(get_tenant_id)
        ) -> RegisterSchemaResponse:
            """Register a new schema version."""
            if not schema_registry:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Schema registry not available"
                )

            try:
                # Parse compatibility level
                try:
                    compatibility_level = CompatibilityLevel(request.compatibility_level)
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid compatibility level: {request.compatibility_level}"
                    )

                result = await schema_registry.register_schema(
                    event_type=event_type,
                    version=request.version,
                    schema=request.schema,
                    compatibility_level=compatibility_level,
                )

                return RegisterSchemaResponse(
                    schema_id=result.schema_id,
                    event_type=result.event_type,
                    version=result.version,
                    compatibility_level=result.compatibility_level.value,
                )

            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to register schema: {str(e)}"
                )

        @self.router.get(
            "/{event_type}",
            response_model=SchemaResponse,
            summary="Get schema",
            description="Get latest schema for event type"
        )
        async def get_schema(
            event_type: str,
            schema_registry: SchemaRegistrySDK = Depends(get_schema_registry),
            tenant_id: str = Depends(get_tenant_id)
        ) -> SchemaResponse:
            """Get latest schema for event type."""
            if not schema_registry:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Schema registry not available"
                )

            try:
                schema_version = await schema_registry.get_schema(event_type)

                if not schema_version:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Schema not found for event type: {event_type}"
                    )

                return SchemaResponse(
                    event_type=schema_version.event_type,
                    version=schema_version.version,
                    schema=schema_version.schema,
                    compatibility_level=schema_version.compatibility_level.value,
                    created_at=schema_version.created_at.isoformat(),
                    created_by=schema_version.created_by,
                )

            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to get schema: {str(e)}"
                )

        @self.router.get(
            "/{event_type}/{version}",
            response_model=SchemaResponse,
            summary="Get schema version",
            description="Get specific schema version"
        )
        async def get_schema_version(
            event_type: str,
            version: str,
            schema_registry: SchemaRegistrySDK = Depends(get_schema_registry),
            tenant_id: str = Depends(get_tenant_id)
        ) -> SchemaResponse:
            """Get specific schema version."""
            if not schema_registry:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Schema registry not available"
                )

            try:
                schema_version = await schema_registry.get_schema(event_type, version)

                if not schema_version:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Schema version {version} not found for event type: {event_type}"
                    )

                return SchemaResponse(
                    event_type=schema_version.event_type,
                    version=schema_version.version,
                    schema=schema_version.schema,
                    compatibility_level=schema_version.compatibility_level.value,
                    created_at=schema_version.created_at.isoformat(),
                    created_by=schema_version.created_by,
                )

            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to get schema version: {str(e)}"
                )

        @self.router.get(
            "/{event_type}/versions",
            response_model=SchemaVersionsResponse,
            summary="List schema versions",
            description="List all versions for event type"
        )
        async def list_schema_versions(
            event_type: str,
            schema_registry: SchemaRegistrySDK = Depends(get_schema_registry),
            tenant_id: str = Depends(get_tenant_id)
        ) -> SchemaVersionsResponse:
            """List all versions for event type."""
            if not schema_registry:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Schema registry not available"
                )

            try:
                versions = await schema_registry.list_versions(event_type)

                return SchemaVersionsResponse(
                    event_type=event_type,
                    versions=versions,
                )

            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to list schema versions: {str(e)}"
                )

        @self.router.post(
            "/{event_type}/validate",
            response_model=ValidateDataResponse,
            summary="Validate data",
            description="Validate data against schema"
        )
        async def validate_data(
            event_type: str,
            request: ValidateDataRequest,
            schema_registry: SchemaRegistrySDK = Depends(get_schema_registry),
            tenant_id: str = Depends(get_tenant_id)
        ) -> ValidateDataResponse:
            """Validate data against schema."""
            if not schema_registry:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Schema registry not available"
                )

            try:
                result = await schema_registry.validate_data(
                    event_type=event_type,
                    data=request.data,
                    version=request.version,
                )

                return ValidateDataResponse(
                    valid=result.valid,
                    errors=result.errors,
                    schema_version=result.schema_version,
                )

            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to validate data: {str(e)}"
                )

        @self.router.post(
            "/{event_type}/compatibility",
            response_model=CompatibilityResponse,
            summary="Check compatibility",
            description="Check schema compatibility"
        )
        async def check_compatibility(
            event_type: str,
            request: CompatibilityRequest,
            schema_registry: SchemaRegistrySDK = Depends(get_schema_registry),
            tenant_id: str = Depends(get_tenant_id)
        ) -> CompatibilityResponse:
            """Check schema compatibility."""
            if not schema_registry:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Schema registry not available"
                )

            try:
                result = await schema_registry.check_compatibility(
                    event_type=event_type,
                    schema=request.schema,
                    version=request.version,
                )

                return CompatibilityResponse(
                    compatible=result.get("compatible", False),
                    compatibility_level=result.get("compatibility_level"),
                    compared_version=result.get("compared_version"),
                    message=result.get("message"),
                )

            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to check compatibility: {str(e)}"
                )

        @self.router.delete(
            "/{event_type}",
            status_code=status.HTTP_204_NO_CONTENT,
            summary="Delete all schema versions",
            description="Delete all versions for event type"
        )
        async def delete_all_schema_versions(
            event_type: str,
            schema_registry: SchemaRegistrySDK = Depends(get_schema_registry),
            tenant_id: str = Depends(get_tenant_id)
        ):
            """Delete all schema versions for event type."""
            if not schema_registry:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Schema registry not available"
                )

            try:
                await schema_registry.delete_schema(event_type)

            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to delete schema: {str(e)}"
                )

        @self.router.delete(
            "/{event_type}/{version}",
            status_code=status.HTTP_204_NO_CONTENT,
            summary="Delete schema version",
            description="Delete specific schema version"
        )
        async def delete_schema_version(
            event_type: str,
            version: str,
            schema_registry: SchemaRegistrySDK = Depends(get_schema_registry),
            tenant_id: str = Depends(get_tenant_id)
        ):
            """Delete specific schema version."""
            if not schema_registry:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Schema registry not available"
                )

            try:
                await schema_registry.delete_schema(event_type, version)

            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to delete schema version: {str(e)}"
                )

        @self.router.get(
            "/",
            response_model=EventTypesResponse,
            summary="List event types",
            description="List all event types with schemas"
        )
        async def list_event_types(
            schema_registry: SchemaRegistrySDK = Depends(get_schema_registry),
            tenant_id: str = Depends(get_tenant_id)
        ) -> EventTypesResponse:
            """List all event types with schemas."""
            if not schema_registry:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Schema registry not available"
                )

            try:
                event_types = await schema_registry.list_event_types()

                return EventTypesResponse(
                    event_types=event_types,
                )

            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to list event types: {str(e)}"
                )
