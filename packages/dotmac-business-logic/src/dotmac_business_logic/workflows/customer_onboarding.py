"""
Customer Onboarding Workflow Implementation.

This workflow orchestrates the complete customer onboarding process from initial
registration through service activation and first billing setup.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .base import BusinessWorkflow, BusinessWorkflowResult

logger = logging.getLogger(__name__)


class CustomerType(str, Enum):
    """Customer type classification."""

    RESIDENTIAL = "residential"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


class OnboardingChannel(str, Enum):
    """Channel through which customer was onboarded."""

    DIRECT = "direct"
    RESELLER = "reseller"
    REFERRAL = "referral"
    MARKETING = "marketing"


class CustomerOnboardingRequest(BaseModel):
    """Request model for customer onboarding workflow."""

    # Customer basic information
    email: str = Field(..., description="Customer email address")
    first_name: str = Field(..., description="Customer first name")
    last_name: str = Field(..., description="Customer last name")
    phone: str | None = Field(None, description="Customer phone number")

    # Business information (for business customers)
    company_name: str | None = Field(None, description="Company name for business customers")
    tax_id: str | None = Field(None, description="Tax ID for business customers")

    # Address information
    address_line1: str = Field(..., description="Primary address line")
    address_line2: str | None = Field(None, description="Secondary address line")
    city: str = Field(..., description="City")
    state: str = Field(..., description="State or province")
    postal_code: str = Field(..., description="Postal/ZIP code")
    country: str = Field(default="US", description="Country code")

    # Service configuration
    customer_type: CustomerType = Field(CustomerType.RESIDENTIAL, description="Customer type")
    onboarding_channel: OnboardingChannel = Field(OnboardingChannel.DIRECT, description="Onboarding channel")
    plan_id: str | None = Field(None, description="Selected service plan ID")

    # Workflow configuration
    tenant_id: str | None = Field(None, description="Tenant context for multi-tenant systems")
    auto_activate: bool = Field(default=False, description="Automatically activate after setup")
    send_welcome_email: bool = Field(default=True, description="Send welcome email to customer")
    require_payment_method: bool = Field(default=True, description="Require payment method during onboarding")

    # Approval settings
    approval_required: bool = Field(default=False, description="Require manual approval")
    approval_threshold: Decimal | None = Field(None, description="Auto-approval threshold for account value")

    # Additional metadata
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    model_config = ConfigDict(
        use_enum_values=True,
        str_strip_whitespace=True,
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        import re
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError("Invalid email format")
        return v.lower()

    @field_validator("postal_code")
    @classmethod
    def validate_postal_code(cls, v: str) -> str:
        """Validate postal code format."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Postal code is required")
        return v.strip()


