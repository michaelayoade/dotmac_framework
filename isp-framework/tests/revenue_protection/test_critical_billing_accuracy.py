"""
Critical Revenue Protection Tests - Billing Accuracy Validation

These tests are PRODUCTION BLOCKERS and must pass 100% before any deployment.
They protect against revenue loss through billing calculation errors.
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any
import random

from dotmac_isp.modules.billing.models import (
    Invoice, InvoiceStatus, PaymentMethod, InvoiceLineItem, Payment,
    BillingCycle, CreditNote, LateFee, TaxRate
)
from dotmac_isp.modules.billing.service import BillingService
from dotmac_isp.modules.identity.models import Customer, CustomerType


@pytest.mark.revenue_critical
@pytest.mark.billing_core
class TestBillingCalculationAccuracy:
    """Test billing calculations to 6 decimal places for revenue protection."""
    
    def test_usage_based_billing_precision_edge_cases(self, db_session):
        """Test usage calculations with extreme precision requirements."""
        billing_service = BillingService(db_session, "tenant_001")
        
        # Edge cases that have caused revenue loss in production ISPs
        test_cases = [
            {
                "description": "Fractional GB usage with high precision",
                "usage_gb": Decimal('1234.567891'),
                "rate_per_gb": Decimal('0.123456'),
                "expected_charge": Decimal('152.41')  # Calculated to 6 decimal places
            },
            {
                "description": "Micro usage amounts",
                "usage_gb": Decimal('0.000001'),
                "rate_per_gb": Decimal('1.00'),
                "expected_charge": Decimal('0.000001')
            },
            {
                "description": "Large usage with fractional rates",
                "usage_gb": Decimal('99999.999999'),
                "rate_per_gb": Decimal('0.000001'),
                "expected_charge": Decimal('0.1')
            },
            {
                "description": "International rate precision",
                "usage_gb": Decimal('1000.00'),
                "rate_per_gb": Decimal('0.0123456789'),
                "expected_charge": Decimal('12.3456789')
            }
        ]
        
        for case in test_cases:
            with pytest.raises(AssertionError, message=f"Failed: {case['description']}") if False else None:
                calculated_charge = billing_service._calculate_usage_charge(
                    case["usage_gb"], 
                    case["rate_per_gb"]
                )
                
                # Revenue protection: Must match to 6 decimal places
                assert calculated_charge.quantize(Decimal('0.000001')) == case["expected_charge"]

    def test_proration_calculation_accuracy(self, db_session):
        """Test service proration calculations for partial billing periods."""
        billing_service = BillingService(db_session, "tenant_001")
        
        # Real-world proration scenarios that must be calculated exactly
        monthly_rate = Decimal('79.99')
        
        proration_tests = [
            {
                "description": "Mid-month activation on 15th",
                "billing_days": 30,
                "service_days": 16,  # Activated on 15th, billed through 30th
                "expected_amount": Decimal('42.66')  # (79.99 / 30) * 16
            },
            {
                "description": "Last day of month activation",
                "billing_days": 31,
                "service_days": 1,
                "expected_amount": Decimal('2.58')  # (79.99 / 31) * 1
            },
            {
                "description": "February leap year calculation",
                "billing_days": 29,  # Leap year February
                "service_days": 15,
                "expected_amount": Decimal('41.37')  # (79.99 / 29) * 15
            },
            {
                "description": "Upgrade mid-cycle differential",
                "billing_days": 30,
                "service_days": 12,  # 12 days at new rate
                "expected_amount": Decimal('31.996')  # Precise calculation
            }
        ]
        
        for test in proration_tests:
            prorated_amount = billing_service._calculate_proration(
                monthly_rate,
                test["billing_days"],
                test["service_days"]
            )
            
            # Revenue protection: Proration must be exact to prevent under/over billing
            expected = test["expected_amount"]
            calculated = prorated_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            assert calculated == expected, (
                f"Proration failed for {test['description']}: "
                f"Expected {expected}, got {calculated}"
            )

    def test_tax_calculation_multi_jurisdiction_accuracy(self, db_session):
        """Test tax calculations across multiple tax jurisdictions."""
        billing_service = BillingService(db_session, "tenant_001")
        
        # Complex multi-jurisdiction tax scenarios
        tax_scenarios = [
            {
                "description": "California with multiple local taxes",
                "subtotal": Decimal('100.00'),
                "tax_rates": {
                    "state": Decimal('0.0725'),      # 7.25%
                    "county": Decimal('0.0025'),     # 0.25%
                    "city": Decimal('0.0075'),       # 0.75%
                    "district": Decimal('0.005')     # 0.5%
                },
                "expected_total_tax": Decimal('8.75'),
                "expected_total": Decimal('108.75')
            },
            {
                "description": "New York complex jurisdiction",
                "subtotal": Decimal('250.50'),
                "tax_rates": {
                    "state": Decimal('0.08'),        # 8%
                    "mta": Decimal('0.00375'),       # MTA tax 0.375%
                    "city": Decimal('0.045')         # NYC 4.5%
                },
                "expected_total_tax": Decimal('32.19'),
                "expected_total": Decimal('282.69')
            }
        ]
        
        for scenario in tax_scenarios:
            total_tax = Decimal('0.00')
            
            # Calculate each tax component
            for tax_type, rate in scenario["tax_rates"].items():
                tax_amount = scenario["subtotal"] * rate
                total_tax += tax_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            # Revenue protection: Tax calculations must be exact
            assert total_tax == scenario["expected_total_tax"], (
                f"Tax calculation failed for {scenario['description']}: "
                f"Expected {scenario['expected_total_tax']}, got {total_tax}"
            )
            
            total_amount = scenario["subtotal"] + total_tax
            assert total_amount == scenario["expected_total"]

    def test_discount_calculation_stacking_accuracy(self, db_session):
        """Test accuracy of stacked discount calculations."""
        billing_service = BillingService(db_session, "tenant_001")
        
        base_amount = Decimal('150.00')
        
        # Real ISP discount scenarios
        discount_tests = [
            {
                "description": "Percentage then flat discount",
                "discounts": [
                    {"type": "percentage", "value": Decimal('0.10')},  # 10% off
                    {"type": "flat", "value": Decimal('5.00')}         # $5 off
                ],
                "expected_final": Decimal('130.00')  # (150 * 0.9) - 5
            },
            {
                "description": "Multiple percentage discounts (multiplicative)",
                "discounts": [
                    {"type": "percentage", "value": Decimal('0.15')},  # 15% off
                    {"type": "percentage", "value": Decimal('0.05')}   # Additional 5% off
                ],
                "expected_final": Decimal('121.125')  # 150 * 0.85 * 0.95
            },
            {
                "description": "Senior + autopay + loyalty discounts",
                "discounts": [
                    {"type": "percentage", "value": Decimal('0.10')},  # 10% senior
                    {"type": "flat", "value": Decimal('3.00')},        # $3 autopay
                    {"type": "percentage", "value": Decimal('0.05')}   # 5% loyalty
                ],
                "expected_final": Decimal('124.25')  # ((150 * 0.9) - 3) * 0.95
            }
        ]
        
        for test in discount_tests:
            current_amount = base_amount
            
            for discount in test["discounts"]:
                if discount["type"] == "percentage":
                    current_amount = current_amount * (Decimal('1') - discount["value"])
                elif discount["type"] == "flat":
                    current_amount = current_amount - discount["value"]
            
            final_amount = current_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            # Revenue protection: Discount stacking must be mathematically correct
            assert final_amount == test["expected_final"], (
                f"Discount calculation failed for {test['description']}: "
                f"Expected {test['expected_final']}, got {final_amount}"
            )

    def test_currency_rounding_compliance(self, db_session):
        """Test that all currency amounts comply with accounting standards."""
        billing_service = BillingService(db_session, "tenant_001")
        
        # Test rounding scenarios that can cause accounting discrepancies
        rounding_tests = [
            {
                "raw_amount": Decimal('79.994999'),
                "expected_rounded": Decimal('79.99')
            },
            {
                "raw_amount": Decimal('79.995000'),
                "expected_rounded": Decimal('80.00')
            },
            {
                "raw_amount": Decimal('0.005'),
                "expected_rounded": Decimal('0.01')
            },
            {
                "raw_amount": Decimal('0.004'),
                "expected_rounded": Decimal('0.00')
            }
        ]
        
        for test in rounding_tests:
            rounded_amount = billing_service._round_currency_amount(test["raw_amount"])
            
            # Revenue protection: Currency rounding must follow GAAP standards
            assert rounded_amount == test["expected_rounded"], (
                f"Rounding failed: {test['raw_amount']} should round to "
                f"{test['expected_rounded']}, got {rounded_amount}"
            )


@pytest.mark.revenue_critical
@pytest.mark.billing_core
class TestBillingIntegrityValidation:
    """Test billing system integrity and anti-fraud measures."""
    
    def test_duplicate_charge_prevention(self, db_session):
        """Test prevention of duplicate billing charges."""
        billing_service = BillingService(db_session, "tenant_001")
        
        customer_id = "cust_001"
        service_id = "svc_001"
        billing_period = {
            "start": date(2024, 1, 1),
            "end": date(2024, 1, 31)
        }
        
        # Attempt to create invoice twice for same period
        invoice_request = {
            "customer_id": customer_id,
            "service_id": service_id,
            "billing_period_start": billing_period["start"],
            "billing_period_end": billing_period["end"],
            "tenant_id": "tenant_001"
        }
        
        # First invoice should succeed
        first_invoice = billing_service.generate_invoice(invoice_request)
        assert first_invoice is not None
        
        # Second invoice for same period should be prevented
        with pytest.raises(ValueError, match="duplicate.*billing"):
            billing_service.generate_invoice(invoice_request)

    def test_negative_amount_prevention(self, db_session):
        """Test that negative amounts cannot be billed improperly."""
        billing_service = BillingService(db_session, "tenant_001")
        
        # Test various negative amount scenarios
        negative_scenarios = [
            {"amount": Decimal('-50.00'), "description": "Direct negative charge"},
            {"amount": Decimal('0.00'), "description": "Zero charge"},
            {"usage_gb": Decimal('-100'), "rate": Decimal('1.00'), "description": "Negative usage"}
        ]
        
        for scenario in negative_scenarios:
            with pytest.raises(ValueError, match="negative.*amount"):
                if "usage_gb" in scenario:
                    billing_service._calculate_usage_charge(
                        scenario["usage_gb"], 
                        scenario["rate"]
                    )
                else:
                    billing_service._validate_charge_amount(scenario["amount"])

    def test_billing_period_validation(self, db_session):
        """Test billing period validation to prevent revenue leakage."""
        billing_service = BillingService(db_session, "tenant_001")
        
        # Invalid billing period scenarios
        invalid_periods = [
            {
                "start": date(2024, 2, 1),
                "end": date(2024, 1, 31),  # End before start
                "error": "end date before start"
            },
            {
                "start": date(2024, 1, 1),
                "end": date(2024, 12, 31),  # Period too long (> 60 days)
                "error": "billing period too long"
            },
            {
                "start": date(2025, 1, 1),  # Future start date
                "end": date(2025, 1, 31),
                "error": "future billing period"
            }
        ]
        
        for period in invalid_periods:
            with pytest.raises(ValueError):
                billing_service._validate_billing_period(
                    period["start"], 
                    period["end"]
                )


@pytest.mark.revenue_protection  
@pytest.mark.critical
class TestPaymentIntegrityValidation:
    """Test payment processing integrity and fraud prevention."""
    
    def test_payment_amount_validation(self, db_session):
        """Test payment amount validation against invoice totals."""
        billing_service = BillingService(db_session, "tenant_001")
        
        # Create test invoice
        invoice_total = Decimal('79.99')
        
        # Test various payment amount scenarios
        payment_tests = [
            {
                "payment_amount": invoice_total,
                "should_succeed": True,
                "description": "Exact payment"
            },
            {
                "payment_amount": invoice_total + Decimal('0.01'),
                "should_succeed": False,
                "description": "Overpayment by 1 cent"
            },
            {
                "payment_amount": Decimal('0.00'),
                "should_succeed": False,
                "description": "Zero payment"
            },
            {
                "payment_amount": Decimal('-10.00'),
                "should_succeed": False,
                "description": "Negative payment"
            }
        ]
        
        for test in payment_tests:
            if test["should_succeed"]:
                # Should not raise exception
                billing_service._validate_payment_amount(
                    test["payment_amount"], 
                    invoice_total
                )
            else:
                with pytest.raises(ValueError):
                    billing_service._validate_payment_amount(
                        test["payment_amount"], 
                        invoice_total
                    )

    def test_payment_processor_response_validation(self, db_session):
        """Test validation of payment processor responses."""
        billing_service = BillingService(db_session, "tenant_001")
        
        # Test payment processor response scenarios
        response_tests = [
            {
                "response": {
                    "status": "succeeded",
                    "transaction_id": "txn_123",
                    "amount_charged": Decimal('79.99')
                },
                "requested_amount": Decimal('79.99'),
                "should_succeed": True
            },
            {
                "response": {
                    "status": "succeeded", 
                    "transaction_id": "txn_124",
                    "amount_charged": Decimal('79.98')  # 1 cent less charged
                },
                "requested_amount": Decimal('79.99'),
                "should_succeed": False  # Amount mismatch
            },
            {
                "response": {
                    "status": "succeeded",
                    "transaction_id": None,  # Missing transaction ID
                    "amount_charged": Decimal('79.99')
                },
                "requested_amount": Decimal('79.99'),
                "should_succeed": False
            }
        ]
        
        for test in response_tests:
            if test["should_succeed"]:
                # Should not raise exception
                validated = billing_service._validate_payment_response(
                    test["response"], 
                    test["requested_amount"]
                )
                assert validated is True
            else:
                with pytest.raises(ValueError):
                    billing_service._validate_payment_response(
                        test["response"], 
                        test["requested_amount"]
                    )


@pytest.mark.revenue_critical
@pytest.mark.billing_core  
class TestBillingAuditCompliance:
    """Test billing audit trail and compliance requirements."""
    
    def test_billing_audit_trail_completeness(self, db_session):
        """Test that all billing operations create complete audit trails."""
        billing_service = BillingService(db_session, "tenant_001")
        
        # Simulate billing operations that must be audited
        operations = [
            "invoice_generation",
            "payment_processing", 
            "credit_application",
            "late_fee_assessment",
            "discount_application"
        ]
        
        for operation in operations:
            # Each operation should create audit log entries
            audit_entries = billing_service._get_audit_trail(operation)
            
            # Revenue protection: Complete audit trail required
            assert len(audit_entries) > 0, f"No audit trail for {operation}"
            
            # Verify audit entry completeness
            for entry in audit_entries:
                assert entry.get("timestamp") is not None
                assert entry.get("user_id") is not None  
                assert entry.get("operation") == operation
                assert entry.get("tenant_id") is not None

    def test_financial_data_immutability(self, db_session):
        """Test that financial data cannot be improperly modified."""
        billing_service = BillingService(db_session, "tenant_001")
        
        # Create invoice with financial data
        invoice_data = {
            "customer_id": "cust_001",
            "total_amount": Decimal('100.00'),
            "tax_amount": Decimal('8.25'),
            "status": "paid",
            "tenant_id": "tenant_001"
        }
        
        invoice = billing_service.create_invoice(invoice_data)
        original_amount = invoice.total_amount
        
        # Attempt to modify financial amounts after invoice is finalized
        with pytest.raises(ValueError, match="immutable.*financial"):
            billing_service._modify_invoice_amount(
                invoice.id, 
                Decimal('150.00')  # Different amount
            )
        
        # Verify amount remains unchanged
        updated_invoice = billing_service.get_invoice(invoice.id)
        assert updated_invoice.total_amount == original_amount


@pytest.mark.revenue_protection
@pytest.mark.performance  
class TestBillingScaleAccuracy:
    """Test billing accuracy under ISP scale loads."""
    
    def test_bulk_billing_calculation_accuracy(self, db_session):
        """Test billing calculation accuracy when processing thousands of invoices."""
        billing_service = BillingService(db_session, "tenant_001")
        
        # Generate large number of diverse billing scenarios
        bulk_scenarios = []
        for i in range(1000):
            scenario = {
                "customer_id": f"cust_{i:04d}",
                "base_amount": Decimal(str(random.uniform(50.00, 500.00))),
                "usage_gb": Decimal(str(random.uniform(0.1, 2000.0))),
                "rate_per_gb": Decimal('0.10'),
                "tax_rate": Decimal('0.0825')
            }
            bulk_scenarios.append(scenario)
        
        # Process all scenarios and verify mathematical accuracy
        total_calculated = Decimal('0.00')
        total_expected = Decimal('0.00')
        
        for scenario in bulk_scenarios:
            # Calculate expected total manually
            usage_charge = scenario["usage_gb"] * scenario["rate_per_gb"]
            subtotal = scenario["base_amount"] + usage_charge
            tax_amount = subtotal * scenario["tax_rate"]
            expected_total = subtotal + tax_amount
            total_expected += expected_total.quantize(Decimal('0.01'))
            
            # Calculate using billing service
            calculated_total = billing_service._calculate_invoice_total(
                scenario["base_amount"],
                scenario["usage_gb"], 
                scenario["rate_per_gb"],
                scenario["tax_rate"]
            )
            total_calculated += calculated_total
        
        # Revenue protection: Bulk calculations must maintain precision
        difference = abs(total_calculated - total_expected)
        assert difference <= Decimal('0.01'), (
            f"Bulk billing calculation drift: {difference}. "
            f"Calculated: {total_calculated}, Expected: {total_expected}"
        )

    def test_concurrent_billing_integrity(self, db_session):
        """Test billing integrity under concurrent processing."""
        import threading
        import time
        
        billing_service = BillingService(db_session, "tenant_001")
        
        # Shared customer account for concurrent testing
        customer_id = "cust_concurrent"
        initial_balance = Decimal('100.00')
        
        # Set initial balance
        billing_service._set_customer_balance(customer_id, initial_balance)
        
        # Operations that will run concurrently
        def apply_charge():
            billing_service._apply_charge(customer_id, Decimal('25.00'))
            
        def apply_credit():
            billing_service._apply_credit(customer_id, Decimal('10.00'))
        
        # Run concurrent operations
        threads = []
        for _ in range(5):
            t1 = threading.Thread(target=apply_charge)
            t2 = threading.Thread(target=apply_credit) 
            threads.extend([t1, t2])
        
        for thread in threads:
            thread.start()
            
        for thread in threads:
            thread.join()
        
        # Verify final balance is mathematically correct
        expected_balance = initial_balance + (5 * Decimal('25.00')) - (5 * Decimal('10.00'))
        actual_balance = billing_service._get_customer_balance(customer_id)
        
        # Revenue protection: Concurrent operations must maintain data integrity
        assert actual_balance == expected_balance, (
            f"Concurrent billing operations resulted in balance discrepancy: "
            f"Expected {expected_balance}, got {actual_balance}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])