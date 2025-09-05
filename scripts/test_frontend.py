#!/usr/bin/env python3
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent  # noqa: B008
sys.path.insert(0, str(project_root / "src"))

DRY Frontend Testing Script - Integrates with Poetry workflow
Runs frontend tests as part of unified testing strategy
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional


def run_command(cmd: list[str], cwd: Optional[str] = None) -> dict[str, Any]:
    """Run command and return result."""
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True)
        return {
            "success": True,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "stdout": e.stdout,
            "stderr": e.stderr,
            "returncode": e.returncode,
        }


def check_node_dependencies(frontend_dir: Path) -> bool:
    """Check if Node.js dependencies are installed."""
    node_modules = frontend_dir / "node_modules"
    return node_modules.exists()


def install_frontend_dependencies(frontend_dir: Path) -> bool:
    """Install frontend dependencies using pnpm."""
    print("📦 Installing frontend dependencies...")

    # Check if pnpm is available
    pnpm_check = run_command(["which", "pnpm"])
    if not pnpm_check["success"]:
        print("❌ pnpm not found. Installing...")
        npm_install = run_command(["npm", "install", "-g", "pnpm"])
        if not npm_install["success"]:
            print("❌ Failed to install pnpm")
            return False

    # Install dependencies
    result = run_command(["pnpm", "install"], cwd=str(frontend_dir))
    if result["success"]:
        print("✅ Frontend dependencies installed")
        return True
    else:
        print(f"❌ Failed to install dependencies: {result['stderr']}")
        return False


def run_frontend_tests(app_path: Path, test_type: str = "unit") -> dict[str, Any]:
    """Run frontend tests for specific app."""
    print(f"🧪 Running {test_type} tests for {app_path.name}...")

    commands = {
        "unit": ["pnpm", "test", "--passWithNoTests"],
        "integration": ["pnpm", "test:integration", "--passWithNoTests"],
        "e2e": ["pnpm", "test:e2e"],
        "coverage": ["pnpm", "test", "--coverage", "--passWithNoTests"],
    }

    cmd = commands.get(test_type, commands["unit"])
    result = run_command(cmd, cwd=str(app_path))

    if result["success"]:
        print(f"✅ {test_type} tests passed for {app_path.name}")
    else:
        print(f"❌ {test_type} tests failed for {app_path.name}")
        print(f"Error: {result['stderr']}")

    return result


def collect_coverage_report(app_path: Path) -> dict[str, Any]:
    """Collect coverage report from app."""
    coverage_file = app_path / "coverage" / "coverage-summary.json"

    if coverage_file.exists():
        try:
            with open(coverage_file) as f:
                coverage_data = json.load(f)

            # Extract total coverage
            total = coverage_data.get("total", {})
            return {
                "app": app_path.name,
                "lines": total.get("lines", {}).get("pct", 0),
                "functions": total.get("functions", {}).get("pct", 0),
                "branches": total.get("branches", {}).get("pct", 0),
                "statements": total.get("statements", {}).get("pct", 0),
            }
        except Exception as e:
            print(f"⚠️ Failed to read coverage for {app_path.name}: {e}")

    return {
        "app": app_path.name,
        "lines": 0,
        "functions": 0,
        "branches": 0,
        "statements": 0,
    }


def generate_frontend_test_report(results: list[dict[str, Any]], coverage_data: list[dict[str, Any]]) -> None:
    """Generate comprehensive frontend test report."""
    print("\n" + "=" * 60)
    print("🎯 FRONTEND TESTING SUMMARY")
    print("=" * 60)

    # Test results summary
    total_apps = len(results)
    passed_apps = sum(1 for r in results if r.get("success", False))
    failed_apps = total_apps - passed_apps

    print("📊 Test Results:")
    print(f"   • Total Apps: {total_apps}")
    print(f"   • Passed: {passed_apps}")
    print(f"   • Failed: {failed_apps}")
    print(f"   • Success Rate: {(passed_apps/total_apps)*100:.1f}%")

    # Coverage summary
    if coverage_data:
        avg_lines = sum(c["lines"] for c in coverage_data) / len(coverage_data)
        avg_functions = sum(c["functions"] for c in coverage_data) / len(coverage_data)
        avg_branches = sum(c["branches"] for c in coverage_data) / len(coverage_data)
        avg_statements = sum(c["statements"] for c in coverage_data) / len(coverage_data)

        print("\n📈 Coverage Summary:")
        print(f"   • Lines: {avg_lines:.1f}%")
        print(f"   • Functions: {avg_functions:.1f}%")
        print(f"   • Branches: {avg_branches:.1f}%")
        print(f"   • Statements: {avg_statements:.1f}%")

        print("\n📱 Per-App Coverage:")
        for cov in coverage_data:
            print(f"   • {cov['app']}: {cov['lines']:.1f}% lines, {cov['functions']:.1f}% functions")

    # DRY architecture benefits
    print("\n🏗️ DRY Architecture Benefits:")
    print(f"   • Shared test utilities across {total_apps} apps")
    print("   • Consistent testing patterns")
    print("   • Reduced code duplication")
    print("   • Unified reporting")

    print("=" * 60)


def main():
    """Main frontend testing workflow integrated with Poetry."""

    # Get project root
    project_root = Path(__file__).parent.parent
    frontend_dir = project_root / "frontend"

    if not frontend_dir.exists():
        print("❌ Frontend directory not found")
        sys.exit(1)

    print("🚀 Starting DRY Frontend Testing Suite")
    print(f"📁 Frontend directory: {frontend_dir}")

    # Check and install dependencies
    if not check_node_dependencies(frontend_dir):
        if not install_frontend_dependencies(frontend_dir):
            sys.exit(1)

    # Find all apps
    apps_dir = frontend_dir / "apps"
    frontend_apps = [d for d in apps_dir.iterdir() if d.is_dir() and (d / "package.json").exists()]

    print(f"📱 Found {len(frontend_apps)} frontend apps:")
    for app in frontend_apps:
        print(f"   • {app.name}")

    # Run tests for each app
    results = []
    coverage_data = []

    test_type = sys.argv[1] if len(sys.argv) > 1 else "unit"

    for app in frontend_apps:
        print(f"\n{'='*40}")
        print(f"Testing {app.name}")
        print(f"{'='*40}")

        # Run tests
        result = run_frontend_tests(app, test_type)
        results.append(
            {
                "app": app.name,
                "success": result["success"],
                "test_type": test_type,
                "output": result["stdout"],
            }
        )

        # Collect coverage if running coverage tests
        if test_type == "coverage":
            cov_data = collect_coverage_report(app)
            coverage_data.append(cov_data)

    # Generate report
    generate_frontend_test_report(results, coverage_data)

    # Exit with error code if any tests failed
    failed_count = sum(1 for r in results if not r.get("success", False))
    if failed_count > 0:
        print(f"\n❌ {failed_count} app(s) failed testing")
        sys.exit(1)
    else:
        print(f"\n✅ All {len(results)} apps passed testing")


if __name__ == "__main__":
    main()
