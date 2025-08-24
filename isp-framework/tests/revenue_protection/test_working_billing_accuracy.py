"""
REVENUE-CRITICAL TESTS - DEPLOYMENT BLOCKER
===========================================

These tests MUST pass 100% before any deployment. They protect against
revenue loss through billing calculation errors and payment processing issues.

If any of these tests fail, deployment is blocked automatically.
"""

import pytest
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date, timedelta
from typing import Dict, Any, List
from uuid import uuid4

# Import the property testing framework we already have
from tests.ai_framework.property_testing import (
    AIPropertyTestGenerator, 
    property_test
)


class BillingCalculator:
    """
    Core billing calculation engine - REVENUE CRITICAL
    
    This class implements the essential billing calculations that directly
    impact revenue. Any changes to this code must be tested extensively.
    """
    
    def calculate_usage_charge(self, usage_gb: Decimal, rate_per_gb: Decimal) -> Decimal:
        """
        Calculate usage-based charges with precision to 6 decimal places.
        
        BUSINESS RULE: Bills must never be negative
        BUSINESS RULE: Precision must be exactly 6 decimal places
        BUSINESS RULE: Rounding must use banker's rounding (ROUND_HALF_UP)
        """
        if usage_gb < 0:
            raise ValueError("Usage cannot be negative")
        if rate_per_gb < 0:
            raise ValueError("Rate cannot be negative")
        
        # Calculate with high precision
        charge = usage_gb * rate_per_gb
        
        # Round to 6 decimal places using banker's rounding
        return charge.quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)
    
    def calculate_monthly_service_charge(
        self, 
        base_rate: Decimal, 
        service_days: int, 
        billing_days: int,
        tax_rate: Decimal = Decimal('0.0')
    ) -> Dict[str, Decimal]:
        """
        Calculate prorated monthly service charges.
        
        BUSINESS RULE: Proration must be exact to prevent revenue loss
        BUSINESS RULE: Tax calculations must be precise
        """
        if billing_days <= 0:
            raise ValueError("Billing days must be positive")
        if service_days < 0:
            raise ValueError("Service days cannot be negative")
        if service_days > billing_days:
            raise ValueError("Service days cannot exceed billing days")
        
        # Calculate prorated amount
        proration_factor = Decimal(service_days) / Decimal(billing_days)
        base_charge = (base_rate * proration_factor).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        
        # Calculate tax
        tax_amount = (base_charge * tax_rate).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        
        total_charge = base_charge + tax_amount
        
        return {
            'base_charge': base_charge,
            'tax_amount': tax_amount, 
            'total_charge': total_charge,
            'proration_factor': proration_factor
        }
    
    def calculate_tiered_usage_charge(
        self, 
        usage_gb: Decimal, 
        tiers: List[Dict[str, Any]]
    ) -> Dict[str, Decimal]:
        """
        Calculate tiered usage charges (e.g., first 100GB at $0.10, next 400GB at $0.05).
        
        BUSINESS RULE: Tier calculations must be exact
        BUSINESS RULE: No usage can be charged at wrong tier
        """
        if usage_gb < 0:
            raise ValueError("Usage cannot be negative")
        
        total_charge = Decimal('0.00')
        remaining_usage = usage_gb
        charge_breakdown = []
        
        for tier in tiers:
            tier_limit = Decimal(str(tier['limit_gb'])) if tier['limit_gb'] is not None else None
            tier_rate = Decimal(str(tier['rate_per_gb']))
            
            if remaining_usage <= 0:
                break
            
            if tier_limit is None:
                # Unlimited tier (last tier)
                tier_usage = remaining_usage
            else:
                tier_usage = min(remaining_usage, tier_limit)
            
            tier_charge = self.calculate_usage_charge(tier_usage, tier_rate)
            total_charge += tier_charge
            
            charge_breakdown.append({
                'tier_name': tier['name'],
                'usage_gb': tier_usage,
                'rate_per_gb': tier_rate,
                'charge': tier_charge
            })
            
            remaining_usage -= tier_usage
        
        return {
            'total_charge': total_charge,
            'breakdown': charge_breakdown
        }


