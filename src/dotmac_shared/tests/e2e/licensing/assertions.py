"""Custom assertion helpers for license E2E testing."""

import asyncio
from datetime import datetime

from dotmac_shared.core.logging import get_logger
from playwright.async_api import Page, expect

logger = get_logger(__name__)


class LicenseAssertions:
    """Custom assertions for license testing scenarios."""

    @staticmethod
    async def assert_feature_access_denied(page: Page, feature_selector: str, timeout: int = 5000):
        """Assert that access to a feature is properly denied."""
        # Check for access denied message
        access_denied_selectors = [
            '[data-testid="access-denied"]',
            '[data-testid="feature-disabled"]',
            '[data-testid="upgrade-required"]',
            ".access-denied",
            ".feature-disabled",
        ]

        access_denied_found = False
        for selector in access_denied_selectors:
            element = page.locator(selector)
            if await element.is_visible():
                access_denied_found = True
                break

        if not access_denied_found:
            # Feature element should not be visible or should be disabled
            feature_element = page.locator(feature_selector)
            try:
                await expect(feature_element).not_to_be_visible(timeout=timeout)
            except AssertionError:
                # If visible, should be disabled
                await expect(feature_element).to_be_disabled()

    @staticmethod
    async def assert_license_limit_error(page: Page, limit_type: str, expected_limit: int = None):
        """Assert that a license limit error is properly displayed."""
        error_messages = {
            "customers": "customer limit",
            "api_calls": "API rate limit",
            "concurrent_users": "concurrent user limit",
            "network_devices": "network device limit",
            "storage": "storage limit",
        }

        # Look for error modal or notification
        error_selectors = [
            '[data-testid="license-error"]',
            '[data-testid="limit-exceeded"]',
            ".error-modal",
            ".license-notification",
        ]

        error_element = None
        for selector in error_selectors:
            element = page.locator(selector)
            if await element.is_visible():
                error_element = element
                break

        assert error_element is not None, f"License limit error not found for {limit_type}"

        # Verify error message contains expected content
        error_text = await error_element.text_content()
        expected_text = error_messages.get(limit_type, limit_type)

        assert (
            expected_text.lower() in error_text.lower()
        ), f"Error message should contain '{expected_text}', got: {error_text}"

        if expected_limit:
            assert (
                str(expected_limit) in error_text
            ), f"Error message should contain limit value '{expected_limit}', got: {error_text}"

    @staticmethod
    async def assert_feature_flag_state(page: Page, feature_name: str, expected_enabled: bool):
        """Assert feature flag state matches expected value."""
        # Check via API call
        response = await page.evaluate(
            f"""
            fetch('/api/v1/features/{feature_name}', {{
                method: 'GET',
                headers: {{ 'Content-Type': 'application/json' }}
            }}).then(res => res.json()).catch(err => ({{ enabled: false, error: err.message }}))
        """
        )

        actual_enabled = response.get("enabled", False)
        assert (
            actual_enabled == expected_enabled
        ), f"Feature '{feature_name}' should be {expected_enabled}, but got {actual_enabled}"

        # Also check UI state if feature has visual indicator
        ui_indicator = page.locator(f'[data-feature="{feature_name}"]')
        if await ui_indicator.count() > 0:
            if expected_enabled:
                await expect(ui_indicator).to_be_visible()
                await expect(ui_indicator).not_to_have_class("disabled")
            else:
                try:
                    await expect(ui_indicator).not_to_be_visible()
                except AssertionError:
                    # If visible, should be disabled
                    await expect(ui_indicator).to_have_class("disabled")

    @staticmethod
    async def assert_subscription_plan_active(page: Page, expected_plan: str):
        """Assert that the correct subscription plan is active."""
        # Navigate to account/subscription page to verify
        await page.goto("/account/subscription")
        await page.wait_for_load_state("networkidle")

        # Check current plan display
        plan_indicator = page.locator('[data-testid="current-plan"], .current-plan')
        await expect(plan_indicator).to_be_visible()

        plan_text = await plan_indicator.text_content()
        assert expected_plan.lower() in plan_text.lower(), f"Expected plan '{expected_plan}' not found in: {plan_text}"

        # Verify plan-specific features are available/unavailable
        feature_checks = {
            "basic": {
                "available": ["basic_analytics", "standard_api"],
                "unavailable": ["advanced_analytics", "sso", "white_label"],
            },
            "premium": {
                "available": ["basic_analytics", "premium_api", "custom_branding"],
                "unavailable": ["sso", "white_label", "advanced_security"],
            },
            "enterprise": {
                "available": ["advanced_analytics", "sso", "white_label", "enterprise_api"],
                "unavailable": [],
            },
        }

        if expected_plan in feature_checks:
            checks = feature_checks[expected_plan]

            for feature in checks["available"]:
                feature_element = page.locator(f'[data-feature="{feature}"]')
                if await feature_element.count() > 0:
                    await expect(feature_element).to_be_visible()

            for feature in checks["unavailable"]:
                feature_element = page.locator(f'[data-feature="{feature}"]')
                if await feature_element.count() > 0:
                    await expect(feature_element).not_to_be_visible()

    @staticmethod
    async def assert_grace_period_active(page: Page, remaining_time_minutes: int = None):
        """Assert that grace period is properly indicated."""
        grace_indicators = [
            '[data-testid="grace-period-notice"]',
            '[data-testid="subscription-grace"]',
            ".grace-period-banner",
        ]

        grace_element = None
        for selector in grace_indicators:
            element = page.locator(selector)
            if await element.is_visible():
                grace_element = element
                break

        assert grace_element is not None, "Grace period indicator not found"

        grace_text = await grace_element.text_content()
        assert "grace period" in grace_text.lower(), f"Grace period text not found in: {grace_text}"

        if remaining_time_minutes:
            # Should indicate remaining time
            time_indicators = [str(remaining_time_minutes), "minutes", "min"]
            time_found = any(indicator in grace_text.lower() for indicator in time_indicators)
            assert time_found, f"Grace period time not indicated properly in: {grace_text}"

    @staticmethod
    async def assert_cross_app_consistency(pages: dict[str, Page], feature_name: str, expected_state: bool):
        """Assert feature state is consistent across multiple apps."""
        results = {}

        for app_name, page in pages.items():
            try:
                await LicenseAssertions.assert_feature_flag_state(page, feature_name, expected_state)
                results[app_name] = {"success": True, "state": expected_state}
            except Exception as e:
                results[app_name] = {"success": False, "error": str(e)}

        # All apps should have consistent state
        failed_apps = [app for app, result in results.items() if not result["success"]]

        assert len(failed_apps) == 0, f"Feature '{feature_name}' state inconsistent across apps. Failed: {failed_apps}"

        return results

    @staticmethod
    async def assert_audit_log_entry(page: Page, action_type: str, tenant_id: str, within_minutes: int = 5):
        """Assert that an audit log entry was created for a license action."""
        await page.goto("/admin/audit-logs")
        await page.wait_for_load_state("networkidle")

        # Filter logs by recent entries
        recent_filter = page.locator('[data-testid="recent-filter"]')
        if await recent_filter.is_visible():
            await recent_filter.click()

        # Look for matching audit entry
        audit_entries = page.locator('[data-testid="audit-entry"]')

        matching_entry_found = False
        for i in range(min(await audit_entries.count(), 20)):  # Check first 20 entries
            entry = audit_entries.nth(i)
            entry_text = await entry.text_content()

            if action_type.lower() in entry_text.lower() and tenant_id in entry_text:
                matching_entry_found = True

                # Verify timestamp is recent
                timestamp_element = entry.locator('[data-testid="audit-timestamp"]')
                if await timestamp_element.is_visible():
                    timestamp_text = await timestamp_element.text_content()
                    # Should be within specified minutes
                    assert (
                        "minute" in timestamp_text or "second" in timestamp_text
                    ), f"Audit entry should be recent, got: {timestamp_text}"

                break

        assert matching_entry_found, f"Audit log entry for '{action_type}' not found for tenant {tenant_id}"

    @staticmethod
    async def assert_license_usage_tracking(page: Page, tenant_id: str, usage_type: str, expected_count: int = None):
        """Assert that license usage is being tracked correctly."""
        # Navigate to license usage dashboard (admin feature)
        await page.goto(f"/admin/tenants/{tenant_id}/usage")
        await page.wait_for_load_state("networkidle")

        usage_metric = page.locator(f'[data-testid="usage-{usage_type}"]')
        await expect(usage_metric).to_be_visible()

        usage_text = await usage_metric.text_content()

        if expected_count is not None:
            assert str(expected_count) in usage_text, f"Usage count {expected_count} not found in: {usage_text}"

        # Verify usage percentage if limits are defined
        usage_percentage = page.locator(f'[data-testid="usage-{usage_type}-percentage"]')
        if await usage_percentage.is_visible():
            percentage_text = await usage_percentage.text_content()
            assert "%" in percentage_text, f"Usage percentage should be displayed: {percentage_text}"

    @staticmethod
    async def assert_real_time_updates(page: Page, feature_name: str, initial_state: bool, timeout: int = 30):
        """Assert that feature flag changes are reflected in real-time."""
        # First verify initial state
        await LicenseAssertions.assert_feature_flag_state(page, feature_name, initial_state)

        # Setup listener for changes
        await page.evaluate(
            """
            window.featureUpdates = [];

            // Listen for SSE or WebSocket updates
            if (window.EventSource) {
                const eventSource = new EventSource('/api/v1/features/stream');
                eventSource.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    window.featureUpdates.push(data);
                };
            }
        """
        )

        # Wait for state change (this would be triggered externally)
        expected_new_state = not initial_state

        # Poll for state change
        start_time = datetime.now()
        while (datetime.now() - start_time).seconds < timeout:
            try:
                await LicenseAssertions.assert_feature_flag_state(page, feature_name, expected_new_state)
                break  # State changed successfully
            except AssertionError:
                await asyncio.sleep(1)
        else:
            raise AssertionError(
                f"Feature {feature_name} did not update to {expected_new_state} within {timeout} seconds"
            )

        # Verify update was received via real-time channel
        updates = await page.evaluate("window.featureUpdates || []")
        feature_update_found = any(
            update.get("feature_name") == feature_name and update.get("enabled") == expected_new_state
            for update in updates
        )

        assert feature_update_found, f"Real-time update for {feature_name} not received"


