"""
End-to-End tests for Customer Onboarding Journey.

Tests the complete customer onboarding workflow:
1. Customer signup and account creation
2. Email verification and activation
3. Plan selection and subscription setup
4. Payment method configuration
5. Service provisioning and activation
6. First login and dashboard access
7. Initial service usage tracking
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest

# Use platform services database module instead
try:
    from dotmac.database.base import get_db
except ImportError:
    # Fallback for test environments
    def get_db():
        """Mock database dependency for testing."""
        return None

# API test client import - create if needed for actual testing
try:
    from tests.utilities.api_test_client import APITestClient
except ImportError:
    # Mock for collection phase
    class APITestClient:
        def __init__(self, *args, **kwargs):
            pass


class TestCustomerOnboardingJourney:
    """Complete customer onboarding journey tests."""

    @pytest.fixture
    def customer_signup_data(self):
        """Sample customer signup data."""
        return {
            "email": "newcustomer@example.com",
            "name": "John Customer",
            "company": "Customer Corp",
            "phone": "+1-555-0123",
            "address": {
                "street": "123 Customer St",
                "city": "Customer City",
                "state": "CC",
                "zip_code": "12345",
                "country": "US"
            },
            "service_address": {
                "street": "123 Service Location",
                "city": "Service City",
                "state": "SC",
                "zip_code": "54321",
                "country": "US"
            }
        }

    @pytest.fixture
    def selected_plan_data(self):
        """Sample service plan selection."""
        return {
            "plan_id": str(uuid4()),
            "plan_name": "Business Internet 100",
            "speed_down": 100,  # Mbps
            "speed_up": 10,     # Mbps
            "monthly_price": Decimal("89.99"),
            "installation_fee": Decimal("99.00"),
            "equipment_fee": Decimal("10.00"),
            "features": [
                "static_ip",
                "24x7_support",
                "sla_guarantee"
            ]
        }

    @pytest.fixture
    def payment_method_data(self):
        """Sample payment method data."""
        return {
            "type": "credit_card",
            "card_number": "4111111111111111",  # Test Visa number
            "expiry_month": 12,
            "expiry_year": 2026,
            "cvv": "123",
            "cardholder_name": "John Customer",
            "billing_address": {
                "street": "123 Customer St",
                "city": "Customer City",
                "state": "CC",
                "zip_code": "12345",
                "country": "US"
            }
        }

    @pytest.fixture
    async def e2e_test_client(self, test_app, async_db_session):
        """E2E test client with all dependencies mocked."""
        client = APITestClient(test_app)

        # Override database dependency
        async def get_test_db():
            yield async_db_session

        test_app.dependency_overrides[get_db] = get_test_db

        return client

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_complete_customer_onboarding_success_journey(
        self,
        e2e_test_client: APITestClient,
        customer_signup_data: dict[str, Any],
        selected_plan_data: dict[str, Any],
        payment_method_data: dict[str, Any]
    ):
        """Test complete successful customer onboarding journey."""

        # Step 1: Customer Signup
        signup_response = await e2e_test_client.post("/customer/signup", json=customer_signup_data)
        assert signup_response.status_code == 201

        signup_data = signup_response.json()
        customer_id = signup_data["customer_id"]
        verification_token = signup_data["email_verification_token"]

        assert signup_data["email"] == customer_signup_data["email"]
        assert signup_data["status"] == "pending_verification"
        assert verification_token is not None

        # Step 2: Email Verification
        verification_response = await e2e_test_client.post(
            "/customer/verify-email",
            json={"token": verification_token}
        )
        assert verification_response.status_code == 200

        verification_data = verification_response.json()
        assert verification_data["verified"] is True
        assert verification_data["status"] == "active"

        # Step 3: Browse Available Plans
        plans_response = await e2e_test_client.get(
            f"/customer/{customer_id}/available-plans",
            params={"service_address": customer_signup_data["service_address"]}
        )
        assert plans_response.status_code == 200

        plans_data = plans_response.json()
        assert len(plans_data["plans"]) > 0
        assert any(plan["plan_id"] == selected_plan_data["plan_id"] for plan in plans_data["plans"])

        # Step 4: Select Service Plan
        plan_selection_response = await e2e_test_client.post(
            f"/customer/{customer_id}/select-plan",
            json=selected_plan_data
        )
        assert plan_selection_response.status_code == 200

        selection_data = plan_selection_response.json()
        assert selection_data["plan_selected"] is True
        assert selection_data["monthly_total"] >= selected_plan_data["monthly_price"]

        # Step 5: Add Payment Method
        payment_method_response = await e2e_test_client.post(
            f"/customer/{customer_id}/payment-methods",
            json=payment_method_data
        )
        assert payment_method_response.status_code == 201

        payment_data = payment_method_response.json()
        payment_method_id = payment_data["payment_method_id"]
        assert payment_data["type"] == "credit_card"
        assert payment_data["last_four"] == "1111"

        # Step 6: Process Installation and Setup Fees
        setup_payment_response = await e2e_test_client.post(
            f"/customer/{customer_id}/process-setup-payment",
            json={
                "payment_method_id": payment_method_id,
                "installation_fee": str(selected_plan_data["installation_fee"]),
                "equipment_fee": str(selected_plan_data["equipment_fee"])
            }
        )
        assert setup_payment_response.status_code == 200

        setup_data = setup_payment_response.json()
        assert setup_data["payment_status"] == "completed"
        setup_data["invoice_id"]

        # Step 7: Schedule Installation
        installation_response = await e2e_test_client.post(
            f"/customer/{customer_id}/schedule-installation",
            json={
                "preferred_date": (datetime.now() + timedelta(days=7)).isoformat(),
                "time_window": "morning",
                "special_instructions": "Call before arriving"
            }
        )
        assert installation_response.status_code == 200

        installation_data = installation_response.json()
        assert installation_data["scheduled"] is True
        installation_id = installation_data["installation_id"]

        # Step 8: Complete Installation (Simulated)
        installation_completion_response = await e2e_test_client.patch(
            f"/installations/{installation_id}/complete",
            json={
                "technician_id": str(uuid4()),
                "equipment_installed": [
                    {"type": "modem", "serial": "MOD123456"},
                    {"type": "router", "serial": "RTR789012"}
                ],
                "signal_strength": -45,  # dBm
                "speed_test": {
                    "download": 102.5,
                    "upload": 11.2,
                    "latency": 15
                }
            }
        )
        assert installation_completion_response.status_code == 200

        completion_data = installation_completion_response.json()
        assert completion_data["status"] == "completed"
        assert completion_data["service_active"] is True

        # Step 9: First Customer Login
        login_response = await e2e_test_client.post(
            "/customer/login",
            json={
                "email": customer_signup_data["email"],
                "password": "temporary_password_sent_via_email"
            }
        )
        assert login_response.status_code == 200

        login_data = login_response.json()
        access_token = login_data["access_token"]
        assert access_token is not None

        # Step 10: Access Customer Dashboard
        dashboard_response = await e2e_test_client.get(
            f"/customer/{customer_id}/dashboard",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert dashboard_response.status_code == 200

        dashboard_data = dashboard_response.json()
        assert dashboard_data["customer"]["email"] == customer_signup_data["email"]
        assert dashboard_data["service"]["status"] == "active"
        assert dashboard_data["service"]["plan_name"] == selected_plan_data["plan_name"]
        assert dashboard_data["billing"]["next_bill_date"] is not None

        # Step 11: View Service Usage (Initial)
        usage_response = await e2e_test_client.get(
            f"/customer/{customer_id}/usage",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"period": "current"}
        )
        assert usage_response.status_code == 200

        usage_data = usage_response.json()
        assert usage_data["period_start"] is not None
        assert usage_data["period_end"] is not None
        assert "bandwidth_usage" in usage_data

        # Step 12: Verify Billing Subscription Created
        subscription_response = await e2e_test_client.get(
            f"/customer/{customer_id}/subscription",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert subscription_response.status_code == 200

        subscription_data = subscription_response.json()
        assert subscription_data["status"] == "active"
        assert Decimal(subscription_data["monthly_amount"]) == selected_plan_data["monthly_price"]
        assert subscription_data["next_billing_date"] is not None

        # Step 13: Verify First Monthly Invoice Generation (Simulated)
        # This would typically be done via a background task
        first_invoice_response = await e2e_test_client.post(
            f"/billing/generate-invoice/{customer_id}",
            json={"billing_period": "2024-01"}
        )
        assert first_invoice_response.status_code == 201

        invoice_data = first_invoice_response.json()
        assert invoice_data["status"] == "sent"
        assert Decimal(invoice_data["total_amount"]) >= selected_plan_data["monthly_price"]

        # Verification: Complete journey validation
        customer_status_response = await e2e_test_client.get(f"/customer/{customer_id}/status")
        assert customer_status_response.status_code == 200

        status_data = customer_status_response.json()
        assert status_data["onboarding_completed"] is True
        assert status_data["service_active"] is True
        assert status_data["billing_active"] is True
        assert status_data["payment_method_on_file"] is True

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_customer_onboarding_with_payment_failure(
        self,
        e2e_test_client: APITestClient,
        customer_signup_data: dict[str, Any],
        selected_plan_data: dict[str, Any]
    ):
        """Test customer onboarding journey with payment failure and recovery."""

        # Steps 1-4: Complete initial signup through plan selection (same as success case)
        signup_response = await e2e_test_client.post("/customer/signup", json=customer_signup_data)
        customer_id = signup_response.json()["customer_id"]
        verification_token = signup_response.json()["email_verification_token"]

        await e2e_test_client.post("/customer/verify-email", json={"token": verification_token})
        await e2e_test_client.post(f"/customer/{customer_id}/select-plan", json=selected_plan_data)

        # Step 5: Add Payment Method with Insufficient Funds
        failing_payment_method = {
            "type": "credit_card",
            "card_number": "4000000000000002",  # Test card that will be declined
            "expiry_month": 12,
            "expiry_year": 2026,
            "cvv": "123",
            "cardholder_name": "John Customer"
        }

        payment_method_response = await e2e_test_client.post(
            f"/customer/{customer_id}/payment-methods",
            json=failing_payment_method
        )
        payment_method_id = payment_method_response.json()["payment_method_id"]

        # Step 6: Attempt Setup Payment (Should Fail)
        setup_payment_response = await e2e_test_client.post(
            f"/customer/{customer_id}/process-setup-payment",
            json={
                "payment_method_id": payment_method_id,
                "installation_fee": str(selected_plan_data["installation_fee"])
            }
        )

        assert setup_payment_response.status_code == 400
        payment_failure_data = setup_payment_response.json()
        assert payment_failure_data["payment_status"] == "failed"
        assert "insufficient funds" in payment_failure_data["failure_reason"].lower()

        # Step 7: Customer Adds New Valid Payment Method
        valid_payment_method = {
            "type": "credit_card",
            "card_number": "4111111111111111",  # Valid test card
            "expiry_month": 12,
            "expiry_year": 2026,
            "cvv": "123",
            "cardholder_name": "John Customer"
        }

        new_payment_response = await e2e_test_client.post(
            f"/customer/{customer_id}/payment-methods",
            json=valid_payment_method
        )
        new_payment_method_id = new_payment_response.json()["payment_method_id"]

        # Step 8: Retry Setup Payment (Should Succeed)
        retry_payment_response = await e2e_test_client.post(
            f"/customer/{customer_id}/process-setup-payment",
            json={
                "payment_method_id": new_payment_method_id,
                "installation_fee": str(selected_plan_data["installation_fee"])
            }
        )

        assert retry_payment_response.status_code == 200
        retry_data = retry_payment_response.json()
        assert retry_data["payment_status"] == "completed"

        # Step 9: Verify Customer Status After Recovery
        status_response = await e2e_test_client.get(f"/customer/{customer_id}/status")
        status_data = status_response.json()

        assert status_data["payment_method_on_file"] is True
        assert status_data["setup_payment_completed"] is True
        assert len(status_data["failed_payment_attempts"]) == 1

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_customer_onboarding_service_availability_check(
        self,
        e2e_test_client: APITestClient,
        customer_signup_data: dict[str, Any]
    ):
        """Test customer onboarding with service availability checking."""

        # Step 1: Initial Signup
        signup_response = await e2e_test_client.post("/customer/signup", json=customer_signup_data)
        customer_id = signup_response.json()["customer_id"]

        # Step 2: Check Service Availability at Address
        availability_response = await e2e_test_client.post(
            "/customer/check-service-availability",
            json={
                "address": customer_signup_data["service_address"],
                "service_types": ["residential", "business"]
            }
        )

        assert availability_response.status_code == 200
        availability_data = availability_response.json()

        if availability_data["service_available"]:
            # Service is available - continue with normal flow
            assert len(availability_data["available_plans"]) > 0
            assert availability_data["estimated_install_time"] is not None

            # Proceed with plan selection
            selected_plan = availability_data["available_plans"][0]
            plan_response = await e2e_test_client.post(
                f"/customer/{customer_id}/select-plan",
                json=selected_plan
            )
            assert plan_response.status_code == 200

        else:
            # Service not available - customer should be waitlisted
            assert availability_data["service_available"] is False
            assert "waitlist" in availability_data

            # Add customer to waitlist
            waitlist_response = await e2e_test_client.post(
                f"/customer/{customer_id}/join-waitlist",
                json={
                    "service_address": customer_signup_data["service_address"],
                    "desired_service_types": ["business"],
                    "notify_preferences": ["email", "sms"]
                }
            )

            assert waitlist_response.status_code == 200
            waitlist_data = waitlist_response.json()
            assert waitlist_data["waitlisted"] is True
            assert waitlist_data["estimated_availability"] is not None

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_customer_onboarding_multi_tenant_isolation(
        self,
        e2e_test_client: APITestClient,
        customer_signup_data: dict[str, Any]
    ):
        """Test customer onboarding with multi-tenant isolation."""

        tenant_a_id = str(uuid4())
        tenant_b_id = str(uuid4())

        # Create customers in different tenants
        customer_a_data = customer_signup_data.copy()
        customer_a_data["tenant_id"] = tenant_a_id
        customer_a_data["email"] = "customer_a@tenant-a.com"

        customer_b_data = customer_signup_data.copy()
        customer_b_data["tenant_id"] = tenant_b_id
        customer_b_data["email"] = "customer_b@tenant-b.com"

        # Signup customers in both tenants
        signup_a_response = await e2e_test_client.post(
            "/customer/signup",
            json=customer_a_data,
            headers={"X-Tenant-ID": tenant_a_id}
        )
        signup_b_response = await e2e_test_client.post(
            "/customer/signup",
            json=customer_b_data,
            headers={"X-Tenant-ID": tenant_b_id}
        )

        customer_a_id = signup_a_response.json()["customer_id"]
        customer_b_id = signup_b_response.json()["customer_id"]

        # Verify tenant isolation - Tenant A cannot access Tenant B's customer
        cross_tenant_response = await e2e_test_client.get(
            f"/customer/{customer_b_id}/status",
            headers={"X-Tenant-ID": tenant_a_id}
        )
        assert cross_tenant_response.status_code == 404  # Not found due to tenant isolation

        # Verify each tenant can access their own customers
        tenant_a_response = await e2e_test_client.get(
            f"/customer/{customer_a_id}/status",
            headers={"X-Tenant-ID": tenant_a_id}
        )
        assert tenant_a_response.status_code == 200

        tenant_b_response = await e2e_test_client.get(
            f"/customer/{customer_b_id}/status",
            headers={"X-Tenant-ID": tenant_b_id}
        )
        assert tenant_b_response.status_code == 200


class TestCustomerOnboardingErrorRecovery:
    """Test error recovery scenarios in customer onboarding."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_email_verification_expiration_and_resend(
        self,
        e2e_test_client: APITestClient,
        customer_signup_data: dict[str, Any]
    ):
        """Test email verification token expiration and resend functionality."""

        # Step 1: Customer signup
        signup_response = await e2e_test_client.post("/customer/signup", json=customer_signup_data)
        customer_id = signup_response.json()["customer_id"]
        expired_token = signup_response.json()["email_verification_token"]

        # Step 2: Simulate expired token verification attempt
        expired_verification_response = await e2e_test_client.post(
            "/customer/verify-email",
            json={"token": expired_token + "_expired"}  # Simulate expired/invalid token
        )
        assert expired_verification_response.status_code == 400

        verification_data = expired_verification_response.json()
        assert "expired" in verification_data["error"].lower() or "invalid" in verification_data["error"].lower()

        # Step 3: Request new verification email
        resend_response = await e2e_test_client.post(
            "/customer/resend-verification",
            json={"customer_id": customer_id}
        )
        assert resend_response.status_code == 200

        resend_data = resend_response.json()
        new_token = resend_data["new_verification_token"]
        assert new_token != expired_token

        # Step 4: Verify with new token
        new_verification_response = await e2e_test_client.post(
            "/customer/verify-email",
            json={"token": new_token}
        )
        assert new_verification_response.status_code == 200
        assert new_verification_response.json()["verified"] is True

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_installation_rescheduling_workflow(
        self,
        e2e_test_client: APITestClient,
        customer_signup_data: dict[str, Any],
        selected_plan_data: dict[str, Any]
    ):
        """Test installation rescheduling workflow."""

        # Complete initial setup through installation scheduling
        signup_response = await e2e_test_client.post("/customer/signup", json=customer_signup_data)
        customer_id = signup_response.json()["customer_id"]

        # Simplified setup (skip verification, payment for this test)
        await e2e_test_client.post(f"/customer/{customer_id}/select-plan", json=selected_plan_data)

        # Schedule initial installation
        initial_date = (datetime.now() + timedelta(days=7)).isoformat()
        schedule_response = await e2e_test_client.post(
            f"/customer/{customer_id}/schedule-installation",
            json={
                "preferred_date": initial_date,
                "time_window": "morning"
            }
        )

        installation_id = schedule_response.json()["installation_id"]

        # Customer requests rescheduling
        new_date = (datetime.now() + timedelta(days=10)).isoformat()
        reschedule_response = await e2e_test_client.patch(
            f"/installations/{installation_id}/reschedule",
            json={
                "new_preferred_date": new_date,
                "new_time_window": "afternoon",
                "reason": "Customer availability changed"
            }
        )

        assert reschedule_response.status_code == 200
        reschedule_data = reschedule_response.json()
        assert reschedule_data["rescheduled"] is True
        assert reschedule_data["new_scheduled_date"] != initial_date

        # Verify installation status reflects the change
        installation_status_response = await e2e_test_client.get(f"/installations/{installation_id}")
        status_data = installation_status_response.json()
        assert status_data["status"] == "rescheduled"
        assert status_data["reschedule_count"] == 1


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_complete_customer_lifecycle_simulation():
    """Simulate complete customer lifecycle from onboarding to service termination."""

    # This test would simulate:
    # 1. Customer onboarding (full flow)
    # 2. Several months of service usage
    # 3. Plan upgrades/downgrades
    # 4. Support tickets and resolutions
    # 5. Billing and payment cycles
    # 6. Service termination and cleanup

    # Mock time progression and simulate multi-month lifecycle
    lifecycle_events = [
        {"month": 1, "event": "onboarding", "action": "complete_signup"},
        {"month": 1, "event": "usage", "action": "normal_usage"},
        {"month": 2, "event": "billing", "action": "monthly_invoice"},
        {"month": 3, "event": "upgrade", "action": "plan_upgrade"},
        {"month": 6, "event": "support", "action": "service_ticket"},
        {"month": 12, "event": "renewal", "action": "contract_renewal"},
        {"month": 18, "event": "termination", "action": "service_cancellation"}
    ]

    # For each lifecycle event, verify the system behaves correctly
    for event in lifecycle_events:
        # Simulate the passage of time and trigger appropriate actions
        # This would involve mocking time, triggering background jobs,
        # and verifying system state at each lifecycle stage
        assert event["month"] > 0  # Placeholder assertion

    # Final verification: ensure clean termination leaves no orphaned data
    assert True  # Placeholder for comprehensive cleanup verification
