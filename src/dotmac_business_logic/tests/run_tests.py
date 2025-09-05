import logging

logger = logging.getLogger(__name__)

#!/usr/bin/env python3
"""
Test runner for DotMac Business Logic package.
Runs the comprehensive test suite with reporting.
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def run_test_suite():
    """Run the complete test suite."""
    test_results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {},
        "details": {},
    }

    # Test categories to run
    test_categories = {
        "unit_tests": "tests/unit/",
        "integration_tests": "tests/integration/",
        "performance_tests": "tests/performance/",
    }

    logger.info("🧪 Running DotMac Business Logic Test Suite")
    logger.info("=" * 50)

    total_passed = 0
    total_failed = 0

    for category, test_path in test_categories.items():
        logger.info(f"\n📋 Running {category.replace('_', ' ').title()}...")
        logger.info("-" * 30)

        try:
            # Run pytest for this category
            cmd = [
                sys.executable,
                "-m",
                "pytest",
                test_path,
                "-v",
                "--tb=short",
                "--durations=10",
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent
            )  # noqa: B008

            if result.returncode == 0:
                logger.info(f"✅ {category}: PASSED")
                status = "passed"
                passed = 1
                failed = 0
            else:
                logger.info(f"❌ {category}: FAILED")
                logger.info(f"Error output: {result.stderr[:500]}...")
                status = "failed"
                passed = 0
                failed = 1

            test_results["details"][category] = {
                "status": status,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
            }

            total_passed += passed
            total_failed += failed

        except Exception as e:
            logger.info(f"❌ {category}: ERROR - {e}")
            test_results["details"][category] = {"status": "error", "error": str(e)}
            total_failed += 1

    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("📊 TEST SUITE SUMMARY")
    logger.info("=" * 50)

    test_results["summary"] = {
        "total_categories": len(test_categories),
        "passed": total_passed,
        "failed": total_failed,
        "success_rate": (total_passed / len(test_categories)) * 100,
    }

    logger.info(f"Total Categories: {len(test_categories)}")
    logger.info(f"Passed: {total_passed}")
    logger.info(f"Failed: {total_failed}")
    logger.info(f"Success Rate: {test_results['summary']['success_rate']:.1f}%")

    # Overall result
    if total_failed == 0:
        logger.info("\n🎉 ALL TESTS PASSED!")
        logger.info("✅ Package is production ready from testing perspective")
        exit_code = 0
    else:
        logger.info(f"\n⚠️  {total_failed} TEST CATEGORIES FAILED")
        logger.info("❌ Package needs additional work before production")
        exit_code = 1

    # Save results
    results_file = Path(__file__).parent / "test_results.json"  # noqa: B008
    with open(results_file, "w") as f:
        json.dump(test_results, f, indent=2)

    logger.info(f"\n📝 Detailed results saved to: {results_file}")

    return exit_code


def check_test_dependencies():
    """Check if required test dependencies are available."""
    logger.info("🔍 Checking test dependencies...")

    required_packages = ["pytest", "pytest-asyncio", "pytest-cov", "psutil"]
    missing_packages = []

    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            logger.info(f"✅ {package}")
        except ImportError:
            logger.info(f"❌ {package} - MISSING")
            missing_packages.append(package)

    if missing_packages:
        logger.info(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        logger.info("Install with: pip install pytest pytest-asyncio pytest-cov psutil")
        return False

    logger.info("✅ All test dependencies available")
    return True


def main():
    """Main test runner."""
    logger.info("🚀 DotMac Business Logic Package - Test Runner")
    logger.info("=" * 60)

    # Check dependencies
    if not check_test_dependencies():
        logger.info("\n❌ Cannot run tests - missing dependencies")
        return 1

    # Run test suite
    return run_test_suite()


if __name__ == "__main__":
    sys.exit(main())
