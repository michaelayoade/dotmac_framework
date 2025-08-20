"""
Comprehensive tests for DotMac Identity SDKs.

Tests customer management, identity accounts, contacts, user profiles,
portal management, and consent preferences functionality.
"""

from uuid import uuid4

import pytest

from dotmac_identity.models.accounts import AccountStatus, MFAFactorType

# Import models and exceptions
from dotmac_identity.models.customers import (
    CustomerState,
)
from dotmac_identity.sdks.consent_preferences import ConsentPreferencesSDK
from dotmac_identity.sdks.contacts import ContactsSDK

# Import identity SDKs
from dotmac_identity.sdks.customer_management import CustomerManagementSDK
from dotmac_identity.sdks.customer_portal import CustomerPortalSDK
from dotmac_identity.sdks.identity_account import IdentityAccountSDK
from dotmac_identity.sdks.user_profile import UserProfileSDK


class TestCustomerManagementSDK:
    """Test customer lifecycle management functionality."""

    @pytest.fixture
    def customer_sdk(self):
        """Create customer management SDK instance."""
        return CustomerManagementSDK(tenant_id="test-tenant-123")

    @pytest.mark.asyncio
    async def test_create_customer(self, customer_sdk):
        """Test customer creation."""
        customer_number = "CUS-2024-001"
        display_name = "John Smith"

        result = await customer_sdk.create_customer(
            customer_number=customer_number,
            display_name=display_name,
            customer_type="residential",
            tags=["new_customer", "fiber_ready"],
            custom_fields={
                "preferred_contact_method": "email",
                "marketing_consent": True
            }
        )

        assert result["customer_number"] == customer_number
        assert result["display_name"] == display_name
        assert result["customer_type"] == "residential"
        assert result["state"] == CustomerState.LEAD.value
        assert "customer_id" in result
        assert "created_at" in result

    @pytest.mark.asyncio
    async def test_customer_lifecycle_transitions(self, customer_sdk):
        """Test complete customer lifecycle state transitions."""
        # Create customer
        customer = await customer_sdk.create_customer(
            customer_number="CUS-2024-002",
            display_name="Jane Doe",
            customer_type="residential"
        )
        customer_id = customer["customer_id"]

        # Transition to prospect
        prospect_result = await customer_sdk.transition_to_prospect(
            customer_id=customer_id,
            changed_by="sales_agent_001"
        )

        assert prospect_result["state"] == CustomerState.PROSPECT.value

        # Activate customer
        activation_result = await customer_sdk.activate_customer(
            customer_id=customer_id,
            changed_by="provisioning_system"
        )

        assert activation_result["state"] == CustomerState.ACTIVE.value
        assert activation_result["activation_date"] is not None

        # Suspend customer
        suspension_result = await customer_sdk.suspend_customer(
            customer_id=customer_id,
            changed_by="billing_system"
        )

        assert suspension_result["state"] == CustomerState.SUSPENDED.value

        # Mark as churned
        churn_result = await customer_sdk.churn_customer(
            customer_id=customer_id,
            changed_by="retention_team"
        )

        assert churn_result["state"] == CustomerState.CHURNED.value
        assert churn_result["churn_date"] is not None

    @pytest.mark.asyncio
    async def test_get_customer_by_number(self, customer_sdk):
        """Test retrieving customer by customer number."""
        customer_number = "CUS-2024-003"

        # Create customer
        created_customer = await customer_sdk.create_customer(
            customer_number=customer_number,
            display_name="Test Customer",
            customer_type="business"
        )

        # Retrieve by number
        retrieved_customer = await customer_sdk.get_customer_by_number(customer_number)

        assert retrieved_customer is not None
        assert retrieved_customer["customer_id"] == created_customer["customer_id"]
        assert retrieved_customer["customer_number"] == customer_number
        assert retrieved_customer["customer_type"] == "business"

    @pytest.mark.asyncio
    async def test_list_customers_with_filters(self, customer_sdk):
        """Test listing customers with various filters."""
        # Create multiple customers
        await customer_sdk.create_customer(
            customer_number="CUS-2024-004",
            display_name="Residential Customer 1",
            customer_type="residential"
        )

        business_customer = await customer_sdk.create_customer(
            customer_number="CUS-2024-005",
            display_name="Business Customer 1",
            customer_type="business"
        )

        # Activate business customer
        await customer_sdk.activate_customer(business_customer["customer_id"])

        # List all customers
        all_customers = await customer_sdk.list_customers(limit=10)
        assert len(all_customers) >= 2

        # List only business customers
        business_customers = await customer_sdk.list_customers(
            customer_type="business",
            limit=10
        )
        assert len(business_customers) >= 1
        assert all(c["customer_type"] == "business" for c in business_customers)

        # List active customers
        active_customers = await customer_sdk.get_active_customers()
        assert len(active_customers) >= 1
        assert all(c["state"] == "active" for c in active_customers)

    @pytest.mark.asyncio
    async def test_update_customer(self, customer_sdk):
        """Test customer update functionality."""
        # Create customer
        customer = await customer_sdk.create_customer(
            customer_number="CUS-2024-006",
            display_name="Update Test Customer"
        )
        customer_id = customer["customer_id"]

        # Update customer
        updated_customer = await customer_sdk.update_customer(
            customer_id=customer_id,
            display_name="Updated Customer Name",
            tags=["updated", "premium"],
            custom_fields={"vip_status": True}
        )

        assert updated_customer["display_name"] == "Updated Customer Name"
        assert "updated" in updated_customer["tags"]
        assert updated_customer["custom_fields"]["vip_status"] is True


