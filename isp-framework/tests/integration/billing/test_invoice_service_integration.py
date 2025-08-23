"""Integration tests for invoice domain service."""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from dotmac_isp.modules.billing.domain.invoice_service import InvoiceService
from dotmac_isp.modules.billing.domain.calculation_service import BillingCalculationService
from dotmac_isp.modules.billing.repository import InvoiceRepository, InvoiceLineItemRepository
from dotmac_isp.modules.billing import schemas
from dotmac_isp.modules.billing.models import InvoiceStatus
from dotmac_isp.shared.exceptions import ValidationError, NotFoundError, ServiceError


@pytest.mark.integration
@pytest.mark.billing
class TestInvoiceServiceIntegration:
    """Integration tests for invoice service with real database."""
    
    @pytest.fixture
    async def tenant_id(self):
        """Test tenant ID."""
        return uuid4()
    
    @pytest.fixture
    async def invoice_service(self, db_session: AsyncSession, tenant_id):
        """Invoice service instance with real repositories."""
        invoice_repo = InvoiceRepository(db_session, tenant_id)
        line_item_repo = InvoiceLineItemRepository(db_session, tenant_id)
        calculation_service = BillingCalculationService()
        
        return InvoiceService(
            invoice_repo=invoice_repo,
            line_item_repo=line_item_repo,
            calculation_service=calculation_service,
            tenant_id=tenant_id
        )
    
    @pytest.fixture
    def sample_invoice_data(self):
        """Sample invoice creation data."""
        return schemas.InvoiceCreate(
            customer_id=uuid4(),
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            line_items=[
                schemas.InvoiceLineItemCreate(
                    description="Internet Service - Monthly",
                    quantity=Decimal('1.0'),
                    unit_price=Decimal('99.99')
                ),
                schemas.InvoiceLineItemCreate(
                    description="Setup Fee",
                    quantity=Decimal('1.0'),
                    unit_price=Decimal('50.00')
                )
            ],
            tax_rate=Decimal('0.085'),  # 8.5%
            discount_rate=Decimal('0.10'),  # 10%
            currency='USD',
            notes='Test invoice',
            terms='Net 30'
        )
    
    async def test_create_invoice_end_to_end(self, invoice_service, sample_invoice_data):
        """Test complete invoice creation workflow."""
        # Create invoice
        invoice = await invoice_service.create_invoice(sample_invoice_data)
        
        # Verify invoice was created
        assert invoice is not None
        assert invoice.customer_id == sample_invoice_data.customer_id
        assert invoice.status == InvoiceStatus.DRAFT
        assert invoice.currency == 'USD'
        assert invoice.notes == 'Test invoice'
        assert invoice.terms == 'Net 30'
        
        # Verify calculations
        # Subtotal: 99.99 + 50.00 = 149.99
        # Tax: 149.99 * 0.085 = 12.75 (rounded)
        # Discount: 149.99 * 0.10 = 15.00 (rounded)
        # Total: 149.99 + 12.75 - 15.00 = 147.74
        assert invoice.subtotal == Decimal('149.99')
        assert invoice.tax_amount == Decimal('12.75')
        assert invoice.discount_amount == Decimal('15.00')
        assert invoice.total_amount == Decimal('147.74')
        assert invoice.amount_due == Decimal('147.74')
        assert invoice.amount_paid == Decimal('0.00')
        
        # Verify line items were created
        line_items = invoice_service.line_item_repo.get_by_invoice_id(invoice.id)
        assert len(line_items) == 2
        
        # Verify first line item
        internet_item = next((item for item in line_items if 'Internet Service' in item.description), None)
        assert internet_item is not None
        assert internet_item.quantity == Decimal('1.0')
        assert internet_item.unit_price == Decimal('99.99')
        assert internet_item.line_total == Decimal('99.99')
        
        # Verify second line item
        setup_item = next((item for item in line_items if 'Setup Fee' in item.description), None)
        assert setup_item is not None
        assert setup_item.quantity == Decimal('1.0')
        assert setup_item.unit_price == Decimal('50.00')
        assert setup_item.line_total == Decimal('50.00')
    
    async def test_create_invoice_with_complex_calculations(self, invoice_service):
        """Test invoice creation with complex line items and calculations."""
        invoice_data = schemas.InvoiceCreate(
            customer_id=uuid4(),
            line_items=[
                schemas.InvoiceLineItemCreate(
                    description="Service A",
                    quantity=Decimal('2.5'),
                    unit_price=Decimal('39.95')
                ),
                schemas.InvoiceLineItemCreate(
                    description="Service B",
                    quantity=Decimal('0.5'),
                    unit_price=Decimal('199.99')
                ),
                schemas.InvoiceLineItemCreate(
                    description="Service C",
                    quantity=Decimal('3.0'),
                    unit_price=Decimal('29.99')
                )
            ],
            tax_rate=Decimal('0.0875'),  # 8.75%
            discount_rate=Decimal('0.05')  # 5%
        )
        
        invoice = await invoice_service.create_invoice(invoice_data)
        
        # Verify calculations
        # Subtotal: (2.5 * 39.95) + (0.5 * 199.99) + (3.0 * 29.99) = 99.88 + 100.00 + 89.97 = 289.85
        # Tax: 289.85 * 0.0875 = 25.36 (rounded)
        # Discount: 289.85 * 0.05 = 14.49 (rounded)
        # Total: 289.85 + 25.36 - 14.49 = 300.72
        assert invoice.subtotal == Decimal('289.85')
        assert invoice.tax_amount == Decimal('25.36')
        assert invoice.discount_amount == Decimal('14.49')
        assert invoice.total_amount == Decimal('300.72')
    
    async def test_get_invoice_by_id(self, invoice_service, sample_invoice_data):
        """Test retrieving invoice by ID."""
        # Create invoice first
        created_invoice = await invoice_service.create_invoice(sample_invoice_data)
        
        # Retrieve invoice
        retrieved_invoice = await invoice_service.get_invoice(created_invoice.id)
        
        # Verify retrieved invoice matches created invoice
        assert retrieved_invoice.id == created_invoice.id
        assert retrieved_invoice.customer_id == created_invoice.customer_id
        assert retrieved_invoice.total_amount == created_invoice.total_amount
        assert retrieved_invoice.status == created_invoice.status
    
    async def test_get_nonexistent_invoice_raises_not_found(self, invoice_service):
        """Test that retrieving non-existent invoice raises NotFoundError."""
        nonexistent_id = uuid4()
        
        with pytest.raises(NotFoundError) as exc_info:
            await invoice_service.get_invoice(nonexistent_id)
        
        assert str(nonexistent_id) in str(exc_info.value)
    
    async def test_update_invoice_status_workflow(self, invoice_service, sample_invoice_data):
        """Test invoice status update workflow."""
        # Create invoice
        invoice = await invoice_service.create_invoice(sample_invoice_data)
        assert invoice.status == InvoiceStatus.DRAFT
        
        # Update to pending
        updated_invoice = await invoice_service.update_invoice_status(invoice.id, InvoiceStatus.PENDING)
        assert updated_invoice.status == InvoiceStatus.PENDING
        
        # Update to sent
        updated_invoice = await invoice_service.update_invoice_status(invoice.id, InvoiceStatus.SENT)
        assert updated_invoice.status == InvoiceStatus.SENT
        
        # Update to paid
        updated_invoice = await invoice_service.update_invoice_status(invoice.id, InvoiceStatus.PAID)
        assert updated_invoice.status == InvoiceStatus.PAID
        assert updated_invoice.amount_paid == updated_invoice.total_amount
        assert updated_invoice.amount_due == Decimal('0.00')
        assert updated_invoice.paid_date is not None
    
    async def test_invalid_status_transition_raises_validation_error(self, invoice_service, sample_invoice_data):
        """Test that invalid status transitions raise ValidationError."""
        # Create invoice
        invoice = await invoice_service.create_invoice(sample_invoice_data)
        
        # Try invalid transition from DRAFT to PAID
        with pytest.raises(ValidationError) as exc_info:
            await invoice_service.update_invoice_status(invoice.id, InvoiceStatus.PAID)
        
        assert "Invalid status transition" in str(exc_info.value)
    
    async def test_get_customer_invoices(self, invoice_service):
        """Test retrieving invoices by customer ID."""
        customer_id = uuid4()
        
        # Create multiple invoices for the customer
        invoice_data_1 = schemas.InvoiceCreate(
            customer_id=customer_id,
            line_items=[
                schemas.InvoiceLineItemCreate(
                    description="Service 1",
                    quantity=Decimal('1.0'),
                    unit_price=Decimal('100.00')
                )
            ]
        )
        
        invoice_data_2 = schemas.InvoiceCreate(
            customer_id=customer_id,
            line_items=[
                schemas.InvoiceLineItemCreate(
                    description="Service 2",
                    quantity=Decimal('1.0'),
                    unit_price=Decimal('200.00')
                )
            ]
        )
        
        # Create another invoice for different customer
        invoice_data_3 = schemas.InvoiceCreate(
            customer_id=uuid4(),  # Different customer
            line_items=[
                schemas.InvoiceLineItemCreate(
                    description="Service 3",
                    quantity=Decimal('1.0'),
                    unit_price=Decimal('150.00')
                )
            ]
        )
        
        await invoice_service.create_invoice(invoice_data_1)
        await invoice_service.create_invoice(invoice_data_2)
        await invoice_service.create_invoice(invoice_data_3)
        
        # Retrieve invoices for the first customer
        customer_invoices = await invoice_service.get_customer_invoices(customer_id)
        
        # Should only return invoices for the specified customer
        assert len(customer_invoices) == 2
        for invoice in customer_invoices:
            assert invoice.customer_id == customer_id
    
    async def test_create_invoice_with_validation_errors(self, invoice_service):
        """Test invoice creation validation errors."""
        # Test with no line items
        invalid_data = schemas.InvoiceCreate(
            customer_id=uuid4(),
            line_items=[]
        )
        
        with pytest.raises(ValidationError) as exc_info:
            await invoice_service.create_invoice(invalid_data)
        
        assert "at least one line item" in str(exc_info.value)
        
        # Test with invalid quantity
        invalid_data = schemas.InvoiceCreate(
            customer_id=uuid4(),
            line_items=[
                schemas.InvoiceLineItemCreate(
                    description="Service",
                    quantity=Decimal('-1.0'),  # Invalid quantity
                    unit_price=Decimal('100.00')
                )
            ]
        )
        
        with pytest.raises(ValidationError) as exc_info:
            await invoice_service.create_invoice(invalid_data)
        
        assert "Invalid quantity" in str(exc_info.value)
        
        # Test with invalid unit price
        invalid_data = schemas.InvoiceCreate(
            customer_id=uuid4(),
            line_items=[
                schemas.InvoiceLineItemCreate(
                    description="Service",
                    quantity=Decimal('1.0'),
                    unit_price=Decimal('-100.00')  # Invalid price
                )
            ]
        )
        
        with pytest.raises(ValidationError) as exc_info:
            await invoice_service.create_invoice(invalid_data)
        
        assert "Invalid unit price" in str(exc_info.value)
        
        # Test with due date before issue date
        invalid_data = schemas.InvoiceCreate(
            customer_id=uuid4(),
            issue_date=date.today(),
            due_date=date.today() - timedelta(days=1),  # Due before issue
            line_items=[
                schemas.InvoiceLineItemCreate(
                    description="Service",
                    quantity=Decimal('1.0'),
                    unit_price=Decimal('100.00')
                )
            ]
        )
        
        with pytest.raises(ValidationError) as exc_info:
            await invoice_service.create_invoice(invalid_data)
        
        assert "Due date cannot be before issue date" in str(exc_info.value)
    
    async def test_calculate_invoice_totals_standalone(self, invoice_service):
        """Test invoice total calculations without creating invoice."""
        line_items = [
            schemas.InvoiceLineItemCreate(
                description="Service A",
                quantity=Decimal('2.0'),
                unit_price=Decimal('50.00')
            ),
            schemas.InvoiceLineItemCreate(
                description="Service B",
                quantity=Decimal('1.5'),
                unit_price=Decimal('40.00')
            )
        ]
        
        totals = await invoice_service.calculate_invoice_totals(
            line_items=line_items,
            tax_rate=Decimal('0.10'),  # 10%
            discount_rate=Decimal('0.05')  # 5%
        )
        
        # Expected calculations:
        # Subtotal: (2.0 * 50.00) + (1.5 * 40.00) = 100.00 + 60.00 = 160.00
        # Tax: 160.00 * 0.10 = 16.00
        # Discount: 160.00 * 0.05 = 8.00
        # Total: 160.00 + 16.00 - 8.00 = 168.00
        
        assert totals['subtotal'] == Decimal('160.00')
        assert totals['tax_amount'] == Decimal('16.00')
        assert totals['discount_amount'] == Decimal('8.00')
        assert totals['total_amount'] == Decimal('168.00')
    
    async def test_concurrent_invoice_creation(self, invoice_service, sample_invoice_data):
        """Test concurrent invoice creation doesn't cause data issues."""
        import asyncio
        
        # Create multiple invoices concurrently
        tasks = []
        for i in range(5):
            # Create separate data for each task to avoid sharing issues
            invoice_data = schemas.InvoiceCreate(
                customer_id=uuid4(),  # Different customer for each
                line_items=[
                    schemas.InvoiceLineItemCreate(
                        description=f"Service {i}",
                        quantity=Decimal('1.0'),
                        unit_price=Decimal('100.00')
                    )
                ]
            )
            tasks.append(invoice_service.create_invoice(invoice_data))
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all invoices were created successfully
        assert len(results) == 5
        for result in results:
            assert not isinstance(result, Exception)
            assert result.id is not None
            assert result.total_amount == Decimal('100.00')
    
    async def test_invoice_service_with_database_rollback(self, invoice_service):
        """Test that service operations properly handle database rollbacks."""
        # This test would require more sophisticated transaction management
        # For now, we'll test basic error handling
        
        invalid_data = schemas.InvoiceCreate(
            customer_id=uuid4(),
            line_items=[
                schemas.InvoiceLineItemCreate(
                    description="Service",
                    quantity=Decimal('1.0'),
                    unit_price=Decimal('100.00')
                )
            ]
        )
        
        # Mock a repository error to test rollback behavior
        original_create = invoice_service.invoice_repo.create
        
        def failing_create(*args, **kwargs):
            raise Exception("Simulated database error")
        
        invoice_service.invoice_repo.create = failing_create
        
        with pytest.raises(ServiceError) as exc_info:
            await invoice_service.create_invoice(invalid_data)
        
        assert "Failed to create invoice" in str(exc_info.value)
        
        # Restore original method
        invoice_service.invoice_repo.create = original_create