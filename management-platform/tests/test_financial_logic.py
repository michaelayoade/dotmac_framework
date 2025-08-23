"""
Comprehensive financial logic tests for the DotMac Management Platform.
Tests critical billing, payment, and revenue calculations.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from typing import List

from app.services.billing_service import BillingService
from app.repositories.billing_additional import (
    SubscriptionRepository, InvoiceRepository, PaymentRepository,
    PricingPlanRepository, UsageRecordRepository
)
from app.models.billing import (
    Subscription, Invoice, Payment, PricingPlan, UsageRecord,
    SubscriptionStatus, InvoiceStatus, PaymentStatus
)
from app.schemas.billing import (
    SubscriptionCreate, InvoiceCreate, PaymentCreate,
    PricingPlanCreate, UsageRecordCreate
)


@pytest.mark.financial
class TestSubscriptionBilling:
    """Test subscription billing calculations and lifecycle."""
    
    async def test_monthly_subscription_calculation(self, db_session, billing_service):
        """Test monthly subscription amount calculation."""
        # Create pricing plan
        plan_data = PricingPlanCreate(
            name="Standard Plan",
            description="Standard monthly plan",
            base_price_cents=2999,  # $29.99
            billing_cycle="monthly",
            features={"users": 10, "storage_gb": 100}
        )
        pricing_plan = await billing_service.create_pricing_plan(plan_data)
        
        # Create subscription
        subscription_data = SubscriptionCreate(
            tenant_id="550e8400-e29b-41d4-a716-446655440001",
            pricing_plan_id=pricing_plan.id,
            billing_cycle="monthly"
        )
        subscription = await billing_service.create_subscription(subscription_data)
        
        # Test billing calculation
        billing_amount = await billing_service.calculate_subscription_amount(
            subscription.id, 
            billing_period_start=datetime.utcnow(),
            billing_period_end=datetime.utcnow() + timedelta(days=30)
        )
        
        assert billing_amount == Decimal("29.99")
        assert subscription.status == SubscriptionStatus.ACTIVE
        assert subscription.monthly_amount_cents == 2999
    
    async def test_annual_subscription_discount(self, db_session, billing_service):
        """Test annual subscription discount calculation."""
        plan_data = PricingPlanCreate(
            name="Premium Annual",
            description="Premium annual plan with discount",
            base_price_cents=29999,  # $299.99 annually (vs $39.99 monthly)
            billing_cycle="annual",
            features={"users": 50, "storage_gb": 1000}
        )
        pricing_plan = await billing_service.create_pricing_plan(plan_data)
        
        subscription_data = SubscriptionCreate(
            tenant_id="550e8400-e29b-41d4-a716-446655440002",
            pricing_plan_id=pricing_plan.id,
            billing_cycle="annual"
        )
        subscription = await billing_service.create_subscription(subscription_data)
        
        # Calculate equivalent monthly cost
        monthly_equivalent = await billing_service.calculate_monthly_equivalent(subscription.id)
        
        # Should be $25 monthly equivalent ($300/12) vs $39.99 monthly
        assert monthly_equivalent < Decimal("30.00")
        assert subscription.annual_amount_cents == 29999
    
    async def test_prorated_billing(self, db_session, billing_service):
        """Test prorated billing for partial periods."""
        plan_data = PricingPlanCreate(
            name="Prorated Plan",
            base_price_cents=3000,  # $30.00
            billing_cycle="monthly"
        )
        pricing_plan = await billing_service.create_pricing_plan(plan_data)
        
        # Start subscription mid-month (15 days into 30-day month)
        start_date = datetime(2024, 1, 15)  # January 15
        end_date = datetime(2024, 1, 31)    # January 31
        
        subscription_data = SubscriptionCreate(
            tenant_id="550e8400-e29b-41d4-a716-446655440003",
            pricing_plan_id=pricing_plan.id,
            billing_cycle="monthly",
            start_date=start_date
        )
        subscription = await billing_service.create_subscription(subscription_data)
        
        # Calculate prorated amount for partial period
        prorated_amount = await billing_service.calculate_prorated_amount(
            subscription.id,
            billing_period_start=start_date,
            billing_period_end=end_date,
            full_month_days=31
        )
        
        # Should be roughly $16.13 (17 days / 31 days * $30.00)
        expected = Decimal("30.00") * Decimal("17") / Decimal("31")
        assert abs(prorated_amount - expected) < Decimal("0.01")


@pytest.mark.financial
class TestUsageBasedBilling:
    """Test usage-based billing and overages."""
    
    async def test_usage_overage_calculation(self, db_session, billing_service):
        """Test overage charges for usage above plan limits."""
        # Plan with usage limits
        plan_data = PricingPlanCreate(
            name="Usage Plan",
            base_price_cents=1999,  # $19.99 base
            billing_cycle="monthly",
            features={"users": 5, "storage_gb": 50, "api_calls": 10000},
            overage_pricing={
                "storage_gb": 200,  # $2.00 per GB over 50GB
                "api_calls": 1      # $0.01 per 1000 calls over 10k
            }
        )
        pricing_plan = await billing_service.create_pricing_plan(plan_data)
        
        subscription_data = SubscriptionCreate(
            tenant_id="550e8400-e29b-41d4-a716-446655440004",
            pricing_plan_id=pricing_plan.id
        )
        subscription = await billing_service.create_subscription(subscription_data)
        
        # Record usage exceeding limits
        usage_records = [
            UsageRecordCreate(
                subscription_id=subscription.id,
                usage_type="storage_gb",
                quantity=75,  # 25GB over limit
                recorded_at=datetime.utcnow()
            ),
            UsageRecordCreate(
                subscription_id=subscription.id,
                usage_type="api_calls", 
                quantity=15000,  # 5000 calls over limit
                recorded_at=datetime.utcnow()
            )
        ]
        
        for usage_data in usage_records:
            await billing_service.record_usage(usage_data)
        
        # Calculate total bill including overages
        total_bill = await billing_service.calculate_usage_bill(
            subscription.id,
            billing_period_start=datetime.utcnow().replace(day=1),
            billing_period_end=datetime.utcnow()
        )
        
        # Base: $19.99 + Storage overage: 25GB * $2.00 = $50 + API overage: 5 * $0.01 = $0.05
        expected_total = Decimal("19.99") + Decimal("50.00") + Decimal("0.05")
        assert abs(total_bill - expected_total) < Decimal("0.01")
    
    async def test_usage_spike_protection(self, db_session, billing_service):
        """Test usage spike protection and billing caps."""
        plan_data = PricingPlanCreate(
            name="Capped Plan",
            base_price_cents=2999,
            billing_cycle="monthly",
            features={"api_calls": 50000},
            overage_pricing={"api_calls": 5},  # $0.05 per 1000 calls
            usage_caps={"api_calls": 200000}  # Cap at 200k total calls
        )
        pricing_plan = await billing_service.create_pricing_plan(plan_data)
        
        subscription_data = SubscriptionCreate(
            tenant_id="550e8400-e29b-41d4-a716-446655440005",
            pricing_plan_id=pricing_plan.id
        )
        subscription = await billing_service.create_subscription(subscription_data)
        
        # Record massive usage spike
        usage_data = UsageRecordCreate(
            subscription_id=subscription.id,
            usage_type="api_calls",
            quantity=500000  # Way over the cap
        )
        
        # System should cap usage at limit
        recorded_usage = await billing_service.record_usage(usage_data)
        
        # Verify usage was capped
        total_usage = await billing_service.get_period_usage(
            subscription.id, "api_calls"
        )
        
        assert total_usage <= 200000  # Should not exceed cap
        
        # Calculate bill with capped usage
        bill = await billing_service.calculate_usage_bill(
            subscription.id,
            billing_period_start=datetime.utcnow().replace(day=1),
            billing_period_end=datetime.utcnow()
        )
        
        # Should not exceed reasonable amount due to cap
        max_expected = Decimal("29.99") + (Decimal("150") * Decimal("0.05"))  # Base + max overage
        assert bill <= max_expected


@pytest.mark.financial
class TestPaymentProcessing:
    """Test payment processing and financial integrity."""
    
    async def test_payment_success_flow(self, db_session, billing_service):
        """Test successful payment processing."""
        # Create invoice
        invoice_data = InvoiceCreate(
            subscription_id="550e8400-e29b-41d4-a716-446655440006",
            amount_cents=2999,
            description="Monthly subscription",
            due_date=datetime.utcnow() + timedelta(days=30)
        )
        invoice = await billing_service.create_invoice(invoice_data)
        
        # Process payment
        payment_data = PaymentCreate(
            invoice_id=invoice.id,
            amount_cents=2999,
            payment_method="credit_card",
            payment_processor="stripe",
            processor_payment_id="pi_test_123456"
        )
        
        payment = await billing_service.process_payment(payment_data)
        
        assert payment.status == PaymentStatus.COMPLETED
        assert payment.amount_cents == 2999
        
        # Verify invoice is marked as paid
        updated_invoice = await billing_service.get_invoice(invoice.id)
        assert updated_invoice.status == InvoiceStatus.PAID
        assert updated_invoice.paid_at is not None
    
    async def test_payment_failure_handling(self, db_session, billing_service):
        """Test payment failure handling and retry logic."""
        invoice_data = InvoiceCreate(
            subscription_id="550e8400-e29b-41d4-a716-446655440007",
            amount_cents=4999,
            description="Failed payment test"
        )
        invoice = await billing_service.create_invoice(invoice_data)
        
        # Simulate payment failure
        payment_data = PaymentCreate(
            invoice_id=invoice.id,
            amount_cents=4999,
            payment_method="credit_card",
            payment_processor="stripe",
            processor_payment_id="pi_fail_123"
        )
        
        with pytest.raises(Exception):  # Should raise payment processing error
            await billing_service.process_payment(payment_data)
        
        # Verify invoice remains unpaid
        updated_invoice = await billing_service.get_invoice(invoice.id)
        assert updated_invoice.status == InvoiceStatus.PENDING
        assert updated_invoice.paid_at is None
        
        # Test payment retry
        retry_payment = await billing_service.retry_payment(
            invoice.id,
            new_payment_method="different_card"
        )
        
        # Should create new payment attempt
        assert retry_payment.attempt_number > 1
    
    async def test_partial_payment_handling(self, db_session, billing_service):
        """Test partial payment handling."""
        invoice_data = InvoiceCreate(
            subscription_id="550e8400-e29b-41d4-a716-446655440008",
            amount_cents=10000,  # $100.00
            description="Large invoice"
        )
        invoice = await billing_service.create_invoice(invoice_data)
        
        # Make partial payment
        partial_payment_data = PaymentCreate(
            invoice_id=invoice.id,
            amount_cents=6000,  # $60.00 partial payment
            payment_method="credit_card"
        )
        
        payment = await billing_service.process_payment(partial_payment_data)
        
        # Verify partial payment recorded
        assert payment.amount_cents == 6000
        assert payment.status == PaymentStatus.COMPLETED
        
        # Verify invoice shows partial payment
        updated_invoice = await billing_service.get_invoice(invoice.id)
        assert updated_invoice.status == InvoiceStatus.PARTIALLY_PAID
        assert updated_invoice.amount_paid_cents == 6000
        assert updated_invoice.amount_due_cents == 4000
        
        # Complete payment
        final_payment_data = PaymentCreate(
            invoice_id=invoice.id,
            amount_cents=4000,  # Remaining $40.00
            payment_method="credit_card"
        )
        
        final_payment = await billing_service.process_payment(final_payment_data)
        
        # Verify invoice fully paid
        final_invoice = await billing_service.get_invoice(invoice.id)
        assert final_invoice.status == InvoiceStatus.PAID
        assert final_invoice.amount_paid_cents == 10000
        assert final_invoice.amount_due_cents == 0


@pytest.mark.financial
class TestRevenueCalculations:
    """Test revenue calculations and financial reporting."""
    
    async def test_monthly_recurring_revenue(self, db_session, billing_service):
        """Test Monthly Recurring Revenue (MRR) calculation."""
        # Create multiple subscriptions
        subscriptions = []
        
        for i, amount in enumerate([2999, 4999, 1999, 3999], 1):  # Different plan amounts
            plan_data = PricingPlanCreate(
                name=f"Plan {i}",
                base_price_cents=amount,
                billing_cycle="monthly"
            )
            plan = await billing_service.create_pricing_plan(plan_data)
            
            subscription_data = SubscriptionCreate(
                tenant_id=f"550e8400-e29b-41d4-a716-44665544000{i}",
                pricing_plan_id=plan.id
            )
            subscription = await billing_service.create_subscription(subscription_data)
            subscriptions.append(subscription)
        
        # Calculate total MRR
        mrr = await billing_service.calculate_mrr(
            as_of_date=datetime.utcnow()
        )
        
        # Total: $29.99 + $49.99 + $19.99 + $39.99 = $139.96
        expected_mrr = Decimal("29.99") + Decimal("49.99") + Decimal("19.99") + Decimal("39.99")
        assert abs(mrr - expected_mrr) < Decimal("0.01")
    
    async def test_annual_recurring_revenue(self, db_session, billing_service):
        """Test Annual Recurring Revenue (ARR) calculation."""
        # Mix of monthly and annual plans
        plans_data = [
            {"base_price_cents": 35999, "billing_cycle": "annual"},   # $359.99 annual
            {"base_price_cents": 2999, "billing_cycle": "monthly"},   # $29.99 monthly
            {"base_price_cents": 119999, "billing_cycle": "annual"},  # $1199.99 annual
        ]
        
        for i, plan_info in enumerate(plans_data, 1):
            plan_data = PricingPlanCreate(
                name=f"ARR Plan {i}",
                **plan_info
            )
            plan = await billing_service.create_pricing_plan(plan_data)
            
            subscription_data = SubscriptionCreate(
                tenant_id=f"550e8400-e29b-41d4-a716-44665544001{i}",
                pricing_plan_id=plan.id,
                billing_cycle=plan_info["billing_cycle"]
            )
            await billing_service.create_subscription(subscription_data)
        
        # Calculate ARR
        arr = await billing_service.calculate_arr(
            as_of_date=datetime.utcnow()
        )
        
        # Expected: $359.99 + ($29.99 * 12) + $1199.99 = $1919.87
        expected_arr = Decimal("359.99") + (Decimal("29.99") * 12) + Decimal("1199.99")
        assert abs(arr - expected_arr) < Decimal("0.01")
    
    async def test_churn_impact_on_revenue(self, db_session, billing_service):
        """Test revenue impact of subscription cancellations."""
        # Create subscription
        plan_data = PricingPlanCreate(
            name="Churn Test Plan",
            base_price_cents=5999,  # $59.99
            billing_cycle="monthly"
        )
        plan = await billing_service.create_pricing_plan(plan_data)
        
        subscription_data = SubscriptionCreate(
            tenant_id="550e8400-e29b-41d4-a716-446655440020",
            pricing_plan_id=plan.id
        )
        subscription = await billing_service.create_subscription(subscription_data)
        
        # Calculate initial MRR
        initial_mrr = await billing_service.calculate_mrr()
        
        # Cancel subscription
        await billing_service.cancel_subscription(
            subscription.id,
            cancellation_date=datetime.utcnow() + timedelta(days=15)
        )
        
        # Calculate MRR after cancellation
        post_cancel_mrr = await billing_service.calculate_mrr(
            as_of_date=datetime.utcnow() + timedelta(days=30)
        )
        
        # MRR should decrease by the subscription amount
        expected_decrease = Decimal("59.99")
        actual_decrease = initial_mrr - post_cancel_mrr
        assert abs(actual_decrease - expected_decrease) < Decimal("0.01")


@pytest.mark.financial
class TestFinancialIntegrity:
    """Test financial data integrity and audit trails."""
    
    async def test_double_payment_prevention(self, db_session, billing_service):
        """Test prevention of duplicate payments."""
        invoice_data = InvoiceCreate(
            subscription_id="550e8400-e29b-41d4-a716-446655440030",
            amount_cents=3999,
            description="Duplicate payment test"
        )
        invoice = await billing_service.create_invoice(invoice_data)
        
        payment_data = PaymentCreate(
            invoice_id=invoice.id,
            amount_cents=3999,
            payment_method="credit_card",
            processor_payment_id="pi_duplicate_test"  # Same processor ID
        )
        
        # First payment should succeed
        payment1 = await billing_service.process_payment(payment_data)
        assert payment1.status == PaymentStatus.COMPLETED
        
        # Duplicate payment should be rejected
        with pytest.raises(Exception):  # Should raise duplicate payment error
            await billing_service.process_payment(payment_data)
        
        # Verify only one payment exists
        payments = await billing_service.get_invoice_payments(invoice.id)
        assert len(payments) == 1
    
    async def test_financial_audit_trail(self, db_session, billing_service):
        """Test comprehensive audit trail for financial transactions."""
        # Create complete billing cycle
        plan_data = PricingPlanCreate(
            name="Audit Trail Plan",
            base_price_cents=2499
        )
        plan = await billing_service.create_pricing_plan(plan_data)
        
        subscription_data = SubscriptionCreate(
            tenant_id="550e8400-e29b-41d4-a716-446655440040",
            pricing_plan_id=plan.id
        )
        subscription = await billing_service.create_subscription(subscription_data)
        
        # Generate invoice
        invoice = await billing_service.generate_monthly_invoice(subscription.id)
        
        # Process payment
        payment_data = PaymentCreate(
            invoice_id=invoice.id,
            amount_cents=2499,
            payment_method="credit_card"
        )
        payment = await billing_service.process_payment(payment_data)
        
        # Get comprehensive audit trail
        audit_trail = await billing_service.get_financial_audit_trail(
            subscription.id,
            start_date=datetime.utcnow() - timedelta(days=30),
            end_date=datetime.utcnow()
        )
        
        # Verify all events are recorded
        event_types = [event["event_type"] for event in audit_trail]
        
        assert "subscription_created" in event_types
        assert "invoice_generated" in event_types  
        assert "payment_processed" in event_types
        assert "invoice_paid" in event_types
        
        # Verify financial amounts match
        total_charges = sum(
            event["amount_cents"] for event in audit_trail 
            if event["event_type"] in ["invoice_generated", "payment_processed"]
        )
        assert total_charges == 4998  # Invoice + Payment = 2499 + 2499
    
    async def test_reconciliation_accuracy(self, db_session, billing_service):
        """Test financial reconciliation and balance accuracy."""
        # Create multiple transactions
        transactions = []
        
        for i in range(5):  # 5 different amounts
            amount = (i + 1) * 1000  # $10, $20, $30, $40, $50
            
            invoice_data = InvoiceCreate(
                subscription_id=f"550e8400-e29b-41d4-a716-44665544005{i}",
                amount_cents=amount,
                description=f"Reconciliation test {i+1}"
            )
            invoice = await billing_service.create_invoice(invoice_data)
            
            payment_data = PaymentCreate(
                invoice_id=invoice.id,
                amount_cents=amount,
                payment_method="credit_card"
            )
            payment = await billing_service.process_payment(payment_data)
            
            transactions.append({"invoice": invoice, "payment": payment})
        
        # Run financial reconciliation
        reconciliation = await billing_service.run_financial_reconciliation(
            start_date=datetime.utcnow() - timedelta(days=1),
            end_date=datetime.utcnow()
        )
        
        # Verify totals match
        expected_total = sum((i + 1) * 1000 for i in range(5))  # 15000 cents = $150
        
        assert reconciliation["total_invoiced_cents"] == expected_total
        assert reconciliation["total_collected_cents"] == expected_total
        assert reconciliation["outstanding_balance_cents"] == 0
        assert reconciliation["reconciliation_status"] == "balanced"


# Test fixtures and helpers
@pytest.fixture
async def billing_service(db_session):
    """Create billing service instance with database session."""
    return BillingService(db_session)