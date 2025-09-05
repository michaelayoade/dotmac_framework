"""
Customer Management API Integration Tests

This module tests complete customer lifecycle workflows across all portals,
ensuring data consistency and business rule enforcement.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import status
from httpx import AsyncClient

# Test utilities
from tests.utilities.test_helpers import (
    create_test_customer,
    create_test_reseller,
)


class TestCustomerLifecycleAPI:
    """Test complete customer lifecycle through API endpoints."""

    @pytest.fixture
    async def test_customer_data(self):
        """Create test customer data."""
        return {
            "email": "test.customer@example.com",
            "first_name": "Test",
            "last_name": "Customer",
            "phone": "+1-555-123-4567",
            "address": {
                "street": "123 Main St",
                "city": "Anytown",
                "state": "CA",
                "zip_code": "90210",
                "country": "US",
            },
            "service_address": {
                "street": "123 Main St",
                "city": "Anytown",
                "state": "CA",
                "zip_code": "90210",
                "country": "US",
            },
            "billing_contact": {"same_as_service": True},
        }

    @pytest.fixture
    async def test_service_plan(self):
        """Create test service plan."""
        return {
            "plan_id": "residential_100mbps",
            "name": "Residential 100Mbps",
            "download_speed": 100,
            "upload_speed": 10,
            "data_allowance": -1,  # Unlimited
            "monthly_price": Decimal("59.99"),
            "setup_fee": Decimal("99.00"),
            "contract_length": 12,
        }

    # Complete Customer Onboarding Flow Tests

    @pytest.mark.asyncio
    async def test_create_customer_complete_flow(
        self,
        async_client: AsyncClient,
        test_customer_data: Dict,
        test_service_plan: Dict,
        admin_auth_headers: Dict,
    ):
        """Test complete customer creation flow through admin portal."""

        # Step 1: Create customer profile
        customer_response = await async_client.post(
            "/api/v1/customers", json=test_customer_data, headers=admin_auth_headers
        )

        assert customer_response.status_code == status.HTTP_201_CREATED
        customer = customer_response.json()
        customer_id = customer["customer_id"]

        # Verify customer creation
        assert customer["email"] == test_customer_data["email"]
        assert customer["status"] == "pending_activation"
        assert customer["created_at"] is not None

        # Step 2: Assign service plan
        service_assignment = {
            "customer_id": customer_id,
            "service_plan_id": test_service_plan["plan_id"],
            "installation_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "billing_cycle": "monthly",
        }

        service_response = await async_client.post(
            f"/api/v1/customers/{customer_id}/services",
            json=service_assignment,
            headers=admin_auth_headers,
        )

        assert service_response.status_code == status.HTTP_201_CREATED
        service = service_response.json()

        # Verify service assignment
        assert service["customer_id"] == customer_id
        assert service["service_plan_id"] == test_service_plan["plan_id"]
        assert service["status"] == "scheduled"

        # Step 3: Setup billing profile
        billing_setup = {
            "payment_method": {
                "type": "credit_card",
                "card_last_four": "4242",
                "expiry_month": 12,
                "expiry_year": 2025,
            },
            "billing_cycle": "monthly",
            "auto_pay": True,
        }

        billing_response = await async_client.post(
            f"/api/v1/customers/{customer_id}/billing/setup",
            json=billing_setup,
            headers=admin_auth_headers,
        )

        assert billing_response.status_code == status.HTTP_201_CREATED
        billing = billing_response.json()

        # Verify billing setup
        assert billing["customer_id"] == customer_id
        assert billing["auto_pay"] is True
        assert billing["next_billing_date"] is not None

        # Step 4: Verify complete customer record
        complete_customer_response = await async_client.get(
            f"/api/v1/customers/{customer_id}/complete", headers=admin_auth_headers
        )

        assert complete_customer_response.status_code == status.HTTP_200_OK
        complete_customer = complete_customer_response.json()

        # Verify complete integration
        assert complete_customer["customer"]["customer_id"] == customer_id
        assert len(complete_customer["services"]) == 1
        assert complete_customer["billing"]["auto_pay"] is True
        assert complete_customer["status"]["overall"] == "pending_activation"

    @pytest.mark.asyncio
    async def test_customer_service_modification_workflow(
        self,
        async_client: AsyncClient,
        existing_customer: Dict,
        admin_auth_headers: Dict,
    ):
        """Test service plan modification workflow."""

        customer_id = existing_customer["customer_id"]

        # Step 1: Request service upgrade
        upgrade_request = {
            "new_service_plan_id": "residential_500mbps",
            "effective_date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "reason": "customer_upgrade_request",
            "prorated_billing": True,
        }

        upgrade_response = await async_client.post(
            f"/api/v1/customers/{customer_id}/services/modify",
            json=upgrade_request,
            headers=admin_auth_headers,
        )

        assert upgrade_response.status_code == status.HTTP_202_ACCEPTED
        modification = upgrade_response.json()

        # Verify modification request
        assert modification["customer_id"] == customer_id
        assert modification["status"] == "pending_approval"
        assert modification["new_service_plan_id"] == "residential_500mbps"

        # Step 2: Approve service modification
        approval_response = await async_client.post(
            f"/api/v1/services/modifications/{modification['modification_id']}/approve",
            headers=admin_auth_headers,
        )

        assert approval_response.status_code == status.HTTP_200_OK

        # Step 3: Verify billing impact calculation
        billing_impact_response = await async_client.get(
            f"/api/v1/customers/{customer_id}/billing/prorated-impact",
            headers=admin_auth_headers,
        )

        assert billing_impact_response.status_code == status.HTTP_200_OK
        billing_impact = billing_impact_response.json()

        # Verify prorated billing calculation
        assert billing_impact["customer_id"] == customer_id
        assert billing_impact["prorated_amount"] > 0
        assert billing_impact["effective_date"] is not None

    @pytest.mark.asyncio
    async def test_customer_deactivation_cleanup_process(
        self,
        async_client: AsyncClient,
        existing_customer: Dict,
        admin_auth_headers: Dict,
    ):
        """Test complete customer deactivation and cleanup process."""

        customer_id = existing_customer["customer_id"]

        # Step 1: Initiate customer deactivation
        deactivation_request = {
            "reason": "customer_request",
            "effective_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "final_bill": True,
            "equipment_return": True,
            "service_transfer": None,  # No transfer
        }

        deactivation_response = await async_client.post(
            f"/api/v1/customers/{customer_id}/deactivate",
            json=deactivation_request,
            headers=admin_auth_headers,
        )

        assert deactivation_response.status_code == status.HTTP_202_ACCEPTED
        deactivation = deactivation_response.json()

        # Verify deactivation process initiated
        assert deactivation["customer_id"] == customer_id
        assert deactivation["status"] == "deactivation_scheduled"
        assert deactivation["final_bill"] is True

        # Step 2: Process service suspension
        suspension_response = await async_client.post(
            f"/api/v1/customers/{customer_id}/services/suspend",
            headers=admin_auth_headers,
        )

        assert suspension_response.status_code == status.HTTP_200_OK

        # Step 3: Generate final billing
        final_billing_response = await async_client.post(
            f"/api/v1/customers/{customer_id}/billing/finalize",
            headers=admin_auth_headers,
        )

        assert final_billing_response.status_code == status.HTTP_201_CREATED
        final_bill = final_billing_response.json()

        # Verify final billing
        assert final_bill["customer_id"] == customer_id
        assert final_bill["is_final_bill"] is True
        assert final_bill["amount_due"] >= 0

        # Step 4: Verify customer status update
        customer_status_response = await async_client.get(
            f"/api/v1/customers/{customer_id}", headers=admin_auth_headers
        )

        assert customer_status_response.status_code == status.HTTP_200_OK
        customer_status = customer_status_response.json()

        # Verify deactivated status
        assert customer_status["status"] == "deactivated"
        assert customer_status["deactivation_date"] is not None


class TestResellerCustomerManagement:
    """Test reseller-specific customer management flows."""

    @pytest.mark.asyncio
    async def test_reseller_customer_onboarding_commission_flow(
        self,
        async_client: AsyncClient,
        test_reseller: Dict,
        test_customer_data: Dict,
        reseller_auth_headers: Dict,
    ):
        """Test reseller customer onboarding with commission tracking."""

        reseller_id = test_reseller["reseller_id"]

        # Step 1: Reseller creates customer lead
        lead_data = {
            **test_customer_data,
            "lead_source": "reseller_direct",
            "reseller_id": reseller_id,
            "commission_eligible": True,
        }

        lead_response = await async_client.post(
            "/api/v1/resellers/leads", json=lead_data, headers=reseller_auth_headers
        )

        assert lead_response.status_code == status.HTTP_201_CREATED
        lead = lead_response.json()

        # Verify lead creation
        assert lead["reseller_id"] == reseller_id
        assert lead["status"] == "qualified"
        assert lead["commission_eligible"] is True

        # Step 2: Convert lead to customer
        conversion_data = {
            "lead_id": lead["lead_id"],
            "service_plan_id": "residential_100mbps",
            "installation_date": (datetime.utcnow() + timedelta(days=14)).isoformat(),
        }

        conversion_response = await async_client.post(
            "/api/v1/resellers/leads/convert",
            json=conversion_data,
            headers=reseller_auth_headers,
        )

        assert conversion_response.status_code == status.HTTP_201_CREATED
        customer = conversion_response.json()
        customer_id = customer["customer_id"]

        # Verify customer conversion
        assert customer["reseller_id"] == reseller_id
        assert customer["lead_source"] == "reseller_direct"
        assert customer["commission_tracking"]["eligible"] is True

        # Step 3: Verify commission calculation
        commission_response = await async_client.get(
            f"/api/v1/resellers/{reseller_id}/commissions/pending",
            headers=reseller_auth_headers,
        )

        assert commission_response.status_code == status.HTTP_200_OK
        commissions = commission_response.json()

        # Find commission for this customer
        customer_commission = next(
            (c for c in commissions["commissions"] if c["customer_id"] == customer_id),
            None,
        )

        assert customer_commission is not None
        assert customer_commission["commission_type"] == "acquisition"
        assert customer_commission["amount"] > 0

    @pytest.mark.asyncio
    async def test_reseller_territory_customer_validation(
        self,
        async_client: AsyncClient,
        test_reseller: Dict,
        reseller_auth_headers: Dict,
    ):
        """Test reseller territory validation for customer assignments."""

        reseller_id = test_reseller["reseller_id"]

        # Step 1: Create customer in reseller territory
        in_territory_customer = {
            "email": "in.territory@example.com",
            "service_address": {
                "street": "456 Territory St",
                "city": "Authorized City",
                "state": "CA",
                "zip_code": "90211",  # Within reseller territory
            },
        }

        valid_response = await async_client.post(
            "/api/v1/resellers/customers/validate-territory",
            json={"reseller_id": reseller_id, "customer_data": in_territory_customer},
            headers=reseller_auth_headers,
        )

        assert valid_response.status_code == status.HTTP_200_OK
        validation = valid_response.json()

        # Verify territory validation passed
        assert validation["territory_valid"] is True
        assert validation["reseller_authorized"] is True

        # Step 2: Attempt customer creation outside territory
        out_territory_customer = {
            "email": "out.territory@example.com",
            "service_address": {
                "street": "789 Outside St",
                "city": "Unauthorized City",
                "state": "NY",
                "zip_code": "10001",  # Outside reseller territory
            },
        }

        invalid_response = await async_client.post(
            "/api/v1/resellers/customers/validate-territory",
            json={"reseller_id": reseller_id, "customer_data": out_territory_customer},
            headers=reseller_auth_headers,
        )

        assert invalid_response.status_code == status.HTTP_403_FORBIDDEN
        error = invalid_response.json()

        # Verify territory validation failed
        assert "territory" in error["detail"].lower()
        assert "unauthorized" in error["detail"].lower()


class TestCustomerPortalIntegration:
    """Test customer portal integration with management APIs."""

    @pytest.mark.asyncio
    async def test_customer_self_service_profile_update(
        self,
        async_client: AsyncClient,
        existing_customer: Dict,
        customer_auth_headers: Dict,
    ):
        """Test customer self-service profile updates."""

        customer_id = existing_customer["customer_id"]

        # Step 1: Customer updates profile information
        profile_update = {
            "phone": "+1-555-999-8888",
            "email": "updated.customer@example.com",
            "preferences": {
                "billing_notifications": True,
                "service_notifications": True,
                "marketing_emails": False,
            },
        }

        update_response = await async_client.patch(
            f"/api/v1/customers/{customer_id}/profile",
            json=profile_update,
            headers=customer_auth_headers,
        )

        assert update_response.status_code == status.HTTP_200_OK
        updated_profile = update_response.json()

        # Verify profile updates
        assert updated_profile["phone"] == profile_update["phone"]
        assert updated_profile["email"] == profile_update["email"]
        assert updated_profile["preferences"]["marketing_emails"] is False

        # Step 2: Verify email change requires verification
        verification_check = await async_client.get(
            f"/api/v1/customers/{customer_id}/email-verification-status",
            headers=customer_auth_headers,
        )

        assert verification_check.status_code == status.HTTP_200_OK
        verification_status = verification_check.json()

        # Verify email verification required
        assert verification_status["email_verified"] is False
        assert verification_status["verification_sent"] is True

    @pytest.mark.asyncio
    async def test_customer_service_request_workflow(
        self,
        async_client: AsyncClient,
        existing_customer: Dict,
        customer_auth_headers: Dict,
    ):
        """Test customer service request workflow."""

        customer_id = existing_customer["customer_id"]

        # Step 1: Customer submits service request
        service_request = {
            "type": "technical_support",
            "priority": "medium",
            "subject": "Internet connection intermittent",
            "description": "Internet connection drops every few hours, especially in the evening",
            "preferred_contact_method": "phone",
            "available_times": ["9am-12pm", "2pm-5pm"],
        }

        request_response = await async_client.post(
            f"/api/v1/customers/{customer_id}/service-requests",
            json=service_request,
            headers=customer_auth_headers,
        )

        assert request_response.status_code == status.HTTP_201_CREATED
        ticket = request_response.json()
        ticket_id = ticket["ticket_id"]

        # Verify service request creation
        assert ticket["customer_id"] == customer_id
        assert ticket["type"] == "technical_support"
        assert ticket["status"] == "open"
        assert ticket["priority"] == "medium"

        # Step 2: Customer adds additional information
        additional_info = {
            "message": "I also noticed the issue happens more frequently when streaming video",
            "attachments": [],
        }

        update_response = await async_client.post(
            f"/api/v1/customers/{customer_id}/service-requests/{ticket_id}/messages",
            json=additional_info,
            headers=customer_auth_headers,
        )

        assert update_response.status_code == status.HTTP_201_CREATED

        # Step 3: Verify ticket update notification
        notifications_response = await async_client.get(
            f"/api/v1/customers/{customer_id}/notifications",
            headers=customer_auth_headers,
        )

        assert notifications_response.status_code == status.HTTP_200_OK
        notifications = notifications_response.json()

        # Verify notification created
        ticket_notifications = [
            n
            for n in notifications["notifications"]
            if n["type"] == "service_request_update" and str(ticket_id) in n["content"]
        ]
        assert len(ticket_notifications) > 0


# Test Fixtures and Utilities


@pytest.fixture
async def existing_customer(async_client: AsyncClient, admin_auth_headers: Dict):
    """Create an existing customer for testing."""
    customer_data = await create_test_customer()
    return customer_data


@pytest.fixture
async def test_reseller(async_client: AsyncClient, admin_auth_headers: Dict):
    """Create a test reseller for testing."""
    reseller_data = await create_test_reseller()
    return reseller_data


@pytest.fixture
def admin_auth_headers(admin_user_token: str) -> dict[str, str]:
    """Create admin authentication headers."""
    return {"Authorization": f"Bearer {admin_user_token}"}


@pytest.fixture
def reseller_auth_headers(reseller_user_token: str) -> dict[str, str]:
    """Create reseller authentication headers."""
    return {"Authorization": f"Bearer {reseller_user_token}"}


@pytest.fixture
def customer_auth_headers(customer_user_token: str) -> dict[str, str]:
    """Create customer authentication headers."""
    return {"Authorization": f"Bearer {customer_user_token}"}


# Test Configuration
pytest_plugins = ["pytest_asyncio"]
