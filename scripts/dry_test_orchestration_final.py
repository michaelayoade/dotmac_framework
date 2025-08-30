#!/usr/bin/env python3
"""
DRY Test Orchestration - Final Implementation

Comprehensive test orchestration system that:
- Leverages existing infrastructure (pytest, FastAPI, existing test patterns)
- Handles syntax errors gracefully with intelligent recommendations
- Implements DRY principles throughout
- Provides actionable remediation steps
- Works with the current codebase state
"""

import ast
import asyncio
import importlib.util
import io
import json
import logging
import os
import subprocess
import sys
import tokenize
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class SyntaxError:
    """Categorized syntax error."""

    file_path: str
    line_number: int
    error_type: str
    message: str
    category: str  # "fixable", "complex", "dependency"
    fix_suggestion: Optional[str] = None


@dataclass
class TestSuiteStatus:
    """Status of a test suite."""

    name: str
    path: str
    status: str  # "ready", "syntax_errors", "missing_deps", "import_errors"
    error_count: int = 0
    errors: List[SyntaxError] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


@dataclass
class OrchestrationResult:
    """Complete orchestration result."""

    timestamp: str
    total_duration: float
    syntax_analysis: Dict[str, Any]
    test_suites: List[TestSuiteStatus]
    dry_recommendations: List[Dict[str, Any]]
    remediation_plan: Dict[str, Any]
    success_metrics: Dict[str, Any]


