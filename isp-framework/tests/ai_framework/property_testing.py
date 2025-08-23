"""
Property-Based Testing Framework for AI-First Development

Generates thousands of test cases automatically to validate properties
and invariants rather than specific input/output combinations.
"""

import pytest
from hypothesis import given, strategies as st, settings, Verbosity
from hypothesis.stateful import RuleBasedStateMachine, rule, initialize
from typing import Any, Callable, Dict, List, Optional, Type, Union
from functools import wraps
import inspect


class AIPropertyTestGenerator:
    """
    AI-powered property-based test generator that creates comprehensive
    test cases for business logic validation.
    """
    
    @staticmethod
    def generate_customer_data():
        """Generate realistic customer data for property testing."""
        return st.fixed_dictionaries({
            'customer_id': st.uuids(),
            'customer_number': st.text(
                alphabet=st.characters(whitelist_categories=('Lu', 'Nd')), 
                min_size=8, 
                max_size=12
            ).map(lambda x: f"CUS-{x[:6]}"),
            'display_name': st.text(min_size=2, max_size=100),
            'email': st.emails(),
            'phone': st.text(
                alphabet=st.characters(whitelist_categories=('Nd',)), 
                min_size=10, 
                max_size=15
            ).map(lambda x: f"+1-{x[:3]}-{x[3:6]}-{x[6:10]}"),
            'billing_address': st.dictionaries(
                st.sampled_from(['street', 'city', 'state', 'zip', 'country']),
                st.text(min_size=1, max_size=50)
            )
        })
    
    @staticmethod
    def generate_billing_data():
        """Generate realistic billing data for property testing."""
        return st.fixed_dictionaries({
            'usage_gb': st.floats(min_value=0.0, max_value=10000.0, allow_nan=False),
            'rate_per_gb': st.floats(min_value=0.01, max_value=1.0, allow_nan=False),
            'tax_rate': st.floats(min_value=0.0, max_value=0.3, allow_nan=False),
            'discount_percent': st.floats(min_value=0.0, max_value=0.5, allow_nan=False),
            'billing_period': st.sampled_from(['daily', 'weekly', 'monthly', 'yearly']),
            'currency': st.sampled_from(['USD', 'EUR', 'GBP', 'CAD'])
        })
    
    @staticmethod
    def generate_service_data():
        """Generate realistic service data for property testing."""
        return st.fixed_dictionaries({
            'service_id': st.uuids(),
            'service_type': st.sampled_from(['internet', 'phone', 'tv', 'bundle']),
            'bandwidth_mbps': st.integers(min_value=1, max_value=1000),
            'monthly_cost': st.decimals(min_value=9.99, max_value=999.99, places=2),
            'contract_length_months': st.integers(min_value=1, max_value=36),
            'data_limit_gb': st.one_of(st.none(), st.integers(min_value=1, max_value=1000))
        })


def property_test(
    *test_data_strategies,
    max_examples: int = 100,
    deadline: Optional[int] = None,
    verbosity: Verbosity = Verbosity.normal
):
    """
    Decorator for property-based tests that generates multiple test cases.
    
    Example:
        @property_test(AIPropertyTestGenerator.generate_billing_data())
        @pytest.mark.property_based
        def test_billing_calculation_properties(billing_data):
            # Test invariants that should always hold
            bill = calculate_bill(**billing_data)
            assert bill >= 0  # Bills should never be negative
            assert bill <= billing_data['usage_gb'] * billing_data['rate_per_gb'] * 2  # Bill shouldn't exceed 2x usage cost
    """
    def decorator(func):
        # Create hypothesis strategy from input strategies
        if len(test_data_strategies) == 1:
            strategy = test_data_strategies[0]
        else:
            strategy = st.tuples(*test_data_strategies)
        
        @given(strategy)
        @settings(
            max_examples=max_examples,
            deadline=deadline,
            verbosity=verbosity
        )
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        # Add pytest marker
        wrapper.pytestmark = pytest.mark.property_based
        return wrapper
    return decorator