class TestIdentityAccountSDK:
    """Test identity account management functionality."""

    @pytest.fixture
    def account_sdk(self):
        """Create identity account SDK instance."""
        return IdentityAccountSDK(tenant_id="test-tenant-123")

    @pytest.mark.asyncio
    async def test_create_account(self, account_sdk):
        """Test account creation."""
        username = "john.smith"
        email = "john.smith@example.com"
        password = "SecurePassword123!"

        result = await account_sdk.create_account(
            username=username,
            email=email,
            password=password
        )

        assert result["username"] == username
        assert result["email"] == email
        assert result["status"] == AccountStatus.ACTIVE.value
        assert "account_id" in result
        assert "created_at" in result

    @pytest.mark.asyncio
    async def test_authenticate_user(self, account_sdk):
        """Test user authentication."""
        username = "auth.test"
        email = "auth.test@example.com"
        password = "TestPassword123!"

        # Create account
        account = await account_sdk.create_account(
            username=username,
            email=email,
            password=password
        )

        # Authenticate with username
        auth_result = await account_sdk.authenticate(username, password)

        assert auth_result["account_id"] == account["account_id"]
        assert auth_result["username"] == username
        assert auth_result["email"] == email

        # Authenticate with email
        email_auth_result = await account_sdk.authenticate(email, password)

        assert email_auth_result["account_id"] == account["account_id"]

    @pytest.mark.asyncio
    async def test_account_status_management(self, account_sdk):
        """Test account enable/disable functionality."""
        # Create account
        account = await account_sdk.create_account(
            username="status.test",
            email="status.test@example.com",
            password="Password123!"
        )
        account_id = account["account_id"]

        # Disable account
        disabled_account = await account_sdk.disable_account(account_id)
        assert disabled_account["status"] == AccountStatus.DISABLED.value

        # Enable account
        enabled_account = await account_sdk.enable_account(account_id)
        assert enabled_account["status"] == AccountStatus.ACTIVE.value

    @pytest.mark.asyncio
    async def test_password_management(self, account_sdk):
        """Test password change functionality."""
        # Create account
        account = await account_sdk.create_account(
            username="password.test",
            email="password.test@example.com",
            password="OldPassword123!"
        )
        account_id = account["account_id"]

        # Set new password
        new_password = "NewPassword456!"
        password_result = await account_sdk.set_password(account_id, new_password)

        assert password_result["account_id"] == account_id
        assert password_result["credential_type"] == "password"
        assert "credential_id" in password_result

        # Verify new password works
        auth_result = await account_sdk.authenticate(
            account["username"],
            new_password
        )
        assert auth_result["account_id"] == account_id

    @pytest.mark.asyncio
    async def test_mfa_factor_management(self, account_sdk):
        """Test MFA factor addition and verification."""
        # Create account
        account = await account_sdk.create_account(
            username="mfa.test",
            email="mfa.test@example.com",
            password="Password123!"
        )
        account_id = account["account_id"]

        # Add TOTP MFA factor
        totp_factor = await account_sdk.add_mfa_factor(
            account_id=account_id,
            factor_type="totp",
            factor_data={
                "secret": "JBSWY3DPEHPK3PXP",
                "issuer": "DotMac ISP",
                "account_name": account["email"]
            },
            name="Authenticator App"
        )

        assert totp_factor["account_id"] == account_id
        assert totp_factor["factor_type"] == MFAFactorType.TOTP.value
        assert totp_factor["name"] == "Authenticator App"
        assert totp_factor["is_verified"] is False

        # Add SMS MFA factor
        sms_factor = await account_sdk.add_mfa_factor(
            account_id=account_id,
            factor_type="sms",
            factor_data={
                "phone_number": "+1234567890"
            },
            name="Mobile Phone"
        )

        assert sms_factor["factor_type"] == MFAFactorType.SMS.value
        assert sms_factor["name"] == "Mobile Phone"

    @pytest.mark.asyncio
    async def test_get_account_by_identifiers(self, account_sdk):
        """Test retrieving accounts by username and email."""
        username = "lookup.test"
        email = "lookup.test@example.com"

        # Create account
        created_account = await account_sdk.create_account(
            username=username,
            email=email,
            password="Password123!"
        )

        # Get by username
        username_lookup = await account_sdk.get_account_by_username(username)
        assert username_lookup is not None
        assert username_lookup["account_id"] == created_account["account_id"]

        # Get by email
        email_lookup = await account_sdk.get_account_by_email(email)
        assert email_lookup is not None
        assert email_lookup["account_id"] == created_account["account_id"]

    @pytest.mark.asyncio
    async def test_list_accounts(self, account_sdk):
        """Test listing accounts for tenant."""
        # Create multiple accounts
        for i in range(3):
            await account_sdk.create_account(
                username=f"user{i}",
                email=f"user{i}@example.com",
                password="Password123!"
            )

        # List accounts
        accounts = await account_sdk.list_accounts(limit=10)

        assert len(accounts) >= 3
        assert all("account_id" in account for account in accounts)
        assert all("username" in account for account in accounts)
        assert all("email" in account for account in accounts)