class PerformanceAssertions:
    """Performance-related assertions for license testing."""

    @staticmethod
    async def assert_feature_check_performance(page: Page, feature_name: str, max_response_time_ms: int = 100):
        """Assert that feature flag checks perform within acceptable time limits."""
        start_time = await page.evaluate("Date.now()")

        # Make feature check API call
        await page.evaluate(
            f"""
            fetch('/api/v1/features/{feature_name}', {{
                method: 'GET',
                headers: {{ 'Content-Type': 'application/json' }}
            }})
        """
        )

        end_time = await page.evaluate("Date.now()")
        response_time = end_time - start_time

        assert (
            response_time <= max_response_time_ms
        ), f"Feature check for '{feature_name}' took {response_time}ms, expected <= {max_response_time_ms}ms"

    @staticmethod
    async def assert_license_cache_effectiveness(page: Page, cache_hit_ratio: float = 0.8):
        """Assert that license caching is working effectively."""
        # This would require monitoring cache hit/miss ratios
        cache_stats = await page.evaluate(
            """
            fetch('/api/v1/admin/license-cache-stats')
                .then(res => res.json())
                .catch(() => ({ hit_ratio: 0 }))
        """
        )

        actual_hit_ratio = cache_stats.get("hit_ratio", 0)
        assert (
            actual_hit_ratio >= cache_hit_ratio
        ), f"License cache hit ratio {actual_hit_ratio} below expected {cache_hit_ratio}"
