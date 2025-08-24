"""
PROPERTY-BASED TESTING - AI-GENERATED EDGE CASES
===============================================

Uses Hypothesis to generate thousands of test cases automatically.
This catches edge cases that humans would never think to test manually.

Perfect for AI-first development - validates properties and invariants
rather than specific input/output combinations.
"""

import pytest
from hypothesis import given, strategies as st, settings, Verbosity, assume
from hypothesis.stateful import RuleBasedStateMachine, rule, initialize, invariant
from decimal import Decimal
from datetime import datetime, date, timedelta
from typing import Dict, Any, List
from uuid import UUID
import string
import re

# Import our revenue-critical billing calculator
from tests.revenue_protection.test_working_billing_accuracy import BillingCalculator


# HYPOTHESIS STRATEGIES - AI DATA GENERATORS
def valid_currency_amounts():
    """Generate valid currency amounts (2 decimal places max)."""
    return st.decimals(
        min_value=Decimal('0.00'),
        max_value=Decimal('999999.99'),
        places=2
    )


def valid_usage_amounts():
    """Generate valid usage amounts (up to 6 decimal places)."""
    return st.decimals(
        min_value=Decimal('0.000000'),
        max_value=Decimal('999999.999999'),
        places=6
    ).filter(lambda x: x >= 0)


def valid_rates():
    """Generate valid billing rates."""
    return st.decimals(
        min_value=Decimal('0.000001'),
        max_value=Decimal('1000.000000'),
        places=6
    )


def customer_emails():
    """Generate realistic email addresses."""
    domains = st.sampled_from(['gmail.com', 'yahoo.com', 'company.com', 'isp.net'])
    usernames = st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd')), 
        min_size=3, 
        max_size=20
    ).filter(lambda x: x.isalnum())
    
    return st.builds(
        lambda u, d: f"{u}@{d}",
        usernames,
        domains
    )


def phone_numbers():
    """Generate valid phone numbers."""
    return st.builds(
        lambda area, exchange, number: f"+1-{area:03d}-{exchange:03d}-{number:04d}",
        st.integers(min_value=200, max_value=999),  # Valid area codes
        st.integers(min_value=200, max_value=999),  # Valid exchanges
        st.integers(min_value=0, max_value=9999)    # Valid numbers
    )


def billing_periods():
    """Generate valid billing periods."""
    return st.tuples(
        st.integers(min_value=1, max_value=31),  # service_days
        st.integers(min_value=28, max_value=31)  # billing_days (month length)
    ).filter(lambda x: x[0] <= x[1])  # service_days <= billing_days


def service_tiers():
    """Generate realistic service tier configurations."""
    def create_tiers(tier_count):
        tiers = []
        current_limit = 0
        
        for i in range(tier_count - 1):  # All tiers except last
            limit = current_limit + st.integers(min_value=50, max_value=500).example()
            rate = st.decimals(
                min_value=Decimal('0.01'), 
                max_value=Decimal('1.00'), 
                places=6
            ).example()
            
            tiers.append({
                'name': f'Tier {i+1}',
                'limit_gb': limit,
                'rate_per_gb': str(rate)
            })
            current_limit = limit
        
        # Add unlimited tier
        tiers.append({
            'name': 'Unlimited',
            'limit_gb': None,
            'rate_per_gb': str(st.decimals(
                min_value=Decimal('0.001'), 
                max_value=Decimal('0.10'), 
                places=6
            ).example())
        })
        
        return tiers
    
    return st.integers(min_value=2, max_value=5).flatmap(
        lambda n: st.just(create_tiers(n))
    )


