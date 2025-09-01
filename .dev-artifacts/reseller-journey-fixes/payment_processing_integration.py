"""
Payment Processing Integration Service
Implements automated payment processing for commission payouts, invoicing, and financial integrations
"""

from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import json
import hashlib
import hmac

from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.database.base import Base
from dotmac_isp.shared.base_service import BaseService


class PaymentProvider(str, Enum):
    STRIPE = "stripe"
    PAYPAL = "paypal"
    SQUARE = "square"
    BANK_TRANSFER = "bank_transfer"
    ACH = "ach"
    WIRE = "wire"
    CHECK = "check"


class PaymentType(str, Enum):
    COMMISSION_PAYOUT = "commission_payout"
    INVOICE_PAYMENT = "invoice_payment"
    REFUND = "refund"
    ADJUSTMENT = "adjustment"
    BONUS_PAYMENT = "bonus_payment"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"
    REFUNDED = "refunded"


class TaxCalculationMethod(str, Enum):
    FLAT_RATE = "flat_rate"
    BRACKET_BASED = "bracket_based"
    STATE_LOCAL = "state_local"
    INTERNATIONAL = "international"


class BankAccount(BaseModel):
    account_id: str
    account_holder_name: str
    bank_name: str
    routing_number: str = Field(..., regex="^[0-9]{9}$")
    account_number: str
    account_type: str = Field(..., regex="^(checking|savings|business_checking)$")
    country: str = "US"
    currency: str = "USD"
    is_verified: bool = False
    verification_date: Optional[datetime] = None


class PaymentMethod(BaseModel):
    method_id: str
    reseller_id: str
    provider: PaymentProvider
    method_type: str = Field(..., regex="^(bank_account|credit_card|paypal_account)$")
    bank_account: Optional[BankAccount] = None
    metadata: Dict[str, Any] = {}
    is_default: bool = False
    is_active: bool = True
    created_at: datetime
    last_used: Optional[datetime] = None


class TaxWithholding(BaseModel):
    reseller_id: str
    tax_year: int = Field(ge=2020, le=2030)
    federal_rate: Decimal = Field(ge=0, le=1)
    state_rate: Decimal = Field(ge=0, le=1)
    local_rate: Decimal = Field(ge=0, le=1)
    total_rate: Decimal = Field(ge=0, le=1)
    tax_id: Optional[str] = None  # SSN or EIN
    w9_on_file: bool = False
    
    @validator('total_rate')
    def validate_total_rate(cls, v, values):
        expected = values.get('federal_rate', 0) + values.get('state_rate', 0) + values.get('local_rate', 0)
        assert abs(v - expected) < Decimal('0.001'), "Total rate must equal sum of individual rates"
        return v


class PaymentRequest(BaseModel):
    request_id: str
    reseller_id: str
    payment_type: PaymentType
    amount: Decimal = Field(gt=0)
    currency: str = "USD"
    payment_method_id: str
    tax_withholding: Optional[TaxWithholding] = None
    gross_amount: Decimal = Field(gt=0)
    net_amount: Decimal = Field(gt=0)
    fees: Decimal = Field(ge=0)
    description: str
    reference_id: Optional[str] = None  # Commission calculation ID, invoice ID, etc.
    metadata: Dict[str, Any] = {}
    
    @validator('net_amount')
    def validate_net_amount(cls, v, values):
        if 'gross_amount' in values and 'fees' in values:
            expected = values['gross_amount'] - values['fees']
            if 'tax_withholding' in values and values['tax_withholding']:
                tax_amount = values['gross_amount'] * values['tax_withholding'].total_rate
                expected -= tax_amount
            assert abs(v - expected) < Decimal('0.01'), "Net amount calculation error"
        return v


class PaymentTransaction(BaseModel):
    transaction_id: str
    payment_request_id: str
    provider_transaction_id: Optional[str] = None
    status: PaymentStatus
    processed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    provider_response: Dict[str, Any] = {}
    fees_charged: Decimal = Field(ge=0)
    exchange_rate: Optional[Decimal] = None


class InvoiceItem(BaseModel):
    item_id: str
    description: str
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(ge=0)
    total_amount: Decimal = Field(ge=0)
    tax_rate: Decimal = Field(ge=0, le=1)
    tax_amount: Decimal = Field(ge=0)
    
    @validator('total_amount')
    def validate_total(cls, v, values):
        if 'quantity' in values and 'unit_price' in values:
            expected = values['quantity'] * values['unit_price']
            assert abs(v - expected) < Decimal('0.01'), "Total amount must equal quantity × unit price"
        return v