class CustomerLifecycleStateMachine(RuleBasedStateMachine):
    """
    Stateful property-based testing for customer lifecycle.
    
    This generates sequences of operations (create customer, activate service,
    suspend account, etc.) and verifies business invariants hold throughout.
    """
    
    def __init__(self):
        super().__init__()
        self.customers: Dict[str, Dict] = {}
        self.services: Dict[str, Dict] = {}
    
    @initialize()
    def setup_initial_state(self):
        """Initialize the system state."""
        pass
    
    @rule(
        customer_data=AIPropertyTestGenerator.generate_customer_data()
    )
    def create_customer(self, customer_data):
        """Test customer creation with property validation."""
        customer_id = str(customer_data['customer_id'])
        
        # Business rule: Customer numbers must be unique
        existing_numbers = [c.get('customer_number') for c in self.customers.values()]
        if customer_data['customer_number'] in existing_numbers:
            return  # Skip this iteration
        
        self.customers[customer_id] = customer_data
        
        # Invariant: Customer should exist after creation
        assert customer_id in self.customers
        # Invariant: Customer data should be preserved
        assert self.customers[customer_id]['display_name'] == customer_data['display_name']
    
    @rule(
        service_data=AIPropertyTestGenerator.generate_service_data()
    )
    def add_service(self, service_data):
        """Test service addition with property validation."""
        if not self.customers:
            return  # Need customers before adding services
        
        customer_id = next(iter(self.customers.keys()))
        service_id = str(service_data['service_id'])
        
        self.services[service_id] = {
            **service_data,
            'customer_id': customer_id,
            'status': 'active'
        }
        
        # Invariant: Service should be linked to a customer
        assert self.services[service_id]['customer_id'] in self.customers
        # Invariant: Service cost should be positive
        assert self.services[service_id]['monthly_cost'] > 0


# Example property-based tests for critical business functions

@property_test(AIPropertyTestGenerator.generate_billing_data())
@pytest.mark.property_based
@pytest.mark.revenue_critical
def property_test_billing_never_negative(billing_data):
    """Property: Bills should never be negative regardless of input."""
    from dotmac_isp.modules.billing.service import BillingService
    
    service = BillingService()
    bill_amount = service.calculate_usage_charge(**billing_data)
    
    # Critical business property: No negative bills
    assert bill_amount >= 0, f"Negative bill generated: {bill_amount}"


@property_test(AIPropertyTestGenerator.generate_customer_data())
@pytest.mark.property_based
@pytest.mark.data_safety
def property_test_customer_data_integrity(customer_data):
    """Property: Customer data should be preserved through create/retrieve cycle."""
    from dotmac_isp.modules.identity.service import IdentityService
    
    service = IdentityService()
    
    # Create customer
    customer = service.create_customer(**customer_data)
    
    # Retrieve customer
    retrieved = service.get_customer(customer.id)
    
    # Property: Retrieved data should match input
    assert retrieved.display_name == customer_data['display_name']
    assert retrieved.customer_number == customer_data['customer_number']


@property_test(
    AIPropertyTestGenerator.generate_service_data(),
    AIPropertyTestGenerator.generate_customer_data()
)
@pytest.mark.property_based
@pytest.mark.business_logic_protection
def property_test_service_customer_relationship(service_data, customer_data):
    """Property: Services must always be linked to valid customers."""
    from dotmac_isp.modules.services.service import ServiceManagement
    from dotmac_isp.modules.identity.service import IdentityService
    
    identity_service = IdentityService()
    service_mgmt = ServiceManagement()
    
    # Create customer first
    customer = identity_service.create_customer(**customer_data)
    
    # Add service to customer
    service = service_mgmt.provision_service(
        customer_id=customer.id,
        **service_data
    )
    
    # Property: Service should be linked to the customer
    assert service.customer_id == customer.id
    # Property: Customer should have the service
    customer_services = service_mgmt.get_customer_services(customer.id)
    assert any(s.id == service.id for s in customer_services)


# Stateful testing example
TestCustomerLifecycle = CustomerLifecycleStateMachine.TestCase