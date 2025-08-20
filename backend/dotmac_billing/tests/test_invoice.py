"""Tests for invoice management."""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal


class TestInvoiceGeneration:
    """Test invoice generation functionality."""

    def test_calculate_invoice_total(self, sample_invoice):
        """Test invoice total calculation."""
        subtotal = sum(item["amount"] for item in sample_invoice["line_items"])
        tax = subtotal * sample_invoice["tax_rate"]
        total = subtotal + tax

        assert subtotal == sample_invoice["subtotal"]
        assert abs(tax - sample_invoice["tax_amount"]) < Decimal("0.01")
        assert abs(total - sample_invoice["total"]) < Decimal("0.01")

    def test_apply_discount(self, sample_invoice):
        """Test discount application to invoice."""
        discount_rate = Decimal("0.15")  # 15% discount
        original_total = sample_invoice["total"]
        discount_amount = original_total * discount_rate
        discounted_total = original_total - discount_amount

        assert discount_amount > 0
        assert discounted_total < original_total
        assert discounted_total == original_total * (1 - discount_rate)

    def test_invoice_due_date_calculation(self, sample_invoice):
        """Test due date calculation based on payment terms."""
        payment_terms = {
            "net30": 30,
            "net60": 60,
            "net90": 90,
            "due_on_receipt": 0
        }

        for term, days in payment_terms.items():
            due_date = sample_invoice["invoice_date"] + timedelta(days=days)
            if term == "net30":
                assert due_date == sample_invoice["due_date"]

    @pytest.mark.asyncio
    async def test_generate_invoice_pdf(self, sample_invoice, mock_invoice_generator):
        """Test PDF generation for invoice."""
        pdf_content = mock_invoice_generator.generate_pdf(sample_invoice)

        assert pdf_content is not None
        assert len(pdf_content) > 0
        assert mock_invoice_generator.generate_pdf.called

    def test_invoice_numbering_sequence(self):
        """Test invoice number generation sequence."""
        year = datetime.now().year
        sequence_numbers = []

        for i in range(1, 11):
            invoice_number = f"INV-{year}-{i:04d}"
            sequence_numbers.append(invoice_number)

        assert len(sequence_numbers) == 10
        assert sequence_numbers[0] == f"INV-{year}-0001"
        assert sequence_numbers[-1] == f"INV-{year}-0010"

    def test_recurring_invoice_generation(self, sample_subscription):
        """Test generation of recurring invoices from subscription."""
        invoice = {
            "customer_id": sample_subscription["customer_id"],
            "subscription_id": sample_subscription["id"],
            "amount": sample_subscription["price"],
            "billing_cycle": sample_subscription["billing_cycle"],
            "auto_generated": True
        }

        assert invoice["amount"] == sample_subscription["price"]
        assert invoice["billing_cycle"] == "monthly"
        assert invoice["auto_generated"] is True


class TestInvoiceManagement:
    """Test invoice management operations."""

    @pytest.mark.asyncio
    async def test_create_invoice(self, sample_invoice, mock_database):
        """Test invoice creation."""
        mock_database.execute.return_value = {"rows_affected": 1}
        mock_database.fetch_one.return_value = {**sample_invoice, "id": "INV-NEW-001"}

        result = await mock_database.fetch_one()

        assert result["id"] is not None
        assert result["status"] == "pending"
        assert result["customer_id"] == sample_invoice["customer_id"]

    @pytest.mark.asyncio
    async def test_update_invoice_status(self, sample_invoice, mock_database):
        """Test updating invoice status."""
        status_transitions = [
            ("pending", "sent"),
            ("sent", "viewed"),
            ("viewed", "paid"),
            ("paid", "closed")
        ]

        for from_status, to_status in status_transitions:
            mock_database.execute.return_value = {"rows_affected": 1}
            result = await mock_database.execute()
            assert result["rows_affected"] == 1

    @pytest.mark.asyncio
    async def test_void_invoice(self, sample_invoice, mock_database):
        """Test voiding an invoice."""
        void_reason = "Customer request"
        mock_database.execute.return_value = {"rows_affected": 1}

        result = await mock_database.execute()
        voided_invoice = {
            **sample_invoice,
            "status": "voided",
            "void_reason": void_reason,
            "voided_at": datetime.now()
        }

        assert result["rows_affected"] == 1
        assert voided_invoice["status"] == "voided"
        assert voided_invoice["void_reason"] == void_reason

    @pytest.mark.asyncio
    async def test_list_overdue_invoices(self, mock_database):
        """Test listing overdue invoices."""
        current_date = datetime.now()
        mock_database.fetch_all.return_value = [
            {"id": "INV-001", "due_date": current_date - timedelta(days=10), "total": Decimal("100.00")},
            {"id": "INV-002", "due_date": current_date - timedelta(days=5), "total": Decimal("200.00")},
        ]

        overdue_invoices = await mock_database.fetch_all()

        assert len(overdue_invoices) == 2
        assert all(inv["due_date"] < current_date for inv in overdue_invoices)

    def test_calculate_late_fees(self, sample_invoice):
        """Test late fee calculation."""
        days_overdue = 15
        late_fee_rate = Decimal("0.015")  # 1.5% per month

        late_fee = sample_invoice["total"] * late_fee_rate * (days_overdue / 30)

        assert late_fee > 0
        assert late_fee == sample_invoice["total"] * late_fee_rate * (days_overdue / 30)


class TestInvoiceNotifications:
    """Test invoice notification functionality."""

    @pytest.mark.asyncio
    async def test_send_invoice_email(self, sample_invoice, sample_customer, mock_email_service):
        """Test sending invoice via email."""
        email_data = {
            "to": sample_customer["email"],
            "subject": f"Invoice {sample_invoice['id']}",
            "template": "invoice_notification",
            "data": sample_invoice
        }

        result = await mock_email_service.send(email_data)

        assert result["sent"] is True
        assert result["message_id"] is not None
        mock_email_service.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_payment_reminder(self, sample_invoice, mock_email_service):
        """Test sending payment reminder."""
        reminders = [
            {"days_before_due": 7, "template": "payment_reminder_7_days"},
            {"days_before_due": 3, "template": "payment_reminder_3_days"},
            {"days_before_due": 1, "template": "payment_reminder_1_day"},
        ]

        for reminder in reminders:
            result = await mock_email_service.send(reminder)
            assert result["sent"] is True

    @pytest.mark.asyncio
    async def test_send_overdue_notice(self, sample_invoice, mock_email_service):
        """Test sending overdue notice."""
        overdue_notice = {
            "invoice_id": sample_invoice["id"],
            "days_overdue": 5,
            "template": "overdue_notice",
            "include_late_fee": True
        }

        result = await mock_email_service.send(overdue_notice)

        assert result["sent"] is True
        mock_email_service.send.assert_called()

    @pytest.mark.asyncio
    async def test_bulk_invoice_sending(self, mock_database, mock_email_service):
        """Test sending invoices in bulk."""
        mock_database.fetch_all.return_value = [
            {"id": f"INV-{i:03d}", "customer_email": f"customer{i}@example.com"}
            for i in range(1, 11)
        ]

        invoices = await mock_database.fetch_all()
        result = await mock_email_service.send_bulk(invoices)

        assert result["sent"] == 10
        assert result["failed"] == 0
