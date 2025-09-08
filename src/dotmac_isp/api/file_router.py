"""File Handling API Router for Frontend Integration.

Provides comprehensive file management including:
- File upload and validation
- Document generation (PDFs, reports)
- Data export (CSV, Excel)
- File categorization and processing
- Security validation and sanitization

Follows DRY patterns using dotmac packages for consistent API structure.
"""

import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator

from dotmac.application import standard_exception_handler
from dotmac.application.dependencies.dependencies import (
    StandardDependencies,
    get_standard_deps,
)
from dotmac.core.schemas.base_schemas import BaseResponseSchema
from dotmac.platform.observability.logging import get_logger
from dotmac_shared.api.rate_limiting_decorators import rate_limit, rate_limit_strict

from ..core.file_handlers import (
    FileUploadManager,
    PDFGenerator,
    detect_file_category,
    export_data_to_csv,
    export_data_to_excel,
    is_safe_filename,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/files", tags=["File Management"])


# ============================================================================
# Request/Response Models
# ============================================================================


class ExportRequest(BaseModel):
    """Data export request model."""

    data: list[dict]
    filename: Optional[str] = None
    columns: Optional[list[str]] = None
    format: str = "csv"  # csv, excel

    @field_validator("format")
    def validate_format(cls, v):
        if v not in ["csv", "excel"]:
            raise ValueError("Format must be 'csv' or 'excel'")
        return v

    @field_validator("filename")
    def validate_filename(cls, v):
        if v and not is_safe_filename(v):
            raise ValueError("Invalid filename")
        return v


class InvoicePDFRequest(BaseModel):
    """Invoice PDF generation request model."""

    invoice_data: dict
    template: Optional[str] = "standard"
    include_logo: bool = True

    @field_validator("template")
    def validate_template(cls, v):
        allowed_templates = ["standard", "compact", "detailed"]
        if v not in allowed_templates:
            raise ValueError(f"Template must be one of: {', '.join(allowed_templates)}")
        return v


class FileUploadResponse(BaseModel):
    """File upload response model."""

    file_id: str
    filename: str
    size: int
    content_type: str
    category: str
    upload_path: str
    secure_url: str


# ============================================================================
# File Upload Management
# ============================================================================


@router.post(
    "/upload",
    response_model=FileUploadResponse,
    summary="Upload file",
    description="Upload and process a file with validation and categorization",
)
@rate_limit(max_requests=60, time_window_seconds=60)
@standard_exception_handler
async def upload_file(
    file: UploadFile = File(...),
    category: Optional[str] = None,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> FileUploadResponse:
    """Upload and process a file with security validation."""

    # Validate filename
    if not is_safe_filename(file.filename or ""):
        from dotmac.core.exceptions import ValidationError

        raise ValidationError("Invalid filename")

    # Initialize upload manager
    upload_manager = FileUploadManager(
        tenant_id=deps.tenant_id,
        user_id=deps.user.get("user_id") if deps.user else None,
    )

    # Process upload
    upload_result = await upload_manager.upload_file(
        file=file,
        category=category or detect_file_category(file.filename or ""),
    )

    return FileUploadResponse(
        file_id=upload_result["file_id"],
        filename=upload_result["filename"],
        size=upload_result["size"],
        content_type=upload_result["content_type"],
        category=upload_result["category"],
        upload_path=upload_result["upload_path"],
        secure_url=upload_result["secure_url"],
    )


@router.get(
    "/{file_id}",
    response_class=FileResponse,
    summary="Download file",
    description="Download a previously uploaded file",
)
@rate_limit(max_requests=120, time_window_seconds=60)
@standard_exception_handler
async def download_file(
    file_id: str,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> FileResponse:
    """Download a file by ID."""

    upload_manager = FileUploadManager(
        tenant_id=deps.tenant_id,
        user_id=deps.user.get("user_id") if deps.user else None,
    )

    file_info = await upload_manager.get_file_info(file_id)

    if not file_info or not Path(file_info["file_path"]).exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_info["file_path"],
        filename=file_info["original_filename"],
        media_type=file_info["content_type"],
    )


@router.delete(
    "/{file_id}",
    response_model=dict,
    summary="Delete file",
    description="Delete a file and its metadata",
)
@rate_limit_strict(max_requests=30, time_window_seconds=60)
@standard_exception_handler
async def delete_file(
    file_id: str,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict:
    """Delete a file by ID."""

    upload_manager = FileUploadManager(
        tenant_id=deps.tenant_id,
        user_id=deps.user.get("user_id") if deps.user else None,
    )

    success = await upload_manager.delete_file(file_id)

    if not success:
        raise HTTPException(status_code=404, detail="File not found or deletion failed")

    return {"status": "success", "message": f"File {file_id} deleted successfully"}


# ============================================================================
# Document Generation
# ============================================================================


@router.post(
    "/generate/invoice-pdf",
    response_class=FileResponse,
    summary="Generate invoice PDF",
    description="Generate a PDF invoice from invoice data",
)
@rate_limit_strict(max_requests=30, time_window_seconds=60)
@standard_exception_handler
async def generate_invoice_pdf_endpoint(
    request: InvoicePDFRequest,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> FileResponse:
    """Generate a PDF invoice from structured data."""

    pdf_generator = PDFGenerator(tenant_id=deps.tenant_id, template=request.template)

    pdf_path = await pdf_generator.generate_invoice_pdf(
        invoice_data=request.invoice_data, include_logo=request.include_logo
    )

    return FileResponse(
        path=pdf_path,
        filename=f"invoice_{request.invoice_data.get('invoice_number', 'unknown')}.pdf",
        media_type="application/pdf",
    )


@router.post(
    "/generate/report-pdf",
    response_class=FileResponse,
    summary="Generate report PDF",
    description="Generate a PDF report from structured data",
)
@rate_limit_strict(max_requests=20, time_window_seconds=60)
@standard_exception_handler
async def generate_report_pdf(
    data: dict,
    template: str = "standard",
    deps: StandardDependencies = Depends(get_standard_deps),
) -> FileResponse:
    """Generate a PDF report from data."""

    pdf_generator = PDFGenerator(tenant_id=deps.tenant_id, template=template)

    pdf_path = await pdf_generator.generate_report_pdf(report_data=data, template=template)

    return FileResponse(
        path=pdf_path,
        filename=f"report_{data.get('title', 'report').replace(' ', '_')}.pdf",
        media_type="application/pdf",
    )


# ============================================================================
# Data Export
# ============================================================================


@router.post(
    "/export/csv",
    response_class=FileResponse,
    summary="Export data to CSV",
    description="Export structured data to CSV format",
)
@rate_limit(max_requests=60, time_window_seconds=60)
@standard_exception_handler
async def export_csv(
    request: ExportRequest,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> FileResponse:
    """Export data to CSV format."""

    if request.format != "csv":
        raise HTTPException(status_code=400, detail="Format must be 'csv' for this endpoint")

    csv_path = await export_data_to_csv(
        data=request.data,
        columns=request.columns,
        filename=request.filename,
        tenant_id=deps.tenant_id,
    )

    return FileResponse(
        path=csv_path,
        filename=request.filename or "export.csv",
        media_type="text/csv",
    )


@router.post(
    "/export/excel",
    response_class=FileResponse,
    summary="Export data to Excel",
    description="Export structured data to Excel format",
)
@rate_limit(max_requests=60, time_window_seconds=60)
@standard_exception_handler
async def export_excel(
    request: ExportRequest,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> FileResponse:
    """Export data to Excel format."""

    if request.format != "excel":
        raise HTTPException(status_code=400, detail="Format must be 'excel' for this endpoint")

    excel_path = await export_data_to_excel(
        data=request.data,
        columns=request.columns,
        filename=request.filename,
        tenant_id=deps.tenant_id,
    )

    return FileResponse(
        path=excel_path,
        filename=request.filename or "export.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ============================================================================
# File Management & Information
# ============================================================================


@router.get(
    "/list",
    response_model=BaseResponseSchema,
    summary="List uploaded files",
    description="Get a list of uploaded files for the current tenant",
)
@rate_limit(max_requests=120, time_window_seconds=60)
@standard_exception_handler
async def list_files(
    category: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> BaseResponseSchema:
    """List uploaded files with optional filtering."""

    upload_manager = FileUploadManager(
        tenant_id=deps.tenant_id,
        user_id=deps.user.get("user_id") if deps.user else None,
    )

    files = await upload_manager.list_files(category=category, limit=limit, offset=offset)

    return BaseResponseSchema(success=True, message=f"Retrieved {len(files)} files", data=files)


@router.get(
    "/info/{file_id}",
    response_model=dict,
    summary="Get file information",
    description="Get detailed information about a specific file",
)
@rate_limit(max_requests=120, time_window_seconds=60)
@standard_exception_handler
async def get_file_info(
    file_id: str,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict:
    """Get detailed information about a file."""

    upload_manager = FileUploadManager(
        tenant_id=deps.tenant_id,
        user_id=deps.user.get("user_id") if deps.user else None,
    )

    file_info = await upload_manager.get_file_info(file_id)

    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")

    return file_info


# ============================================================================
# Health & Status
# ============================================================================


@router.get(
    "/health",
    response_model=dict,
    summary="Check file service health",
    description="Check the health status of file handling services",
)
@standard_exception_handler
async def check_file_service_health(
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict:
    """Check file handler service health."""

    # Check upload directory access - use secure temp directory
    import tempfile
    upload_dir = Path(tempfile.gettempdir()) / "uploads" / deps.tenant_id
    upload_dir.mkdir(parents=True, exist_ok=True, mode=0o700)  # Secure permissions

    # Basic health checks
    health_status = {
        "status": "healthy",
        "upload_directory_writable": os.access(upload_dir, os.W_OK),
        "pdf_generation_available": True,  # Would check PDF libraries
        "export_functions_available": True,  # Would check export libraries
    }

    overall_healthy = all(
        [
            health_status["upload_directory_writable"],
            health_status["pdf_generation_available"],
            health_status["export_functions_available"],
        ]
    )

    health_status["status"] = "healthy" if overall_healthy else "degraded"

    return health_status
