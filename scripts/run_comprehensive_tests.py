#!/usr/bin/env python3
"""
Comprehensive Test Execution Script for DotMac Framework

This script orchestrates the execution of all test suites with:
- Parallel test execution for performance
- Coverage analysis and reporting
- Test result aggregation
- CI/CD integration
- Failure analysis and recommendations
"""

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TestResult:
    """Test execution result."""

    suite: str
    passed: int
    failed: int
    errors: int
    skipped: int
    execution_time: float
    coverage_percent: float
    exit_code: int
    error_details: list[str]


@dataclass
class TestSuiteConfig:
    """Configuration for a test suite."""

    name: str
    command: list[str]
    timeout: int
    parallel: bool
    critical: bool
    coverage_target: float


class ComprehensiveTestRunner:
    """Orchestrates comprehensive test execution."""

    def __init__(self, args):
        self.args = args
        self.results: dict[str, TestResult] = {}
        self.start_time = time.time()

        # Configure test suites
        self.test_suites = {
            "unit": TestSuiteConfig(
                name="Unit Tests",
                command=["python3", "-m", "pytest", "tests/unit", "-v", "--tb=short"],
                timeout=300,  # 5 minutes
                parallel=True,
                critical=True,
                coverage_target=85.0,
            ),
            "platform-services": TestSuiteConfig(
                name="Platform Services Tests",
                command=["python3", "scripts/test_platform_services.py"],
                timeout=300,  # 5 minutes
                parallel=False,
                critical=True,
                coverage_target=80.0,
            ),
            "integration": TestSuiteConfig(
                name="Integration Tests",
                command=["python3", "-m", "pytest", "tests/integration", "-v", "--tb=short"],
                timeout=600,  # 10 minutes
                parallel=True,
                critical=True,
                coverage_target=80.0,
            ),
            "security": TestSuiteConfig(
                name="Security Tests",
                command=["python3", "-m", "pytest", "tests/unit/security", "-v", "--tb=short", "-m", "security"],
                timeout=300,
                parallel=False,  # Security tests run sequentially for isolation
                critical=True,
                coverage_target=95.0,
            ),
            "e2e": TestSuiteConfig(
                name="End-to-End Tests",
                command=["python3", "-m", "pytest", "tests/e2e", "-v", "--tb=long", "-m", "e2e"],
                timeout=1800,  # 30 minutes
                parallel=False,
                critical=False,  # Optional for PR checks
                coverage_target=70.0,
            ),
            "performance": TestSuiteConfig(
                name="Performance Tests",
                command=[
                    "python3",
                    "-m",
                    "pytest",
                    "tests/performance",
                    "-v",
                    "--benchmark-json=test-reports/benchmark.json",
                ],
                timeout=900,  # 15 minutes
                parallel=False,
                critical=False,
                coverage_target=60.0,
            ),
        }

    def run_all_tests(self) -> bool:
        """Run all configured test suites."""
        print("🚀 Starting Comprehensive Test Execution")
        print("=" * 50)

        # Filter test suites based on arguments
        suites_to_run = self._filter_test_suites()

        if not suites_to_run:
            print("❌ No test suites selected for execution")
            return False

        # Setup test environment
        self._setup_test_environment()

        # Run test suites
        success = True
        for suite_name in suites_to_run:
            suite_config = self.test_suites[suite_name]

            print(f"\n📋 Running {suite_config.name}...")
            result = self._run_test_suite(suite_name, suite_config)
            self.results[suite_name] = result

            if result.exit_code != 0 and suite_config.critical:
                success = False
                print(f"❌ Critical test suite {suite_config.name} failed")

        # Generate comprehensive report
        self._generate_final_report()

        # Run coverage analysis
        if not self.args.skip_coverage:
            self._run_coverage_analysis()

        return success

    def _filter_test_suites(self) -> list[str]:
        """Filter test suites based on command line arguments."""
        if self.args.suites:
            # Specific suites requested
            requested_suites = self.args.suites.split(",")
            return [s.strip() for s in requested_suites if s.strip() in self.test_suites]

        if self.args.quick:
            # Quick test mode - only unit, platform-services, and integration
            return ["unit", "platform-services", "integration"]

        if self.args.critical_only:
            # Only critical test suites
            return [name for name, config in self.test_suites.items() if config.critical]

        # All test suites by default
        return list(self.test_suites.keys())

    def _setup_test_environment(self):
        """Setup test environment."""
        print("⚙️ Setting up test environment...")

        # Create test report directories
        os.makedirs("test-reports", exist_ok=True)
        os.makedirs("test-reports/coverage-html", exist_ok=True)

        # Set environment variables for testing
        os.environ["ENVIRONMENT"] = "test"
        os.environ["LOG_LEVEL"] = "DEBUG" if self.args.verbose else "INFO"
        os.environ["PYTHONPATH"] = "src"

        # Clean up previous test artifacts
        self._cleanup_previous_results()

    def _cleanup_previous_results(self):
        """Clean up previous test results."""
        artifacts_to_clean = [
            ".coverage",
            "test-reports/junit.xml",
            "test-reports/coverage.json",
            "test-reports/report.html",
        ]

        for artifact in artifacts_to_clean:
            if os.path.exists(artifact):
                try:
                    os.remove(artifact)
                except OSError:
                    pass  # Ignore cleanup failures

    def _run_test_suite(self, suite_name: str, config: TestSuiteConfig) -> TestResult:
        """Run a single test suite."""
        start_time = time.time()

        # Build command with additional arguments
        command = config.command.copy()

        if self.args.verbose:
            command.append("-vvv")

        if self.args.no_capture:
            command.append("-s")

        if config.parallel and not self.args.no_parallel:
            command.extend(["-n", "auto"])  # pytest-xdist for parallel execution

        # Add coverage reporting
        command.extend(["--cov=src", "--cov-report=term-missing", "--cov-append"])

        print(f"  Command: {' '.join(command)}")

        try:
            # Execute the test suite
            result = subprocess.run(command, timeout=config.timeout, capture_output=True, text=True, cwd=os.getcwd())

            execution_time = time.time() - start_time

            # Parse test results
            passed, failed, errors, skipped = self._parse_pytest_output(result.stdout)
            coverage_percent = self._extract_coverage_percent(result.stdout)
            error_details = self._extract_error_details(result.stdout, result.stderr)

            test_result = TestResult(
                suite=config.name,
                passed=passed,
                failed=failed,
                errors=errors,
                skipped=skipped,
                execution_time=execution_time,
                coverage_percent=coverage_percent,
                exit_code=result.returncode,
                error_details=error_details,
            )

            # Print suite summary
            self._print_suite_summary(test_result)

            return test_result

        except subprocess.TimeoutExpired:
            print(f"  ⏰ Test suite timed out after {config.timeout} seconds")
            return TestResult(
                suite=config.name,
                passed=0,
                failed=1,
                errors=1,
                skipped=0,
                execution_time=config.timeout,
                coverage_percent=0.0,
                exit_code=1,
                error_details=["Test suite timed out"],
            )

        except Exception as e:
            print(f"  ❌ Error running test suite: {e}")
            return TestResult(
                suite=config.name,
                passed=0,
                failed=1,
                errors=1,
                skipped=0,
                execution_time=0.0,
                coverage_percent=0.0,
                exit_code=1,
                error_details=[str(e)],
            )

    def _parse_pytest_output(self, output: str) -> tuple[int, int, int, int]:
        """Parse pytest output to extract test counts."""
        passed = failed = errors = skipped = 0

        # Look for pytest summary line
        lines = output.split("\n")
        for line in lines:
            if "passed" in line and "failed" in line:
                # Parse line like "10 passed, 2 failed, 1 error, 3 skipped"
                parts = line.split(",")
                for part in parts:
                    part = part.strip()
                    if "passed" in part:
                        passed = int(part.split()[0])
                    elif "failed" in part:
                        failed = int(part.split()[0])
                    elif "error" in part:
                        errors = int(part.split()[0])
                    elif "skipped" in part:
                        skipped = int(part.split()[0])
                break

        return passed, failed, errors, skipped

    def _extract_coverage_percent(self, output: str) -> float:
        """Extract coverage percentage from pytest output."""
        lines = output.split("\n")
        for line in lines:
            if "TOTAL" in line and "%" in line:
                # Look for coverage total line
                parts = line.split()
                for part in parts:
                    if "%" in part:
                        try:
                            return float(part.rstrip("%"))
                        except ValueError:
                            continue
        return 0.0

    def _extract_error_details(self, stdout: str, stderr: str) -> list[str]:
        """Extract error details from test output."""
        errors = []

        # Parse FAILED test details from stdout
        lines = stdout.split("\n")
        in_failure = False
        current_failure = []

        for line in lines:
            if line.startswith("FAILED "):
                if current_failure:
                    errors.append("\n".join(current_failure))
                current_failure = [line]
                in_failure = True
            elif in_failure and (line.startswith("=") or line.startswith("FAILED ")):
                in_failure = False
                if current_failure:
                    errors.append("\n".join(current_failure))
                current_failure = []
            elif in_failure:
                current_failure.append(line)

        # Add any remaining failure
        if current_failure:
            errors.append("\n".join(current_failure))

        # Add stderr if present
        if stderr.strip():
            errors.append(f"STDERR: {stderr}")

        return errors

    def _print_suite_summary(self, result: TestResult):
        """Print summary for a test suite."""
        status = "✅ PASSED" if result.exit_code == 0 else "❌ FAILED"
        print(f"  {status}")
        print(
            f"  Tests: {result.passed} passed, {result.failed} failed, {result.errors} errors, {result.skipped} skipped"
        )
        print(f"  Coverage: {result.coverage_percent:.1f}%")
        print(f"  Time: {result.execution_time:.1f}s")

    def _generate_final_report(self):
        """Generate final comprehensive test report."""
        total_time = time.time() - self.start_time

        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE TEST EXECUTION SUMMARY")
        print("=" * 60)

        # Overall statistics
        total_passed = sum(r.passed for r in self.results.values())
        total_failed = sum(r.failed for r in self.results.values())
        total_errors = sum(r.errors for r in self.results.values())
        total_skipped = sum(r.skipped for r in self.results.values())

        overall_success = all(r.exit_code == 0 for r in self.results.values())

        print(f"Overall Status: {'✅ PASSED' if overall_success else '❌ FAILED'}")
        print(f"Total Tests: {total_passed + total_failed + total_errors}")
        print(f"  Passed: {total_passed}")
        print(f"  Failed: {total_failed}")
        print(f"  Errors: {total_errors}")
        print(f"  Skipped: {total_skipped}")
        print(f"Total Execution Time: {total_time:.1f}s")

        # Per-suite breakdown
        print("\n📋 Test Suite Breakdown:")
        for suite_name, result in self.results.items():
            status = "✅" if result.exit_code == 0 else "❌"
            config = self.test_suites[suite_name]
            coverage_status = "✅" if result.coverage_percent >= config.coverage_target else "❌"

            print(f"  {status} {result.suite}")
            print(f"    Tests: {result.passed}/{result.passed + result.failed + result.errors}")
            print(
                f"    Coverage: {coverage_status} {result.coverage_percent:.1f}% (target: {config.coverage_target:.1f}%)"
            )
            print(f"    Time: {result.execution_time:.1f}s")

        # Failure details
        failed_suites = [name for name, result in self.results.items() if result.exit_code != 0]
        if failed_suites:
            print(f"\n❌ Failed Test Suites ({len(failed_suites)}):")
            for suite_name in failed_suites:
                result = self.results[suite_name]
                print(f"  {result.suite}:")
                for i, error in enumerate(result.error_details[:3]):  # Show first 3 errors
                    print(f"    Error {i+1}: {error[:100]}...")

        # Save detailed results to JSON
        self._save_json_results()

    def _save_json_results(self):
        """Save detailed test results to JSON file."""
        results_data = {
            "timestamp": datetime.now().isoformat(),
            "overall_success": all(r.exit_code == 0 for r in self.results.values()),
            "total_execution_time": time.time() - self.start_time,
            "suites": {},
        }

        for suite_name, result in self.results.items():
            results_data["suites"][suite_name] = {
                "name": result.suite,
                "passed": result.passed,
                "failed": result.failed,
                "errors": result.errors,
                "skipped": result.skipped,
                "execution_time": result.execution_time,
                "coverage_percent": result.coverage_percent,
                "exit_code": result.exit_code,
                "error_count": len(result.error_details),
            }

        with open("test-reports/comprehensive_results.json", "w") as f:
            json.dump(results_data, f, indent=2)

    def _run_coverage_analysis(self):
        """Run comprehensive coverage analysis."""
        print("\n📈 Running Coverage Analysis...")

        try:
            # Import and run our comprehensive coverage system (optional)
            sys.path.append("tests/coverage")
            import importlib

            try:
                CoverageIntegration = importlib.import_module("test_coverage_config").CoverageIntegration
            except Exception:
                print("⚠️ Coverage analysis module not available")
                return

            success = CoverageIntegration.run_coverage_analysis()
            regression_check = CoverageIntegration.check_coverage_regression()

            if not success:
                print("❌ Coverage targets not met")
            if not regression_check:
                print("❌ Coverage regression detected")

        except Exception as e:
            print(f"❌ Coverage analysis failed: {e}")


def main():
    """Main entry point for comprehensive test runner."""
    parser = argparse.ArgumentParser(description="Run comprehensive tests for DotMac Framework")

    parser.add_argument(
        "--suites", help="Comma-separated list of test suites to run (unit,integration,security,e2e,performance)"
    )
    parser.add_argument("--quick", action="store_true", help="Run only unit and integration tests")
    parser.add_argument("--critical-only", action="store_true", help="Run only critical test suites")
    parser.add_argument("--skip-coverage", action="store_true", help="Skip coverage analysis")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--no-capture", "-s", action="store_true", help="Don't capture output (for debugging)")
    parser.add_argument("--no-parallel", action="store_true", help="Disable parallel test execution")

    args = parser.parse_args()

    # Run comprehensive tests
    runner = ComprehensiveTestRunner(args)
    success = runner.run_all_tests()

    # Exit with appropriate code for CI/CD
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