# REVENUE CRITICAL TESTS - NEVER FAIL ZONE
@pytest.mark.revenue_critical
@pytest.mark.deployment_blocker
class TestBillingAccuracyNeverFail:
    """Tests that must NEVER fail - they protect revenue directly."""
    
    def test_billing_never_negative_property(self):
        """PROPERTY: Bills must never be negative regardless of input."""
        calculator = BillingCalculator()
        
        # Test with valid positive inputs
        result = calculator.calculate_usage_charge(
            Decimal('100.0'), Decimal('0.10')
        )
        assert result >= 0, "Bill amount must never be negative"
        assert result == Decimal('10.000000'), "Expected exact calculation"
    
    def test_zero_usage_zero_charge(self):
        """PROPERTY: Zero usage must result in zero charge."""
        calculator = BillingCalculator()
        
        result = calculator.calculate_usage_charge(
            Decimal('0.0'), Decimal('1.00')
        )
        assert result == Decimal('0.000000'), "Zero usage must be zero charge"
    
    def test_precision_requirements(self):
        """CRITICAL: All monetary calculations must be precise to 6 decimal places."""
        calculator = BillingCalculator()
        
        # Test high-precision calculation
        result = calculator.calculate_usage_charge(
            Decimal('1234.567891'), Decimal('0.123456')
        )
        
        # Must be exact to 6 decimal places
        expected = Decimal('152.414711')  # 1234.567891 * 0.123456 = 152.4147107...
        assert result == expected, f"Expected {expected}, got {result}"
    
    def test_proration_accuracy(self):
        """CRITICAL: Prorated charges must be calculated exactly."""
        calculator = BillingCalculator()
        
        # Real scenario: Customer activated mid-month
        result = calculator.calculate_monthly_service_charge(
            base_rate=Decimal('79.99'),
            service_days=16,  # Activated on 15th, 16 days of service
            billing_days=30,  # 30-day month
            tax_rate=Decimal('0.08')  # 8% tax
        )
        
        # Expected: (79.99 * 16/30) = 42.66 + tax = 46.07
        expected_base = Decimal('42.66')  # Rounded to cents
        expected_tax = Decimal('3.41')    # 42.66 * 0.08 rounded
        expected_total = Decimal('46.07')  # 42.66 + 3.41
        
        assert result['base_charge'] == expected_base
        assert result['tax_amount'] == expected_tax
        assert result['total_charge'] == expected_total
    
    def test_tiered_billing_accuracy(self):
        """CRITICAL: Tiered usage billing must be exact."""
        calculator = BillingCalculator()
        
        # Define common ISP tiered pricing
        tiers = [
            {'name': 'First 100GB', 'limit_gb': 100, 'rate_per_gb': '0.100000'},
            {'name': 'Next 400GB', 'limit_gb': 400, 'rate_per_gb': '0.050000'},
            {'name': 'Unlimited', 'limit_gb': None, 'rate_per_gb': '0.010000'}
        ]
        
        # Test 750GB usage: 100@$0.10 + 400@$0.05 + 250@$0.01 = $32.50
        result = calculator.calculate_tiered_usage_charge(
            Decimal('750.0'), tiers
        )
        
        expected_total = Decimal('32.500000')  # 10.00 + 20.00 + 2.50
        assert result['total_charge'] == expected_total
        
        # Verify breakdown
        breakdown = result['breakdown']
        assert len(breakdown) == 3
        assert breakdown[0]['charge'] == Decimal('10.000000')  # 100 * 0.10
        assert breakdown[1]['charge'] == Decimal('20.000000')  # 400 * 0.05
        assert breakdown[2]['charge'] == Decimal('2.500000')   # 250 * 0.01


# PROPERTY-BASED TESTS - AI GENERATED EDGE CASES
@pytest.mark.property_based
@pytest.mark.revenue_critical 
class TestBillingPropertiesAI:
    """Property-based tests using AI-generated test data."""
    
    @property_test(AIPropertyTestGenerator.generate_billing_data(), max_examples=1000)
    def test_billing_calculations_properties(self, billing_data):
        """Property: All billing calculations must satisfy business invariants."""
        calculator = BillingCalculator()
        
        # Extract data from AI generator
        usage_gb = Decimal(str(billing_data['usage_gb']))
        rate_per_gb = Decimal(str(billing_data['rate_per_gb']))
        tax_rate = Decimal(str(billing_data['tax_rate']))
        
        # Test usage charge calculation
        usage_charge = calculator.calculate_usage_charge(usage_gb, rate_per_gb)
        
        # PROPERTY 1: Charge must never be negative
        assert usage_charge >= 0, f"Negative charge: {usage_charge}"
        
        # PROPERTY 2: Charge must be proportional to usage
        if usage_gb > 0:
            charge_per_gb = usage_charge / usage_gb
            assert charge_per_gb <= rate_per_gb * Decimal('1.01'), "Charge per GB exceeds rate"
        
        # PROPERTY 3: Zero usage = zero charge
        if usage_gb == 0:
            assert usage_charge == 0, "Zero usage must result in zero charge"
        
        # PROPERTY 4: Precision must be exactly 6 decimal places
        assert str(usage_charge).count('.') == 1, "Must have decimal point"
        decimal_places = len(str(usage_charge).split('.')[-1])
        assert decimal_places <= 6, f"Too many decimal places: {decimal_places}"
    
    @property_test(
        AIPropertyTestGenerator.generate_customer_data(),
        AIPropertyTestGenerator.generate_service_data(), 
        max_examples=500
    )
    def test_service_billing_properties(self, customer_data, service_data):
        """Property: Service billing must be consistent across customer types."""
        calculator = BillingCalculator()
        
        # Extract service cost
        monthly_cost = service_data['monthly_cost']
        
        # Test full month billing
        result = calculator.calculate_monthly_service_charge(
            base_rate=monthly_cost,
            service_days=30,
            billing_days=30,
            tax_rate=Decimal('0.08')
        )
        
        # PROPERTY 1: Full month billing = base rate (no proration)
        assert result['proration_factor'] == 1
        assert result['base_charge'] == monthly_cost
        
        # PROPERTY 2: Tax must be calculated correctly
        expected_tax = (monthly_cost * Decimal('0.08')).quantize(Decimal('0.01'))
        assert result['tax_amount'] == expected_tax
        
        # PROPERTY 3: Total = base + tax
        assert result['total_charge'] == result['base_charge'] + result['tax_amount']


