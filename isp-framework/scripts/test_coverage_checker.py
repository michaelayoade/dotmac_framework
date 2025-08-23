#!/usr/bin/env python3
"""
Test Coverage Checker

TESTING IMPROVEMENT: Script to assess current test coverage
and identify areas needing additional tests to reach 60% minimum target.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import re


def count_files_in_directory(directory: Path, pattern: str) -> List[Path]:
    """Count files matching pattern in directory."""
    if not directory.exists():
        return []
    
    files = []
    for file_path in directory.rglob(pattern):
        if file_path.is_file():
            files.append(file_path)
    return files


def analyze_test_coverage(project_root: Path) -> Dict:
    """Analyze test coverage across the project."""
    src_dir = project_root / "src"
    test_dir = project_root / "tests"
    
    # Count source files
    source_files = count_files_in_directory(src_dir, "*.py")
    source_files = [f for f in source_files if not any(exclude in str(f) for exclude in 
                   ['__pycache__', '.pyc', 'migrations', 'alembic'])]
    
    # Count test files
    test_files = count_files_in_directory(test_dir, "test_*.py")
    test_files.extend(count_files_in_directory(test_dir, "*_test.py"))
    
    # Also count root-level test files
    root_test_files = list(project_root.glob("test_*.py"))
    test_files.extend(root_test_files)
    
    # Analyze by module
    module_coverage = analyze_module_coverage(src_dir, test_dir)
    
    return {
        "total_source_files": len(source_files),
        "total_test_files": len(test_files),
        "test_to_source_ratio": len(test_files) / len(source_files) if source_files else 0,
        "source_files": source_files,
        "test_files": test_files,
        "module_coverage": module_coverage
    }


def analyze_module_coverage(src_dir: Path, test_dir: Path) -> Dict:
    """Analyze test coverage by module."""
    module_coverage = {}
    
    # Find all modules in src
    for module_path in src_dir.rglob("*/"):
        if module_path.is_dir() and not any(exclude in str(module_path) for exclude in 
                                          ['__pycache__', '.git', '.pytest_cache']):
            
            relative_path = module_path.relative_to(src_dir)
            module_name = str(relative_path).replace(os.sep, '.')
            
            # Count source files in module
            source_files = count_files_in_directory(module_path, "*.py")
            source_files = [f for f in source_files if f.name != "__init__.py"]
            
            # Look for corresponding test directory
            test_module_path = test_dir / "unit" / relative_path
            test_files = []
            if test_module_path.exists():
                test_files = count_files_in_directory(test_module_path, "test_*.py")
            
            if source_files:  # Only include modules with source files
                module_coverage[module_name] = {
                    "source_files": len(source_files),
                    "test_files": len(test_files),
                    "coverage_ratio": len(test_files) / len(source_files) if source_files else 0,
                    "source_paths": [str(f) for f in source_files],
                    "test_paths": [str(f) for f in test_files]
                }
    
    return module_coverage


def identify_uncovered_areas(coverage_data: Dict) -> List[str]:
    """Identify areas with insufficient test coverage."""
    uncovered_areas = []
    
    for module_name, data in coverage_data["module_coverage"].items():
        if data["coverage_ratio"] < 0.5:  # Less than 50% coverage
            uncovered_areas.append(f"{module_name}: {data['coverage_ratio']:.1%} coverage "
                                 f"({data['test_files']}/{data['source_files']} files)")
    
    return uncovered_areas


def generate_coverage_report(project_root: Path) -> str:
    """Generate comprehensive coverage report."""
    coverage_data = analyze_test_coverage(project_root)
    
    report = []
    report.append("=" * 60)
    report.append("TEST COVERAGE ANALYSIS REPORT")
    report.append("=" * 60)
    report.append("")
    
    # Overall summary
    ratio = coverage_data["test_to_source_ratio"]
    report.append("OVERALL SUMMARY:")
    report.append(f"  Total Source Files: {coverage_data['total_source_files']}")
    report.append(f"  Total Test Files: {coverage_data['total_test_files']}")
    report.append(f"  Test-to-Source Ratio: {ratio:.1%}")
    report.append("")
    
    # Coverage assessment
    if ratio >= 0.6:
        status = "✅ EXCELLENT"
    elif ratio >= 0.4:
        status = "⚠️  GOOD" 
    elif ratio >= 0.2:
        status = "⚠️  NEEDS IMPROVEMENT"
    else:
        status = "❌ CRITICAL"
    
    report.append(f"Coverage Status: {status}")
    report.append("")
    
    # Module breakdown
    report.append("MODULE COVERAGE BREAKDOWN:")
    report.append("-" * 40)
    
    module_coverage = coverage_data["module_coverage"]
    sorted_modules = sorted(module_coverage.items(), 
                          key=lambda x: x[1]["coverage_ratio"])
    
    for module_name, data in sorted_modules:
        ratio = data["coverage_ratio"]
        status_icon = "✅" if ratio >= 0.6 else "⚠️" if ratio >= 0.3 else "❌"
        report.append(f"  {status_icon} {module_name}: {ratio:.1%} "
                     f"({data['test_files']}/{data['source_files']} files)")
    
    report.append("")
    
    # Identify priority areas
    uncovered = identify_uncovered_areas(coverage_data)
    if uncovered:
        report.append("PRIORITY AREAS FOR TESTING:")
        report.append("-" * 40)
        for area in uncovered[:10]:  # Top 10
            report.append(f"  📝 {area}")
        report.append("")
    
    # Recommendations
    report.append("RECOMMENDATIONS:")
    report.append("-" * 40)
    if ratio < 0.6:
        report.append(f"  🎯 Target: Increase coverage to 60% minimum")
        needed_tests = int((0.6 * coverage_data['total_source_files']) - coverage_data['total_test_files'])
        report.append(f"  📈 Need ~{needed_tests} additional test files")
    
    report.append("  🔍 Focus on modules with <50% coverage")
    report.append("  🧪 Add integration tests for cross-service functionality")
    report.append("  📊 Add performance/load tests for critical paths")
    
    return "\n".join(report)


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        project_root = Path(sys.argv[1])
    else:
        project_root = Path.cwd()
    
    if not project_root.exists():
        print(f"Error: Project root {project_root} does not exist")
        sys.exit(1)
    
    print(f"Analyzing test coverage for: {project_root}")
    print()
    
    report = generate_coverage_report(project_root)
    print(report)
    
    # Also save to file
    report_file = project_root / "test_coverage_report.txt"
    report_file.write_text(report)
    print(f"\nReport saved to: {report_file}")


if __name__ == "__main__":
    main()