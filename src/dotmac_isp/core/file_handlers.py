"""File Handling Utilities for Frontend Integration."""

import csv
import io
import logging
import mimetypes
import os
import tempfile
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Union

import aiofiles
import openpyxl
import pandas as pd
from fastapi import HTTPException, UploadFile
from openpyxl.styles import Alignment, Border, Fill, Font, PatternFill, Side
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.platypus.flowables import HRFlowable

logger = logging.getLogger(__name__)


@dataclass
class FileMetadata:
    """File metadata structure."""

    file_id: str
    original_name: str
    stored_path: str
    mime_type: str
    size_bytes: int
    uploaded_at: datetime
    tenant_id: str
    user_id: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = None

    def __post_init__(self):
        """Post Init   operation."""
        if self.tags is None:
            self.tags = []


class PDFGenerator:
    """PDF generation utilities for invoices, reports, and documents."""

    def __init__(self, company_info: Dict[str, str] = None):
        """Initialize PDF generator with company information."""
        self.company_info = company_info or {
            "name": "DotMac ISP",
            "address": "123 Main Street",
            "city": "City, State 12345",
            "phone": "(555) 123-4567",
            "email": "info@dotmacisp.com",
            "website": "www.dotmacisp.com",
        }

    def generate_invoice_pdf(
        self, invoice_data: Dict[str, Any], output_path: str = None
    ) -> str:
        """
        Generate invoice PDF.

        Args:
            invoice_data: Invoice data dictionary
            output_path: Output file path (optional, will generate if not provided)

        Returns:
            Path to generated PDF file
        """
        if not output_path:
            output_path = (
                f"/tmp/invoice_{invoice_data['invoice_number']}_{uuid.uuid4()}.pdf"
            )

        # Create PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18,
        )
        # Build content
        story = []
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue,
        )
        header_style = ParagraphStyle(
            "Header",
            parent=styles["Normal"],
            fontSize=12,
            spaceAfter=6,
            textColor=colors.darkblue,
        )
        # Company header
        company_name = Paragraph(self.company_info["name"], title_style)
        story.append(company_name)

        company_details = f"""
        {self.company_info['address']}<br/>
        {self.company_info['city']}<br/>
        Phone: {self.company_info['phone']}<br/>
        Email: {self.company_info['email']}
        """
        story.append(Paragraph(company_details, styles["Normal"]))
        story.append(Spacer(1, 20))

        # Invoice title and details
        invoice_title = Paragraph("INVOICE", title_style)
        story.append(invoice_title)
        story.append(Spacer(1, 20))

        # Invoice info table
        invoice_info = [
            ["Invoice Number:", invoice_data["invoice_number"]],
            ["Invoice Date:", invoice_data["invoice_date"]],
            ["Due Date:", invoice_data["due_date"]],
            ["Customer ID:", invoice_data["customer_id"]],
        ]

        invoice_table = Table(invoice_info, colWidths=[2 * inch, 3 * inch])
        invoice_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        story.append(invoice_table)
        story.append(Spacer(1, 20))

        # Customer information
        customer_info = invoice_data.get("customer_info", {})
        if customer_info:
            story.append(Paragraph("Bill To:", header_style))
            bill_to = f"""
            {customer_info.get('name', 'N/A')}<br/>
            {customer_info.get('address', '')}<br/>
            {customer_info.get('city', '')} {customer_info.get('state', '')} {customer_info.get('zip_code', '')}<br/>
            Email: {customer_info.get('email', 'N/A')}
            """
            story.append(Paragraph(bill_to, styles["Normal"]))
            story.append(Spacer(1, 20))

        # Invoice items
        story.append(Paragraph("Invoice Items:", header_style))

        items_data = [["Description", "Quantity", "Unit Price", "Total"]]

        for item in invoice_data.get("items", []):
            items_data.append(
                [
                    item.get("description", ""),
                    str(item.get("quantity", 0)),
                    f"${float(item.get('unit_price', 0)):.2f}",
                    f"${float(item.get('total', 0)):.2f}",
                ]
            )

        # Add totals
        subtotal = invoice_data.get("subtotal", 0)
        tax_amount = invoice_data.get("tax_amount", 0)
        total_amount = invoice_data.get("total_amount", 0)

        items_data.extend(
            [
                ["", "", "Subtotal:", f"${float(subtotal):.2f}"],
                ["", "", "Tax:", f"${float(tax_amount):.2f}"],
                ["", "", "Total:", f"${float(total_amount):.2f}"],
            ]
        )

        items_table = Table(
            items_data, colWidths=[3 * inch, 1 * inch, 1.5 * inch, 1.5 * inch]
        )
        items_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -4), colors.beige),
                    ("GRID", (0, 0), (-1, -4), 1, colors.black),
                    ("BACKGROUND", (0, -3), (-1, -1), colors.lightgrey),
                    ("FONTNAME", (0, -3), (-1, -1), "Helvetica-Bold"),
                    ("GRID", (0, -3), (-1, -1), 1, colors.black),
                ]
            )
        )
        story.append(items_table)
        story.append(Spacer(1, 30))

        # Payment information
        payment_info = invoice_data.get("payment_info", {})
        if payment_info:
            story.append(Paragraph("Payment Information:", header_style))
            payment_text = f"""
            Payment Terms: {payment_info.get('terms', 'Net 30')}<br/>
            Payment Methods: {', '.join(payment_info.get('methods', ['Bank Transfer', 'Credit Card']))}<br/>
            """
            story.append(Paragraph(payment_text, styles["Normal"]))
            story.append(Spacer(1, 20))

        # Footer
        story.append(HRFlowable(width="100%", thickness=1, color=colors.black))
        story.append(Spacer(1, 10))
        footer_text = "Thank you for your business!"
        story.append(Paragraph(footer_text, styles["Normal"]))

        # Build PDF
        doc.build(story)

        logger.info(f"Generated invoice PDF: {output_path}")
        return output_path

    def generate_report_pdf(
        self, report_data: Dict[str, Any], output_path: str = None
    ) -> str:
        """
        Generate report PDF.

        Args:
            report_data: Report data dictionary
            output_path: Output file path (optional)

        Returns:
            Path to generated PDF file
        """
        if not output_path:
            report_name = report_data.get("title", "report").replace(" ", "_").lower()
            output_path = f"/tmp/{report_name}_{uuid.uuid4()}.pdf"

        doc = SimpleDocTemplate(output_path, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()

        # Title
        title = report_data.get("title", "Report")
        story.append(Paragraph(title, styles["Title"]))
        story.append(Spacer(1, 20))

        # Report metadata
        generated_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        story.append(Paragraph(f"Generated: {generated_date}", styles["Normal"]))
        story.append(Spacer(1, 10))

        # Report content
        content = report_data.get("content", [])
        for section in content:
            if section.get("type") == "heading":
                story.append(Paragraph(section["text"], styles["Heading2"]))
                story.append(Spacer(1, 12))
            elif section.get("type") == "paragraph":
                story.append(Paragraph(section["text"], styles["Normal"]))
                story.append(Spacer(1, 12))
            elif section.get("type") == "table":
                table_data = section["data"]
                table = Table(table_data)
                table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, -1), 9),
                            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                            ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                            ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        ]
                    )
                )
                story.append(table)
                story.append(Spacer(1, 12))

        doc.build(story)

        logger.info(f"Generated report PDF: {output_path}")
        return output_path


