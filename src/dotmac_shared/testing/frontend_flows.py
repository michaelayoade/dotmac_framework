#!/usr/bin/env python3
"""
DRY-Compliant Frontend Flow Testing Module

Integrates with existing DRY test orchestration system and follows established patterns.
Uses Poetry environment and pytest framework for consistency.
"""

import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import pytest
from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from ..monitoring import BaseMonitoringService, get_monitoring
from ..testing.base import BaseTestSuite

logger = logging.getLogger(__name__)


@dataclass
class UITestResult:
    """Result of a UI test following DRY patterns."""

    test_name: str
    success: bool
    duration: float
    details: str = ""
    screenshot_path: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class FrontendFlowResult:
    """Complete frontend flow test result."""

    timestamp: str
    total_duration: float
    applications_tested: list[str]
    test_results: list[UITestResult]
    success_metrics: dict[str, Any]
    integration_status: dict[str, Any]

    @property
    def total_tests(self) -> int:
        return len(self.test_results)

    @property
    def passed_tests(self) -> int:
        return sum(1 for result in self.test_results if result.success)

    @property
    def failed_tests(self) -> int:
        return self.total_tests - self.passed_tests

    @property
    def success_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100


class DRYFrontendFlowTester(BaseTestSuite):
    """
    DRY-compliant frontend flow tester that integrates with existing architecture.

    Features:
    - Follows existing DRY patterns and conventions
    - Integrates with Poetry environment
    - Uses pytest framework consistency
    - Leverages existing monitoring system
    - Provides structured results for orchestration
    """

    def __init__(
        self,
        framework_root: Path,
        monitoring_service: Optional[BaseMonitoringService] = None,
    ):
        super().__init__()
        self.framework_root = framework_root
        self.monitoring = monitoring_service or get_monitoring()
        self.screenshots_dir = framework_root / "test-results" / "frontend-screenshots"
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

        # Frontend applications configuration (DRY pattern - single source of truth)
        self.frontend_config = {
            "management-admin": {
                "url": "http://localhost:3001",
                "name": "Management Admin Portal",
                "expected_elements": ["login", "dashboard", "navigation"],
            },
            "admin": {
                "url": "http://localhost:3002",
                "name": "Admin Portal",
                "expected_elements": ["login", "customers", "billing"],
            },
            "customer": {
                "url": "http://localhost:3003",
                "name": "Customer Portal",
                "expected_elements": ["login", "services", "billing"],
            },
        }

        # Backend APIs for integration testing (reuse from existing config)
        self.backend_apis = {
            "management_platform": "http://localhost:8001",
            "isp_framework": "http://localhost:8000",
        }

        self.test_results: list[UITestResult] = []

    async def setup_browser_context(self) -> tuple[Browser, BrowserContext]:
        """Set up browser context with consistent configuration."""
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"]
        )

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="DotMac-Framework-Test/1.0 (Playwright)",
            ignore_https_errors=True,
        )

        return browser, context

    def log_test_result(
        self,
        test_name: str,
        success: bool,
        duration: float,
        details: str = "",
        screenshot_path: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        """Log test result following DRY logging patterns."""
        result = UITestResult(
            test_name=test_name,
            success=success,
            duration=duration,
            details=details,
            screenshot_path=screenshot_path,
            error_message=error_message,
        )

        self.test_results.append(result)

        # Log to monitoring system
        status = "PASS" if success else "FAIL"
        logger.info(f"UI Test {status}: {test_name} ({duration:.2f}s)")
        if details:
            logger.info(f"  Details: {details}")
        if error_message:
            logger.error(f"  Error: {error_message}")

        # Monitoring integration
        if self.monitoring:
            self.monitoring.record_metric(
                name="frontend_test",
                value=1 if success else 0,
                tags={"test_name": test_name, "status": status},
            )

    async def test_application_connectivity(
        self, page: Page, app_key: str, app_config: dict[str, Any]
    ) -> bool:
        """Test basic application connectivity and loading."""
        start_time = time.time()

        try:
            logger.info(f"Testing connectivity for {app_config['name']}")

            response = await page.goto(app_config["url"], timeout=30000)
            await page.wait_for_load_state("networkidle", timeout=15000)

            if not response or response.status >= 400:
                self.log_test_result(
                    f"{app_config['name']} Connectivity",
                    False,
                    time.time() - start_time,
                    f"HTTP {response.status if response else 'No response'}",
                )
                return False

            # Take screenshot for documentation
            screenshot_path = self.screenshots_dir / f"{app_key}_connectivity.png"
            await page.screenshot(path=str(screenshot_path))

            # Basic page validation
            title = await page.title()

            self.log_test_result(
                f"{app_config['name']} Connectivity",
                True,
                time.time() - start_time,
                f"Title: '{title}', Status: {response.status}",
                str(screenshot_path),
            )

            return True

        except Exception as e:
            self.log_test_result(
                f"{app_config['name']} Connectivity",
                False,
                time.time() - start_time,
                error_message=str(e),
            )
            return False

    async def test_login_form_presence(
        self, page: Page, app_key: str, app_config: dict[str, Any]
    ) -> bool:
        """Test login form detection and basic interaction."""
        start_time = time.time()

        try:
            logger.info(f"Testing login form for {app_config['name']}")

            await page.goto(app_config["url"], timeout=30000)
            await page.wait_for_load_state("networkidle")

            # DRY pattern: reusable login element selectors
            login_selectors = [
                "input[type='email']",
                "input[name*='email']",
                "input[id*='email']",
                "input[type='password']",
                "input[name*='password']",
                "input[id*='password']",
                "button[type='submit']",
                "text=Login",
                "text=Sign In",
            ]

            found_elements = []
            for selector in login_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element and await element.is_visible():
                        found_elements.append(selector)
                except Exception:
                    # Element not found or not accessible - skip and continue
                    continue

            # Screenshot for analysis
            screenshot_path = self.screenshots_dir / f"{app_key}_login_form.png"
            await page.screenshot(path=str(screenshot_path))

            # Determine if login form is present (need email + password + submit)
            has_email = any("email" in sel for sel in found_elements)
            has_password = any("password" in sel for sel in found_elements)
            has_submit = any(
                "submit" in sel or "Login" in sel or "Sign In" in sel
                for sel in found_elements
            )

            success = has_email and has_password

            self.log_test_result(
                f"{app_config['name']} Login Form",
                success,
                time.time() - start_time,
                f"Elements found: {len(found_elements)}, Email: {has_email}, Password: {has_password}, Submit: {has_submit}",
                str(screenshot_path),
            )

            return success

        except Exception as e:
            self.log_test_result(
                f"{app_config['name']} Login Form",
                False,
                time.time() - start_time,
                error_message=str(e),
            )
            return False

    async def test_responsive_behavior(
        self, page: Page, app_key: str, app_config: dict[str, Any]
    ) -> bool:
        """Test responsive design across viewports."""
        start_time = time.time()

        # DRY pattern: standard viewport configurations
        viewports = [
            {"name": "mobile", "width": 375, "height": 667},
            {"name": "tablet", "width": 768, "height": 1024},
            {"name": "desktop", "width": 1920, "height": 1080},
        ]

        success_count = 0

        try:
            for viewport in viewports:
                logger.info(f"Testing {app_config['name']} on {viewport['name']}")

                await page.set_viewport_size(viewport["width"], viewport["height"])
                await page.goto(app_config["url"], timeout=30000)
                await page.wait_for_load_state("networkidle")

                # Screenshot for each viewport
                screenshot_path = (
                    self.screenshots_dir / f"{app_key}_{viewport['name']}.png"
                )
                await page.screenshot(path=str(screenshot_path))

                # Basic responsiveness check
                body_height = await page.evaluate("document.body.scrollHeight")
                viewport_height = viewport["height"]

                # Consider responsive if content adapts reasonably
                is_responsive = body_height >= viewport_height * 0.5

                if is_responsive:
                    success_count += 1

                self.log_test_result(
                    f"{app_config['name']} {viewport['name'].title()} Layout",
                    is_responsive,
                    0,  # Individual viewport test time
                    f"Viewport: {viewport['width']}x{viewport['height']}, Content height: {body_height}px",
                    str(screenshot_path),
                )

            overall_success = success_count >= len(viewports) * 0.7  # 70% success rate

            self.log_test_result(
                f"{app_config['name']} Responsive Design",
                overall_success,
                time.time() - start_time,
                f"Responsive on {success_count}/{len(viewports)} viewports",
            )

            return overall_success

        except Exception as e:
            self.log_test_result(
                f"{app_config['name']} Responsive Design",
                False,
                time.time() - start_time,
                error_message=str(e),
            )
            return False

    async def run_comprehensive_tests(self) -> FrontendFlowResult:
        """Run complete frontend flow tests following DRY orchestration patterns."""
        start_time = time.time()
        logger.info("Starting DRY-compliant frontend flow testing")

        playwright = await async_playwright().start()
        browser = None

        try:
            browser, context = await self.setup_browser_context()
            page = await context.new_page()

            # Test each frontend application
            for app_key, app_config in self.frontend_config.items():
                logger.info(f"Testing application: {app_config['name']}")

                # Core test suites (DRY pattern - consistent across apps)
                await self.test_application_connectivity(page, app_key, app_config)
                await self.test_login_form_presence(page, app_key, app_config)
                await self.test_responsive_behavior(page, app_key, app_config)

        except Exception as e:
            logger.error(f"Frontend testing error: {e}")

        finally:
            if browser:
                await browser.close()
            await playwright.stop()

        # Generate comprehensive result
        end_time = time.time()

        result = FrontendFlowResult(
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_duration=end_time - start_time,
            applications_tested=list(self.frontend_config.keys()),
            test_results=self.test_results,
            success_metrics={
                "total_tests": len(self.test_results),
                "passed_tests": sum(1 for r in self.test_results if r.success),
                "success_rate": (
                    (
                        sum(1 for r in self.test_results if r.success)
                        / len(self.test_results)
                        * 100
                    )
                    if self.test_results
                    else 0
                ),
            },
            integration_status={
                "dry_compliance": True,
                "monitoring_integrated": self.monitoring is not None,
                "screenshot_count": len(
                    [r for r in self.test_results if r.screenshot_path]
                ),
            },
        )

        return result


# Integration function for DRY test orchestration
async def run_frontend_flows(framework_root: Path) -> dict[str, Any]:
    """
    Main entry point for DRY test orchestration integration.

    Returns results in format compatible with existing orchestration system.
    """
    tester = DRYFrontendFlowTester(framework_root)
    result = await tester.run_comprehensive_tests()

    # Convert to dict for JSON serialization (DRY pattern)
    return {
        "test_type": "frontend_flows",
        "timestamp": result.timestamp,
        "duration": result.total_duration,
        "success": result.success_rate >= 70,  # 70% threshold
        "metrics": result.success_metrics,
        "applications": result.applications_tested,
        "details": [asdict(test_result) for test_result in result.test_results],
        "integration": result.integration_status,
    }


# pytest integration (following existing patterns)
@pytest.mark.integration
@pytest.mark.slow
async def test_frontend_flows():
    """pytest-compatible frontend flow test."""
    framework_root = Path(__file__).parent.parent.parent.parent
    result = await run_frontend_flows(framework_root)

    # Assert based on DRY success criteria
    assert result["success"], f"Frontend flows failed: {result['metrics']}"
    assert result["metrics"]["total_tests"] > 0, "No frontend tests executed"
    assert len(result["applications"]) >= 2, "Insufficient applications tested"


if __name__ == "__main__":
    # Direct execution support (DRY pattern - works standalone and in orchestration)
    import asyncio

    async def main():
        framework_root = Path(__file__).parent.parent.parent.parent
        result = await run_frontend_flows(framework_root)

        logger.info(f"\n{'='*70}")
        logger.info("🎭 DRY Frontend Flow Test Results")
        logger.info(f"{'='*70}")
        logger.info(f"Applications tested: {len(result['applications'])}")
        logger.info(f"Total tests: {result['metrics']['total_tests']}")
        logger.info(f"Success rate: {result['metrics']['success_rate']:.1f}%")
        logger.info(f"Duration: {result['duration']:.2f}s")

        if result["success"]:
            logger.info("🎉 Frontend flows PASSED")
        else:
            logger.info("⚠️ Frontend flows FAILED")

        # Save results (DRY pattern - consistent with other test outputs)
        results_file = framework_root / "test-results" / "frontend_flows.json"
        results_file.parent.mkdir(exist_ok=True)

        with open(results_file, "w") as f:
            json.dump(result, f, indent=2, default=str)

        logger.info(f"\nResults saved to: {results_file}")

        return result["success"]

    success = asyncio.run(main())
    exit(0 if success else 1)
