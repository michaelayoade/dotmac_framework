"""
Billing Process Workflow Implementation.

Provides end-to-end billing run workflow with validation, invoice generation,
payment processing, and notifications using existing billing services.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

from ..billing.core.events import SubscriptionRenewed, publish_event
from ..billing.core.services import BillingService
from .base import BusinessWorkflow, BusinessWorkflowResult


class BillingPeriodModel(BaseModel):
    """Pydantic model for billing period validation."""

    period: str = Field(..., description="Billing period in YYYY-MM format")
    start_date: date | None = None
    end_date: date | None = None

    @field_validator("period")
    @classmethod
    def validate_period_format(cls, v: str) -> str:
        """Validate billing period format."""
        parts = v.split("-")
        if len(parts) != 2:
            raise ValueError("Billing period must be in YYYY-MM format")

        try:
            year, month = int(parts[0]), int(parts[1])
            if year < 2020 or year > 2030:
                raise ValueError("Year must be between 2020 and 2030")
            if month < 1 or month > 12:
                raise ValueError("Month must be between 1 and 12")
        except ValueError as e:
            raise ValueError(f"Invalid billing period: {e}") from e

        return v

    def model_post_init(self, __context) -> None:
        """Calculate start and end dates from period."""
        year, month = map(int, self.period.split("-"))
        self.start_date = date(year, month, 1)

        if month == 12:
            self.end_date = date(year + 1, 1, 1)
        else:
            self.end_date = date(year, month + 1, 1)


class BillingRunRequest(BaseModel):
    """Pydantic model for billing run request validation."""

    billing_period: BillingPeriodModel
    tenant_id: str | None = None
    dry_run: bool = Field(default=False, description="Run in dry-run mode")
    approval_threshold: Decimal | None = Field(
        default=None,
        description="Amount threshold requiring approval"
    )
    notification_enabled: bool = Field(
        default=True,
        description="Enable customer notifications"
    )
    max_retries: int = Field(default=3, ge=0, le=10)

    model_config = {"arbitrary_types_allowed": True}


class BillingProcessWorkflow(BusinessWorkflow):
    """
    End-to-end billing process workflow.
    Orchestrates the complete billing cycle:
    1. validate_billing_period - Validate period and prerequisites
    2. generate_invoices - Create invoices for eligible customers
    3. process_payments - Attempt payment processing
    4. send_notifications - Notify customers of results
    5. finalize_billing - Update records and generate reports

    Features:
    - Approval gates for high-value billing runs
    - Rollback support with compensation
    - Integration with existing billing services
    - Comprehensive error handling and recovery
    """

    def __init__(
        self,
        billing_service: BillingService,
        billing_request: BillingRunRequest,
        workflow_id: str | None = None,
        tenant_id: str | None = None,
    ):
        """Initialize billing process workflow.
        Args:
            billing_service: Injected billing service dependency
            billing_request: Validated billing run parameters
            workflow_id: Optional workflow identifier
            tenant_id: Tenant context for multi-tenant systems
        """
        steps = [
            "validate_billing_period",
            "generate_invoices",
            "process_payments",
            "send_notifications",
            "finalize_billing",
        ]

        super().__init__(
            workflow_id=workflow_id,
            workflow_type="billing_process",
            steps=steps,
            tenant_id=tenant_id or billing_request.tenant_id,
        )

        self.billing_service = billing_service
        self.billing_request = billing_request

        # Configure workflow behavior
        self.rollback_on_failure = True
        self.continue_on_step_failure = False
        self.require_approval = billing_request.approval_threshold is not None
        self.approval_threshold = billing_request.approval_threshold

        # Workflow state
        self._eligible_subscriptions: list[Any] = []
        self._generated_invoices: list[Any] = []
        self._payment_results: list[dict[str, Any]] = []
        self._notification_results: list[dict[str, Any]] = []
        self._total_amount: Decimal = Decimal("0.00")

    async def validate_business_rules(self) -> BusinessWorkflowResult:
        """Validate business rules before workflow execution."""
        try:
            # Validate billing period is not in the future
            today = date.today()
            if self.billing_request.billing_period.end_date > today:
                return BusinessWorkflowResult(
                    success=False,
                    step_name="business_rules_validation",
                    error="future_billing_period",
                    message="Cannot run billing for future periods",
                )

            # Check if billing already completed for this period
            existing_run = await self._check_existing_billing_run()
            if existing_run and not self.billing_request.dry_run:
                return BusinessWorkflowResult(
                    success=False,
                    step_name="business_rules_validation",
                    error="billing_already_completed",
                    message=f"Billing already completed for {self.billing_request.billing_period.period}",
                )

            return BusinessWorkflowResult(
                success=True,
                step_name="business_rules_validation",
                data={"validation_passed": True},
                message="Business rules validation passed",
            )

        except Exception as e:
            return BusinessWorkflowResult(
                success=False,
                step_name="business_rules_validation",
                error=str(e),
                message=f"Business rules validation failed: {e}",
            )

    async def execute_step(self, step_name: str) -> BusinessWorkflowResult:
        """Execute individual workflow step."""
        step_handlers = {
            "validate_billing_period": self._validate_billing_period,
            "generate_invoices": self._generate_invoices,
            "process_payments": self._process_payments,
            "send_notifications": self._send_notifications,
            "finalize_billing": self._finalize_billing,
        }

        handler = step_handlers.get(step_name)
        if not handler:
            return BusinessWorkflowResult(
                success=False,
                step_name=step_name,
                error="unknown_step",
                message=f"Unknown workflow step: {step_name}",
            )

        return await handler()

    async def _validate_billing_period(self) -> BusinessWorkflowResult:
        """Validate billing period and get eligible subscriptions."""
        try:
            period = self.billing_request.billing_period

            # Get subscriptions due for billing in this period
            self._eligible_subscriptions = await self.billing_service.repository.get_due_subscriptions(
                as_of_date=period.end_date
            )

            # Filter by tenant if specified
            if self.tenant_id:
                self._eligible_subscriptions = [
                    sub for sub in self._eligible_subscriptions
                    if getattr(sub, 'tenant_id', None) == self.tenant_id
                ]

            validation_data = {
                "billing_period": period.period,
                "period_start": period.start_date.isoformat(),
                "period_end": period.end_date.isoformat(),
                "eligible_subscriptions": len(self._eligible_subscriptions),
                "tenant_id": self.tenant_id,
                "dry_run": self.billing_request.dry_run,
            }

            return BusinessWorkflowResult(
                success=True,
                step_name="validate_billing_period",
                data=validation_data,
                message=f"Found {len(self._eligible_subscriptions)} eligible subscriptions",
            )

        except Exception as e:
            return BusinessWorkflowResult(
                success=False,
                step_name="validate_billing_period",
                error=str(e),
                message=f"Billing period validation failed: {e}",
            )

    async def _generate_invoices(self) -> BusinessWorkflowResult:
        """Generate invoices for eligible subscriptions."""
        try:
            generated_invoices = []
            failed_subscriptions = []
            total_amount = Decimal("0.00")

            for subscription in self._eligible_subscriptions:
                try:
                    if not self.billing_request.dry_run:
                        invoice = await self.billing_service.generate_invoice(
                            subscription_id=subscription.id
                        )
                        generated_invoices.append(invoice)
                        total_amount += invoice.total
                    else:
                        # Dry run - simulate invoice generation
                        mock_total = Decimal("99.99")  # Mock amount
                        generated_invoices.append({
                            "id": str(uuid4()),
                            "subscription_id": subscription.id,
                            "total": mock_total,
                            "status": "draft",
                            "dry_run": True,
                        })
                        total_amount += mock_total

                except Exception as e:
                    failed_subscriptions.append({
                        "subscription_id": subscription.id,
                        "error": str(e),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

            self._generated_invoices = generated_invoices
            self._total_amount = total_amount

            result_data = {
                "total_subscriptions": len(self._eligible_subscriptions),
                "successful_invoices": len(generated_invoices),
                "failed_invoices": len(failed_subscriptions),
                "total_amount": float(total_amount),
                "failed_subscriptions": failed_subscriptions,
                "dry_run": self.billing_request.dry_run,
            }

            # Check if approval is required based on total amount
            requires_approval = (
                self.approval_threshold is not None and
                total_amount > self.approval_threshold and
                not self.billing_request.dry_run
            )

            return BusinessWorkflowResult(
                success=True,
                step_name="generate_invoices",
                data=result_data,
                message=f"Generated {len(generated_invoices)} invoices, total: ${total_amount}",
                requires_approval=requires_approval,
                approval_data={
                    "total_amount": float(total_amount),
                    "invoice_count": len(generated_invoices),
                    "threshold": float(self.approval_threshold) if self.approval_threshold else None,
                },
            )

        except Exception as e:
            return BusinessWorkflowResult(
                success=False,
                step_name="generate_invoices",
                error=str(e),
                message=f"Invoice generation failed: {e}",
            )

    async def _process_payments(self) -> BusinessWorkflowResult:
        """Process payments for generated invoices."""
        try:
            if self.billing_request.dry_run:
                return BusinessWorkflowResult(
                    success=True,
                    step_name="process_payments",
                    data={"dry_run": True, "message": "Payment processing skipped for dry run"},
                    message="Payment processing skipped for dry run",
                )

            payment_results = []
            successful_payments = 0
            failed_payments = 0
            total_processed = Decimal("0.00")

            for invoice in self._generated_invoices:
                try:
                    # Get customer's default payment method
                    customer_id = getattr(invoice, 'customer_id', None)
                    if not customer_id:
                        continue

                    payment_methods = await self.billing_service.payment_gateway.get_payment_methods(
                        str(customer_id)
                    )

                    if not payment_methods:
                        payment_results.append({
                            "invoice_id": invoice.id,
                            "status": "failed",
                            "error": "no_payment_method",
                            "message": "No payment method on file",
                        })
                        failed_payments += 1
                        continue

                    # Use first available payment method
                    payment_method = payment_methods[0]['id']

                    # Process payment with retry logic
                    payment = await self._process_invoice_payment(
                        invoice, payment_method
                    )

                    payment_results.append({
                        "invoice_id": invoice.id,
                        "payment_id": payment.id if payment else None,
                        "status": "success" if payment else "failed",
                        "amount": float(invoice.total),
                    })

                    if payment:
                        successful_payments += 1
                        total_processed += invoice.total
                    else:
                        failed_payments += 1

                except Exception as e:
                    payment_results.append({
                        "invoice_id": invoice.id,
                        "status": "failed",
                        "error": str(e),
                        "message": f"Payment processing failed: {e}",
                    })
                    failed_payments += 1

            self._payment_results = payment_results

            result_data = {
                "total_invoices": len(self._generated_invoices),
                "successful_payments": successful_payments,
                "failed_payments": failed_payments,
                "total_amount_processed": float(total_processed),
                "payment_results": payment_results,
            }

            return BusinessWorkflowResult(
                success=True,
                step_name="process_payments",
                data=result_data,
                message=f"Processed {successful_payments} payments, total: ${total_processed}",
            )

        except Exception as e:
            return BusinessWorkflowResult(
                success=False,
                step_name="process_payments",
                error=str(e),
                message=f"Payment processing failed: {e}",
            )

    async def _send_notifications(self) -> BusinessWorkflowResult:
        """Send billing notifications to customers."""
        try:
            if not self.billing_request.notification_enabled:
                return BusinessWorkflowResult(
                    success=True,
                    step_name="send_notifications",
                    data={"notifications_disabled": True},
                    message="Notifications disabled by request",
                )

            if self.billing_request.dry_run:
                return BusinessWorkflowResult(
                    success=True,
                    step_name="send_notifications",
                    data={"dry_run": True},
                    message="Notification sending skipped for dry run",
                )

            notification_results = []
            successful_notifications = 0
            failed_notifications = 0

            # Create payment status lookup
            payment_status_map = {
                result["invoice_id"]: result["status"]
                for result in self._payment_results
            }

            for invoice in self._generated_invoices:
                try:
                    # Get customer details
                    customer = await self.billing_service.repository.get_customer(
                        invoice.customer_id
                    )

                    if not customer or not getattr(customer, 'email', None):
                        continue

                    payment_status = payment_status_map.get(invoice.id, "pending")

                    # Send appropriate notification based on payment status
                    if payment_status == "success":
                        await self.billing_service.notification_service.send_payment_notification(
                            customer.email,
                            {
                                "invoice_id": str(invoice.id),
                                "amount": float(invoice.total),
                                "payment_status": payment_status,
                            }
                        )
                    elif payment_status == "failed":
                        await self.billing_service.notification_service.send_failure_notification(
                            customer.email,
                            {
                                "invoice_id": str(invoice.id),
                                "amount": float(invoice.total),
                                "error": "Payment failed - please update payment method",
                            }
                        )
                    else:
                        await self.billing_service.notification_service.send_invoice_notification(
                            customer.email,
                            {
                                "invoice_id": str(invoice.id),
                                "amount": float(invoice.total),
                                "due_date": invoice.due_date.isoformat() if hasattr(invoice, 'due_date') else None,
                            }
                        )

                    notification_results.append({
                        "invoice_id": invoice.id,
                        "customer_email": customer.email,
                        "notification_type": payment_status,
                        "status": "sent",
                    })
                    successful_notifications += 1

                except Exception as e:
                    notification_results.append({
                        "invoice_id": invoice.id,
                        "status": "failed",
                        "error": str(e),
                    })
                    failed_notifications += 1

            self._notification_results = notification_results

            result_data = {
                "total_notifications": len(self._generated_invoices),
                "successful_notifications": successful_notifications,
                "failed_notifications": failed_notifications,
                "notification_results": notification_results,
            }

            return BusinessWorkflowResult(
                success=True,
                step_name="send_notifications",
                data=result_data,
                message=f"Sent {successful_notifications} notifications",
            )

        except Exception as e:
            return BusinessWorkflowResult(
                success=False,
                step_name="send_notifications",
                error=str(e),
                message=f"Notification sending failed: {e}",
            )

    async def _finalize_billing(self) -> BusinessWorkflowResult:
        """Finalize billing run and update records."""
        try:
            # Create billing run summary
            summary = {
                "billing_run_id": self.workflow_id,
                "billing_period": self.billing_request.billing_period.period,
                "tenant_id": self.tenant_id,
                "run_type": "dry_run" if self.billing_request.dry_run else "live",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "summary": {
                    "total_subscriptions": len(self._eligible_subscriptions),
                    "invoices_generated": len(self._generated_invoices),
                    "total_invoice_amount": float(self._total_amount),
                    "successful_payments": len([
                        r for r in self._payment_results if r["status"] == "success"
                    ]),
                    "failed_payments": len([
                        r for r in self._payment_results if r["status"] == "failed"
                    ]),
                    "notifications_sent": len([
                        r for r in self._notification_results if r["status"] == "sent"
                    ]),
                },
                "status": "completed",
            }

            # Update subscription billing dates for successful invoices
            if not self.billing_request.dry_run:
                for invoice in self._generated_invoices:
                    subscription_id = getattr(invoice, 'subscription_id', None)
                    if subscription_id:
                        await self._advance_subscription_period(subscription_id)

            # Store billing run summary in business context
            self.business_context["billing_run_summary"] = summary

            return BusinessWorkflowResult(
                success=True,
                step_name="finalize_billing",
                data=summary,
                message="Billing run finalized successfully",
            )

        except Exception as e:
            return BusinessWorkflowResult(
                success=False,
                step_name="finalize_billing",
                error=str(e),
                message=f"Billing finalization failed: {e}",
            )

    async def rollback_step(self, step_name: str) -> BusinessWorkflowResult:
        """Rollback specific workflow step."""
        rollback_handlers = {
            "generate_invoices": self._rollback_invoice_generation,
            "process_payments": self._rollback_payment_processing,
            "send_notifications": self._rollback_notifications,
            "finalize_billing": self._rollback_finalization,
        }

        handler = rollback_handlers.get(step_name)
        if handler:
            return await handler()

        return BusinessWorkflowResult(
            success=True,
            step_name=f"rollback_{step_name}",
            message=f"No rollback needed for step: {step_name}",
        )

    async def _rollback_invoice_generation(self) -> BusinessWorkflowResult:
        """Rollback invoice generation by canceling generated invoices."""
        try:
            if self.billing_request.dry_run:
                return BusinessWorkflowResult(
                    success=True,
                    step_name="rollback_generate_invoices",
                    message="No rollback needed for dry run",
                )

            cancelled_count = 0
            for invoice in self._generated_invoices:
                try:
                    from ..billing.core.models import InvoiceStatus
                    await self.billing_service.repository.update_invoice_status(
                        invoice.id, InvoiceStatus.CANCELLED
                    )
                    cancelled_count += 1
                except Exception:
                    pass  # Continue with other invoices

            return BusinessWorkflowResult(
                success=True,
                step_name="rollback_generate_invoices",
                data={"cancelled_invoices": cancelled_count},
                message=f"Cancelled {cancelled_count} invoices",
            )

        except Exception as e:
            return BusinessWorkflowResult(
                success=False,
                step_name="rollback_generate_invoices",
                error=str(e),
                message=f"Invoice rollback failed: {e}",
            )

    async def _rollback_payment_processing(self) -> BusinessWorkflowResult:
        """Rollback payment processing by refunding successful payments."""
        try:
            if self.billing_request.dry_run:
                return BusinessWorkflowResult(
                    success=True,
                    step_name="rollback_process_payments",
                    message="No rollback needed for dry run",
                )

            refunded_count = 0
            successful_payments = [
                r for r in self._payment_results if r["status"] == "success"
            ]

            for payment_result in successful_payments:
                try:
                    await self.billing_service.payment_gateway.refund(
                        payment_result["payment_id"],
                        reason="billing_run_rollback"
                    )
                    refunded_count += 1
                except Exception:
                    pass  # Continue with other refunds

            return BusinessWorkflowResult(
                success=True,
                step_name="rollback_process_payments",
                data={"refunded_payments": refunded_count},
                message=f"Refunded {refunded_count} payments",
            )

        except Exception as e:
            return BusinessWorkflowResult(
                success=False,
                step_name="rollback_process_payments",
                error=str(e),
                message=f"Payment rollback failed: {e}",
            )

    async def _rollback_notifications(self) -> BusinessWorkflowResult:
        """Rollback notifications (no action needed - notifications can't be unsent)."""
        return BusinessWorkflowResult(
            success=True,
            step_name="rollback_send_notifications",
            message="Notifications cannot be rolled back",
        )

    async def _rollback_finalization(self) -> BusinessWorkflowResult:
        """Rollback finalization by marking billing run as cancelled."""
        try:
            if "billing_run_summary" in self.business_context:
                self.business_context["billing_run_summary"]["status"] = "cancelled"
                self.business_context["billing_run_summary"]["cancelled_at"] = (
                    datetime.now(timezone.utc).isoformat()
                )

            return BusinessWorkflowResult(
                success=True,
                step_name="rollback_finalize_billing",
                message="Billing run marked as cancelled",
            )

        except Exception as e:
            return BusinessWorkflowResult(
                success=False,
                step_name="rollback_finalize_billing",
                error=str(e),
                message=f"Finalization rollback failed: {e}",
            )

    async def _check_existing_billing_run(self) -> dict[str, Any] | None:
        """Check if billing run already exists for this period."""
        # Implementation would query billing run history
        # For now, return None (no existing run)
        return None

    async def _process_invoice_payment(
        self, invoice: Any, payment_method_id: str
    ) -> Any | None:
        """Process payment for a single invoice with retry logic."""
        max_retries = self.billing_request.max_retries

        for attempt in range(max_retries):
            try:
                payment = await self.billing_service.process_payment(
                    invoice_id=invoice.id,
                    payment_method_id=payment_method_id,
                    amount=invoice.total,
                )
                return payment

            except Exception as e:
                if attempt < max_retries - 1:
                    # Wait before retry (exponential backoff)
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    # Final attempt failed
                    raise e

        return None

    async def _advance_subscription_period(self, subscription_id: UUID) -> None:
        """Advance subscription to next billing period."""
        try:
            subscription = await self.billing_service.repository.get_subscription(
                subscription_id
            )

            if subscription:
                # Calculate next billing period
                from dateutil.relativedelta import relativedelta

                current_end = subscription.current_period_end
                next_start = current_end
                next_end = current_end + relativedelta(months=1)  # Assume monthly billing

                # Update subscription
                await self.billing_service.repository.update_subscription(
                    subscription_id,
                    {
                        "current_period_start": next_start,
                        "current_period_end": next_end,
                        "next_billing_date": next_end,
                    }
                )

                # Emit renewal event
                await publish_event(SubscriptionRenewed(
                    event_id=uuid4(),
                    occurred_at=datetime.now(timezone.utc),
                    subscription_id=subscription_id,
                    customer_id=subscription.customer_id,
                    previous_period_end=current_end,
                    new_period_end=next_end,
                    amount=subscription.billing_plan.monthly_price,
                ))

        except Exception:
            # Log error but don't fail the workflow
            pass
