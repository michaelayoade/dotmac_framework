#!/usr/bin/env python3
"""
Simple Package Test Runner
Pragmatic approach to test packages individually without Poetry dependency hell.
"""

import os
import subprocess
import sys
import time
from pathlib import Path


def run_package_tests(package_dir: Path) -> tuple[str, bool, str, float]:
    """Run tests for a single package."""
    package_name = package_dir.name
    tests_dir = package_dir / "tests"
    src_dir = package_dir / "src"

    if not tests_dir.exists():
        return package_name, True, "No tests directory found - skipped", 0.0

    # Set up environment for the package
    env = os.environ.copy()
    if src_dir.exists():
        env["PYTHONPATH"] = str(src_dir)

    start_time = time.time()

    try:
        result = subprocess.run(
            ["python3", "-m", "pytest", str(tests_dir), "-v", "--tb=short", "--no-cov"],
            cwd=str(package_dir),
            env=env,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes max per package
        )

        execution_time = time.time() - start_time
        success = result.returncode == 0

        if success:
            # Count passed tests
            lines = result.stdout.split("\n")
            passed_line = [
                line for line in lines if "passed" in line and ("failed" in line or "error" in line or "100%" in line)
            ]
            output = passed_line[0] if passed_line else f"Tests passed in {execution_time:.1f}s"
        else:
            # Show failure summary
            output = f"FAILED (exit code {result.returncode})\n{result.stdout}\n{result.stderr}"

        return package_name, success, output, execution_time

    except subprocess.TimeoutExpired:
        execution_time = time.time() - start_time
        return package_name, False, "TIMEOUT after 5 minutes", execution_time
    except Exception as e:
        execution_time = time.time() - start_time
        return package_name, False, f"ERROR: {e}", execution_time


def main():
    """Run tests for all packages."""
    print("🧪 Simple Package Test Runner")
    print("=" * 50)

    packages_dir = Path("packages")
    if not packages_dir.exists():
        print("❌ packages/ directory not found")
        sys.exit(1)

    # Find all packages with tests
    test_packages = []
    for package_dir in packages_dir.iterdir():
        if package_dir.is_dir() and (package_dir / "tests").exists():
            test_packages.append(package_dir)

    if not test_packages:
        print("❌ No packages with tests found")
        sys.exit(1)

    print(f"📋 Found {len(test_packages)} packages with tests")

    results = []
    total_time = time.time()

    # Test each package
    for package_dir in sorted(test_packages):
        print(f"\n🔍 Testing {package_dir.name}...")
        name, success, output, exec_time = run_package_tests(package_dir)
        results.append((name, success, output, exec_time))

        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"   {status} ({exec_time:.1f}s)")
        if not success and len(output) < 200:
            print(f"   Error: {output.strip()}")

    total_time = time.time() - total_time

    # Summary
    print("\n" + "=" * 60)
    print("📊 PACKAGE TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, success, _, _ in results if success)
    total = len(results)

    print(f"Overall: {passed}/{total} packages passed ({total_time:.1f}s total)")

    # Detailed results
    print("\n📋 Package Results:")
    for name, success, output, exec_time in results:
        status = "✅" if success else "❌"
        print(f"  {status} {name:<25} ({exec_time:.1f}s)")

    # Show failures
    failures = [(name, output) for name, success, output, _ in results if not success]
    if failures:
        print(f"\n❌ Failed Packages ({len(failures)}):")
        for name, output in failures:
            print(f"\n  {name}:")
            # Show first few lines of error
            error_lines = output.split("\n")[:3]
            for line in error_lines:
                if line.strip():
                    print(f"    {line}")

    # Exit code
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
