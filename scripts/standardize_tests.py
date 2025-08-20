#!/usr/bin/env python3
"""
Test Organization Standardization Script

This script analyzes the current test structure across all DotMac services
and provides recommendations for standardizing test organization according
to the established standards.
"""

import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class TestFile:
    """Represents a test file with metadata."""
    path: Path
    relative_path: Path
    service: str
    category: str
    name: str
    size: int
    test_count: int
    markers: List[str]
    imports: List[str]
    classes: List[str]


@dataclass
class TestAnalysis:
    """Analysis results for test organization."""
    total_files: int
    files_by_category: Dict[str, int]
    files_by_service: Dict[str, int]
    naming_violations: List[str]
    organization_issues: List[str]
    recommendations: List[str]


class TestStandardizer:
    """Analyzes and standardizes test organization."""

    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.services = self._discover_services()
        self.test_files: List[TestFile] = []

        # Standard test categories
        self.standard_categories = {
            "unit", "integration", "e2e", "performance",
            "contracts", "smoke", "fixtures", "helpers"
        }

        # Expected test file patterns
        self.test_patterns = {
            "unit": r"test_.*\.py$",
            "integration": r"test_.*_integration\.py$",
            "e2e": r"test_.*_e2e\.py$",
            "performance": r"test_.*_performance\.py$",
            "contracts": r"test_.*_contracts\.py$",
            "smoke": r"test_.*_smoke\.py$"
        }

    def _discover_services(self) -> List[str]:
        """Discover all DotMac services."""
        services = []
        for item in self.root_path.iterdir():
            if (item.is_dir() and
                item.name.startswith("dotmac_") and
                not item.name.endswith("_framework")):
                services.append(item.name)
        return services

    def analyze_test_structure(self) -> TestAnalysis:
        """Analyze current test structure across all services."""
        print("Analyzing test structure across DotMac services...")

        self._scan_test_files()

        analysis = TestAnalysis(
            total_files=len(self.test_files),
            files_by_category=self._count_by_category(),
            files_by_service=self._count_by_service(),
            naming_violations=self._find_naming_violations(),
            organization_issues=self._find_organization_issues(),
            recommendations=self._generate_recommendations()
        )

        return analysis

    def _scan_test_files(self):
        """Scan all test files across services."""
        for service in self.services:
            service_path = self.root_path / service
            tests_path = service_path / "tests"

            if tests_path.exists():
                self._scan_directory(tests_path, service)

    def _scan_directory(self, directory: Path, service: str):
        """Recursively scan directory for test files."""
        for item in directory.rglob("*.py"):
            if item.name.startswith("test_") or "test" in item.name:
                test_file = self._analyze_test_file(item, service)
                if test_file:
                    self.test_files.append(test_file)

    def _analyze_test_file(self, file_path: Path, service: str) -> TestFile:
        """Analyze individual test file."""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Determine category based on path and name
            category = self._determine_category(file_path)

            # Extract metadata
            test_count = len(re.findall(r"def test_\w+", content))
            markers = re.findall(r"@pytest\.mark\.(\w+)", content)
            imports = re.findall(r"from ([\w\.]+) import", content)
            classes = re.findall(r"class (Test\w+)", content)

            relative_path = file_path.relative_to(self.root_path)

            return TestFile(
                path=file_path,
                relative_path=relative_path,
                service=service,
                category=category,
                name=file_path.name,
                size=file_path.stat().st_size,
                test_count=test_count,
                markers=markers,
                imports=imports,
                classes=classes
            )
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            return None

    def _determine_category(self, file_path: Path) -> str:
        """Determine test category based on path and filename."""
        path_str = str(file_path).lower()
        filename = file_path.name.lower()

        # Check directory structure first
        for category in self.standard_categories:
            if f"/{category}/" in path_str or f"\\{category}\\" in path_str:
                return category

        # Check filename patterns
        if "integration" in filename:
            return "integration"
        if "e2e" in filename or "end_to_end" in filename:
            return "e2e"
        if "performance" in filename or "benchmark" in filename:
            return "performance"
        if "contract" in filename:
            return "contracts"
        if "smoke" in filename:
            return "smoke"
        if filename.startswith("test_"):
            return "unit"
        return "other"

    def _count_by_category(self) -> Dict[str, int]:
        """Count test files by category."""
        counts = defaultdict(int)
        for test_file in self.test_files:
            counts[test_file.category] += 1
        return dict(counts)

    def _count_by_service(self) -> Dict[str, int]:
        """Count test files by service."""
        counts = defaultdict(int)
        for test_file in self.test_files:
            counts[test_file.service] += 1
        return dict(counts)

    def _find_naming_violations(self) -> List[str]:
        """Find naming convention violations."""
        violations = []

        for test_file in self.test_files:
            # Check file naming
            if not test_file.name.startswith("test_"):
                violations.append(f"File {test_file.relative_path} doesn't follow 'test_' naming convention")

            # Check class naming for test classes
            for class_name in test_file.classes:
                if not class_name.startswith("Test"):
                    violations.append(f"Class {class_name} in {test_file.relative_path} doesn't follow 'Test' naming convention")

        return violations

    def _find_organization_issues(self) -> List[str]:
        """Find test organization issues."""
        issues = []

        # Check for missing test directories
        for service in self.services:
            service_tests = [tf for tf in self.test_files if tf.service == service]
            if not service_tests:
                issues.append(f"Service {service} has no tests")
                continue

            # Check for proper directory structure
            categories_present = set(tf.category for tf in service_tests)
            missing_categories = self.standard_categories - categories_present - {"fixtures", "helpers"}

            if "unit" not in categories_present:
                issues.append(f"Service {service} missing unit tests")
            if "integration" not in categories_present:
                issues.append(f"Service {service} missing integration tests")

        # Check for mixed test types in single files
        for test_file in self.test_files:
            markers_set = set(test_file.markers)
            type_markers = markers_set & {"unit", "integration", "e2e", "performance"}
            if len(type_markers) > 1:
                issues.append(f"File {test_file.relative_path} mixes test types: {type_markers}")

        return issues

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations for standardization."""
        recommendations = []

        # Analyze current state
        total_files = len(self.test_files)
        categories = self._count_by_category()

        # Structure recommendations
        if categories.get("other", 0) > 0:
            recommendations.append(f"Reorganize {categories['other']} miscategorized test files")

        if categories.get("unit", 0) < total_files * 0.6:
            recommendations.append("Increase unit test coverage - should be ~60% of all tests")

        if categories.get("integration", 0) < total_files * 0.3:
            recommendations.append("Add more integration tests - should be ~30% of all tests")

        if categories.get("e2e", 0) == 0:
            recommendations.append("Add end-to-end tests for critical workflows")

        # Missing standard directories
        for service in self.services:
            service_path = self.root_path / service / "tests"
            if service_path.exists():
                for category in ["unit", "integration", "e2e", "performance"]:
                    category_path = service_path / category
                    if not category_path.exists():
                        recommendations.append(f"Create {category} directory for {service}")

        # Test quality recommendations
        low_test_files = [tf for tf in self.test_files if tf.test_count < 3]
        if low_test_files:
            recommendations.append(f"Enhance {len(low_test_files)} test files with minimal test coverage")

        return recommendations

    def generate_migration_plan(self) -> Dict[str, Any]:
        """Generate a migration plan for standardization."""
        plan = {
            "directory_creation": [],
            "file_moves": [],
            "file_renames": [],
            "structure_changes": []
        }

        # Plan directory creation
        for service in self.services:
            service_tests_path = self.root_path / service / "tests"
            if service_tests_path.exists():
                for category in self.standard_categories:
                    category_path = service_tests_path / category
                    if not category_path.exists() and category not in ["fixtures", "helpers"]:
                        plan["directory_creation"].append({
                            "service": service,
                            "directory": category,
                            "path": str(category_path)
                        })

        # Plan file moves and renames
        for test_file in self.test_files:
            current_category = test_file.category
            expected_path = self._get_expected_path(test_file)

            if str(test_file.path) != str(expected_path):
                plan["file_moves"].append({
                    "current_path": str(test_file.relative_path),
                    "target_path": str(expected_path.relative_to(self.root_path)),
                    "reason": f"Move from {current_category} to proper location"
                })

        return plan

    def _get_expected_path(self, test_file: TestFile) -> Path:
        """Get expected path for a test file based on standards."""
        service_tests = self.root_path / test_file.service / "tests"

        # Determine proper category directory
        if test_file.category == "other":
            category = "unit"  # Default to unit tests
        else:
            category = test_file.category

        # Generate proper filename
        filename = test_file.name
        if not filename.startswith("test_"):
            filename = f"test_{filename}"

        return service_tests / category / filename

    def print_analysis_report(self, analysis: TestAnalysis):
        """Print comprehensive analysis report."""
        print("\n" + "="*80)
        print("DOTMAC PLATFORM TEST ORGANIZATION ANALYSIS")
        print("="*80)

        print("\n📊 OVERVIEW")
        print(f"Total test files: {analysis.total_files}")
        print(f"Services analyzed: {len(self.services)}")

        print("\n📁 FILES BY CATEGORY")
        for category, count in analysis.files_by_category.items():
            percentage = (count / analysis.total_files) * 100 if analysis.total_files > 0 else 0
            print(f"  {category:12}: {count:3d} files ({percentage:5.1f}%)")

        print("\n🏢 FILES BY SERVICE")
        for service, count in analysis.files_by_service.items():
            print(f"  {service:20}: {count:3d} files")

        if analysis.naming_violations:
            print(f"\n⚠️  NAMING VIOLATIONS ({len(analysis.naming_violations)})")
            for violation in analysis.naming_violations[:10]:  # Show first 10
                print(f"  • {violation}")
            if len(analysis.naming_violations) > 10:
                print(f"  ... and {len(analysis.naming_violations) - 10} more")

        if analysis.organization_issues:
            print(f"\n🔧 ORGANIZATION ISSUES ({len(analysis.organization_issues)})")
            for issue in analysis.organization_issues:
                print(f"  • {issue}")

        if analysis.recommendations:
            print(f"\n💡 RECOMMENDATIONS ({len(analysis.recommendations)})")
            for i, rec in enumerate(analysis.recommendations, 1):
                print(f"  {i}. {rec}")

        print("\n✅ NEXT STEPS")
        print("  1. Review the migration plan")
        print("  2. Create missing directory structure")
        print("  3. Move and rename files as recommended")
        print("  4. Add missing test categories")
        print("  5. Update CI/CD pipeline configuration")

        print("\n" + "="*80)


def main():
    """Main execution function."""
    import argparse

    parser = argparse.ArgumentParser(description="Standardize DotMac test organization")
    parser.add_argument("--root", default=".", help="Root directory of DotMac framework")
    parser.add_argument("--output", help="Output file for analysis results")
    parser.add_argument("--plan", action="store_true", help="Generate migration plan")

    args = parser.parse_args()

    standardizer = TestStandardizer(args.root)
    analysis = standardizer.analyze_test_structure()

    # Print analysis report
    standardizer.print_analysis_report(analysis)

    # Generate migration plan if requested
    if args.plan:
        migration_plan = standardizer.generate_migration_plan()
        print("\n📋 MIGRATION PLAN")
        print(f"Directories to create: {len(migration_plan['directory_creation'])}")
        print(f"Files to move: {len(migration_plan['file_moves'])}")

        if args.output:
            with open(args.output, "w") as f:
                json.dump({
                    "analysis": {
                        "total_files": analysis.total_files,
                        "files_by_category": analysis.files_by_category,
                        "files_by_service": analysis.files_by_service,
                        "naming_violations": analysis.naming_violations,
                        "organization_issues": analysis.organization_issues,
                        "recommendations": analysis.recommendations
                    },
                    "migration_plan": migration_plan
                }, f, indent=2)
            print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()