class TestContactsSDK:
    """Test contact management functionality."""

    @pytest.fixture
    def contacts_sdk(self):
        """Create contacts SDK instance."""
        return ContactsSDK(tenant_id="test-tenant-123")

    @pytest.mark.asyncio
    async def test_create_contact(self, contacts_sdk):
        """Test contact creation."""
        contact = await contacts_sdk.create_contact(
            first_name="John",
            last_name="Smith",
            email="john.smith@example.com",
            phone="+1234567890",
            contact_type="primary"
        )

        assert contact["first_name"] == "John"
        assert contact["last_name"] == "Smith"
        assert contact["email"] == "john.smith@example.com"
        assert contact["phone"] == "+1234567890"
        assert contact["contact_type"] == "primary"
        assert "contact_id" in contact

    @pytest.mark.asyncio
    async def test_update_contact(self, contacts_sdk):
        """Test contact update functionality."""
        # Create contact
        contact = await contacts_sdk.create_contact(
            first_name="Jane",
            last_name="Doe",
            email="jane.doe@example.com"
        )
        contact_id = contact["contact_id"]

        # Update contact
        updated_contact = await contacts_sdk.update_contact(
            contact_id=contact_id,
            phone="+9876543210",
            contact_type="billing",
            preferred_contact_method="phone"
        )

        assert updated_contact["phone"] == "+9876543210"
        assert updated_contact["contact_type"] == "billing"
        assert updated_contact["preferred_contact_method"] == "phone"

    @pytest.mark.asyncio
    async def test_search_contacts(self, contacts_sdk):
        """Test contact search functionality."""
        # Create multiple contacts
        await contacts_sdk.create_contact(
            first_name="Alice",
            last_name="Johnson",
            email="alice.johnson@example.com"
        )

        await contacts_sdk.create_contact(
            first_name="Bob",
            last_name="Johnson",
            email="bob.johnson@example.com"
        )

        # Search by last name
        johnson_contacts = await contacts_sdk.search_contacts(
            search_query="Johnson",
            search_fields=["last_name"]
        )

        assert len(johnson_contacts) >= 2
        assert all("Johnson" in contact["last_name"] for contact in johnson_contacts)

        # Search by email domain
        example_contacts = await contacts_sdk.search_contacts(
            search_query="example.com",
            search_fields=["email"]
        )

        assert len(example_contacts) >= 2