class CustomerOnboardingWorkflow(BusinessWorkflow):
    """
    Customer Onboarding Workflow.

    Orchestrates the complete customer onboarding process:
    1. validate_customer_data - Validate and sanitize customer information
    2. create_customer_account - Create customer account and user credentials
    3. setup_billing_profile - Configure billing information and payment methods
    4. provision_services - Provision requested services and resources
    5. send_welcome_communications - Send welcome materials and account details
    6. finalize_onboarding - Complete onboarding and activate account
    """

    def __init__(
        self,
        identity_service: Any,
        billing_service: Any,
        notification_service: Any,
        onboarding_request: CustomerOnboardingRequest,
        provisioning_service: Any = None,
        workflow_id: Optional[str] = None,
    ):
        """Initialize customer onboarding workflow."""
        steps = [
            "validate_customer_data",
            "create_customer_account",
            "setup_billing_profile",
            "provision_services",
            "send_welcome_communications",
            "finalize_onboarding",
        ]

        super().__init__(
            workflow_id=workflow_id,
            workflow_type="customer_onboarding",
            steps=steps,
            tenant_id=onboarding_request.tenant_id,
        )

        # Services
        self.identity_service = identity_service
        self.billing_service = billing_service
        self.notification_service = notification_service
        self.provisioning_service = provisioning_service

        # Request data
        self.onboarding_request = onboarding_request

        # Workflow state
        self._customer_id: Optional[UUID] = None
        self._user_id: Optional[UUID] = None
        self._billing_profile_id: Optional[UUID] = None
        self._provisioned_resources: list[dict[str, Any]] = []

        # Configure workflow behavior
        self.require_approval = onboarding_request.approval_required
        self.approval_threshold = onboarding_request.approval_threshold

        # Set rollback behavior
        self.rollback_on_failure = True
        self.continue_on_step_failure = False

    async def validate_business_rules(self) -> BusinessWorkflowResult:
        """Validate business rules for customer onboarding."""
        try:
            validation_errors = []

            # Validate customer data completeness
            if not self.onboarding_request.email:
                validation_errors.append("Customer email is required")

            if not self.onboarding_request.first_name:
                validation_errors.append("Customer first name is required")

            if not self.onboarding_request.last_name:
                validation_errors.append("Customer last name is required")

            # Validate business customer requirements
            if self.onboarding_request.customer_type == CustomerType.BUSINESS:
                if not self.onboarding_request.company_name:
                    validation_errors.append("Company name is required for business customers")

            # Validate address information
            required_address_fields = ["address_line1", "city", "state", "postal_code"]
            for field in required_address_fields:
                if not getattr(self.onboarding_request, field, None):
                    validation_errors.append(f"Address field '{field}' is required")

            # Check for duplicate customer
            if hasattr(self.identity_service, 'get_customer_by_email'):
                existing_customer = await self._check_existing_customer()
                if existing_customer:
                    validation_errors.append(f"Customer with email {self.onboarding_request.email} already exists")

            if validation_errors:
                return BusinessWorkflowResult(
                    success=False,
                    step_name="business_rules_validation",
                    error="Validation errors: " + "; ".join(validation_errors),
                    data={"validation_errors": validation_errors},
                )

            return BusinessWorkflowResult(
                success=True,
                step_name="business_rules_validation",
                message="Business rules validation passed",
                data={
                    "customer_type": self.onboarding_request.customer_type,
                    "onboarding_channel": self.onboarding_request.onboarding_channel,
                    "tenant_id": self.onboarding_request.tenant_id,
                },
            )

        except Exception as e:
            logger.error(f"Business rules validation failed: {str(e)}")
            return BusinessWorkflowResult(
                success=False,
                step_name="business_rules_validation",
                error=f"Validation error: {str(e)}",
            )

    async def execute_step(self, step_name: str) -> BusinessWorkflowResult:
        """Execute a specific onboarding step."""
        try:
            if step_name == "validate_customer_data":
                return await self._validate_customer_data()
            elif step_name == "create_customer_account":
                return await self._create_customer_account()
            elif step_name == "setup_billing_profile":
                return await self._setup_billing_profile()
            elif step_name == "provision_services":
                return await self._provision_services()
            elif step_name == "send_welcome_communications":
                return await self._send_welcome_communications()
            elif step_name == "finalize_onboarding":
                return await self._finalize_onboarding()
            else:
                return BusinessWorkflowResult(
                    success=False,
                    step_name=step_name,
                    error=f"Unknown step: {step_name}",
                )

        except Exception as e:
            logger.error(f"Step {step_name} failed: {str(e)}")
            return BusinessWorkflowResult(
                success=False,
                step_name=step_name,
                error=f"Step execution failed: {str(e)}",
            )

    async def _validate_customer_data(self) -> BusinessWorkflowResult:
        """Step 1: Validate and sanitize customer data."""
        logger.info(f"Validating customer data for {self.onboarding_request.email}")

        try:
            # Sanitize and validate data
            sanitized_data = {
                "email": self.onboarding_request.email.lower().strip(),
                "first_name": self.onboarding_request.first_name.strip().title(),
                "last_name": self.onboarding_request.last_name.strip().title(),
                "phone": self.onboarding_request.phone.strip() if self.onboarding_request.phone else None,
                "company_name": self.onboarding_request.company_name.strip() if self.onboarding_request.company_name else None,
                "address": {
                    "line1": self.onboarding_request.address_line1.strip(),
                    "line2": self.onboarding_request.address_line2.strip() if self.onboarding_request.address_line2 else None,
                    "city": self.onboarding_request.city.strip().title(),
                    "state": self.onboarding_request.state.strip().upper(),
                    "postal_code": self.onboarding_request.postal_code.strip(),
                    "country": self.onboarding_request.country.upper(),
                }
            }

            # Additional validation logic
            validation_results = []

            # Phone number validation
            if sanitized_data["phone"]:
                phone_valid = await self._validate_phone_number(sanitized_data["phone"])
                validation_results.append(f"Phone validation: {'passed' if phone_valid else 'failed'}")

            # Address validation
            address_valid = await self._validate_address(sanitized_data["address"])
            validation_results.append(f"Address validation: {'passed' if address_valid else 'warning'}")

            return BusinessWorkflowResult(
                success=True,
                step_name="validate_customer_data",
                message="Customer data validated successfully",
                data={
                    "sanitized_data": sanitized_data,
                    "validation_results": validation_results,
                    "customer_type": self.onboarding_request.customer_type,
                },
            )

        except Exception as e:
            return BusinessWorkflowResult(
                success=False,
                step_name="validate_customer_data",
                error=f"Data validation failed: {str(e)}",
            )

    async def _create_customer_account(self) -> BusinessWorkflowResult:
        """Step 2: Create customer account and user credentials."""
        logger.info(f"Creating customer account for {self.onboarding_request.email}")

        try:
            # Create customer record
            customer_data = {
                "email": self.onboarding_request.email,
                "first_name": self.onboarding_request.first_name,
                "last_name": self.onboarding_request.last_name,
                "phone": self.onboarding_request.phone,
                "customer_type": self.onboarding_request.customer_type,
                "status": "pending_verification",
                "tenant_id": self.onboarding_request.tenant_id,
                "metadata": {
                    "onboarding_channel": self.onboarding_request.onboarding_channel,
                    "company_name": self.onboarding_request.company_name,
                    "tax_id": self.onboarding_request.tax_id,
                    **self.onboarding_request.metadata,
                }
            }

            # Use identity service to create customer
            customer = await self.identity_service.create_customer(customer_data)
            self._customer_id = customer.id if hasattr(customer, 'id') else customer['id']

            # Create user account if needed
            if hasattr(self.identity_service, 'create_user'):
                user_data = {
                    "username": self.onboarding_request.email,
                    "email": self.onboarding_request.email,
                    "first_name": self.onboarding_request.first_name,
                    "last_name": self.onboarding_request.last_name,
                    "customer_id": self._customer_id,
                    "portal_type": "customer",
                    "is_active": False,  # Will be activated after onboarding
                }

                user = await self.identity_service.create_user(user_data)
                self._user_id = user.id if hasattr(user, 'id') else user['id']

            return BusinessWorkflowResult(
                success=True,
                step_name="create_customer_account",
                message="Customer account created successfully",
                data={
                    "customer_id": str(self._customer_id),
                    "user_id": str(self._user_id) if self._user_id else None,
                    "email": self.onboarding_request.email,
                    "customer_type": self.onboarding_request.customer_type,
                },
            )

        except Exception as e:
            return BusinessWorkflowResult(
                success=False,
                step_name="create_customer_account",
                error=f"Account creation failed: {str(e)}",
            )

    async def _setup_billing_profile(self) -> BusinessWorkflowResult:
        """Step 3: Setup billing profile and payment methods."""
        logger.info(f"Setting up billing profile for customer {self._customer_id}")

        try:
            if not self._customer_id:
                raise ValueError("Customer ID not available")

            # Create billing profile
            billing_data = {
                "customer_id": self._customer_id,
                "billing_email": self.onboarding_request.email,
                "billing_address": {
                    "line1": self.onboarding_request.address_line1,
                    "line2": self.onboarding_request.address_line2,
                    "city": self.onboarding_request.city,
                    "state": self.onboarding_request.state,
                    "postal_code": self.onboarding_request.postal_code,
                    "country": self.onboarding_request.country,
                },
                "company_name": self.onboarding_request.company_name,
                "tax_id": self.onboarding_request.tax_id,
                "tenant_id": self.onboarding_request.tenant_id,
            }

            # Create billing profile using billing service
            if hasattr(self.billing_service, 'create_billing_profile'):
                billing_profile = await self.billing_service.create_billing_profile(billing_data)
                self._billing_profile_id = billing_profile.id if hasattr(billing_profile, 'id') else billing_profile['id']

            # Check if approval is required for high-value customers
            requires_approval = False
            approval_data = {}

            if self.approval_threshold and self.onboarding_request.plan_id:
                # Get plan details to check value
                estimated_monthly_value = await self._get_plan_value(self.onboarding_request.plan_id)
                if estimated_monthly_value and estimated_monthly_value > self.approval_threshold:
                    requires_approval = True
                    approval_data = {
                        "estimated_monthly_value": float(estimated_monthly_value),
                        "plan_id": self.onboarding_request.plan_id,
                        "customer_type": self.onboarding_request.customer_type,
                        "threshold": float(self.approval_threshold),
                    }

            return BusinessWorkflowResult(
                success=True,
                step_name="setup_billing_profile",
                message="Billing profile setup completed",
                data={
                    "billing_profile_id": str(self._billing_profile_id) if self._billing_profile_id else None,
                    "customer_id": str(self._customer_id),
                    "require_payment_method": self.onboarding_request.require_payment_method,
                },
                requires_approval=requires_approval,
                approval_data=approval_data,
            )

        except Exception as e:
            return BusinessWorkflowResult(
                success=False,
                step_name="setup_billing_profile",
                error=f"Billing setup failed: {str(e)}",
            )

    async def _provision_services(self) -> BusinessWorkflowResult:
        """Step 4: Provision requested services and resources."""
        logger.info(f"Provisioning services for customer {self._customer_id}")

        try:
            provisioned_resources = []

            # Provision services based on plan
            if self.onboarding_request.plan_id and self.provisioning_service:
                provisioning_request = {
                    "customer_id": self._customer_id,
                    "plan_id": self.onboarding_request.plan_id,
                    "customer_type": self.onboarding_request.customer_type,
                    "tenant_id": self.onboarding_request.tenant_id,
                }

                resources = await self.provisioning_service.provision_customer_services(provisioning_request)
                provisioned_resources.extend(resources)
                self._provisioned_resources = provisioned_resources

            # Create default customer portal access
            if hasattr(self.identity_service, 'create_portal_access'):
                portal_access = await self.identity_service.create_portal_access({
                    "customer_id": self._customer_id,
                    "portal_type": "customer",
                    "permissions": ["view_account", "view_billing", "manage_services"],
                })
                provisioned_resources.append({
                    "type": "portal_access",
                    "id": str(portal_access.id) if hasattr(portal_access, 'id') else "created",
                })

            return BusinessWorkflowResult(
                success=True,
                step_name="provision_services",
                message="Services provisioned successfully",
                data={
                    "customer_id": str(self._customer_id),
                    "provisioned_resources": provisioned_resources,
                    "plan_id": self.onboarding_request.plan_id,
                    "resource_count": len(provisioned_resources),
                },
            )

        except Exception as e:
            return BusinessWorkflowResult(
                success=False,
                step_name="provision_services",
                error=f"Service provisioning failed: {str(e)}",
            )

    async def _send_welcome_communications(self) -> BusinessWorkflowResult:
        """Step 5: Send welcome communications and account details."""
        logger.info(f"Sending welcome communications to {self.onboarding_request.email}")

        try:
            if not self.onboarding_request.send_welcome_email:
                return BusinessWorkflowResult(
                    success=True,
                    step_name="send_welcome_communications",
                    message="Welcome communications skipped per configuration",
                )

            # Prepare welcome email data
            communication_data = {
                "customer_id": self._customer_id,
                "email": self.onboarding_request.email,
                "first_name": self.onboarding_request.first_name,
                "last_name": self.onboarding_request.last_name,
                "company_name": self.onboarding_request.company_name,
                "customer_type": self.onboarding_request.customer_type,
                "onboarding_channel": self.onboarding_request.onboarding_channel,
                "account_details": {
                    "customer_id": str(self._customer_id),
                    "user_id": str(self._user_id) if self._user_id else None,
                    "plan_id": self.onboarding_request.plan_id,
                },
            }

            # Send welcome email
            notifications_sent = []
            if hasattr(self.notification_service, 'send_welcome_email'):
                await self.notification_service.send_welcome_email(communication_data)
                notifications_sent.append("welcome_email")

            # Send SMS welcome if phone provided
            if self.onboarding_request.phone and hasattr(self.notification_service, 'send_welcome_sms'):
                await self.notification_service.send_welcome_sms({
                    "phone": self.onboarding_request.phone,
                    "first_name": self.onboarding_request.first_name,
                    "customer_id": str(self._customer_id),
                })
                notifications_sent.append("welcome_sms")

            return BusinessWorkflowResult(
                success=True,
                step_name="send_welcome_communications",
                message="Welcome communications sent successfully",
                data={
                    "customer_id": str(self._customer_id),
                    "notifications_sent": notifications_sent,
                    "email": self.onboarding_request.email,
                    "phone": self.onboarding_request.phone,
                },
            )

        except Exception as e:
            return BusinessWorkflowResult(
                success=False,
                step_name="send_welcome_communications",
                error=f"Communication sending failed: {str(e)}",
            )

    async def _finalize_onboarding(self) -> BusinessWorkflowResult:
        """Step 6: Complete onboarding and activate account."""
        logger.info(f"Finalizing onboarding for customer {self._customer_id}")

        try:
            finalization_actions = []

            # Activate customer account if configured
            if self.onboarding_request.auto_activate and self._customer_id:
                if hasattr(self.identity_service, 'activate_customer'):
                    await self.identity_service.activate_customer(self._customer_id)
                    finalization_actions.append("customer_activated")

                # Activate user account
                if self._user_id and hasattr(self.identity_service, 'activate_user'):
                    await self.identity_service.activate_user(self._user_id)
                    finalization_actions.append("user_activated")

            # Update customer lifecycle stage
            if hasattr(self.identity_service, 'update_customer_lifecycle'):
                await self.identity_service.update_customer_lifecycle(
                    self._customer_id,
                    "onboarding_completed" if self.onboarding_request.auto_activate else "pending_activation"
                )
                finalization_actions.append("lifecycle_updated")

            # Record onboarding completion
            completion_data = {
                "workflow_id": self.workflow_id,
                "customer_id": str(self._customer_id),
                "user_id": str(self._user_id) if self._user_id else None,
                "billing_profile_id": str(self._billing_profile_id) if self._billing_profile_id else None,
                "onboarding_channel": self.onboarding_request.onboarding_channel,
                "customer_type": self.onboarding_request.customer_type,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "auto_activated": self.onboarding_request.auto_activate,
                "provisioned_resources": self._provisioned_resources,
            }

            return BusinessWorkflowResult(
                success=True,
                step_name="finalize_onboarding",
                message="Customer onboarding completed successfully",
                data={
                    **completion_data,
                    "finalization_actions": finalization_actions,
                    "total_steps": len(self.steps),
                },
            )

        except Exception as e:
            return BusinessWorkflowResult(
                success=False,
                step_name="finalize_onboarding",
                error=f"Onboarding finalization failed: {str(e)}",
            )

    async def rollback_step(self, step_name: str) -> BusinessWorkflowResult:
        """Rollback a specific onboarding step."""
        logger.info(f"Rolling back step: {step_name}")

        try:
            if step_name == "finalize_onboarding":
                # Deactivate accounts if they were activated
                if self._customer_id and hasattr(self.identity_service, 'suspend_customer'):
                    await self.identity_service.suspend_customer(self._customer_id)

            elif step_name == "send_welcome_communications":
                # Cannot rollback sent communications, but can mark as needs resend
                pass

            elif step_name == "provision_services":
                # Deprovision created resources
                if self._provisioned_resources and self.provisioning_service:
                    for resource in self._provisioned_resources:
                        try:
                            await self.provisioning_service.deprovision_resource(resource)
                        except Exception as e:
                            logger.warning(f"Failed to deprovision resource {resource}: {str(e)}")

            elif step_name == "setup_billing_profile":
                # Remove billing profile
                if self._billing_profile_id and hasattr(self.billing_service, 'delete_billing_profile'):
                    await self.billing_service.delete_billing_profile(self._billing_profile_id)

            elif step_name == "create_customer_account":
                # Remove customer and user accounts
                if self._user_id and hasattr(self.identity_service, 'delete_user'):
                    await self.identity_service.delete_user(self._user_id)

                if self._customer_id and hasattr(self.identity_service, 'delete_customer'):
                    await self.identity_service.delete_customer(self._customer_id)

            return BusinessWorkflowResult(
                success=True,
                step_name=f"rollback_{step_name}",
                message=f"Successfully rolled back step: {step_name}",
            )

        except Exception as e:
            return BusinessWorkflowResult(
                success=False,
                step_name=f"rollback_{step_name}",
                error=f"Rollback failed for {step_name}: {str(e)}",
            )

    # Helper methods

    async def _check_existing_customer(self) -> Any:
        """Check if customer already exists."""
        try:
            if hasattr(self.identity_service, 'get_customer_by_email'):
                return await self.identity_service.get_customer_by_email(self.onboarding_request.email)
        except Exception as e:
            logger.warning(f"Failed to check existing customer: {str(e)}")
        return None

    async def _validate_phone_number(self, phone: str) -> bool:
        """Validate phone number format."""
        import re

        # Basic phone validation - can be enhanced with external service
        phone_pattern = r'^[\+]?[1-9][\d]{0,15}$'
        return bool(re.match(phone_pattern, re.sub(r'[\s\-\(\)]', '', phone)))

    async def _validate_address(self, address: dict[str, Any]) -> bool:
        """Validate address - placeholder for address validation service."""
        # Basic validation - can be enhanced with address validation service
        required_fields = ['line1', 'city', 'state', 'postal_code', 'country']
        return all(address.get(field) for field in required_fields)

    async def _get_plan_value(self, plan_id: str) -> Decimal | None:
        """Get estimated monthly value for a plan."""
        try:
            if hasattr(self.billing_service, 'get_plan'):
                plan = await self.billing_service.get_plan(plan_id)
                if plan and hasattr(plan, 'monthly_price'):
                    return Decimal(str(plan.monthly_price))
            return Decimal('0')
        except Exception:
            return None