class CSVExporter:
    """CSV export utilities for data export functionality."""

    def export_to_csv(
        self,
        data: List[Dict[str, Any]],
        output_path: str = None,
        columns: List[str] = None,
    ) -> str:
        """
        Export data to CSV file.

        Args:
            data: List of data dictionaries
            output_path: Output file path (optional)
            columns: Column names to include (optional, uses all keys if not provided)

        Returns:
            Path to generated CSV file
        """
        if not output_path:
            output_path = f"/tmp/export_{uuid.uuid4()}.csv"

        if not data:
            # Create empty CSV file
            with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                if columns:
                    writer.writerow(columns)
            return output_path

        # Determine columns
        if not columns:
            columns = list(data[0].keys())

        with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=columns)
            writer.writeheader()

            for row in data:
                # Convert non-string values to strings
                cleaned_row = {}
                for key in columns:
                    value = row.get(key, "")
                    if isinstance(value, (datetime, date)):
                        cleaned_row[key] = value.isoformat()
                    elif isinstance(value, Decimal):
                        cleaned_row[key] = str(value)
                    elif isinstance(value, (dict, list)):
                        cleaned_row[key] = str(value)
                    else:
                        cleaned_row[key] = value

                writer.writerow(cleaned_row)

        logger.info(f"Exported {len(data)} rows to CSV: {output_path}")
        return output_path

    def export_to_excel(
        self,
        data: List[Dict[str, Any]],
        output_path: str = None,
        sheet_name: str = "Data",
        columns: List[str] = None,
    ) -> str:
        """
        Export data to Excel file.

        Args:
            data: List of data dictionaries
            output_path: Output file path (optional)
            sheet_name: Excel sheet name
            columns: Column names to include (optional)

        Returns:
            Path to generated Excel file
        """
        if not output_path:
            output_path = f"/tmp/export_{uuid.uuid4()}.xlsx"

        # Use pandas for easier Excel export
        if not data:
            df = pd.DataFrame(columns=columns or [])
        else:
            df = pd.DataFrame(data)
            if columns:
                df = df[columns]

        # Convert datetime columns
        for col in df.columns:
            if df[col].dtype == "object":
                # Try to convert datetime strings
                try:
                    df[col] = pd.to_datetime(df[col], errors="ignore")
                except Exception:
                    pass

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)

            # Format the worksheet
            worksheet = writer.sheets[sheet_name]

            # Style header row
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(
                start_color="366092", end_color="366092", fill_type="solid"
            )

            for cell in worksheet[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center")

            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter

                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except Exception:
                        pass

                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width

        logger.info(f"Exported {len(data)} rows to Excel: {output_path}")
        return output_path


class FileUploadManager:
    """File upload management for frontend integration."""

    def __init__(self, upload_directory: str = "/tmp/uploads"):
        """Initialize file upload manager."""
        self.upload_directory = Path(upload_directory)
        self.upload_directory.mkdir(parents=True, exist_ok=True)

        # Allowed file types and size limits
        self.allowed_extensions = {
            "images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"},
            "documents": {".pdf", ".doc", ".docx", ".txt", ".rtf"},
            "spreadsheets": {".xls", ".xlsx", ".csv"},
            "archives": {".zip", ".rar", ".tar", ".gz"},
        }

        self.max_file_size = 50 * 1024 * 1024  # 50MB default
        self.category_limits = {
            "images": 10 * 1024 * 1024,  # 10MB for images
            "documents": 50 * 1024 * 1024,  # 50MB for documents
            "spreadsheets": 20 * 1024 * 1024,  # 20MB for spreadsheets
            "archives": 100 * 1024 * 1024,  # 100MB for archives
        }

    async def upload_file(
        self,
        file: UploadFile,
        tenant_id: str,
        user_id: str = None,
        category: str = None,
        tags: List[str] = None,
    ) -> FileMetadata:
        """
        Upload file and return metadata.

        Args:
            file: FastAPI UploadFile object
            tenant_id: Tenant ID
            user_id: User ID (optional)
            category: File category (optional)
            tags: File tags (optional)

        Returns:
            FileMetadata object
        """
        # Validate file
        await self._validate_file(file, category)

        # Generate file ID and path
        file_id = str(uuid.uuid4())
        file_extension = Path(file.filename).suffix.lower()
        stored_filename = f"{file_id}{file_extension}"
        stored_path = self.upload_directory / tenant_id / stored_filename

        # Create tenant directory if it doesn't exist
        stored_path.parent.mkdir(parents=True, exist_ok=True)

        # Save file
        try:
            async with aiofiles.open(stored_path, "wb") as f:
                content = await file.read()
                await f.write(content)

            # Get file size
            file_size = len(content)

            # Determine MIME type
            mime_type, _ = mimetypes.guess_type(file.filename)
            if not mime_type:
                mime_type = "application/octet-stream"

            # Create metadata
            metadata = FileMetadata(
                file_id=file_id,
                original_name=file.filename,
                stored_path=str(stored_path),
                mime_type=mime_type,
                size_bytes=file_size,
                uploaded_at=datetime.now(timezone.utc),
                tenant_id=tenant_id,
                user_id=user_id,
                category=category,
                tags=tags or [],
            )
            logger.info(f"File uploaded: {file.filename} -> {file_id}")
            return metadata

        except Exception as e:
            # Clean up file if upload failed
            if stored_path.exists():
                stored_path.unlink()
            raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

    async def _validate_file(self, file: UploadFile, category: str = None):
        """Validate uploaded file."""
        # Check file size
        content = await file.read()
        file_size = len(content)

        # Reset file position
        await file.seek(0)

        # Check category-specific size limits
        if category and category in self.category_limits:
            max_size = self.category_limits[category]
        else:
            max_size = self.max_file_size

        if file_size > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {max_size / (1024*1024):.1f}MB",
            )
        # Check file extension
        file_extension = Path(file.filename).suffix.lower()

        if category:
            allowed_extensions = self.allowed_extensions.get(category, set())
            if file_extension not in allowed_extensions:
                raise HTTPException(
                    status_code=400,
                    detail=f"File type not allowed for category '{category}'. "
                    f"Allowed: {', '.join(allowed_extensions)}",
                )

    async def delete_file(self, file_metadata: FileMetadata):
        """Delete uploaded file."""
        try:
            file_path = Path(file_metadata.stored_path)
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted file: {file_metadata.file_id}")
        except Exception as e:
            logger.error(f"Failed to delete file {file_metadata.file_id}: {e}")
            raise

    def get_file_url(self, file_metadata: FileMetadata, base_url: str) -> str:
        """Generate file download URL."""
        return f"{base_url}/api/files/{file_metadata.file_id}"