class TestUserProfileSDK:
    """Test user profile management functionality."""

    @pytest.fixture
    def profile_sdk(self):
        """Create user profile SDK instance."""
        return UserProfileSDK(tenant_id="test-tenant-123")

    @pytest.mark.asyncio
    async def test_create_user_profile(self, profile_sdk):
        """Test user profile creation."""
        profile = await profile_sdk.create_user_profile(
            first_name="John",
            last_name="Smith",
            display_name="John S.",
            email="john.smith@example.com",
            phone="+1234567890",
            timezone="America/New_York",
            locale="en_US"
        )

        assert profile["first_name"] == "John"
        assert profile["last_name"] == "Smith"
        assert profile["display_name"] == "John S."
        assert profile["email"] == "john.smith@example.com"
        assert profile["timezone"] == "America/New_York"
        assert profile["locale"] == "en_US"
        assert "profile_id" in profile

    @pytest.mark.asyncio
    async def test_update_profile_preferences(self, profile_sdk):
        """Test profile preferences update."""
        # Create profile
        profile = await profile_sdk.create_user_profile(
            first_name="Jane",
            last_name="Doe",
            email="jane.doe@example.com"
        )
        profile_id = profile["profile_id"]

        # Update preferences
        updated_profile = await profile_sdk.update_profile_preferences(
            profile_id=profile_id,
            email_notifications=True,
            sms_notifications=False,
            marketing_emails=True,
            language="es",
            timezone="America/Los_Angeles"
        )

        assert updated_profile["preferences"]["email_notifications"] is True
        assert updated_profile["preferences"]["sms_notifications"] is False
        assert updated_profile["preferences"]["marketing_emails"] is True
        assert updated_profile["language"] == "es"
        assert updated_profile["timezone"] == "America/Los_Angeles"

    @pytest.mark.asyncio
    async def test_profile_avatar_management(self, profile_sdk):
        """Test profile avatar upload and management."""
        # Create profile
        profile = await profile_sdk.create_user_profile(
            first_name="Avatar",
            last_name="Test",
            email="avatar.test@example.com"
        )
        profile_id = profile["profile_id"]

        # Upload avatar
        avatar_result = await profile_sdk.upload_avatar(
            profile_id=profile_id,
            avatar_data=b"fake_image_data",
            content_type="image/jpeg",
            filename="avatar.jpg"
        )

        assert avatar_result["profile_id"] == profile_id
        assert avatar_result["avatar_url"] is not None
        assert avatar_result["content_type"] == "image/jpeg"

        # Get updated profile
        updated_profile = await profile_sdk.get_user_profile(profile_id)
        assert updated_profile["avatar_url"] is not None


