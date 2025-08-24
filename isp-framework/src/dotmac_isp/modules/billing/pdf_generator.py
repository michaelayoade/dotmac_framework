"""PDF generation utilities for billing documents."""

import io
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.platypus.flowables import HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

from dotmac_isp.modules.billing.models import Invoice, InvoiceLineItem, Payment, Receipt


logger = logging.getLogger(__name__)


class InvoicePDFGenerator:
    """Generate PDF documents for invoices."""
    
    def __init__(self, company_info: Optional[Dict[str, Any]] = None):
        """  Init   operation."""
        self.company_info = company_info or self._get_default_company_info()
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _get_default_company_info(self) -> Dict[str, Any]:
        """Get default company information."""
        return {
            'name': 'DotMac ISP Services',
            'address': '123 Network Street',
            'city': 'Tech City',
            'state': 'CA',
            'zip': '90210',
            'phone': '(555) 123-4567',
            'email': 'billing@dotmac-isp.com',
            'website': 'www.dotmac-isp.com',
            'tax_id': 'TAX123456789'
        }
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles."""
        self.styles.add(ParagraphStyle(
            name='CompanyName',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2563eb'),
            spaceAfter=6,
            alignment=TA_LEFT
        ))
        
        self.styles.add(ParagraphStyle(
            name='InvoiceTitle',
            parent=self.styles['Heading2'],
            fontSize=18,
            textColor=colors.HexColor('#1f2937'),
            spaceAfter=12,
            alignment=TA_RIGHT
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#374151'),
            spaceAfter=6,
            spaceBefore=12,
            alignment=TA_LEFT
        ))
        
        self.styles.add(ParagraphStyle(
            name='FieldLabel',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#6b7280'),
            spaceAfter=2,
            alignment=TA_LEFT
        ))
        
        self.styles.add(ParagraphStyle(
            name='FieldValue',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#111827'),
            spaceAfter=6,
            alignment=TA_LEFT
        ))
    
    async def generate_invoice_pdf(self, invoice: Invoice, customer_data: Dict[str, Any]) -> bytes:
        """Generate PDF for an invoice."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        story = []
        
        # Header section
        story.extend(self._build_header(invoice))
        story.append(Spacer(1, 12))
        
        # Invoice and customer info
        story.extend(self._build_invoice_info(invoice, customer_data))
        story.append(Spacer(1, 20))
        
        # Line items table
        story.extend(self._build_line_items_table(invoice.line_items))
        story.append(Spacer(1, 20))
        
        # Totals section
        story.extend(self._build_totals_section(invoice))
        story.append(Spacer(1, 20))
        
        # Payment information
        if invoice.payments:
            story.extend(self._build_payment_section(invoice.payments))
            story.append(Spacer(1, 20))
        
        # Footer
        story.extend(self._build_footer())
        
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    
    def _build_header(self, invoice: Invoice) -> List[Any]:
        """Build PDF header with company info and invoice title."""
        elements = []
        
        # Company info and invoice title in two columns
        header_data = [
            [
                Paragraph(self.company_info['name'], self.styles['CompanyName']),
                Paragraph('INVOICE', self.styles['InvoiceTitle'])
            ],
            [
                Paragraph(f"{self.company_info['address']}<br/>"
                         f"{self.company_info['city']}, {self.company_info['state']} {self.company_info['zip']}<br/>"
                         f"Phone: {self.company_info['phone']}<br/>"
                         f"Email: {self.company_info['email']}", 
                         self.styles['Normal']),
                Paragraph(f"Invoice #{invoice.invoice_number}<br/>"
                         f"Date: {invoice.invoice_date.strftime('%B %d, %Y')}<br/>"
                         f"Due Date: {invoice.due_date.strftime('%B %d, %Y')}", 
                         self.styles['Normal'])
            ]
        ]
        
        header_table = Table(header_data, colWidths=[4*inch, 2.5*inch])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ]))
        
        elements.append(header_table)
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e5e7eb')))
        
        return elements
    
    def _build_invoice_info(self, invoice: Invoice, customer_data: Dict[str, Any]) -> List[Any]:
        """Build invoice and customer information section."""
        elements = []
        
        # Customer information
        customer_info = [
            ['Bill To:', ''],
            [customer_data.get('name', 'N/A'), ''],
            [customer_data.get('address', 'N/A'), ''],
            [f"{customer_data.get('city', '')}, {customer_data.get('state', '')} {customer_data.get('zip', '')}", '']
        ]
        
        if customer_data.get('email'):
            customer_info.append([f"Email: {customer_data['email']}", ''])
        
        customer_table = Table(customer_info, colWidths=[3*inch, 3.5*inch])
        customer_table.setStyle(TableStyle([
            ('FONT', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        elements.append(customer_table)
        
        return elements
    
    def _build_line_items_table(self, line_items: List[InvoiceLineItem]) -> List[Any]:
        """Build line items table."""
        elements = []
        
        # Table headers
        headers = ['Description', 'Quantity', 'Unit Price', 'Tax', 'Total']
        data = [headers]
        
        # Add line items
        for item in line_items:
            data.append([
                item.description,
                f"{item.quantity:,.2f}",
                f"${item.unit_price:,.2f}",
                f"${item.tax_amount:,.2f}",
                f"${item.line_total:,.2f}"
            ])
        
        table = Table(data, colWidths=[2.5*inch, 0.8*inch, 1*inch, 0.8*inch, 1*inch])
        table.setStyle(TableStyle([
            # Header styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#374151')),
            ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Data styling
            ('FONT', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),  # Right align numbers
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),   # Left align descriptions
            
            # Borders
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#d1d5db')),
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#9ca3af')),
            
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')])
        ]))
        
        elements.append(table)
        
        return elements
    
    def _build_totals_section(self, invoice: Invoice) -> List[Any]:
        """Build totals section."""
        elements = []
        
        # Build totals data
        totals_data = []
        
        if invoice.subtotal > 0:
            totals_data.append(['Subtotal:', f"${invoice.subtotal:,.2f}"])
        
        if invoice.discount_amount > 0:
            totals_data.append(['Discount:', f"-${invoice.discount_amount:,.2f}"])
        
        if invoice.tax_amount > 0:
            totals_data.append(['Tax:', f"${invoice.tax_amount:,.2f}"])
        
        totals_data.append(['Total Amount:', f"${invoice.total_amount:,.2f}"])
        
        if invoice.paid_amount > 0:
            totals_data.append(['Amount Paid:', f"${invoice.paid_amount:,.2f}"])
            
        balance_due = invoice.balance_due
        if balance_due > 0:
            totals_data.append(['Balance Due:', f"${balance_due:,.2f}"])
        
        # Create totals table
        totals_table = Table(totals_data, colWidths=[4.5*inch, 2*inch])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONT', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONT', (0, -1), (-1, -1), 'Helvetica-Bold'),  # Bold total row
            ('FONTSIZE', (0, -1), (-1, -1), 12),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor('#374151')),
            ('TOPPADDING', (0, -1), (-1, -1), 6),
        ]))
        
        elements.append(totals_table)
        
        return elements
    
    def _build_payment_section(self, payments: List[Payment]) -> List[Any]:
        """Build payment history section."""
        elements = []
        
        elements.append(Paragraph('Payment History', self.styles['SectionHeader']))
        
        # Payment table headers
        headers = ['Date', 'Method', 'Amount', 'Status', 'Reference']
        data = [headers]
        
        # Add payment records
        for payment in payments:
            data.append([
                payment.payment_date.strftime('%m/%d/%Y'),
                payment.payment_method.value.replace('_', ' ').title(),
                f"${payment.amount:,.2f}",
                payment.status.value.title(),
                payment.reference_number or payment.transaction_id or 'N/A'
            ])
        
        payment_table = Table(data, colWidths=[1*inch, 1.2*inch, 1*inch, 1*inch, 1.5*inch])
        payment_table.setStyle(TableStyle([
            # Header styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#374151')),
            ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Data styling
            ('FONT', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (2, 1), (2, -1), 'RIGHT'),  # Right align amounts
            
            # Borders
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#d1d5db')),
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#9ca3af')),
        ]))
        
        elements.append(payment_table)
        
        return elements
    
    def _build_footer(self) -> List[Any]:
        """Build PDF footer."""
        elements = []
        
        elements.append(Spacer(1, 40))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e5e7eb')))
        elements.append(Spacer(1, 12))
        
        footer_text = f"""
        <b>Payment Instructions:</b><br/>
        Please remit payment by the due date to avoid late fees.<br/>
        For questions about this invoice, contact us at {self.company_info['email']}<br/>
        Tax ID: {self.company_info['tax_id']}
        """
        
        elements.append(Paragraph(footer_text, self.styles['Normal']))
        
        return elements