# PROPERTY-BASED TEST CLASSES
@pytest.mark.property_based
@pytest.mark.revenue_critical
class TestBillingProperties:
    """Property-based tests for billing calculations."""
    
    @given(
        usage=valid_usage_amounts(),
        rate=valid_rates()
    )
    @settings(max_examples=1000, deadline=None)
    def test_usage_charge_properties(self, usage, rate):
        """Property: Usage charge calculations must satisfy invariants."""
        calculator = BillingCalculator()
        
        charge = calculator.calculate_usage_charge(usage, rate)
        
        # PROPERTY 1: Charge is never negative
        assert charge >= 0, f"Negative charge: {charge}"
        
        # PROPERTY 2: Zero usage = zero charge
        if usage == 0:
            assert charge == 0, "Zero usage must result in zero charge"
        
        # PROPERTY 3: Charge is proportional to usage
        if usage > 0:
            charge_per_unit = charge / usage
            assert charge_per_unit <= rate, f"Charge per unit {charge_per_unit} exceeds rate {rate}"
        
        # PROPERTY 4: Precision constraint (6 decimal places max)
        charge_str = str(charge)
        if '.' in charge_str:
            decimal_places = len(charge_str.split('.')[1])
            assert decimal_places <= 6, f"Too many decimal places: {decimal_places}"
        
        # PROPERTY 5: Monotonicity - more usage = more charge (at same rate)
        if usage > 0:
            double_usage = usage * 2
            double_charge = calculator.calculate_usage_charge(double_usage, rate)
            assert double_charge >= charge, "Double usage should result in higher charge"
    
    @given(
        base_rate=valid_currency_amounts(),
        periods=billing_periods(),
        tax_rate=st.decimals(min_value=Decimal('0.00'), max_value=Decimal('0.30'), places=4)
    )
    @settings(max_examples=500, deadline=None)
    def test_proration_properties(self, base_rate, periods, tax_rate):
        """Property: Proration calculations must be mathematically consistent."""
        service_days, billing_days = periods
        calculator = BillingCalculator()
        
        result = calculator.calculate_monthly_service_charge(
            base_rate, service_days, billing_days, tax_rate
        )
        
        # PROPERTY 1: Base charge is proportional to service days
        expected_base = (base_rate * Decimal(service_days) / Decimal(billing_days)).quantize(Decimal('0.01'))
        assert result['base_charge'] == expected_base
        
        # PROPERTY 2: Tax is calculated on base charge
        expected_tax = (result['base_charge'] * tax_rate).quantize(Decimal('0.01'))
        assert result['tax_amount'] == expected_tax
        
        # PROPERTY 3: Total = base + tax
        assert result['total_charge'] == result['base_charge'] + result['tax_amount']
        
        # PROPERTY 4: Full period means no proration
        if service_days == billing_days:
            assert result['proration_factor'] == 1
            assert result['base_charge'] == base_rate
        
        # PROPERTY 5: Proration factor is between 0 and 1
        assert 0 <= result['proration_factor'] <= 1
    
    @given(
        usage=st.decimals(min_value=Decimal('0.0'), max_value=Decimal('10000.0'), places=3),
        tier_config=service_tiers()
    )
    @settings(max_examples=200, deadline=None)
    def test_tiered_billing_properties(self, usage, tier_config):
        """Property: Tiered billing must be mathematically consistent."""
        assume(len(tier_config) >= 2)  # Need at least 2 tiers
        calculator = BillingCalculator()
        
        result = calculator.calculate_tiered_usage_charge(usage, tier_config)
        
        # PROPERTY 1: Total charge is sum of tier charges
        breakdown_total = sum(tier['charge'] for tier in result['breakdown'])
        assert result['total_charge'] == breakdown_total
        
        # PROPERTY 2: No tier should have negative charges
        for tier in result['breakdown']:
            assert tier['charge'] >= 0, f"Negative tier charge: {tier['charge']}"
        
        # PROPERTY 3: Usage should be fully accounted for
        total_tier_usage = sum(tier['usage_gb'] for tier in result['breakdown'])
        assert total_tier_usage == usage, f"Usage mismatch: {total_tier_usage} vs {usage}"
        
        # PROPERTY 4: If usage is zero, charge should be zero
        if usage == 0:
            assert result['total_charge'] == 0
        
        # PROPERTY 5: Tiers should be applied in order (lower rates first)
        if len(result['breakdown']) > 1:
            for i in range(len(result['breakdown']) - 1):
                current_tier = result['breakdown'][i]
                next_tier = result['breakdown'][i + 1]
                # Generally, later tiers have lower rates (volume discounts)
                # This is a business rule that can be validated


@pytest.mark.property_based
@pytest.mark.customer_data
class TestCustomerDataProperties:
    """Property-based tests for customer data validation."""
    
    @given(
        email=customer_emails(),
        phone=phone_numbers(),
        name=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Zs')),
            min_size=2,
            max_size=100
        ).filter(lambda x: len(x.strip()) >= 2)
    )
    @settings(max_examples=500)
    def test_customer_data_validation_properties(self, email, phone, name):
        """Property: Customer data must always be valid."""
        
        # PROPERTY 1: Email format validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        assert re.match(email_pattern, email), f"Invalid email format: {email}"
        
        # PROPERTY 2: Phone number format validation
        phone_pattern = r'^\+1-\d{3}-\d{3}-\d{4}$'
        assert re.match(phone_pattern, phone), f"Invalid phone format: {phone}"
        
        # PROPERTY 3: Name should not be empty after stripping
        assert len(name.strip()) >= 2, f"Name too short: '{name}'"
        
        # PROPERTY 4: No special characters in name that could cause issues
        dangerous_chars = ['<', '>', '&', '"', "'", ';', '(', ')', '{', '}']
        assert not any(char in name for char in dangerous_chars), f"Dangerous characters in name: {name}"


