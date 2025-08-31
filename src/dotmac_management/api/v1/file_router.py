"""File Management API Router for the Management Platform."""

import logging
from typing import List, Optional

from fastapi import Depends, File, Query, UploadFile
from fastapi.responses import StreamingResponse

from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.api.rate_limiting_decorators import rate_limit, rate_limit_strict
from dotmac_shared.api.router_factory import RouterFactory
from dotmac_shared.file_management.schemas import (
    FileListResponse,
    FileMetadataCreate,
    FileMetadataResponse,
    FileMetadataUpdate,
    FilePermissionCreate,
    FileSearchFilters,
    FileSearchRequest,
    FileUploadSessionCreate,
    FileValidationRequest,
    FileValidationResponse,
    TenantFileStatsResponse,
)

from ...dependencies import get_current_user, get_file_service
from ...services.file_service import FileService

logger = logging.getLogger(__name__)

# Create router using RouterFactory
router = RouterFactory.create_router(
    prefix="/files",
    tags=["File Management"],
    dependencies=[Depends(get_current_user)]
)


# File Upload Endpoints

@router.post("/upload", response_model=FileMetadataResponse)
@rate_limit_strict(max_requests=20, time_window_seconds=60)
@standard_exception_handler
async def upload_file(
    file: UploadFile = File(...),
    category: Optional[str] = Query(None, description="File category"),
    description: Optional[str] = Query(None, description="File description"),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    access_level: Optional[str] = Query("tenant_only", description="Access level"),
    expiration_days: Optional[int] = Query(None, description="Expiration in days"),
    related_entity_type: Optional[str] = Query(None, description="Related entity type"),
    related_entity_id: Optional[str] = Query(None, description="Related entity ID"),
    current_user: dict = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service)
):
    """Upload a new file."""
    # Read file content
    file_content = await file.read()
    
    # Parse tags
    tag_list = []
    if tags:
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
    
    # Create file metadata request
    file_data = FileMetadataCreate(
        tenant_id=current_user["tenant_id"],
        owner_user_id=current_user["user_id"],
        original_filename=file.filename,
        file_category=category or "other",
        access_level=access_level,
        description=description,
        tags=tag_list,
        expiration_days=expiration_days,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id
    )
    
    return await file_service.create_file(
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        file_data=file_data,
        file_content=file_content
    )


@router.post("/upload/session", response_model=dict)
@rate_limit_strict(max_requests=10, time_window_seconds=60)
@standard_exception_handler
async def create_upload_session(
    session_data: FileUploadSessionCreate,
    current_user: dict = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service)
):
    """Create upload session for large files."""
    session = await file_service.create_upload_session(
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        session_data=session_data
    )
    
    return {
        "upload_session_id": session.upload_session_id,
        "expires_at": session.expires_at,
        "chunk_size": session.chunk_size,
        "max_chunks": session.max_chunks
    }


# File Access Endpoints

@router.get("/{file_id}", response_model=FileMetadataResponse)
@rate_limit(max_requests=100, time_window_seconds=60)
@standard_exception_handler
async def get_file(
    file_id: str,
    current_user: dict = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service)
):
    """Get file metadata by ID."""
    return await file_service.get_file(
        file_id=file_id,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"]
    )


@router.get("/{file_id}/download")
@rate_limit(max_requests=50, time_window_seconds=60)
@standard_exception_handler
async def download_file(
    file_id: str,
    current_user: dict = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service)
):
    """Download file content."""
    content, filename, mime_type = await file_service.get_file_content(
        file_id=file_id,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"]
    )
    
    def generate_file_stream():
        yield content
    
    return StreamingResponse(
        generate_file_stream(),
        media_type=mime_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Length": str(len(content))
        }
    )


@router.put("/{file_id}", response_model=FileMetadataResponse)
@rate_limit(max_requests=50, time_window_seconds=60)
@standard_exception_handler
async def update_file(
    file_id: str,
    updates: FileMetadataUpdate,
    current_user: dict = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service)
):
    """Update file metadata."""
    return await file_service.update_file(
        file_id=file_id,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        updates=updates
    )


@router.delete("/{file_id}")
@rate_limit_strict(max_requests=20, time_window_seconds=60)
@standard_exception_handler
async def delete_file(
    file_id: str,
    permanent: bool = Query(False, description="Permanent deletion"),
    current_user: dict = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service)
):
    """Delete file."""
    success = await file_service.delete_file(
        file_id=file_id,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        permanent=permanent
    )
    
    return {"success": success, "message": "File deleted successfully"}


# File Search and Listing

@router.post("/search", response_model=FileListResponse)
@rate_limit(max_requests=100, time_window_seconds=60)
@standard_exception_handler
async def search_files(
    search_request: FileSearchRequest,
    current_user: dict = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service)
):
    """Search files with advanced filters."""
    files, total = await file_service.search_files(
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        search_filters=search_request.filters or FileSearchFilters(),
        page=search_request.page,
        size=search_request.size
    )
    
    return FileListResponse(
        items=files,
        total=total,
        page=search_request.page,
        size=search_request.size,
        pages=(total + search_request.size - 1) // search_request.size
    )


@router.get("/", response_model=FileListResponse)
@rate_limit(max_requests=100, time_window_seconds=60)
@standard_exception_handler
async def list_user_files(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size"),
    current_user: dict = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service)
):
    """List current user's files."""
    files, total = await file_service.get_user_files(
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        page=page,
        size=size
    )
    
    return FileListResponse(
        items=files,
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size
    )


# File Permissions

@router.post("/{file_id}/permissions")
@rate_limit_strict(max_requests=30, time_window_seconds=60)
@standard_exception_handler
async def grant_file_permission(
    file_id: str,
    permission_data: FilePermissionCreate,
    current_user: dict = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service)
):
    """Grant file permission to another user."""
    success = await file_service.grant_file_permission(
        file_id=file_id,
        tenant_id=current_user["tenant_id"],
        granter_user_id=current_user["user_id"],
        permission_data=permission_data
    )
    
    return {"success": success, "message": "Permission granted successfully"}


# File Validation

@router.post("/validate", response_model=FileValidationResponse)
@rate_limit(max_requests=100, time_window_seconds=60)
@standard_exception_handler
async def validate_file(
    validation_request: FileValidationRequest,
    file_service: FileService = Depends(get_file_service)
):
    """Validate file before upload."""
    return await file_service.validate_file(
        filename=validation_request.filename,
        file_size=validation_request.file_size,
        content_type=validation_request.content_type,
        category=validation_request.category
    )


# Statistics and Analytics

@router.get("/stats/tenant", response_model=TenantFileStatsResponse)
@rate_limit(max_requests=20, time_window_seconds=60)
@standard_exception_handler
async def get_tenant_file_stats(
    current_user: dict = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service)
):
    """Get file statistics for current tenant."""
    stats = await file_service.get_tenant_file_stats(current_user["tenant_id"])
    
    return TenantFileStatsResponse(
        tenant_id=current_user["tenant_id"],
        **stats
    )


# Health Check

@router.get("/health")
@standard_exception_handler
async def file_service_health():
    """Check file service health."""
    return {
        "status": "healthy",
        "service": "file_management",
        "timestamp": datetime.utcnow().isoformat()
    }