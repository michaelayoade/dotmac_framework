"""Helper utilities for license E2E testing."""

import asyncio
from typing import Any

from playwright.async_api import BrowserContext, Page, expect

from dotmac_shared.core.logging import get_logger

logger = get_logger(__name__)


class LicenseTestHelper:
    """Helper class for common license testing operations."""

    def __init__(self, page: Page, base_url: str = "http://localhost:3000"):
        self.page = page
        self.base_url = base_url

    async def login_as_admin(self, tenant_id: str, user_email: str = "admin@test.com"):
        """Login as admin user for a tenant."""
        await self.page.goto(f"{self.base_url}/login")

        # Fill login form
        await self.page.fill('[data-testid="email-input"]', user_email)
        await self.page.fill('[data-testid="password-input"]', "password123")
        await self.page.click('[data-testid="login-button"]')

        # Wait for dashboard to load
        await expect(self.page.locator('[data-testid="dashboard"]')).to_be_visible()

        # Verify tenant context is set
        tenant_indicator = self.page.locator('[data-testid="tenant-indicator"]')
        if await tenant_indicator.is_visible():
            await expect(tenant_indicator).to_contain_text(tenant_id)

    async def navigate_to_feature(self, feature_path: str):
        """Navigate to a specific feature page."""
        await self.page.goto(f"{self.base_url}{feature_path}")
        await self.page.wait_for_load_state("networkidle")

    async def check_feature_access(
        self, feature_selector: str, should_have_access: bool = True
    ):
        """Check if user has access to a specific feature."""
        feature_element = self.page.locator(feature_selector)

        if should_have_access:
            await expect(feature_element).to_be_visible()

            # Check that feature is not disabled
            disabled_indicator = self.page.locator('[data-testid="feature-disabled"]')
            await expect(disabled_indicator).not_to_be_visible()
        else:
            # Feature should be hidden or show access denied message
            try:
                await expect(feature_element).not_to_be_visible(timeout=3000)
            except Exception:
                # If element is visible when it shouldn't be, verify access denied message
                access_denied = self.page.locator('[data-testid="access-denied"]')
                await expect(access_denied).to_be_visible()

    async def trigger_license_limit_scenario(self, limit_type: str):
        """Trigger a scenario that should hit license limits."""
        if limit_type == "customers":
            await self.navigate_to_feature("/customers")
            await self.page.click('[data-testid="add-customer-button"]')

            # Fill customer form with test data
            await self.page.fill(
                '[data-testid="customer-name"]', "Test Customer Overflow"
            )
            await self.page.fill('[data-testid="customer-email"]', "overflow@test.com")
            await self.page.click('[data-testid="save-customer"]')

        elif limit_type == "api_calls":
            # Make rapid API calls to trigger rate limit
            for _i in range(20):
                await self.page.evaluate(
                    """
                    fetch('/api/v1/dashboard/stats', {
                        method: 'GET',
                        headers: { 'Content-Type': 'application/json' }
                    })
                """
                )

        elif limit_type == "premium_feature":
            await self.navigate_to_feature("/analytics/advanced")
            await self.page.click('[data-testid="generate-report"]')

    async def verify_license_error_message(self, expected_message_type: str):
        """Verify that appropriate license error message is shown."""
        error_selectors = {
            "limit_exceeded": '[data-testid="limit-exceeded-error"]',
            "feature_disabled": '[data-testid="feature-disabled-error"]',
            "license_expired": '[data-testid="license-expired-error"]',
            "upgrade_required": '[data-testid="upgrade-required-error"]',
        }

        selector = error_selectors.get(
            expected_message_type, '[data-testid="license-error"]'
        )
        error_element = self.page.locator(selector)

        await expect(error_element).to_be_visible()

        # Verify error contains relevant information
        error_text = await error_element.text_content()
        logger.info(f"License error message: {error_text}")

        return error_text

    async def check_feature_flag_propagation(
        self, feature_name: str, expected_state: bool
    ):
        """Check that feature flag changes have propagated to the UI."""
        # Check feature flag status endpoint
        response = await self.page.evaluate(
            f"""
            fetch('/api/v1/features/{feature_name}', {{
                method: 'GET',
                headers: {{ 'Content-Type': 'application/json' }}
            }}).then(res => res.json())
        """
        )

        assert (
            response.get("enabled") == expected_state
        ), f"Feature {feature_name} should be {expected_state}, but got {response.get('enabled')}"

        # Check UI reflects the feature state
        if expected_state:
            feature_element = self.page.locator(f'[data-feature="{feature_name}"]')
            await expect(feature_element).to_be_visible()
        else:
            feature_element = self.page.locator(f'[data-feature="{feature_name}"]')
            await expect(feature_element).not_to_be_visible()

    async def simulate_user_actions_across_apps(
        self, tenant_id: str, actions: list[dict[str, Any]]
    ):
        """Simulate user actions across multiple apps to test cross-app permissions."""
        apps = {
            "admin": "http://localhost:3000",
            "customer": "http://localhost:3001",
            "reseller": "http://localhost:3003",
        }

        results = []

        for action in actions:
            app = action["app"]
            path = action["path"]
            expected_access = action.get("expected_access", True)

            if app in apps:
                app_url = apps[app]

                # Navigate to the app
                await self.page.goto(f"{app_url}{path}")
                await self.page.wait_for_load_state("networkidle")

                # Check for access denied or successful access
                try:
                    if expected_access:
                        # Should be able to access the feature
                        await expect(
                            self.page.locator('[data-testid="main-content"]')
                        ).to_be_visible(timeout=5000)
                        results.append(
                            {"app": app, "path": path, "access_granted": True}
                        )
                    else:
                        # Should see access denied
                        access_denied = self.page.locator(
                            '[data-testid="access-denied"], [data-testid="unauthorized"]'
                        )
                        await expect(access_denied).to_be_visible(timeout=5000)
                        results.append(
                            {"app": app, "path": path, "access_granted": False}
                        )

                except Exception as e:
                    logger.warning(f"Access check failed for {app}{path}: {e}")
                    results.append(
                        {
                            "app": app,
                            "path": path,
                            "access_granted": False,
                            "error": str(e),
                        }
                    )

        return results

    async def verify_subscription_changes_reflected(self, old_plan: str, new_plan: str):
        """Verify that subscription plan changes are reflected in the UI."""
        # Navigate to account/subscription page
        await self.navigate_to_feature("/account/subscription")

        # Check that current plan is displayed correctly
        plan_display = self.page.locator('[data-testid="current-plan"]')
        await expect(plan_display).to_contain_text(new_plan.title())

        # Check that new plan features are available
        if new_plan == "enterprise":
            # Should have access to enterprise features
            await self.check_feature_access('[data-testid="sso-settings"]', True)
            await self.check_feature_access('[data-testid="advanced-analytics"]', True)
            await self.check_feature_access(
                '[data-testid="white-label-settings"]', True
            )

        elif new_plan == "premium":
            # Should have premium features but not enterprise
            await self.check_feature_access('[data-testid="custom-branding"]', True)
            await self.check_feature_access('[data-testid="premium-api"]', True)
            await self.check_feature_access('[data-testid="sso-settings"]', False)

        elif new_plan == "basic":
            # Should only have basic features
            await self.check_feature_access('[data-testid="basic-analytics"]', True)
            await self.check_feature_access('[data-testid="custom-branding"]', False)
            await self.check_feature_access('[data-testid="advanced-analytics"]', False)

    async def check_grace_period_handling(self, grace_period_minutes: int = 5):
        """Check that grace period is handled correctly during subscription changes."""
        # During grace period, old features should still work
        await self.check_feature_access('[data-testid="premium-feature"]', True)

        # Check that grace period is indicated in UI
        grace_notice = self.page.locator('[data-testid="grace-period-notice"]')
        await expect(grace_notice).to_be_visible()

        grace_text = await grace_notice.text_content()
        assert (
            "grace period" in grace_text.lower()
        ), "Grace period notice should be displayed"

        return grace_text

    async def verify_audit_trail_creation(self, action_type: str, tenant_id: str):
        """Verify that license-related actions are logged in audit trail."""
        # Navigate to audit logs (admin feature)
        await self.navigate_to_feature("/admin/audit-logs")

        # Look for recent audit entries
        audit_entries = self.page.locator('[data-testid="audit-entry"]')

        # Find entry matching the action type
        matching_entry = None
        for i in range(await audit_entries.count()):
            entry = audit_entries.nth(i)
            entry_text = await entry.text_content()

            if action_type in entry_text and tenant_id in entry_text:
                matching_entry = entry
                break

        assert matching_entry is not None, f"Audit entry for {action_type} not found"

        # Verify entry contains expected information
        await expect(matching_entry).to_be_visible()
        entry_text = await matching_entry.text_content()

        # Should contain timestamp, action, and tenant info
        assert tenant_id in entry_text
        assert action_type in entry_text

        return entry_text