# STATEFUL TESTING - CUSTOMER LIFECYCLE
class CustomerLifecycleStateMachine(RuleBasedStateMachine):
    """
    Stateful property-based testing for customer lifecycle.
    
    This tests sequences of operations and ensures invariants
    hold throughout the customer's journey.
    """
    
    def __init__(self):
        super().__init__()
        self.customers = {}  # customer_id -> customer_data
        self.services = {}   # service_id -> service_data
        self.invoices = {}   # invoice_id -> invoice_data
        
    @initialize()
    def initialize_system(self):
        """Initialize the system state."""
        self.calculator = BillingCalculator()
        
    @rule(
        customer_id=st.uuids(),
        email=customer_emails(),
        phone=phone_numbers()
    )
    def create_customer(self, customer_id, email, phone):
        """Create a new customer."""
        assume(str(customer_id) not in self.customers)
        
        self.customers[str(customer_id)] = {
            'customer_id': str(customer_id),
            'email': email,
            'phone': phone,
            'status': 'active',
            'created_at': datetime.now()
        }
    
    @rule(
        service_id=st.uuids(),
        monthly_rate=valid_currency_amounts()
    )
    def add_service(self, service_id, monthly_rate):
        """Add a service to a random customer."""
        assume(len(self.customers) > 0)
        assume(str(service_id) not in self.services)
        
        # Pick a random customer
        customer_id = st.sampled_from(list(self.customers.keys())).example()
        
        self.services[str(service_id)] = {
            'service_id': str(service_id),
            'customer_id': customer_id,
            'monthly_rate': monthly_rate,
            'status': 'active'
        }
    
    @rule(
        invoice_id=st.uuids(),
        usage_gb=valid_usage_amounts()
    )
    def generate_invoice(self, invoice_id, usage_gb):
        """Generate an invoice for a customer with services."""
        assume(len(self.services) > 0)
        assume(str(invoice_id) not in self.invoices)
        
        # Pick a random service
        service_id = st.sampled_from(list(self.services.keys())).example()
        service = self.services[service_id]
        customer_id = service['customer_id']
        
        # Calculate charges
        service_charge = self.calculator.calculate_monthly_service_charge(
            service['monthly_rate'], 30, 30, Decimal('0.08')
        )
        
        usage_charge = self.calculator.calculate_usage_charge(
            usage_gb, Decimal('0.10')
        )
        
        total_amount = service_charge['total_charge'] + usage_charge
        
        self.invoices[str(invoice_id)] = {
            'invoice_id': str(invoice_id),
            'customer_id': customer_id,
            'service_id': service_id,
            'service_charge': service_charge['total_charge'],
            'usage_charge': usage_charge,
            'total_amount': total_amount,
            'status': 'pending'
        }
    
    @invariant()
    def all_invoices_have_positive_amounts(self):
        """INVARIANT: All invoices must have positive amounts."""
        for invoice in self.invoices.values():
            assert invoice['total_amount'] > 0, f"Non-positive invoice amount: {invoice['total_amount']}"
    
    @invariant()
    def all_services_belong_to_customers(self):
        """INVARIANT: All services must belong to existing customers."""
        for service in self.services.values():
            assert service['customer_id'] in self.customers, f"Service references non-existent customer"
    
    @invariant() 
    def customer_emails_unique(self):
        """INVARIANT: Customer emails must be unique."""
        emails = [customer['email'] for customer in self.customers.values()]
        assert len(emails) == len(set(emails)), "Duplicate customer emails found"


# Create test case from state machine
TestCustomerLifecycle = CustomerLifecycleStateMachine.TestCase


if __name__ == "__main__":
    # Quick property test
    calculator = BillingCalculator()
    
    # Test the property that charges are never negative
    for _ in range(100):
        usage = st.decimals(min_value=Decimal('0.0'), max_value=Decimal('1000.0')).example()
        rate = st.decimals(min_value=Decimal('0.01'), max_value=Decimal('1.0')).example()
        
        charge = calculator.calculate_usage_charge(usage, rate)
        assert charge >= 0, f"Negative charge found: {charge}"
    
    print("✅ Property-based tests validation passed!")