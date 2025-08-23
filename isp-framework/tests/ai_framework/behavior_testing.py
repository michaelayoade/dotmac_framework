"""
Behavior-Driven Testing Framework for AI-First Development

Focuses on testing business outcomes and user workflows rather than
implementation details. Perfect for validating AI-generated code.
"""

import pytest
from typing import Dict, Any, List, Optional, Callable
from functools import wraps
from dataclasses import dataclass
from enum import Enum


class BusinessOutcome(Enum):
    """Expected business outcomes for behavior testing."""
    CUSTOMER_ONBOARDED = "customer_onboarded"
    SERVICE_PROVISIONED = "service_provisioned"
    BILL_GENERATED = "bill_generated"
    PAYMENT_PROCESSED = "payment_processed"
    CUSTOMER_SUSPENDED = "customer_suspended"
    REVENUE_RECORDED = "revenue_recorded"


@dataclass
class BehaviorTestContext:
    """Context for behavior-driven tests."""
    customer_data: Dict[str, Any]
    service_data: Dict[str, Any]
    billing_data: Dict[str, Any]
    expected_outcome: BusinessOutcome
    success_criteria: List[str]


class BehaviorValidator:
    """
    AI-friendly behavior validator that tests business workflows
    and outcomes rather than implementation details.
    """
    
    def __init__(self):
        self.test_context: Optional[BehaviorTestContext] = None
    
    def given_customer_wants_service(self, customer_data: Dict[str, Any], service_type: str):
        """Set up initial context: customer wants a service."""
        service_data = {
            "service_type": service_type,
            "bandwidth_mbps": 100 if service_type == "internet" else None,
            "monthly_cost": 49.99
        }
        
        billing_data = {
            "billing_cycle": "monthly",
            "payment_method": "credit_card"
        }
        
        self.test_context = BehaviorTestContext(
            customer_data=customer_data,
            service_data=service_data,
            billing_data=billing_data,
            expected_outcome=BusinessOutcome.SERVICE_PROVISIONED,
            success_criteria=[
                "customer_exists",
                "service_activated", 
                "billing_setup",
                "customer_can_use_service"
            ]
        )
        
        return self
    
    def when_customer_subscribes(self):
        """Execute the subscription workflow."""
        if not self.test_context:
            raise ValueError("Must call given_* method first")
        
        # This would call actual business logic
        from dotmac_isp.modules.identity.service import IdentityService
        from dotmac_isp.modules.services.service import ServiceManagement
        from dotmac_isp.modules.billing.service import BillingService
        
        identity_service = IdentityService()
        service_mgmt = ServiceManagement() 
        billing_service = BillingService()
        
        # Execute workflow
        customer = identity_service.create_customer(**self.test_context.customer_data)
        service = service_mgmt.provision_service(
            customer_id=customer.id,
            **self.test_context.service_data
        )
        billing_account = billing_service.setup_billing(
            customer_id=customer.id,
            service_id=service.id,
            **self.test_context.billing_data
        )
        
        self.test_context.results = {
            "customer": customer,
            "service": service,
            "billing_account": billing_account
        }
        
        return self
    
    def then_customer_should_have_working_service(self):
        """Verify the expected business outcome."""
        if not self.test_context or not hasattr(self.test_context, 'results'):
            raise ValueError("Must call when_* method first")
        
        results = self.test_context.results
        
        # Verify business outcomes
        assert results["customer"] is not None, "Customer should be created"
        assert results["service"] is not None, "Service should be provisioned"
        assert results["billing_account"] is not None, "Billing should be set up"
        
        # Verify customer can actually use the service
        customer = results["customer"]
        service = results["service"]
        
        # Business outcome: Customer should be able to access their service
        assert customer.status == "active", "Customer should be active"
        assert service.status == "active", "Service should be active"
        assert service.customer_id == customer.id, "Service should be linked to customer"
        
        return True


