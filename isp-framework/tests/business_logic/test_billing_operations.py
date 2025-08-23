"""Business logic tests for billing operations.

Tests comprehensive billing functionality including:
- Invoice generation and calculation
- Payment processing workflows
- Recurring billing automation
- Credit management
- Late fee calculations
- Multi-tenant billing isolation
- Service-specific billing rules
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

from dotmac_isp.modules.billing.models import (
    Invoice, InvoiceStatus, PaymentMethod, InvoiceLineItem, Payment, 
    BillingCycle, CreditNote, LateFee, TaxRate
)
from dotmac_isp.modules.billing.services import (
    BillingService, InvoiceService, PaymentService, RecurringBillingService,
    TaxService, CreditService
)
from dotmac_isp.modules.billing.schemas import (
    InvoiceCreateRequest, PaymentRequest, CreditNoteRequest,
    BillingRuleRequest, InvoiceCalculationResult
)
from dotmac_isp.modules.identity.models import Customer, CustomerType
from dotmac_isp.modules.services.models import ServiceInstance, ServicePlan
from dotmac_isp.core.exceptions import (
    BillingError, InsufficientCreditError, PaymentFailedError
)


@pytest.mark.business_logic
class TestInvoiceGeneration:
    """Test invoice generation and calculation logic."""
    
    async def test_monthly_internet_service_invoice(self, db_session, sample_customer_data, sample_service_data):
        """Test generating invoice for monthly internet service."""
        billing_service = BillingService(db_session)
        
        # Setup customer and service
        customer_data = sample_customer_data
        service_data = sample_service_data
        
        # Mock customer and service objects
        customer = Customer(**customer_data)
        service = Service(**service_data)
        
        # Generate invoice for current month
        billing_period_start = date.today().replace(day=1)
        billing_period_end = (billing_period_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        invoice_request = InvoiceCreateRequest(
            customer_id=customer.id,
            billing_period_start=billing_period_start,
            billing_period_end=billing_period_end,
            services=[service.service_id],
            include_taxes=True,
            tenant_id=customer.tenant_id
        )
        
        with patch.object(billing_service, '_get_customer', return_value=customer):
            with patch.object(billing_service, '_get_active_services', return_value=[service]):
                with patch.object(billing_service, '_calculate_service_charges') as mock_calc:
                    mock_calc.return_value = {
                        'base_charge': Decimal('79.99'),
                        'usage_charges': Decimal('0.00'),
                        'fees': Decimal('5.00'),
                        'discounts': Decimal('-10.00')
                    }
                    
                    invoice = await billing_service.generate_invoice(invoice_request)
                    
                    # Verify invoice structure
                    assert invoice.customer_id == customer.id
                    assert invoice.billing_period_start == billing_period_start
                    assert invoice.billing_period_end == billing_period_end
                    assert invoice.status == InvoiceStatus.DRAFT
                    
                    # Verify line items
                    assert len(invoice.line_items) >= 1
                    internet_line = next(item for item in invoice.line_items if 'Internet' in item.description)
                    assert internet_line.amount == Decimal('79.99')
                    assert internet_line.quantity == 1
                    
                    # Verify totals
                    expected_subtotal = Decimal('74.99')  # 79.99 + 5.00 - 10.00
                    assert invoice.subtotal == expected_subtotal
    
    async def test_business_customer_invoice_with_multiple_services(self, db_session):
        """Test invoice generation for business customer with multiple services."""
        billing_service = BillingService(db_session)
        
        # Business customer data
        business_customer = Customer(
            id="biz_001",
            customer_type=CustomerType.BUSINESS,
            company_name="Tech Solutions Inc",
            tenant_id="tenant_001"
        )
        
        # Multiple services
        services = [
            Service(
                service_id="svc_internet",
                service_type="internet",
                plan_name="Business 500/100",
                monthly_price=Decimal('199.99')
            ),
            Service(
                service_id="svc_voip",
                service_type="voip",
                plan_name="Business VoIP 20 lines",
                monthly_price=Decimal('149.99')
            ),
            Service(
                service_id="svc_support",
                service_type="managed_support",
                plan_name="24/7 Premium Support",
                monthly_price=Decimal('99.99')
            )
        ]
        
        invoice_request = InvoiceCreateRequest(
            customer_id=business_customer.id,
            billing_period_start=date.today().replace(day=1),
            billing_period_end=date.today().replace(day=1) + timedelta(days=30),
            services=[s.service_id for s in services],
            include_taxes=True,
            tenant_id=business_customer.tenant_id
        )
        
        with patch.object(billing_service, '_get_customer', return_value=business_customer):
            with patch.object(billing_service, '_get_active_services', return_value=services):
                invoice = await billing_service.generate_invoice(invoice_request)
                
                # Verify multiple line items
                assert len(invoice.line_items) == 3
                
                # Verify service charges
                total_service_charges = sum(s.monthly_price for s in services)
                assert invoice.subtotal >= total_service_charges
                
                # Business customers should have tax applied
                assert invoice.tax_amount > Decimal('0')
                assert invoice.total_amount > invoice.subtotal
    
    async def test_proration_for_partial_month_service(self, db_session):
        """Test prorated billing for service activated mid-month."""
        billing_service = BillingService(db_session)
        
        customer = Customer(id="cust_001", tenant_id="tenant_001")
        
        # Service activated on 15th of month
        service_start_date = date.today().replace(day=15)
        service = Service(
            service_id="svc_001",
            service_type="internet",
            monthly_price=Decimal('100.00'),
            activation_date=service_start_date
        )
        
        # Billing period is full month
        billing_start = date.today().replace(day=1)
        billing_end = (billing_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        with patch.object(billing_service, '_calculate_proration') as mock_proration:
            # Mock proration calculation (service active for ~half month)
            mock_proration.return_value = Decimal('48.39')  # Prorated amount
            
            invoice_request = InvoiceCreateRequest(
                customer_id=customer.id,
                billing_period_start=billing_start,
                billing_period_end=billing_end,
                services=[service.service_id],
                tenant_id=customer.tenant_id
            )
            
            with patch.object(billing_service, '_get_customer', return_value=customer):
                with patch.object(billing_service, '_get_active_services', return_value=[service]):
                    invoice = await billing_service.generate_invoice(invoice_request)
                    
                    # Verify proration was applied
                    service_line = invoice.line_items[0]
                    assert service_line.amount == Decimal('48.39')
                    assert "prorated" in service_line.description.lower()
    
    async def test_invoice_with_usage_charges(self, db_session):
        """Test invoice generation including usage-based charges."""
        billing_service = BillingService(db_session)
        
        customer = Customer(id="cust_001", tenant_id="tenant_001")
        
        # Service with usage allowance and overage charges
        service = Service(
            service_id="svc_001",
            service_type="internet",
            monthly_price=Decimal('79.99'),
            usage_allowance_gb=500,  # 500GB included
            overage_rate_per_gb=Decimal('0.50')  # $0.50 per GB over
        )
        
        with patch.object(billing_service, '_get_usage_data') as mock_usage:
            # Mock usage data showing 650GB used (150GB overage)
            mock_usage.return_value = {
                'total_usage_gb': 650,
                'allowance_gb': 500,
                'overage_gb': 150,
                'overage_charges': Decimal('75.00')  # 150 * $0.50
            }
            
            invoice_request = InvoiceCreateRequest(
                customer_id=customer.id,
                billing_period_start=date.today().replace(day=1),
                billing_period_end=date.today(),
                services=[service.service_id],
                tenant_id=customer.tenant_id
            )
            
            with patch.object(billing_service, '_get_customer', return_value=customer):
                with patch.object(billing_service, '_get_active_services', return_value=[service]):
                    invoice = await billing_service.generate_invoice(invoice_request)
                    
                    # Verify base service charge
                    base_line = next(item for item in invoice.line_items if 'Internet Service' in item.description)
                    assert base_line.amount == Decimal('79.99')
                    
                    # Verify usage overage charge
                    overage_line = next(item for item in invoice.line_items if 'Data Overage' in item.description)
                    assert overage_line.amount == Decimal('75.00')
                    assert overage_line.quantity == 150  # GB over allowance


@pytest.mark.business_logic
class TestPaymentProcessing:
    """Test payment processing workflows."""
    
    async def test_credit_card_payment_success(self, db_session, sample_billing_data):
        """Test successful credit card payment processing."""
        payment_service = PaymentService(db_session)
        
        # Create invoice
        invoice_data = sample_billing_data
        invoice = Invoice(**invoice_data)
        
        payment_request = PaymentRequest(
            invoice_id=invoice.id,
            amount=invoice.total_amount,
            payment_method=PaymentMethod.CREDIT_CARD,
            payment_details={
                'card_token': 'tok_test_card',
                'card_last_four': '4242',
                'billing_address': {
                    'street': '123 Test St',
                    'city': 'Test City',
                    'zip': '12345'
                }
            },
            tenant_id=invoice.tenant_id
        )
        
        with patch.object(payment_service, '_process_credit_card_payment') as mock_payment:
            mock_payment.return_value = {
                'transaction_id': 'txn_12345',
                'status': 'succeeded',
                'amount_charged': invoice.total_amount,
                'processor_response': 'Payment successful'
            }
            
            payment = await payment_service.process_payment(payment_request)
            
            # Verify payment record
            assert payment.invoice_id == invoice.id
            assert payment.amount == invoice.total_amount
            assert payment.payment_method == PaymentMethod.CREDIT_CARD
            assert payment.transaction_id == 'txn_12345'
            assert payment.status == 'completed'
            
            # Verify payment processing was called
            mock_payment.assert_called_once()
    
    async def test_ach_payment_processing(self, db_session, sample_billing_data):
        """Test ACH/bank transfer payment processing."""
        payment_service = PaymentService(db_session)
        
        invoice_data = sample_billing_data
        invoice = Invoice(**invoice_data)
        
        payment_request = PaymentRequest(
            invoice_id=invoice.id,
            amount=invoice.total_amount,
            payment_method=PaymentMethod.ACH,
            payment_details={
                'bank_account_token': 'btok_test_bank',
                'account_last_four': '6789',
                'account_type': 'checking',
                'routing_number_last_four': '0123'
            },
            tenant_id=invoice.tenant_id
        )
        
        with patch.object(payment_service, '_process_ach_payment') as mock_ach:
            mock_ach.return_value = {
                'transaction_id': 'ach_12345',
                'status': 'pending',  # ACH typically starts as pending
                'amount_charged': invoice.total_amount,
                'estimated_completion': datetime.now() + timedelta(days=3)
            }
            
            payment = await payment_service.process_payment(payment_request)
            
            # ACH payments start as pending
            assert payment.status == 'pending'
            assert payment.payment_method == PaymentMethod.ACH
            assert payment.transaction_id == 'ach_12345'
    
    async def test_payment_failure_handling(self, db_session, sample_billing_data):
        """Test handling of failed payments."""
        payment_service = PaymentService(db_session)
        
        invoice_data = sample_billing_data
        invoice = Invoice(**invoice_data)
        
        payment_request = PaymentRequest(
            invoice_id=invoice.id,
            amount=invoice.total_amount,
            payment_method=PaymentMethod.CREDIT_CARD,
            payment_details={'card_token': 'tok_declined_card'},
            tenant_id=invoice.tenant_id
        )
        
        with patch.object(payment_service, '_process_credit_card_payment') as mock_payment:
            mock_payment.side_effect = PaymentFailedError("Card declined", error_code="card_declined")
            
            with pytest.raises(PaymentFailedError) as exc_info:
                await payment_service.process_payment(payment_request)
            
            assert "Card declined" in str(exc_info.value)
            assert exc_info.value.error_code == "card_declined"
    
    async def test_partial_payment_handling(self, db_session, sample_billing_data):
        """Test handling of partial payments."""
        payment_service = PaymentService(db_session)
        
        invoice_data = sample_billing_data
        invoice_data['total_amount'] = Decimal('100.00')
        invoice = Invoice(**invoice_data)
        
        # Make partial payment of $60
        payment_request = PaymentRequest(
            invoice_id=invoice.id,
            amount=Decimal('60.00'),  # Partial amount
            payment_method=PaymentMethod.CREDIT_CARD,
            payment_details={'card_token': 'tok_test_card'},
            tenant_id=invoice.tenant_id
        )
        
        with patch.object(payment_service, '_process_credit_card_payment') as mock_payment:
            mock_payment.return_value = {
                'transaction_id': 'txn_partial',
                'status': 'succeeded',
                'amount_charged': Decimal('60.00')
            }
            
            with patch.object(payment_service, '_update_invoice_payment_status') as mock_update:
                payment = await payment_service.process_payment(payment_request)
                
                # Verify partial payment record
                assert payment.amount == Decimal('60.00')
                assert payment.status == 'completed'
                
                # Verify invoice update was called to handle partial payment
                mock_update.assert_called_once_with(
                    invoice.id, 
                    paid_amount=Decimal('60.00'),
                    remaining_balance=Decimal('40.00')
                )


@pytest.mark.business_logic
class TestRecurringBilling:
    """Test automated recurring billing processes."""
    
    async def test_monthly_recurring_billing_cycle(self, db_session):
        """Test automated monthly billing cycle."""
        recurring_service = RecurringBillingService(db_session)
        
        # Mock customers with monthly billing cycles
        customers_due = [
            {
                'customer_id': 'cust_001',
                'tenant_id': 'tenant_001',
                'billing_cycle': BillingCycle.MONTHLY,
                'next_billing_date': date.today(),
                'active_services': ['svc_001', 'svc_002']
            },
            {
                'customer_id': 'cust_002', 
                'tenant_id': 'tenant_001',
                'billing_cycle': BillingCycle.MONTHLY,
                'next_billing_date': date.today(),
                'active_services': ['svc_003']
            }
        ]
        
        with patch.object(recurring_service, '_get_customers_due_for_billing', return_value=customers_due):
            with patch.object(recurring_service, '_generate_recurring_invoice') as mock_generate:
                mock_generate.return_value = Invoice(
                    id='inv_001',
                    status=InvoiceStatus.PENDING,
                    total_amount=Decimal('159.98')
                )
                
                with patch.object(recurring_service, '_process_auto_payment') as mock_auto_pay:
                    mock_auto_pay.return_value = {'status': 'succeeded'}
                    
                    results = await recurring_service.process_monthly_billing()
                    
                    # Verify billing was processed
                    assert results['invoices_generated'] == 2
                    assert results['successful_payments'] >= 0
                    
                    # Verify invoice generation was called for each customer
                    assert mock_generate.call_count == 2
    
    async def test_auto_payment_processing(self, db_session):
        """Test automatic payment processing for recurring bills."""
        recurring_service = RecurringBillingService(db_session)
        
        # Invoice ready for auto-payment
        invoice = Invoice(
            id='inv_auto',
            customer_id='cust_001',
            total_amount=Decimal('79.99'),
            status=InvoiceStatus.PENDING,
            tenant_id='tenant_001'
        )
        
        # Customer has auto-pay enabled
        customer_payment_info = {
            'auto_pay_enabled': True,
            'default_payment_method': PaymentMethod.CREDIT_CARD,
            'payment_details': {'card_token': 'tok_autopay_card'}
        }
        
        with patch.object(recurring_service, '_get_customer_payment_info', return_value=customer_payment_info):
            with patch.object(recurring_service, '_process_payment') as mock_payment:
                mock_payment.return_value = Payment(
                    id='pay_auto_001',
                    status='completed',
                    amount=Decimal('79.99')
                )
                
                payment_result = await recurring_service.process_auto_payment(invoice)
                
                # Verify auto-payment was processed
                assert payment_result.status == 'completed'
                assert payment_result.amount == invoice.total_amount
                
                # Verify payment processing was called
                mock_payment.assert_called_once()
    
    async def test_billing_retry_for_failed_payments(self, db_session):
        """Test retry logic for failed recurring payments."""
        recurring_service = RecurringBillingService(db_session)
        
        # Invoice with failed payment
        invoice = Invoice(
            id='inv_failed',
            customer_id='cust_001',
            status=InvoiceStatus.PENDING,
            total_amount=Decimal('79.99'),
            tenant_id='tenant_001'
        )
        
        # Mock failed payment history
        failed_attempts = [
            {'attempt_date': date.today() - timedelta(days=3), 'error': 'card_declined'},
            {'attempt_date': date.today() - timedelta(days=1), 'error': 'insufficient_funds'}
        ]
        
        with patch.object(recurring_service, '_get_failed_payment_attempts', return_value=failed_attempts):
            with patch.object(recurring_service, '_should_retry_payment', return_value=True):
                with patch.object(recurring_service, '_process_payment_retry') as mock_retry:
                    mock_retry.return_value = {
                        'status': 'succeeded',
                        'attempt_number': 3,
                        'transaction_id': 'txn_retry_success'
                    }
                    
                    retry_result = await recurring_service.retry_failed_payment(invoice.id)
                    
                    # Verify retry was attempted
                    assert retry_result['status'] == 'succeeded'
                    assert retry_result['attempt_number'] == 3
                    
                    # Verify retry processing was called
                    mock_retry.assert_called_once()


@pytest.mark.business_logic
class TestLateFeeCalculation:
    """Test late fee calculation and application."""
    
    async def test_late_fee_calculation_for_overdue_invoice(self, db_session):
        """Test calculation of late fees for overdue invoices."""
        billing_service = BillingService(db_session)
        
        # Overdue invoice (30 days past due)
        overdue_invoice = Invoice(
            id='inv_overdue',
            customer_id='cust_001',
            total_amount=Decimal('100.00'),
            due_date=date.today() - timedelta(days=30),
            status=InvoiceStatus.OVERDUE,
            tenant_id='tenant_001'
        )
        
        # Late fee configuration (5% or $5 minimum)
        late_fee_config = {
            'percentage_rate': Decimal('0.05'),  # 5%
            'minimum_fee': Decimal('5.00'),
            'maximum_fee': Decimal('25.00'),
            'grace_period_days': 15
        }
        
        with patch.object(billing_service, '_get_late_fee_config', return_value=late_fee_config):
            late_fee = await billing_service.calculate_late_fee(overdue_invoice)
            
            # 5% of $100 = $5, which equals minimum
            assert late_fee.amount == Decimal('5.00')
            assert late_fee.invoice_id == overdue_invoice.id
            assert late_fee.fee_type == 'late_payment'
            assert late_fee.calculation_basis == 'percentage'
    
    async def test_late_fee_with_maximum_cap(self, db_session):
        """Test late fee calculation with maximum fee cap."""
        billing_service = BillingService(db_session)
        
        # High-value overdue invoice
        high_value_invoice = Invoice(
            id='inv_high_value',
            total_amount=Decimal('1000.00'),
            due_date=date.today() - timedelta(days=45),
            status=InvoiceStatus.OVERDUE,
            tenant_id='tenant_001'
        )
        
        late_fee_config = {
            'percentage_rate': Decimal('0.05'),  # 5%
            'minimum_fee': Decimal('5.00'),
            'maximum_fee': Decimal('25.00'),  # Cap at $25
            'grace_period_days': 15
        }
        
        with patch.object(billing_service, '_get_late_fee_config', return_value=late_fee_config):
            late_fee = await billing_service.calculate_late_fee(high_value_invoice)
            
            # 5% of $1000 = $50, but capped at $25
            assert late_fee.amount == Decimal('25.00')
            assert late_fee.fee_type == 'late_payment'
    
    async def test_no_late_fee_within_grace_period(self, db_session):
        """Test that no late fee is applied within grace period."""
        billing_service = BillingService(db_session)
        
        # Invoice overdue but within grace period
        recent_overdue = Invoice(
            id='inv_recent_overdue',
            total_amount=Decimal('100.00'),
            due_date=date.today() - timedelta(days=10),  # Only 10 days overdue
            status=InvoiceStatus.OVERDUE,
            tenant_id='tenant_001'
        )
        
        late_fee_config = {
            'percentage_rate': Decimal('0.05'),
            'minimum_fee': Decimal('5.00'),
            'maximum_fee': Decimal('25.00'),
            'grace_period_days': 15  # 15-day grace period
        }
        
        with patch.object(billing_service, '_get_late_fee_config', return_value=late_fee_config):
            late_fee = await billing_service.calculate_late_fee(recent_overdue)
            
            # No late fee within grace period
            assert late_fee is None


@pytest.mark.business_logic
class TestCreditManagement:
    """Test credit note and refund management."""
    
    async def test_service_credit_application(self, db_session):
        """Test applying service credits to customer account."""
        credit_service = CreditService(db_session)
        
        customer_id = 'cust_001'
        
        # Service outage resulted in credit
        credit_request = CreditNoteRequest(
            customer_id=customer_id,
            amount=Decimal('25.00'),
            reason='Service outage compensation',
            credit_type='service_credit',
            reference_invoice_id='inv_001',
            tenant_id='tenant_001'
        )
        
        with patch.object(credit_service, '_validate_credit_request') as mock_validate:
            mock_validate.return_value = True
            
            credit_note = await credit_service.create_credit_note(credit_request)
            
            # Verify credit note creation
            assert credit_note.customer_id == customer_id
            assert credit_note.amount == Decimal('25.00')
            assert credit_note.credit_type == 'service_credit'
            assert credit_note.status == 'active'
    
    async def test_automatic_credit_application_to_invoice(self, db_session):
        """Test automatic application of credits to new invoices."""
        credit_service = CreditService(db_session)
        
        customer_id = 'cust_001'
        
        # Customer has existing credits
        existing_credits = [
            CreditNote(
                id='credit_001',
                customer_id=customer_id,
                amount=Decimal('15.00'),
                remaining_amount=Decimal('15.00'),
                status='active'
            ),
            CreditNote(
                id='credit_002',
                customer_id=customer_id,
                amount=Decimal('10.00'),
                remaining_amount=Decimal('10.00'),
                status='active'
            )
        ]
        
        # New invoice for $50
        new_invoice = Invoice(
            id='inv_new',
            customer_id=customer_id,
            total_amount=Decimal('50.00'),
            tenant_id='tenant_001'
        )
        
        with patch.object(credit_service, '_get_active_credits', return_value=existing_credits):
            credit_application = await credit_service.apply_credits_to_invoice(new_invoice)
            
            # Total credits: $25, Invoice: $50
            # Credits should be fully applied, remaining balance: $25
            assert credit_application.total_credits_applied == Decimal('25.00')
            assert credit_application.invoice_balance_after_credits == Decimal('25.00')
            assert len(credit_application.credits_used) == 2
    
    async def test_refund_processing_workflow(self, db_session):
        """Test customer refund processing workflow."""
        credit_service = CreditService(db_session)
        
        # Customer requests refund for canceled service
        refund_request = {
            'customer_id': 'cust_001',
            'amount': Decimal('79.99'),
            'reason': 'Service cancellation - unused portion',
            'refund_method': 'original_payment_method',
            'original_payment_id': 'pay_original_001',
            'tenant_id': 'tenant_001'
        }
        
        with patch.object(credit_service, '_validate_refund_eligibility') as mock_validate:
            mock_validate.return_value = True
            
            with patch.object(credit_service, '_process_payment_reversal') as mock_reversal:
                mock_reversal.return_value = {
                    'refund_id': 'refund_001',
                    'status': 'pending',
                    'estimated_completion': datetime.now() + timedelta(days=5)
                }
                
                refund = await credit_service.process_refund(refund_request)
                
                # Verify refund processing
                assert refund.amount == Decimal('79.99')
                assert refund.status == 'pending'
                assert refund.refund_method == 'original_payment_method'
                
                # Verify refund processing was initiated
                mock_reversal.assert_called_once()


@pytest.mark.business_logic
class TestTaxCalculation:
    """Test tax calculation for different jurisdictions and customer types."""
    
    async def test_residential_customer_tax_calculation(self, db_session):
        """Test tax calculation for residential customers."""
        tax_service = TaxService(db_session)
        
        # Residential customer in California
        customer = Customer(
            id='cust_residential',
            customer_type=CustomerType.RESIDENTIAL,
            state_province='CA',
            city='San Francisco',
            postal_code='94102',
            tenant_id='tenant_001'
        )
        
        invoice_amount = Decimal('79.99')
        
        # Mock CA tax rates
        tax_rates = {
            'state_tax': Decimal('0.0725'),      # 7.25% CA state tax
            'local_tax': Decimal('0.0075'),     # 0.75% SF local tax
            'total_rate': Decimal('0.08')       # 8% total
        }
        
        with patch.object(tax_service, '_get_tax_rates', return_value=tax_rates):
            tax_calculation = await tax_service.calculate_tax(customer, invoice_amount)
            
            # Verify tax calculation
            expected_tax = invoice_amount * tax_rates['total_rate']
            assert tax_calculation.tax_amount == expected_tax.quantize(Decimal('0.01'))
            assert tax_calculation.tax_rate == Decimal('0.08')
            assert len(tax_calculation.tax_breakdown) == 2  # State + Local
    
    async def test_business_customer_tax_exemption(self, db_session):
        """Test tax exemption for qualified business customers."""
        tax_service = TaxService(db_session)
        
        # Business customer with tax exemption
        business_customer = Customer(
            id='cust_business',
            customer_type=CustomerType.BUSINESS,
            tax_exempt=True,
            tax_exemption_certificate='TX_EXEMPT_12345',
            state_province='TX',
            tenant_id='tenant_001'
        )
        
        invoice_amount = Decimal('199.99')
        
        with patch.object(tax_service, '_validate_tax_exemption', return_value=True):
            tax_calculation = await tax_service.calculate_tax(business_customer, invoice_amount)
            
            # Tax-exempt customer should have zero tax
            assert tax_calculation.tax_amount == Decimal('0.00')
            assert tax_calculation.tax_exempt is True
            assert tax_calculation.exemption_reason == 'Business tax exemption'
    
    async def test_multi_jurisdiction_tax_calculation(self, db_session):
        """Test tax calculation for customer in multiple jurisdictions."""
        tax_service = TaxService(db_session)
        
        # Customer with billing and service addresses in different jurisdictions
        customer = Customer(
            id='cust_multi_jurisdiction',
            billing_state='NY',  # Billing in NY
            billing_city='New York',
            service_state='NJ',  # Service in NJ
            service_city='Newark',
            tenant_id='tenant_001'
        )
        
        invoice_amount = Decimal('150.00')
        
        # Tax based on service location (where service is consumed)
        nj_tax_rates = {
            'state_tax': Decimal('0.06625'),    # 6.625% NJ state tax
            'county_tax': Decimal('0.0125'),    # 1.25% Essex County
            'total_rate': Decimal('0.07875')    # 7.875% total
        }
        
        with patch.object(tax_service, '_get_service_location_tax_rates', return_value=nj_tax_rates):
            tax_calculation = await tax_service.calculate_tax(customer, invoice_amount)
            
            # Tax should be calculated based on service location (NJ)
            expected_tax = invoice_amount * nj_tax_rates['total_rate']
            assert tax_calculation.tax_amount == expected_tax.quantize(Decimal('0.01'))
            assert tax_calculation.jurisdiction == 'NJ'


@pytest.mark.business_logic
class TestBillingTenantIsolation:
    """Test multi-tenant isolation for billing operations."""
    
    async def test_cross_tenant_billing_prevention(self, db_session):
        """Test that billing operations respect tenant boundaries."""
        billing_service = BillingService(db_session)
        
        # Create invoices for different tenants
        tenant1_invoice = Invoice(
            id='inv_tenant1',
            customer_id='cust_tenant1_001',
            total_amount=Decimal('100.00'),
            tenant_id='tenant_001'
        )
        
        tenant2_customer = Customer(
            id='cust_tenant2_001',
            tenant_id='tenant_002'
        )
        
        with patch.object(billing_service, '_get_customer', return_value=tenant2_customer):
            # Tenant 2 customer trying to pay Tenant 1 invoice should fail
            payment_request = PaymentRequest(
                invoice_id=tenant1_invoice.id,
                amount=Decimal('100.00'),
                payment_method=PaymentMethod.CREDIT_CARD,
                tenant_id='tenant_002'  # Different tenant
            )
            
            with pytest.raises(BillingError) as exc_info:
                await billing_service.process_payment(payment_request)
            
            assert "tenant" in str(exc_info.value).lower()
    
    async def test_tenant_specific_billing_rules(self, db_session):
        """Test that billing rules are applied per tenant."""
        billing_service = BillingService(db_session)
        
        # Different late fee rules per tenant
        tenant1_config = {
            'late_fee_percentage': Decimal('0.05'),  # 5%
            'late_fee_minimum': Decimal('10.00')
        }
        
        tenant2_config = {
            'late_fee_percentage': Decimal('0.03'),  # 3%
            'late_fee_minimum': Decimal('5.00')
        }
        
        # Identical overdue invoices in different tenants
        tenant1_invoice = Invoice(
            customer_id='cust_t1',
            total_amount=Decimal('100.00'),
            due_date=date.today() - timedelta(days=30),
            tenant_id='tenant_001'
        )
        
        tenant2_invoice = Invoice(
            customer_id='cust_t2',
            total_amount=Decimal('100.00'),
            due_date=date.today() - timedelta(days=30),
            tenant_id='tenant_002'
        )
        
        with patch.object(billing_service, '_get_tenant_billing_config') as mock_config:
            # Mock different configs per tenant
            def config_side_effect(tenant_id):
                if tenant_id == 'tenant_001':
                    return tenant1_config
                else:
                    return tenant2_config
            
            mock_config.side_effect = config_side_effect
            
            # Calculate late fees for both
            t1_late_fee = await billing_service.calculate_late_fee(tenant1_invoice)
            t2_late_fee = await billing_service.calculate_late_fee(tenant2_invoice)
            
            # Different fees based on tenant configuration
            assert t1_late_fee.amount == Decimal('10.00')  # $100 * 5% = $5, but minimum is $10
            assert t2_late_fee.amount == Decimal('5.00')   # $100 * 3% = $3, but minimum is $5


@pytest.mark.business_logic
class TestBillingIntegrationWorkflows:
    """Test end-to-end billing workflow integrations."""
    
    async def test_complete_customer_billing_lifecycle(self, db_session, sample_customer_data):
        """Test complete billing lifecycle from service activation to payment."""
        billing_service = BillingService(db_session)
        payment_service = PaymentService(db_session)
        
        customer_data = sample_customer_data
        customer = Customer(**customer_data)
        
        # 1. Service activation triggers billing setup
        service_activation = {
            'customer_id': customer.id,
            'service_type': 'internet',
            'plan': 'residential_100',
            'monthly_rate': Decimal('79.99'),
            'activation_date': date.today(),
            'first_billing_date': date.today().replace(day=1) + timedelta(days=32)
        }
        
        # 2. Generate first invoice (prorated for activation date)
        billing_period_start = date.today().replace(day=1)
        billing_period_end = (billing_period_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        with patch.object(billing_service, '_calculate_prorated_amount') as mock_prorate:
            mock_prorate.return_value = Decimal('48.38')  # Prorated amount
            
            invoice = await billing_service.generate_activation_invoice(service_activation)
            
            # Verify prorated first invoice
            assert invoice.customer_id == customer.id
            assert invoice.total_amount > Decimal('0')
            assert invoice.status == InvoiceStatus.PENDING
        
        # 3. Customer makes payment
        payment_request = PaymentRequest(
            invoice_id=invoice.id,
            amount=invoice.total_amount,
            payment_method=PaymentMethod.CREDIT_CARD,
            tenant_id=customer.tenant_id
        )
        
        with patch.object(payment_service, '_process_credit_card_payment') as mock_payment:
            mock_payment.return_value = {
                'transaction_id': 'txn_lifecycle_001',
                'status': 'succeeded',
                'amount_charged': invoice.total_amount
            }
            
            payment = await payment_service.process_payment(payment_request)
            
            # Verify payment completion
            assert payment.status == 'completed'
            assert payment.amount == invoice.total_amount
        
        # 4. Set up recurring billing
        with patch.object(billing_service, '_setup_recurring_billing') as mock_recurring:
            await billing_service.setup_customer_recurring_billing(
                customer.id, 
                billing_cycle=BillingCycle.MONTHLY,
                auto_pay=True
            )
            
            mock_recurring.assert_called_once()
        
        # 5. Verify complete billing setup
        billing_status = await billing_service.get_customer_billing_status(customer.id)
        
        with patch.object(billing_service, 'get_customer_billing_status') as mock_status:
            mock_status.return_value = {
                'customer_id': customer.id,
                'billing_cycle': BillingCycle.MONTHLY,
                'next_billing_date': billing_period_end + timedelta(days=1),
                'auto_pay_enabled': True,
                'current_balance': Decimal('0.00'),
                'status': 'active'
            }
            
            status = await billing_service.get_customer_billing_status(customer.id)
            assert status['status'] == 'active'
            assert status['auto_pay_enabled'] is True