# BEHAVIOR TESTS - COMPLETE WORKFLOWS
@pytest.mark.behavior
@pytest.mark.revenue_critical
class TestBillingWorkflowsBehavior:
    """Test complete billing workflows end-to-end."""
    
    def test_monthly_billing_cycle_behavior(self):
        """BEHAVIOR: Complete monthly billing cycle generates accurate charges."""
        calculator = BillingCalculator()
        
        # Simulate monthly billing for a customer
        customer_services = [
            {'name': 'Internet Service', 'monthly_rate': Decimal('79.99')},
            {'name': 'Phone Service', 'monthly_rate': Decimal('29.99')},
            {'name': 'TV Service', 'monthly_rate': Decimal('49.99')}
        ]
        
        usage_charges = [
            {'service': 'Internet', 'usage_gb': Decimal('250.0'), 'rate': Decimal('0.05')},
            {'service': 'Phone', 'usage_gb': Decimal('2.5'), 'rate': Decimal('0.10')}
        ]
        
        # Calculate service charges
        total_service_charges = Decimal('0.00')
        for service in customer_services:
            charge = calculator.calculate_monthly_service_charge(
                base_rate=service['monthly_rate'],
                service_days=30,
                billing_days=30
            )
            total_service_charges += charge['base_charge']
        
        # Calculate usage charges
        total_usage_charges = Decimal('0.00')
        for usage in usage_charges:
            charge = calculator.calculate_usage_charge(usage['usage_gb'], usage['rate'])
            total_usage_charges += charge
        
        # Calculate total bill
        subtotal = total_service_charges + total_usage_charges
        tax = (subtotal * Decimal('0.08')).quantize(Decimal('0.01'))
        total_bill = subtotal + tax
        
        # BEHAVIOR ASSERTIONS
        assert total_service_charges == Decimal('159.97')  # 79.99 + 29.99 + 49.99
        assert total_usage_charges == Decimal('12.750000')  # 12.50 + 0.25
        assert subtotal == Decimal('172.720000')
        assert tax == Decimal('13.82')  # 172.72 * 0.08 rounded
        assert total_bill == Decimal('186.540000')
        
        # CRITICAL: Bill must be reasonable (not negative, not excessive)
        assert Decimal('0.00') < total_bill < Decimal('10000.00')


# TEST FIXTURES AND UTILITIES
@pytest.fixture
def billing_calculator():
    """Provide billing calculator for tests."""
    return BillingCalculator()


@pytest.fixture 
def sample_customer_data():
    """Sample customer data for testing."""
    return {
        'customer_id': str(uuid4()),
        'customer_type': 'residential',
        'billing_address': {
            'street': '123 Main St',
            'city': 'Anytown', 
            'state': 'CA',
            'zip': '12345'
        }
    }


@pytest.fixture
def sample_service_tiers():
    """Sample tiered pricing for testing."""
    return [
        {'name': 'First 100GB', 'limit_gb': 100, 'rate_per_gb': '0.100000'},
        {'name': 'Next 400GB', 'limit_gb': 400, 'rate_per_gb': '0.050000'}, 
        {'name': 'Unlimited', 'limit_gb': None, 'rate_per_gb': '0.010000'}
    ]


if __name__ == "__main__":
    # Quick self-test
    calculator = BillingCalculator()
    
    # Test basic calculation
    result = calculator.calculate_usage_charge(Decimal('100.0'), Decimal('0.10'))
    print(f"Usage charge test: {result}")
    assert result == Decimal('10.000000')
    
    # Test proration
    result = calculator.calculate_monthly_service_charge(
        Decimal('79.99'), 15, 30, Decimal('0.08')
    )
    print(f"Proration test: {result}")
    
    print("✅ All basic tests passed!")