class MultiAppTestHelper:
    """Helper for testing across multiple apps simultaneously."""

    def __init__(self, context: BrowserContext):
        self.context = context
        self.app_pages: dict[str, Page] = {}
        self.app_urls = {
            "admin": "http://localhost:3000",
            "customer": "http://localhost:3001",
            "reseller": "http://localhost:3003",
            "field-ops": "http://localhost:3002",
        }

    async def setup_app_pages(self, apps: list[str]):
        """Create pages for each app that needs testing."""
        for app in apps:
            if app in self.app_urls:
                page = await self.context.new_page()
                self.app_pages[app] = page

    async def login_to_all_apps(self, tenant_id: str, user_credentials: dict[str, str]):
        """Login to all apps with the same user credentials."""
        login_tasks = []

        for app, page in self.app_pages.items():
            task = self._login_to_app(page, self.app_urls[app], user_credentials)
            login_tasks.append(task)

        await asyncio.gather(*login_tasks)

    async def verify_feature_across_apps(
        self, feature_name: str, expected_states: dict[str, bool]
    ):
        """Verify feature availability across multiple apps."""
        results = {}

        for app, expected_state in expected_states.items():
            if app in self.app_pages:
                page = self.app_pages[app]
                helper = LicenseTestHelper(page, self.app_urls[app])

                try:
                    await helper.check_feature_flag_propagation(
                        feature_name, expected_state
                    )
                    results[app] = {"success": True, "state": expected_state}
                except Exception as e:
                    results[app] = {"success": False, "error": str(e)}

        return results

    async def cleanup(self):
        """Close all app pages."""
        for page in self.app_pages.values():
            await page.close()
        self.app_pages.clear()

    async def _login_to_app(
        self, page: Page, app_url: str, credentials: dict[str, str]
    ):
        """Login to a specific app."""
        await page.goto(f"{app_url}/login")
        await page.fill('[data-testid="email-input"]', credentials["email"])
        await page.fill('[data-testid="password-input"]', credentials["password"])
        await page.click('[data-testid="login-button"]')

        # Wait for successful login
        await expect(
            page.locator('[data-testid="dashboard"], [data-testid="main-content"]')
        ).to_be_visible(timeout=10000)
