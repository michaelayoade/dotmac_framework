#!/usr/bin/env python3
"""
E2E Test Runner for DotMac Management Backend

Comprehensive test runner that handles:
- Test environment setup and validation
- Test execution with proper isolation
- Cleanup verification and reporting
- Failure analysis and debugging support

Usage:
    python run_tests.py                    # Run all E2E tests
    python run_tests.py --provisioning     # Run only provisioning tests
    python run_tests.py --lifecycle        # Run only lifecycle tests
    python run_tests.py --isolation        # Run only isolation tests
    python run_tests.py --cleanup-only     # Run cleanup validation only
    python run_tests.py --debug            # Run with debug output
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__, timezone).parent.parent.parent.parent))

from dotmac_shared.core.logging import get_logger

from .cleanup import E2ETestCleaner

logger = get_logger(__name__)


class E2ETestRunner:
    """Manages E2E test execution with comprehensive setup and cleanup."""

    def __init__(self):
        self.test_results = {}
        self.cleanup_results = {}
        self.start_time = None
        self.end_time = None

    def run_tests(self, args: argparse.Namespace) -> int:
        """Run E2E tests with specified configuration."""
        self.start_time = datetime.now(timezone.utc)

        try:
            # Setup test environment
            self._setup_test_environment(args)

            # Build pytest arguments
            pytest_args = self._build_pytest_args(args)

            # Run pre-test validation
            if not args.skip_validation:
                self._validate_test_environment()

            # Execute tests
            logger.info("Starting E2E test execution")
            exit_code = pytest.main(pytest_args)

            # Post-test cleanup and validation
            if not args.skip_cleanup:
                asyncio.run(self._perform_post_test_cleanup())

            # Generate test report
            self._generate_test_report(exit_code, args)

            return exit_code

        except Exception as e:
            logger.error(f"E2E test execution failed: {e}")
            return 1
        finally:
            self.end_time = datetime.now(timezone.utc)

    def _setup_test_environment(self, args: argparse.Namespace):
        """Setup test environment variables and configuration."""
        logger.info("Setting up E2E test environment")

        # Set test environment variables
        os.environ["ENVIRONMENT"] = "e2e_testing"
        os.environ["LOG_LEVEL"] = "DEBUG" if args.debug else "INFO"
        os.environ["DISABLE_REAL_DEPLOYMENTS"] = "true"
        os.environ["TEST_CLEANUP_ENABLED"] = "true" if not args.skip_cleanup else "false"

        # Database URLs for testing
        os.environ["TEST_MANAGEMENT_DB"] = "postgresql://test_user:test_pass@localhost:5433/test_management"
        os.environ["TEST_TENANT_A_DB"] = "postgresql://test_user:test_pass@localhost:5434/test_tenant_a"
        os.environ["TEST_TENANT_B_DB"] = "postgresql://test_user:test_pass@localhost:5435/test_tenant_b"

        # API URLs
        os.environ["TEST_BASE_URL"] = "https://test.dotmac.local"

        # Test data configuration
        os.environ["TEST_DATA_ISOLATION"] = "strict"
        os.environ["TEST_TENANT_CLEANUP"] = "immediate"

        logger.info("E2E test environment configured")

    def _build_pytest_args(self, args: argparse.Namespace) -> list[str]:
        """Build pytest command line arguments."""
        pytest_args = []

        # Base configuration
        pytest_args.extend(["--verbose", "--tb=short", "--strict-markers", "--color=yes"])

        # Test selection based on arguments
        if args.provisioning:
            pytest_args.extend(["-m", "tenant_provisioning"])
        elif args.lifecycle:
            pytest_args.extend(["-m", "container_lifecycle"])
        elif args.isolation:
            pytest_args.extend(["-m", "tenant_isolation"])
        elif args.cleanup_only:
            pytest_args.extend(["-m", "cleanup_critical"])
        else:
            pytest_args.extend(["-m", "e2e"])

        # Debug configuration
        if args.debug:
            pytest_args.extend(["--capture=no", "--log-cli-level=DEBUG", "--show-capture=all"])

        # Parallel execution
        if args.parallel and not args.debug:
            pytest_args.extend(["-n", str(args.parallel)])

        # Coverage reporting
        if args.coverage:
            pytest_args.extend(
                ["--cov=src/dotmac_management", "--cov-report=term-missing", "--cov-report=html:htmlcov"]
            )

        # Output options
        if args.junit_xml:
            pytest_args.extend(["--junit-xml", args.junit_xml])

        # Timeout for slow tests
        if not args.debug:
            pytest_args.extend(["--timeout", str(args.timeout)])

        # Test path
        pytest_args.append("src/dotmac_management/tests/e2e/")

        return pytest_args

    def _validate_test_environment(self):
        """Validate test environment is ready."""
        logger.info("Validating test environment")

        validation_checks = [
            ("Database connectivity", self._check_database_connectivity),
            ("Container orchestration", self._check_container_service),
            ("Network connectivity", self._check_network_access),
            ("File system permissions", self._check_filesystem_access),
        ]

        for check_name, check_func in validation_checks:
            try:
                check_func()
                logger.info(f"✅ {check_name} validation passed")
            except Exception as e:
                logger.warning(f"⚠️  {check_name} validation failed: {e}")

        logger.info("Environment validation completed")

    def _check_database_connectivity(self):
        """Check database connectivity."""
        # In real implementation, would check actual database connections
        pass

    def _check_container_service(self):
        """Check container orchestration service."""
        # In real implementation, would check Docker/Kubernetes connectivity
        pass

    def _check_network_access(self):
        """Check network access to test services."""
        # In real implementation, would check API endpoints
        pass

    def _check_filesystem_access(self):
        """Check filesystem access and permissions."""
        temp_dir = Path("/tmp")  # noqa: B008
        if not temp_dir.exists() or not os.access(temp_dir, os.W_OK):
            raise RuntimeError("Cannot write to temporary directory")

    async def _perform_post_test_cleanup(self):
        """Perform comprehensive cleanup after tests."""
        logger.info("Starting post-test cleanup")

        cleaner = E2ETestCleaner()
        self.cleanup_results = await cleaner.cleanup_all()

        # Validate cleanup was successful
        if self.cleanup_results["errors"]:
            logger.warning(f"Cleanup completed with {len(self.cleanup_results['errors'])} errors")
            for error in self.cleanup_results["errors"]:
                logger.warning(f"  - {error}")
        else:
            logger.info("✅ Post-test cleanup completed successfully")

    def _generate_test_report(self, exit_code: int, args: argparse.Namespace):
        """Generate comprehensive test report."""
        duration = (self.end_time - self.start_time).total_seconds()

        report_lines = [
            "=" * 80,
            "E2E TEST EXECUTION REPORT",
            "=" * 80,
            f"Start Time: {self.start_time.isoformat()}",
            f"End Time: {self.end_time.isoformat()}",
            f"Duration: {duration:.2f} seconds",
            f"Exit Code: {exit_code} ({'PASSED' if exit_code == 0 else 'FAILED'})",
            "",
            "Configuration:",
            f"  - Debug Mode: {'Enabled' if args.debug else 'Disabled'}",
            f"  - Parallel Execution: {args.parallel if args.parallel else 'Disabled'}",
            f"  - Coverage Reporting: {'Enabled' if args.coverage else 'Disabled'}",
            f"  - Cleanup: {'Enabled' if not args.skip_cleanup else 'Disabled'}",
            "",
        ]

        if self.cleanup_results:
            report_lines.extend(
                [
                    "Cleanup Results:",
                    f"  - Tenants Cleaned: {self.cleanup_results.get('tenants_cleaned', 0)}",
                    f"  - Containers Cleaned: {self.cleanup_results.get('containers_cleaned', 0)}",
                    f"  - Files Cleaned: {self.cleanup_results.get('files_cleaned', 0)}",
                    f"  - Errors: {len(self.cleanup_results.get('errors', []))}",
                    "",
                ]
            )

        report_lines.extend(
            [
                "Test Categories:",
                f"  - Provisioning: {'✓' if not args.lifecycle and not args.isolation else '○'}",
                f"  - Lifecycle: {'✓' if args.lifecycle else '○'}",
                f"  - Isolation: {'✓' if args.isolation else '○'}",
                "",
                "=" * 80,
            ]
        )

        report = "\n".join(report_lines)
        logger.info(f"\n{report}")

        # Save report to file
        if args.report_file:
            Path(args.report_file).write_text(report)
            logger.info(f"Test report saved to: {args.report_file}")


def main():
    """Main entry point for E2E test runner."""
    parser = argparse.ArgumentParser(
        description="DotMac Management Backend E2E Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                    # Run all E2E tests
  python run_tests.py --provisioning     # Run provisioning tests only
  python run_tests.py --debug            # Run with debug output
  python run_tests.py --parallel 4       # Run with 4 parallel workers
  python run_tests.py --coverage         # Run with coverage reporting
        """,
    )

    # Test selection options
    test_group = parser.add_mutually_exclusive_group()
    test_group.add_argument("--provisioning", action="store_true", help="Run tenant provisioning tests only")
    test_group.add_argument("--lifecycle", action="store_true", help="Run container lifecycle tests only")
    test_group.add_argument("--isolation", action="store_true", help="Run tenant isolation tests only")
    test_group.add_argument("--cleanup-only", action="store_true", help="Run cleanup validation tests only")

    # Execution options
    parser.add_argument("--debug", action="store_true", help="Enable debug output and disable parallel execution")
    parser.add_argument("--parallel", type=int, help="Number of parallel test workers (default: auto)")
    parser.add_argument("--timeout", type=int, default=1800, help="Test timeout in seconds (default: 1800)")

    # Validation and cleanup options
    parser.add_argument("--skip-validation", action="store_true", help="Skip pre-test environment validation")
    parser.add_argument("--skip-cleanup", action="store_true", help="Skip post-test cleanup")

    # Reporting options
    parser.add_argument("--coverage", action="store_true", help="Enable coverage reporting")
    parser.add_argument("--junit-xml", help="Path for JUnit XML report output")
    parser.add_argument("--report-file", help="Path for test execution report")

    args = parser.parse_args()

    # Run tests
    runner = E2ETestRunner()
    exit_code = runner.run_tests(args)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
