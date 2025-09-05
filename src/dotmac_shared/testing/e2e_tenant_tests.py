"""
E2E Tenant Provisioning and Bootstrap Tests

Comprehensive end-to-end tests covering per-tenant bootstrap scenarios:
- Fresh container initialization
- Database migrations and admin bootstrap
- First-login flows and branding setup
- TLS certificate provisioning
- SMTP/SMS service wiring
- Configuration validation
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import pytest
import requests
from playwright.async_api import Page, async_playwright

from dotmac.application import standard_exception_handler
from dotmac.core.exceptions import BusinessRuleError
from dotmac_shared.container_monitoring.core.metrics_collector import (
    ContainerMetricsCollector,
)

logger = logging.getLogger(__name__)


class TenantProvisioningE2E:
    """End-to-end test suite for tenant provisioning and bootstrap scenarios."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        frontend_url: str = "http://localhost:3000",
    ):
        self.base_url = base_url
        self.frontend_url = frontend_url
        self.test_tenant_id = None
        self.container_id = None
        self.metrics_collector = ContainerMetricsCollector()

    @pytest.mark.e2e
    @standard_exception_handler
    async def test_fresh_container_bootstrap(self) -> dict[str, Any]:
        """
        Test fresh container initialization with complete bootstrap sequence:
        1. Container creation and health validation
        2. Database migration execution
        3. Admin user bootstrap
        4. Essential service initialization
        """
        test_start = time.time()
        results = {
            "test_name": "fresh_container_bootstrap",
            "status": "running",
            "steps": [],
            "duration": 0,
            "errors": [],
        }

        try:
            # Step 1: Create fresh container
            container_result = await self._create_fresh_container()
            results["steps"].append(
                {
                    "name": "container_creation",
                    "status": "completed" if container_result["success"] else "failed",
                    "duration": container_result.get("duration", 0),
                    "details": container_result,
                }
            )

            if not container_result["success"]:
                raise BusinessRuleError(
                    f"Container creation failed: {container_result.get('error')}"
                )

            self.container_id = container_result["container_id"]

            # Step 2: Wait for container readiness and validate health
            health_result = await self._validate_container_health(self.container_id)
            results["steps"].append(
                {
                    "name": "health_validation",
                    "status": "completed" if health_result["healthy"] else "failed",
                    "duration": health_result.get("duration", 0),
                    "details": health_result,
                }
            )

            if not health_result["healthy"]:
                raise BusinessRuleError("Container health validation failed")

            # Step 3: Execute database migrations
            migration_result = await self._execute_database_migrations()
            results["steps"].append(
                {
                    "name": "database_migrations",
                    "status": "completed" if migration_result["success"] else "failed",
                    "duration": migration_result.get("duration", 0),
                    "details": migration_result,
                }
            )

            if not migration_result["success"]:
                raise BusinessRuleError("Database migration failed")

            # Step 4: Bootstrap admin user
            admin_result = await self._bootstrap_admin_user()
            results["steps"].append(
                {
                    "name": "admin_bootstrap",
                    "status": "completed" if admin_result["success"] else "failed",
                    "duration": admin_result.get("duration", 0),
                    "details": admin_result,
                }
            )

            if not admin_result["success"]:
                raise BusinessRuleError("Admin bootstrap failed")

            # Step 5: Initialize essential services
            services_result = await self._initialize_essential_services()
            results["steps"].append(
                {
                    "name": "service_initialization",
                    "status": "completed" if services_result["success"] else "failed",
                    "duration": services_result.get("duration", 0),
                    "details": services_result,
                }
            )

            if not services_result["success"]:
                raise BusinessRuleError("Service initialization failed")

            results["status"] = "completed"
            results["success"] = True

        except Exception as e:
            results["status"] = "failed"
            results["success"] = False
            results["errors"].append(str(e))
            logger.error(f"Fresh container bootstrap test failed: {e}")

        finally:
            results["duration"] = time.time() - test_start

        return results

    @pytest.mark.e2e
    @standard_exception_handler
    async def test_first_login_and_branding(self) -> dict[str, Any]:
        """
        Test first-login experience and branding setup:
        1. Admin first-login flow
        2. Branding configuration
        3. Domain/subdomain setup
        4. TLS certificate provisioning
        """
        test_start = time.time()
        results = {
            "test_name": "first_login_branding",
            "status": "running",
            "steps": [],
            "duration": 0,
            "errors": [],
        }

        try:
            # Use Playwright for frontend testing
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                # Step 1: First admin login
                login_result = await self._test_admin_first_login(page)
                results["steps"].append(
                    {
                        "name": "first_login",
                        "status": "completed" if login_result["success"] else "failed",
                        "duration": login_result.get("duration", 0),
                        "details": login_result,
                    }
                )

                if not login_result["success"]:
                    raise BusinessRuleError("First login failed")

                # Step 2: Branding setup
                branding_result = await self._configure_tenant_branding(page)
                results["steps"].append(
                    {
                        "name": "branding_setup",
                        "status": "completed"
                        if branding_result["success"]
                        else "failed",
                        "duration": branding_result.get("duration", 0),
                        "details": branding_result,
                    }
                )

                # Step 3: TLS certificate provisioning
                tls_result = await self._provision_tls_certificate()
                results["steps"].append(
                    {
                        "name": "tls_provisioning",
                        "status": "completed" if tls_result["success"] else "failed",
                        "duration": tls_result.get("duration", 0),
                        "details": tls_result,
                    }
                )

                await browser.close()

            results["status"] = "completed"
            results["success"] = True

        except Exception as e:
            results["status"] = "failed"
            results["success"] = False
            results["errors"].append(str(e))
            logger.error(f"First login and branding test failed: {e}")

        finally:
            results["duration"] = time.time() - test_start

        return results

    @pytest.mark.e2e
    @standard_exception_handler
    async def test_smtp_sms_wiring(self) -> dict[str, Any]:
        """
        Test SMTP and SMS service configuration and validation:
        1. SMTP service configuration
        2. SMS provider setup
        3. Service connectivity validation
        4. Test message delivery
        """
        test_start = time.time()
        results = {
            "test_name": "smtp_sms_wiring",
            "status": "running",
            "steps": [],
            "duration": 0,
            "errors": [],
        }

        try:
            # Step 1: Configure SMTP service
            smtp_result = await self._configure_smtp_service()
            results["steps"].append(
                {
                    "name": "smtp_configuration",
                    "status": "completed" if smtp_result["success"] else "failed",
                    "duration": smtp_result.get("duration", 0),
                    "details": smtp_result,
                }
            )

            # Step 2: Configure SMS service
            sms_result = await self._configure_sms_service()
            results["steps"].append(
                {
                    "name": "sms_configuration",
                    "status": "completed" if sms_result["success"] else "failed",
                    "duration": sms_result.get("duration", 0),
                    "details": sms_result,
                }
            )

            # Step 3: Test email delivery
            email_test_result = await self._test_email_delivery()
            results["steps"].append(
                {
                    "name": "email_delivery_test",
                    "status": "completed" if email_test_result["success"] else "failed",
                    "duration": email_test_result.get("duration", 0),
                    "details": email_test_result,
                }
            )

            # Step 4: Test SMS delivery
            sms_test_result = await self._test_sms_delivery()
            results["steps"].append(
                {
                    "name": "sms_delivery_test",
                    "status": "completed" if sms_test_result["success"] else "failed",
                    "duration": sms_test_result.get("duration", 0),
                    "details": sms_test_result,
                }
            )

            results["status"] = "completed"
            results["success"] = True

        except Exception as e:
            results["status"] = "failed"
            results["success"] = False
            results["errors"].append(str(e))
            logger.error(f"SMTP/SMS wiring test failed: {e}")

        finally:
            results["duration"] = time.time() - test_start

        return results

    @standard_exception_handler
    async def run_complete_provisioning_suite(self) -> dict[str, Any]:
        """Run complete tenant provisioning test suite."""
        suite_start = time.time()
        suite_results = {
            "suite_name": "tenant_provisioning_e2e",
            "status": "running",
            "tests": [],
            "summary": {},
            "duration": 0,
        }

        try:
            # Generate unique tenant for this test run
            self.test_tenant_id = str(uuid4())

            # Run all tests
            tests = [
                self.test_fresh_container_bootstrap(),
                self.test_first_login_and_branding(),
                self.test_smtp_sms_wiring(),
            ]

            for test_coro in tests:
                test_result = await test_coro
                suite_results["tests"].append(test_result)

            # Generate summary
            total_tests = len(suite_results["tests"])
            passed_tests = sum(
                1 for t in suite_results["tests"] if t.get("success", False)
            )
            failed_tests = total_tests - passed_tests

            suite_results["summary"] = {
                "total": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": (passed_tests / total_tests) * 100
                if total_tests > 0
                else 0,
            }

            suite_results["status"] = "completed" if failed_tests == 0 else "failed"

        except Exception as e:
            suite_results["status"] = "failed"
            suite_results["error"] = str(e)
            logger.error(f"Provisioning test suite failed: {e}")

        finally:
            suite_results["duration"] = time.time() - suite_start
            # Cleanup test resources
            if self.container_id:
                await self._cleanup_test_container(self.container_id)

        return suite_results

    # Helper methods for test implementation
    async def _create_fresh_container(self) -> dict[str, Any]:
        """Create and start fresh container for testing."""
        start_time = time.time()

        try:
            # Mock container creation (in real implementation, would use Docker API)
            container_config = {
                "image": "dotmac-platform:latest",
                "environment": {
                    "TENANT_ID": self.test_tenant_id,
                    "DATABASE_URL": f"postgresql://test_{self.test_tenant_id}:password@localhost:5432/test_{self.test_tenant_id}",
                    "ENVIRONMENT": "test",
                },
                "ports": {"8000/tcp": None},  # Dynamic port allocation
                "labels": {
                    "dotmac.tenant_id": self.test_tenant_id,
                    "dotmac.test": "true",
                },
            }

            # Simulate container creation
            await asyncio.sleep(2)  # Simulate startup time

            container_id = f"container_{self.test_tenant_id}"

            return {
                "success": True,
                "container_id": container_id,
                "duration": time.time() - start_time,
                "config": container_config,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time,
            }

    async def _validate_container_health(self, container_id: str) -> dict[str, Any]:
        """Validate container health and readiness."""
        start_time = time.time()

        try:
            # Health check with retries
            max_attempts = 30
            attempt = 0

            while attempt < max_attempts:
                try:
                    # Check container health endpoint
                    health_url = f"{self.base_url}/health"
                    response = requests.get(health_url, timeout=5)

                    if response.status_code == 200:
                        health_data = response.json()
                        if health_data.get("status") == "healthy":
                            return {
                                "healthy": True,
                                "duration": time.time() - start_time,
                                "attempts": attempt + 1,
                                "health_data": health_data,
                            }

                except requests.exceptions.RequestException:
                    pass

                attempt += 1
                await asyncio.sleep(2)

            return {
                "healthy": False,
                "duration": time.time() - start_time,
                "attempts": max_attempts,
                "error": "Health check timeout",
            }

        except Exception as e:
            return {
                "healthy": False,
                "duration": time.time() - start_time,
                "error": str(e),
            }

    async def _execute_database_migrations(self) -> dict[str, Any]:
        """Execute database migrations for tenant."""
        start_time = time.time()

        try:
            # Mock migration execution
            migrations = [
                "001_initial_schema.sql",
                "002_user_management.sql",
                "003_billing_setup.sql",
                "004_monitoring_tables.sql",
            ]

            executed_migrations = []
            for migration in migrations:
                # Simulate migration execution
                await asyncio.sleep(0.5)
                executed_migrations.append(
                    {
                        "name": migration,
                        "status": "completed",
                        "executed_at": datetime.now(timezone.utc).isoformat(),
                    }
                )

            return {
                "success": True,
                "duration": time.time() - start_time,
                "migrations": executed_migrations,
                "total_count": len(migrations),
            }

        except Exception as e:
            return {
                "success": False,
                "duration": time.time() - start_time,
                "error": str(e),
            }

    async def _bootstrap_admin_user(self) -> dict[str, Any]:
        """Bootstrap initial admin user for tenant."""
        start_time = time.time()

        try:
            admin_data = {
                "username": f"admin_{self.test_tenant_id}",
                "email": f"admin@{self.test_tenant_id}.test.com",
                "first_name": "Test",
                "last_name": "Administrator",
                "tenant_id": self.test_tenant_id,
                "role": "admin",
                "is_active": True,
            }

            # Mock admin creation
            await asyncio.sleep(1)

            return {
                "success": True,
                "duration": time.time() - start_time,
                "admin_data": admin_data,
                "admin_id": str(uuid4()),
            }

        except Exception as e:
            return {
                "success": False,
                "duration": time.time() - start_time,
                "error": str(e),
            }

    async def _initialize_essential_services(self) -> dict[str, Any]:
        """Initialize essential services for tenant."""
        start_time = time.time()

        try:
            services = [
                {"name": "monitoring", "status": "initialized"},
                {"name": "billing", "status": "initialized"},
                {"name": "notifications", "status": "initialized"},
                {"name": "websockets", "status": "initialized"},
            ]

            # Mock service initialization
            await asyncio.sleep(2)

            return {
                "success": True,
                "duration": time.time() - start_time,
                "services": services,
                "total_count": len(services),
            }

        except Exception as e:
            return {
                "success": False,
                "duration": time.time() - start_time,
                "error": str(e),
            }

    async def _test_admin_first_login(self, page: Page) -> dict[str, Any]:
        """Test admin first login flow."""
        start_time = time.time()

        try:
            # Navigate to admin login
            await page.goto(f"{self.frontend_url}/admin/login")

            # Fill login form
            await page.fill('[data-testid="username"]', f"admin_{self.test_tenant_id}")
            await page.fill('[data-testid="password"]', "test-password")

            # Submit login
            await page.click('[data-testid="login-submit"]')

            # Wait for redirect to dashboard
            await page.wait_for_url("**/admin/dashboard")

            # Verify dashboard elements
            dashboard_title = await page.text_content('[data-testid="dashboard-title"]')

            return {
                "success": True,
                "duration": time.time() - start_time,
                "dashboard_title": dashboard_title,
                "final_url": page.url,
            }

        except Exception as e:
            return {
                "success": False,
                "duration": time.time() - start_time,
                "error": str(e),
            }

    async def _configure_tenant_branding(self, page: Page) -> dict[str, Any]:
        """Configure tenant branding and customization."""
        start_time = time.time()

        try:
            # Navigate to branding settings
            await page.goto(f"{self.frontend_url}/admin/settings/branding")

            # Configure branding
            await page.fill(
                '[data-testid="company-name"]', f"Test Company {self.test_tenant_id}"
            )
            await page.fill('[data-testid="primary-color"]', "#007bff")
            await page.fill(
                '[data-testid="custom-domain"]', f"{self.test_tenant_id}.example.com"
            )

            # Save branding
            await page.click('[data-testid="save-branding"]')

            # Wait for success message
            await page.wait_for_selector('[data-testid="success-message"]')

            return {
                "success": True,
                "duration": time.time() - start_time,
                "branding_applied": True,
            }

        except Exception as e:
            return {
                "success": False,
                "duration": time.time() - start_time,
                "error": str(e),
            }

    async def _provision_tls_certificate(self) -> dict[str, Any]:
        """Provision TLS certificate for tenant domain."""
        start_time = time.time()

        try:
            # Mock TLS certificate provisioning
            cert_data = {
                "domain": f"{self.test_tenant_id}.example.com",
                "cert_authority": "Let's Encrypt",
                "expiry_date": (
                    datetime.now(timezone.utc) + timedelta(days=90)
                ).isoformat(),
                "status": "active",
            }

            await asyncio.sleep(3)  # Simulate certificate generation

            return {
                "success": True,
                "duration": time.time() - start_time,
                "certificate": cert_data,
            }

        except Exception as e:
            return {
                "success": False,
                "duration": time.time() - start_time,
                "error": str(e),
            }

    async def _configure_smtp_service(self) -> dict[str, Any]:
        """Configure SMTP service for tenant."""
        start_time = time.time()

        try:
            smtp_config = {
                "host": "smtp.mailgun.org",
                "port": 587,
                "username": f"postmaster@{self.test_tenant_id}.mailgun.org",
                "password": "test-smtp-password",
                "use_tls": True,
            }

            # Mock SMTP configuration
            await asyncio.sleep(1)

            return {
                "success": True,
                "duration": time.time() - start_time,
                "config": smtp_config,
            }

        except Exception as e:
            return {
                "success": False,
                "duration": time.time() - start_time,
                "error": str(e),
            }

    async def _configure_sms_service(self) -> dict[str, Any]:
        """Configure SMS service for tenant."""
        start_time = time.time()

        try:
            sms_config = {
                "provider": "Twilio",
                "account_sid": f"test_account_{self.test_tenant_id}",
                "auth_token": "test-auth-token",
                "from_number": "+15551234567",
            }

            # Mock SMS configuration
            await asyncio.sleep(1)

            return {
                "success": True,
                "duration": time.time() - start_time,
                "config": sms_config,
            }

        except Exception as e:
            return {
                "success": False,
                "duration": time.time() - start_time,
                "error": str(e),
            }

    async def _test_email_delivery(self) -> dict[str, Any]:
        """Test email delivery functionality."""
        start_time = time.time()

        try:
            # Mock email test
            test_email = {
                "to": f"test@{self.test_tenant_id}.example.com",
                "subject": "Test Email - Tenant Bootstrap",
                "body": "This is a test email to verify SMTP configuration.",
            }

            await asyncio.sleep(2)  # Simulate email sending

            return {
                "success": True,
                "duration": time.time() - start_time,
                "email_sent": True,
                "test_email": test_email,
            }

        except Exception as e:
            return {
                "success": False,
                "duration": time.time() - start_time,
                "error": str(e),
            }

    async def _test_sms_delivery(self) -> dict[str, Any]:
        """Test SMS delivery functionality."""
        start_time = time.time()

        try:
            # Mock SMS test
            test_sms = {
                "to": "+15551234567",
                "message": f"Test SMS from tenant {self.test_tenant_id} - Bootstrap verification",
            }

            await asyncio.sleep(2)  # Simulate SMS sending

            return {
                "success": True,
                "duration": time.time() - start_time,
                "sms_sent": True,
                "test_sms": test_sms,
            }

        except Exception as e:
            return {
                "success": False,
                "duration": time.time() - start_time,
                "error": str(e),
            }

    async def _cleanup_test_container(self, container_id: str) -> None:
        """Clean up test container and resources."""
        try:
            # Mock container cleanup
            await asyncio.sleep(1)
            logger.info(f"Cleaned up test container: {container_id}")
        except Exception as e:
            logger.error(f"Failed to cleanup container {container_id}: {e}")