class DRYTestOrchestrator:
    """
    Production-ready test orchestrator that implements DRY principles.

    Key Features:
    - Graceful syntax error handling with categorization
    - Leverages existing pytest, FastAPI test patterns
    - Intelligent remediation recommendations
    - Shared fixture generation
    - CI/CD ready reporting
    """

    def __init__(self, framework_root: str):
        """Initialize orchestrator."""
        self.framework_root = Path(framework_root)
        self.src_path = self.framework_root / "src"

        # Error categorization patterns
        self.error_categories = {
            "fixable": [
                "was never closed",
                "unexpected indent",
                "invalid syntax",
                "unmatched",
                "closing parenthesis",
            ],
            "complex": [
                "cannot contain assignment",
                "expected 'except' or 'finally'",
                "invalid decimal literal",
            ],
            "dependency": ["No module named", "ImportError", "ModuleNotFoundError"],
        }

        # DRY infrastructure components
        self.shared_patterns = {
            "pytest_fixtures": [],
            "common_imports": set(),
            "test_utilities": [],
            "mock_patterns": [],
        }

    def categorize_syntax_error(
        self, error_msg: str, file_path: str, line_no: int
    ) -> SyntaxError:
        """Categorize and provide fix suggestions for syntax errors."""

        # Determine category
        category = "complex"  # default
        for cat, patterns in self.error_categories.items():
            if any(pattern in error_msg for pattern in patterns):
                category = cat
                break

        # Generate fix suggestions based on category and error type
        fix_suggestion = None
        if "was never closed" in error_msg:
            if "(" in error_msg:
                fix_suggestion = "Add missing closing parenthesis ')' at end of line"
            elif "[" in error_msg:
                fix_suggestion = "Add missing closing bracket ']' at end of line"
            elif "{" in error_msg:
                fix_suggestion = "Add missing closing brace '}' at end of line"
        elif "unexpected indent" in error_msg:
            fix_suggestion = (
                "Remove extra indentation or add missing colon ':' on previous line"
            )
        elif "invalid syntax" in error_msg and "." in error_msg:
            fix_suggestion = "Check for missing comma, colon, or parenthesis on this or previous line"
        elif "No module named" in error_msg:
            module = error_msg.split("'")[-2] if "'" in error_msg else "unknown"
            fix_suggestion = f"Install missing dependency: pip install {module}"

        return SyntaxError(
            file_path=file_path,
            line_number=line_no,
            error_type=error_msg.split(":")[0] if ":" in error_msg else error_msg,
            message=error_msg,
            category=category,
            fix_suggestion=fix_suggestion,
        )

    def analyze_syntax_errors(self) -> Dict[str, Any]:
        """Comprehensive syntax error analysis with categorization."""
        logger.info("🔍 Analyzing syntax errors across codebase...")

        all_errors = []
        files_analyzed = 0

        for py_file in self.src_path.rglob("*.py"):
            files_analyzed += 1

            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Try to compile
                compile(content, str(py_file), "exec")

            except SyntaxError as e:
                syntax_error = self.categorize_syntax_error(
                    str(e.msg), str(py_file), e.lineno or 0
                )
                all_errors.append(syntax_error)

            except Exception as e:
                # Other errors (encoding, etc.)
                syntax_error = self.categorize_syntax_error(str(e), str(py_file), 0)
                all_errors.append(syntax_error)

        # Categorize errors
        error_summary = {
            "total_files": files_analyzed,
            "total_errors": len(all_errors),
            "by_category": {},
            "by_error_type": {},
            "fixable_count": 0,
            "errors": all_errors,
        }

        for error in all_errors:
            # Count by category
            cat = error.category
            error_summary["by_category"][cat] = (
                error_summary["by_category"].get(cat, 0) + 1
            )

            # Count by error type
            err_type = error.error_type
            error_summary["by_error_type"][err_type] = (
                error_summary["by_error_type"].get(err_type, 0) + 1
            )

            # Count fixable
            if error.category == "fixable":
                error_summary["fixable_count"] += 1

        logger.info(
            f"  📊 Found {len(all_errors)} syntax errors across {files_analyzed} files"
        )
        logger.info(f"  🔧 {error_summary['fixable_count']} are automatically fixable")

        return error_summary

    def discover_test_suites(
        self, syntax_analysis: Dict[str, Any]
    ) -> List[TestSuiteStatus]:
        """Discover test suites and categorize their status."""
        logger.info("🔍 Discovering test suites...")

        test_suites = []
        error_files = {error.file_path for error in syntax_analysis["errors"]}

        # Find all test directories
        for test_dir in self.src_path.rglob("test*"):
            if test_dir.is_dir() and test_dir.name in ["tests", "test"]:
                module_name = test_dir.parent.name
                suite_path = str(test_dir)

                # Count errors in this test suite
                suite_errors = [
                    error
                    for error in syntax_analysis["errors"]
                    if error.file_path.startswith(str(test_dir.parent))
                ]

                # Determine status
                if not suite_errors:
                    status = "ready"
                elif any(error.category == "dependency" for error in suite_errors):
                    status = "missing_deps"
                elif any(
                    error.category in ["fixable", "complex"] for error in suite_errors
                ):
                    status = "syntax_errors"
                else:
                    status = "import_errors"

                suite = TestSuiteStatus(
                    name=f"{module_name}_tests",
                    path=suite_path,
                    status=status,
                    error_count=len(suite_errors),
                    errors=suite_errors,
                )

                test_suites.append(suite)
                logger.info(
                    f"  📦 {suite.name}: {suite.status} ({suite.error_count} errors)"
                )

        return test_suites

    def generate_dry_recommendations(
        self, test_suites: List[TestSuiteStatus], syntax_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate DRY-focused recommendations."""
        recommendations = []

        # 1. Shared Test Infrastructure
        ready_suites = [suite for suite in test_suites if suite.status == "ready"]
        if len(ready_suites) > 2:
            recommendations.append(
                {
                    "type": "shared_infrastructure",
                    "priority": "high",
                    "title": "Create Shared Test Infrastructure",
                    "description": f"{len(ready_suites)} test suites are ready. Create shared conftest.py and fixtures.",
                    "implementation": {
                        "action": "create_shared_conftest",
                        "files": [
                            "tests/conftest.py",
                            "tests/fixtures/shared_fixtures.py",
                        ],
                        "benefits": [
                            "Reduces test duplication",
                            "Ensures consistent test setup",
                            "Faster test execution",
                        ],
                    },
                }
            )

        # 2. Systematic Syntax Error Fixing
        fixable_count = syntax_analysis["fixable_count"]
        if fixable_count > 0:
            recommendations.append(
                {
                    "type": "syntax_automation",
                    "priority": "high",
                    "title": "Automated Syntax Error Fixing",
                    "description": f"{fixable_count} syntax errors can be automatically fixed.",
                    "implementation": {
                        "action": "run_automated_fixer",
                        "command": "python3 scripts/targeted_syntax_fixer.py --auto-fix",
                        "estimated_fix_rate": "80-90%",
                    },
                }
            )

        # 3. Dependency Management
        dep_errors = [
            error
            for error in syntax_analysis["errors"]
            if error.category == "dependency"
        ]
        if dep_errors:
            missing_modules = set()
            for error in dep_errors:
                if "No module named" in error.message:
                    module = (
                        error.message.split("'")[-2] if "'" in error.message else None
                    )
                    if module:
                        missing_modules.add(module)

            recommendations.append(
                {
                    "type": "dependency_management",
                    "priority": "medium",
                    "title": "Consolidate Dependencies",
                    "description": f"Missing {len(missing_modules)} dependencies across test suites.",
                    "implementation": {
                        "action": "consolidate_requirements",
                        "missing_modules": list(missing_modules),
                        "files": ["requirements.txt", "pyproject.toml"],
                    },
                }
            )

        # 4. CI/CD Integration
        total_suites = len(test_suites)
        if total_suites > 5:
            recommendations.append(
                {
                    "type": "cicd_integration",
                    "priority": "medium",
                    "title": "CI/CD Test Orchestration",
                    "description": f"Integrate {total_suites} test suites into CI/CD pipeline.",
                    "implementation": {
                        "action": "setup_github_actions",
                        "files": [".github/workflows/test-orchestration.yml"],
                        "benefits": [
                            "Automated testing",
                            "Quality gates",
                            "Performance monitoring",
                        ],
                    },
                }
            )

        return recommendations

    def create_remediation_plan(
        self, syntax_analysis: Dict[str, Any], test_suites: List[TestSuiteStatus]
    ) -> Dict[str, Any]:
        """Create prioritized remediation plan."""

        # Phase 1: Quick wins (automated fixes)
        fixable_errors = [
            error for error in syntax_analysis["errors"] if error.category == "fixable"
        ]

        # Phase 2: Dependency resolution
        dep_errors = [
            error
            for error in syntax_analysis["errors"]
            if error.category == "dependency"
        ]

        # Phase 3: Complex manual fixes
        complex_errors = [
            error for error in syntax_analysis["errors"] if error.category == "complex"
        ]

        plan = {
            "phase_1_automated": {
                "title": "Automated Syntax Fixes",
                "error_count": len(fixable_errors),
                "estimated_time": "30-60 minutes",
                "success_rate": "85%",
                "tools": ["targeted_syntax_fixer.py", "AST-based fixers"],
                "errors_sample": fixable_errors[:10],  # Show first 10 as examples
            },
            "phase_2_dependencies": {
                "title": "Dependency Resolution",
                "error_count": len(dep_errors),
                "estimated_time": "15-30 minutes",
                "success_rate": "95%",
                "tools": ["pip install", "requirements.txt update"],
                "errors_sample": dep_errors[:5],
            },
            "phase_3_manual": {
                "title": "Complex Manual Fixes",
                "error_count": len(complex_errors),
                "estimated_time": "2-4 hours",
                "success_rate": "70%",
                "tools": ["Manual code review", "IDE assistance"],
                "errors_sample": complex_errors[:5],
            },
            "total_errors": syntax_analysis["total_errors"],
            "estimated_total_time": "3-5 hours",
            "projected_success_rate": "80%",
        }

        return plan

    async def run_test_collection_sample(
        self, ready_suites: List[TestSuiteStatus]
    ) -> Dict[str, Any]:
        """Run test collection on ready suites to demonstrate functionality."""

        if not ready_suites:
            return {"message": "No ready test suites available", "results": []}

        logger.info("🧪 Running test collection on ready suites...")

        collection_results = []

        # Sample up to 3 ready suites to avoid long execution
        sample_suites = ready_suites[:3]

        for suite in sample_suites:
            try:
                # Set up environment
                env = os.environ.copy()
                env["PYTHONPATH"] = str(self.src_path)

                # Run pytest collection
                cmd = [
                    sys.executable,
                    "-m",
                    "pytest",
                    suite.path,
                    "--collect-only",
                    "--quiet",
                    "--tb=no",
                ]

                result = subprocess.run(
                    cmd,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=str(self.framework_root),
                )

                collection_results.append(
                    {
                        "suite": suite.name,
                        "status": "success" if result.returncode == 0 else "error",
                        "output": result.stdout,
                        "error": result.stderr if result.returncode != 0 else None,
                    }
                )

            except subprocess.TimeoutExpired:
                collection_results.append(
                    {
                        "suite": suite.name,
                        "status": "timeout",
                        "error": "Collection timeout after 30s",
                    }
                )
            except Exception as e:
                collection_results.append(
                    {"suite": suite.name, "status": "error", "error": str(e)}
                )

        success_count = sum(
            1 for result in collection_results if result["status"] == "success"
        )

        return {
            "total_tested": len(collection_results),
            "successful": success_count,
            "success_rate": (
                success_count / len(collection_results) if collection_results else 0
            ),
            "results": collection_results,
        }

    async def execute_orchestration(self) -> OrchestrationResult:
        """Execute complete DRY test orchestration."""
        logger.info("🚀 Starting comprehensive DRY test orchestration...")
        start_time = datetime.now()

        # Step 1: Analyze syntax errors
        syntax_analysis = self.analyze_syntax_errors()

        # Step 2: Discover test suites
        test_suites = self.discover_test_suites(syntax_analysis)

        # Step 3: Generate DRY recommendations
        dry_recommendations = self.generate_dry_recommendations(
            test_suites, syntax_analysis
        )

        # Step 4: Create remediation plan
        remediation_plan = self.create_remediation_plan(syntax_analysis, test_suites)

        # Step 5: Test ready suites (sample)
        ready_suites = [suite for suite in test_suites if suite.status == "ready"]
        test_results = await self.run_test_collection_sample(ready_suites)

        # Step 6: Calculate success metrics
        total_duration = (datetime.now() - start_time).total_seconds()

        success_metrics = {
            "total_files": syntax_analysis["total_files"],
            "error_free_files": syntax_analysis["total_files"]
            - len({error.file_path for error in syntax_analysis["errors"]}),
            "ready_test_suites": len(ready_suites),
            "total_test_suites": len(test_suites),
            "fixable_errors": syntax_analysis["fixable_count"],
            "test_collection_success_rate": test_results.get("success_rate", 0),
            "orchestration_readiness": (
                "high"
                if len(ready_suites) > 5
                else "medium" if len(ready_suites) > 2 else "low"
            ),
        }

        result = OrchestrationResult(
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_duration=total_duration,
            syntax_analysis=syntax_analysis,
            test_suites=test_suites,
            dry_recommendations=dry_recommendations,
            remediation_plan=remediation_plan,
            success_metrics=success_metrics,
        )

        logger.info("✅ DRY test orchestration complete!")
        return result


def save_orchestration_report(
    result: OrchestrationResult, output_path: str = None
) -> str:
    """Save orchestration report to JSON file."""
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"dry_test_orchestration_report_{timestamp}.json"

    # Convert dataclasses to dicts for JSON serialization
    report_data = {
        "timestamp": result.timestamp,
        "total_duration": result.total_duration,
        "syntax_analysis": {
            **result.syntax_analysis,
            "errors": [asdict(error) for error in result.syntax_analysis["errors"]],
        },
        "test_suites": [asdict(suite) for suite in result.test_suites],
        "dry_recommendations": result.dry_recommendations,
        "remediation_plan": result.remediation_plan,
        "success_metrics": result.success_metrics,
    }

    with open(output_path, "w") as f:
        json.dump(report_data, f, indent=2)

    logger.info(f"📊 Full report saved to {output_path}")
    return output_path


async def main():
    """Main orchestration entry point."""
    framework_root = "/home/dotmac_framework"

    # Execute orchestration
    orchestrator = DRYTestOrchestrator(framework_root)
    result = await orchestrator.execute_orchestration()

    # Save detailed report
    report_path = save_orchestration_report(result)

    # Print executive summary
    print("\n" + "=" * 80)
    print("🚀 DRY TEST ORCHESTRATION - EXECUTIVE SUMMARY")
    print("=" * 80)

    print(f"📊 CODEBASE ANALYSIS:")
    print(f"  • Total Files: {result.success_metrics['total_files']}")
    print(f"  • Files with Syntax Errors: {result.syntax_analysis['total_errors']}")
    print(
        f"  • Automatically Fixable: {result.syntax_analysis['fixable_count']} ({result.syntax_analysis['fixable_count']/result.syntax_analysis['total_errors']*100:.1f}%)"
    )

    print(f"\n🧪 TEST INFRASTRUCTURE:")
    print(f"  • Total Test Suites: {result.success_metrics['total_test_suites']}")
    print(f"  • Ready for Testing: {result.success_metrics['ready_test_suites']}")
    print(
        f"  • Orchestration Readiness: {result.success_metrics['orchestration_readiness'].upper()}"
    )

    print(f"\n🎯 DRY RECOMMENDATIONS ({len(result.dry_recommendations)}):")
    for rec in result.dry_recommendations:
        print(f"  • {rec['title']} ({rec['priority']} priority)")

    print(f"\n📋 REMEDIATION PLAN:")
    for phase_name, phase in result.remediation_plan.items():
        if phase_name.startswith("phase_"):
            print(
                f"  • {phase['title']}: {phase['error_count']} errors (~{phase['estimated_time']})"
            )

    print(f"\n⏱️  EXECUTION:")
    print(f"  • Total Duration: {result.total_duration:.2f}s")
    print(f"  • Report: {report_path}")

    print(f"\n🚀 NEXT STEPS:")
    if result.success_metrics["orchestration_readiness"] == "high":
        print("  ✅ Ready for production test orchestration")
        print("  ✅ Implement shared test infrastructure")
        print("  ✅ Set up CI/CD integration")
    elif result.success_metrics["orchestration_readiness"] == "medium":
        print("  🔧 Fix syntax errors using automated tools")
        print("  🔧 Resolve dependency issues")
        print("  ✅ Create shared test fixtures for ready suites")
    else:
        print("  ❌ Systematic syntax error fixing required")
        print("  ❌ Dependency resolution needed")
        print("  ❌ Manual code review for complex issues")

    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
