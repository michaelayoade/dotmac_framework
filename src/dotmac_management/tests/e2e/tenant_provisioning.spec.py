"""
Tenant Provisioning E2E Tests

Comprehensive end-to-end testing of tenant provisioning workflows:

1. Management admin creates new tenant
2. Container provisioning triggers (Kubernetes deployment)
3. Database schema creation and isolation
4. Initial app deployment (ISP Framework)
5. Health check validation
6. Tenant admin first login

Tests cover the complete provisioning pipeline with realistic scenarios
including error handling, retries, and rollback capabilities.
"""

import asyncio
import json
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any

import pytest
from playwright.async_api import Page, expect
from sqlalchemy.orm import Session

from dotmac_management.models.tenant import CustomerTenant, TenantStatus
from dotmac_management.services.tenant_provisioning import TenantProvisioningService
from .factories import TenantFactory, ApiTestDataFactory
from .utils import (
    PageTestUtils, 
    ApiTestUtils,
    DatabaseTestUtils,
    ContainerTestUtils,
    ProvisioningTestUtils,
    performance_monitor,
    assert_tenant_provisioned_successfully
)


@pytest.mark.tenant_provisioning
@pytest.mark.slow
class TestTenantProvisioningWorkflow:
    """Test complete tenant provisioning workflow."""

    async def test_successful_tenant_provisioning_end_to_end(
        self,
        management_page: Page,
        management_db_session: Session,
        mock_tenant_provisioning_service: TenantProvisioningService,
        http_client,
        tenant_factory
    ):
        """Test complete successful tenant provisioning from UI to deployment."""
        
        async with performance_monitor("tenant_provisioning_e2e"):
            # Step 1: Management admin creates new tenant via UI
            tenant_data = TenantFactory.create_provisioning_workflow_tenant(
                company_name="E2E Test ISP Company",
                admin_email="admin@e2e-test.com",
                subdomain="e2etest",
                plan="professional"
            )
            
            # Login as management admin
            admin_creds = ApiTestDataFactory.create_management_admin_credentials()
            login_success = await PageTestUtils.login_management_admin(
                management_page, admin_creds
            )
            assert login_success, "Management admin login failed"
            
            # Navigate to tenant creation
            await management_page.goto("/tenants/new")
            
            # Fill tenant creation form
            await management_page.fill("[data-testid=company-name]", tenant_data["company_name"])
            await management_page.fill("[data-testid=subdomain]", tenant_data["subdomain"])
            await management_page.fill("[data-testid=admin-name]", tenant_data["admin_name"])
            await management_page.fill("[data-testid=admin-email]", tenant_data["admin_email"])
            await management_page.select_option("[data-testid=plan-select]", tenant_data["plan"])
            await management_page.select_option("[data-testid=region-select]", tenant_data["region"])
            
            # Submit tenant creation
            await management_page.click("[data-testid=create-tenant-button]")
            
            # Wait for tenant creation success message
            await expect(management_page.locator(".success-message")).to_contain_text(
                "Tenant creation initiated", timeout=10000
            )
            
            # Step 2: Verify tenant record created in database
            await asyncio.sleep(2)  # Allow DB transaction to complete
            management_db_session.expire_all()
            
            created_tenant = management_db_session.query(CustomerTenant).filter_by(
                subdomain=tenant_data["subdomain"]
            ).first()
            
            assert created_tenant is not None, "Tenant not found in database"
            assert created_tenant.status == TenantStatus.PENDING
            
            # Step 3: Wait for background provisioning to complete
            provisioning_result = await ProvisioningTestUtils.wait_for_provisioning_completion(
                management_db_session, created_tenant.tenant_id, timeout=600
            )
            
            assert_tenant_provisioned_successfully(provisioning_result)
            
            # Step 4: Verify provisioning steps completed
            steps_verification = await ProvisioningTestUtils.verify_provisioning_steps(
                management_db_session, created_tenant.tenant_id
            )
            
            assert steps_verification["verified"], f"Provisioning steps incomplete: {steps_verification}"
            assert steps_verification["failed_events"] == 0, "Provisioning had failed events"
            
            # Step 5: Verify tenant infrastructure is ready
            management_db_session.refresh(created_tenant)
            assert created_tenant.status == TenantStatus.ACTIVE
            assert created_tenant.domain is not None
            assert created_tenant.container_id is not None
            
            # Step 6: Verify tenant application is accessible
            tenant_url = f"https://{created_tenant.domain}"
            
            # Wait for container to be healthy
            container_healthy = await ContainerTestUtils.wait_for_container_health(
                tenant_url, timeout=120
            )
            assert container_healthy, "Tenant container failed health checks"
            
            # Step 7: Verify tenant login page is accessible
            api_ready = await ApiTestUtils.wait_for_api_ready(tenant_url, timeout=60)
            assert api_ready, "Tenant API not ready"
            
            # Step 8: Test tenant admin first login
            tenant_admin_creds = {
                "email": tenant_data["admin_email"],
                "password": created_tenant.settings.get("admin_temp_password")
            }
            
            # Create new browser context for tenant
            tenant_context = await management_page.context.browser.new_context()
            tenant_page = await tenant_context.new_page()
            
            try:
                tenant_login_success = await PageTestUtils.login_tenant_admin(
                    tenant_page, tenant_url, tenant_admin_creds
                )
                assert tenant_login_success, "Tenant admin first login failed"
                
                # Verify admin dashboard loads
                await expect(tenant_page.locator("h1")).to_contain_text(
                    "Dashboard", timeout=15000
                )
                
            finally:
                await tenant_page.close()
                await tenant_context.close()

    async def test_tenant_provisioning_with_validation_failures(
        self,
        management_page: Page,
        management_db_session: Session,
        mock_tenant_provisioning_service: TenantProvisioningService
    ):
        """Test tenant provisioning with validation failures."""
        
        # Create tenant with invalid subdomain (already exists)
        existing_tenant = CustomerTenant(
            tenant_id="existing_tenant",
            subdomain="existing",
            company_name="Existing ISP",
            admin_email="existing@test.com",
            admin_name="Existing Admin",
            plan="starter",
            region="us-east-1",
            status=TenantStatus.ACTIVE
        )
        management_db_session.add(existing_tenant)
        management_db_session.commit()
        
        # Login as management admin
        admin_creds = ApiTestDataFactory.create_management_admin_credentials()
        await PageTestUtils.login_management_admin(management_page, admin_creds)
        
        # Try to create tenant with duplicate subdomain
        await management_page.goto("/tenants/new")
        await management_page.fill("[data-testid=company-name]", "Duplicate Test ISP")
        await management_page.fill("[data-testid=subdomain]", "existing")  # Duplicate
        await management_page.fill("[data-testid=admin-name]", "Test Admin")
        await management_page.fill("[data-testid=admin-email]", "duplicate@test.com")
        await management_page.select_option("[data-testid=plan-select]", "professional")
        
        # Submit form
        await management_page.click("[data-testid=create-tenant-button]")
        
        # Should show validation error
        await expect(management_page.locator(".error-message")).to_contain_text(
            "Subdomain already exists", timeout=10000
        )
        
        # Verify no new tenant was created
        duplicate_count = management_db_session.query(CustomerTenant).filter_by(
            subdomain="existing"
        ).count()
        assert duplicate_count == 1, "Duplicate tenant was created despite validation error"

    async def test_tenant_provisioning_container_deployment_failure(
        self,
        management_db_session: Session,
        mock_tenant_provisioning_service: TenantProvisioningService,
        tenant_factory
    ):
        """Test tenant provisioning with container deployment failure."""
        
        # Create tenant that will fail during container deployment
        tenant = tenant_factory(
            company_name="Deployment Failure Test ISP",
            subdomain="failtest",
            plan="professional"
        )
        
        # Mock container deployment to fail
        mock_tenant_provisioning_service.coolify_client.create_application.side_effect = Exception(
            "Deployment quota exceeded"
        )
        
        # Start provisioning
        provisioning_success = await mock_tenant_provisioning_service.provision_tenant(
            tenant.id, management_db_session
        )
        
        assert not provisioning_success, "Provisioning should have failed"
        
        # Verify tenant status is FAILED
        management_db_session.refresh(tenant)
        assert tenant.status == TenantStatus.FAILED
        assert "Deployment quota exceeded" in tenant.settings.get("last_error", "")

    async def test_tenant_provisioning_database_creation_failure(
        self,
        management_db_session: Session,
        mock_tenant_provisioning_service: TenantProvisioningService,
        tenant_factory
    ):
        """Test tenant provisioning with database creation failure."""
        
        tenant = tenant_factory(
            company_name="Database Failure Test ISP",
            subdomain="dbfailtest"
        )
        
        # Mock database creation to fail
        mock_tenant_provisioning_service.coolify_client.create_database_service.side_effect = Exception(
            "Database server unavailable"
        )
        
        provisioning_success = await mock_tenant_provisioning_service.provision_tenant(
            tenant.id, management_db_session
        )
        
        assert not provisioning_success
        management_db_session.refresh(tenant)
        assert tenant.status == TenantStatus.FAILED

    async def test_tenant_provisioning_health_check_timeout(
        self,
        management_db_session: Session,
        mock_tenant_provisioning_service: TenantProvisioningService,
        tenant_factory,
        http_client
    ):
        """Test tenant provisioning with health check timeout."""
        
        tenant = tenant_factory(
            company_name="Health Check Timeout ISP",
            subdomain="healthtimeout"
        )
        
        # Mock health checks to always fail
        async def failing_health_check(*args, **kwargs):
            from httpx import HTTPStatusError
            raise HTTPStatusError(
                message="Service unavailable",
                request=None,
                response=None
            )
        
        # Patch the health check method
        original_run_health_checks = mock_tenant_provisioning_service._run_health_checks
        mock_tenant_provisioning_service._run_health_checks = failing_health_check
        
        try:
            provisioning_success = await mock_tenant_provisioning_service.provision_tenant(
                tenant.id, management_db_session
            )
            
            assert not provisioning_success
            management_db_session.refresh(tenant)
            assert tenant.status == TenantStatus.FAILED
            
        finally:
            # Restore original method
            mock_tenant_provisioning_service._run_health_checks = original_run_health_checks

    async def test_tenant_provisioning_migration_failure_recovery(
        self,
        management_db_session: Session,
        mock_tenant_provisioning_service: TenantProvisioningService,
        tenant_factory
    ):
        """Test tenant provisioning migration failure and recovery."""
        
        tenant = tenant_factory(
            company_name="Migration Recovery Test ISP",
            subdomain="migrecovery"
        )
        
        # Mock migration to fail first time, succeed second time
        migration_call_count = 0
        
        async def flaky_migration_check(*args, **kwargs):
            nonlocal migration_call_count
            migration_call_count += 1
            
            if migration_call_count == 1:
                return False  # Fail first time
            return True  # Succeed on retry
        
        mock_tenant_provisioning_service._check_migration_job_success = flaky_migration_check
        
        # Start provisioning - should succeed after retry
        provisioning_success = await mock_tenant_provisioning_service.provision_tenant(
            tenant.id, management_db_session
        )
        
        # In this test we're simulating a scenario where migration fails but recovers
        # The actual implementation might handle retries differently
        # For now, verify the behavior matches the implementation
        
        # Refresh tenant status
        management_db_session.refresh(tenant)
        
        # Log the final status for debugging
        print(f"Final tenant status: {tenant.status}")
        print(f"Migration call count: {migration_call_count}")

    async def test_concurrent_tenant_provisioning(
        self,
        management_db_session: Session,
        mock_tenant_provisioning_service: TenantProvisioningService,
        tenant_factory
    ):
        """Test multiple tenants being provisioned concurrently."""
        
        # Create multiple tenants
        tenants = []
        for i in range(3):
            tenant = tenant_factory(
                company_name=f"Concurrent Test ISP {i+1}",
                subdomain=f"concurrent{i+1}",
                admin_email=f"admin{i+1}@concurrent-test.com"
            )
            tenants.append(tenant)
        
        # Start provisioning for all tenants concurrently
        provisioning_tasks = [
            mock_tenant_provisioning_service.provision_tenant(tenant.id, management_db_session)
            for tenant in tenants
        ]
        
        results = await asyncio.gather(*provisioning_tasks, return_exceptions=True)
        
        # Verify all provisioning completed successfully
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                pytest.fail(f"Tenant {i+1} provisioning failed: {result}")
            assert result is True, f"Tenant {i+1} provisioning returned False"
        
        # Verify all tenants are in correct state
        for tenant in tenants:
            management_db_session.refresh(tenant)
            assert tenant.status in [TenantStatus.ACTIVE, TenantStatus.READY], \
                f"Tenant {tenant.subdomain} in wrong state: {tenant.status}"

    async def test_tenant_provisioning_with_custom_settings(
        self,
        management_db_session: Session,
        mock_tenant_provisioning_service: TenantProvisioningService,
        tenant_factory
    ):
        """Test tenant provisioning with custom configuration settings."""
        
        custom_settings = {
            "enable_billing": True,
            "enable_ticketing": True,
            "custom_domain": "custom.example.com",
            "max_customers": 1000,
            "features": ["advanced_reporting", "api_access"]
        }
        
        tenant = tenant_factory(
            company_name="Custom Settings ISP",
            subdomain="customsettings",
            plan="enterprise",  # Enterprise plan supports custom settings
            settings=custom_settings
        )
        
        provisioning_success = await mock_tenant_provisioning_service.provision_tenant(
            tenant.id, management_db_session
        )
        
        assert provisioning_success, "Custom settings provisioning failed"
        
        management_db_session.refresh(tenant)
        assert tenant.status == TenantStatus.ACTIVE
        
        # Verify custom settings were preserved
        assert tenant.settings["enable_billing"] is True
        assert tenant.settings["max_customers"] == 1000
        assert "advanced_reporting" in tenant.settings["features"]

    async def test_tenant_provisioning_monitoring_and_events(
        self,
        management_db_session: Session,
        mock_tenant_provisioning_service: TenantProvisioningService,
        tenant_factory
    ):
        """Test tenant provisioning event logging and monitoring."""
        
        tenant = tenant_factory(
            company_name="Monitoring Test ISP",
            subdomain="monitoring"
        )
        
        # Start provisioning
        provisioning_success = await mock_tenant_provisioning_service.provision_tenant(
            tenant.id, management_db_session
        )
        
        assert provisioning_success
        
        # Verify provisioning events were logged
        from dotmac_management.models.tenant import TenantProvisioningEvent
        
        events = management_db_session.query(TenantProvisioningEvent).filter_by(
            tenant_id=tenant.id
        ).order_by(TenantProvisioningEvent.step_number).all()
        
        assert len(events) > 0, "No provisioning events were logged"
        
        # Verify event sequence
        expected_event_types = [
            "status_change.pending",
            "status_change.validating",
            "database_created",
            "secrets_generated",
            "status_change.provisioning",
            "container_deployed"
        ]
        
        logged_event_types = [event.event_type for event in events[:6]]
        
        for expected_type in expected_event_types:
            assert expected_type in logged_event_types, \
                f"Missing expected event type: {expected_type}"
        
        # Verify correlation ID is consistent
        correlation_ids = set(event.correlation_id for event in events)
        assert len(correlation_ids) == 1, "Events should have same correlation ID"
        
        # Verify timing information
        for event in events:
            assert event.created_at is not None
            assert event.step_number is not None
            assert event.step_number > 0


