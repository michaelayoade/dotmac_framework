"""File Management API Router for the Management Platform.

Provides comprehensive file management for the management platform including:
- Secure file upload and validation
- File metadata management
- Access control and permissions
- Search and filtering capabilities
- Tenant-isolated file storage

Follows DRY patterns using dotmac packages for consistent API structure.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Path, Query, UploadFile
from fastapi.responses import FileResponse

from dotmac.application import standard_exception_handler
from dotmac.application.api.router_factory import RouterFactory
from dotmac.application.dependencies.dependencies import (
    StandardDependencies,
    get_standard_deps,
)
from dotmac.core.schemas.base_schemas import PaginatedResponseSchema
from dotmac.platform.observability.logging import get_logger
from dotmac_shared.api.rate_limiting_decorators import rate_limit, rate_limit_strict
from dotmac_shared.file_management.schemas import (
    FileMetadataCreate,
    FileMetadataResponse,
    FileMetadataUpdate,
    FileSearchFilters,
    FileSearchRequest,
    FileUploadSessionCreate,
    FileValidationRequest,
    FileValidationResponse,
    TenantFileStatsResponse,
)

from ...services.file_service import FileService

logger = get_logger(__name__)

# Create router using DRY RouterFactory pattern
router_factory = RouterFactory("File Management")
router = APIRouter(prefix="/files", tags=["File Management"])


# ============================================================================
# File Upload Management
# ============================================================================


@router.post(
    "/upload",
    response_model=FileMetadataResponse,
    summary="Upload file",
    description="Upload a new file with metadata and validation",
)
@rate_limit_strict(max_requests=20, time_window_seconds=60)
@standard_exception_handler
async def upload_file(
    file: UploadFile = File(...),
    category: Optional[str] = Query(None, description="File category"),
    description: Optional[str] = Query(None, description="File description"),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    access_level: Optional[str] = Query("private", description="Access level (private, shared, public)"),
    expiration_days: Optional[int] = Query(None, description="Days until expiration"),
    related_entity_type: Optional[str] = Query(None, description="Related entity type"),
    related_entity_id: Optional[str] = Query(None, description="Related entity ID"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> FileMetadataResponse:
    """Upload a new file with comprehensive metadata and validation."""

    file_service = FileService(deps.db, deps.tenant_id)

    # Create upload request
    upload_request = FileMetadataCreate(
        filename=file.filename,
        content_type=file.content_type,
        category=category,
        description=description,
        tags=tags.split(",") if tags else [],
        access_level=access_level,
        expiration_days=expiration_days,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
    )

    # Process upload
    file_content = await file.read()
    uploaded_file = await file_service.upload_file(
        file_content=file_content,
        metadata=upload_request,
        user_id=deps.user.get("user_id") if deps.user else None,
    )

    return uploaded_file


@router.post(
    "/upload/session",
    response_model=dict,
    summary="Create upload session",
    description="Create a secure upload session for large files",
)
@rate_limit_strict(max_requests=10, time_window_seconds=60)
@standard_exception_handler
async def create_upload_session(
    request: FileUploadSessionCreate,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict:
    """Create a secure upload session for large files."""

    file_service = FileService(deps.db, deps.tenant_id)

    session = await file_service.create_upload_session(
        request=request,
        user_id=deps.user.get("user_id") if deps.user else None,
    )

    return {
        "success": True,
        "message": "Upload session created",
        "data": session,
    }


# ============================================================================
# File Access & Download
# ============================================================================


@router.get(
    "/{file_id}",
    response_class=FileResponse,
    summary="Download file",
    description="Download a file by ID",
)
@rate_limit(max_requests=120, time_window_seconds=60)
@standard_exception_handler
async def download_file(
    file_id: UUID = Path(..., description="File ID"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> FileResponse:
    """Download a file by ID."""

    file_service = FileService(deps.db, deps.tenant_id)

    file_info = await file_service.get_file_for_download(
        file_id=file_id,
        user_id=deps.user.get("user_id") if deps.user else None,
    )

    return FileResponse(
        path=file_info["file_path"],
        filename=file_info["filename"],
        media_type=file_info["content_type"],
    )


@router.get(
    "/{file_id}/metadata",
    response_model=FileMetadataResponse,
    summary="Get file metadata",
    description="Get metadata for a specific file",
)
@rate_limit(max_requests=180, time_window_seconds=60)
@standard_exception_handler
async def get_file_metadata(
    file_id: UUID = Path(..., description="File ID"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> FileMetadataResponse:
    """Get metadata for a specific file."""

    file_service = FileService(deps.db, deps.tenant_id)

    metadata = await file_service.get_file_metadata(
        file_id=file_id,
        user_id=deps.user.get("user_id") if deps.user else None,
    )

    return metadata


# ============================================================================
# File Management Operations
# ============================================================================


@router.put(
    "/{file_id}/metadata",
    response_model=FileMetadataResponse,
    summary="Update file metadata",
    description="Update metadata for a specific file",
)
@rate_limit_strict(max_requests=60, time_window_seconds=60)
@standard_exception_handler
async def update_file_metadata(
    request: FileMetadataUpdate,
    file_id: UUID = Path(..., description="File ID"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> FileMetadataResponse:
    """Update metadata for a specific file."""

    file_service = FileService(deps.db, deps.tenant_id)

    updated_file = await file_service.update_file_metadata(
        file_id=file_id,
        updates=request,
        user_id=deps.user.get("user_id") if deps.user else None,
    )

    return updated_file


@router.delete(
    "/{file_id}",
    response_model=dict,
    summary="Delete file",
    description="Delete a file and its metadata",
)
@rate_limit_strict(max_requests=30, time_window_seconds=60)
@standard_exception_handler
async def delete_file(
    file_id: UUID = Path(..., description="File ID"),
    force: bool = Query(False, description="Force delete even if referenced"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict:
    """Delete a file and its metadata."""

    file_service = FileService(deps.db, deps.tenant_id)

    success = await file_service.delete_file(
        file_id=file_id,
        user_id=deps.user.get("user_id") if deps.user else None,
        force=force,
    )

    if not success:
        from dotmac.core.exceptions import BusinessRuleError

        raise BusinessRuleError("File cannot be deleted (may be referenced by other entities)")

    return {
        "success": True,
        "message": f"File {file_id} deleted successfully",
    }


# ============================================================================
# File Search & Listing
# ============================================================================


@router.get(
    "",
    response_model=PaginatedResponseSchema[FileMetadataResponse],
    summary="List files",
    description="List files with filtering and pagination",
)
@rate_limit(max_requests=120, time_window_seconds=60)
@standard_exception_handler
async def list_files(
    category: Optional[str] = Query(None, description="Filter by category"),
    access_level: Optional[str] = Query(None, description="Filter by access level"),
    tags: Optional[str] = Query(None, description="Filter by comma-separated tags"),
    search: Optional[str] = Query(None, description="Search term"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> PaginatedResponseSchema[FileMetadataResponse]:
    """List files with filtering and pagination."""

    file_service = FileService(deps.db, deps.tenant_id)

    # Build search filters
    filters = FileSearchFilters(
        category=category,
        access_level=access_level,
        tags=tags.split(",") if tags else None,
        search_term=search,
    )

    files = await file_service.list_files(
        filters=filters,
        user_id=deps.user.get("user_id") if deps.user else None,
        limit=50,  # Default pagination
        offset=0,
    )

    return PaginatedResponseSchema[FileMetadataResponse](
        items=files,
        total=len(files),
        page=1,
        per_page=50,
    )


@router.post(
    "/search",
    response_model=PaginatedResponseSchema[FileMetadataResponse],
    summary="Advanced file search",
    description="Perform advanced search with complex filters",
)
@rate_limit(max_requests=60, time_window_seconds=60)
@standard_exception_handler
async def search_files(
    request: FileSearchRequest,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> PaginatedResponseSchema[FileMetadataResponse]:
    """Perform advanced search with complex filters."""

    file_service = FileService(deps.db, deps.tenant_id)

    results = await file_service.advanced_search(
        search_request=request,
        user_id=deps.user.get("user_id") if deps.user else None,
    )

    return PaginatedResponseSchema[FileMetadataResponse](
        items=results["items"],
        total=results["total"],
        page=request.page,
        per_page=request.per_page,
    )


# ============================================================================
# File Validation & Security
# ============================================================================


@router.post(
    "/validate",
    response_model=FileValidationResponse,
    summary="Validate file",
    description="Validate file content and security",
)
@rate_limit_strict(max_requests=30, time_window_seconds=60)
@standard_exception_handler
async def validate_file(
    request: FileValidationRequest,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> FileValidationResponse:
    """Validate file content and security."""

    file_service = FileService(deps.db, deps.tenant_id)

    validation_result = await file_service.validate_file(
        validation_request=request,
        user_id=deps.user.get("user_id") if deps.user else None,
    )

    return validation_result


# ============================================================================
# Tenant File Statistics
# ============================================================================


@router.get(
    "/stats/tenant",
    response_model=TenantFileStatsResponse,
    summary="Get tenant file statistics",
    description="Get file usage statistics for the current tenant",
)
@rate_limit(max_requests=60, time_window_seconds=60)
@standard_exception_handler
async def get_tenant_file_stats(
    deps: StandardDependencies = Depends(get_standard_deps),
) -> TenantFileStatsResponse:
    """Get file usage statistics for the current tenant."""

    file_service = FileService(deps.db, deps.tenant_id)

    stats = await file_service.get_tenant_file_stats(deps.tenant_id)

    return stats