class TestCustomerPortalSDK:
    """Test customer portal functionality."""

    @pytest.fixture
    def portal_sdk(self):
        """Create customer portal SDK instance."""
        return CustomerPortalSDK(tenant_id="test-tenant-123")

    @pytest.mark.asyncio
    async def test_create_portal_session(self, portal_sdk):
        """Test portal session creation."""
        customer_id = str(uuid4())
        account_id = str(uuid4())

        session = await portal_sdk.create_portal_session(
            customer_id=customer_id,
            account_id=account_id,
            session_type="customer_dashboard",
            permissions=["view_bills", "manage_services", "update_profile"]
        )

        assert session["customer_id"] == customer_id
        assert session["account_id"] == account_id
        assert session["session_type"] == "customer_dashboard"
        assert "view_bills" in session["permissions"]
        assert session["status"] == "active"
        assert "session_id" in session

    @pytest.mark.asyncio
    async def test_portal_quick_actions(self, portal_sdk):
        """Test portal quick actions functionality."""
        customer_id = str(uuid4())

        # Test service restart
        restart_result = await portal_sdk.restart_service(
            customer_id=customer_id,
            service_id=str(uuid4()),
            restart_type="soft"
        )

        assert restart_result["customer_id"] == customer_id
        assert restart_result["action"] == "restart_service"
        assert restart_result["status"] == "initiated"

        # Test speed test
        speed_test_result = await portal_sdk.initiate_speed_test(
            customer_id=customer_id,
            service_id=str(uuid4())
        )

        assert speed_test_result["customer_id"] == customer_id
        assert speed_test_result["test_type"] == "speed_test"
        assert "test_id" in speed_test_result

    @pytest.mark.asyncio
    async def test_portal_notifications(self, portal_sdk):
        """Test portal notification system."""
        customer_id = str(uuid4())

        # Create notification
        notification = await portal_sdk.create_notification(
            customer_id=customer_id,
            title="Service Maintenance",
            message="Scheduled maintenance on your internet service tonight from 2-4 AM",
            notification_type="maintenance",
            priority="medium"
        )

        assert notification["customer_id"] == customer_id
        assert notification["title"] == "Service Maintenance"
        assert notification["notification_type"] == "maintenance"
        assert notification["priority"] == "medium"
        assert notification["status"] == "unread"

        # Mark as read
        read_result = await portal_sdk.mark_notification_read(
            customer_id=customer_id,
            notification_id=notification["notification_id"]
        )

        assert read_result["status"] == "read"


class TestConsentPreferencesSDK:
    """Test consent and preferences management."""

    @pytest.fixture
    def consent_sdk(self):
        """Create consent preferences SDK instance."""
        return ConsentPreferencesSDK(tenant_id="test-tenant-123")

    @pytest.mark.asyncio
    async def test_record_consent(self, consent_sdk):
        """Test consent recording."""
        customer_id = str(uuid4())

        consent = await consent_sdk.record_consent(
            customer_id=customer_id,
            consent_type="marketing_emails",
            consent_given=True,
            consent_method="web_form",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 (Test Browser)"
        )

        assert consent["customer_id"] == customer_id
        assert consent["consent_type"] == "marketing_emails"
        assert consent["consent_given"] is True
        assert consent["consent_method"] == "web_form"
        assert consent["ip_address"] == "192.168.1.100"
        assert "consent_id" in consent

    @pytest.mark.asyncio
    async def test_update_preferences(self, consent_sdk):
        """Test preferences update."""
        customer_id = str(uuid4())

        # Set initial preferences
        preferences = await consent_sdk.update_preferences(
            customer_id=customer_id,
            preferences={
                "email_notifications": True,
                "sms_notifications": False,
                "marketing_calls": False,
                "newsletter": True,
                "service_updates": True
            }
        )

        assert preferences["customer_id"] == customer_id
        assert preferences["preferences"]["email_notifications"] is True
        assert preferences["preferences"]["sms_notifications"] is False
        assert preferences["preferences"]["marketing_calls"] is False

        # Update specific preference
        updated_preferences = await consent_sdk.update_preferences(
            customer_id=customer_id,
            preferences={
                "sms_notifications": True,
                "marketing_calls": True
            }
        )

        assert updated_preferences["preferences"]["sms_notifications"] is True
        assert updated_preferences["preferences"]["marketing_calls"] is True
        assert updated_preferences["preferences"]["email_notifications"] is True  # Should remain unchanged

    @pytest.mark.asyncio
    async def test_consent_withdrawal(self, consent_sdk):
        """Test consent withdrawal."""
        customer_id = str(uuid4())

        # Record initial consent
        consent = await consent_sdk.record_consent(
            customer_id=customer_id,
            consent_type="data_processing",
            consent_given=True,
            consent_method="web_form"
        )

        # Withdraw consent
        withdrawal = await consent_sdk.withdraw_consent(
            customer_id=customer_id,
            consent_type="data_processing",
            withdrawal_method="customer_request",
            reason="No longer interested"
        )

        assert withdrawal["customer_id"] == customer_id
        assert withdrawal["consent_type"] == "data_processing"
        assert withdrawal["withdrawal_method"] == "customer_request"
        assert withdrawal["reason"] == "No longer interested"
        assert withdrawal["consent_given"] is False

    @pytest.mark.asyncio
    async def test_consent_history(self, consent_sdk):
        """Test consent history tracking."""
        customer_id = str(uuid4())

        # Record multiple consent events
        await consent_sdk.record_consent(
            customer_id=customer_id,
            consent_type="terms_of_service",
            consent_given=True,
            consent_method="signup"
        )

        await consent_sdk.record_consent(
            customer_id=customer_id,
            consent_type="privacy_policy",
            consent_given=True,
            consent_method="signup"
        )

        await consent_sdk.withdraw_consent(
            customer_id=customer_id,
            consent_type="terms_of_service",
            withdrawal_method="customer_request"
        )

        # Get consent history
        history = await consent_sdk.get_consent_history(customer_id)

        assert len(history) >= 3  # 2 consents + 1 withdrawal
        assert any(event["consent_type"] == "terms_of_service" for event in history)
        assert any(event["consent_type"] == "privacy_policy" for event in history)
        assert any(event["consent_given"] is False for event in history)  # Withdrawal