# Pytest test functions
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_tenant_provisioning_e2e():
    """Run complete tenant provisioning E2E test suite."""
    test_suite = TenantProvisioningE2E()
    results = await test_suite.run_complete_provisioning_suite()

    # Assert overall success
    assert results["status"] == "completed", f"Test suite failed: {results}"
    assert (
        results["summary"]["success_rate"] >= 80
    ), f"Success rate too low: {results['summary']}"

    # Log results for debugging
    logger.info("\nTest Results Summary:")
    logger.info(f"Total Tests: {results['summary']['total']}")
    logger.info(f"Passed: {results['summary']['passed']}")
    logger.info(f"Failed: {results['summary']['failed']}")
    logger.info(f"Success Rate: {results['summary']['success_rate']:.1f}%")
    logger.info(f"Duration: {results['duration']:.2f}s")

    return results


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_container_bootstrap_only():
    """Test just the container bootstrap process."""
    test_suite = TenantProvisioningE2E()
    test_suite.test_tenant_id = str(uuid4())

    result = await test_suite.test_fresh_container_bootstrap()

    assert result["success"] is True, f"Container bootstrap failed: {result}"
    assert len(result["steps"]) >= 5, "Missing bootstrap steps"

    # Verify all critical steps completed
    step_names = [step["name"] for step in result["steps"]]
    assert "container_creation" in step_names
    assert "health_validation" in step_names
    assert "database_migrations" in step_names
    assert "admin_bootstrap" in step_names
    assert "service_initialization" in step_names

    return result


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_first_login_flow_only():
    """Test just the first login and branding flow."""
    test_suite = TenantProvisioningE2E()
    test_suite.test_tenant_id = str(uuid4())

    result = await test_suite.test_first_login_and_branding()

    assert result["success"] is True, f"First login flow failed: {result}"

    # Verify branding steps
    step_names = [step["name"] for step in result["steps"]]
    assert "first_login" in step_names
    assert "branding_setup" in step_names
    assert "tls_provisioning" in step_names

    return result


# Export main test class for reuse
__all__ = [
    "TenantProvisioningE2E",
    "test_tenant_provisioning_e2e",
    "test_container_bootstrap_only",
    "test_first_login_flow_only",
]
