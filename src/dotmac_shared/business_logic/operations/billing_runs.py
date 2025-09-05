"""
Billing Run Operations

Idempotent operations and saga orchestration for billing runs
including invoice generation, payment processing, and notifications.
"""

import asyncio
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Optional
from uuid import uuid4

from ...standard_exception_handler import standard_exception_handler
from ..exceptions import BillingRunError, ErrorContext
from ..idempotency import IdempotentOperation
from ..sagas import CompensationHandler, SagaContext, SagaDefinition, SagaStep


class ValidateBillingPeriodStep(SagaStep):
    """Step to validate billing period and prerequisites"""

    def __init__(self):
        super().__init__(
            name="validate_billing_period",
            timeout_seconds=30,
            retry_count=3,
            compensation_required=False,
        )

    @standard_exception_handler
    async def execute(self, context: SagaContext) -> dict[str, Any]:
        """Validate billing period and system readiness"""
        billing_request = context.get_shared_data("billing_request")

        billing_period = billing_request["billing_period"]
        tenant_id = billing_request.get("tenant_id")

        # Parse billing period (e.g., "2024-03")
        try:
            period_parts = billing_period.split("-")
            if len(period_parts) != 2:
                raise ValueError("Invalid billing period format. Use YYYY-MM")

            year = int(period_parts[0])
            month = int(period_parts[1])

            if month < 1 or month > 12:
                raise ValueError("Invalid month in billing period")

            period_start = date(year, month, 1)

            # Calculate period end
            if month == 12:
                period_end = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                period_end = date(year, month + 1, 1) - timedelta(days=1)

        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid billing period format: {e}") from e

        # Check if billing period is in the past
        today = date.today()
        if period_end > today:
            raise ValueError("Cannot run billing for future periods")

        # Check if billing has already been run for this period
        # (In real implementation, check database)

        validation_result = {
            "billing_period": billing_period,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "tenant_id": tenant_id,
            "validated_at": datetime.utcnow().isoformat(),
            "estimated_customers": billing_request.get("estimated_customers", 0),
            "dry_run": billing_request.get("dry_run", False),
        }

        context.set_shared_data("validation_result", validation_result)

        await asyncio.sleep(0.1)  # Simulate validation

        return validation_result

    @standard_exception_handler
    async def compensate(self, context: SagaContext) -> None:
        """No compensation needed for validation"""
        pass


