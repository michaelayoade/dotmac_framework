#!/usr/bin/env python3
"""
Unified Test Reporter for DotMac Framework
==========================================
Aggregates test results from Python (pytest) and TypeScript (Jest/Playwright) 
into a single comprehensive report.
"""

import json
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict

@dataclass
class TestResult:
    """Individual test result."""
    name: str
    status: str  # "passed", "failed", "skipped"
    duration: float
    error_message: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None

@dataclass
class TestSuite:
    """Test suite results."""
    name: str
    framework: str  # "pytest", "jest", "playwright"
    total: int
    passed: int
    failed: int
    skipped: int
    duration: float
    coverage_percentage: Optional[float] = None
    tests: List[TestResult] = None

    def __post_init__(self):
        if self.tests is None:
            self.tests = []

@dataclass
class UnifiedTestReport:
    """Unified test report across all frameworks."""
    timestamp: str
    commit_sha: Optional[str]
    branch: Optional[str]
    total_suites: int
    total_tests: int
    total_passed: int
    total_failed: int
    total_skipped: int
    total_duration: float
    overall_success_rate: float
    coverage_percentage: Optional[float]
    suites: List[TestSuite]

class UnifiedTestReporter:
    """Main test reporter class."""
    
    def __init__(self, output_dir: str = "test-results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.suites: List[TestSuite] = []
        
    def parse_pytest_xml(self, xml_path: str) -> Optional[TestSuite]:
        """Parse pytest XML results."""
        if not Path(xml_path).exists():
            print(f"⚠️  Pytest XML not found: {xml_path}")
            return None
            
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # Parse testsuite element
            testsuite = root.find('testsuite') or root
            
            total = int(testsuite.get('tests', 0))
            failures = int(testsuite.get('failures', 0))
            errors = int(testsuite.get('errors', 0))
            skipped = int(testsuite.get('skipped', 0))
            duration = float(testsuite.get('time', 0))
            
            passed = total - failures - errors - skipped
            failed = failures + errors
            
            tests = []
            for testcase in testsuite.findall('testcase'):
                test_name = f"{testcase.get('classname')}.{testcase.get('name')}"
                test_duration = float(testcase.get('time', 0))
                
                # Determine status
                if testcase.find('failure') is not None:
                    status = "failed"
                    error_msg = testcase.find('failure').text
                elif testcase.find('error') is not None:
                    status = "failed"
                    error_msg = testcase.find('error').text
                elif testcase.find('skipped') is not None:
                    status = "skipped"
                    error_msg = None
                else:
                    status = "passed"
                    error_msg = None
                
                tests.append(TestResult(
                    name=test_name,
                    status=status,
                    duration=test_duration,
                    error_message=error_msg,
                    file_path=testcase.get('file')
                ))
            
            return TestSuite(
                name="Backend Tests (Python)",
                framework="pytest",
                total=total,
                passed=passed,
                failed=failed,
                skipped=skipped,
                duration=duration,
                tests=tests
            )
            
        except Exception as e:
            print(f"❌ Error parsing pytest XML {xml_path}: {e}")
            return None

    def parse_jest_json(self, json_path: str) -> Optional[TestSuite]:
        """Parse Jest JSON results."""
        if not Path(json_path).exists():
            print(f"⚠️  Jest JSON not found: {json_path}")
            return None
            
        try:
            with open(json_path) as f:
                data = json.load(f)
            
            # Extract test results
            total_tests = data.get('numTotalTests', 0)
            passed_tests = data.get('numPassedTests', 0)
            failed_tests = data.get('numFailedTests', 0)
            skipped_tests = data.get('numPendingTests', 0)
            
            # Calculate duration (Jest reports in milliseconds)
            start_time = data.get('startTime', 0)
            end_time = data.get('endTime', start_time)
            duration = (end_time - start_time) / 1000.0  # Convert to seconds
            
            tests = []
            for test_suite in data.get('testResults', []):
                for assertion in test_suite.get('assertionResults', []):
                    tests.append(TestResult(
                        name=assertion.get('fullName', 'Unknown'),
                        status=assertion.get('status', 'unknown'),
                        duration=assertion.get('duration', 0) / 1000.0,  # Convert to seconds
                        error_message=assertion.get('failureMessages', [None])[0],
                        file_path=test_suite.get('name')
                    ))
            
            return TestSuite(
                name="Frontend Tests (TypeScript)",
                framework="jest",
                total=total_tests,
                passed=passed_tests,
                failed=failed_tests,
                skipped=skipped_tests,
                duration=duration,
                tests=tests
            )
            
        except Exception as e:
            print(f"❌ Error parsing Jest JSON {json_path}: {e}")
            return None

    def parse_playwright_json(self, json_path: str) -> Optional[TestSuite]:
        """Parse Playwright JSON results."""
        if not Path(json_path).exists():
            print(f"⚠️  Playwright JSON not found: {json_path}")
            return None
            
        try:
            with open(json_path) as f:
                data = json.load(f)
            
            # Extract test statistics
            total_tests = 0
            passed_tests = 0
            failed_tests = 0
            skipped_tests = 0
            total_duration = 0
            
            tests = []
            
            for suite in data.get('suites', []):
                for spec in suite.get('specs', []):
                    for test in spec.get('tests', []):
                        total_tests += 1
                        test_duration = sum(result.get('duration', 0) for result in test.get('results', [])) / 1000.0
                        total_duration += test_duration
                        
                        # Determine overall test status
                        results = test.get('results', [])
                        if not results:
                            status = "skipped"
                            skipped_tests += 1
                        else:
                            status = results[0].get('status', 'unknown')
                            if status == 'passed':
                                passed_tests += 1
                            elif status in ['failed', 'timedOut', 'interrupted']:
                                failed_tests += 1
                                status = "failed"
                            else:
                                skipped_tests += 1
                                status = "skipped"
                        
                        error_message = None
                        if status == "failed" and results:
                            error_message = results[0].get('error', {}).get('message')
                        
                        tests.append(TestResult(
                            name=test.get('title', 'Unknown'),
                            status=status,
                            duration=test_duration,
                            error_message=error_message,
                            file_path=spec.get('file')
                        ))
            
            return TestSuite(
                name="E2E Tests (Playwright)",
                framework="playwright",
                total=total_tests,
                passed=passed_tests,
                failed=failed_tests,
                skipped=skipped_tests,
                duration=total_duration,
                tests=tests
            )
            
        except Exception as e:
            print(f"❌ Error parsing Playwright JSON {json_path}: {e}")
            return None

    def parse_coverage_data(self) -> Optional[float]:
        """Parse coverage data from various sources."""
        coverage_files = [
            "coverage.xml",  # Python coverage
            "frontend/coverage/coverage-summary.json",  # JavaScript coverage
        ]
        
        total_coverage = []
        
        # Parse Python coverage
        python_coverage_path = "coverage.xml"
        if Path(python_coverage_path).exists():
            try:
                tree = ET.parse(python_coverage_path)
                root = tree.getroot()
                coverage_elem = root.find('.//coverage')
                if coverage_elem is not None:
                    line_rate = float(coverage_elem.get('line-rate', 0))
                    total_coverage.append(line_rate * 100)
            except Exception as e:
                print(f"⚠️  Could not parse Python coverage: {e}")
        
        # Parse JavaScript coverage
        js_coverage_path = "frontend/coverage/coverage-summary.json"
        if Path(js_coverage_path).exists():
            try:
                with open(js_coverage_path) as f:
                    data = json.load(f)
                coverage_pct = data.get('total', {}).get('lines', {}).get('pct', 0)
                total_coverage.append(coverage_pct)
            except Exception as e:
                print(f"⚠️  Could not parse JavaScript coverage: {e}")
        
        if total_coverage:
            return sum(total_coverage) / len(total_coverage)
        return None

    def collect_all_results(self):
        """Collect results from all test frameworks."""
        # Pytest results
        pytest_result = self.parse_pytest_xml("pytest-results.xml")
        if pytest_result:
            self.suites.append(pytest_result)

        # Jest results
        jest_result = self.parse_jest_json("frontend/test-results/jest-results.json")
        if jest_result:
            self.suites.append(jest_result)

        # Playwright results
        playwright_result = self.parse_playwright_json("frontend/test-results/results.json")
        if playwright_result:
            self.suites.append(playwright_result)

    def generate_unified_report(self) -> UnifiedTestReport:
        """Generate unified report from all collected results."""
        total_suites = len(self.suites)
        total_tests = sum(suite.total for suite in self.suites)
        total_passed = sum(suite.passed for suite in self.suites)
        total_failed = sum(suite.failed for suite in self.suites)
        total_skipped = sum(suite.skipped for suite in self.suites)
        total_duration = sum(suite.duration for suite in self.suites)
        
        success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        coverage = self.parse_coverage_data()
        
        # Get git information
        commit_sha = os.getenv('GITHUB_SHA') or os.getenv('CI_COMMIT_SHA')
        branch = os.getenv('GITHUB_REF_NAME') or os.getenv('CI_COMMIT_REF_NAME')
        
        return UnifiedTestReport(
            timestamp=datetime.now().isoformat(),
            commit_sha=commit_sha,
            branch=branch,
            total_suites=total_suites,
            total_tests=total_tests,
            total_passed=total_passed,
            total_failed=total_failed,
            total_skipped=total_skipped,
            total_duration=total_duration,
            overall_success_rate=success_rate,
            coverage_percentage=coverage,
            suites=self.suites
        )

    def generate_html_report(self, report: UnifiedTestReport, output_path: str = "test-results/unified-report.html"):
        """Generate HTML report."""
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>DotMac Framework - Unified Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { border-bottom: 2px solid #eee; padding-bottom: 20px; margin-bottom: 30px; }
        .title { color: #333; margin: 0; }
        .subtitle { color: #666; margin: 5px 0 0 0; font-size: 14px; }
        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .metric { background: #f8f9fa; padding: 15px; border-radius: 6px; text-align: center; border-left: 4px solid #007bff; }
        .metric-value { font-size: 24px; font-weight: bold; color: #333; }
        .metric-label { color: #666; font-size: 12px; text-transform: uppercase; margin-top: 5px; }
        .success { border-left-color: #28a745; }
        .warning { border-left-color: #ffc107; }
        .danger { border-left-color: #dc3545; }
        .suite { margin-bottom: 30px; border: 1px solid #ddd; border-radius: 6px; }
        .suite-header { background: #f8f9fa; padding: 15px; border-bottom: 1px solid #ddd; font-weight: bold; }
        .suite-stats { display: flex; gap: 20px; padding: 15px; background: #fafafa; font-size: 14px; }
        .test-list { max-height: 300px; overflow-y: auto; }
        .test-item { padding: 10px 15px; border-bottom: 1px solid #eee; display: flex; justify-content: between; align-items: center; }
        .test-item:last-child { border-bottom: none; }
        .test-name { flex: 1; }
        .test-status { padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; text-transform: uppercase; }
        .status-passed { background: #d4edda; color: #155724; }
        .status-failed { background: #f8d7da; color: #721c24; }
        .status-skipped { background: #fff3cd; color: #856404; }
        .test-duration { margin-left: 10px; color: #666; font-size: 12px; }
        .footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; text-align: center; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="title">🧪 DotMac Framework - Unified Test Report</h1>
            <p class="subtitle">Generated on {timestamp}</p>
            {git_info}
        </div>
        
        <div class="summary">
            <div class="metric {success_class}">
                <div class="metric-value">{total_tests}</div>
                <div class="metric-label">Total Tests</div>
            </div>
            <div class="metric success">
                <div class="metric-value">{total_passed}</div>
                <div class="metric-label">Passed</div>
            </div>
            <div class="metric {failed_class}">
                <div class="metric-value">{total_failed}</div>
                <div class="metric-label">Failed</div>
            </div>
            <div class="metric">
                <div class="metric-value">{total_skipped}</div>
                <div class="metric-label">Skipped</div>
            </div>
            <div class="metric {success_rate_class}">
                <div class="metric-value">{success_rate:.1f}%</div>
                <div class="metric-label">Success Rate</div>
            </div>
            {coverage_metric}
            <div class="metric">
                <div class="metric-value">{duration:.1f}s</div>
                <div class="metric-label">Total Duration</div>
            </div>
        </div>
        
        {suites_html}
        
        <div class="footer">
            <p>Generated by DotMac Framework Unified Test Reporter</p>
        </div>
    </div>
</body>
</html>
        """
        
        # Generate git info
        git_info = ""
        if report.commit_sha:
            git_info += f"<p class='subtitle'>Commit: <code>{report.commit_sha[:8]}</code>"
            if report.branch:
                git_info += f" on <code>{report.branch}</code>"
            git_info += "</p>"
        
        # Generate coverage metric
        coverage_metric = ""
        if report.coverage_percentage is not None:
            coverage_class = "success" if report.coverage_percentage >= 80 else "warning" if report.coverage_percentage >= 70 else "danger"
            coverage_metric = f'''
            <div class="metric {coverage_class}">
                <div class="metric-value">{report.coverage_percentage:.1f}%</div>
                <div class="metric-label">Coverage</div>
            </div>
            '''
        
        # Generate suites HTML
        suites_html = ""
        for suite in report.suites:
            suite_success_rate = (suite.passed / suite.total * 100) if suite.total > 0 else 0
            
            tests_html = ""
            for test in suite.tests[:20]:  # Show first 20 tests
                status_class = f"status-{test.status}"
                tests_html += f'''
                <div class="test-item">
                    <div class="test-name">{test.name}</div>
                    <div class="test-status {status_class}">{test.status}</div>
                    <div class="test-duration">{test.duration:.2f}s</div>
                </div>
                '''
            
            if len(suite.tests) > 20:
                tests_html += f'<div class="test-item"><div class="test-name">... and {len(suite.tests) - 20} more tests</div></div>'
            
            suites_html += f'''
            <div class="suite">
                <div class="suite-header">
                    {suite.name} ({suite.framework})
                </div>
                <div class="suite-stats">
                    <span><strong>Total:</strong> {suite.total}</span>
                    <span><strong>Passed:</strong> {suite.passed}</span>
                    <span><strong>Failed:</strong> {suite.failed}</span>
                    <span><strong>Skipped:</strong> {suite.skipped}</span>
                    <span><strong>Duration:</strong> {suite.duration:.1f}s</span>
                    <span><strong>Success Rate:</strong> {suite_success_rate:.1f}%</span>
                </div>
                <div class="test-list">
                    {tests_html}
                </div>
            </div>
            '''
        
        # Fill template
        success_rate_class = "success" if report.overall_success_rate >= 95 else "warning" if report.overall_success_rate >= 80 else "danger"
        failed_class = "danger" if report.total_failed > 0 else "success"
        success_class = "" if report.total_tests > 0 else "warning"
        
        html_content = html_template.format(
            timestamp=report.timestamp,
            git_info=git_info,
            total_tests=report.total_tests,
            total_passed=report.total_passed,
            total_failed=report.total_failed,
            total_skipped=report.total_skipped,
            success_rate=report.overall_success_rate,
            duration=report.total_duration,
            coverage_metric=coverage_metric,
            suites_html=suites_html,
            success_rate_class=success_rate_class,
            failed_class=failed_class,
            success_class=success_class
        )
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        print(f"✅ HTML report generated: {output_file}")

    def generate_json_report(self, report: UnifiedTestReport, output_path: str = "test-results/unified-report.json"):
        """Generate JSON report."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(asdict(report), f, indent=2)
        
        print(f"✅ JSON report generated: {output_file}")

    def print_summary(self, report: UnifiedTestReport):
        """Print test summary to console."""
        print("\n" + "="*60)
        print("🧪 DOTMAC FRAMEWORK - UNIFIED TEST REPORT")
        print("="*60)
        
        if report.commit_sha:
            print(f"📊 Commit: {report.commit_sha[:8]}")
        if report.branch:
            print(f"🌿 Branch: {report.branch}")
        
        print(f"⏰ Duration: {report.total_duration:.1f}s")
        print(f"📦 Test Suites: {report.total_suites}")
        print(f"🔬 Total Tests: {report.total_tests}")
        print(f"✅ Passed: {report.total_passed}")
        print(f"❌ Failed: {report.total_failed}")
        print(f"⏭️  Skipped: {report.total_skipped}")
        print(f"📈 Success Rate: {report.overall_success_rate:.1f}%")
        
        if report.coverage_percentage is not None:
            coverage_emoji = "🎯" if report.coverage_percentage >= 80 else "⚠️" if report.coverage_percentage >= 70 else "🔴"
            print(f"{coverage_emoji} Coverage: {report.coverage_percentage:.1f}%")
        
        print("\n📋 Suite Breakdown:")
        print("-" * 60)
        for suite in report.suites:
            suite_rate = (suite.passed / suite.total * 100) if suite.total > 0 else 0
            status_emoji = "✅" if suite.failed == 0 else "❌" if suite_rate < 80 else "⚠️"
            print(f"{status_emoji} {suite.name}: {suite.passed}/{suite.total} ({suite_rate:.1f}%) in {suite.duration:.1f}s")
        
        print("\n" + "="*60)
        
        # Overall status
        if report.total_failed == 0:
            print("🎉 ALL TESTS PASSED! Ready for deployment.")
            return 0
        else:
            print("❌ TESTS FAILED! Please review and fix failing tests.")
            return 1


def main():
    """Main entry point."""
    print("🚀 Starting DotMac Framework Unified Test Reporter...")
    
    reporter = UnifiedTestReporter()
    
    # Collect results from all frameworks
    reporter.collect_all_results()
    
    if not reporter.suites:
        print("⚠️  No test results found. Please run tests first.")
        return 1
    
    # Generate unified report
    report = reporter.generate_unified_report()
    
    # Generate outputs
    reporter.generate_json_report(report)
    reporter.generate_html_report(report)
    
    # Print summary and return exit code
    return reporter.print_summary(report)


if __name__ == "__main__":
    sys.exit(main())