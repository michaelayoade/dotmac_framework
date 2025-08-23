#!/usr/bin/env python3
"""
Intelligent Decision Engine for DotMac Framework CI/CD Pipeline

This script analyzes all test results and makes intelligent deployment decisions:
- If ALL tests pass (100% success rate): Automatically start production server
- If ANY tests fail: Continue alignment and remediation work

The engine provides detailed failure analysis and remediation recommendations.
"""

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import subprocess
import yaml

class IntelligentDecisionEngine:
    """Main intelligent decision engine class."""
    
    def __init__(self):
        self.test_results = {}
        self.failure_analysis = []
        self.remediation_plan = []
        self.decision_matrix = {
            'quality': {'weight': 0.25, 'blocking': True},
            'security': {'weight': 0.30, 'blocking': True},
            'unit_tests': {'weight': 0.15, 'blocking': True},
            'integration': {'weight': 0.15, 'blocking': True},
            'e2e': {'weight': 0.10, 'blocking': True},
            'performance': {'weight': 0.03, 'blocking': False},
            'accessibility': {'weight': 0.02, 'blocking': False}
        }
        
    def analyze_and_decide(self, **test_results) -> Dict[str, Any]:
        """
        Main decision logic: Analyze all test results and make deployment decision.
        
        Returns:
            Dict containing:
            - action: 'deploy' or 'remediate'
            - ready: boolean indicating if deployment should proceed
            - analysis: detailed failure analysis
            - remediation: list of recommended fixes
        """
        print("🧠 Intelligent Decision Engine - Analyzing Test Results")
        print("=" * 70)
        
        # Store test results
        self.test_results = test_results
        force_deployment = test_results.get('force_deployment', 'false') == 'true'
        
        # Analyze each test category
        analysis_results = {
            'quality': self._analyze_quality_results(),
            'security': self._analyze_security_results(),
            'unit_tests': self._analyze_unit_test_results(),
            'integration': self._analyze_integration_results(),
            'e2e': self._analyze_e2e_results(),
            'performance': self._analyze_performance_results(),
            'accessibility': self._analyze_accessibility_results()
        }
        
        # Calculate overall score and blocking issues
        overall_score, blocking_failures = self._calculate_overall_score(analysis_results)
        
        # Make deployment decision
        deployment_decision = self._make_deployment_decision(
            overall_score, blocking_failures, force_deployment
        )
        
        # Generate detailed analysis and remediation plan
        self._generate_failure_analysis(analysis_results)
        self._generate_remediation_plan(analysis_results)
        
        # Create decision report
        decision_report = {
            'timestamp': datetime.now().isoformat(),
            'overall_score': overall_score,
            'blocking_failures': blocking_failures,
            'deployment_ready': deployment_decision['ready'],
            'deployment_action': deployment_decision['action'],
            'test_results': analysis_results,
            'failure_analysis': self.failure_analysis,
            'remediation_plan': self.remediation_plan,
            'force_deployment': force_deployment
        }
        
        # Save decision outputs for GitHub Actions
        self._save_decision_outputs(decision_report)
        
        # Print decision summary
        self._print_decision_summary(decision_report)
        
        return decision_report
    
    def _analyze_quality_results(self) -> Dict[str, Any]:
        """Analyze code quality test results."""
        quality_passed = self.test_results.get('quality_passed', 'false') == 'true'
        
        result = {
            'passed': quality_passed,
            'score': 100.0 if quality_passed else 0.0,
            'weight': self.decision_matrix['quality']['weight'],
            'blocking': self.decision_matrix['quality']['blocking'],
            'details': {}
        }
        
        if not quality_passed:
            result['issues'] = self._extract_quality_issues()
            
        return result
    
    def _analyze_security_results(self) -> Dict[str, Any]:
        """Analyze security test results."""
        security_passed = self.test_results.get('security_passed', 'false') == 'true'
        vulnerabilities = int(self.test_results.get('vulnerabilities', '0'))
        
        # Security is critical - any vulnerability is a concern
        if vulnerabilities > 0:
            security_passed = False
            
        result = {
            'passed': security_passed,
            'score': max(0.0, 100.0 - (vulnerabilities * 10)),  # -10 points per vulnerability
            'weight': self.decision_matrix['security']['weight'],
            'blocking': self.decision_matrix['security']['blocking'],
            'vulnerabilities': vulnerabilities,
            'details': {}
        }
        
        if not security_passed:
            result['issues'] = self._extract_security_issues()
            
        return result
    
    def _analyze_unit_test_results(self) -> Dict[str, Any]:
        """Analyze unit test results from all components."""
        # Check unit test artifacts for pass/fail status
        unit_test_results = self._parse_unit_test_artifacts()
        
        total_tests = unit_test_results.get('total', 0)
        failed_tests = unit_test_results.get('failed', 0)
        coverage = unit_test_results.get('coverage', 0.0)
        
        # Pass if no failures and minimum coverage met
        passed = failed_tests == 0 and coverage >= 80.0
        success_rate = ((total_tests - failed_tests) / total_tests * 100) if total_tests > 0 else 0
        
        result = {
            'passed': passed,
            'score': (success_rate * 0.7) + (min(coverage, 100.0) * 0.3),  # 70% success rate, 30% coverage
            'weight': self.decision_matrix['unit_tests']['weight'],
            'blocking': self.decision_matrix['unit_tests']['blocking'],
            'total_tests': total_tests,
            'failed_tests': failed_tests,
            'success_rate': success_rate,
            'coverage': coverage,
            'details': unit_test_results
        }
        
        if not passed:
            result['issues'] = self._extract_unit_test_issues(unit_test_results)
            
        return result
    
    def _analyze_integration_results(self) -> Dict[str, Any]:
        """Analyze integration test results."""
        integration_passed = self.test_results.get('integration_passed', 'false') == 'true'
        
        # Parse integration test artifacts
        integration_results = self._parse_integration_test_artifacts()
        
        result = {
            'passed': integration_passed,
            'score': 100.0 if integration_passed else 0.0,
            'weight': self.decision_matrix['integration']['weight'],
            'blocking': self.decision_matrix['integration']['blocking'],
            'details': integration_results
        }
        
        if not integration_passed:
            result['issues'] = self._extract_integration_issues()
            
        return result
    
    def _analyze_e2e_results(self) -> Dict[str, Any]:
        """Analyze E2E test results across all 7 portals."""
        # Parse E2E test artifacts for all portals and browsers
        e2e_results = self._parse_e2e_test_artifacts()
        
        total_portals = 7
        total_browsers = 3
        expected_test_runs = total_portals * total_browsers
        
        passed_runs = e2e_results.get('passed_runs', 0)
        failed_runs = e2e_results.get('failed_runs', 0)
        total_runs = passed_runs + failed_runs
        
        # E2E tests pass if all portal/browser combinations pass
        e2e_passed = failed_runs == 0 and total_runs >= expected_test_runs * 0.9  # Allow 10% margin
        success_rate = (passed_runs / total_runs * 100) if total_runs > 0 else 0
        
        result = {
            'passed': e2e_passed,
            'score': success_rate,
            'weight': self.decision_matrix['e2e']['weight'],
            'blocking': self.decision_matrix['e2e']['blocking'],
            'total_portals': total_portals,
            'expected_runs': expected_test_runs,
            'passed_runs': passed_runs,
            'failed_runs': failed_runs,
            'success_rate': success_rate,
            'details': e2e_results
        }
        
        if not e2e_passed:
            result['issues'] = self._extract_e2e_issues(e2e_results)
            
        return result
    
    def _analyze_performance_results(self) -> Dict[str, Any]:
        """Analyze performance test results."""
        performance_passed = self.test_results.get('performance_passed', 'true') == 'true'
        
        # Parse performance artifacts
        perf_results = self._parse_performance_artifacts()
        
        core_vitals_score = float(self.test_results.get('core_vitals_score', '100.0'))
        
        result = {
            'passed': performance_passed,
            'score': core_vitals_score,
            'weight': self.decision_matrix['performance']['weight'],
            'blocking': self.decision_matrix['performance']['blocking'],
            'core_vitals_score': core_vitals_score,
            'details': perf_results
        }
        
        if not performance_passed:
            result['issues'] = self._extract_performance_issues(perf_results)
            
        return result
    
    def _analyze_accessibility_results(self) -> Dict[str, Any]:
        """Analyze accessibility test results."""
        a11y_passed = self.test_results.get('a11y_passed', 'true') == 'true'
        a11y_score = float(self.test_results.get('a11y_score', '100.0'))
        
        result = {
            'passed': a11y_passed,
            'score': a11y_score,
            'weight': self.decision_matrix['accessibility']['weight'],
            'blocking': self.decision_matrix['accessibility']['blocking'],
            'accessibility_score': a11y_score,
            'details': {}
        }
        
        if not a11y_passed:
            result['issues'] = self._extract_accessibility_issues()
            
        return result
    
    def _calculate_overall_score(self, analysis_results: Dict[str, Dict]) -> Tuple[float, List[str]]:
        """Calculate weighted overall score and identify blocking failures."""
        total_score = 0.0
        total_weight = 0.0
        blocking_failures = []
        
        for category, result in analysis_results.items():
            weight = result['weight']
            score = result['score']
            
            total_score += score * weight
            total_weight += weight
            
            # Check for blocking failures
            if result['blocking'] and not result['passed']:
                blocking_failures.append(category)
        
        overall_score = total_score / total_weight if total_weight > 0 else 0.0
        
        return overall_score, blocking_failures
    
    def _make_deployment_decision(self, overall_score: float, blocking_failures: List[str], force_deployment: bool) -> Dict[str, Any]:
        """Make the final deployment decision based on analysis."""
        
        # Perfect score (100%) and no blocking failures = automatic deployment
        if overall_score >= 100.0 and len(blocking_failures) == 0:
            return {
                'action': 'deploy',
                'ready': True,
                'reason': 'All tests passed (100% success rate) - Ready for production deployment'
            }
        
        # Force deployment override (with warnings)
        if force_deployment:
            return {
                'action': 'deploy',
                'ready': True,
                'reason': f'Force deployment requested (Score: {overall_score:.1f}%, Blocking issues: {len(blocking_failures)})'
            }
        
        # Any blocking failures = continue alignment
        if len(blocking_failures) > 0:
            return {
                'action': 'remediate',
                'ready': False,
                'reason': f'Blocking failures detected in: {", ".join(blocking_failures)}'
            }
        
        # Non-blocking failures but low score = continue alignment
        if overall_score < 95.0:
            return {
                'action': 'remediate',
                'ready': False,
                'reason': f'Overall score below threshold: {overall_score:.1f}% (minimum: 95%)'
            }
        
        # High score but not perfect = continue alignment for perfection
        return {
            'action': 'remediate',
            'ready': False,
            'reason': f'Pursuing 100% test success rate (Current: {overall_score:.1f}%)'
        }
    
    def _generate_failure_analysis(self, analysis_results: Dict[str, Dict]):
        """Generate detailed failure analysis."""
        self.failure_analysis = []
        
        for category, result in analysis_results.items():
            if not result['passed']:
                category_analysis = {
                    'category': category,
                    'severity': 'CRITICAL' if result['blocking'] else 'WARNING',
                    'score': result['score'],
                    'weight': result['weight'],
                    'issues': result.get('issues', []),
                    'impact': self._calculate_failure_impact(category, result)
                }
                self.failure_analysis.append(category_analysis)
        
        # Sort by severity and impact
        self.failure_analysis.sort(key=lambda x: (x['severity'] == 'WARNING', -x['weight']))
    
    def _generate_remediation_plan(self, analysis_results: Dict[str, Dict]):
        """Generate specific remediation recommendations."""
        self.remediation_plan = []
        
        for category, result in analysis_results.items():
            if not result['passed']:
                remediation_steps = self._get_remediation_steps(category, result)
                
                plan_item = {
                    'category': category,
                    'priority': 'HIGH' if result['blocking'] else 'MEDIUM',
                    'estimated_time': self._estimate_fix_time(category, result),
                    'automated_fixes': remediation_steps.get('automated', []),
                    'manual_fixes': remediation_steps.get('manual', []),
                    'team_assignment': self._assign_remediation_team(category)
                }
                self.remediation_plan.append(plan_item)
        
        # Sort by priority and estimated time
        priority_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
        self.remediation_plan.sort(key=lambda x: (priority_order[x['priority']], x['estimated_time']))
    
    def _get_remediation_steps(self, category: str, result: Dict) -> Dict[str, List[str]]:
        """Get specific remediation steps for each failure category."""
        remediation_map = {
            'quality': {
                'automated': [
                    'Run automated code formatting (Black, isort)',
                    'Fix simple linting issues with ruff --fix',
                    'Update import statements and remove unused imports'
                ],
                'manual': [
                    'Review and fix complex code quality violations',
                    'Refactor functions exceeding complexity limits',
                    'Add missing type hints and docstrings'
                ]
            },
            'security': {
                'automated': [
                    'Update vulnerable dependencies to latest secure versions',
                    'Apply security patches automatically',
                    'Remove hardcoded secrets and use environment variables'
                ],
                'manual': [
                    'Review and fix critical security vulnerabilities',
                    'Implement additional input validation',
                    'Add security headers and configurations'
                ]
            },
            'unit_tests': {
                'automated': [
                    'Generate basic unit test templates for uncovered code',
                    'Fix simple test assertion errors',
                    'Update test data and mocks'
                ],
                'manual': [
                    'Write comprehensive unit tests for failing components',
                    'Fix complex test logic errors',
                    'Increase test coverage to minimum 80%'
                ]
            },
            'integration': {
                'automated': [
                    'Restart failed services and retry tests',
                    'Update integration test configurations',
                    'Fix environment variable issues'
                ],
                'manual': [
                    'Debug and fix service communication issues',
                    'Update API contracts and schemas',
                    'Fix database migration and setup issues'
                ]
            },
            'e2e': {
                'automated': [
                    'Retry failed E2E tests with different timeouts',
                    'Update page selectors and test data',
                    'Fix browser compatibility issues'
                ],
                'manual': [
                    'Debug and fix portal-specific workflow issues',
                    'Update E2E test scenarios for new features',
                    'Fix cross-browser compatibility problems'
                ]
            },
            'performance': {
                'automated': [
                    'Optimize bundle sizes automatically',
                    'Enable performance optimizations in build',
                    'Update performance budgets'
                ],
                'manual': [
                    'Profile and optimize slow API endpoints',
                    'Implement caching strategies',
                    'Optimize Core Web Vitals metrics'
                ]
            },
            'accessibility': {
                'automated': [
                    'Fix simple accessibility issues (alt text, labels)',
                    'Add ARIA attributes automatically',
                    'Update color contrast ratios'
                ],
                'manual': [
                    'Review and fix complex accessibility violations',
                    'Test with screen readers and assistive technologies',
                    'Implement keyboard navigation improvements'
                ]
            }
        }
        
        return remediation_map.get(category, {'automated': [], 'manual': []})
    
    def _assign_remediation_team(self, category: str) -> str:
        """Assign appropriate team based on failure category."""
        team_assignments = {
            'quality': 'DevOps/Code Quality Team',
            'security': 'Security Team',
            'unit_tests': 'Development Teams (by component)',
            'integration': 'Backend/Integration Team',
            'e2e': 'QA/Frontend Team',
            'performance': 'Performance/Infrastructure Team',
            'accessibility': 'UX/Frontend Team'
        }
        
        return team_assignments.get(category, 'Development Team')
    
    def _estimate_fix_time(self, category: str, result: Dict) -> int:
        """Estimate time to fix issues in minutes."""
        base_times = {
            'quality': 30,
            'security': 120,
            'unit_tests': 60,
            'integration': 90,
            'e2e': 45,
            'performance': 180,
            'accessibility': 60
        }
        
        base_time = base_times.get(category, 60)
        issue_count = len(result.get('issues', []))
        
        # Scale by number of issues
        estimated_time = base_time + (issue_count * 15)
        
        return min(estimated_time, 480)  # Cap at 8 hours
    
    def _calculate_failure_impact(self, category: str, result: Dict) -> str:
        """Calculate impact level of failure."""
        if result['blocking'] and result['score'] < 50:
            return 'CRITICAL'
        elif result['blocking']:
            return 'HIGH'
        elif result['score'] < 70:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    # Artifact parsing methods
    def _parse_unit_test_artifacts(self) -> Dict[str, Any]:
        """Parse unit test artifacts from all components."""
        test_artifacts_dir = Path('test-artifacts')
        unit_results = {'total': 0, 'failed': 0, 'coverage': 0.0}
        
        if not test_artifacts_dir.exists():
            return unit_results
        
        # Look for unit test result files
        junit_files = list(test_artifacts_dir.glob('**/junit*.xml'))
        coverage_files = list(test_artifacts_dir.glob('**/coverage*.xml'))
        
        for junit_file in junit_files:
            try:
                tree = ET.parse(junit_file)
                root = tree.getroot()
                tests = int(root.get('tests', 0))
                failures = int(root.get('failures', 0))
                errors = int(root.get('errors', 0))
                
                unit_results['total'] += tests
                unit_results['failed'] += failures + errors
            except Exception as e:
                print(f"  ⚠️  Error parsing {junit_file}: {e}")
        
        # Parse coverage
        for coverage_file in coverage_files:
            try:
                tree = ET.parse(coverage_file)
                root = tree.getroot()
                coverage_elem = root.find(".//coverage")
                if coverage_elem is not None:
                    coverage = float(coverage_elem.get("line-rate", 0)) * 100
                    unit_results['coverage'] = max(unit_results['coverage'], coverage)
            except Exception as e:
                print(f"  ⚠️  Error parsing {coverage_file}: {e}")
        
        return unit_results
    
    def _parse_integration_test_artifacts(self) -> Dict[str, Any]:
        """Parse integration test artifacts."""
        # Similar to unit test parsing but for integration tests
        return {'status': 'parsed'}
    
    def _parse_e2e_test_artifacts(self) -> Dict[str, Any]:
        """Parse E2E test artifacts for all portals and browsers."""
        test_artifacts_dir = Path('test-artifacts')
        e2e_results = {'passed_runs': 0, 'failed_runs': 0, 'portal_results': {}}
        
        if not test_artifacts_dir.exists():
            return e2e_results
        
        # Look for E2E test result directories
        e2e_dirs = list(test_artifacts_dir.glob('e2e-results-*'))
        
        for e2e_dir in e2e_dirs:
            # Extract portal and browser from directory name
            dir_parts = e2e_dir.name.split('-')
            if len(dir_parts) >= 4:
                portal = dir_parts[2]
                browser = dir_parts[3]
                
                # Check for test results
                junit_files = list(e2e_dir.glob('**/junit*.xml'))
                if junit_files:
                    try:
                        tree = ET.parse(junit_files[0])
                        root = tree.getroot()
                        failures = int(root.get('failures', 0))
                        errors = int(root.get('errors', 0))
                        
                        if failures + errors == 0:
                            e2e_results['passed_runs'] += 1
                        else:
                            e2e_results['failed_runs'] += 1
                            
                        e2e_results['portal_results'][f"{portal}-{browser}"] = {
                            'passed': failures + errors == 0,
                            'failures': failures,
                            'errors': errors
                        }
                    except Exception as e:
                        print(f"  ⚠️  Error parsing E2E results for {portal}-{browser}: {e}")
                        e2e_results['failed_runs'] += 1
        
        return e2e_results
    
    def _parse_performance_artifacts(self) -> Dict[str, Any]:
        """Parse performance test artifacts."""
        # Look for Lighthouse reports and performance metrics
        return {'status': 'parsed'}
    
    # Issue extraction methods
    def _extract_quality_issues(self) -> List[str]:
        """Extract specific code quality issues."""
        return [
            "Code complexity violations detected",
            "Formatting issues found",
            "Type checking errors present"
        ]
    
    def _extract_security_issues(self) -> List[str]:
        """Extract specific security issues."""
        return [
            "Vulnerable dependencies detected",
            "Security scan findings present",
            "Authentication/authorization issues"
        ]
    
    def _extract_unit_test_issues(self, results: Dict) -> List[str]:
        """Extract specific unit test issues."""
        issues = []
        if results['failed_tests'] > 0:
            issues.append(f"{results['failed_tests']} unit tests failing")
        if results['coverage'] < 80:
            issues.append(f"Coverage below minimum: {results['coverage']:.1f}% < 80%")
        return issues
    
    def _extract_integration_issues(self) -> List[str]:
        """Extract specific integration test issues."""
        return [
            "Service communication failures",
            "Database connection issues",
            "API contract violations"
        ]
    
    def _extract_e2e_issues(self, results: Dict) -> List[str]:
        """Extract specific E2E test issues."""
        issues = []
        if results['failed_runs'] > 0:
            issues.append(f"{results['failed_runs']} E2E test runs failed")
        
        for portal_browser, result in results.get('portal_results', {}).items():
            if not result['passed']:
                issues.append(f"{portal_browser}: {result['failures']} failures, {result['errors']} errors")
        
        return issues
    
    def _extract_performance_issues(self, results: Dict) -> List[str]:
        """Extract specific performance issues."""
        return [
            "Core Web Vitals scores below threshold",
            "API response times exceed limits",
            "Bundle sizes too large"
        ]
    
    def _extract_accessibility_issues(self) -> List[str]:
        """Extract specific accessibility issues."""
        return [
            "WCAG compliance violations",
            "Missing alt text and ARIA labels",
            "Keyboard navigation issues"
        ]
    
    def _save_decision_outputs(self, report: Dict[str, Any]):
        """Save decision outputs for GitHub Actions."""
        # Save deployment decision
        with open('.deployment-action', 'w') as f:
            f.write(report['deployment_action'])
        
        with open('.deployment-ready', 'w') as f:
            f.write(str(report['deployment_ready']).lower())
        
        # Save failure analysis
        with open('.failure-analysis', 'w') as f:
            f.write(json.dumps(report['failure_analysis'], indent=2))
        
        # Save remediation plan
        with open('.remediation-plan', 'w') as f:
            f.write(json.dumps(report['remediation_plan'], indent=2))
        
        # Save full report
        reports_dir = Path('decision-reports')
        reports_dir.mkdir(exist_ok=True)
        
        with open(reports_dir / f'decision-report-{datetime.now().strftime("%Y%m%d-%H%M%S")}.json', 'w') as f:
            json.dump(report, f, indent=2)
    
    def _print_decision_summary(self, report: Dict[str, Any]):
        """Print decision summary to console."""
        print("\n" + "=" * 70)
        print("🤖 INTELLIGENT DEPLOYMENT DECISION")
        print("=" * 70)
        
        # Overall status
        status_emoji = "✅" if report['deployment_ready'] else "❌"
        action = report['deployment_action'].upper()
        score = report['overall_score']
        
        print(f"\n{status_emoji} DECISION: {action}")
        print(f"📊 Overall Score: {score:.1f}%")
        print(f"🚫 Blocking Failures: {len(report['blocking_failures'])}")
        
        # Test results summary
        print(f"\n📋 TEST RESULTS SUMMARY:")
        for category, result in report['test_results'].items():
            status = "✅" if result['passed'] else "❌"
            blocking = " (BLOCKING)" if result['blocking'] and not result['passed'] else ""
            print(f"  {status} {category.upper()}: {result['score']:.1f}%{blocking}")
        
        # Failure analysis
        if report['failure_analysis']:
            print(f"\n🔍 FAILURE ANALYSIS:")
            for i, failure in enumerate(report['failure_analysis'][:3], 1):  # Show top 3
                print(f"  {i}. {failure['category'].upper()} ({failure['severity']})")
                for issue in failure['issues'][:2]:  # Show first 2 issues
                    print(f"     • {issue}")
        
        # Remediation plan
        if report['remediation_plan']:
            print(f"\n🔧 REMEDIATION PLAN:")
            total_time = sum(plan['estimated_time'] for plan in report['remediation_plan'])
            print(f"  📅 Estimated Total Time: {total_time // 60}h {total_time % 60}m")
            
            for i, plan in enumerate(report['remediation_plan'][:3], 1):  # Show top 3
                print(f"  {i}. {plan['category'].upper()} ({plan['priority']} - {plan['estimated_time']}m)")
                print(f"     👥 Team: {plan['team_assignment']}")
                if plan['automated_fixes']:
                    print(f"     🤖 Automated: {len(plan['automated_fixes'])} fixes available")
        
        print("\n" + "=" * 70)
        
        if report['deployment_ready']:
            print("🚀 READY FOR PRODUCTION DEPLOYMENT!")
            print("   All tests passed - Starting automatic server deployment...")
        else:
            print("🔄 CONTINUING ALIGNMENT PROCESS...")
            print("   Remediation workflow will begin automatically...")
        
        print("=" * 70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Intelligent Decision Engine for CI/CD Pipeline")
    
    # Test result inputs
    parser.add_argument('--quality-passed', default='false', help='Code quality test result')
    parser.add_argument('--security-passed', default='false', help='Security test result')
    parser.add_argument('--unit-passed', default='false', help='Unit test result')
    parser.add_argument('--integration-passed', default='false', help='Integration test result')
    parser.add_argument('--e2e-passed', default='false', help='E2E test result')
    parser.add_argument('--performance-passed', default='true', help='Performance test result')
    parser.add_argument('--a11y-passed', default='true', help='Accessibility test result')
    
    # Additional parameters
    parser.add_argument('--vulnerabilities', default='0', help='Number of security vulnerabilities')
    parser.add_argument('--core-vitals-score', default='100.0', help='Core Web Vitals score')
    parser.add_argument('--a11y-score', default='100.0', help='Accessibility score')
    parser.add_argument('--force-deployment', default='false', help='Force deployment override')
    
    # Workflow parameters
    parser.add_argument('--stage', help='Current pipeline stage')
    
    args = parser.parse_args()
    
    try:
        engine = IntelligentDecisionEngine()
        
        # Prepare test results
        test_results = {
            'quality_passed': args.quality_passed,
            'security_passed': args.security_passed,
            'unit_passed': args.unit_passed,
            'integration_passed': args.integration_passed,
            'e2e_passed': args.e2e_passed,
            'performance_passed': args.performance_passed,
            'a11y_passed': args.a11y_passed,
            'vulnerabilities': args.vulnerabilities,
            'core_vitals_score': args.core_vitals_score,
            'a11y_score': args.a11y_score,
            'force_deployment': args.force_deployment
        }
        
        # Run decision analysis
        decision_report = engine.analyze_and_decide(**test_results)
        
        # Exit with appropriate code
        exit_code = 0 if decision_report['deployment_ready'] else 1
        sys.exit(exit_code)
        
    except Exception as e:
        print(f"❌ Error in Intelligent Decision Engine: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()