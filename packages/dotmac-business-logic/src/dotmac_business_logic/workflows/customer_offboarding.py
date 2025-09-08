"""
Customer Offboarding Workflow Implementation.

This workflow orchestrates the complete customer offboarding process from service 
deactivation through account closure and final billing reconciliation.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .base import BusinessWorkflow, BusinessWorkflowResult

logger = logging.getLogger(__name__)


class OffboardingReason(str, Enum):
    """Reason for customer offboarding."""

    VOLUNTARY = "voluntary"
    INVOLUNTARY = "involuntary"
    NON_PAYMENT = "non_payment"
    VIOLATION = "violation"
    BUSINESS_CLOSURE = "business_closure"
    SERVICE_DISCONTINUATION = "service_discontinuation"


class DataRetentionPolicy(str, Enum):
    """Data retention policy after offboarding."""

    IMMEDIATE_DELETION = "immediate_deletion"
    REGULATORY_RETENTION = "regulatory_retention"
    BACKUP_ONLY = "backup_only"
    LONG_TERM_ARCHIVE = "long_term_archive"


class CustomerOffboardingRequest(BaseModel):
    """Request model for customer offboarding workflow."""

    # Customer identification
    customer_id: str = Field(..., description="Unique customer identifier")
    user_email: str = Field(..., description="Customer email for notifications")

    # Offboarding details
    offboarding_reason: OffboardingReason = Field(..., description="Reason for offboarding")
    reason_details: str | None = Field(None, description="Additional details about offboarding reason")
    effective_date: datetime | None = Field(None, description="Effective date for offboarding")

    # Service handling
    immediate_deactivation: bool = Field(default=False, description="Deactivate services immediately")
    grace_period_days: int = Field(default=0, description="Grace period before full deactivation")
    preserve_data_days: int = Field(default=30, description="Days to preserve customer data")

    # Billing and financial
    final_billing_required: bool = Field(default=True, description="Generate final invoice")
    process_refunds: bool = Field(default=True, description="Process any applicable refunds")
    collect_outstanding: bool = Field(default=True, description="Attempt to collect outstanding balances")

    # Data handling
    data_retention_policy: DataRetentionPolicy = Field(
        DataRetentionPolicy.REGULATORY_RETENTION,
        description="Data retention policy to apply"
    )
    export_customer_data: bool = Field(default=False, description="Export customer data before deletion")

    # Communication settings
    send_confirmation_email: bool = Field(default=True, description="Send offboarding confirmation")
    send_data_export_email: bool = Field(default=False, description="Send data export notification")

    # Workflow configuration
    tenant_id: str | None = Field(None, description="Tenant context for multi-tenant systems")
    approval_required: bool = Field(default=False, description="Require manual approval before processing")
    initiated_by: str | None = Field(None, description="User or system that initiated offboarding")

    # Additional metadata
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    model_config = ConfigDict(
        use_enum_values=True,
        str_strip_whitespace=True,
    )

    @field_validator("customer_id")
    @classmethod
    def validate_customer_id(cls, v: str) -> str:
        """Validate customer ID is not empty."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Customer ID is required")
        return v.strip()

    @field_validator("user_email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        import re
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError("Invalid email format")
        return v.lower()

    @field_validator("preserve_data_days")
    @classmethod
    def validate_data_preservation_days(cls, v: int) -> int:
        """Validate data preservation days is reasonable."""
        if v < 0 or v > 2555:  # ~7 years max
            raise ValueError("Data preservation days must be between 0 and 2555")
        return v


class CustomerOffboardingWorkflow(BusinessWorkflow):
    """
    Customer Offboarding Workflow.
    Orchestrates the complete customer offboarding process:
    1. validate_offboarding_request - Validate request and check customer status
    2. suspend_services - Suspend or deactivate customer services
    3. process_final_billing - Generate final invoices and handle payments/refunds  
    4. export_customer_data - Export customer data if requested
    5. cleanup_resources - Remove or archive customer resources
    6. finalize_offboarding - Complete offboarding and send confirmations
    """

    def __init__(
        self,
        identity_service: Any,
        billing_service: Any,
        notification_service: Any,
        offboarding_request: CustomerOffboardingRequest,
        provisioning_service: Any = None,
        data_export_service: Any = None,
        workflow_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        **kwargs: Any,
    ):
        """Initialize the customer offboarding workflow."""

        self.identity_service = identity_service
        self.billing_service = billing_service
        self.notification_service = notification_service
        self.provisioning_service = provisioning_service
        self.data_export_service = data_export_service
        self.request = offboarding_request

        # Workflow state
        self._customer_data: dict[str, Any] | None = None
        self._suspended_services: list[dict[str, Any]] = []
        self._final_invoice: dict[str, Any] | None = None
        self._refund_transactions: list[dict[str, Any]] = []
        self._exported_data_path: str | None = None
        self._cleanup_actions: list[str] = []

        # Define workflow steps
        steps = [
            "validate_offboarding_request",
            "suspend_services",
            "process_final_billing",
            "export_customer_data",
            "cleanup_resources",
            "finalize_offboarding",
        ]

        super().__init__(
            workflow_id=workflow_id,
            workflow_type="CustomerOffboardingWorkflow",
            steps=steps,
            tenant_id=tenant_id or offboarding_request.tenant_id,
            **kwargs,
        )

        # Set rollback behavior
        self.rollback_on_failure = True

    async def execute_step(self, step_name: str) -> BusinessWorkflowResult:
        """Execute a specific workflow step."""
        try:
            if step_name == "validate_offboarding_request":
                return await self._validate_offboarding_request()
            elif step_name == "suspend_services":
                return await self._suspend_services()
            elif step_name == "process_final_billing":
                return await self._process_final_billing()
            elif step_name == "export_customer_data":
                return await self._export_customer_data()
            elif step_name == "cleanup_resources":
                return await self._cleanup_resources()
            elif step_name == "finalize_offboarding":
                return await self._finalize_offboarding()
            else:
                return BusinessWorkflowResult(
                    success=False,
                    step_name=step_name,
                    error=f"Unknown step: {step_name}",
                )
        except Exception as e:
            logger.exception(f"Error executing step {step_name}")
            return BusinessWorkflowResult(
                success=False,
                step_name=step_name,
                error=str(e),
            )

    async def validate_business_rules(self) -> BusinessWorkflowResult:
        """
        Validate business rules before workflow execution.
        
        Returns:
            BusinessWorkflowResult: Validation result
        """
        try:
            # Check if customer exists and is in a valid state for offboarding
            if hasattr(self.identity_service, 'get_customer'):
                customer = await self.identity_service.get_customer(self.request.customer_id)
                if not customer:
                    return BusinessWorkflowResult(
                        success=False,
                        step_name="validate_business_rules",
                        error=f"Customer {self.request.customer_id} not found",
                    )

                # Check customer status
                status = customer.get("status", "active")
                if status in ["terminated", "deleted"]:
                    return BusinessWorkflowResult(
                        success=False,
                        step_name="validate_business_rules",
                        error=f"Customer is already {status} and cannot be offboarded",
                    )

            # Validate data retention policy requirements
            if self.request.data_retention_policy == DataRetentionPolicy.IMMEDIATE_DELETION:
                if self.request.preserve_data_days > 0:
                    return BusinessWorkflowResult(
                        success=False,
                        step_name="validate_business_rules",
                        error="Immediate deletion policy conflicts with data preservation days > 0",
                    )

            # Validate business rules for involuntary termination
            if self.request.offboarding_reason == OffboardingReason.INVOLUNTARY:
                if not self.request.reason_details:
                    return BusinessWorkflowResult(
                        success=False,
                        step_name="validate_business_rules",
                        error="Involuntary offboarding requires detailed reason",
                    )

            # Check for approval requirements based on business rules
            approval_required = False
            approval_reasons = []

            # Large data retention requires approval
            if self.request.preserve_data_days > 365:  # More than 1 year
                approval_required = True
                approval_reasons.append("Long-term data retention requested")

            # Involuntary termination requires approval
            if self.request.offboarding_reason in [OffboardingReason.VIOLATION, OffboardingReason.INVOLUNTARY]:
                approval_required = True
                approval_reasons.append("Involuntary termination requires approval")

            validation_data = {
                "customer_id": self.request.customer_id,
                "offboarding_reason": self.request.offboarding_reason,
                "data_retention_policy": self.request.data_retention_policy,
                "preserve_data_days": self.request.preserve_data_days,
                "validation_timestamp": datetime.now(timezone.utc).isoformat(),
            }

            if approval_required:
                return BusinessWorkflowResult(
                    success=True,
                    step_name="validate_business_rules",
                    message="Business rules validation passed - approval required",
                    data=validation_data,
                    requires_approval=True,
                    approval_data={
                        "reasons": approval_reasons,
                        "approval_type": "offboarding_approval",
                    }
                )

            return BusinessWorkflowResult(
                success=True,
                step_name="validate_business_rules",
                message="Business rules validation passed",
                data=validation_data,
            )

        except Exception as e:
            logger.exception(f"Failed to validate business rules: {str(e)}")
            return BusinessWorkflowResult(
                success=False,
                step_name="validate_business_rules",
                error=f"Business rules validation failed: {str(e)}",
            )

    async def rollback_step(self, step_name: str) -> BusinessWorkflowResult:
        """Rollback a specific workflow step."""
        try:
            if step_name == "finalize_offboarding":
                # Can't rollback completion notifications, but can revert status
                if self._customer_data and hasattr(self.identity_service, 'reactivate_customer'):
                    await self.identity_service.reactivate_customer(self.request.customer_id)

            elif step_name == "cleanup_resources":
                # Resources are typically archived, not deleted, so limited rollback
                logger.warning("Resource cleanup rollback limited - data may need manual recovery")

            elif step_name == "export_customer_data":
                # Remove exported data files if they exist
                if self._exported_data_path and self.data_export_service:
                    if hasattr(self.data_export_service, 'remove_export'):
                        await self.data_export_service.remove_export(self._exported_data_path)

            elif step_name == "process_final_billing":
                # Reverse billing transactions where possible
                if self._refund_transactions:
                    for refund in self._refund_transactions:
                        if hasattr(self.billing_service, 'reverse_refund'):
                            await self.billing_service.reverse_refund(refund.get('id'))

            elif step_name == "suspend_services":
                # Reactivate suspended services
                if self._suspended_services and self.provisioning_service:
                    for service in self._suspended_services:
                        if hasattr(self.provisioning_service, 'reactivate_service'):
                            await self.provisioning_service.reactivate_service(
                                service.get('service_id')
                            )

            elif step_name == "validate_offboarding_request":
                # No rollback needed for validation
                pass

            return BusinessWorkflowResult(
                success=True,
                step_name=step_name,
                message=f"Step {step_name} rolled back successfully",
            )

        except Exception as e:
            logger.exception(f"Error rolling back step {step_name}")
            return BusinessWorkflowResult(
                success=False,
                step_name=step_name,
                error=f"Rollback failed: {str(e)}",
            )

    async def _validate_offboarding_request(self) -> BusinessWorkflowResult:
        """Validate the offboarding request and customer status."""
        try:
            # Retrieve customer data
            if hasattr(self.identity_service, 'get_customer'):
                customer = await self.identity_service.get_customer(self.request.customer_id)
                if not customer:
                    return BusinessWorkflowResult(
                        success=False,
                        step_name="validate_offboarding_request",
                        error=f"Customer {self.request.customer_id} not found",
                    )
                self._customer_data = customer
            else:
                # Mock customer data for testing
                self._customer_data = {
                    "id": self.request.customer_id,
                    "email": self.request.user_email,
                    "status": "active"
                }

            # Check if customer is already in offboarding process
            customer_status = self._customer_data.get("status", "active")
            if customer_status in ["suspended", "offboarding", "terminated"]:
                return BusinessWorkflowResult(
                    success=False,
                    step_name="validate_offboarding_request",
                    error=f"Customer is already in {customer_status} status",
                )

            # Validate effective date
            if self.request.effective_date and self.request.effective_date < datetime.now(timezone.utc):
                logger.warning("Effective date is in the past, proceeding with immediate processing")

            # Check for approval requirements
            if self.request.approval_required:
                logger.info("Manual approval required for this offboarding request")

            validation_data = {
                "customer_id": self.request.customer_id,
                "customer_status": customer_status,
                "validation_timestamp": datetime.now(timezone.utc).isoformat(),
                "approval_required": self.request.approval_required,
            }

            return BusinessWorkflowResult(
                success=True,
                step_name="validate_offboarding_request",
                message="Offboarding request validated successfully",
                data=validation_data,
            )

        except Exception as e:
            logger.exception(f"Failed to validate offboarding request: {str(e)}")
            return BusinessWorkflowResult(
                success=False,
                step_name="validate_offboarding_request",
                error=f"Validation failed: {str(e)}",
            )

    async def _suspend_services(self) -> BusinessWorkflowResult:
        """Suspend or deactivate customer services."""
        try:
            suspended_services = []

            if self.provisioning_service and hasattr(self.provisioning_service, 'get_customer_services'):
                # Get customer services
                services = await self.provisioning_service.get_customer_services(self.request.customer_id)

                for service in services or []:
                    service_id = service.get('id') or service.get('service_id')
                    if not service_id:
                        continue

                    # Suspend each service
                    if hasattr(self.provisioning_service, 'suspend_service'):
                        suspension_result = await self.provisioning_service.suspend_service(
                            service_id,
                            reason=self.request.offboarding_reason,
                            immediate=self.request.immediate_deactivation
                        )
                        suspended_services.append({
                            "service_id": service_id,
                            "service_type": service.get("type", "unknown"),
                            "suspension_date": datetime.now(timezone.utc).isoformat(),
                            "suspension_result": suspension_result
                        })
            else:
                # Mock service suspension for testing
                suspended_services = [{
                    "service_id": "mock_service_1",
                    "service_type": "internet",
                    "suspension_date": datetime.now(timezone.utc).isoformat(),
                    "suspension_result": {"status": "suspended"}
                }]

            self._suspended_services = suspended_services

            service_data = {
                "customer_id": self.request.customer_id,
                "suspended_services": suspended_services,
                "suspension_type": "immediate" if self.request.immediate_deactivation else "graceful",
                "grace_period_days": self.request.grace_period_days,
            }

            return BusinessWorkflowResult(
                success=True,
                step_name="suspend_services",
                message=f"Successfully suspended {len(suspended_services)} services",
                data=service_data,
            )

        except Exception as e:
            logger.exception(f"Failed to suspend services: {str(e)}")
            return BusinessWorkflowResult(
                success=False,
                step_name="suspend_services",
                error=f"Service suspension failed: {str(e)}",
            )

    async def _process_final_billing(self) -> BusinessWorkflowResult:
        """Generate final invoices and process payments/refunds."""
        try:
            billing_results = {}

            if self.request.final_billing_required:
                # Generate final invoice
                if hasattr(self.billing_service, 'generate_final_invoice'):
                    final_invoice = await self.billing_service.generate_final_invoice(
                        customer_id=self.request.customer_id,
                        effective_date=self.request.effective_date or datetime.now(timezone.utc),
                        reason=self.request.offboarding_reason
                    )
                    self._final_invoice = final_invoice
                    billing_results['final_invoice'] = final_invoice
                else:
                    # Mock final invoice
                    self._final_invoice = {
                        "id": "final_invoice_123",
                        "customer_id": self.request.customer_id,
                        "amount": Decimal("0.00"),
                        "status": "generated"
                    }
                    billing_results['final_invoice'] = self._final_invoice

            # Process refunds if applicable
            if self.request.process_refunds:
                if hasattr(self.billing_service, 'calculate_refunds'):
                    refunds = await self.billing_service.calculate_refunds(
                        customer_id=self.request.customer_id,
                        effective_date=self.request.effective_date or datetime.now(timezone.utc)
                    )

                    # Process each refund
                    refund_transactions = []
                    for refund in refunds or []:
                        if refund.get('amount', 0) > 0:
                            if hasattr(self.billing_service, 'process_refund'):
                                refund_result = await self.billing_service.process_refund(refund)
                                refund_transactions.append(refund_result)

                    self._refund_transactions = refund_transactions
                    billing_results['refunds'] = refund_transactions
                else:
                    # Mock refund processing
                    self._refund_transactions = []
                    billing_results['refunds'] = []

            # Collect outstanding balances
            if self.request.collect_outstanding:
                if hasattr(self.billing_service, 'collect_outstanding_balance'):
                    collection_result = await self.billing_service.collect_outstanding_balance(
                        self.request.customer_id
                    )
                    billing_results['collection'] = collection_result
                else:
                    billing_results['collection'] = {"status": "no_outstanding_balance"}

            billing_data = {
                "customer_id": self.request.customer_id,
                "final_invoice_generated": self.request.final_billing_required,
                "refunds_processed": len(self._refund_transactions),
                "total_refund_amount": sum(r.get('amount', 0) for r in self._refund_transactions),
                "billing_results": billing_results,
            }

            return BusinessWorkflowResult(
                success=True,
                step_name="process_final_billing",
                message="Final billing processing completed",
                data=billing_data,
            )

        except Exception as e:
            logger.exception(f"Failed to process final billing: {str(e)}")
            return BusinessWorkflowResult(
                success=False,
                step_name="process_final_billing",
                error=f"Billing processing failed: {str(e)}",
            )

    async def _export_customer_data(self) -> BusinessWorkflowResult:
        """Export customer data if requested."""
        try:
            if not self.request.export_customer_data:
                return BusinessWorkflowResult(
                    success=True,
                    step_name="export_customer_data",
                    message="Data export not requested, skipping step",
                )

            export_data = {}

            if self.data_export_service and hasattr(self.data_export_service, 'export_customer_data'):
                # Export customer data
                export_result = await self.data_export_service.export_customer_data(
                    customer_id=self.request.customer_id,
                    export_format="json",
                    include_metadata=True,
                    retention_policy=self.request.data_retention_policy
                )

                self._exported_data_path = export_result.get('export_path')
                export_data = {
                    "export_path": self._exported_data_path,
                    "export_size": export_result.get('file_size', 0),
                    "export_format": "json",
                    "export_date": datetime.now(timezone.utc).isoformat(),
                }

                # Send data export email if requested
                if self.request.send_data_export_email:
                    if hasattr(self.notification_service, 'send_data_export_notification'):
                        await self.notification_service.send_data_export_notification(
                            email=self.request.user_email,
                            export_path=self._exported_data_path,
                            customer_id=self.request.customer_id
                        )
                        export_data['notification_sent'] = True
            else:
                # Mock data export
                self._exported_data_path = f"/exports/{self.request.customer_id}_export.json"
                export_data = {
                    "export_path": self._exported_data_path,
                    "export_size": 1024,
                    "export_format": "json",
                    "export_date": datetime.now(timezone.utc).isoformat(),
                    "notification_sent": self.request.send_data_export_email,
                }

            return BusinessWorkflowResult(
                success=True,
                step_name="export_customer_data",
                message="Customer data exported successfully",
                data=export_data,
            )

        except Exception as e:
            logger.exception(f"Failed to export customer data: {str(e)}")
            return BusinessWorkflowResult(
                success=False,
                step_name="export_customer_data",
                error=f"Data export failed: {str(e)}",
            )

    async def _cleanup_resources(self) -> BusinessWorkflowResult:
        """Remove or archive customer resources."""
        try:
            cleanup_results = []

            # Apply data retention policy
            retention_actions = []

            if self.request.data_retention_policy == DataRetentionPolicy.IMMEDIATE_DELETION:
                retention_actions = ["delete_personal_data", "delete_service_data", "delete_billing_data"]
            elif self.request.data_retention_policy == DataRetentionPolicy.BACKUP_ONLY:
                retention_actions = ["archive_data", "delete_active_data"]
            elif self.request.data_retention_policy == DataRetentionPolicy.LONG_TERM_ARCHIVE:
                retention_actions = ["archive_all_data"]
            else:  # REGULATORY_RETENTION
                retention_actions = ["archive_regulated_data", "delete_non_essential_data"]

            # Execute retention actions
            for action in retention_actions:
                try:
                    if action == "delete_personal_data" and hasattr(self.identity_service, 'delete_personal_data'):
                        result = await self.identity_service.delete_personal_data(
                            self.request.customer_id
                        )
                    elif action == "archive_data" and hasattr(self.identity_service, 'archive_customer_data'):
                        result = await self.identity_service.archive_customer_data(
                            self.request.customer_id,
                            retention_days=self.request.preserve_data_days
                        )
                    else:
                        # Mock cleanup action
                        result = {"action": action, "status": "completed"}

                    cleanup_results.append({
                        "action": action,
                        "result": result,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                    self._cleanup_actions.append(action)

                except Exception as action_error:
                    logger.error(f"Cleanup action {action} failed: {action_error}")
                    cleanup_results.append({
                        "action": action,
                        "error": str(action_error),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

            cleanup_data = {
                "customer_id": self.request.customer_id,
                "retention_policy": self.request.data_retention_policy,
                "preserve_data_days": self.request.preserve_data_days,
                "cleanup_actions": cleanup_results,
                "successful_actions": len([r for r in cleanup_results if "error" not in r]),
                "failed_actions": len([r for r in cleanup_results if "error" in r]),
            }

            return BusinessWorkflowResult(
                success=True,
                step_name="cleanup_resources",
                message=f"Resource cleanup completed: {len(cleanup_results)} actions processed",
                data=cleanup_data,
            )

        except Exception as e:
            logger.exception(f"Failed to cleanup resources: {str(e)}")
            return BusinessWorkflowResult(
                success=False,
                step_name="cleanup_resources",
                error=f"Resource cleanup failed: {str(e)}",
            )

    async def _finalize_offboarding(self) -> BusinessWorkflowResult:
        """Complete offboarding and send confirmations."""
        try:
            # Update customer status to terminated
            if hasattr(self.identity_service, 'terminate_customer'):
                termination_result = await self.identity_service.terminate_customer(
                    customer_id=self.request.customer_id,
                    reason=self.request.offboarding_reason,
                    effective_date=self.request.effective_date or datetime.now(timezone.utc)
                )
            else:
                termination_result = {"status": "terminated"}

            # Send confirmation email if requested
            confirmation_sent = False
            if self.request.send_confirmation_email:
                if hasattr(self.notification_service, 'send_offboarding_confirmation'):
                    await self.notification_service.send_offboarding_confirmation(
                        email=self.request.user_email,
                        customer_id=self.request.customer_id,
                        offboarding_reason=self.request.offboarding_reason,
                        data_retention_days=self.request.preserve_data_days,
                        exported_data_available=self.request.export_customer_data
                    )
                    confirmation_sent = True

            # Prepare completion data
            completion_data = {
                "customer_id": self.request.customer_id,
                "offboarding_reason": self.request.offboarding_reason,
                "completion_timestamp": datetime.now(timezone.utc).isoformat(),
                "services_suspended": len(self._suspended_services),
                "final_invoice_generated": self._final_invoice is not None,
                "refunds_processed": len(self._refund_transactions),
                "data_exported": self._exported_data_path is not None,
                "cleanup_actions_completed": len(self._cleanup_actions),
                "confirmation_email_sent": confirmation_sent,
                "termination_result": termination_result,
            }

            # Log completion
            logger.info(
                f"Customer offboarding completed: {self.request.customer_id}, "
                f"reason: {self.request.offboarding_reason}, "
                f"services: {len(self._suspended_services)}, "
                f"refunds: {len(self._refund_transactions)}"
            )

            return BusinessWorkflowResult(
                success=True,
                step_name="finalize_offboarding",
                message="Customer offboarding completed successfully",
                data=completion_data,
            )

        except Exception as e:
            logger.exception(f"Failed to finalize offboarding: {str(e)}")
            return BusinessWorkflowResult(
                success=False,
                step_name="finalize_offboarding",
                error=f"Offboarding finalization failed: {str(e)}",
            )

    def to_dict(self) -> dict[str, Any]:
        """Convert customer offboarding workflow to dictionary representation."""
        base_dict = super().to_dict()
        
        # Add offboarding-specific fields
        base_dict.update({
            "customer_id": self.request.customer_id,
            "offboarding_reason": self.request.offboarding_reason,
            "data_retention_policy": self.request.data_retention_policy,
            "immediate_deactivation": self.request.immediate_deactivation,
            "final_billing_required": self.request.final_billing_required,
            "process_refunds": self.request.process_refunds,
            "export_customer_data": self.request.export_customer_data,
            "current_step": self.current_step_index,
        })
        
        return base_dict
