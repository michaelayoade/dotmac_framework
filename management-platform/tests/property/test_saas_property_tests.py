"""
SAAS PROPERTY-BASED TESTING - AI-GENERATED EDGE CASES
====================================================

Uses Hypothesis to generate thousands of test cases automatically for SaaS scenarios.
This catches edge cases that humans would never think to test manually.

Perfect for AI-first development - validates properties and invariants
for multi-tenant SaaS billing and provisioning.
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

# Import our SaaS billing calculator
from tests.revenue_protection.test_saas_billing_accuracy import SaaSBillingCalculator


# HYPOTHESIS STRATEGIES - AI DATA GENERATORS FOR SAAS
def valid_subscription_prices():
    """Generate valid SaaS subscription prices."""
    return st.decimals(
        min_value=Decimal('0.00'),
        max_value=Decimal('99999.99'),
        places=2
    )


def valid_usage_amounts():
    """Generate valid usage amounts for SaaS metrics."""
    return st.decimals(
        min_value=Decimal('0.0'),
        max_value=Decimal('999999.0'),
        places=3
    ).filter(lambda x: x >= 0)


def billing_periods():
    """Generate realistic billing periods for SaaS."""
    return st.tuples(
        st.integers(min_value=1, max_value=31),  # usage_days
        st.integers(min_value=28, max_value=31)  # billing_period_days
    ).filter(lambda x: x[0] <= x[1])  # usage_days <= billing_period_days


def tenant_names():
    """Generate realistic tenant names."""
    return st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs')),
        min_size=3,
        max_size=50
    ).filter(lambda x: len(x.strip()) >= 3 and not any(char in x for char in ['<', '>', '&', '"', "'", ';']))


def saas_plan_configurations():
    """Generate realistic SaaS plan configurations."""
    def create_plan(tier_level):
        base_price = 50 * tier_level  # $50, $100, $150, etc.
        user_limit = 25 * tier_level  # 25, 50, 75 users
        storage_limit = 100 * tier_level  # 100, 200, 300 GB
        api_limit = 10000 * tier_level  # 10k, 20k, 30k calls
        
        return {
            'name': f'Tier {tier_level}',
            'price': Decimal(str(base_price)),
            'limits': {
                'active_users': Decimal(str(user_limit)),
                'storage_gb': Decimal(str(storage_limit)),
                'api_calls': Decimal(str(api_limit))
            },
            'overage_rates': {
                'active_users': Decimal(str(5.0 - (0.5 * tier_level))),  # Volume discount
                'storage_gb': Decimal(str(1.0 - (0.1 * tier_level))),
                'api_calls': Decimal('0.001')
            }
        }
    
    return st.integers(min_value=1, max_value=5).map(create_plan)


def tenant_usage_patterns():
    """Generate realistic tenant usage patterns."""
    return st.fixed_dictionaries({
        'active_users': st.decimals(min_value=Decimal('1'), max_value=Decimal('500'), places=0),
        'storage_gb': st.decimals(min_value=Decimal('1.0'), max_value=Decimal('1000.0'), places=1),
        'api_calls': st.decimals(min_value=Decimal('100'), max_value=Decimal('100000'), places=0)
    })


# PROPERTY-BASED TEST CLASSES FOR SAAS
@pytest.mark.property_based
@pytest.mark.revenue_critical
@pytest.mark.saas_billing
class TestSaaSBillingProperties:
    """Property-based tests for SaaS billing calculations."""
    
    @given(
        plan_price=valid_subscription_prices(),
        periods=billing_periods()
    )
    @settings(max_examples=1000, deadline=None)
    def test_subscription_charge_properties(self, plan_price, periods):
        """Property: Subscription charge calculations must satisfy invariants."""
        usage_days, billing_period_days = periods
        calculator = SaaSBillingCalculator()
        
        result = calculator.calculate_subscription_charge(
            plan_price, usage_days, billing_period_days
        )
        
        # PROPERTY 1: Charge is never negative
        assert result['base_charge'] >= 0, f"Negative charge: {result['base_charge']}"
        
        # PROPERTY 2: Full period means no proration (charge equals plan price)
        if usage_days == billing_period_days:
            assert result['proration_factor'] == Decimal('1.0')
            assert result['base_charge'] == plan_price
        
        # PROPERTY 3: Proration factor is between 0 and 1
        assert 0 <= result['proration_factor'] <= 1
        
        # PROPERTY 4: Partial period means proportional charge
        if usage_days < billing_period_days:
            expected_factor = Decimal(usage_days) / Decimal(billing_period_days)
            assert result['proration_factor'] == expected_factor
            
            # Allow small rounding differences due to quantize
            expected_charge = (plan_price * expected_factor).quantize(Decimal('0.01'))
            assert result['base_charge'] == expected_charge
        
        # PROPERTY 5: Precision constraint (2 decimal places for money)
        charge_str = str(result['base_charge'])
        if '.' in charge_str:
            decimal_places = len(charge_str.split('.')[1])
            assert decimal_places <= 2, f"Too many decimal places: {decimal_places}"
        
        # PROPERTY 6: Monotonicity - more days = higher charge (same plan price)
        if usage_days > 0 and usage_days < billing_period_days:
            double_days = min(usage_days * 2, billing_period_days)
            double_result = calculator.calculate_subscription_charge(
                plan_price, double_days, billing_period_days
            )
            assert double_result['base_charge'] >= result['base_charge']
    
    @given(
        tenant_usage=tenant_usage_patterns(),
        plan_config=saas_plan_configurations()
    )
    @settings(max_examples=500, deadline=None)
    def test_usage_overage_properties(self, tenant_usage, plan_config):
        """Property: Usage overage calculations must be mathematically consistent."""
        calculator = SaaSBillingCalculator()
        
        result = calculator.calculate_tenant_usage_charges(
            tenant_usage, plan_config['limits'], plan_config['overage_rates']
        )
        
        # PROPERTY 1: Total overage is sum of individual charges
        breakdown_total = sum(
            item['charge'] for item in result['usage_breakdown'].values()
        )
        assert result['total_overage_charge'] == breakdown_total
        
        # PROPERTY 2: No metric should have negative charges
        for metric, breakdown in result['usage_breakdown'].items():
            assert breakdown['charge'] >= 0, f"Negative charge for {metric}: {breakdown['charge']}"
        
        # PROPERTY 3: Usage within limits = zero charge
        for metric, usage_amount in tenant_usage.items():
            if metric in plan_config['limits']:
                plan_limit = plan_config['limits'][metric]
                breakdown = result['usage_breakdown'][metric]
                
                if usage_amount <= plan_limit:
                    assert breakdown['charge'] == Decimal('0.00')
                    assert breakdown['overage'] == Decimal('0.00')
        
        # PROPERTY 4: Overage amount calculation accuracy
        for metric, breakdown in result['usage_breakdown'].items():
            if metric in tenant_usage:
                usage = tenant_usage[metric]
                limit = plan_config['limits'][metric]
                
                if usage > limit:
                    expected_overage = usage - limit
                    assert breakdown['overage'] == expected_overage
                else:
                    assert breakdown['overage'] == Decimal('0.00')
        
        # PROPERTY 5: Charge calculation accuracy
        for metric, breakdown in result['usage_breakdown'].items():
            if breakdown['overage'] > 0:
                overage_rate = plan_config['overage_rates'][metric]
                expected_charge = (breakdown['overage'] * overage_rate).quantize(Decimal('0.01'))
                assert breakdown['charge'] == expected_charge
    
    @given(
        subscription=valid_subscription_prices(),
        usage_charges=valid_subscription_prices(),
        tax_rate=st.decimals(min_value=Decimal('0.00'), max_value=Decimal('0.30'), places=4)
    )
    @settings(max_examples=300, deadline=None)
    def test_total_bill_properties(self, subscription, usage_charges, tax_rate):
        """Property: Total bill calculations must be mathematically consistent."""
        calculator = SaaSBillingCalculator()
        
        result = calculator.calculate_total_tenant_bill(
            subscription, usage_charges, tax_rate
        )
        
        # PROPERTY 1: Total = subscription + usage + tax
        assert result['total_amount'] == (
            result['subscription_charge'] + 
            result['usage_charges'] + 
            result['tax_amount']
        )
        
        # PROPERTY 2: Subtotal = subscription + usage
        assert result['subtotal'] == result['subscription_charge'] + result['usage_charges']
        
        # PROPERTY 3: Tax calculated on subtotal
        expected_tax = (result['subtotal'] * tax_rate).quantize(Decimal('0.01'))
        assert result['tax_amount'] == expected_tax
        
        # PROPERTY 4: All amounts are non-negative
        assert result['subscription_charge'] >= 0
        assert result['usage_charges'] >= 0
        assert result['tax_amount'] >= 0
        assert result['total_amount'] >= 0
        
        # PROPERTY 5: No tax means tax amount is zero
        if tax_rate == 0:
            assert result['tax_amount'] == Decimal('0.00')
            assert result['total_amount'] == result['subtotal']


@pytest.mark.property_based
@pytest.mark.tenant_management
class TestTenantDataProperties:
    """Property-based tests for tenant data validation."""
    
    @given(
        tenant_name=tenant_names(),
        plan_config=saas_plan_configurations()
    )
    @settings(max_examples=300)
    def test_tenant_configuration_properties(self, tenant_name, plan_config):
        """Property: Tenant configuration must always be valid."""
        
        # PROPERTY 1: Tenant name should not be empty after stripping
        assert len(tenant_name.strip()) >= 3, f"Tenant name too short: '{tenant_name}'"
        
        # PROPERTY 2: Plan price should be reasonable for SaaS
        assert Decimal('0.00') <= plan_config['price'] <= Decimal('10000.00')
        
        # PROPERTY 3: Plan limits should be positive
        for metric, limit in plan_config['limits'].items():
            assert limit > 0, f"Plan limit for {metric} must be positive: {limit}"
        
        # PROPERTY 4: Overage rates should be positive
        for metric, rate in plan_config['overage_rates'].items():
            assert rate > 0, f"Overage rate for {metric} must be positive: {rate}"
        
        # PROPERTY 5: Plan structure consistency
        assert set(plan_config['limits'].keys()) == set(plan_config['overage_rates'].keys())


# STATEFUL TESTING - SAAS TENANT LIFECYCLE
class SaaSTenantLifecycleStateMachine(RuleBasedStateMachine):
    """
    Stateful property-based testing for SaaS tenant lifecycle.
    
    This tests sequences of operations and ensures invariants
    hold throughout the tenant's SaaS journey.
    """
    
    def __init__(self):
        super().__init__()
        self.tenants = {}  # tenant_id -> tenant_data
        self.subscriptions = {}  # subscription_id -> subscription_data
        self.invoices = {}  # invoice_id -> invoice_data
        
    @initialize()
    def initialize_saas_system(self):
        """Initialize the SaaS system state."""
        self.calculator = SaaSBillingCalculator()
        
    @rule(
        tenant_id=st.uuids(),
        tenant_name=tenant_names(),
        plan_config=saas_plan_configurations()
    )
    def create_tenant(self, tenant_id, tenant_name, plan_config):
        """Create a new SaaS tenant."""
        assume(str(tenant_id) not in self.tenants)
        
        self.tenants[str(tenant_id)] = {
            'tenant_id': str(tenant_id),
            'name': tenant_name,
            'plan': plan_config,
            'status': 'active',
            'created_at': datetime.now()
        }
    
    @rule(
        subscription_id=st.uuids(),
        usage_days=st.integers(min_value=1, max_value=31)
    )
    def create_subscription(self, subscription_id, usage_days):
        """Create a subscription for a tenant."""
        assume(len(self.tenants) > 0)
        assume(str(subscription_id) not in self.subscriptions)
        
        # Pick a random tenant
        tenant_id = st.sampled_from(list(self.tenants.keys())).example()
        tenant = self.tenants[tenant_id]
        
        subscription_charge = self.calculator.calculate_subscription_charge(
            tenant['plan']['price'], usage_days, 30
        )
        
        self.subscriptions[str(subscription_id)] = {
            'subscription_id': str(subscription_id),
            'tenant_id': tenant_id,
            'usage_days': usage_days,
            'charge': subscription_charge['base_charge'],
            'proration_factor': subscription_charge['proration_factor'],
            'status': 'active'
        }
    
    @rule(
        invoice_id=st.uuids(),
        tenant_usage=tenant_usage_patterns()
    )
    def generate_invoice(self, invoice_id, tenant_usage):
        """Generate an invoice for a tenant with subscriptions."""
        assume(len(self.subscriptions) > 0)
        assume(str(invoice_id) not in self.invoices)
        
        # Pick a random subscription
        subscription_id = st.sampled_from(list(self.subscriptions.keys())).example()
        subscription = self.subscriptions[subscription_id]
        tenant_id = subscription['tenant_id']
        tenant = self.tenants[tenant_id]
        
        # Calculate usage charges
        usage_charges = self.calculator.calculate_tenant_usage_charges(
            tenant_usage, tenant['plan']['limits'], tenant['plan']['overage_rates']
        )
        
        # Calculate total bill
        total_bill = self.calculator.calculate_total_tenant_bill(
            subscription['charge'], usage_charges['total_overage_charge'], Decimal('0.08')
        )
        
        self.invoices[str(invoice_id)] = {
            'invoice_id': str(invoice_id),
            'tenant_id': tenant_id,
            'subscription_id': subscription_id,
            'subscription_charge': subscription['charge'],
            'usage_charges': usage_charges['total_overage_charge'],
            'total_amount': total_bill['total_amount'],
            'status': 'pending'
        }
    
    @invariant()
    def all_invoices_have_positive_amounts(self):
        """INVARIANT: All invoices must have positive amounts."""
        for invoice in self.invoices.values():
            assert invoice['total_amount'] > 0, f"Non-positive invoice amount: {invoice['total_amount']}"
    
    @invariant()
    def all_subscriptions_belong_to_tenants(self):
        """INVARIANT: All subscriptions must belong to existing tenants."""
        for subscription in self.subscriptions.values():
            assert subscription['tenant_id'] in self.tenants, f"Subscription references non-existent tenant"
    
    @invariant()
    def tenant_names_reasonable_length(self):
        """INVARIANT: Tenant names must be reasonable length."""
        for tenant in self.tenants.values():
            assert 3 <= len(tenant['name'].strip()) <= 100, f"Unreasonable tenant name length: {tenant['name']}"
    
    @invariant()
    def subscription_charges_reasonable(self):
        """INVARIANT: Subscription charges must be reasonable for SaaS."""
        for subscription in self.subscriptions.values():
            assert Decimal('0.00') < subscription['charge'] < Decimal('100000.00')


# Create test case from state machine
TestSaaSTenantLifecycle = SaaSTenantLifecycleStateMachine.TestCase


if __name__ == "__main__":
    # Quick property test
    calculator = SaaSBillingCalculator()
    
    # Test the property that subscription charges are never negative
    for _ in range(100):
        plan_price = st.decimals(min_value=Decimal('1.0'), max_value=Decimal('1000.0')).example()
        usage_days = st.integers(min_value=1, max_value=30).example()
        
        result = calculator.calculate_subscription_charge(plan_price, usage_days, 30)
        assert result['base_charge'] >= 0, f"Negative charge found: {result['base_charge']}"
    
    print("✅ SaaS property-based tests validation passed!")