class ReceiptPDFGenerator:
    """Generate PDF receipts for payments."""
    
    def __init__(self, company_info: Optional[Dict[str, Any]] = None):
        """  Init   operation."""
        self.company_info = company_info or self._get_default_company_info()
        self.styles = getSampleStyleSheet()
    
    def _get_default_company_info(self) -> Dict[str, Any]:
        """Get default company information."""
        return {
            'name': 'DotMac ISP Services',
            'address': '123 Network Street',
            'city': 'Tech City',
            'state': 'CA',
            'zip': '90210',
            'phone': '(555) 123-4567',
            'email': 'billing@dotmac-isp.com',
            'website': 'www.dotmac-isp.com',
            'tax_id': 'TAX123456789'
        }
    
    async def generate_receipt_pdf(self, receipt: Receipt, customer_data: Dict[str, Any]) -> bytes:
        """Generate PDF receipt for a payment."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        
        story = []
        
        # Header
        story.append(Paragraph(self.company_info['name'], self.styles['Title']))
        story.append(Paragraph('PAYMENT RECEIPT', self.styles['Heading1']))
        story.append(Spacer(1, 20))
        
        # Receipt details
        receipt_data = [
            ['Receipt Number:', receipt.receipt_number],
            ['Payment Date:', receipt.issued_at.strftime('%B %d, %Y')],
            ['Invoice Number:', receipt.invoice_number],
            ['Customer:', customer_data.get('name', 'N/A')],
            ['Payment Method:', receipt.payment_method.value.replace('_', ' ').title()],
            ['Amount Paid:', f"${receipt.amount:,.2f}"]
        ]
        
        receipt_table = Table(receipt_data, colWidths=[2*inch, 3*inch])
        receipt_table.setStyle(TableStyle([
            ('FONT', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        story.append(receipt_table)
        story.append(Spacer(1, 40))
        
        # Thank you message
        story.append(Paragraph('Thank you for your payment!', self.styles['Heading2']))
        
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()


class PDFBatchProcessor:
    """Process multiple PDFs in batch operations."""
    
    def __init__(self):
        """  Init   operation."""
        self.invoice_generator = InvoicePDFGenerator()
        self.receipt_generator = ReceiptPDFGenerator()
    
    async def generate_monthly_invoices(self, invoices: List[Invoice], 
                                      customer_data_map: Dict[str, Dict[str, Any]]) -> Dict[str, bytes]:
        """Generate PDFs for multiple invoices."""
        results = {}
        
        for invoice in invoices:
            try:
                customer_data = customer_data_map.get(str(invoice.customer_id), {})
                pdf_data = await self.invoice_generator.generate_invoice_pdf(invoice, customer_data)
                results[invoice.invoice_number] = pdf_data
                logger.info(f"Generated PDF for invoice {invoice.invoice_number}")
            except Exception as e:
                logger.error(f"Failed to generate PDF for invoice {invoice.invoice_number}: {e}")
                results[invoice.invoice_number] = None
        
        return results
    
    async def generate_payment_receipts(self, receipts: List[Receipt],
                                      customer_data_map: Dict[str, Dict[str, Any]]) -> Dict[str, bytes]:
        """Generate PDFs for multiple receipts."""
        results = {}
        
        for receipt in receipts:
            try:
                customer_data = customer_data_map.get(receipt.customer_name, {})
                pdf_data = await self.receipt_generator.generate_receipt_pdf(receipt, customer_data)
                results[receipt.receipt_number] = pdf_data
                logger.info(f"Generated PDF for receipt {receipt.receipt_number}")
            except Exception as e:
                logger.error(f"Failed to generate PDF for receipt {receipt.receipt_number}: {e}")
                results[receipt.receipt_number] = None
        
        return results


# Utility functions for external use
async def generate_invoice_pdf(invoice: Invoice, customer_data: Dict[str, Any], 
                             company_info: Optional[Dict[str, Any]] = None) -> bytes:
    """Convenience function to generate invoice PDF."""
    generator = InvoicePDFGenerator(company_info)
    return await generator.generate_invoice_pdf(invoice, customer_data)


async def generate_receipt_pdf(receipt: Receipt, customer_data: Dict[str, Any],
                             company_info: Optional[Dict[str, Any]] = None) -> bytes:
    """Convenience function to generate receipt PDF."""
    generator = ReceiptPDFGenerator(company_info)
    return await generator.generate_receipt_pdf(receipt, customer_data)