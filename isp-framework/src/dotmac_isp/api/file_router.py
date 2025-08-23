"""File Handling API Router for Frontend Integration."""

import logging
import os
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
import aiofiles

from ..core.file_handlers import (
    FileUploadManager, PDFGenerator, CSVExporter,
    generate_invoice_pdf, export_data_to_csv, export_data_to_excel,
    detect_file_category, is_safe_filename
)
from ..shared.auth import get_current_user
from ..shared.database.base import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic models for API requests

class ExportRequest(BaseModel):
    """Data export request model."""
    data: List[dict]
    filename: Optional[str] = None
    columns: Optional[List[str]] = None
    format: str = "csv"  # csv, excel


class InvoicePDFRequest(BaseModel):
    """Invoice PDF generation request model."""
    invoice_data: dict
    filename: Optional[str] = None


class FileMetadataResponse(BaseModel):
    """File metadata response model."""
    file_id: str
    original_name: str
    mime_type: str
    size_bytes: int
    uploaded_at: str
    category: Optional[str]
    tags: List[str]
    download_url: str


# File upload endpoints

@router.post("/upload", response_model=FileMetadataResponse)
async def upload_file(
    file: UploadFile = File(...),
    category: Optional[str] = Query(None, description="File category (images, documents, spreadsheets, archives)"),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    current_user=Depends(get_current_user)
):
    """
    Upload a file.
    
    Args:
        file: File to upload
        category: File category for validation
        tags: Comma-separated tags
        
    Returns:
        File metadata
    """
    try:
        # Validate filename
        if not is_safe_filename(file.filename):
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        # Auto-detect category if not provided
        if not category:
            category = detect_file_category(file.filename)
        
        # Parse tags
        tag_list = []
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        
        # Initialize upload manager
        upload_manager = FileUploadManager()
        
        # Upload file
        metadata = await upload_manager.upload_file(
            file=file,
            tenant_id=current_user["tenant_id"],
            user_id=current_user["user_id"],
            category=category,
            tags=tag_list
        )
        
        # Generate download URL
        download_url = f"/api/files/{metadata.file_id}"
        
        return FileMetadataResponse(
            file_id=metadata.file_id,
            original_name=metadata.original_name,
            mime_type=metadata.mime_type,
            size_bytes=metadata.size_bytes,
            uploaded_at=metadata.uploaded_at.isoformat(),
            category=metadata.category,
            tags=metadata.tags,
            download_url=download_url
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/upload/multiple", response_model=List[FileMetadataResponse])
async def upload_multiple_files(
    files: List[UploadFile] = File(...),
    category: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),
    current_user=Depends(get_current_user)
):
    """
    Upload multiple files.
    
    Args:
        files: Files to upload
        category: File category for validation
        tags: Comma-separated tags
        
    Returns:
        List of file metadata
    """
    try:
        upload_manager = FileUploadManager()
        tag_list = []
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        
        results = []
        
        for file in files:
            # Validate filename
            if not is_safe_filename(file.filename):
                logger.warning(f"Skipping file with invalid name: {file.filename}")
                continue
            
            # Auto-detect category if not provided
            file_category = category or detect_file_category(file.filename)
            
            try:
                metadata = await upload_manager.upload_file(
                    file=file,
                    tenant_id=current_user["tenant_id"],
                    user_id=current_user["user_id"],
                    category=file_category,
                    tags=tag_list
                )
                
                download_url = f"/api/files/{metadata.file_id}"
                
                results.append(FileMetadataResponse(
                    file_id=metadata.file_id,
                    original_name=metadata.original_name,
                    mime_type=metadata.mime_type,
                    size_bytes=metadata.size_bytes,
                    uploaded_at=metadata.uploaded_at.isoformat(),
                    category=metadata.category,
                    tags=metadata.tags,
                    download_url=download_url
                ))
                
            except Exception as e:
                logger.error(f"Failed to upload {file.filename}: {e}")
                # Continue with other files
        
        return results
        
    except Exception as e:
        logger.error(f"Multiple file upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# File download endpoints

@router.get("/files/{file_id}")
async def download_file(
    file_id: str,
    current_user=Depends(get_current_user)
):
    """
    Download a file by ID.
    
    Args:
        file_id: File ID
        
    Returns:
        File content
    """
    try:
        # In a real implementation, you would:
        # 1. Look up file metadata from database
        # 2. Verify user has permission to access the file
        # 3. Return the file from storage
        
        # For now, we'll check if file exists in upload directory
        upload_manager = FileUploadManager()
        tenant_id = current_user["tenant_id"]
        
        # Find file in tenant directory
        tenant_dir = Path(upload_manager.upload_directory) / tenant_id
        
        # Search for file with matching ID
        matching_files = list(tenant_dir.glob(f"{file_id}.*"))
        
        if not matching_files:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_path = matching_files[0]
        
        # Determine appropriate headers
        filename = file_path.name
        
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File download failed for {file_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


# PDF generation endpoints

@router.post("/generate/invoice-pdf")
async def generate_invoice_pdf_endpoint(
    request: InvoicePDFRequest,
    current_user=Depends(get_current_user)
):
    """
    Generate invoice PDF.
    
    Args:
        request: Invoice PDF generation request
        
    Returns:
        PDF file
    """
    try:
        # Generate PDF
        pdf_path = await generate_invoice_pdf(request.invoice_data)
        
        # Determine filename
        filename = request.filename
        if not filename:
            invoice_number = request.invoice_data.get('invoice_number', 'invoice')
            filename = f"invoice_{invoice_number}.pdf"
        
        # Return PDF file
        return FileResponse(
            path=pdf_path,
            filename=filename,
            media_type='application/pdf'
        )
        
    except Exception as e:
        logger.error(f"Invoice PDF generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


@router.post("/generate/report-pdf")
async def generate_report_pdf_endpoint(
    report_data: dict,
    filename: Optional[str] = Query(None),
    current_user=Depends(get_current_user)
):
    """
    Generate report PDF.
    
    Args:
        report_data: Report data
        filename: Output filename (optional)
        
    Returns:
        PDF file
    """
    try:
        # Generate PDF
        pdf_generator = PDFGenerator()
        pdf_path = pdf_generator.generate_report_pdf(report_data)
        
        # Determine filename
        if not filename:
            report_title = report_data.get('title', 'report').replace(' ', '_').lower()
            filename = f"{report_title}.pdf"
        
        # Return PDF file
        return FileResponse(
            path=pdf_path,
            filename=filename,
            media_type='application/pdf'
        )
        
    except Exception as e:
        logger.error(f"Report PDF generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


# Data export endpoints

@router.post("/export/csv")
async def export_csv_endpoint(
    request: ExportRequest,
    current_user=Depends(get_current_user)
):
    """
    Export data to CSV.
    
    Args:
        request: Export request
        
    Returns:
        CSV file
    """
    try:
        # Export to CSV
        csv_path = await export_data_to_csv(request.data, request.columns)
        
        # Determine filename
        filename = request.filename or "export.csv"
        if not filename.endswith('.csv'):
            filename += '.csv'
        
        # Return CSV file
        return FileResponse(
            path=csv_path,
            filename=filename,
            media_type='text/csv'
        )
        
    except Exception as e:
        logger.error(f"CSV export failed: {e}")
        raise HTTPException(status_code=500, detail=f"CSV export failed: {str(e)}")


@router.post("/export/excel")
async def export_excel_endpoint(
    request: ExportRequest,
    current_user=Depends(get_current_user)
):
    """
    Export data to Excel.
    
    Args:
        request: Export request
        
    Returns:
        Excel file
    """
    try:
        # Export to Excel
        excel_path = await export_data_to_excel(request.data, request.columns)
        
        # Determine filename
        filename = request.filename or "export.xlsx"
        if not filename.endswith('.xlsx'):
            filename += '.xlsx'
        
        # Return Excel file
        return FileResponse(
            path=excel_path,
            filename=filename,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        logger.error(f"Excel export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Excel export failed: {str(e)}")


@router.post("/export")
async def export_data_endpoint(
    request: ExportRequest,
    current_user=Depends(get_current_user)
):
    """
    Export data in specified format.
    
    Args:
        request: Export request
        
    Returns:
        File in requested format
    """
    try:
        if request.format.lower() == 'csv':
            return await export_csv_endpoint(request, current_user)
        elif request.format.lower() in ['excel', 'xlsx']:
            return await export_excel_endpoint(request, current_user)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported export format: {request.format}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Data export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


# Utility endpoints

@router.get("/upload/categories")
async def get_upload_categories():
    """Get available file upload categories."""
    upload_manager = FileUploadManager()
    
    categories = {}
    for category, extensions in upload_manager.allowed_extensions.items():
        max_size = upload_manager.category_limits.get(category, upload_manager.max_file_size)
        categories[category] = {
            "allowed_extensions": list(extensions),
            "max_size_bytes": max_size,
            "max_size_mb": round(max_size / (1024 * 1024), 1)
        }
    
    return {
        "categories": categories,
        "default_max_size_bytes": upload_manager.max_file_size,
        "default_max_size_mb": round(upload_manager.max_file_size / (1024 * 1024), 1)
    }


@router.post("/validate/filename")
async def validate_filename_endpoint(filename: str):
    """
    Validate a filename for upload.
    
    Args:
        filename: Filename to validate
        
    Returns:
        Validation result
    """
    is_safe = is_safe_filename(filename)
    category = detect_file_category(filename)
    
    return {
        "filename": filename,
        "is_safe": is_safe,
        "detected_category": category,
        "issues": [] if is_safe else ["Filename contains invalid characters or patterns"]
    }


# File management endpoints (for admin)

@router.delete("/files/{file_id}")
async def delete_file_endpoint(
    file_id: str,
    current_user=Depends(get_current_user)
):
    """
    Delete a file.
    
    Args:
        file_id: File ID to delete
        
    Returns:
        Deletion status
    """
    try:
        # In a real implementation, you would:
        # 1. Look up file metadata from database
        # 2. Verify user has permission to delete the file
        # 3. Delete file from storage and database
        
        upload_manager = FileUploadManager()
        tenant_id = current_user["tenant_id"]
        
        # Find file in tenant directory
        tenant_dir = Path(upload_manager.upload_directory) / tenant_id
        matching_files = list(tenant_dir.glob(f"{file_id}.*"))
        
        if not matching_files:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_path = matching_files[0]
        
        # Delete file
        file_path.unlink()
        
        logger.info(f"File deleted: {file_id}")
        return {"status": "success", "message": "File deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File deletion failed for {file_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}")


@router.get("/files")
async def list_files(
    category: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user=Depends(get_current_user)
):
    """
    List uploaded files for the current tenant.
    
    Args:
        category: Filter by category (optional)
        limit: Maximum number of results
        offset: Result offset for pagination
        
    Returns:
        List of file metadata
    """
    try:
        # In a real implementation, you would query the database
        # For now, we'll list files from the upload directory
        
        upload_manager = FileUploadManager()
        tenant_id = current_user["tenant_id"]
        tenant_dir = Path(upload_manager.upload_directory) / tenant_id
        
        if not tenant_dir.exists():
            return {"files": [], "total": 0}
        
        files = []
        for file_path in tenant_dir.iterdir():
            if file_path.is_file():
                # Extract file ID from filename (format: {file_id}.{extension})
                file_id = file_path.stem
                
                file_info = {
                    "file_id": file_id,
                    "original_name": file_path.name,
                    "size_bytes": file_path.stat().st_size,
                    "modified_at": file_path.stat().st_mtime,
                    "download_url": f"/api/files/{file_id}"
                }
                
                files.append(file_info)
        
        # Apply pagination
        total = len(files)
        files = files[offset:offset + limit]
        
        return {
            "files": files,
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"File listing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Listing failed: {str(e)}")


# Health check endpoint

@router.get("/health")
async def file_handler_health():
    """Check file handler service health."""
    try:
        upload_manager = FileUploadManager()
        
        # Check if upload directory is accessible
        if not upload_manager.upload_directory.exists():
            upload_manager.upload_directory.mkdir(parents=True, exist_ok=True)
        
        # Check available disk space
        statvfs = os.statvfs(upload_manager.upload_directory)
        available_bytes = statvfs.f_frsize * statvfs.f_bavail
        available_mb = available_bytes / (1024 * 1024)
        
        return {
            "status": "healthy",
            "upload_directory": str(upload_manager.upload_directory),
            "available_space_mb": round(available_mb, 1),
            "max_file_size_mb": round(upload_manager.max_file_size / (1024 * 1024), 1),
            "supported_categories": list(upload_manager.allowed_extensions.keys())
        }
        
    except Exception as e:
        logger.error(f"File handler health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }