"""File handling utilities for billing module."""

import hashlib
import logging
import mimetypes
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Tuple

import aiofiles
import pandas as pd
from fastapi import HTTPException, UploadFile

from dotmac_isp.core.settings import get_settings
from dotmac_shared.api.exception_handlers import standard_exception_handler

logger = logging.getLogger(__name__, timezone)
settings = get_settings()


class FileUploadConfig:
    """Configuration for file uploads."""

    # Allowed file types for different purposes
    INVOICE_ATTACHMENTS = {
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/gif",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    }

    PAYMENT_RECEIPTS = {"application/pdf", "image/jpeg", "image/png", "image/gif"}

    BULK_IMPORT = {
        "text/csv",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }

    # Maximum file sizes (in bytes)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
    MAX_BULK_IMPORT_SIZE = 20 * 1024 * 1024  # 20MB

    # Storage paths
    UPLOAD_BASE_DIR = "uploads/billing"
    INVOICE_ATTACHMENTS_DIR = "attachments/invoices"
    PAYMENT_RECEIPTS_DIR = "attachments/payments"
    BULK_IMPORTS_DIR = "imports"
    TEMP_DIR = "temp"


class FileValidator:
    """Validate uploaded files."""

    def __init__(self):
        """Init   operation."""
        self.config = FileUploadConfig()

    async def validate_file(self, file: UploadFile, purpose: str) -> Dict[str, Any]:
        """Validate uploaded file based on purpose."""
        # Get allowed types and max size based on purpose
        if purpose == "invoice_attachment":
            allowed_types = self.config.INVOICE_ATTACHMENTS
            max_size = self.config.MAX_FILE_SIZE
        elif purpose == "payment_receipt":
            allowed_types = self.config.PAYMENT_RECEIPTS
            max_size = self.config.MAX_IMAGE_SIZE
        elif purpose == "bulk_import":
            allowed_types = self.config.BULK_IMPORT
            max_size = self.config.MAX_BULK_IMPORT_SIZE
        else:
            raise ValueError(f"Unknown file purpose: {purpose}")

        # Validate file type
        content_type = file.content_type
        if content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"File type {content_type} not allowed for {purpose}",
            )
        # Check file size
        file_content = await file.read()
        file_size = len(file_content)
        await file.seek(0)  # Reset file pointer

        if file_size > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File size {file_size} exceeds maximum {max_size} bytes",
            )
        # Calculate file hash for deduplication
        file_hash = hashlib.sha256(file_content).hexdigest()

        return {
            "valid": True,
            "size": file_size,
            "content_type": content_type,
            "hash": file_hash,
            "filename": file.filename,
        }

    def validate_csv_structure(
        self, df: pd.DataFrame, expected_columns: List[str]
    ) -> Dict[str, Any]:
        """Validate CSV structure for bulk imports."""
        missing_columns = set(expected_columns) - set(df.columns)
        extra_columns = set(df.columns) - set(expected_columns)

        if missing_columns:
            return {
                "valid": False,
                "error": f"Missing required columns: {', '.join(missing_columns)}",
            }

        return {
            "valid": True,
            "missing_columns": list(missing_columns),
            "extra_columns": list(extra_columns),
            "row_count": len(df),
        }


class FileStorageManager:
    """Manage file storage operations."""

    def __init__(self):
        """Init   operation."""
        self.config = FileUploadConfig()
        self.base_path = Path(settings.file_storage_path) / self.config.UPLOAD_BASE_DIR
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure all required directories exist."""
        directories = [
            self.base_path / self.config.INVOICE_ATTACHMENTS_DIR,
            self.base_path / self.config.PAYMENT_RECEIPTS_DIR,
            self.base_path / self.config.BULK_IMPORTS_DIR,
            self.base_path / self.config.TEMP_DIR,
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def _generate_filename(
        self, original_filename: str, tenant_id: str, entity_id: Optional[str] = None
    ) -> str:
        """Generate unique filename."""
        file_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        # Extract file extension
        _, ext = os.path.splitext(original_filename)

        if entity_id:
            return f"{tenant_id}_{entity_id}_{timestamp}_{file_id}{ext}"
        else:
            return f"{tenant_id}_{timestamp}_{file_id}{ext}"

    async def store_file(
        self,
        file: UploadFile,
        purpose: str,
        tenant_id: str,
        entity_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Store uploaded file."""
        # Determine storage subdirectory
        if purpose == "invoice_attachment":
            subdir = self.config.INVOICE_ATTACHMENTS_DIR
        elif purpose == "payment_receipt":
            subdir = self.config.PAYMENT_RECEIPTS_DIR
        elif purpose == "bulk_import":
            subdir = self.config.BULK_IMPORTS_DIR
        else:
            subdir = self.config.TEMP_DIR

        # Generate filename and path
        filename = self._generate_filename(file.filename, tenant_id, entity_id)
        file_path = self.base_path / subdir / filename

        # Store file
        async with aiofiles.open(file_path, "wb") as f:
            content = await file.read()
            await f.write(content)

        # Calculate file hash
        file_hash = hashlib.sha256(content).hexdigest()

        return {
            "filename": filename,
            "original_filename": file.filename,
            "file_path": str(file_path),
            "relative_path": f"{subdir}/{filename}",
            "size": len(content),
            "content_type": file.content_type,
            "hash": file_hash,
            "stored_at": datetime.now(timezone.utc),
        }

    async def retrieve_file(self, relative_path: str) -> Tuple[bytes, str]:
        """Retrieve stored file."""
        file_path = self.base_path / relative_path

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {relative_path}")

        async with aiofiles.open(file_path, "rb") as f:
            content = await f.read()

        # Determine content type
        content_type, _ = mimetypes.guess_type(str(file_path))

        return content, content_type or "application/octet-stream"

    async def delete_file(self, relative_path: str) -> bool:
        """Delete stored file."""
        file_path = self.base_path / relative_path

        if file_path.exists():
            file_path.unlink()
            return True

        return False

    def get_file_info(self, relative_path: str) -> Dict[str, Any]:
        """Get file information."""
        file_path = self.base_path / relative_path

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {relative_path}")

        stat = file_path.stat()
        content_type, _ = mimetypes.guess_type(str(file_path))

        return {
            "size": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_ctime),
            "modified_at": datetime.fromtimestamp(stat.st_mtime),
            "content_type": content_type or "application/octet-stream",
        }


class BulkImportProcessor:
    """Process bulk import files."""

    def __init__(self):
        """Init   operation."""
        self.validator = FileValidator()

    async def process_invoice_import(self, file_path: str) -> Dict[str, Any]:
        """Process invoice bulk import file."""
        # Expected columns for invoice import
        expected_columns = [
            "customer_id",
            "invoice_date",
            "due_date",
            "description",
            "quantity",
            "unit_price",
            "tax_rate",
        ]

        try:
            # Read CSV file
            df = pd.read_csv(file_path)

            # Validate structure
            validation = self.validator.validate_csv_structure(df, expected_columns)
            if not validation["valid"]:
                return validation

            # Process data
            processed_invoices = []
            errors = []

            for index, row in df.iterrows():
                try:
                    # Validate required fields
                    if pd.isna(row["customer_id"]) or pd.isna(row["description"]):
                        errors.append(f"Row {index + 1}: Missing required fields")
                        continue

                    # Process invoice data
                    invoice_data = {
                        "customer_id": str(row["customer_id"]),
                        "invoice_date": pd.to_datetime(row["invoice_date"]).date(),
                        "due_date": pd.to_datetime(row["due_date"]).date(),
                        "line_items": [
                            {
                                "description": row["description"],
                                "quantity": float(row.get("quantity", 1)),
                                "unit_price": float(row["unit_price"]),
                                "tax_rate": float(row.get("tax_rate", 0)),
                            }
                        ],
                    }

                    processed_invoices.append(invoice_data)

                except Exception as e:
                    errors.append(f"Row {index + 1}: {str(e)}")

            return {
                "valid": True,
                "processed_count": len(processed_invoices),
                "error_count": len(errors),
                "invoices": processed_invoices,
                "errors": errors,
            }

        except Exception as e:
            return {"valid": False, "error": f"Failed to process file: {str(e)}"}

    async def process_payment_import(self, file_path: str) -> Dict[str, Any]:
        """Process payment bulk import file."""
        expected_columns = [
            "invoice_number",
            "payment_date",
            "amount",
            "payment_method",
            "transaction_id",
        ]

        try:
            df = pd.read_csv(file_path)

            validation = self.validator.validate_csv_structure(df, expected_columns)
            if not validation["valid"]:
                return validation

            processed_payments = []
            errors = []

            for index, row in df.iterrows():
                try:
                    if pd.isna(row["invoice_number"]) or pd.isna(row["amount"]):
                        errors.append(f"Row {index + 1}: Missing required fields")
                        continue

                    payment_data = {
                        "invoice_number": row["invoice_number"],
                        "payment_date": pd.to_datetime(row["payment_date"]).date(),
                        "amount": float(row["amount"]),
                        "payment_method": row["payment_method"],
                        "transaction_id": row.get("transaction_id", ""),
                    }

                    processed_payments.append(payment_data)

                except Exception as e:
                    errors.append(f"Row {index + 1}: {str(e)}")

            return {
                "valid": True,
                "processed_count": len(processed_payments),
                "error_count": len(errors),
                "payments": processed_payments,
                "errors": errors,
            }

        except Exception as e:
            return {"valid": False, "error": f"Failed to process file: {str(e)}"}


