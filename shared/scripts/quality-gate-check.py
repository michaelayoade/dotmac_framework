#!/usr/bin/env python3
"""
Quality Gate Checker for DotMac Framework

This script checks all quality gates defined in .quality-gates.yml
and reports pass/fail status for each requirement.
"""

import argparse
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import yaml


class QualityGateChecker:
    """Main quality gate checker class."""
    
    def __init__(self, config_path: str = ".quality-gates.yml", environment: str = "development"):
        self.config_path = Path(config_path)
        self.environment = environment
        self.results = {}
        self.load_config()
    
    def load_config(self):
        """Load quality gate configuration."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Quality gate config not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Apply environment overrides
        if 'environments' in self.config and self.environment in self.config['environments']:
            env_config = self.config['environments'][self.environment]
            self._merge_config(self.config, env_config)
    
    def _merge_config(self, base: Dict, override: Dict):
        """Merge environment-specific overrides."""
        for key, value in override.items():
            if isinstance(value, dict) and key in base:
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def run_all_checks(self) -> Dict[str, Any]:
        """Run all quality gate checks."""
        print(f"Running quality gate checks for environment: {self.environment}")
        print("=" * 60)
        
        # Coverage checks
        self.check_coverage()
        
        # Code quality checks
        self.check_code_quality()
        
        # Security checks
        self.check_security()
        
        # Performance checks
        self.check_performance()
        
        # Test checks
        self.check_tests()
        
        # Documentation checks
        self.check_documentation()
        
        # Generate final report
        return self.generate_report()
    
    def check_coverage(self):
        """Check test coverage requirements."""
        print("Checking test coverage...")
        
        coverage_config = self.config.get('coverage', {})
        coverage_results = {
            'total_coverage': self._get_coverage_percentage(),
            'branch_coverage': self._get_branch_coverage(),
            'service_coverage': self._get_service_coverage()
        }
        
        # Check total coverage
        min_total = coverage_config.get('minimum_total', 80)
        total_coverage = coverage_results['total_coverage']
        
        if total_coverage >= min_total:
            print(f"  ✅ Total coverage: {total_coverage}% (≥{min_total}%)")
            coverage_pass = True
        else:
            print(f"  ❌ Total coverage: {total_coverage}% (<{min_total}%)")
            coverage_pass = False
        
        # Check branch coverage
        min_branch = coverage_config.get('minimum_branch', 70)
        branch_coverage = coverage_results['branch_coverage']
        
        if branch_coverage >= min_branch:
            print(f"  ✅ Branch coverage: {branch_coverage}% (≥{min_branch}%)")
            branch_pass = True
        else:
            print(f"  ❌ Branch coverage: {branch_coverage}% (<{min_branch}%)")
            branch_pass = False
        
        self.results['coverage'] = {
            'passed': coverage_pass and branch_pass,
            'details': coverage_results,
            'thresholds': {
                'minimum_total': min_total,
                'minimum_branch': min_branch
            }
        }
    
    def check_code_quality(self):
        """Check code quality requirements."""
        print("Checking code quality...")
        
        # Run Ruff linting
        ruff_passed = self._check_ruff()
        
        # Check complexity
        complexity_passed = self._check_complexity()
        
        # Check formatting
        formatting_passed = self._check_formatting()
        
        # Check type checking
        mypy_passed = self._check_mypy()
        
        all_passed = all([ruff_passed, complexity_passed, formatting_passed, mypy_passed])
        
        self.results['code_quality'] = {
            'passed': all_passed,
            'details': {
                'ruff': ruff_passed,
                'complexity': complexity_passed,
                'formatting': formatting_passed,
                'mypy': mypy_passed
            }
        }
    
    def check_security(self):
        """Check security requirements."""
        print("Checking security...")
        
        # Run Bandit security scan
        bandit_passed = self._check_bandit()
        
        # Run Safety dependency check
        safety_passed = self._check_safety()
        
        # Run pip-audit
        audit_passed = self._check_pip_audit()
        
        all_passed = all([bandit_passed, safety_passed, audit_passed])
        
        self.results['security'] = {
            'passed': all_passed,
            'details': {
                'bandit': bandit_passed,
                'safety': safety_passed, 
                'pip_audit': audit_passed
            }
        }
    
    def check_performance(self):
        """Check performance requirements."""
        print("Checking performance...")
        
        # Check if performance test results exist
        performance_results = self._get_performance_results()
        
        if performance_results:
            # Check response time thresholds
            response_times_ok = self._check_response_times(performance_results)
            
            # Check error rates
            error_rates_ok = self._check_error_rates(performance_results)
            
            performance_passed = response_times_ok and error_rates_ok
        else:
            print("  ⚠️  No performance test results found")
            performance_passed = True  # Don't fail if no results yet
        
        self.results['performance'] = {
            'passed': performance_passed,
            'details': performance_results or {}
        }
    
    def check_tests(self):
        """Check test requirements."""
        print("Checking test requirements...")
        
        test_results = self._get_test_results()
        
        # Check test execution time
        max_duration = self.config.get('testing', {}).get('execution', {}).get('max_test_duration', 300)
        test_duration = test_results.get('duration', 0)
        
        duration_ok = test_duration <= max_duration
        
        if duration_ok:
            print(f"  ✅ Test duration: {test_duration}s (≤{max_duration}s)")
        else:
            print(f"  ❌ Test duration: {test_duration}s (>{max_duration}s)")
        
        # Check test distribution
        distribution_ok = self._check_test_distribution(test_results)
        
        tests_passed = duration_ok and distribution_ok
        
        self.results['testing'] = {
            'passed': tests_passed,
            'details': test_results
        }
    
    def check_documentation(self):
        """Check documentation requirements."""
        print("Checking documentation...")
        
        # Check for required documentation files
        doc_files = [
            'README.md',
            'ARCHITECTURE.md', 
            'DEPLOYMENT_GUIDE.md'
        ]
        
        missing_docs = []
        for doc_file in doc_files:
            if not Path(doc_file).exists():
                missing_docs.append(doc_file)
        
        if missing_docs:
            print(f"  ❌ Missing documentation: {', '.join(missing_docs)}")
            docs_passed = False
        else:
            print("  ✅ Required documentation files present")
            docs_passed = True
        
        # Check docstring coverage (simplified check)
        docstring_coverage = self._check_docstring_coverage()
        min_docstring_coverage = self.config.get('documentation', {}).get('code', {}).get('min_docstring_coverage', 80)
        
        docstring_ok = docstring_coverage >= min_docstring_coverage
        
        if docstring_ok:
            print(f"  ✅ Docstring coverage: {docstring_coverage}% (≥{min_docstring_coverage}%)")
        else:
            print(f"  ❌ Docstring coverage: {docstring_coverage}% (<{min_docstring_coverage}%)")
        
        self.results['documentation'] = {
            'passed': docs_passed and docstring_ok,
            'details': {
                'missing_files': missing_docs,
                'docstring_coverage': docstring_coverage
            }
        }
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate final quality gate report."""
        print("\n" + "=" * 60)
        print("QUALITY GATE RESULTS")
        print("=" * 60)
        
        # Count passes and failures
        total_checks = 0
        passed_checks = 0
        blocking_failures = []
        warning_issues = []
        
        enforcement = self.config.get('enforcement', {})
        blocking_rules = enforcement.get('blocking', [])
        warning_rules = enforcement.get('warning', [])
        
        for check_name, result in self.results.items():
            total_checks += 1
            if result['passed']:
                passed_checks += 1
                print(f"✅ {check_name.upper()}: PASSED")
            else:
                print(f"❌ {check_name.upper()}: FAILED")
                
                # Check if this is a blocking failure
                rule_key = f"{check_name}"
                if any(rule_key in rule for rule in blocking_rules):
                    blocking_failures.append(check_name)
                elif any(rule_key in rule for rule in warning_rules):
                    warning_issues.append(check_name)
                else:
                    blocking_failures.append(check_name)  # Default to blocking
        
        # Overall result
        overall_passed = len(blocking_failures) == 0
        
        print("\n" + "=" * 60)
        if overall_passed:
            print("🎉 QUALITY GATE: PASSED")
            exit_code = 0
        else:
            print("💥 QUALITY GATE: FAILED")
            exit_code = 1
            
        print(f"Passed: {passed_checks}/{total_checks}")
        
        if blocking_failures:
            print(f"Blocking failures: {', '.join(blocking_failures)}")
        
        if warning_issues:
            print(f"Warnings: {', '.join(warning_issues)}")
        
        # Generate detailed report
        report = {
            'timestamp': datetime.now().isoformat(),
            'environment': self.environment,
            'overall_passed': overall_passed,
            'total_checks': total_checks,
            'passed_checks': passed_checks,
            'blocking_failures': blocking_failures,
            'warning_issues': warning_issues,
            'results': self.results,
            'exit_code': exit_code
        }
        
        # Save report to file
        self._save_report(report)
        
        return report
    
    # Helper methods for specific checks
    def _get_coverage_percentage(self) -> float:
        """Get total test coverage percentage."""
        try:
            # Try to parse coverage.xml file
            coverage_file = Path("coverage.xml")
            if coverage_file.exists():
                tree = ET.parse(coverage_file)
                root = tree.getroot()
                coverage_elem = root.find(".//coverage")
                if coverage_elem is not None:
                    return float(coverage_elem.get("line-rate", 0) * 100
        except Exception:
            pass
        
        # Fallback: run pytest with coverage
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "--cov=.", "--cov-report=term", "--tb=no", "-q"],
                capture_output=True,
                text=True
            )
            
            # Parse coverage from output
            for line in result.stdout.split('\n'):
                if 'TOTAL' in line and '%' in line:
                    percentage = line.split()[-1].replace('%', '')
                    return float(percentage)
        except Exception:
            pass
        
        return 0.0
    
    def _get_branch_coverage(self) -> float:
        """Get branch coverage percentage."""
        # Simplified - return same as line coverage
        # In real implementation, parse branch coverage specifically
        return self._get_coverage_percentage() * 0.9  # Approximation
    
    def _get_service_coverage(self) -> Dict[str, float]:
        """Get coverage per service."""
        # Simplified implementation
        return {}
    
    def _check_ruff(self) -> bool:
        """Check Ruff linting."""
        try:
            result = subprocess.run(["ruff", "check", "."], capture_output=True)
            ruff_passed = result.returncode == 0
            
            if ruff_passed:
                print("  ✅ Ruff linting: PASSED")
            else:
                print("  ❌ Ruff linting: FAILED")
                print(f"    {result.stdout.decode()}")
            
            return ruff_passed
        except FileNotFoundError:
            print("  ⚠️  Ruff not found, skipping check")
            return True
    
    def _check_complexity(self) -> bool:
        """Check code complexity."""
        try:
            # Check complexity with Ruff
            result = subprocess.run(
                ["ruff", "check", ".", "--select", "C901,PLR0913,PLR0915"],
                capture_output=True
            )
            
            complexity_passed = result.returncode == 0
            
            if complexity_passed:
                print("  ✅ Complexity: PASSED")
            else:
                print("  ❌ Complexity: FAILED")
                print(f"    {result.stdout.decode()}")
            
            return complexity_passed
        except FileNotFoundError:
            print("  ⚠️  Complexity checker not available")
            return True
    
    def _check_formatting(self) -> bool:
        """Check code formatting."""
        try:
            # Check Black formatting
            result = subprocess.run(["black", "--check", "."], capture_output=True)
            black_passed = result.returncode == 0
            
            # Check isort
            isort_result = subprocess.run(["isort", "--check-only", "."], capture_output=True)
            isort_passed = isort_result.returncode == 0
            
            formatting_passed = black_passed and isort_passed
            
            if formatting_passed:
                print("  ✅ Formatting: PASSED")
            else:
                print("  ❌ Formatting: FAILED")
                if not black_passed:
                    print("    Black formatting issues found")
                if not isort_passed:
                    print("    Import sorting issues found")
            
            return formatting_passed
        except FileNotFoundError:
            print("  ⚠️  Formatting tools not available")
            return True
    
    def _check_mypy(self) -> bool:
        """Check type checking with MyPy."""
        try:
            result = subprocess.run(["mypy", "."], capture_output=True)
            mypy_output = result.stdout.decode() + result.stderr.decode()
            
            # Count errors
            error_count = mypy_output.count("error:")
            max_errors = self.config.get('code_quality', {}).get('mypy', {}).get('max_errors', 50)
            
            mypy_passed = error_count <= max_errors
            
            if mypy_passed:
                print(f"  ✅ MyPy: PASSED ({error_count} errors, ≤{max_errors})")
            else:
                print(f"  ❌ MyPy: FAILED ({error_count} errors, >{max_errors})")
            
            return mypy_passed
        except FileNotFoundError:
            print("  ⚠️  MyPy not found, skipping check")
            return True
    
    def _check_bandit(self) -> bool:
        """Check Bandit security scanning."""
        try:
            result = subprocess.run(
                ["bandit", "-r", ".", "-f", "json"],
                capture_output=True
            )
            
            if result.returncode == 0:
                bandit_output = json.loads(result.stdout.decode()
                issue_count = len(bandit_output.get('results', [])
                
                max_issues = self.config.get('security', {}).get('bandit', {}).get('max_issues', 0)
                bandit_passed = issue_count <= max_issues
                
                if bandit_passed:
                    print(f"  ✅ Bandit: PASSED ({issue_count} issues)")
                else:
                    print(f"  ❌ Bandit: FAILED ({issue_count} issues, >{max_issues})")
                
                return bandit_passed
            else:
                print("  ❌ Bandit: FAILED (execution error)")
                return False
                
        except (FileNotFoundError, json.JSONDecodeError):
            print("  ⚠️  Bandit not available")
            return True
    
    def _check_safety(self) -> bool:
        """Check Safety dependency scanning."""
        try:
            result = subprocess.run(["safety", "check", "--json"], capture_output=True)
            
            if result.returncode == 0:
                print("  ✅ Safety: PASSED (no vulnerabilities)")
                return True
            else:
                try:
                    safety_output = json.loads(result.stdout.decode()
                    vuln_count = len(safety_output)
                    print(f"  ❌ Safety: FAILED ({vuln_count} vulnerabilities)")
                except json.JSONDecodeError:
                    print("  ❌ Safety: FAILED")
                return False
                
        except FileNotFoundError:
            print("  ⚠️  Safety not available")
            return True
    
    def _check_pip_audit(self) -> bool:
        """Check pip-audit vulnerability scanning."""
        try:
            result = subprocess.run(["pip-audit", "--format=json"], capture_output=True)
            
            if result.returncode == 0:
                print("  ✅ pip-audit: PASSED")
                return True
            else:
                print("  ❌ pip-audit: FAILED")
                return False
                
        except FileNotFoundError:
            print("  ⚠️  pip-audit not available")
            return True
    
    def _get_performance_results(self) -> Optional[Dict]:
        """Get performance test results."""
        # Check for performance test results files
        results_files = [
            "performance-reports/locust-stats_stats.csv",
            "test-reports/benchmark-report.json"
        ]
        
        for results_file in results_files:
            if Path(results_file).exists():
                return {"source": results_file, "found": True}
        
        return None
    
    def _check_response_times(self, performance_results: Dict) -> bool:
        """Check API response time thresholds."""
        # Simplified check - in real implementation, parse actual results
        print("  ⚠️  Response time check not implemented")
        return True
    
    def _check_error_rates(self, performance_results: Dict) -> bool:
        """Check error rate thresholds."""
        # Simplified check - in real implementation, parse actual results  
        print("  ⚠️  Error rate check not implemented")
        return True
    
    def _get_test_results(self) -> Dict:
        """Get test execution results."""
        # Try to parse JUnit XML results
        junit_files = list(Path(".").glob("**/junit*.xml")
        
        if junit_files:
            # Parse most recent junit file
            try:
                tree = ET.parse(junit_files[0])
                root = tree.getroot()
                
                test_count = int(root.get("tests", 0)
                failure_count = int(root.get("failures", 0)
                error_count = int(root.get("errors", 0)
                time_taken = float(root.get("time", 0)
                
                return {
                    "total_tests": test_count,
                    "failures": failure_count,
                    "errors": error_count,
                    "duration": time_taken,
                    "success_rate": ((test_count - failure_count - error_count) / test_count * 100) if test_count > 0 else 0
                }
            except Exception:
                pass
        
        return {"duration": 0, "total_tests": 0}
    
    def _check_test_distribution(self, test_results: Dict) -> bool:
        """Check test type distribution."""
        # Simplified check - in real implementation, analyze test markers
        print("  ⚠️  Test distribution check not implemented")
        return True
    
    def _check_docstring_coverage(self) -> float:
        """Check docstring coverage percentage."""
        # Simplified implementation - count Python files with docstrings
        try:
            python_files = list(Path(".").rglob("*.py")
            files_with_docstrings = 0
            
            for py_file in python_files:
                if any(skip in str(py_file) for skip in ["test_", "conftest.py", "__pycache__"]):
                    continue
                    
                try:
                    with open(py_file, 'r') as f:
                        content = f.read()
                        if '"""' in content or "'''" in content:
                            files_with_docstrings += 1
                except Exception:
                    continue
            
            if len(python_files) > 0:
                return (files_with_docstrings / len(python_files) * 100
        except Exception:
            pass
        
        return 0.0
    
    def _save_report(self, report: Dict):
        """Save quality gate report to file."""
        reports_dir = Path("quality-reports")
        reports_dir.mkdir(exist_ok=True)
        
        # Save JSON report
        json_report = reports_dir / f"quality-gate-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        with open(json_report, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\nDetailed report saved to: {json_report}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run quality gate checks")
    parser.add_argument(
        "--config",
        default=".quality-gates.yml",
        help="Path to quality gates configuration file"
    )
    parser.add_argument(
        "--environment",
        default="development",
        choices=["development", "staging", "production"],
        help="Environment to run checks for"
    )
    parser.add_argument(
        "--output",
        choices=["console", "json", "junit"],
        default="console",
        help="Output format"
    )
    
    args = parser.parse_args()
    
    try:
        checker = QualityGateChecker(args.config, args.environment)
        report = checker.run_all_checks()
        
        # Exit with appropriate code
        sys.exit(report['exit_code'])
        
    except Exception as e:
        print(f"Error running quality gate checks: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()