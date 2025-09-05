"""
Process Billing Use Case
Orchestrates billing operations for tenant services
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from dotmac_shared.core.logging import get_logger
from dotmac_shared.exceptions import ExceptionContext

from ..base import TransactionalUseCase, UseCaseContext, UseCaseResult

logger = get_logger(__name__)


class BillingOperation(str, Enum):
    """Available billing operations"""

    CALCULATE_USAGE = "calculate_usage"
    GENERATE_INVOICE = "generate_invoice"
    PROCESS_PAYMENT = "process_payment"
    APPLY_CREDITS = "apply_credits"
    HANDLE_DISPUTE = "handle_dispute"


@dataclass
class ProcessBillingInput:
    """Input data for billing processing"""

    tenant_id: str
    operation: BillingOperation
    billing_period_start: str
    billing_period_end: str
    parameters: dict[str, Any] = None

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


@dataclass
class BillingLineItem:
    """Billing line item"""

    service: str
    description: str
    quantity: Decimal
    unit_price: Decimal
    total: Decimal
    usage_data: dict[str, Any] = None

    def __post_init__(self):
        if self.usage_data is None:
            self.usage_data = {}


@dataclass
class ProcessBillingOutput:
    """Output data for billing processing"""

    tenant_id: str
    operation: BillingOperation
    billing_period: dict[str, str]
    line_items: list[BillingLineItem]
    subtotal: Decimal
    taxes: Decimal
    credits_applied: Decimal
    total: Decimal
    invoice_id: Optional[str] = None
    payment_status: Optional[str] = None
    processing_details: dict[str, Any] = None

    def __post_init__(self):
        if self.processing_details is None:
            self.processing_details = {}


class ProcessBillingUseCase(TransactionalUseCase[ProcessBillingInput, ProcessBillingOutput]):
    """
    Process billing operations for tenant services.

    Handles:
    - Usage calculation and metering
    - Invoice generation
    - Payment processing
    - Credit application
    - Dispute handling

    This use case orchestrates the complex billing workflow
    and ensures all billing operations are consistent and auditable.
    """

    def __init__(self, input_data: dict[str, Any]):
        super().__init__()

    async def validate_input(self, input_data: ProcessBillingInput) -> bool:
        """Validate billing input"""
        if not input_data.tenant_id:
            return False

        if not input_data.operation:
            return False

        try:
            datetime.fromisoformat(input_data.billing_period_start.replace("Z", "+00:00"))
            datetime.fromisoformat(input_data.billing_period_end.replace("Z", "+00:00"))
        except ValueError:
            return False

        return True

    async def can_execute(self, input_data: dict[str, Any], context: Optional[UseCaseContext] = None) -> bool:
        """Check if billing operation can be executed"""

        # Check permissions
        if context and context.permissions:
            required_permission = f"billing.{input_data.operation.value}"
            user_permissions = context.permissions.get("actions", [])

            if required_permission not in user_permissions:
                return False

        return True

    async def _execute_transaction(
        self, input_data: ProcessBillingInput, context: Optional[UseCaseContext] = None
    ) -> UseCaseResult[ProcessBillingOutput]:
        """Execute the billing transaction"""

        try:
            self.logger.info(
                "Processing billing operation",
                extra={
                    "tenant_id": input_data.tenant_id,
                    "operation": input_data.operation.value,
                    "period_start": input_data.billing_period_start,
                    "period_end": input_data.billing_period_end,
                },
            )

            # Execute the specific billing operation
            billing_result = await self._execute_billing_operation(input_data)

            if not billing_result["success"]:
                return self._create_error_result(billing_result["error"], error_code="BILLING_OPERATION_FAILED")

            # Create output data
            output_data = ProcessBillingOutput(
                tenant_id=input_data.tenant_id,
                operation=input_data.operation,
                billing_period={"start": input_data.billing_period_start, "end": input_data.billing_period_end},
                line_items=billing_result["line_items"],
                subtotal=billing_result["subtotal"],
                taxes=billing_result["taxes"],
                credits_applied=billing_result["credits_applied"],
                total=billing_result["total"],
                invoice_id=billing_result.get("invoice_id"),
                payment_status=billing_result.get("payment_status"),
                processing_details=billing_result.get("details", {}),
            )

            return self._create_success_result(output_data)

        except ExceptionContext.LIFECYCLE_EXCEPTIONS as e:
            self.logger.error(f"Billing transaction failed: {e}")
            return self._create_error_result(str(e), error_code="BILLING_TRANSACTION_FAILED")

    async def _execute_billing_operation(self, input_data: ProcessBillingInput) -> dict[str, Any]:
        """Execute the specific billing operation"""

        operation_map = {
            BillingOperation.CALCULATE_USAGE: self._calculate_usage,
            BillingOperation.GENERATE_INVOICE: self._generate_invoice,
            BillingOperation.PROCESS_PAYMENT: self._process_payment,
            BillingOperation.APPLY_CREDITS: self._apply_credits,
            BillingOperation.HANDLE_DISPUTE: self._handle_dispute,
        }

        operation_func = operation_map.get(input_data.operation)
        if not operation_func:
            return {"success": False, "error": f"Unsupported billing operation: {input_data.operation}"}

        return await operation_func(input_data)

    async def _calculate_usage(self, input_data: ProcessBillingInput) -> dict[str, Any]:
        """Calculate usage for billing period"""
        try:
            # Mock implementation - would integrate with actual metering service
            line_items = [
                BillingLineItem(
                    service="compute",
                    description="Container hosting",
                    quantity=Decimal("720"),  # hours in month
                    unit_price=Decimal("0.05"),
                    total=Decimal("36.00"),
                    usage_data={"cpu_hours": 720, "memory_gb_hours": 1440},
                ),
                BillingLineItem(
                    service="storage",
                    description="Database storage",
                    quantity=Decimal("10"),  # GB
                    unit_price=Decimal("0.10"),
                    total=Decimal("1.00"),
                    usage_data={"storage_gb": 10},
                ),
                BillingLineItem(
                    service="bandwidth",
                    description="Data transfer",
                    quantity=Decimal("100"),  # GB
                    unit_price=Decimal("0.02"),
                    total=Decimal("2.00"),
                    usage_data={"transfer_gb": 100},
                ),
            ]

            subtotal = sum(item.total for item in line_items)
            taxes = subtotal * Decimal("0.08")  # 8% tax
            credits_applied = Decimal("0.00")
            total = subtotal + taxes - credits_applied

            return {
                "success": True,
                "line_items": line_items,
                "subtotal": subtotal,
                "taxes": taxes,
                "credits_applied": credits_applied,
                "total": total,
                "details": {"calculation_method": "usage_based", "calculated_at": datetime.utcnow().isoformat()},
            }

        except (ValueError, TypeError) as e:
            return {"success": False, "error": f"Usage calculation failed: {e}"}

    async def _generate_invoice(self, input_data: ProcessBillingInput) -> dict[str, Any]:
        """Generate invoice for tenant"""
        try:
            # First calculate usage
            usage_result = await self._calculate_usage(input_data)
            if not usage_result["success"]:
                return usage_result

            # Generate invoice ID
            invoice_id = f"INV-{input_data.tenant_id}-{int(datetime.utcnow().timestamp())}"

            return {
                **usage_result,
                "invoice_id": invoice_id,
                "details": {
                    "invoice_generated_at": datetime.utcnow().isoformat(),
                    "due_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
                    "payment_terms": "Net 30",
                },
            }

        except (ValueError, TypeError) as e:
            return {"success": False, "error": f"Invoice generation failed: {e}"}

    async def _process_payment(self, input_data: ProcessBillingInput) -> dict[str, Any]:
        """Process payment for invoice"""
        try:
            # Mock payment processing
            payment_method = input_data.parameters.get("payment_method", "credit_card")
            amount = Decimal(input_data.parameters.get("amount", "0"))

            # Would integrate with actual payment processor
            payment_id = f"PAY-{int(datetime.utcnow().timestamp())}"

            return {
                "success": True,
                "line_items": [],
                "subtotal": amount,
                "taxes": Decimal("0.00"),
                "credits_applied": Decimal("0.00"),
                "total": amount,
                "payment_status": "completed",
                "details": {
                    "payment_id": payment_id,
                    "payment_method": payment_method,
                    "processed_at": datetime.utcnow().isoformat(),
                },
            }

        except (ValueError, TypeError) as e:
            return {"success": False, "error": f"Payment processing failed: {e}"}

    async def _apply_credits(self, input_data: ProcessBillingInput) -> dict[str, Any]:
        """Apply credits to billing"""
        try:
            credit_amount = Decimal(input_data.parameters.get("credit_amount", "0"))

            return {
                "success": True,
                "line_items": [],
                "subtotal": Decimal("0.00"),
                "taxes": Decimal("0.00"),
                "credits_applied": credit_amount,
                "total": -credit_amount,
                "details": {
                    "credit_applied_at": datetime.utcnow().isoformat(),
                    "credit_reason": input_data.parameters.get("reason", "Manual credit"),
                },
            }

        except (ValueError, TypeError) as e:
            return {"success": False, "error": f"Credit application failed: {e}"}

    async def _handle_dispute(self, input_data: ProcessBillingInput) -> dict[str, Any]:
        """Handle billing dispute"""
        try:
            dispute_reason = input_data.parameters.get("dispute_reason", "")
            dispute_amount = Decimal(input_data.parameters.get("dispute_amount", "0"))

            return {
                "success": True,
                "line_items": [],
                "subtotal": Decimal("0.00"),
                "taxes": Decimal("0.00"),
                "credits_applied": Decimal("0.00"),
                "total": Decimal("0.00"),
                "details": {
                    "dispute_id": f"DISP-{int(datetime.utcnow().timestamp())}",
                    "dispute_reason": dispute_reason,
                    "dispute_amount": dispute_amount,
                    "dispute_status": "under_review",
                    "created_at": datetime.utcnow().isoformat(),
                },
            }

        except (ValueError, TypeError) as e:
            return {"success": False, "error": f"Dispute handling failed: {e}"}