class GenerateInvoicesStep(SagaStep):
    """Step to generate invoices for billing period"""

    def __init__(self):
        super().__init__(
            name="generate_invoices",
            timeout_seconds=300,  # 5 minutes for potentially many invoices
            retry_count=2,
            compensation_required=True,
        )

    @standard_exception_handler
    async def execute(self, context: SagaContext) -> dict[str, Any]:
        """Generate invoices for all eligible customers"""
        billing_request = context.get_shared_data("billing_request")
        validation_result = context.get_shared_data("validation_result")

        tenant_id = billing_request.get("tenant_id")
        billing_period = validation_result["billing_period"]
        is_dry_run = validation_result["dry_run"]

        # Get customers eligible for billing
        eligible_customers = await self._get_eligible_customers(
            tenant_id, validation_result
        )

        generated_invoices = []
        failed_customers = []
        total_amount = Decimal("0.00")

        for customer in eligible_customers:
            try:
                invoice = await self._generate_customer_invoice(
                    customer, validation_result, is_dry_run
                )
                generated_invoices.append(invoice)
                total_amount += Decimal(str(invoice["total_amount"]))

            except Exception as e:
                failed_customers.append(
                    {
                        "customer_id": customer["customer_id"],
                        "error": str(e),
                        "failed_at": datetime.utcnow().isoformat(),
                    }
                )

        invoice_generation_result = {
            "billing_period": billing_period,
            "tenant_id": tenant_id,
            "total_customers": len(eligible_customers),
            "successful_invoices": len(generated_invoices),
            "failed_invoices": len(failed_customers),
            "total_amount": float(total_amount),
            "invoices": generated_invoices,
            "failed_customers": failed_customers,
            "generated_at": datetime.utcnow().isoformat(),
            "dry_run": is_dry_run,
        }

        context.set_shared_data("invoice_generation_result", invoice_generation_result)

        await asyncio.sleep(0.2)  # Simulate invoice generation

        return invoice_generation_result

    async def _get_eligible_customers(
        self, tenant_id: Optional[str], validation_result: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Get customers eligible for billing"""

        # Simulate customer data
        base_customers = [
            {
                "customer_id": f"cust_{i:05d}",
                "name": f"Customer {i}",
                "email": f"customer{i}@example.com",
                "services": [
                    {
                        "service_id": f"svc_{i}_{j}",
                        "service_type": "internet" if j == 0 else "hosting",
                        "plan": "standard" if i % 2 == 0 else "premium",
                        "monthly_fee": 79.99 if j == 0 else 24.99,
                        "prorated_amount": 79.99 if j == 0 else 24.99,
                        "usage_charges": 0.00,
                    }
                    for j in range(1 if i % 3 == 0 else 2)
                ],
                "billing_address": {
                    "country": "US",
                    "state": "CA",
                    "city": "San Francisco",
                },
            }
            for i in range(1, 11)  # Generate 10 test customers
        ]

        # Filter by tenant if specified
        if tenant_id:
            return [
                c
                for c in base_customers
                if c["customer_id"].endswith("1") or c["customer_id"].endswith("5")
            ]

        return base_customers

    async def _generate_customer_invoice(
        self,
        customer: dict[str, Any],
        validation_result: dict[str, Any],
        is_dry_run: bool,
    ) -> dict[str, Any]:
        """Generate invoice for a single customer"""

        customer_id = customer["customer_id"]
        billing_period = validation_result["billing_period"]

        # Calculate invoice line items
        line_items = []
        subtotal = Decimal("0.00")

        for service in customer["services"]:
            line_item = {
                "service_id": service["service_id"],
                "service_type": service["service_type"],
                "plan": service["plan"],
                "description": f"{service['service_type'].title()} - {service['plan'].title()} Plan",
                "quantity": 1,
                "unit_price": service["monthly_fee"],
                "prorated_amount": service["prorated_amount"],
                "usage_charges": service["usage_charges"],
                "line_total": service["prorated_amount"] + service["usage_charges"],
            }
            line_items.append(line_item)
            subtotal += Decimal(str(line_item["line_total"]))

        # Calculate taxes
        tax_rate = Decimal("0.0875")  # 8.75% tax
        tax_amount = subtotal * tax_rate
        total_amount = subtotal + tax_amount

        invoice = {
            "invoice_id": str(uuid4()),
            "customer_id": customer_id,
            "customer_name": customer["name"],
            "customer_email": customer["email"],
            "billing_period": billing_period,
            "invoice_date": datetime.utcnow().date().isoformat(),
            "due_date": (datetime.utcnow() + timedelta(days=30)).date().isoformat(),
            "line_items": line_items,
            "subtotal": float(subtotal),
            "tax_rate": float(tax_rate),
            "tax_amount": float(tax_amount),
            "total_amount": float(total_amount),
            "currency": "USD",
            "status": "draft" if is_dry_run else "pending",
            "billing_address": customer["billing_address"],
            "generated_at": datetime.utcnow().isoformat(),
        }

        return invoice

    @standard_exception_handler
    async def compensate(self, context: SagaContext) -> None:
        """Remove generated invoices"""
        invoice_generation_result = context.get_shared_data("invoice_generation_result")

        if invoice_generation_result and not invoice_generation_result.get("dry_run"):
            # In real implementation, mark invoices as cancelled/void
            cancelled_invoices = []

            for invoice in invoice_generation_result.get("invoices", []):
                cancelled_invoices.append(
                    {
                        "invoice_id": invoice["invoice_id"],
                        "customer_id": invoice["customer_id"],
                        "cancelled_at": datetime.utcnow().isoformat(),
                    }
                )

            context.set_shared_data("cancelled_invoices", cancelled_invoices)

        await asyncio.sleep(0.1)  # Simulate cancellation


class ProcessPaymentsStep(SagaStep):
    """Step to process payments for generated invoices"""

    def __init__(self):
        super().__init__(
            name="process_payments",
            timeout_seconds=300,
            retry_count=2,
            compensation_required=True,
        )

    @standard_exception_handler
    async def execute(self, context: SagaContext) -> dict[str, Any]:
        """Process payments for invoices"""
        invoice_generation_result = context.get_shared_data("invoice_generation_result")

        if invoice_generation_result.get("dry_run"):
            # Skip payment processing for dry runs
            return {
                "dry_run": True,
                "message": "Payment processing skipped for dry run",
                "processed_at": datetime.utcnow().isoformat(),
            }

        invoices = invoice_generation_result.get("invoices", [])

        payment_results = []
        total_processed = Decimal("0.00")
        failed_payments = []

        for invoice in invoices:
            try:
                payment_result = await self._process_invoice_payment(invoice)
                payment_results.append(payment_result)

                if payment_result["status"] == "completed":
                    total_processed += Decimal(str(payment_result["amount"]))

            except Exception as e:
                failed_payments.append(
                    {
                        "invoice_id": invoice["invoice_id"],
                        "customer_id": invoice["customer_id"],
                        "amount": invoice["total_amount"],
                        "error": str(e),
                        "failed_at": datetime.utcnow().isoformat(),
                    }
                )

        payment_processing_result = {
            "total_invoices": len(invoices),
            "successful_payments": len(
                [p for p in payment_results if p["status"] == "completed"]
            ),
            "failed_payments_count": len(failed_payments),
            "pending_payments": len(
                [p for p in payment_results if p["status"] == "pending"]
            ),
            "total_amount_processed": float(total_processed),
            "payment_results": payment_results,
            "failed_payments": failed_payments,
            "processed_at": datetime.utcnow().isoformat(),
        }

        context.set_shared_data("payment_processing_result", payment_processing_result)

        await asyncio.sleep(0.3)  # Simulate payment processing

        return payment_processing_result

    async def _process_invoice_payment(self, invoice: dict[str, Any]) -> dict[str, Any]:
        """Process payment for a single invoice"""

        # Simulate payment processing with some randomization (non-crypto)
        from secrets import SystemRandom

        _sr = SystemRandom()

        payment_methods = ["credit_card", "ach", "paypal"]
        payment_method = _sr.choice(payment_methods)

        # Simulate occasional payment failures
        success_rate = 0.85
        is_successful = _sr.random() < success_rate

        if is_successful:
            payment_result = {
                "payment_id": str(uuid4()),
                "invoice_id": invoice["invoice_id"],
                "customer_id": invoice["customer_id"],
                "amount": invoice["total_amount"],
                "payment_method": payment_method,
                "status": "completed",
                "transaction_id": f"txn_{uuid4().hex[:12]}",
                "processed_at": datetime.utcnow().isoformat(),
                "gateway_response": {"code": "00", "message": "Approved"},
            }
        else:
            payment_result = {
                "payment_id": str(uuid4()),
                "invoice_id": invoice["invoice_id"],
                "customer_id": invoice["customer_id"],
                "amount": invoice["total_amount"],
                "payment_method": payment_method,
                "status": "failed",
                "error_code": "INSUFFICIENT_FUNDS",
                "error_message": "Insufficient funds",
                "processed_at": datetime.utcnow().isoformat(),
                "gateway_response": {"code": "51", "message": "Insufficient funds"},
            }

        return payment_result

    @standard_exception_handler
    async def compensate(self, context: SagaContext) -> None:
        """Refund processed payments"""
        payment_processing_result = context.get_shared_data("payment_processing_result")

        if payment_processing_result and not payment_processing_result.get("dry_run"):
            successful_payments = [
                p
                for p in payment_processing_result.get("payment_results", [])
                if p["status"] == "completed"
            ]

            refunded_payments = []

            for payment in successful_payments:
                # Simulate refund processing
                refund = {
                    "refund_id": str(uuid4()),
                    "original_payment_id": payment["payment_id"],
                    "invoice_id": payment["invoice_id"],
                    "customer_id": payment["customer_id"],
                    "refund_amount": payment["amount"],
                    "reason": "billing_run_compensation",
                    "status": "completed",
                    "refunded_at": datetime.utcnow().isoformat(),
                }
                refunded_payments.append(refund)

            context.set_shared_data("refunded_payments", refunded_payments)

        await asyncio.sleep(0.2)  # Simulate refund processing


class SendNotificationsStep(SagaStep):
    """Step to send billing notifications to customers"""

    def __init__(self):
        super().__init__(
            name="send_notifications",
            timeout_seconds=120,
            retry_count=3,
            compensation_required=False,  # Notifications don't need compensation
        )

    @standard_exception_handler
    async def execute(self, context: SagaContext) -> dict[str, Any]:
        """Send billing notifications"""
        invoice_generation_result = context.get_shared_data("invoice_generation_result")
        payment_processing_result = context.get_shared_data("payment_processing_result")

        if invoice_generation_result.get("dry_run"):
            return {
                "dry_run": True,
                "message": "Notifications skipped for dry run",
                "processed_at": datetime.utcnow().isoformat(),
            }

        invoices = invoice_generation_result.get("invoices", [])
        payment_results = payment_processing_result.get("payment_results", [])

        # Create payment status lookup
        payment_status_map = {p["invoice_id"]: p["status"] for p in payment_results}

        notifications_sent = []
        notification_failures = []

        for invoice in invoices:
            try:
                payment_status = payment_status_map.get(
                    invoice["invoice_id"], "pending"
                )
                notification_result = await self._send_customer_notification(
                    invoice, payment_status
                )
                notifications_sent.append(notification_result)

            except Exception as e:
                notification_failures.append(
                    {
                        "invoice_id": invoice["invoice_id"],
                        "customer_id": invoice["customer_id"],
                        "error": str(e),
                        "failed_at": datetime.utcnow().isoformat(),
                    }
                )

        notification_result = {
            "total_notifications": len(invoices),
            "successful_notifications": len(notifications_sent),
            "failed_notifications": len(notification_failures),
            "notifications_sent": notifications_sent,
            "notification_failures": notification_failures,
            "sent_at": datetime.utcnow().isoformat(),
        }

        context.set_shared_data("notification_result", notification_result)

        await asyncio.sleep(0.2)  # Simulate notification sending

        return notification_result

    async def _send_customer_notification(
        self, invoice: dict[str, Any], payment_status: str
    ) -> dict[str, Any]:
        """Send notification for a single invoice"""

        if payment_status == "completed":
            notification_type = "payment_confirmation"
            subject = "Payment Confirmation - Invoice Paid"
        elif payment_status == "failed":
            notification_type = "payment_failure"
            subject = "Payment Failed - Action Required"
        else:
            notification_type = "invoice_generated"
            subject = "New Invoice Available"

        notification = {
            "notification_id": str(uuid4()),
            "customer_id": invoice["customer_id"],
            "customer_email": invoice["customer_email"],
            "notification_type": notification_type,
            "subject": subject,
            "invoice_id": invoice["invoice_id"],
            "amount": invoice["total_amount"],
            "payment_status": payment_status,
            "channels": ["email"],
            "sent_at": datetime.utcnow().isoformat(),
            "delivery_status": "sent",
        }

        return notification

    @standard_exception_handler
    async def compensate(self, context: SagaContext) -> None:
        """No compensation needed for notifications"""
        pass


class FinalizeBillingStep(SagaStep):
    """Step to finalize billing run and update records"""

    def __init__(self):
        super().__init__(
            name="finalize_billing",
            timeout_seconds=60,
            retry_count=3,
            compensation_required=True,
        )

    @standard_exception_handler
    async def execute(self, context: SagaContext) -> dict[str, Any]:
        """Finalize billing run"""
        billing_request = context.get_shared_data("billing_request")
        validation_result = context.get_shared_data("validation_result")
        invoice_generation_result = context.get_shared_data("invoice_generation_result")
        payment_processing_result = context.get_shared_data("payment_processing_result")
        notification_result = context.get_shared_data("notification_result")

        billing_period = validation_result["billing_period"]
        tenant_id = billing_request.get("tenant_id")
        is_dry_run = validation_result.get("dry_run", False)

        # Create billing run summary
        billing_run_summary = {
            "billing_run_id": str(uuid4()),
            "billing_period": billing_period,
            "tenant_id": tenant_id,
            "run_type": "dry_run" if is_dry_run else "live",
            "started_at": context.get_shared_data("operation_context", {}).get(
                "started_at"
            ),
            "completed_at": datetime.utcnow().isoformat(),
            "summary": {
                "total_customers": invoice_generation_result.get("total_customers", 0),
                "invoices_generated": invoice_generation_result.get(
                    "successful_invoices", 0
                ),
                "invoice_failures": invoice_generation_result.get("failed_invoices", 0),
                "total_invoice_amount": invoice_generation_result.get(
                    "total_amount", 0.0
                ),
                "payments_processed": payment_processing_result.get(
                    "successful_payments", 0
                )
                if payment_processing_result
                else 0,
                "payment_failures": payment_processing_result.get("failed_payments", 0)
                if payment_processing_result
                else 0,
                "total_payment_amount": payment_processing_result.get(
                    "total_amount_processed", 0.0
                )
                if payment_processing_result
                else 0.0,
                "notifications_sent": notification_result.get(
                    "successful_notifications", 0
                )
                if notification_result
                else 0,
                "notification_failures": notification_result.get(
                    "failed_notifications", 0
                )
                if notification_result
                else 0,
            },
            "status": "completed",
            "next_billing_period": self._calculate_next_billing_period(billing_period),
        }

        context.set_shared_data("billing_run_summary", billing_run_summary)

        if not is_dry_run:
            # Update billing run status in database
            await self._update_billing_run_status(billing_run_summary)

        await asyncio.sleep(0.1)  # Simulate finalization

        return billing_run_summary

    def _calculate_next_billing_period(self, current_period: str) -> str:
        """Calculate next billing period"""
        year, month = map(int, current_period.split("-"))

        if month == 12:
            next_year = year + 1
            next_month = 1
        else:
            next_year = year
            next_month = month + 1

        return f"{next_year:04d}-{next_month:02d}"

    async def _update_billing_run_status(
        self, billing_run_summary: dict[str, Any]
    ) -> None:
        """Update billing run status in database"""
        # Simulate database update
        await asyncio.sleep(0.05)

    @standard_exception_handler
    async def compensate(self, context: SagaContext) -> None:
        """Rollback billing run finalization"""
        billing_run_summary = context.get_shared_data("billing_run_summary")

        if billing_run_summary:
            # Mark billing run as failed/cancelled
            rollback_summary = {
                "billing_run_id": billing_run_summary["billing_run_id"],
                "status": "cancelled",
                "cancelled_at": datetime.utcnow().isoformat(),
                "reason": "saga_compensation",
            }

            context.set_shared_data("billing_run_rollback", rollback_summary)

        await asyncio.sleep(0.05)  # Simulate rollback


class BillingRunCompensationHandler(CompensationHandler):
    """Custom compensation handler for billing runs"""

    @standard_exception_handler
    async def compensate(
        self, context: SagaContext, failed_step: str, completed_steps: list[str]
    ) -> None:
        """Execute custom compensation logic"""

        billing_request = context.get_shared_data("billing_request")

        compensation_log = {
            "billing_period": billing_request.get("billing_period"),
            "tenant_id": billing_request.get("tenant_id"),
            "failed_step": failed_step,
            "completed_steps": completed_steps,
            "compensation_started_at": datetime.utcnow().isoformat(),
        }

        context.set_shared_data("compensation_log", compensation_log)

        # Send admin notification about billing run failure
        if "process_payments" in completed_steps:
            await self._send_admin_notification(
                context, billing_request, "payments_refunded"
            )
        elif "generate_invoices" in completed_steps:
            await self._send_admin_notification(
                context, billing_request, "invoices_cancelled"
            )
        else:
            await self._send_admin_notification(
                context, billing_request, "billing_run_failed"
            )

        context.set_shared_data("custom_compensation_completed", True)

    async def _send_admin_notification(
        self,
        context: SagaContext,
        billing_request: dict[str, Any],
        notification_type: str,
    ) -> None:
        """Send notification to administrators"""

        admin_notification = {
            "notification_id": str(uuid4()),
            "type": "billing_run_failure",
            "billing_period": billing_request.get("billing_period"),
            "tenant_id": billing_request.get("tenant_id"),
            "failure_type": notification_type,
            "sent_to": ["billing-team@company.com", "admin@company.com"],
            "sent_at": datetime.utcnow().isoformat(),
        }

        context.set_shared_data("admin_notification", admin_notification)
        await asyncio.sleep(0.05)  # Simulate notification


class BillingRunOperation(IdempotentOperation[dict[str, Any]]):
    """Idempotent billing run operation"""

    def __init__(self):
        super().__init__(
            operation_type="billing_run",
            max_attempts=2,
            timeout_seconds=900,  # 15 minutes
            ttl_seconds=86400,  # 24 hours
        )

    def validate_operation_data(self, operation_data: dict[str, Any]) -> None:
        """Validate billing run request data"""

        required_fields = ["billing_period"]

        for field in required_fields:
            if field not in operation_data:
                raise ValueError(f"Missing required field: {field}")

        # Validate billing period format
        billing_period = operation_data["billing_period"]
        if not isinstance(billing_period, str):
            raise ValueError("Billing period must be a string")

        try:
            parts = billing_period.split("-")
            if len(parts) != 2:
                raise ValueError("Invalid format")

            year = int(parts[0])
            month = int(parts[1])

            if year < 2020 or year > 2030:
                raise ValueError("Year out of range")

            if month < 1 or month > 12:
                raise ValueError("Month out of range")

        except (ValueError, TypeError) as e:
            raise ValueError("Billing period must be in YYYY-MM format") from e

        # Validate optional fields
        if "estimated_customers" in operation_data:
            estimated = operation_data["estimated_customers"]
            if not isinstance(estimated, int) or estimated < 0:
                raise ValueError("Estimated customers must be a non-negative integer")

    @standard_exception_handler
    async def execute(
        self, operation_data: dict[str, Any], context: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Execute billing run via saga orchestration"""

        context = context or {}

        # Create saga context
        saga_context = SagaContext(
            saga_id=str(uuid4()),
            tenant_id=context.get("tenant_id", "system"),
            user_id=context.get("user_id"),
            correlation_id=context.get("correlation_id", str(uuid4())),
        )

        # Store operation data
        saga_context.set_shared_data("billing_request", operation_data)
        saga_context.set_shared_data(
            "operation_context",
            {**context, "started_at": datetime.utcnow().isoformat()},
        )

        try:
            # Execute steps sequentially
            steps = [
                ValidateBillingPeriodStep(),
                GenerateInvoicesStep(),
                ProcessPaymentsStep(),
                SendNotificationsStep(),
                FinalizeBillingStep(),
            ]

            step_results = {}

            for step in steps:
                result = await step.execute(saga_context)
                step_results[step.name] = result

            # Return consolidated result
            billing_run_summary = saga_context.get_shared_data("billing_run_summary")

            return {
                "billing_run_id": billing_run_summary["billing_run_id"],
                "billing_period": operation_data["billing_period"],
                "tenant_id": operation_data.get("tenant_id"),
                "status": "completed",
                "run_type": "dry_run" if operation_data.get("dry_run") else "live",
                "completed_at": datetime.utcnow().isoformat(),
                "summary": billing_run_summary["summary"],
                "step_results": step_results,
                "saga_context": {
                    "saga_id": saga_context.saga_id,
                    "correlation_id": saga_context.correlation_id,
                },
            }

        except Exception as e:
            # Handle compensation
            error_context = ErrorContext(
                operation="billing_run",
                resource_type="billing",
                resource_id=operation_data["billing_period"],
                tenant_id=context.get("tenant_id", "system"),
                user_id=context.get("user_id"),
                correlation_id=saga_context.correlation_id,
            )

            raise BillingRunError(
                message=f"Billing run failed: {str(e)}",
                billing_period=operation_data["billing_period"],
                tenant_id=operation_data.get("tenant_id"),
                customer_count=operation_data.get("estimated_customers", 0),
                failed_customers=[],
                context=error_context,
                saga_id=saga_context.saga_id,
            ) from e


class BillingRunSaga:
    """Saga definition for billing runs"""

    @staticmethod
    def create_definition() -> SagaDefinition:
        """Create billing run saga definition"""

        definition = SagaDefinition(
            name="billing_run",
            description="Complete billing run with invoice generation, payment processing, and notifications",
            timeout_seconds=900,  # 15 minutes
            compensation_handler=BillingRunCompensationHandler(),
        )

        # Add steps in order
        definition.add_steps(
            [
                ValidateBillingPeriodStep(),
                GenerateInvoicesStep(),
                ProcessPaymentsStep(),
                SendNotificationsStep(),
                FinalizeBillingStep(),
            ]
        )

        return definition
