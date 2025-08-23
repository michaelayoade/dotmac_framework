#!/usr/bin/env python3
"""
AI Safety Pipeline for CI/CD Integration

This script orchestrates AI safety checks, revenue protection validation,
and property-based testing to ensure AI-generated code meets safety standards.
"""

import os
import sys
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from enum import Enum


class SafetyLevel(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH" 
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class SafetyResult:
    check_name: str
    status: str  # PASS, FAIL, WARN
    level: SafetyLevel
    message: str
    details: Dict[str, Any]
    execution_time: float


class AISafetyPipeline:
    """
    AI Safety Pipeline orchestrator for automated validation
    of AI-generated code changes in CI/CD environment.
    """
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        self.results: List[SafetyResult] = []
        self.start_time = time.time()
        
    def run_property_based_tests(self) -> SafetyResult:
        """Run Hypothesis property-based tests"""
        start = time.time()
        
        try:
            cmd = [
                sys.executable, "-m", "pytest", 
                "tests/property/", 
                "-v", "--tb=short", 
                "--hypothesis-show-statistics",
                "--hypothesis-profile=fast"  # Faster for CI/CD
            ]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True,
                cwd=self.project_root
            )
            
            execution_time = time.time() - start
            
            if result.returncode == 0:
                return SafetyResult(
                    check_name="Property-Based Tests",
                    status="PASS",
                    level=SafetyLevel.HIGH,
                    message="All property-based invariants verified",
                    details={
                        "stdout": result.stdout,
                        "test_count": self._extract_test_count(result.stdout)
                    },
                    execution_time=execution_time
                )
            else:
                return SafetyResult(
                    check_name="Property-Based Tests", 
                    status="FAIL",
                    level=SafetyLevel.CRITICAL,
                    message="Property-based test failures detected",
                    details={
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "return_code": result.returncode
                    },
                    execution_time=execution_time
                )
                
        except Exception as e:
            return SafetyResult(
                check_name="Property-Based Tests",
                status="FAIL", 
                level=SafetyLevel.CRITICAL,
                message=f"Failed to execute property tests: {str(e)}",
                details={"error": str(e)},
                execution_time=time.time() - start
            )
    
    def run_revenue_protection_scan(self) -> SafetyResult:
        """Run revenue-critical code protection scan"""
        start = time.time()
        
        try:
            cmd = [
                sys.executable, "-m", "pytest",
                "tests/ai_safety/test_revenue_protection.py",
                "-v", "--tb=short"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True, 
                cwd=self.project_root
            )
            
            execution_time = time.time() - start
            
            if result.returncode == 0:
                return SafetyResult(
                    check_name="Revenue Protection Scan",
                    status="PASS",
                    level=SafetyLevel.CRITICAL,
                    message="No revenue-critical vulnerabilities detected",
                    details={"stdout": result.stdout},
                    execution_time=execution_time
                )
            else:
                # Parse specific failures for revenue risks
                failures = self._parse_revenue_failures(result.stdout)
                
                return SafetyResult(
                    check_name="Revenue Protection Scan",
                    status="FAIL",
                    level=SafetyLevel.CRITICAL,
                    message=f"Revenue protection failures: {len(failures)} issues",
                    details={
                        "failures": failures,
                        "stdout": result.stdout,
                        "stderr": result.stderr
                    },
                    execution_time=execution_time
                )
                
        except Exception as e:
            return SafetyResult(
                check_name="Revenue Protection Scan", 
                status="FAIL",
                level=SafetyLevel.CRITICAL,
                message=f"Revenue scan failed: {str(e)}",
                details={"error": str(e)},
                execution_time=time.time() - start
            )
    
    def run_ai_code_detection(self) -> SafetyResult:
        """Detect and validate AI-generated code modifications"""
        start = time.time()
        
        try:
            # Run git diff to find recent changes
            git_diff = subprocess.run(
                ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            changed_files = git_diff.stdout.strip().split('\n') if git_diff.stdout.strip() else []
            python_files = [f for f in changed_files if f.endswith('.py')]
            
            ai_generated_files = []
            untagged_revenue_files = []
            
            for file_path in python_files:
                full_path = self.project_root / file_path
                if full_path.exists():
                    content = full_path.read_text()
                    
                    # Check for AI markers
                    ai_markers = [
                        '# AI-GENERATED', '# AI-MODIFIED', '# Claude Code',
                        '"""AI-Generated', '@ai_generated'
                    ]
                    has_ai_marker = any(marker in content for marker in ai_markers)
                    
                    if has_ai_marker:
                        ai_generated_files.append(file_path)
                    
                    # Check if it's revenue-critical but untagged
                    revenue_keywords = ['amount', 'price', 'payment', 'billing', 'charge']
                    is_revenue_critical = (
                        any(keyword in content.lower() for keyword in revenue_keywords) and
                        any(module in file_path for module in ['billing', 'services', 'payment'])
                    )
                    
                    if is_revenue_critical and not has_ai_marker:
                        untagged_revenue_files.append(file_path)
            
            execution_time = time.time() - start
            
            # Determine status based on findings
            if untagged_revenue_files:
                return SafetyResult(
                    check_name="AI Code Detection",
                    status="WARN",
                    level=SafetyLevel.HIGH,
                    message=f"Revenue-critical files modified without AI markers: {len(untagged_revenue_files)}",
                    details={
                        "ai_generated_files": ai_generated_files,
                        "untagged_revenue_files": untagged_revenue_files,
                        "total_changes": len(python_files)
                    },
                    execution_time=execution_time
                )
            else:
                return SafetyResult(
                    check_name="AI Code Detection",
                    status="PASS",
                    level=SafetyLevel.MEDIUM,
                    message=f"AI code properly tagged: {len(ai_generated_files)} files",
                    details={
                        "ai_generated_files": ai_generated_files,
                        "total_changes": len(python_files)
                    },
                    execution_time=execution_time
                )
                
        except Exception as e:
            return SafetyResult(
                check_name="AI Code Detection",
                status="FAIL",
                level=SafetyLevel.MEDIUM,
                message=f"AI detection failed: {str(e)}",
                details={"error": str(e)},
                execution_time=time.time() - start
            )
    
    def run_business_rule_validation(self) -> SafetyResult:
        """Validate that core business rules haven't been compromised"""
        start = time.time()
        
        try:
            # Define critical business rules that must always hold
            business_rules = [
                {
                    "rule": "Service costs must be positive",
                    "pattern": r"monthly_cost\s*=\s*0",
                    "severity": "HIGH"
                },
                {
                    "rule": "Tax rates must be applied", 
                    "pattern": r"tax_rate\s*=\s*0",
                    "severity": "CRITICAL"
                },
                {
                    "rule": "Payment validation required",
                    "pattern": r"payment_required\s*=\s*False",
                    "severity": "CRITICAL"
                }
            ]
            
            violations = []
            
            # Scan revenue-critical modules
            revenue_modules = [
                "src/dotmac_isp/modules/billing",
                "src/dotmac_isp/modules/services",
                "src/dotmac_isp/sdks/services"
            ]
            
            for module_path in revenue_modules:
                module_dir = self.project_root / module_path
                if module_dir.exists():
                    for py_file in module_dir.rglob("*.py"):
                        content = py_file.read_text()
                        
                        for rule in business_rules:
                            import re
                            if re.search(rule["pattern"], content, re.IGNORECASE):
                                violations.append({
                                    "file": str(py_file.relative_to(self.project_root)),
                                    "rule": rule["rule"],
                                    "severity": rule["severity"]
                                })
            
            execution_time = time.time() - start
            
            if not violations:
                return SafetyResult(
                    check_name="Business Rule Validation",
                    status="PASS", 
                    level=SafetyLevel.HIGH,
                    message="All business rules intact",
                    details={"rules_checked": len(business_rules)},
                    execution_time=execution_time
                )
            else:
                critical_violations = [v for v in violations if v["severity"] == "CRITICAL"]
                
                return SafetyResult(
                    check_name="Business Rule Validation",
                    status="FAIL" if critical_violations else "WARN",
                    level=SafetyLevel.CRITICAL if critical_violations else SafetyLevel.HIGH,
                    message=f"Business rule violations: {len(violations)} total, {len(critical_violations)} critical",
                    details={"violations": violations},
                    execution_time=execution_time
                )
                
        except Exception as e:
            return SafetyResult(
                check_name="Business Rule Validation",
                status="FAIL",
                level=SafetyLevel.HIGH, 
                message=f"Business rule validation failed: {str(e)}",
                details={"error": str(e)},
                execution_time=time.time() - start
            )
    
    def run_integration_smoke_tests(self) -> SafetyResult:
        """Run fast smoke tests to verify integration points"""
        start = time.time()
        
        try:
            cmd = [
                sys.executable, "-m", "pytest",
                "tests/integration/test_environment_validation.py",
                "-v", "--tb=short", "-x"  # Stop on first failure
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            execution_time = time.time() - start
            
            if result.returncode == 0:
                return SafetyResult(
                    check_name="Integration Smoke Tests",
                    status="PASS",
                    level=SafetyLevel.MEDIUM,
                    message="All integration points healthy",
                    details={"stdout": result.stdout},
                    execution_time=execution_time
                )
            else:
                return SafetyResult(
                    check_name="Integration Smoke Tests",
                    status="FAIL",
                    level=SafetyLevel.HIGH,
                    message="Integration smoke test failures",
                    details={
                        "stdout": result.stdout,
                        "stderr": result.stderr
                    },
                    execution_time=execution_time
                )
                
        except Exception as e:
            return SafetyResult(
                check_name="Integration Smoke Tests",
                status="FAIL",
                level=SafetyLevel.MEDIUM,
                message=f"Smoke tests failed: {str(e)}",
                details={"error": str(e)},
                execution_time=time.time() - start
            )
    
    def run_full_pipeline(self) -> Dict[str, Any]:
        """Execute complete AI safety pipeline"""
        print("🤖 Starting AI Safety Pipeline...")
        
        # Execute all safety checks
        checks = [
            self.run_property_based_tests,
            self.run_revenue_protection_scan,
            self.run_ai_code_detection,
            self.run_business_rule_validation,
            self.run_integration_smoke_tests
        ]
        
        for check_func in checks:
            print(f"  Running {check_func.__name__.replace('run_', '').replace('_', ' ').title()}...")
            result = check_func()
            self.results.append(result)
            
            # Print immediate status
            status_emoji = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️"}
            print(f"    {status_emoji.get(result.status, '❓')} {result.message}")
        
        return self.generate_report()
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive safety report"""
        total_time = time.time() - self.start_time
        
        passed = len([r for r in self.results if r.status == "PASS"])
        failed = len([r for r in self.results if r.status == "FAIL"]) 
        warned = len([r for r in self.results if r.status == "WARN"])
        
        # Determine overall status
        has_critical_failures = any(
            r.status == "FAIL" and r.level in [SafetyLevel.CRITICAL, SafetyLevel.HIGH]
            for r in self.results
        )
        
        overall_status = "FAIL" if has_critical_failures else ("WARN" if warned > 0 else "PASS")
        
        report = {
            "overall_status": overall_status,
            "total_execution_time": total_time,
            "summary": {
                "total_checks": len(self.results),
                "passed": passed,
                "failed": failed, 
                "warned": warned
            },
            "checks": [
                {
                    "name": r.check_name,
                    "status": r.status,
                    "level": r.level.value,
                    "message": r.message,
                    "execution_time": r.execution_time,
                    "details": r.details
                }
                for r in self.results
            ],
            "recommendations": self._generate_recommendations()
        }
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Generate actionable recommendations based on results"""
        recommendations = []
        
        failed_results = [r for r in self.results if r.status == "FAIL"]
        warned_results = [r for r in self.results if r.status == "WARN"]
        
        if any("Revenue Protection" in r.check_name for r in failed_results):
            recommendations.append("🚨 CRITICAL: Revenue protection failures detected - manual review required before deployment")
        
        if any("Property-Based" in r.check_name for r in failed_results):
            recommendations.append("⚡ Fix property-based test failures - business logic invariants violated")
            
        if any("AI Code Detection" in r.check_name for r in warned_results):
            recommendations.append("🏷️ Tag revenue-critical code modifications with AI markers")
        
        if any("Business Rule" in r.check_name for r in failed_results):
            recommendations.append("📋 Business rule violations require immediate attention")
        
        if not recommendations:
            recommendations.append("✨ All AI safety checks passed - code ready for deployment")
        
        return recommendations
    
    def _extract_test_count(self, output: str) -> int:
        """Extract number of tests run from pytest output"""
        import re
        match = re.search(r'(\d+) passed', output)
        return int(match.group(1)) if match else 0
    
    def _parse_revenue_failures(self, output: str) -> List[Dict[str, str]]:
        """Parse revenue protection failures from pytest output"""
        # Simple parsing - in production this would be more sophisticated
        failures = []
        lines = output.split('\n')
        
        for i, line in enumerate(lines):
            if 'FAILED' in line and 'revenue' in line.lower():
                failures.append({
                    "test": line.strip(),
                    "location": lines[i-1] if i > 0 else "Unknown"
                })
        
        return failures


def main():
    """Main entry point for CI/CD integration"""
    pipeline = AISafetyPipeline()
    
    try:
        report = pipeline.run_full_pipeline()
        
        # Output results
        print("\n" + "="*60)
        print("🛡️  AI SAFETY PIPELINE REPORT")
        print("="*60)
        print(f"Overall Status: {report['overall_status']}")
        print(f"Execution Time: {report['total_execution_time']:.2f}s")
        print(f"Results: {report['summary']['passed']}✅ {report['summary']['failed']}❌ {report['summary']['warned']}⚠️")
        
        if report['recommendations']:
            print("\n📋 Recommendations:")
            for rec in report['recommendations']:
                print(f"  • {rec}")
        
        # Save detailed report
        report_file = Path("ai_safety_report.json")
        with report_file.open('w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📊 Detailed report saved: {report_file}")
        
        # Exit with appropriate code for CI/CD
        exit_code = 1 if report['overall_status'] == 'FAIL' else 0
        sys.exit(exit_code)
        
    except Exception as e:
        print(f"❌ AI Safety Pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()