"""
PDF generation for billing documents.

This module provides PDF invoice generation using reportlab.
Falls back gracefully if reportlab is not available.
"""

from decimal import Decimal
from pathlib import Path
from typing import Any, Optional, Union

# Optional reportlab imports
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    REPORTLAB_AVAILABLE = True
except ImportError as e:
    REPORTLAB_AVAILABLE = False
    _import_error = str(e)

    # Create stub classes if reportlab not available
    class SimpleDocTemplate:
        def __init__(self, *args, **kwargs):
            raise ImportError(f"reportlab not available: {_import_error}")

    letter = (612, 792)  # Default letter size


class PDFInvoiceGenerator:
    """PDF invoice generator using reportlab."""

    def __init__(
        self,
        page_size: tuple = (612, 792),  # letter size
        margin: int = 72,
        company_logo: Optional[str] = None,
    ):
        """
        Initialize PDF generator.

        Args:
            page_size: Page size tuple (default: letter)
            margin: Page margin in points
            company_logo: Path to company logo image
        """
        if not REPORTLAB_AVAILABLE:
            raise ImportError(
                f"PDF generation requires reportlab: {_import_error}. "
                "Install with: pip install reportlab"
            )

        self.page_size = page_size
        self.margin = margin
        self.company_logo = company_logo
        self.styles = getSampleStyleSheet()

    def generate_invoice(
        self,
        invoice_data: dict[str, Any],
        output_path: Union[str, Path],
        company_info: Optional[dict[str, str]] = None,
    ) -> str:
        """
        Generate PDF invoice.

        Args:
            invoice_data: Invoice data dictionary
            output_path: Output file path
            company_info: Optional company information

        Returns:
            Path to generated PDF file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Create PDF document
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=self.page_size,
            rightMargin=self.margin,
            leftMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin,
        )

        # Build story (content elements)
        story = []

        # Add company header
        if company_info:
            story.extend(self._create_company_header(company_info))
            story.append(Spacer(1, 12))

        # Add invoice header
        story.extend(self._create_invoice_header(invoice_data))
        story.append(Spacer(1, 24))

        # Add customer information
        story.extend(self._create_customer_section(invoice_data))
        story.append(Spacer(1, 24))

        # Add line items table
        story.extend(self._create_line_items_table(invoice_data))
        story.append(Spacer(1, 24))

        # Add totals section
        story.extend(self._create_totals_section(invoice_data))
        story.append(Spacer(1, 24))

        # Add payment information
        if invoice_data.get('payment_terms') or invoice_data.get('payment_instructions'):
            story.extend(self._create_payment_section(invoice_data))
            story.append(Spacer(1, 12))

        # Add footer
        story.extend(self._create_footer(invoice_data))

        # Build PDF
        doc.build(story)

        return str(output_path)

    def _create_company_header(self, company_info: dict[str, str]) -> list:
        """Create company header section."""
        elements = []

        # Company name
        company_name = company_info.get('name', 'Company Name')
        elements.append(Paragraph(
            f'<font size="18"><b>{company_name}</b></font>',
            self.styles['Title']
        ))

        # Company address
        address_lines = []
        for field in ['address_line_1', 'address_line_2', 'city_state_zip']:
            if company_info.get(field):
                address_lines.append(company_info[field])

        if address_lines:
            address_text = '<br/>'.join(address_lines)
            elements.append(Paragraph(address_text, self.styles['Normal']))

        # Contact information
        contact_lines = []
        if company_info.get('phone'):
            contact_lines.append(f"Phone: {company_info['phone']}")
        if company_info.get('email'):
            contact_lines.append(f"Email: {company_info['email']}")

        if contact_lines:
            contact_text = ' | '.join(contact_lines)
            elements.append(Paragraph(contact_text, self.styles['Normal']))

        return elements

    def _create_invoice_header(self, invoice_data: dict[str, Any]) -> list:
        """Create invoice header with invoice number and date."""
        elements = []

        # Create two-column layout for invoice info
        invoice_info_data = [
            ['INVOICE', ''],
            [f'Invoice #: {invoice_data.get("invoice_number", "N/A")}', ''],
            [f'Issue Date: {self._format_date(invoice_data.get("issue_date"))}', ''],
            [f'Due Date: {self._format_date(invoice_data.get("due_date"))}', ''],
        ]

        invoice_table = Table(invoice_info_data, colWidths=[3*72, 3*72])
        invoice_table.setStyle(TableStyle([
            ('FONT', (0, 0), (0, 0), 'Helvetica-Bold', 16),
            ('FONT', (0, 1), (0, 3), 'Helvetica', 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ]))

        elements.append(invoice_table)
        return elements

    def _create_customer_section(self, invoice_data: dict[str, Any]) -> list:
        """Create customer/bill-to section."""
        elements = []

        customer = invoice_data.get('customer', {})

        elements.append(Paragraph('<b>Bill To:</b>', self.styles['Heading2']))

        # Customer name
        customer_name = customer.get('name', customer.get('company_name', 'N/A'))
        elements.append(Paragraph(customer_name, self.styles['Normal']))

        # Customer address
        address_parts = []
        if customer.get('address_line_1'):
            address_parts.append(customer['address_line_1'])
        if customer.get('address_line_2'):
            address_parts.append(customer['address_line_2'])
        if customer.get('city'):
            city_line = customer['city']
            if customer.get('state'):
                city_line += f", {customer['state']}"
            if customer.get('zip_code'):
                city_line += f" {customer['zip_code']}"
            address_parts.append(city_line)

        for line in address_parts:
            elements.append(Paragraph(line, self.styles['Normal']))

        return elements

    def _create_line_items_table(self, invoice_data: dict[str, Any]) -> list:
        """Create line items table."""
        elements = []

        line_items = invoice_data.get('line_items', [])
        if not line_items:
            return elements

        # Table headers
        table_data = [
            ['Description', 'Quantity', 'Unit Price', 'Total']
        ]

        # Add line items
        for item in line_items:
            row = [
                item.get('description', ''),
                str(item.get('quantity', 1)),
                f"${self._format_currency(item.get('unit_price', 0))}",
                f"${self._format_currency(item.get('total', item.get('subtotal', 0)))}",
            ]
            table_data.append(row)

        # Create table
        line_items_table = Table(
            table_data,
            colWidths=[3.5*72, 0.75*72, 1*72, 1*72]
        )

        line_items_table.setStyle(TableStyle([
            # Header styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 10),

            # Data styling
            ('FONT', (0, 1), (-1, -1), 'Helvetica', 9),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),  # Right-align numbers
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),   # Left-align descriptions

            # Grid
            ('GRID', (0, 0), (-1, -1), 1, colors.black),

            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))

        elements.append(line_items_table)
        return elements

    def _create_totals_section(self, invoice_data: dict[str, Any]) -> list:
        """Create invoice totals section."""
        elements = []

        # Create totals table (right-aligned)
        totals_data = []

        if invoice_data.get('subtotal'):
            totals_data.append(['Subtotal:', f"${self._format_currency(invoice_data['subtotal'])}"])

        if invoice_data.get('tax_amount'):
            totals_data.append(['Tax:', f"${self._format_currency(invoice_data['tax_amount'])}"])

        if invoice_data.get('discount_amount'):
            totals_data.append(['Discount:', f"-${self._format_currency(invoice_data['discount_amount'])}"])

        # Total (bold)
        total_amount = invoice_data.get('total', 0)
        totals_data.append(['<b>Total:</b>', f"<b>${self._format_currency(total_amount)}</b>"])

        totals_table = Table(totals_data, colWidths=[1.5*72, 1.5*72])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONT', (0, 0), (-1, -2), 'Helvetica', 10),
            ('FONT', (0, -1), (-1, -1), 'Helvetica-Bold', 12),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.black),
        ]))

        # Create container to right-align the totals table
        container_data = [['', totals_table]]
        container = Table(container_data, colWidths=[4.5*72, 2*72])
        container.setStyle(TableStyle([
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        elements.append(container)
        return elements

    def _create_payment_section(self, invoice_data: dict[str, Any]) -> list:
        """Create payment terms and instructions section."""
        elements = []

        if invoice_data.get('payment_terms'):
            elements.append(Paragraph('<b>Payment Terms:</b>', self.styles['Heading3']))
            elements.append(Paragraph(invoice_data['payment_terms'], self.styles['Normal']))
            elements.append(Spacer(1, 6))

        if invoice_data.get('payment_instructions'):
            elements.append(Paragraph('<b>Payment Instructions:</b>', self.styles['Heading3']))
            elements.append(Paragraph(invoice_data['payment_instructions'], self.styles['Normal']))

        return elements

    def _create_footer(self, invoice_data: dict[str, Any]) -> list:
        """Create invoice footer."""
        elements = []

        footer_text = invoice_data.get('footer_text', 'Thank you for your business!')
        elements.append(Spacer(1, 24))
        elements.append(Paragraph(
            f'<i>{footer_text}</i>',
            self.styles['Normal']
        ))

        return elements

    def _format_date(self, date_value: Any) -> str:
        """Format date for display."""
        if date_value is None:
            return 'N/A'

        if hasattr(date_value, 'strftime'):
            return date_value.strftime('%B %d, %Y')

        return str(date_value)

    def _format_currency(self, amount: Any) -> str:
        """Format currency amount."""
        if amount is None:
            return '0.00'

        if isinstance(amount, Decimal):
            return str(amount.quantize(Decimal('0.01')))

        try:
            return f"{float(amount):.2f}"
        except (ValueError, TypeError):
            return '0.00'