# Utility functions for common file operations


async def generate_invoice_pdf(invoice_data: Dict[str, Any]) -> str:
    """Generate invoice PDF and return file path."""
    pdf_generator = PDFGenerator()
    return pdf_generator.generate_invoice_pdf(invoice_data)


async def export_data_to_csv(
    data: List[Dict[str, Any]], columns: List[str] = None
) -> str:
    """Export data to CSV and return file path."""
    csv_exporter = CSVExporter()
    return csv_exporter.export_to_csv(data, columns=columns)


async def export_data_to_excel(
    data: List[Dict[str, Any]], columns: List[str] = None
) -> str:
    """Export data to Excel and return file path."""
    csv_exporter = CSVExporter()
    return csv_exporter.export_to_excel(data, columns=columns)


# File type detection utilities


def detect_file_category(filename: str) -> Optional[str]:
    """Detect file category based on extension."""
    file_extension = Path(filename).suffix.lower()

    upload_manager = FileUploadManager()
    for category, extensions in upload_manager.allowed_extensions.items():
        if file_extension in extensions:
            return category

    return None


def is_safe_filename(filename: str) -> bool:
    """Check if filename is safe for storage."""
    # Check for path traversal attempts
    if ".." in filename or "/" in filename or "\\" in filename:
        return False

    # Check for reserved names (Windows)
    reserved_names = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    }

    name_without_ext = Path(filename).stem.upper()
    if name_without_ext in reserved_names:
        return False

    # Check for invalid characters
    invalid_chars = '<>:"|?*\x00'
    if any(char in filename for char in invalid_chars):
        return False

    return True
