"""
File generation module for billing documents.

This module provides optional file generation capabilities including
PDF invoices, Excel reports, and CSV exports. Dependencies are optional
and gracefully degraded if not available.
"""

import warnings

# Check for optional dependencies
try:
    from .pdf import PDFInvoiceGenerator
    _PDF_AVAILABLE = True
except ImportError as e:
    _PDF_AVAILABLE = False
    _pdf_error = str(e)

try:
    from .excel import ExcelReportGenerator
    _EXCEL_AVAILABLE = True
except ImportError as e:
    _EXCEL_AVAILABLE = False
    _excel_error = str(e)

from .csv import CSVExporter  # CSV is always available

# Public API
__all__ = ["CSVExporter"]

if _PDF_AVAILABLE:
    __all__.append("PDFInvoiceGenerator")
else:
    def PDFInvoiceGenerator(*args, **kwargs):
        raise ImportError(
            f"PDF generation not available: {_pdf_error}. "
            "Install reportlab: pip install reportlab"
        )

if _EXCEL_AVAILABLE:
    __all__.append("ExcelReportGenerator")
else:
    def ExcelReportGenerator(*args, **kwargs):
        raise ImportError(
            f"Excel generation not available: {_excel_error}. "
            "Install openpyxl: pip install openpyxl"
        )

# Convenience functions
def create_invoice_pdf(invoice_data: dict, output_path: str, **kwargs):
    """Create PDF invoice (requires reportlab)."""
    if not _PDF_AVAILABLE:
        raise ImportError("PDF generation requires reportlab")

    generator = PDFInvoiceGenerator(**kwargs)
    return generator.generate_invoice(invoice_data, output_path)

def create_billing_report_excel(report_data: dict, output_path: str, **kwargs):
    """Create Excel billing report (requires openpyxl)."""
    if not _EXCEL_AVAILABLE:
        raise ImportError("Excel generation requires openpyxl")

    generator = ExcelReportGenerator(**kwargs)
    return generator.generate_billing_report(report_data, output_path)

def create_usage_report_csv(usage_data: list, output_path: str, **kwargs):
    """Create CSV usage report (always available)."""
    exporter = CSVExporter(**kwargs)
    return exporter.export_usage_data(usage_data, output_path)