# Integration tests
class TestIdentityIntegration:
    """Test integration between identity SDKs."""

    @pytest.mark.asyncio
    async def test_customer_account_integration(self):
        """Test integration between customer and account management."""
        customer_sdk = CustomerManagementSDK(tenant_id="test-tenant")
        account_sdk = IdentityAccountSDK(tenant_id="test-tenant")

        # Create customer
        customer = await customer_sdk.create_customer(
            customer_number="INT-001",
            display_name="Integration Test Customer",
            customer_type="residential"
        )

        # Create account for customer
        account = await account_sdk.create_account(
            username="integration.test",
            email="integration.test@example.com",
            password="Password123!",
            customer_id=customer["customer_id"]
        )

        assert account["username"] == "integration.test"
        assert account["status"] == AccountStatus.ACTIVE.value

        # Activate customer
        activated_customer = await customer_sdk.activate_customer(
            customer["customer_id"]
        )

        assert activated_customer["state"] == CustomerState.ACTIVE.value

    @pytest.mark.asyncio
    async def test_profile_account_integration(self):
        """Test integration between profile and account management."""
        account_sdk = IdentityAccountSDK(tenant_id="test-tenant")
        profile_sdk = UserProfileSDK(tenant_id="test-tenant")

        # Create account
        account = await account_sdk.create_account(
            username="profile.integration",
            email="profile.integration@example.com",
            password="Password123!"
        )

        # Create profile for account
        profile = await profile_sdk.create_user_profile(
            account_id=account["account_id"],
            first_name="Profile",
            last_name="Integration",
            email=account["email"],
            timezone="America/New_York"
        )

        assert profile["first_name"] == "Profile"
        assert profile["last_name"] == "Integration"
        assert profile["email"] == account["email"]

        # Update account with profile reference
        updated_account = await account_sdk.update_account(
            account["account_id"],
            profile_id=profile["profile_id"]
        )

        assert updated_account["profile_id"] == profile["profile_id"]

    @pytest.mark.asyncio
    async def test_customer_portal_integration(self):
        """Test customer portal with customer and account data."""
        customer_sdk = CustomerManagementSDK(tenant_id="test-tenant")
        account_sdk = IdentityAccountSDK(tenant_id="test-tenant")
        portal_sdk = CustomerPortalSDK(tenant_id="test-tenant")
        consent_sdk = ConsentPreferencesSDK(tenant_id="test-tenant")

        # Create customer and account
        customer = await customer_sdk.create_customer(
            customer_number="PORTAL-001",
            display_name="Portal Test Customer"
        )

        account = await account_sdk.create_account(
            username="portal.test",
            email="portal.test@example.com",
            password="Password123!"
        )

        # Activate customer
        await customer_sdk.activate_customer(customer["customer_id"])

        # Create portal session
        session = await portal_sdk.create_portal_session(
            customer_id=customer["customer_id"],
            account_id=account["account_id"],
            session_type="customer_dashboard"
        )

        assert session["customer_id"] == customer["customer_id"]
        assert session["account_id"] == account["account_id"]

        # Record consent through portal
        consent = await consent_sdk.record_consent(
            customer_id=customer["customer_id"],
            consent_type="portal_terms",
            consent_given=True,
            consent_method="portal_login"
        )

        assert consent["customer_id"] == customer["customer_id"]
        assert consent["consent_given"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
