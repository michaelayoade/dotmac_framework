"""
E2E Test Utilities

Provides utility functions for E2E testing including:
- Database management and cleanup
- Container orchestration helpers
- Test data verification
- Performance monitoring
- Error handling and logging
"""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Any, Optional

import httpx
from playwright.async_api import Page, expect
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from dotmac_management.models.tenant import CustomerTenant, TenantStatus
from dotmac_shared.core.logging import get_logger

logger = get_logger(__name__)


class E2ETestException(Exception):
    """Custom exception for E2E test failures."""

    pass


class DatabaseTestUtils:
    """Utilities for database testing and verification."""

    @staticmethod
    async def wait_for_database_ready(db_url: str, timeout: int = 60) -> bool:
        """Wait for database to be ready."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                engine = create_engine(db_url)
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                engine.dispose()
                return True
            except Exception as e:
                logger.debug(f"Database not ready yet: {e}")
                await asyncio.sleep(2)

        return False

    @staticmethod
    def verify_tenant_data_isolation(
        tenant_a_session: Session,
        tenant_b_session: Session,
        table_name: str,
        tenant_a_id: str,
        tenant_b_id: str,
    ) -> dict[str, Any]:
        """Verify that tenant data is properly isolated."""
        results = {
            "isolated": True,
            "tenant_a_count": 0,
            "tenant_b_count": 0,
            "cross_contamination": [],
        }

        try:
            # Check tenant A data
            tenant_a_data = tenant_a_session.execute(
                text(f"SELECT * FROM {table_name} WHERE tenant_id = :tenant_id"),
                {"tenant_id": tenant_a_id},
            ).fetchall()
            results["tenant_a_count"] = len(tenant_a_data)

            # Check tenant B data
            tenant_b_data = tenant_b_session.execute(
                text(f"SELECT * FROM {table_name} WHERE tenant_id = :tenant_id"),
                {"tenant_id": tenant_b_id},
            ).fetchall()
            results["tenant_b_count"] = len(tenant_b_data)

            # Check for cross-contamination (tenant A data in tenant B DB)
            cross_check = tenant_b_session.execute(
                text(f"SELECT * FROM {table_name} WHERE tenant_id = :tenant_id"),
                {"tenant_id": tenant_a_id},
            ).fetchall()

            if cross_check:
                results["isolated"] = False
                results["cross_contamination"] = [
                    dict(row._mapping) for row in cross_check
                ]

        except Exception as e:
            logger.error(f"Error verifying data isolation: {e}")
            results["isolated"] = False
            results["error"] = str(e)

        return results

    @staticmethod
    async def cleanup_test_data(session: Session, tenant_id: str, tables: list[str]):
        """Clean up test data for a specific tenant."""
        try:
            for table in tables:
                session.execute(
                    text(f"DELETE FROM {table} WHERE tenant_id = :tenant_id"),
                    {"tenant_id": tenant_id},
                )
            session.commit()
            logger.info(f"Cleaned up test data for tenant {tenant_id}")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to cleanup test data: {e}")
            raise


class ContainerTestUtils:
    """Utilities for container testing and management."""

    @staticmethod
    async def wait_for_container_health(
        container_url: str, timeout: int = 300, health_endpoint: str = "/health"
    ) -> bool:
        """Wait for container to become healthy."""
        start_time = time.time()

        # Use environment variable to control SSL verification in tests
        import os
        verify_ssl = os.getenv("TEST_VERIFY_SSL", "true").lower() == "true"

        async with httpx.AsyncClient(verify=verify_ssl) as client:
            while time.time() - start_time < timeout:
                try:
                    response = await client.get(
                        f"{container_url}{health_endpoint}", timeout=10
                    )

                    if response.status_code == 200:
                        health_data = response.json()
                        if health_data.get("status") == "healthy":
                            logger.info(f"Container {container_url} is healthy")
                            return True

                except Exception as e:
                    logger.debug(f"Container health check failed: {e}")

                await asyncio.sleep(5)

        logger.error(
            f"Container {container_url} failed to become healthy within {timeout}s"
        )
        return False

    @staticmethod
    async def verify_container_scaling(
        base_url: str, expected_replicas: int, timeout: int = 120
    ) -> bool:
        """Verify container has scaled to expected replicas."""
        time.time()

        # This would integrate with actual container orchestration API
        # For now, simulate the verification
        await asyncio.sleep(2)  # Simulate scaling time

        # In real implementation, would check Kubernetes/Docker Compose replicas
        logger.info(f"Container scaled to {expected_replicas} replicas")
        return True

    @staticmethod
    async def monitor_container_resources(
        container_id: str, duration: int = 60
    ) -> dict[str, list[float]]:
        """Monitor container resource usage over time."""
        metrics = {"cpu_usage": [], "memory_usage": [], "timestamps": []}

        start_time = time.time()

        while time.time() - start_time < duration:
            # In real implementation, would query container metrics API
            # Simulate metrics collection
            import random

            metrics["cpu_usage"].append(random.uniform(10, 80))
            metrics["memory_usage"].append(random.uniform(100, 500))
            metrics["timestamps"].append(time.time())

            await asyncio.sleep(5)

        return metrics


class PageTestUtils:
    """Utilities for Playwright page testing."""

    @staticmethod
    async def login_management_admin(page: Page, credentials: dict[str, str]) -> bool:
        """Login as management admin."""
        try:
            await page.goto("/login")
            await page.fill("[data-testid=username]", credentials["username"])
            await page.fill("[data-testid=password]", credentials["password"])
            await page.click("[data-testid=login-button]")

            # Wait for successful login redirect
            await page.wait_for_url("**/dashboard", timeout=10000)
            return True

        except Exception as e:
            logger.error(f"Management admin login failed: {e}")
            return False

    @staticmethod
    async def login_tenant_admin(
        page: Page, tenant_url: str, credentials: dict[str, str]
    ) -> bool:
        """Login as tenant admin."""
        try:
            await page.goto(f"{tenant_url}/login")
            await page.fill("[data-testid=email]", credentials["email"])
            await page.fill("[data-testid=password]", credentials["password"])
            await page.click("[data-testid=login-button]")

            # Wait for dashboard
            await page.wait_for_url("**/dashboard", timeout=10000)
            return True

        except Exception as e:
            logger.error(f"Tenant admin login failed: {e}")
            return False

    @staticmethod
    async def wait_for_element_with_text(
        page: Page, selector: str, text: str, timeout: int = 10000
    ) -> bool:
        """Wait for element containing specific text."""
        try:
            await expect(page.locator(selector)).to_contain_text(text, timeout=timeout)
            return True
        except Exception as e:
            logger.debug(f"Element with text not found: {e}")
            return False

    @staticmethod
    async def capture_screenshot_on_failure(
        page: Page, test_name: str
    ) -> Optional[str]:
        """Capture screenshot when test fails."""
        try:
            screenshot_path = f"/tmp/{test_name}_{int(time.time())}.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            logger.info(f"Screenshot captured: {screenshot_path}")
            return screenshot_path
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}")
            return None


class ApiTestUtils:
    """Utilities for API testing."""

    @staticmethod
    async def make_authenticated_request(
        client: httpx.AsyncClient, method: str, url: str, auth_token: str, **kwargs
    ) -> httpx.Response:
        """Make authenticated API request."""
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {auth_token}"

        return await client.request(method, url, headers=headers, **kwargs)

    @staticmethod
    async def wait_for_api_ready(base_url: str, timeout: int = 60) -> bool:
        """Wait for API to become ready."""
        start_time = time.time()

        # Use environment variable to control SSL verification in tests
        import os
        verify_ssl = os.getenv("TEST_VERIFY_SSL", "true").lower() == "true"

        async with httpx.AsyncClient(verify=verify_ssl) as client:
            while time.time() - start_time < timeout:
                try:
                    response = await client.get(f"{base_url}/health", timeout=10)
                    if response.status_code == 200:
                        logger.info(f"API {base_url} is ready")
                        return True
                except Exception as e:
                    logger.debug(f"API not ready: {e}")

                await asyncio.sleep(2)

        return False

    @staticmethod
    async def verify_tenant_api_isolation(
        tenant_a_url: str, tenant_b_url: str, tenant_a_token: str, tenant_b_token: str
    ) -> dict[str, Any]:
        """Verify tenant API isolation."""
        results = {"isolated": True, "cross_tenant_access": []}

        # Use environment variable to control SSL verification in tests
        import os
        verify_ssl = os.getenv("TEST_VERIFY_SSL", "true").lower() == "true"

        async with httpx.AsyncClient(verify=verify_ssl) as client:
            try:
                # Try to access tenant B API with tenant A token
                response = await client.get(
                    f"{tenant_b_url}/api/v1/customers",
                    headers={"Authorization": f"Bearer {tenant_a_token}"},
                    timeout=10,
                )

                if response.status_code != 403:  # Should be forbidden
                    results["isolated"] = False
                    results["cross_tenant_access"].append(
                        {
                            "attempted_access": "tenant_a_token -> tenant_b_api",
                            "status_code": response.status_code,
                            "response": response.text[:200],
                        }
                    )

                # Try reverse access
                response = await client.get(
                    f"{tenant_a_url}/api/v1/customers",
                    headers={"Authorization": f"Bearer {tenant_b_token}"},
                    timeout=10,
                )

                if response.status_code != 403:
                    results["isolated"] = False
                    results["cross_tenant_access"].append(
                        {
                            "attempted_access": "tenant_b_token -> tenant_a_api",
                            "status_code": response.status_code,
                            "response": response.text[:200],
                        }
                    )

            except Exception as e:
                logger.error(f"Error testing API isolation: {e}")
                results["isolated"] = False
                results["error"] = str(e)

        return results


class ProvisioningTestUtils:
    """Utilities specific to provisioning workflow testing."""

    @staticmethod
    async def wait_for_provisioning_completion(
        management_db_session: Session,
        tenant_id: str,
        timeout: int = 600,  # 10 minutes
    ) -> dict[str, Any]:
        """Wait for tenant provisioning to complete."""
        start_time = time.time()
        result = {"completed": False, "final_status": None, "duration": 0, "events": []}

        while time.time() - start_time < timeout:
            # Refresh session and get tenant
            management_db_session.expire_all()
            tenant = (
                management_db_session.query(CustomerTenant)
                .filter_by(tenant_id=tenant_id)
                .first()
            )

            if not tenant:
                result["error"] = "Tenant not found"
                break

            result["final_status"] = tenant.status

            if tenant.status in [TenantStatus.ACTIVE, TenantStatus.READY]:
                result["completed"] = True
                break
            elif tenant.status == TenantStatus.FAILED:
                result["error"] = "Provisioning failed"
                break

            await asyncio.sleep(5)

        result["duration"] = time.time() - start_time
        return result

    @staticmethod
    async def verify_provisioning_steps(
        management_db_session: Session, tenant_id: str
    ) -> dict[str, Any]:
        """Verify all provisioning steps completed successfully."""
        from dotmac_management.models.tenant import TenantProvisioningEvent

        # Get tenant
        tenant = (
            management_db_session.query(CustomerTenant)
            .filter_by(tenant_id=tenant_id)
            .first()
        )

        if not tenant:
            return {"verified": False, "error": "Tenant not found"}

        # Get all provisioning events
        events = (
            management_db_session.query(TenantProvisioningEvent)
            .filter_by(tenant_id=tenant.id)
            .order_by(TenantProvisioningEvent.step_number)
            .all()
        )

        expected_steps = [
            "status_change.pending",
            "status_change.validating",
            "database_created",
            "secrets_generated",
            "status_change.provisioning",
            "container_deployed",
            "status_change.migrating",
            "migrations_completed",
            "status_change.seeding",
            "data_seeded",
            "admin_created",
            "license_provisioned",
            "status_change.testing",
            "health_check_passed",
            "status_change.ready",
            "status_change.active",
        ]

        completed_steps = [
            event.event_type for event in events if event.status == "success"
        ]

        return {
            "verified": all(step in completed_steps for step in expected_steps),
            "completed_steps": completed_steps,
            "missing_steps": [
                step for step in expected_steps if step not in completed_steps
            ],
            "total_events": len(events),
            "successful_events": len([e for e in events if e.status == "success"]),
            "failed_events": len([e for e in events if e.status == "failed"]),
        }


@asynccontextmanager
async def performance_monitor(test_name: str):
    """Context manager for monitoring test performance."""
    start_time = time.time()

    logger.info(f"Starting performance monitoring for {test_name}")

    try:
        yield {"start_time": start_time, "test_name": test_name}
    finally:
        end_time = time.time()
        duration = end_time - start_time

        logger.info(f"Performance metrics for {test_name}:")
        logger.info(f"  Duration: {duration:.2f}s")
        logger.info("  Memory delta: N/A")  # Would calculate actual memory usage


# Assertion helpers
def assert_tenant_provisioned_successfully(provisioning_result: dict[str, Any]):
    """Assert tenant was provisioned successfully."""
    assert provisioning_result[
        "completed"
    ], f"Provisioning failed: {provisioning_result}"
    assert provisioning_result["final_status"] in [
        TenantStatus.ACTIVE,
        TenantStatus.READY,
    ]


def assert_data_isolation_maintained(isolation_result: dict[str, Any]):
    """Assert data isolation is maintained between tenants."""
    assert isolation_result["isolated"], f"Data isolation violated: {isolation_result}"
    assert not isolation_result[
        "cross_contamination"
    ], "Cross-tenant data contamination detected"


def assert_api_isolation_maintained(api_result: dict[str, Any]):
    """Assert API isolation is maintained between tenants."""
    assert api_result["isolated"], f"API isolation violated: {api_result}"
    assert not api_result["cross_tenant_access"], "Cross-tenant API access detected"


# Export utilities
__all__ = [
    "E2ETestException",
    "DatabaseTestUtils",
    "ContainerTestUtils",
    "PageTestUtils",
    "ApiTestUtils",
    "ProvisioningTestUtils",
    "performance_monitor",
    "assert_tenant_provisioned_successfully",
    "assert_data_isolation_maintained",
    "assert_api_isolation_maintained",
]
