"""
Process Billing Use Case
Orchestrates billing operations for tenant services
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
import os
import secrets

from dotmac_shared.core.logging import get_logger
from dotmac_shared.exceptions import ExceptionContext
from dotmac_shared.business_logic.idempotency import (
    IdempotencyKey,
    IdempotencyManager,
    IdempotentOperation,
    OperationResult,
    OperationStatus,
)

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
            correlation_id = context.correlation_id if context else f"billing-{secrets.token_hex(8)}"
            
            self.logger.info(
                "Processing billing operation",
                extra={
                    "tenant_id": input_data.tenant_id,
                    "operation": input_data.operation.value,
                    "period_start": input_data.billing_period_start,
                    "period_end": input_data.billing_period_end,
                    "correlation_id": correlation_id,
                },
            )

            # Phase 3: Add idempotency to critical billing operations
            if os.getenv("BUSINESS_LOGIC_WORKFLOWS_ENABLED", "false").lower() == "true":
                return await self._execute_with_idempotency(input_data, context, correlation_id)

            # Execute the specific billing operation
            billing_result = await self._execute_billing_operation(input_data)

            if not billing_result["success"]:
                return self._create_error_result(billing_result["error"], error_code="BILLING_OPERATION_FAILED")

            # Create output data
            output_data = ProcessBillingOutput(
                tenant_id=input_data.tenant_id,
                operation=input_data.operation,
                billing_period={
                    "start": input_data.billing_period_start,
                    "end": input_data.billing_period_end,
                },
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
            return {
                "success": False,
                "error": f"Unsupported billing operation: {input_data.operation}",
            }

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
                "details": {
                    "calculation_method": "usage_based",
                    "calculated_at": datetime.utcnow().isoformat(),
                },
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

    async def _execute_with_idempotency(
        self, input_data: ProcessBillingInput, context: Optional[UseCaseContext], correlation_id: str
    ) -> UseCaseResult[ProcessBillingOutput]:
        """Execute billing operation with idempotency guarantees (Phase 3)"""
        try:
            # Generate idempotency key based on billing operation and period
            op_key = IdempotencyKey.generate(
                operation_type=f"billing_{input_data.operation.value}",
                tenant_id=input_data.tenant_id,
                operation_data={
                    "operation": input_data.operation.value,
                    "billing_period_start": input_data.billing_period_start,
                    "billing_period_end": input_data.billing_period_end,
                    "parameters": input_data.parameters,
                },
            )

            # Context for operation metadata
            op_context = {
                "correlation_id": correlation_id,
                "initiator": context.user_id if context else None,
                "use_case": "ProcessBillingUseCase",
                "operation": input_data.operation.value,
            }

            # Get or create idempotency manager
            idempotency_manager = getattr(self, '_idempotency_manager', None)
            
            if not idempotency_manager:
                from dotmac.database.base import get_db_session
                
                def _db_session_factory():
                    return get_db_session()
                
                idempotency_manager = IdempotencyManager(db_session_factory=_db_session_factory)
                self.logger.warning("Using local IdempotencyManager instance - consider injecting from service layer")

            # Define idempotent billing operation
            outer_self = self
            
            class BillingIdempotentOperation(IdempotentOperation[dict[str, Any]]):
                def __init__(self):
                    # Different TTLs based on operation type
                    ttl_map = {
                        "calculate_usage": 3600,  # 1 hour
                        "generate_invoice": 86400,  # 24 hours  
                        "process_payment": 300,  # 5 minutes
                        "apply_credits": 3600,  # 1 hour
                        "handle_dispute": 86400,  # 24 hours
                    }
                    ttl = ttl_map.get(input_data.operation.value, 3600)
                    
                    super().__init__(
                        operation_type=f"billing_{input_data.operation.value}",
                        max_attempts=3,
                        ttl_seconds=ttl
                    )

                def validate_operation_data(self, data: dict[str, Any]) -> None:
                    required_fields = ["operation", "billing_period_start", "billing_period_end"]
                    missing = [field for field in required_fields if not data.get(field)]
                    if missing:
                        raise ValueError(f"Missing required billing fields: {', '.join(missing)}")
                    
                    # Validate operation type
                    if data.get("operation") not in [op.value for op in BillingOperation]:
                        raise ValueError(f"Invalid billing operation: {data.get('operation')}")

                async def execute(self, data: dict[str, Any], ctx: Optional[dict[str, Any]] = None) -> dict[str, Any]:
                    # Execute the billing operation
                    billing_result = await outer_self._execute_billing_operation(input_data)
                    
                    if not billing_result["success"]:
                        raise Exception(billing_result["error"])
                    
                    # Convert result to serializable format
                    return {
                        "tenant_id": input_data.tenant_id,
                        "operation": input_data.operation.value,
                        "billing_period": {
                            "start": input_data.billing_period_start,
                            "end": input_data.billing_period_end,
                        },
                        "line_items": [
                            {
                                "service": item.service,
                                "description": item.description,
                                "quantity": str(item.quantity),
                                "unit_price": str(item.unit_price),
                                "total": str(item.total),
                                "usage_data": item.usage_data,
                            }
                            for item in billing_result["line_items"]
                        ],
                        "subtotal": str(billing_result["subtotal"]),
                        "taxes": str(billing_result["taxes"]),
                        "credits_applied": str(billing_result["credits_applied"]),
                        "total": str(billing_result["total"]),
                        "invoice_id": billing_result.get("invoice_id"),
                        "payment_status": billing_result.get("payment_status"),
                        "processing_details": billing_result.get("details", {}),
                        "processed_at": datetime.utcnow().isoformat(),
                    }

            # Register the operation
            operation_name = f"billing_{input_data.operation.value}"
            idempotency_manager.register_operation(operation_name, BillingIdempotentOperation)

            # Execute with idempotency
            op_result: OperationResult = await idempotency_manager.execute_idempotent(
                op_key, op_key.model_dump(), op_context  # type: ignore[attr-defined]
            )

            if op_result.success and op_result.data:
                # Convert back to proper types
                result_data = op_result.data
                
                # Reconstruct line items
                line_items = []
                for item_data in result_data.get("line_items", []):
                    line_items.append(BillingLineItem(
                        service=item_data["service"],
                        description=item_data["description"],
                        quantity=Decimal(item_data["quantity"]),
                        unit_price=Decimal(item_data["unit_price"]),
                        total=Decimal(item_data["total"]),
                        usage_data=item_data.get("usage_data", {}),
                    ))
                
                # Create output
                output_data = ProcessBillingOutput(
                    tenant_id=result_data["tenant_id"],
                    operation=BillingOperation(result_data["operation"]),
                    billing_period=result_data["billing_period"],
                    line_items=line_items,
                    subtotal=Decimal(result_data["subtotal"]),
                    taxes=Decimal(result_data["taxes"]),
                    credits_applied=Decimal(result_data["credits_applied"]),
                    total=Decimal(result_data["total"]),
                    invoice_id=result_data.get("invoice_id"),
                    payment_status=result_data.get("payment_status"),
                    processing_details=result_data.get("processing_details", {}),
                )
                
                return self._create_success_result(
                    output_data,
                    metadata={
                        "correlation_id": correlation_id,
                        "idempotency_key": str(op_key),
                        "from_cache": op_result.from_cache,
                        "execution_method": "idempotent_operation",
                        "processed_at": result_data.get("processed_at"),
                    }
                )
            
            # Handle in-progress or failed operations
            if op_result.status == OperationStatus.IN_PROGRESS:
                return self._create_error_result(
                    "Billing operation already in progress",
                    error_code="BILLING_IN_PROGRESS"
                )
            
            return self._create_error_result(
                f"Billing operation failed: {op_result.error_message or 'Unknown error'}",
                error_code="IDEMPOTENT_BILLING_FAILED"
            )

        except Exception as e:
            self.logger.error(f"Idempotent billing execution failed: {e}")
            return self._create_error_result(
                f"Failed to execute idempotent billing operation: {str(e)}",
                error_code="IDEMPOTENCY_ERROR"
            )

    def inject_idempotency_manager(self, idempotency_manager):
        """Inject idempotency manager for workflow orchestration (Phase 3)"""
        self._idempotency_manager = idempotency_manager
