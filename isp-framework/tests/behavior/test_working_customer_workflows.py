import logging

logger = logging.getLogger(__name__)

"""
BEHAVIOR-DRIVEN TESTING - COMPLETE CUSTOMER WORKFLOWS
=====================================================

Tests complete business workflows end-to-end, validating business outcomes
rather than implementation details. Perfect for AI-first development where
we need to ensure AI changes don't break customer experience.

Focus: Customer journey validation from signup to billing to payment.
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional
from uuid import uuid4, UUID
from dataclasses import dataclass, field
from enum import Enum

# Import our existing frameworks
from tests.ai_framework.property_testing import AIPropertyTestGenerator
from tests.revenue_protection.test_working_billing_accuracy import BillingCalculator


class CustomerType(Enum):
    """Class for CustomerType operations."""
    RESIDENTIAL = "residential"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


class ServiceStatus(Enum):
    """Class for ServiceStatus operations."""
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class PaymentStatus(Enum):
    """Class for PaymentStatus operations."""
    PENDING = "pending"
    COMPLETED = "completed" 
    FAILED = "failed"
    REFUNDED = "refunded"


@dataclass
class CustomerProfile:
    """Customer profile for behavior testing."""
    customer_id: str = field(default_factory=lambda: str(uuid4()))
    customer_number: str = field(default_factory=lambda: f"CUS-{str(uuid4())[:8].upper()}")
    display_name: str = "Test Customer"
    email: str = "test@example.com"
    phone: str = "+1-555-123-4567"
    customer_type: CustomerType = CustomerType.RESIDENTIAL
    credit_score: int = 700
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """To Dict operation."""
        return {
            'customer_id': self.customer_id,
            'customer_number': self.customer_number,
            'display_name': self.display_name,
            'email': self.email,
            'phone': self.phone,
            'customer_type': self.customer_type.value,
            'credit_score': self.credit_score,
            'created_at': self.created_at
        }


@dataclass 
class ServicePlan:
    """Service plan for behavior testing."""
    service_id: str = field(default_factory=lambda: str(uuid4()))
    service_name: str = "Basic Internet"
    service_type: str = "internet"
    monthly_rate: Decimal = Decimal('79.99')
    bandwidth_mbps: int = 100
    data_limit_gb: Optional[int] = None
    contract_length_months: int = 12
    
    def to_dict(self) -> Dict[str, Any]:
        """To Dict operation."""
        return {
            'service_id': self.service_id,
            'service_name': self.service_name,
            'service_type': self.service_type,
            'monthly_rate': self.monthly_rate,
            'bandwidth_mbps': self.bandwidth_mbps,
            'data_limit_gb': self.data_limit_gb,
            'contract_length_months': self.contract_length_months
        }


@dataclass
class WorkflowResult:
    """Result of a workflow execution."""
    success: bool
    steps_completed: List[str]
    errors: List[str] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)
    
    def add_step(self, step_name: str):
        """Add a completed step."""
        self.steps_completed.append(step_name)
    
    def add_error(self, error_message: str):
        """Add an error."""
        self.errors.append(error_message)
        self.success = False


class CustomerWorkflowSimulator:
    """
    Simulates complete customer workflows for behavior testing.
    
    This class doesn't depend on actual database or external services,
    making tests fast and reliable while still testing business logic.
    """
    
    def __init__(self):
        """  Init   operation."""
        self.billing_calculator = BillingCalculator()
        self.customers: Dict[str, CustomerProfile] = {}
        self.services: Dict[str, Dict[str, Any]] = {}  # customer_id -> services
        self.invoices: Dict[str, List[Dict[str, Any]]] = {}  # customer_id -> invoices
        self.payments: Dict[str, List[Dict[str, Any]]] = {}  # customer_id -> payments
    
    def customer_signup_workflow(
        self, 
        customer_data: Dict[str, Any], 
        service_plan: ServicePlan
    ) -> WorkflowResult:
        """
        Complete customer signup workflow.
        
        BUSINESS BEHAVIOR: Customer signs up for service and gets activated.
        """
        result = WorkflowResult(success=True, steps_completed=[])
        
        try:
            # Step 1: Create customer profile
            customer = CustomerProfile(
                display_name=customer_data.get('display_name', 'Test Customer'),
                email=customer_data.get('email', 'test@example.com'),
                phone=customer_data.get('phone', '+1-555-123-4567'),
                customer_type=CustomerType(customer_data.get('customer_type', 'residential'))
            )
            result.add_step("customer_created")
            
            # Step 2: Credit check
            credit_approved = self._perform_credit_check(customer)
            if not credit_approved:
                result.add_error("Credit check failed")
                return result
            result.add_step("credit_check_passed")
            
            # Step 3: Service availability check  
            service_available = self._check_service_availability(customer, service_plan)
            if not service_available:
                result.add_error("Service not available in customer area")
                return result
            result.add_step("service_availability_confirmed")
            
            # Step 4: Create service subscription
            service_record = self._create_service_subscription(customer, service_plan)
            result.add_step("service_subscription_created")
            
            # Step 5: Setup billing
            billing_setup = self._setup_customer_billing(customer, service_plan)
            result.add_step("billing_setup_completed")
            
            # Step 6: Schedule service activation
            activation_scheduled = self._schedule_service_activation(customer, service_plan)
            result.add_step("service_activation_scheduled")
            
            # Store customer and service
            self.customers[customer.customer_id] = customer
            if customer.customer_id not in self.services:
                self.services[customer.customer_id] = []
            self.services[customer.customer_id].append(service_record)
            
            result.data = {
                'customer': customer.to_dict(),
                'service': service_record,
                'billing_setup': billing_setup
            }
            
        except Exception as e:
            result.add_error(f"Workflow failed: {str(e)}")
        
        return result
    
    def monthly_billing_workflow(
        self, 
        customer_id: str, 
        usage_data: Dict[str, Decimal]
    ) -> WorkflowResult:
        """
        Complete monthly billing workflow.
        
        BUSINESS BEHAVIOR: Generate monthly bill including services and usage.
        """
        result = WorkflowResult(success=True, steps_completed=[])
        
        try:
            if customer_id not in self.customers:
                result.add_error("Customer not found")
                return result
            
            customer = self.customers[customer_id]
            services = self.services.get(customer_id, [])
            
            if not services:
                result.add_error("No services found for customer")
                return result
            
            # Step 1: Calculate service charges
            service_charges = []
            total_service_charges = Decimal('0.00')
            
            for service in services:
                if service['status'] == ServiceStatus.ACTIVE.value:
                    charge = self.billing_calculator.calculate_monthly_service_charge(
                        base_rate=service['monthly_rate'],
                        service_days=30,
                        billing_days=30,
                        tax_rate=Decimal('0.08')
                    )
                    service_charges.append({
                        'service_id': service['service_id'],
                        'service_name': service['service_name'],
                        'charge': charge
                    })
                    total_service_charges += charge['total_charge']
            
            result.add_step("service_charges_calculated")
            
            # Step 2: Calculate usage charges
            usage_charges = []
            total_usage_charges = Decimal('0.00')
            
            for service_id, usage_gb in usage_data.items():
                # Find service
                service = next((s for s in services if s['service_id'] == service_id), None)
                if service and service['status'] == ServiceStatus.ACTIVE.value:
                    # Standard usage rate of $0.10 per GB
                    usage_charge = self.billing_calculator.calculate_usage_charge(
                        usage_gb, Decimal('0.10')
                    )
                    usage_charges.append({
                        'service_id': service_id,
                        'usage_gb': usage_gb,
                        'charge': usage_charge
                    })
                    total_usage_charges += usage_charge
            
            result.add_step("usage_charges_calculated")
            
            # Step 3: Generate invoice
            invoice = self._generate_invoice(
                customer, service_charges, usage_charges, 
                total_service_charges, total_usage_charges
            )
            result.add_step("invoice_generated")
            
            # Step 4: Store invoice
            if customer_id not in self.invoices:
                self.invoices[customer_id] = []
            self.invoices[customer_id].append(invoice)
            result.add_step("invoice_stored")
            
            result.data = {
                'invoice': invoice,
                'service_charges': service_charges,
                'usage_charges': usage_charges,
                'total_amount': invoice['total_amount']
            }
            
        except Exception as e:
            result.add_error(f"Billing workflow failed: {str(e)}")
        
        return result
    
    def payment_processing_workflow(
        self, 
        customer_id: str, 
        invoice_id: str,
        payment_amount: Decimal,
        payment_method: str = "credit_card"
    ) -> WorkflowResult:
        """
        Complete payment processing workflow.
        
        BUSINESS BEHAVIOR: Process customer payment and update invoice status.
        """
        result = WorkflowResult(success=True, steps_completed=[])
        
        try:
            # Step 1: Validate customer and invoice
            if customer_id not in self.customers:
                result.add_error("Customer not found")
                return result
            
            customer_invoices = self.invoices.get(customer_id, [])
            invoice = next((inv for inv in customer_invoices if inv['invoice_id'] == invoice_id), None)
            
            if not invoice:
                result.add_error("Invoice not found")
                return result
            
            result.add_step("invoice_validated")
            
            # Step 2: Validate payment amount
            if payment_amount <= 0:
                result.add_error("Payment amount must be positive")
                return result
            
            if payment_amount > invoice['total_amount']:
                result.add_error("Payment amount exceeds invoice total")
                return result
            
            result.add_step("payment_amount_validated")
            
            # Step 3: Process payment
            payment_result = self._process_payment(
                customer_id, invoice_id, payment_amount, payment_method
            )
            
            if payment_result['status'] != PaymentStatus.COMPLETED.value:
                result.add_error(f"Payment processing failed: {payment_result.get('error', 'Unknown error')}")
                return result
            
            result.add_step("payment_processed")
            
            # Step 4: Update invoice status
            if payment_amount >= invoice['total_amount']:
                invoice['status'] = 'paid'
                invoice['paid_amount'] = payment_amount
                invoice['paid_date'] = datetime.now()
            else:
                invoice['status'] = 'partially_paid'
                invoice['paid_amount'] = invoice.get('paid_amount', Decimal('0.00')) + payment_amount
            
            result.add_step("invoice_status_updated")
            
            # Step 5: Store payment record
            if customer_id not in self.payments:
                self.payments[customer_id] = []
            self.payments[customer_id].append(payment_result)
            result.add_step("payment_recorded")
            
            result.data = {
                'payment': payment_result,
                'invoice': invoice
            }
            
        except Exception as e:
            result.add_error(f"Payment workflow failed: {str(e)}")
        
        return result
    
    # Helper methods
    def _perform_credit_check(self, customer: CustomerProfile) -> bool:
        """Simulate credit check."""
        # Business rules for credit approval
        if customer.customer_type == CustomerType.RESIDENTIAL:
            return customer.credit_score >= 600
        elif customer.customer_type == CustomerType.BUSINESS:
            return customer.credit_score >= 650  
        else:  # Enterprise
            return customer.credit_score >= 700
    
    def _check_service_availability(self, customer: CustomerProfile, service_plan: ServicePlan) -> bool:
        """Simulate service availability check."""
        # For testing, always return True unless specific conditions
        return True
    
    def _create_service_subscription(self, customer: CustomerProfile, service_plan: ServicePlan) -> Dict[str, Any]:
        """Create service subscription record."""
        return {
            'service_id': service_plan.service_id,
            'customer_id': customer.customer_id,
            'service_name': service_plan.service_name,
            'service_type': service_plan.service_type,
            'monthly_rate': service_plan.monthly_rate,
            'status': ServiceStatus.ACTIVE.value,
            'activation_date': datetime.now(),
            'contract_end_date': datetime.now() + timedelta(days=service_plan.contract_length_months * 30)
        }
    
    def _setup_customer_billing(self, customer: CustomerProfile, service_plan: ServicePlan) -> Dict[str, Any]:
        """Setup customer billing configuration."""
        return {
            'billing_cycle': 'monthly',
            'billing_day': 1,  # Bill on 1st of each month
            'tax_rate': Decimal('0.08'),  # 8% tax
            'payment_terms': 'net_30'  # 30 days to pay
        }
    
    def _schedule_service_activation(self, customer: CustomerProfile, service_plan: ServicePlan) -> bool:
        """Schedule service activation."""
        # For testing, always succeed
        return True
    
    def _generate_invoice(
        self, 
        customer: CustomerProfile,
        service_charges: List[Dict[str, Any]], 
        usage_charges: List[Dict[str, Any]],
        total_service: Decimal,
        total_usage: Decimal
    ) -> Dict[str, Any]:
        """Generate invoice record."""
        subtotal = total_service + total_usage
        return {
            'invoice_id': str(uuid4()),
            'customer_id': customer.customer_id,
            'invoice_number': f"INV-{datetime.now().strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}",
            'invoice_date': datetime.now(),
            'due_date': datetime.now() + timedelta(days=30),
            'service_charges': service_charges,
            'usage_charges': usage_charges,
            'subtotal': subtotal,
            'total_amount': subtotal,  # Tax already included in service charges
            'status': 'pending',
            'paid_amount': Decimal('0.00')
        }
    
    def _process_payment(
        self, 
        customer_id: str, 
        invoice_id: str, 
        amount: Decimal,
        payment_method: str
    ) -> Dict[str, Any]:
        """Simulate payment processing."""
        # For testing, payments succeed unless amount is exactly $999.99 (simulate failure)
        if amount == Decimal('999.99'):
            return {
                'payment_id': str(uuid4()),
                'customer_id': customer_id,
                'invoice_id': invoice_id,
                'amount': amount,
                'payment_method': payment_method,
                'status': PaymentStatus.FAILED.value,
                'error': 'Payment processor declined',
                'processed_date': datetime.now()
            }
        
        return {
            'payment_id': str(uuid4()),
            'customer_id': customer_id,
            'invoice_id': invoice_id,
            'amount': amount,
            'payment_method': payment_method,
            'status': PaymentStatus.COMPLETED.value,
            'processed_date': datetime.now(),
            'confirmation_code': f"PAY-{str(uuid4())[:8].upper()}"
        }


# BEHAVIOR TESTS - COMPLETE WORKFLOWS
@pytest.mark.behavior
@pytest.mark.customer_journey
class TestCustomerWorkflowsBehavior:
    """Test complete customer workflows end-to-end."""
    
    def test_residential_customer_complete_journey(self):
        """BEHAVIOR: Complete residential customer journey from signup to payment."""
        simulator = CustomerWorkflowSimulator()
        
        # Customer wants internet service
        customer_data = {
            'display_name': 'John Smith',
            'email': 'john.smith@email.com',
            'phone': '+1-555-123-4567',
            'customer_type': 'residential'
        }
        
        service_plan = ServicePlan(
            service_name="Residential Internet",
            service_type="internet",
            monthly_rate=Decimal('79.99'),
            bandwidth_mbps=100
        )
        
        # STEP 1: Customer signup
        signup_result = simulator.customer_signup_workflow(customer_data, service_plan)
        
        assert signup_result.success, f"Signup failed: {signup_result.errors}"
        assert "customer_created" in signup_result.steps_completed
        assert "credit_check_passed" in signup_result.steps_completed
        assert "billing_setup_completed" in signup_result.steps_completed
        
        customer_id = signup_result.data['customer']['customer_id']
        
        # STEP 2: Monthly usage and billing
        usage_data = {
            service_plan.service_id: Decimal('150.5')  # 150.5 GB usage
        }
        
        billing_result = simulator.monthly_billing_workflow(customer_id, usage_data)
        
        assert billing_result.success, f"Billing failed: {billing_result.errors}"
        assert "service_charges_calculated" in billing_result.steps_completed
        assert "usage_charges_calculated" in billing_result.steps_completed
        assert "invoice_generated" in billing_result.steps_completed
        
        # Validate billing amounts
        invoice = billing_result.data['invoice']
        expected_service_charge = Decimal('86.39')  # 79.99 + 8% tax
        expected_usage_charge = Decimal('15.05')    # 150.5 * $0.10
        expected_total = expected_service_charge + expected_usage_charge
        
        assert invoice['total_amount'] == expected_total
        
        # STEP 3: Payment processing
        invoice_id = invoice['invoice_id']
        payment_amount = invoice['total_amount']
        
        payment_result = simulator.payment_processing_workflow(
            customer_id, invoice_id, payment_amount, "credit_card"
        )
        
        assert payment_result.success, f"Payment failed: {payment_result.errors}"
        assert "payment_processed" in payment_result.steps_completed
        assert "invoice_status_updated" in payment_result.steps_completed
        
        # Validate payment
        payment = payment_result.data['payment']
        assert payment['status'] == PaymentStatus.COMPLETED.value
        assert payment['amount'] == payment_amount
        
        # Validate invoice is now paid
        updated_invoice = payment_result.data['invoice']
        assert updated_invoice['status'] == 'paid'
        assert updated_invoice['paid_amount'] == payment_amount
    
    def test_business_customer_high_usage_journey(self):
        """BEHAVIOR: Business customer with high usage and tiered billing."""
        simulator = CustomerWorkflowSimulator()
        
        customer_data = {
            'display_name': 'ABC Company LLC',
            'email': 'billing@abccompany.com',
            'phone': '+1-555-987-6543',
            'customer_type': 'business'
        }
        
        service_plan = ServicePlan(
            service_name="Business Internet Pro",
            service_type="internet",
            monthly_rate=Decimal('299.99'),
            bandwidth_mbps=500
        )
        
        # Signup
        signup_result = simulator.customer_signup_workflow(customer_data, service_plan)
        assert signup_result.success
        
        customer_id = signup_result.data['customer']['customer_id']
        
        # High usage month
        usage_data = {
            service_plan.service_id: Decimal('2750.0')  # 2.75 TB usage
        }
        
        billing_result = simulator.monthly_billing_workflow(customer_id, usage_data)
        assert billing_result.success
        
        # Validate high usage billing
        invoice = billing_result.data['invoice']
        expected_service = Decimal('323.99')  # 299.99 + 8% tax
        expected_usage = Decimal('275.00')    # 2750 * $0.10
        
        # Business customer should have reasonable total bill
        assert invoice['total_amount'] == expected_service + expected_usage
        assert invoice['total_amount'] > Decimal('500.00')  # Significant bill
        assert invoice['total_amount'] < Decimal('1000.00') # But not excessive
    
    def test_payment_failure_and_retry_behavior(self):
        """BEHAVIOR: Handle payment failures and successful retry."""
        simulator = CustomerWorkflowSimulator()
        
        # Setup customer and invoice
        customer_data = {'display_name': 'Test Customer', 'customer_type': 'residential'}
        service_plan = ServicePlan(monthly_rate=Decimal('49.99'))
        
        signup_result = simulator.customer_signup_workflow(customer_data, service_plan)
        customer_id = signup_result.data['customer']['customer_id']
        
        billing_result = simulator.monthly_billing_workflow(customer_id, {})
        invoice_id = billing_result.data['invoice']['invoice_id']
        
        # STEP 1: Failed payment (using special failure amount)
        failed_payment_result = simulator.payment_processing_workflow(
            customer_id, invoice_id, Decimal('999.99'), "credit_card"
        )
        
        assert not failed_payment_result.success
        assert "Payment processor declined" in failed_payment_result.errors[0]
        
        # STEP 2: Successful retry with correct amount
        correct_amount = billing_result.data['invoice']['total_amount']
        successful_payment_result = simulator.payment_processing_workflow(
            customer_id, invoice_id, correct_amount, "credit_card"
        )
        
        assert successful_payment_result.success
        payment = successful_payment_result.data['payment']
        assert payment['status'] == PaymentStatus.COMPLETED.value
        
        # Invoice should now be paid
        invoice = successful_payment_result.data['invoice']
        assert invoice['status'] == 'paid'
    
    def test_partial_payment_behavior(self):
        """BEHAVIOR: Handle partial payments correctly."""
        simulator = CustomerWorkflowSimulator()
        
        # Setup customer with $100 bill
        customer_data = {'display_name': 'Test Customer', 'customer_type': 'residential'}
        service_plan = ServicePlan(monthly_rate=Decimal('92.59'))  # Results in ~$100 with tax
        
        signup_result = simulator.customer_signup_workflow(customer_data, service_plan)
        customer_id = signup_result.data['customer']['customer_id']
        
        billing_result = simulator.monthly_billing_workflow(customer_id, {})
        invoice = billing_result.data['invoice']
        invoice_id = invoice['invoice_id']
        total_amount = invoice['total_amount']
        
        # Make partial payment (50%)
        partial_amount = total_amount / 2
        
        payment_result = simulator.payment_processing_workflow(
            customer_id, invoice_id, partial_amount, "credit_card"
        )
        
        assert payment_result.success
        
        # Invoice should be partially paid
        updated_invoice = payment_result.data['invoice']
        assert updated_invoice['status'] == 'partially_paid'
        assert updated_invoice['paid_amount'] == partial_amount
        
        # Make second payment for remaining amount
        remaining_amount = total_amount - partial_amount
        
        final_payment_result = simulator.payment_processing_workflow(
            customer_id, invoice_id, remaining_amount, "credit_card"
        )
        
        assert final_payment_result.success
        
        # Invoice should now be fully paid
        final_invoice = final_payment_result.data['invoice']
        assert final_invoice['status'] == 'paid'
        assert final_invoice['paid_amount'] == total_amount


@pytest.mark.behavior
@pytest.mark.business_rules
class TestBusinessRulesBehavior:
    """Test business rules and constraints through workflows."""
    
    def test_credit_check_requirements_by_customer_type(self):
        """BEHAVIOR: Different customer types have different credit requirements."""
        simulator = CustomerWorkflowSimulator()
        
        service_plan = ServicePlan(monthly_rate=Decimal('79.99'))
        
        # Test residential customer with poor credit
        residential_data = {
            'display_name': 'Poor Credit Customer',
            'customer_type': 'residential'
        }
        
        # Override credit score to test failure
        simulator_residential = CustomerWorkflowSimulator()
        def mock_credit_check_fail(customer):
            """Mock Credit Check Fail operation."""
            return False
        simulator_residential._perform_credit_check = mock_credit_check_fail
        
        result = simulator_residential.customer_signup_workflow(residential_data, service_plan)
        assert not result.success
        assert "Credit check failed" in result.errors
        
        # Test business customer with good credit
        business_data = {
            'display_name': 'Good Credit Business',
            'customer_type': 'business'
        }
        
        result = simulator.customer_signup_workflow(business_data, service_plan)
        assert result.success
        assert "credit_check_passed" in result.steps_completed


if __name__ == "__main__":
    # Quick behavior test
    simulator = CustomerWorkflowSimulator()
    
    customer_data = {'display_name': 'Test Customer', 'customer_type': 'residential'}
    service_plan = ServicePlan(monthly_rate=Decimal('79.99'))
    
    result = simulator.customer_signup_workflow(customer_data, service_plan)
    assert result.success, f"Workflow failed: {result.errors}"
    
logger.info("✅ Behavior testing validation passed!")