def behavior_test(
    outcome: BusinessOutcome,
    critical: bool = False
):
    """
    Decorator for behavior-driven tests focused on business outcomes.
    
    Example:
        @behavior_test(BusinessOutcome.CUSTOMER_ONBOARDED, critical=True)
        @pytest.mark.behavior
        @pytest.mark.revenue_critical
        def test_customer_onboarding_workflow():
            # Given a potential customer
            # When they complete signup
            # Then they should have working service
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        # Add appropriate pytest markers
        markers = [pytest.mark.behavior]
        if critical:
            markers.append(pytest.mark.revenue_critical)
        
        wrapper.pytestmark = markers
        wrapper.expected_outcome = outcome
        return wrapper
    return decorator


# Behavior test examples

@behavior_test(BusinessOutcome.CUSTOMER_ONBOARDED, critical=True)
@pytest.mark.behavior
@pytest.mark.revenue_critical
def behavior_test_customer_onboarding_workflow():
    """
    Behavior: When a potential customer signs up for internet service,
    they should be able to use the service immediately after completion.
    """
    validator = BehaviorValidator()
    
    # Given: A potential customer wants internet service
    customer_data = {
        "customer_number": "CUS-BEHAV1",
        "display_name": "Behavior Test Customer",
        "email": "behavior@example.com",
        "phone": "+1-555-987-6543"
    }
    
    validator.given_customer_wants_service(customer_data, "internet")
    
    # When: Customer completes the subscription process
    validator.when_customer_subscribes()
    
    # Then: Customer should have working internet service
    assert validator.then_customer_should_have_working_service()


@behavior_test(BusinessOutcome.BILL_GENERATED, critical=True)
@pytest.mark.behavior
@pytest.mark.billing_core
def behavior_test_monthly_billing_workflow():
    """
    Behavior: At the end of each month, customers should receive
    accurate bills for their service usage.
    """
    from dotmac_isp.modules.billing.service import BillingService
    from dotmac_isp.modules.identity.service import IdentityService
    from dotmac_isp.modules.services.service import ServiceManagement
    
    # Given: Customer with active service for one month
    identity_service = IdentityService()
    service_mgmt = ServiceManagement()
    billing_service = BillingService()
    
    customer = identity_service.create_customer(
        customer_number="CUS-BILL01",
        display_name="Billing Test Customer",
        email="billing@example.com"
    )
    
    service = service_mgmt.provision_service(
        customer_id=customer.id,
        service_type="internet",
        monthly_cost=79.99,
        bandwidth_mbps=200
    )
    
    # When: Monthly billing cycle runs
    invoice = billing_service.generate_monthly_invoice(
        customer_id=customer.id,
        billing_month="2024-01"
    )
    
    # Then: Customer should receive accurate bill
    assert invoice is not None, "Invoice should be generated"
    assert invoice.customer_id == customer.id, "Invoice should be for correct customer"
    assert invoice.amount >= 79.99, "Invoice should include service cost"
    assert invoice.total_amount > invoice.amount, "Invoice should include taxes"
    assert invoice.status == "draft", "New invoice should be in draft status"


@behavior_test(BusinessOutcome.PAYMENT_PROCESSED, critical=True)
@pytest.mark.behavior
@pytest.mark.payment_flow
def behavior_test_customer_payment_workflow():
    """
    Behavior: When customers pay their bills, the payment should be
    processed correctly and their account updated.
    """
    from dotmac_isp.modules.billing.service import BillingService
    from dotmac_isp.modules.identity.service import IdentityService
    
    # Given: Customer with outstanding invoice
    identity_service = IdentityService()
    billing_service = BillingService()
    
    customer = identity_service.create_customer(
        customer_number="CUS-PAY01",
        display_name="Payment Test Customer", 
        email="payment@example.com"
    )
    
    invoice = billing_service.create_invoice(
        customer_id=customer.id,
        amount=89.99,
        tax_amount=7.20,
        total_amount=97.19
    )
    
    # When: Customer makes payment
    payment_result = billing_service.process_payment(
        invoice_id=invoice.id,
        payment_method="credit_card",
        payment_amount=97.19
    )
    
    # Then: Payment should be processed and account updated
    assert payment_result["status"] == "success", "Payment should be successful"
    assert payment_result["amount_paid"] == 97.19, "Full amount should be paid"
    
    # And invoice should be marked as paid
    updated_invoice = billing_service.get_invoice(invoice.id)
    assert updated_invoice.status == "paid", "Invoice should be marked as paid"
    assert updated_invoice.payment_date is not None, "Payment date should be recorded"


@behavior_test(BusinessOutcome.CUSTOMER_SUSPENDED, critical=True)
@pytest.mark.behavior
@pytest.mark.business_logic_protection
def behavior_test_overdue_account_suspension():
    """
    Behavior: When customers don't pay their bills for 30 days,
    their service should be automatically suspended.
    """
    from dotmac_isp.modules.billing.service import BillingService
    from dotmac_isp.modules.identity.service import IdentityService
    from dotmac_isp.modules.services.service import ServiceManagement
    from datetime import datetime, timedelta
    
    # Given: Customer with overdue invoice (30+ days)
    identity_service = IdentityService()
    billing_service = BillingService()
    service_mgmt = ServiceManagement()
    
    customer = identity_service.create_customer(
        customer_number="CUS-SUSP01",
        display_name="Suspension Test Customer",
        email="suspension@example.com"
    )
    
    service = service_mgmt.provision_service(
        customer_id=customer.id,
        service_type="internet",
        monthly_cost=59.99
    )
    
    # Create overdue invoice
    overdue_date = datetime.now() - timedelta(days=35)
    invoice = billing_service.create_invoice(
        customer_id=customer.id,
        amount=59.99,
        due_date=overdue_date.date()
    )
    
    # When: Automated suspension process runs
    suspension_result = billing_service.process_overdue_accounts()
    
    # Then: Customer service should be suspended
    suspended_customers = [r for r in suspension_result if r["customer_id"] == customer.id]
    assert len(suspended_customers) == 1, "Customer should be in suspension list"
    
    # And service should be inactive
    updated_service = service_mgmt.get_service(service.id)
    assert updated_service.status == "suspended", "Service should be suspended"
    
    # And customer should be notified
    notifications = billing_service.get_customer_notifications(customer.id)
    suspension_notices = [n for n in notifications if "suspend" in n.message.lower()]
    assert len(suspension_notices) > 0, "Customer should be notified of suspension"


@behavior_test(BusinessOutcome.REVENUE_RECORDED)
@pytest.mark.behavior
@pytest.mark.revenue_critical
def behavior_test_revenue_recognition_workflow():
    """
    Behavior: When payments are received, revenue should be properly
    recognized in the accounting system.
    """
    from dotmac_isp.modules.billing.service import BillingService
    from dotmac_isp.modules.analytics.service import AnalyticsService
    
    # Given: Customer payment for service
    billing_service = BillingService()
    analytics_service = AnalyticsService()
    
    # When: Payment is processed
    payment_data = {
        "customer_id": "test-customer-id",
        "service_type": "internet",
        "amount": 99.99,
        "tax_amount": 8.00,
        "total_amount": 107.99,
        "payment_date": datetime.now()
    }
    
    billing_service.record_payment(**payment_data)
    
    # Then: Revenue should be properly recorded
    revenue_data = analytics_service.get_revenue_data(
        start_date=datetime.now().date(),
        end_date=datetime.now().date()
    )
    
    assert revenue_data["total_revenue"] >= 99.99, "Revenue should include service payment"
    assert revenue_data["tax_collected"] >= 8.00, "Tax amount should be recorded"
    
    # And revenue should be categorized by service type
    service_revenue = analytics_service.get_revenue_by_service_type("internet")
    assert service_revenue >= 99.99, "Internet service revenue should be recorded"