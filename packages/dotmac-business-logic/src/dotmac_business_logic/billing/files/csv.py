"""
CSV export functionality for billing data.

This module provides CSV export capabilities using only standard library,
making it always available without optional dependencies.
"""

import csv
from datetime import date, datetime
from decimal import Decimal
from io import StringIO
from pathlib import Path
from typing import Any, Union


class CSVExporter:
    """CSV exporter for billing data."""

    def __init__(self, encoding: str = 'utf-8', delimiter: str = ','):
        """
        Initialize CSV exporter.

        Args:
            encoding: File encoding
            delimiter: CSV delimiter character
        """
        self.encoding = encoding
        self.delimiter = delimiter

    def export_usage_data(
        self,
        usage_data: list[dict[str, Any]],
        output_path: Union[str, Path]
    ) -> str:
        """
        Export usage data to CSV file.

        Args:
            usage_data: List of usage records
            output_path: Output file path

        Returns:
            Path to generated file
        """
        if not usage_data:
            raise ValueError("No usage data to export")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Define standard columns for usage data
        fieldnames = [
            'subscription_id',
            'customer_id',
            'usage_date',
            'meter_type',
            'quantity',
            'unit',
            'service_identifier',
            'raw_value',
            'processed_value',
        ]

        with open(output_path, 'w', newline='', encoding=self.encoding) as csvfile:
            writer = csv.DictWriter(
                csvfile,
                fieldnames=fieldnames,
                delimiter=self.delimiter,
                extrasaction='ignore'
            )

            writer.writeheader()

            for record in usage_data:
                # Ensure consistent data formatting
                formatted_record = self._format_usage_record(record)
                writer.writerow(formatted_record)

        return str(output_path)

    def export_invoice_data(
        self,
        invoices: list[dict[str, Any]],
        output_path: Union[str, Path],
        include_line_items: bool = False,
    ) -> str:
        """
        Export invoice data to CSV.

        Args:
            invoices: List of invoice records
            output_path: Output file path
            include_line_items: Whether to include line item details

        Returns:
            Path to generated file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if include_line_items:
            return self._export_invoices_with_line_items(invoices, output_path)
        else:
            return self._export_invoice_summary(invoices, output_path)

    def export_payment_data(
        self,
        payments: list[dict[str, Any]],
        output_path: Union[str, Path],
    ) -> str:
        """
        Export payment data to CSV.

        Args:
            payments: List of payment records
            output_path: Output file path

        Returns:
            Path to generated file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            'payment_id',
            'invoice_id',
            'customer_id',
            'amount',
            'currency',
            'payment_date',
            'payment_method',
            'status',
            'transaction_id',
            'processor_fee',
            'net_amount',
        ]

        with open(output_path, 'w', newline='', encoding=self.encoding) as csvfile:
            writer = csv.DictWriter(
                csvfile,
                fieldnames=fieldnames,
                delimiter=self.delimiter,
                extrasaction='ignore'
            )

            writer.writeheader()

            for payment in payments:
                formatted_payment = self._format_payment_record(payment)
                writer.writerow(formatted_payment)

        return str(output_path)

    def export_subscription_summary(
        self,
        subscriptions: list[dict[str, Any]],
        output_path: Union[str, Path],
    ) -> str:
        """
        Export subscription summary to CSV.

        Args:
            subscriptions: List of subscription records
            output_path: Output file path

        Returns:
            Path to generated file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            'subscription_id',
            'customer_id',
            'plan_name',
            'status',
            'start_date',
            'current_period_start',
            'current_period_end',
            'next_billing_date',
            'monthly_revenue',
            'billing_cycle',
            'trial_end_date',
        ]

        with open(output_path, 'w', newline='', encoding=self.encoding) as csvfile:
            writer = csv.DictWriter(
                csvfile,
                fieldnames=fieldnames,
                delimiter=self.delimiter,
                extrasaction='ignore'
            )

            writer.writeheader()

            for subscription in subscriptions:
                formatted_sub = self._format_subscription_record(subscription)
                writer.writerow(formatted_sub)

        return str(output_path)

    def create_csv_string(self, data: list[dict[str, Any]], fieldnames: list[str]) -> str:
        """
        Create CSV content as string without writing to file.

        Args:
            data: List of records
            fieldnames: Column names

        Returns:
            CSV content as string
        """
        output = StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=fieldnames,
            delimiter=self.delimiter,
            extrasaction='ignore'
        )

        writer.writeheader()
        for record in data:
            writer.writerow(record)

        return output.getvalue()

    def _format_usage_record(self, record: dict[str, Any]) -> dict[str, str]:
        """Format usage record for CSV export."""
        return {
            'subscription_id': str(record.get('subscription_id', '')),
            'customer_id': str(record.get('customer_id', '')),
            'usage_date': self._format_date(record.get('recorded_at', record.get('usage_date'))),
            'meter_type': str(record.get('meter_type', record.get('service_type', ''))),
            'quantity': self._format_decimal(record.get('quantity', 0)),
            'unit': str(record.get('unit', record.get('usage_unit', 'units'))),
            'service_identifier': str(record.get('service_identifier', '')),
            'raw_value': self._format_decimal(record.get('raw_value', record.get('quantity', 0))),
            'processed_value': self._format_decimal(record.get('processed_value', record.get('quantity', 0))),
        }

    def _format_payment_record(self, record: dict[str, Any]) -> dict[str, str]:
        """Format payment record for CSV export."""
        return {
            'payment_id': str(record.get('id', record.get('payment_id', ''))),
            'invoice_id': str(record.get('invoice_id', '')),
            'customer_id': str(record.get('customer_id', '')),
            'amount': self._format_decimal(record.get('amount', 0)),
            'currency': str(record.get('currency', 'USD')),
            'payment_date': self._format_datetime(record.get('payment_date', record.get('created_at'))),
            'payment_method': str(record.get('payment_method', '')),
            'status': str(record.get('status', '')),
            'transaction_id': str(record.get('transaction_id', record.get('gateway_transaction_id', ''))),
            'processor_fee': self._format_decimal(record.get('processing_fee', 0)),
            'net_amount': self._format_decimal(record.get('net_amount', record.get('amount', 0))),
        }

    def _format_subscription_record(self, record: dict[str, Any]) -> dict[str, str]:
        """Format subscription record for CSV export."""
        return {
            'subscription_id': str(record.get('id', record.get('subscription_id', ''))),
            'customer_id': str(record.get('customer_id', '')),
            'plan_name': str(record.get('plan_name', record.get('billing_plan', {}).get('name', ''))),
            'status': str(record.get('status', '')),
            'start_date': self._format_date(record.get('start_date')),
            'current_period_start': self._format_date(record.get('current_period_start')),
            'current_period_end': self._format_date(record.get('current_period_end')),
            'next_billing_date': self._format_date(record.get('next_billing_date')),
            'monthly_revenue': self._format_decimal(record.get('monthly_price', record.get('amount', 0))),
            'billing_cycle': str(record.get('billing_cycle', '')),
            'trial_end_date': self._format_date(record.get('trial_end_date')),
        }

    def _export_invoice_summary(self, invoices: list[dict], output_path: Path) -> str:
        """Export invoice summary without line items."""
        fieldnames = [
            'invoice_id',
            'invoice_number',
            'customer_id',
            'subscription_id',
            'issue_date',
            'due_date',
            'status',
            'subtotal',
            'tax_amount',
            'total',
            'currency',
            'billing_period_start',
            'billing_period_end',
        ]

        with open(output_path, 'w', newline='', encoding=self.encoding) as csvfile:
            writer = csv.DictWriter(
                csvfile,
                fieldnames=fieldnames,
                delimiter=self.delimiter,
                extrasaction='ignore'
            )

            writer.writeheader()

            for invoice in invoices:
                formatted_invoice = {
                    'invoice_id': str(invoice.get('id', invoice.get('invoice_id', ''))),
                    'invoice_number': str(invoice.get('invoice_number', '')),
                    'customer_id': str(invoice.get('customer_id', '')),
                    'subscription_id': str(invoice.get('subscription_id', '')),
                    'issue_date': self._format_date(invoice.get('issue_date')),
                    'due_date': self._format_date(invoice.get('due_date')),
                    'status': str(invoice.get('status', '')),
                    'subtotal': self._format_decimal(invoice.get('subtotal', 0)),
                    'tax_amount': self._format_decimal(invoice.get('tax_amount', 0)),
                    'total': self._format_decimal(invoice.get('total', 0)),
                    'currency': str(invoice.get('currency', 'USD')),
                    'billing_period_start': self._format_date(invoice.get('billing_period_start')),
                    'billing_period_end': self._format_date(invoice.get('billing_period_end')),
                }
                writer.writerow(formatted_invoice)

        return str(output_path)

    def _export_invoices_with_line_items(self, invoices: list[dict], output_path: Path) -> str:
        """Export invoices with expanded line items."""
        fieldnames = [
            'invoice_id',
            'invoice_number',
            'customer_id',
            'line_item_id',
            'line_description',
            'line_quantity',
            'line_unit_price',
            'line_subtotal',
            'line_tax_amount',
            'line_total',
            'invoice_total',
            'invoice_status',
            'issue_date',
            'due_date',
        ]

        with open(output_path, 'w', newline='', encoding=self.encoding) as csvfile:
            writer = csv.DictWriter(
                csvfile,
                fieldnames=fieldnames,
                delimiter=self.delimiter,
                extrasaction='ignore'
            )

            writer.writeheader()

            for invoice in invoices:
                line_items = invoice.get('line_items', [])
                if not line_items:
                    # Create single row for invoice without line items
                    row = self._format_invoice_line_row(invoice, {})
                    writer.writerow(row)
                else:
                    # Create row for each line item
                    for line_item in line_items:
                        row = self._format_invoice_line_row(invoice, line_item)
                        writer.writerow(row)

        return str(output_path)

    def _format_invoice_line_row(self, invoice: dict, line_item: dict) -> dict[str, str]:
        """Format invoice + line item for expanded CSV."""
        return {
            'invoice_id': str(invoice.get('id', invoice.get('invoice_id', ''))),
            'invoice_number': str(invoice.get('invoice_number', '')),
            'customer_id': str(invoice.get('customer_id', '')),
            'line_item_id': str(line_item.get('id', '')),
            'line_description': str(line_item.get('description', '')),
            'line_quantity': self._format_decimal(line_item.get('quantity', 0)),
            'line_unit_price': self._format_decimal(line_item.get('unit_price', 0)),
            'line_subtotal': self._format_decimal(line_item.get('subtotal', 0)),
            'line_tax_amount': self._format_decimal(line_item.get('tax_amount', 0)),
            'line_total': self._format_decimal(line_item.get('total', 0)),
            'invoice_total': self._format_decimal(invoice.get('total', 0)),
            'invoice_status': str(invoice.get('status', '')),
            'issue_date': self._format_date(invoice.get('issue_date')),
            'due_date': self._format_date(invoice.get('due_date')),
        }

    def _format_date(self, value: Any) -> str:
        """Format date value for CSV."""
        if value is None:
            return ''
        if isinstance(value, (date, datetime)):
            return value.strftime('%Y-%m-%d')
        return str(value)

    def _format_datetime(self, value: Any) -> str:
        """Format datetime value for CSV."""
        if value is None:
            return ''
        if isinstance(value, datetime):
            return value.strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(value, date):
            return value.strftime('%Y-%m-%d')
        return str(value)

    def _format_decimal(self, value: Any) -> str:
        """Format decimal/numeric value for CSV."""
        if value is None:
            return '0.00'
        if isinstance(value, Decimal):
            return str(value.quantize(Decimal('0.01')))
        try:
            return f"{float(value):.2f}"
        except (ValueError, TypeError):
            return '0.00'