class Invoice(BaseModel):
    invoice_id: str
    reseller_id: str
    invoice_number: str
    issue_date: datetime
    due_date: datetime
    items: List[InvoiceItem] = []
    subtotal: Decimal = Field(ge=0)
    tax_amount: Decimal = Field(ge=0)
    total_amount: Decimal = Field(ge=0)
    currency: str = "USD"
    status: str = Field(..., regex="^(draft|sent|paid|overdue|cancelled)$")
    payment_terms: str = "Net 30"
    notes: Optional[str] = None


class PaymentProcessingService(BaseService):
    """Service for payment processing, tax calculation, and financial integrations"""
    
    def __init__(self, db: AsyncSession, tenant_id: Optional[str] = None):
        super().__init__(db, tenant_id)
        self.tax_rates = self._initialize_tax_rates()
        self.provider_configs = self._initialize_provider_configs()
        self.journey_templates = self._initialize_journey_templates()
    
    def _initialize_tax_rates(self) -> Dict[str, Dict[str, Decimal]]:
        """Initialize tax rates by state/jurisdiction"""
        
        return {
            "federal": {"rate": Decimal("0.22")},  # Federal tax withholding
            "states": {
                "CA": {"rate": Decimal("0.0725"), "name": "California"},
                "NY": {"rate": Decimal("0.0882"), "name": "New York"},
                "TX": {"rate": Decimal("0.0000"), "name": "Texas"},
                "FL": {"rate": Decimal("0.0000"), "name": "Florida"},
                "WA": {"rate": Decimal("0.0000"), "name": "Washington"}
            },
            "local": {
                "NYC": {"rate": Decimal("0.0378"), "state": "NY"},
                "LA": {"rate": Decimal("0.0050"), "state": "CA"},
                "CHICAGO": {"rate": Decimal("0.0325"), "state": "IL"}
            }
        }
    
    def _initialize_provider_configs(self) -> Dict[str, Dict[str, Any]]:
        """Initialize payment provider configurations"""
        
        return {
            PaymentProvider.STRIPE.value: {
                "api_base": "https://api.stripe.com",
                "fee_structure": {"rate": Decimal("0.029"), "fixed": Decimal("0.30")},
                "supported_methods": ["card", "ach", "wire"],
                "settlement_time_days": 2,
                "max_transaction": Decimal("100000.00")
            },
            PaymentProvider.ACH.value: {
                "fee_structure": {"rate": Decimal("0.008"), "fixed": Decimal("0.25")},
                "settlement_time_days": 3,
                "max_transaction": Decimal("1000000.00"),
                "min_transaction": Decimal("1.00")
            },
            PaymentProvider.WIRE.value: {
                "fee_structure": {"rate": Decimal("0.001"), "fixed": Decimal("25.00")},
                "settlement_time_days": 1,
                "max_transaction": Decimal("10000000.00"),
                "min_transaction": Decimal("1000.00")
            }
        }
    
    def _initialize_journey_templates(self) -> Dict[str, Any]:
        """Initialize payment processing journey templates"""
        
        return {
            "PAYMENT_PROCESSING": {
                "id": "payment_processing_automation",
                "name": "Payment Processing Automation Journey",
                "description": "End-to-end payment processing with validation and reconciliation",
                "category": "financial_processing",
                "version": "1.0.0",
                "steps": [
                    {
                        "id": "payment_validation",
                        "name": "Payment Request Validation",
                        "description": "Validate payment request details and compliance",
                        "stage": "validation",
                        "order": 1,
                        "type": "automated",
                        "packageName": "payment-processing",
                        "actionType": "validate_payment_request",
                        "estimatedDuration": 5
                    },
                    {
                        "id": "tax_calculation",
                        "name": "Tax Calculation",
                        "description": "Calculate applicable taxes and withholdings",
                        "stage": "calculation",
                        "order": 2,
                        "type": "automated", 
                        "packageName": "tax-service",
                        "actionType": "calculate_tax_withholding",
                        "estimatedDuration": 10,
                        "dependencies": ["payment_validation"]
                    },
                    {
                        "id": "payment_processing",
                        "name": "Payment Processing",
                        "description": "Process payment through selected provider",
                        "stage": "processing",
                        "order": 3,
                        "type": "integration",
                        "packageName": "payment-gateway",
                        "actionType": "process_payment",
                        "estimatedDuration": 30,
                        "dependencies": ["tax_calculation"]
                    },
                    {
                        "id": "transaction_confirmation",
                        "name": "Transaction Confirmation",
                        "description": "Confirm transaction completion and update records",
                        "stage": "confirmation",
                        "order": 4,
                        "type": "automated",
                        "packageName": "payment-processing",
                        "actionType": "confirm_transaction",
                        "estimatedDuration": 10,
                        "dependencies": ["payment_processing"]
                    },
                    {
                        "id": "notification_sending",
                        "name": "Send Notifications",
                        "description": "Send payment confirmation to reseller",
                        "stage": "notification",
                        "order": 5,
                        "type": "automated",
                        "packageName": "communication-system",
                        "actionType": "send_payment_notification",
                        "estimatedDuration": 5,
                        "dependencies": ["transaction_confirmation"]
                    }
                ]
            }
        }
    
    @standard_exception_handler
    async def calculate_tax_withholding(self, reseller_id: str, gross_amount: Decimal, jurisdiction: str = "CA") -> TaxWithholding:
        """Calculate tax withholding for commission payments"""
        
        # Get current tax year
        tax_year = datetime.utcnow().year
        
        # Federal rate
        federal_rate = self.tax_rates["federal"]["rate"]
        
        # State rate
        state_rate = self.tax_rates["states"].get(jurisdiction, {"rate": Decimal("0.00")})["rate"]
        
        # Local rate (simplified - would use actual address)
        local_rate = Decimal("0.00")  # Would calculate based on specific location
        
        # Total rate
        total_rate = federal_rate + state_rate + local_rate
        
        tax_withholding = TaxWithholding(
            reseller_id=reseller_id,
            tax_year=tax_year,
            federal_rate=federal_rate,
            state_rate=state_rate,
            local_rate=local_rate,
            total_rate=total_rate,
            w9_on_file=True  # Would check actual records
        )
        
        return tax_withholding
    
    @standard_exception_handler
    async def create_payment_request(
        self,
        reseller_id: str,
        payment_type: PaymentType,
        gross_amount: Decimal,
        payment_method_id: str,
        reference_id: Optional[str] = None,
        description: str = ""
    ) -> PaymentRequest:
        """Create payment request with tax calculations"""
        
        # Calculate tax withholding
        tax_withholding = await self.calculate_tax_withholding(reseller_id, gross_amount)
        
        # Calculate fees (based on payment method)
        payment_method = await self._get_payment_method(payment_method_id)
        fees = await self._calculate_processing_fees(gross_amount, payment_method.provider)
        
        # Calculate net amount
        tax_amount = gross_amount * tax_withholding.total_rate
        net_amount = gross_amount - tax_amount - fees
        
        payment_request = PaymentRequest(
            request_id=f"pay_req_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{reseller_id}",
            reseller_id=reseller_id,
            payment_type=payment_type,
            amount=net_amount,
            payment_method_id=payment_method_id,
            tax_withholding=tax_withholding,
            gross_amount=gross_amount,
            net_amount=net_amount,
            fees=fees,
            description=description or f"{payment_type.value} payment",
            reference_id=reference_id,
            metadata={
                "tax_amount": str(tax_amount),
                "tax_rate": str(tax_withholding.total_rate),
                "processing_fees": str(fees)
            }
        )
        
        return payment_request
    
    @standard_exception_handler
    async def process_payment(self, payment_request: PaymentRequest) -> PaymentTransaction:
        """Process payment through appropriate provider"""
        
        payment_method = await self._get_payment_method(payment_request.payment_method_id)
        
        # Create transaction record
        transaction = PaymentTransaction(
            transaction_id=f"txn_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{payment_request.request_id[-8:]}",
            payment_request_id=payment_request.request_id,
            status=PaymentStatus.PROCESSING,
            fees_charged=payment_request.fees
        )
        
        try:
            # Process based on provider
            if payment_method.provider == PaymentProvider.ACH:
                result = await self._process_ach_payment(payment_request, payment_method)
            elif payment_method.provider == PaymentProvider.WIRE:
                result = await self._process_wire_transfer(payment_request, payment_method)
            elif payment_method.provider == PaymentProvider.STRIPE:
                result = await self._process_stripe_payment(payment_request, payment_method)
            else:
                raise ValueError(f"Unsupported payment provider: {payment_method.provider}")
            
            # Update transaction with results
            transaction.provider_transaction_id = result.get("transaction_id")
            transaction.status = PaymentStatus.COMPLETED if result.get("success") else PaymentStatus.FAILED
            transaction.processed_at = datetime.utcnow()
            transaction.provider_response = result
            
            if transaction.status == PaymentStatus.COMPLETED:
                transaction.completed_at = datetime.utcnow()
            else:
                transaction.failure_reason = result.get("error_message")
                
        except Exception as e:
            transaction.status = PaymentStatus.FAILED
            transaction.failure_reason = str(e)
            transaction.processed_at = datetime.utcnow()
        
        return transaction
    
    @standard_exception_handler
    async def create_invoice(
        self,
        reseller_id: str,
        items: List[InvoiceItem],
        due_date: Optional[datetime] = None,
        payment_terms: str = "Net 30"
    ) -> Invoice:
        """Create invoice for reseller services"""
        
        if not due_date:
            due_date = datetime.utcnow() + timedelta(days=30)
        
        # Calculate totals
        subtotal = sum(item.total_amount for item in items)
        tax_amount = sum(item.tax_amount for item in items)
        total_amount = subtotal + tax_amount
        
        invoice = Invoice(
            invoice_id=f"inv_{datetime.utcnow().strftime('%Y%m%d')}_{reseller_id}",
            reseller_id=reseller_id,
            invoice_number=f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{reseller_id[-4:].upper()}",
            issue_date=datetime.utcnow(),
            due_date=due_date,
            items=items,
            subtotal=subtotal,
            tax_amount=tax_amount,
            total_amount=total_amount,
            status="draft",
            payment_terms=payment_terms
        )
        
        return invoice
    
    @standard_exception_handler
    async def validate_payment_method(self, payment_method_id: str) -> Dict[str, Any]:
        """Validate payment method details"""
        
        payment_method = await self._get_payment_method(payment_method_id)
        
        validation_results = {
            "is_valid": True,
            "validation_checks": [],
            "warnings": [],
            "errors": []
        }
        
        # Validate bank account if present
        if payment_method.bank_account:
            bank_account = payment_method.bank_account
            
            # Check routing number
            if not self._validate_routing_number(bank_account.routing_number):
                validation_results["errors"].append("Invalid routing number")
                validation_results["is_valid"] = False
            
            # Check account verification
            if not bank_account.is_verified:
                validation_results["warnings"].append("Bank account not verified")
            
            # Check account age
            if payment_method.created_at > datetime.utcnow() - timedelta(days=7):
                validation_results["warnings"].append("Recently added payment method")
        
        validation_results["validation_checks"] = [
            "Routing number format",
            "Account verification status", 
            "Payment method age",
            "Provider compliance"
        ]
        
        return validation_results
    
    @standard_exception_handler
    async def reconcile_payments(self, date_range: Optional[tuple] = None) -> Dict[str, Any]:
        """Reconcile payments for accounting purposes"""
        
        if not date_range:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)
        else:
            start_date, end_date = date_range
        
        # Mock implementation - would query actual payment data
        reconciliation_data = {
            "reconciliation_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "payment_summary": {
                "total_payments": 45,
                "total_amount": Decimal("125000.00"),
                "successful_payments": 43,
                "failed_payments": 2,
                "disputed_payments": 0,
                "pending_payments": 0
            },
            "by_payment_type": {
                PaymentType.COMMISSION_PAYOUT.value: {
                    "count": 35,
                    "amount": Decimal("98000.00")
                },
                PaymentType.BONUS_PAYMENT.value: {
                    "count": 8,
                    "amount": Decimal("24000.00")
                },
                PaymentType.ADJUSTMENT.value: {
                    "count": 2,
                    "amount": Decimal("3000.00")
                }
            },
            "by_provider": {
                PaymentProvider.ACH.value: {
                    "count": 32,
                    "amount": Decimal("87000.00"),
                    "fees": Decimal("348.00")
                },
                PaymentProvider.WIRE.value: {
                    "count": 11,
                    "amount": Decimal("38000.00"),
                    "fees": Decimal("275.00")
                }
            },
            "tax_withholdings": {
                "total_withheld": Decimal("27500.00"),
                "federal": Decimal("22000.00"),
                "state": Decimal("4500.00"),
                "local": Decimal("1000.00")
            },
            "discrepancies": [],
            "next_reconciliation": (end_date + timedelta(days=30)).isoformat()
        }
        
        return reconciliation_data
    
    async def _get_payment_method(self, payment_method_id: str) -> PaymentMethod:
        """Get payment method by ID"""
        
        # Mock implementation - would query actual database
        return PaymentMethod(
            method_id=payment_method_id,
            reseller_id="reseller_001",
            provider=PaymentProvider.ACH,
            method_type="bank_account",
            bank_account=BankAccount(
                account_id="acct_001",
                account_holder_name="Reseller Business LLC",
                bank_name="First National Bank",
                routing_number="021000021",
                account_number="****1234",
                account_type="business_checking",
                is_verified=True,
                verification_date=datetime.utcnow() - timedelta(days=5)
            ),
            is_default=True,
            created_at=datetime.utcnow() - timedelta(days=30)
        )
    
    async def _calculate_processing_fees(self, amount: Decimal, provider: PaymentProvider) -> Decimal:
        """Calculate processing fees based on provider and amount"""
        
        provider_config = self.provider_configs.get(provider.value, {})
        fee_structure = provider_config.get("fee_structure", {"rate": Decimal("0.01"), "fixed": Decimal("0.30")})
        
        rate_fee = amount * fee_structure["rate"]
        fixed_fee = fee_structure["fixed"]
        
        total_fee = rate_fee + fixed_fee
        return total_fee.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    def _validate_routing_number(self, routing_number: str) -> bool:
        """Validate routing number using check digit algorithm"""
        
        if len(routing_number) != 9 or not routing_number.isdigit():
            return False
        
        # ABA routing number check digit validation
        weights = [3, 7, 1, 3, 7, 1, 3, 7, 1]
        check_sum = sum(int(digit) * weight for digit, weight in zip(routing_number, weights))
        
        return check_sum % 10 == 0
    
    async def _process_ach_payment(self, payment_request: PaymentRequest, payment_method: PaymentMethod) -> Dict[str, Any]:
        """Process ACH payment"""
        
        # Mock implementation - would integrate with actual ACH processor
        await asyncio.sleep(0.1)  # Simulate processing time
        
        return {
            "success": True,
            "transaction_id": f"ach_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "settlement_date": (datetime.utcnow() + timedelta(days=3)).isoformat(),
            "status": "processing",
            "fees": str(payment_request.fees)
        }
    
    async def _process_wire_transfer(self, payment_request: PaymentRequest, payment_method: PaymentMethod) -> Dict[str, Any]:
        """Process wire transfer"""
        
        # Mock implementation - would integrate with banking APIs
        await asyncio.sleep(0.2)  # Simulate processing time
        
        return {
            "success": True,
            "transaction_id": f"wire_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "settlement_date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "status": "completed",
            "fees": str(payment_request.fees)
        }
    
    async def _process_stripe_payment(self, payment_request: PaymentRequest, payment_method: PaymentMethod) -> Dict[str, Any]:
        """Process Stripe payment"""
        
        # Mock implementation - would use Stripe API
        await asyncio.sleep(0.1)
        
        return {
            "success": True,
            "transaction_id": f"stripe_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "settlement_date": (datetime.utcnow() + timedelta(days=2)).isoformat(),
            "status": "completed",
            "fees": str(payment_request.fees)
        }


# Journey template exports
PAYMENT_PROCESSING_JOURNEY_TEMPLATES = {
    "PAYMENT_PROCESSING": PaymentProcessingService(None)._initialize_journey_templates()["PAYMENT_PROCESSING"]
}

__all__ = [
    "PaymentProvider",
    "PaymentType",
    "PaymentStatus", 
    "TaxCalculationMethod",
    "BankAccount",
    "PaymentMethod",
    "TaxWithholding",
    "PaymentRequest",
    "PaymentTransaction",
    "InvoiceItem",
    "Invoice",
    "PaymentProcessingService",
    "PAYMENT_PROCESSING_JOURNEY_TEMPLATES"
]