class FileUploadService:
    """Main service for handling file uploads."""

    def __init__(self):
        """Init   operation."""
        self.validator = FileValidator()
        self.storage = FileStorageManager()
        self.import_processor = BulkImportProcessor()

    async def upload_invoice_attachment(
        self, file: UploadFile, tenant_id: str, invoice_id: str
    ) -> Dict[str, Any]:
        """Upload invoice attachment."""
        # Validate file
        validation = await self.validator.validate_file(file, "invoice_attachment")

        # Store file
        storage_info = await self.storage.store_file(
            file, "invoice_attachment", tenant_id, invoice_id
        )
        return {
            "success": True,
            "file_id": storage_info["hash"],
            "filename": storage_info["filename"],
            "original_filename": storage_info["original_filename"],
            "size": storage_info["size"],
            "content_type": storage_info["content_type"],
            "relative_path": storage_info["relative_path"],
        }

    async def upload_payment_receipt(
        self, file: UploadFile, tenant_id: str, payment_id: str
    ) -> Dict[str, Any]:
        """Upload payment receipt."""
        validation = await self.validator.validate_file(file, "payment_receipt")

        storage_info = await self.storage.store_file(
            file, "payment_receipt", tenant_id, payment_id
        )
        return {
            "success": True,
            "file_id": storage_info["hash"],
            "filename": storage_info["filename"],
            "original_filename": storage_info["original_filename"],
            "size": storage_info["size"],
            "content_type": storage_info["content_type"],
            "relative_path": storage_info["relative_path"],
        }

    async def upload_bulk_import(
        self, file: UploadFile, tenant_id: str, import_type: str
    ) -> Dict[str, Any]:
        """Upload bulk import file."""
        validation = await self.validator.validate_file(file, "bulk_import")

        storage_info = await self.storage.store_file(file, "bulk_import", tenant_id)
        # Process the import file
        if import_type == "invoices":
            processing_result = await self.import_processor.process_invoice_import(
                storage_info["file_path"]
            )
        elif import_type == "payments":
            processing_result = await self.import_processor.process_payment_import(
                storage_info["file_path"]
            )
        else:
            processing_result = {
                "valid": False,
                "error": f"Unknown import type: {import_type}",
            }

        return {
            "success": True,
            "file_info": {
                "file_id": storage_info["hash"],
                "filename": storage_info["filename"],
                "relative_path": storage_info["relative_path"],
            },
            "processing_result": processing_result,
        }

    async def get_file(self, relative_path: str) -> Tuple[bytes, str]:
        """Get uploaded file."""
        return await self.storage.retrieve_file(relative_path)

    async def delete_file(self, relative_path: str) -> bool:
        """Delete uploaded file."""
        return await self.storage.delete_file(relative_path)

    def get_file_info(self, relative_path: str) -> Dict[str, Any]:
        """Get file information."""
        return self.storage.get_file_info(relative_path)


# Global file upload service instance
file_upload_service = FileUploadService()


# Utility functions for external use
async def upload_invoice_attachment(
    file: UploadFile, tenant_id: str, invoice_id: str
) -> Dict[str, Any]:
    """Convenience function to upload invoice attachment."""
    return await file_upload_service.upload_invoice_attachment(
        file, tenant_id, invoice_id
    )


async def upload_payment_receipt(
    file: UploadFile, tenant_id: str, payment_id: str
) -> Dict[str, Any]:
    """Convenience function to upload payment receipt."""
    return await file_upload_service.upload_payment_receipt(file, tenant_id, payment_id)


async def process_bulk_import(
    file: UploadFile, tenant_id: str, import_type: str
) -> Dict[str, Any]:
    """Convenience function to process bulk import."""
    return await file_upload_service.upload_bulk_import(file, tenant_id, import_type)
