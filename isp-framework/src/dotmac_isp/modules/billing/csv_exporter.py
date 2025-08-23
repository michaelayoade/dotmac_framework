"""CSV export functionality for billing data."""

import csv
import io
import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, date
from decimal import Decimal

from dotmac_isp.modules.billing.models import (
    Invoice, InvoiceLineItem, Payment, Subscription, 
    BillingAccount, TaxRate, CreditNote, Receipt, LateFee
)


logger = logging.getLogger(__name__)


class BillingCSVExporter:
    """Export billing data to CSV format."""
    
    def __init__(self):
        self.date_format = "%Y-%m-%d"
        self.datetime_format = "%Y-%m-%d %H:%M:%S"
    
    def _format_value(self, value: Any) -> str:
        """Format value for CSV output."""
        if value is None:
            return ""
        elif isinstance(value, (date, datetime)):
            format_str = self.datetime_format if isinstance(value, datetime) else self.date_format
            return value.strftime(format_str)
        elif isinstance(value, Decimal):
            return str(float(value))
        elif isinstance(value, bool):
            return "Yes" if value else "No"
        elif hasattr(value, 'value'):  # Enum values
            return value.value
        else:
            return str(value)
    
    async def export_invoices(self, invoices: List[Invoice], 
                            include_line_items: bool = False) -> str:
        """Export invoices to CSV format."""
        output = io.StringIO()
        
        if include_line_items:
            # Detailed export with line items
            fieldnames = [
                'invoice_number', 'invoice_date', 'due_date', 'customer_id',
                'status', 'currency', 'subtotal', 'tax_amount', 'discount_amount',
                'total_amount', 'paid_amount', 'balance_due', 'is_overdue',
                'line_item_description', 'line_item_quantity', 'line_item_unit_price',
                'line_item_tax_rate', 'line_item_tax_amount', 'line_item_total',
                'service_instance_id', 'notes'
            ]
            
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            for invoice in invoices:
                base_row = {
                    'invoice_number': invoice.invoice_number,
                    'invoice_date': self._format_value(invoice.invoice_date),
                    'due_date': self._format_value(invoice.due_date),
                    'customer_id': str(invoice.customer_id),
                    'status': self._format_value(invoice.status),
                    'currency': invoice.currency,
                    'subtotal': self._format_value(invoice.subtotal),
                    'tax_amount': self._format_value(invoice.tax_amount),
                    'discount_amount': self._format_value(invoice.discount_amount),
                    'total_amount': self._format_value(invoice.total_amount),
                    'paid_amount': self._format_value(invoice.paid_amount),
                    'balance_due': self._format_value(invoice.balance_due),
                    'is_overdue': self._format_value(invoice.is_overdue),
                    'notes': invoice.notes or ""
                }
                
                if invoice.line_items:
                    for item in invoice.line_items:
                        row = base_row.copy()
                        row.update({
                            'line_item_description': item.description,
                            'line_item_quantity': self._format_value(item.quantity),
                            'line_item_unit_price': self._format_value(item.unit_price),
                            'line_item_tax_rate': self._format_value(item.tax_rate),
                            'line_item_tax_amount': self._format_value(item.tax_amount),
                            'line_item_total': self._format_value(item.line_total),
                            'service_instance_id': str(item.service_instance_id) if item.service_instance_id else ""
                        })
                        writer.writerow(row)
                else:
                    # Invoice without line items
                    writer.writerow(base_row)
        else:
            # Summary export without line items
            fieldnames = [
                'invoice_number', 'invoice_date', 'due_date', 'customer_id',
                'status', 'currency', 'subtotal', 'tax_amount', 'discount_amount',
                'total_amount', 'paid_amount', 'balance_due', 'is_overdue',
                'paid_date', 'notes'
            ]
            
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            for invoice in invoices:
                writer.writerow({
                    'invoice_number': invoice.invoice_number,
                    'invoice_date': self._format_value(invoice.invoice_date),
                    'due_date': self._format_value(invoice.due_date),
                    'customer_id': str(invoice.customer_id),
                    'status': self._format_value(invoice.status),
                    'currency': invoice.currency,
                    'subtotal': self._format_value(invoice.subtotal),
                    'tax_amount': self._format_value(invoice.tax_amount),
                    'discount_amount': self._format_value(invoice.discount_amount),
                    'total_amount': self._format_value(invoice.total_amount),
                    'paid_amount': self._format_value(invoice.paid_amount),
                    'balance_due': self._format_value(invoice.balance_due),
                    'is_overdue': self._format_value(invoice.is_overdue),
                    'paid_date': self._format_value(invoice.paid_date),
                    'notes': invoice.notes or ""
                })
        
        content = output.getvalue()
        output.close()
        return content
    
    async def export_payments(self, payments: List[Payment]) -> str:
        """Export payments to CSV format."""
        output = io.StringIO()
        
        fieldnames = [
            'payment_number', 'invoice_id', 'amount', 'payment_date',
            'payment_method', 'status', 'transaction_id', 'reference_number',
            'failure_reason', 'notes'
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for payment in payments:
            writer.writerow({
                'payment_number': payment.payment_number,
                'invoice_id': str(payment.invoice_id),
                'amount': self._format_value(payment.amount),
                'payment_date': self._format_value(payment.payment_date),
                'payment_method': self._format_value(payment.payment_method),
                'status': self._format_value(payment.status),
                'transaction_id': payment.transaction_id or "",
                'reference_number': payment.reference_number or "",
                'failure_reason': payment.failure_reason or "",
                'notes': payment.notes or ""
            })
        
        content = output.getvalue()
        output.close()
        return content
    
    async def export_subscriptions(self, subscriptions: List[Subscription]) -> str:
        """Export subscriptions to CSV format."""
        output = io.StringIO()
        
        fieldnames = [
            'id', 'customer_id', 'service_instance_id', 'billing_cycle',
            'amount', 'currency', 'start_date', 'end_date', 'next_billing_date',
            'is_active', 'auto_renew', 'created_at', 'updated_at'
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for subscription in subscriptions:
            writer.writerow({
                'id': str(subscription.id),
                'customer_id': str(subscription.customer_id),
                'service_instance_id': str(subscription.service_instance_id),
                'billing_cycle': self._format_value(subscription.billing_cycle),
                'amount': self._format_value(subscription.amount),
                'currency': subscription.currency,
                'start_date': self._format_value(subscription.start_date),
                'end_date': self._format_value(subscription.end_date),
                'next_billing_date': self._format_value(subscription.next_billing_date),
                'is_active': self._format_value(subscription.is_active),
                'auto_renew': self._format_value(subscription.auto_renew),
                'created_at': self._format_value(subscription.created_at),
                'updated_at': self._format_value(subscription.updated_at)
            })
        
        content = output.getvalue()
        output.close()
        return content
    
    async def export_credit_notes(self, credit_notes: List[CreditNote]) -> str:
        """Export credit notes to CSV format."""
        output = io.StringIO()
        
        fieldnames = [
            'credit_note_number', 'customer_id', 'invoice_id', 'amount',
            'reason', 'credit_date', 'is_applied', 'applied_date',
            'created_at', 'updated_at'
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for credit_note in credit_notes:
            writer.writerow({
                'credit_note_number': credit_note.credit_note_number,
                'customer_id': str(credit_note.customer_id),
                'invoice_id': str(credit_note.invoice_id) if credit_note.invoice_id else "",
                'amount': self._format_value(credit_note.amount),
                'reason': credit_note.reason,
                'credit_date': self._format_value(credit_note.credit_date),
                'is_applied': self._format_value(credit_note.is_applied),
                'applied_date': self._format_value(credit_note.applied_date),
                'created_at': self._format_value(credit_note.created_at),
                'updated_at': self._format_value(credit_note.updated_at)
            })
        
        content = output.getvalue()
        output.close()
        return content
    
    async def export_late_fees(self, late_fees: List[LateFee]) -> str:
        """Export late fees to CSV format."""
        output = io.StringIO()
        
        fieldnames = [
            'id', 'invoice_id', 'customer_id', 'fee_amount', 'fee_date',
            'days_overdue', 'is_waived', 'waived_date', 'waived_reason',
            'created_at', 'updated_at'
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for fee in late_fees:
            writer.writerow({
                'id': str(fee.id),
                'invoice_id': str(fee.invoice_id),
                'customer_id': str(fee.customer_id),
                'fee_amount': self._format_value(fee.fee_amount),
                'fee_date': self._format_value(fee.fee_date),
                'days_overdue': fee.days_overdue,
                'is_waived': self._format_value(fee.is_waived),
                'waived_date': self._format_value(fee.waived_date),
                'waived_reason': fee.waived_reason or "",
                'created_at': self._format_value(fee.created_at),
                'updated_at': self._format_value(fee.updated_at)
            })
        
        content = output.getvalue()
        output.close()
        return content
    
    async def export_receipts(self, receipts: List[Receipt]) -> str:
        """Export receipts to CSV format."""
        output = io.StringIO()
        
        fieldnames = [
            'receipt_number', 'payment_id', 'issued_at', 'amount',
            'payment_method', 'customer_name', 'invoice_number',
            'created_at', 'updated_at'
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for receipt in receipts:
            writer.writerow({
                'receipt_number': receipt.receipt_number,
                'payment_id': str(receipt.payment_id),
                'issued_at': self._format_value(receipt.issued_at),
                'amount': self._format_value(receipt.amount),
                'payment_method': self._format_value(receipt.payment_method),
                'customer_name': receipt.customer_name,
                'invoice_number': receipt.invoice_number,
                'created_at': self._format_value(receipt.created_at),
                'updated_at': self._format_value(receipt.updated_at)
            })
        
        content = output.getvalue()
        output.close()
        return content


class FinancialReportExporter:
    """Export financial reports in CSV format."""
    
    def __init__(self):
        self.exporter = BillingCSVExporter()
    
    async def export_revenue_report(self, data: List[Dict[str, Any]]) -> str:
        """Export revenue report data."""
        output = io.StringIO()
        
        fieldnames = [
            'period', 'total_revenue', 'subscription_revenue', 'one_time_revenue',
            'tax_collected', 'refunds', 'net_revenue', 'invoice_count',
            'payment_count', 'average_invoice_value'
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in data:
            writer.writerow({
                'period': row.get('period', ''),
                'total_revenue': self.exporter._format_value(row.get('total_revenue', 0)),
                'subscription_revenue': self.exporter._format_value(row.get('subscription_revenue', 0)),
                'one_time_revenue': self.exporter._format_value(row.get('one_time_revenue', 0)),
                'tax_collected': self.exporter._format_value(row.get('tax_collected', 0)),
                'refunds': self.exporter._format_value(row.get('refunds', 0)),
                'net_revenue': self.exporter._format_value(row.get('net_revenue', 0)),
                'invoice_count': row.get('invoice_count', 0),
                'payment_count': row.get('payment_count', 0),
                'average_invoice_value': self.exporter._format_value(row.get('average_invoice_value', 0))
            })
        
        content = output.getvalue()
        output.close()
        return content
    
    async def export_aging_report(self, data: List[Dict[str, Any]]) -> str:
        """Export accounts receivable aging report."""
        output = io.StringIO()
        
        fieldnames = [
            'customer_id', 'customer_name', 'total_outstanding',
            'current', 'days_1_30', 'days_31_60', 'days_61_90', 'days_90_plus',
            'oldest_invoice_date', 'contact_email', 'contact_phone'
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in data:
            writer.writerow({
                'customer_id': str(row.get('customer_id', '')),
                'customer_name': row.get('customer_name', ''),
                'total_outstanding': self.exporter._format_value(row.get('total_outstanding', 0)),
                'current': self.exporter._format_value(row.get('current', 0)),
                'days_1_30': self.exporter._format_value(row.get('days_1_30', 0)),
                'days_31_60': self.exporter._format_value(row.get('days_31_60', 0)),
                'days_61_90': self.exporter._format_value(row.get('days_61_90', 0)),
                'days_90_plus': self.exporter._format_value(row.get('days_90_plus', 0)),
                'oldest_invoice_date': self.exporter._format_value(row.get('oldest_invoice_date')),
                'contact_email': row.get('contact_email', ''),
                'contact_phone': row.get('contact_phone', '')
            })
        
        content = output.getvalue()
        output.close()
        return content
    
    async def export_tax_report(self, data: List[Dict[str, Any]]) -> str:
        """Export tax collection report."""
        output = io.StringIO()
        
        fieldnames = [
            'period', 'tax_type', 'jurisdiction', 'taxable_amount',
            'tax_rate', 'tax_collected', 'invoice_count'
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in data:
            writer.writerow({
                'period': row.get('period', ''),
                'tax_type': row.get('tax_type', ''),
                'jurisdiction': row.get('jurisdiction', ''),
                'taxable_amount': self.exporter._format_value(row.get('taxable_amount', 0)),
                'tax_rate': self.exporter._format_value(row.get('tax_rate', 0)),
                'tax_collected': self.exporter._format_value(row.get('tax_collected', 0)),
                'invoice_count': row.get('invoice_count', 0)
            })
        
        content = output.getvalue()
        output.close()
        return content


class CSVBatchExporter:
    """Handle batch CSV exports."""
    
    def __init__(self):
        self.billing_exporter = BillingCSVExporter()
        self.financial_exporter = FinancialReportExporter()
    
    async def export_complete_billing_data(self, 
                                         invoices: List[Invoice],
                                         payments: List[Payment],
                                         subscriptions: List[Subscription],
                                         credit_notes: List[CreditNote]) -> Dict[str, str]:
        """Export complete billing dataset."""
        results = {}
        
        try:
            results['invoices'] = await self.billing_exporter.export_invoices(invoices, include_line_items=True)
            logger.info(f"Exported {len(invoices)} invoices to CSV")
        except Exception as e:
            logger.error(f"Failed to export invoices: {e}")
            results['invoices'] = None
        
        try:
            results['payments'] = await self.billing_exporter.export_payments(payments)
            logger.info(f"Exported {len(payments)} payments to CSV")
        except Exception as e:
            logger.error(f"Failed to export payments: {e}")
            results['payments'] = None
        
        try:
            results['subscriptions'] = await self.billing_exporter.export_subscriptions(subscriptions)
            logger.info(f"Exported {len(subscriptions)} subscriptions to CSV")
        except Exception as e:
            logger.error(f"Failed to export subscriptions: {e}")
            results['subscriptions'] = None
        
        try:
            results['credit_notes'] = await self.billing_exporter.export_credit_notes(credit_notes)
            logger.info(f"Exported {len(credit_notes)} credit notes to CSV")
        except Exception as e:
            logger.error(f"Failed to export credit notes: {e}")
            results['credit_notes'] = None
        
        return results
    
    async def export_monthly_reports(self, 
                                   revenue_data: List[Dict[str, Any]],
                                   aging_data: List[Dict[str, Any]],
                                   tax_data: List[Dict[str, Any]]) -> Dict[str, str]:
        """Export monthly financial reports."""
        results = {}
        
        try:
            results['revenue_report'] = await self.financial_exporter.export_revenue_report(revenue_data)
            logger.info("Exported revenue report to CSV")
        except Exception as e:
            logger.error(f"Failed to export revenue report: {e}")
            results['revenue_report'] = None
        
        try:
            results['aging_report'] = await self.financial_exporter.export_aging_report(aging_data)
            logger.info("Exported aging report to CSV")
        except Exception as e:
            logger.error(f"Failed to export aging report: {e}")
            results['aging_report'] = None
        
        try:
            results['tax_report'] = await self.financial_exporter.export_tax_report(tax_data)
            logger.info("Exported tax report to CSV")
        except Exception as e:
            logger.error(f"Failed to export tax report: {e}")
            results['tax_report'] = None
        
        return results


# Utility functions for external use
async def export_invoices_csv(invoices: List[Invoice], include_line_items: bool = False) -> str:
    """Convenience function to export invoices to CSV."""
    exporter = BillingCSVExporter()
    return await exporter.export_invoices(invoices, include_line_items)


async def export_payments_csv(payments: List[Payment]) -> str:
    """Convenience function to export payments to CSV."""
    exporter = BillingCSVExporter()
    return await exporter.export_payments(payments)


async def export_financial_report_csv(data: List[Dict[str, Any]], report_type: str) -> str:
    """Convenience function to export financial reports to CSV."""
    exporter = FinancialReportExporter()
    
    if report_type == 'revenue':
        return await exporter.export_revenue_report(data)
    elif report_type == 'aging':
        return await exporter.export_aging_report(data)
    elif report_type == 'tax':
        return await exporter.export_tax_report(data)
    else:
        raise ValueError(f"Unknown report type: {report_type}")