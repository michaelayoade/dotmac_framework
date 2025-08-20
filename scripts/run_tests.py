#!/usr/bin/env python3
"""
Standardized Test Execution Script for DotMac Platform

This script provides a unified interface for running tests across all services
following the established test organization standards.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List


class TestRunner:
    """Unified test runner for DotMac Platform."""

    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path)
        self.services = self._discover_services()

        # Test categories with execution order
        self.test_categories = {
            "unit": {"order": 1, "parallel": True, "timeout": 300},
            "integration": {"order": 2, "parallel": True, "timeout": 600},
            "contracts": {"order": 3, "parallel": False, "timeout": 300},
            "smoke": {"order": 4, "parallel": False, "timeout": 180},
            "e2e": {"order": 5, "parallel": False, "timeout": 1800},
            "performance": {"order": 6, "parallel": False, "timeout": 3600}
        }

    def _discover_services(self) -> List[str]:
        """Discover all DotMac services."""
        services = []
        for item in self.root_path.iterdir():
            if (item.is_dir() and
                item.name.startswith("dotmac_") and
                not item.name.endswith("_framework")):
                services.append(item.name)
        return sorted(services)

    def run_tests(self,
                  categories: List[str] = None,
                  services: List[str] = None,
                  parallel: bool = True,
                  coverage: bool = True,
                  fail_fast: bool = False,
                  verbose: bool = False) -> bool:
        """
        Run tests according to specified criteria.

        Args:
            categories: Test categories to run (unit, integration, etc.)
            services: Services to test (all if None)
            parallel: Enable parallel execution where supported
            coverage: Enable coverage reporting
            fail_fast: Stop on first failure
            verbose: Enable verbose output

        Returns:
            bool: True if all tests passed, False otherwise
        """
        if categories is None:
            categories = ["unit", "integration", "smoke"]

        if services is None:
            services = self.services

        print("🚀 Running DotMac Platform Tests")
        print(f"📦 Services: {', '.join(services)}")
        print(f"🧪 Categories: {', '.join(categories)}")
        print(f"⚡ Parallel: {parallel}")
        print(f"📊 Coverage: {coverage}")
        print("=" * 80)

        total_start_time = time.time()
        results = {}
        overall_success = True

        # Sort categories by execution order
        sorted_categories = sorted(categories, key=lambda c: self.test_categories.get(c, {}).get("order", 999))

        for category in sorted_categories:
            category_start_time = time.time()
            print(f"\n🔧 Running {category.upper()} tests...")

            success = self._run_category_tests(
                category=category,
                services=services,
                parallel=parallel,
                coverage=coverage,
                fail_fast=fail_fast,
                verbose=verbose
            )

            category_duration = time.time() - category_start_time
            results[category] = {
                "success": success,
                "duration": category_duration
            }

            if success:
                print(f"✅ {category.upper()} tests passed in {category_duration:.2f}s")
            else:
                print(f"❌ {category.upper()} tests failed in {category_duration:.2f}s")
                overall_success = False

                if fail_fast:
                    print("🛑 Stopping due to --fail-fast")
                    break

        total_duration = time.time() - total_start_time

        # Print summary
        print("\n" + "=" * 80)
        print("📋 TEST EXECUTION SUMMARY")
        print("=" * 80)

        for category, result in results.items():
            status = "✅ PASSED" if result["success"] else "❌ FAILED"
            print(f"{category.upper():12} | {status} | {result['duration']:6.2f}s")

        print(f"\n⏱️  Total execution time: {total_duration:.2f}s")
        print(f"🎯 Overall result: {'✅ ALL PASSED' if overall_success else '❌ SOME FAILED'}")

        return overall_success

    def _run_category_tests(self,
                           category: str,
                           services: List[str],
                           parallel: bool,
                           coverage: bool,
                           fail_fast: bool,
                           verbose: bool) -> bool:
        """Run tests for a specific category."""
        cmd = self._build_pytest_command(
            category=category,
            services=services,
            parallel=parallel,
            coverage=coverage,
            fail_fast=fail_fast,
            verbose=verbose
        )

        if verbose:
            print(f"💻 Command: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                check=False, cwd=self.root_path,
                capture_output=not verbose,
                text=True,
                timeout=self.test_categories.get(category, {}).get("timeout", 600)
            )

            if not verbose and result.returncode != 0:
                print(f"📝 STDOUT:\n{result.stdout}")
                print(f"🚨 STDERR:\n{result.stderr}")

            return result.returncode == 0

        except subprocess.TimeoutExpired:
            print(f"⏰ {category.upper()} tests timed out")
            return False
        except Exception as e:
            print(f"💥 Error running {category} tests: {e}")
            return False

    def _build_pytest_command(self,
                             category: str,
                             services: List[str],
                             parallel: bool,
                             coverage: bool,
                             fail_fast: bool,
                             verbose: bool) -> List[str]:
        """Build pytest command for given parameters."""
        cmd = ["pytest"]

        # Add test paths
        test_paths = []
        for service in services:
            service_tests = self.root_path / service / "tests"
            if service_tests.exists():
                category_tests = service_tests / category
                if category_tests.exists():
                    test_paths.append(str(category_tests))

        if test_paths:
            cmd.extend(test_paths)
        else:
            # Fallback to marker-based selection
            cmd.extend(["-m", category])

        # Add markers
        cmd.extend(["-m", category])

        # Parallel execution
        if parallel and self.test_categories.get(category, {}).get("parallel", False):
            cmd.extend(["-n", "auto"])

        # Coverage
        if coverage:
            for service in services:
                cmd.extend(["--cov", service.replace("dotmac_", "dotmac_")])
            cmd.extend(["--cov-report", "term-missing"])
            cmd.extend(["--cov-report", f"html:htmlcov/{category}"])

        # Fail fast
        if fail_fast:
            cmd.extend(["--maxfail", "1"])

        # Verbosity
        if verbose:
            cmd.extend(["-v"])
        else:
            cmd.extend(["-q"])

        # Additional options
        cmd.extend(["--tb=short"])
        cmd.extend(["--strict-markers"])

        return cmd

    def run_service_tests(self, service: str, category: str = None) -> bool:
        """Run tests for a specific service."""
        if service not in self.services:
            print(f"❌ Service '{service}' not found")
            return False

        categories = [category] if category else list(self.test_categories.keys())

        return self.run_tests(
            categories=categories,
            services=[service],
            parallel=True,
            coverage=True,
            fail_fast=False,
            verbose=True
        )

    def run_quick_tests(self) -> bool:
        """Run quick test suite (unit + smoke tests)."""
        return self.run_tests(
            categories=["unit", "smoke"],
            parallel=True,
            coverage=True,
            fail_fast=True,
            verbose=False
        )

    def run_full_suite(self) -> bool:
        """Run complete test suite."""
        return self.run_tests(
            categories=list(self.test_categories.keys()),
            parallel=True,
            coverage=True,
            fail_fast=False,
            verbose=False
        )

    def run_ci_tests(self) -> bool:
        """Run CI-appropriate test suite."""
        return self.run_tests(
            categories=["unit", "integration", "contracts"],
            parallel=True,
            coverage=True,
            fail_fast=True,
            verbose=False
        )

    def list_tests(self, services: List[str] = None) -> Dict:
        """List available tests by category and service."""
        if services is None:
            services = self.services

        test_inventory = {}

        for service in services:
            service_tests = self.root_path / service / "tests"
            if not service_tests.exists():
                continue

            test_inventory[service] = {}

            for category in self.test_categories.keys():
                category_path = service_tests / category
                if category_path.exists():
                    test_files = list(category_path.glob("test_*.py"))
                    test_inventory[service][category] = [f.name for f in test_files]

        return test_inventory

    def validate_test_structure(self) -> Dict:
        """Validate test structure against standards."""
        issues = []
        recommendations = []

        for service in self.services:
            service_tests = self.root_path / service / "tests"

            if not service_tests.exists():
                issues.append(f"Service {service} has no tests directory")
                continue

            # Check for required directories
            if not (service_tests / "unit").exists():
                issues.append(f"Service {service} missing unit tests directory")

            if not (service_tests / "integration").exists():
                recommendations.append(f"Service {service} should have integration tests")

            # Check for conftest.py
            if not (service_tests / "conftest.py").exists():
                recommendations.append(f"Service {service} should have conftest.py")

        return {
            "issues": issues,
            "recommendations": recommendations
        }


def main():  # noqa: C901
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description="DotMac Platform Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --quick                           # Run unit + smoke tests
  %(prog)s --full                            # Run complete test suite
  %(prog)s --ci                              # Run CI test suite
  %(prog)s --category unit --service platform  # Run unit tests for platform
  %(prog)s --list                            # List available tests
  %(prog)s --validate                        # Validate test structure
        """
    )

    # Preset commands
    preset_group = parser.add_mutually_exclusive_group()
    preset_group.add_argument("--quick", action="store_true", help="Run quick test suite (unit + smoke)")
    preset_group.add_argument("--full", action="store_true", help="Run complete test suite")
    preset_group.add_argument("--ci", action="store_true", help="Run CI test suite")

    # Custom options
    parser.add_argument("--category", choices=["unit", "integration", "e2e", "performance", "contracts", "smoke"],
                       help="Test category to run")
    parser.add_argument("--service", help="Specific service to test")
    parser.add_argument("--parallel", action="store_true", default=True, help="Enable parallel execution")
    parser.add_argument("--no-parallel", action="store_false", dest="parallel", help="Disable parallel execution")
    parser.add_argument("--coverage", action="store_true", default=True, help="Enable coverage reporting")
    parser.add_argument("--no-coverage", action="store_false", dest="coverage", help="Disable coverage reporting")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on first failure")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    # Utility commands
    parser.add_argument("--list", action="store_true", help="List available tests")
    parser.add_argument("--validate", action="store_true", help="Validate test structure")

    # General options
    parser.add_argument("--root", default=".", help="Root directory of DotMac framework")

    args = parser.parse_args()

    runner = TestRunner(args.root)

    # Handle utility commands
    if args.list:
        test_inventory = runner.list_tests()
        print("📋 Available Tests:")
        for service, categories in test_inventory.items():
            print(f"\n{service}:")
            for category, files in categories.items():
                print(f"  {category}: {len(files)} files")
        return 0

    if args.validate:
        validation = runner.validate_test_structure()
        print("🔍 Test Structure Validation:")
        if validation["issues"]:
            print("\n❌ Issues:")
            for issue in validation["issues"]:
                print(f"  • {issue}")
        if validation["recommendations"]:
            print("\n💡 Recommendations:")
            for rec in validation["recommendations"]:
                print(f"  • {rec}")
        if not validation["issues"] and not validation["recommendations"]:
            print("✅ Test structure looks good!")
        return 0

    # Handle preset commands
    success = False

    if args.quick:
        success = runner.run_quick_tests()
    elif args.full:
        success = runner.run_full_suite()
    elif args.ci:
        success = runner.run_ci_tests()
    elif args.service and args.category:
        success = runner.run_service_tests(args.service, args.category)
    elif args.service:
        success = runner.run_service_tests(args.service)
    elif args.category:
        success = runner.run_tests(
            categories=[args.category],
            parallel=args.parallel,
            coverage=args.coverage,
            fail_fast=args.fail_fast,
            verbose=args.verbose
        )
    else:
        # Default: run quick tests
        success = runner.run_quick_tests()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