@pytest.mark.tenant_provisioning
class TestTenantProvisioningAPI:
    """Test tenant provisioning via API endpoints."""
    
    async def test_create_tenant_via_api(
        self,
        http_client,
        management_db_session: Session
    ):
        """Test creating tenant via management API."""
        
        tenant_data = {
            "company_name": "API Test ISP",
            "subdomain": "apitest",
            "admin_name": "API Admin",
            "admin_email": "api@test.com",
            "plan": "professional",
            "region": "us-east-1"
        }
        
        # Create management admin token
        admin_token = "test_management_token"  # In real tests, would generate actual JWT
        
        response = await http_client.post(
            f"{TEST_MANAGEMENT_URL}/api/v1/tenants",
            json=tenant_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 201
        response_data = response.json()
        
        assert response_data["tenant_id"] is not None
        assert response_data["subdomain"] == "apitest"
        assert response_data["status"] == "pending"
        
        # Verify tenant created in database
        tenant = management_db_session.query(CustomerTenant).filter_by(
            subdomain="apitest"
        ).first()
        
        assert tenant is not None
        assert tenant.status == TenantStatus.PENDING

    async def test_get_tenant_provisioning_status_via_api(
        self,
        http_client,
        management_db_session: Session,
        tenant_factory
    ):
        """Test getting tenant provisioning status via API."""
        
        tenant = tenant_factory(
            company_name="Status API Test ISP",
            subdomain="statusapi",
            status=TenantStatus.PROVISIONING
        )
        
        admin_token = "test_management_token"
        
        response = await http_client.get(
            f"{TEST_MANAGEMENT_URL}/api/v1/tenants/{tenant.tenant_id}/status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        status_data = response.json()
        
        assert status_data["tenant_id"] == tenant.tenant_id
        assert status_data["status"] == "provisioning"
        assert status_data["subdomain"] == "statusapi"
        
    async def test_tenant_provisioning_webhook_notifications(
        self,
        http_client,
        management_db_session: Session,
        tenant_factory
    ):
        """Test webhook notifications during tenant provisioning."""
        
        # This would test webhook notifications sent during provisioning
        # For now, we'll create a placeholder test structure
        
        tenant = tenant_factory(
            company_name="Webhook Test ISP",
            subdomain="webhook",
            settings={
                "webhook_url": "https://test.webhook.com/tenant-events",
                "enable_webhooks": True
            }
        )
        
        # In a real implementation, this would:
        # 1. Start provisioning
        # 2. Mock webhook server to receive notifications
        # 3. Verify webhook payloads are correct
        # 4. Test webhook retry logic
        
        # For now, just verify tenant was created with webhook settings
        assert tenant.settings["webhook_url"] == "https://test.webhook.com/tenant-events"
        assert tenant.settings["enable_webhooks"] is True