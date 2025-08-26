#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)

"""
Quality Assurance Automation Suite

QUALITY SPRINT: Week 4 - Standards & Documentation
Comprehensive automation for code quality enforcement, monitoring, and reporting.
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import tempfile
import shutil


class QualityGateStatus(Enum, timezone):
    """Quality gate status enumeration."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


class QualitySeverity(Enum):
    """Quality issue severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class QualityIssue:
    """Represents a quality issue found during analysis."""
    file_path: str
    line_number: Optional[int]
    rule_id: str
    message: str
    severity: QualitySeverity
    category: str
    tool: str
    fix_suggestion: Optional[str] = None


@dataclass
class QualityGateResult:
    """Result of a quality gate execution."""
    gate_name: str
    status: QualityGateStatus
    duration_seconds: float
    issues: List[QualityIssue]
    metrics: Dict[str, Any]
    started_at: datetime
    completed_at: datetime


@dataclass
class QualityReport:
    """Comprehensive quality assessment report."""
    project_root: str
    report_timestamp: datetime
    overall_status: QualityGateStatus
    gate_results: List[QualityGateResult]
    summary_metrics: Dict[str, Any]
    recommendations: List[str]
    trend_analysis: Dict[str, Any]


class QualityAssuranceAutomation:
    """Comprehensive quality assurance automation system."""
    
    def __init__(self, project_root: Path, config_file: Optional[Path] = None):
        """Initialize the QA automation system.
        
        Args:
            project_root: Root directory of the project
            config_file: Optional configuration file path
        """
        self.project_root = project_root
        self.config = self._load_config(config_file)
        self.report_dir = project_root / "quality-reports"
        self.report_dir.mkdir(exist_ok=True)
        
        # Quality gates configuration
        self.quality_gates = {
            'security_scan': {
                'enabled': True,
                'blocking': True,
                'timeout': 300,
                'retry_count': 0
            },
            'complexity_check': {
                'enabled': True,
                'blocking': True,
                'timeout': 120,
                'retry_count': 0
            },
            'type_check': {
                'enabled': True,
                'blocking': True,
                'timeout': 180,
                'retry_count': 1
            },
            'test_coverage': {
                'enabled': True,
                'blocking': True,
                'timeout': 600,
                'retry_count': 1
            },
            'code_style': {
                'enabled': True,
                'blocking': False,
                'timeout': 60,
                'retry_count': 0
            },
            'documentation_check': {
                'enabled': True,
                'blocking': False,
                'timeout': 120,
                'retry_count': 0
            }
        }
    
    def _load_config(self, config_file: Optional[Path]) -> Dict[str, Any]:
        """Load configuration from file or use defaults."""
        default_config = {
            'complexity_threshold': 10,
            'coverage_threshold': 80,
            'critical_coverage_threshold': 90,
            'security_threshold': 'critical',
            'fail_fast': True,
            'generate_reports': True,
            'send_notifications': False,
            'excluded_paths': [
                '__pycache__',
                '.git',
                'venv',
                'quality_test_env',
                'alembic/versions'
            ]
        }
        
        if config_file and config_file.exists():
            try:
                import yaml
                with open(config_file, 'r') as f:
                    file_config = yaml.safe_load(f)
                default_config.update(file_config)
            except Exception as e:
logger.warning(f"Warning: Could not load config file {config_file}: {e}")
        
        return default_config
    
    def run_all_quality_gates(self, fail_fast: Optional[bool] = None) -> QualityReport:
        """Run all enabled quality gates and generate comprehensive report.
        
        Args:
            fail_fast: Stop on first failure if True
            
        Returns:
            QualityReport with results of all gates
        """
        if fail_fast is None:
            fail_fast = self.config.get('fail_fast', True)
        
logger.info("🚀 Starting Comprehensive Quality Assurance Analysis")
logger.info("=" * 60)
        
        report_start = datetime.now(timezone.utc)
        gate_results = []
        overall_status = QualityGateStatus.PASSED
        
        # Execute all enabled quality gates
        for gate_name, gate_config in self.quality_gates.items():
            if not gate_config['enabled']:
logger.info(f"⏭️  Skipping {gate_name} (disabled)")
                continue
            
logger.info(f"\n🔍 Running {gate_name.replace('_', ' ').title()}")
logger.info("-" * 40)
            
            gate_result = self._run_quality_gate(gate_name, gate_config)
            gate_results.append(gate_result)
            
            # Display gate result
            status_icon = {
                QualityGateStatus.PASSED: "✅",
                QualityGateStatus.FAILED: "❌",
                QualityGateStatus.WARNING: "⚠️",
                QualityGateStatus.SKIPPED: "⏭️"
            }[gate_result.status]
            
logger.info(f"{status_icon} {gate_name}: {gate_result.status.value.upper()
                  f"({gate_result.duration_seconds:.1f}s)")
            
            if gate_result.issues:
                critical_count = sum(1 for issue in gate_result.issues 
                                   if issue.severity == QualitySeverity.CRITICAL)
                high_count = sum(1 for issue in gate_result.issues 
                               if issue.severity == QualitySeverity.HIGH)
                
                if critical_count > 0:
logger.info(f"  🔴 {critical_count} critical issues")
                if high_count > 0:
logger.info(f"  🟡 {high_count} high priority issues")
            
            # Check if we should fail fast
            if (gate_result.status == QualityGateStatus.FAILED and 
                gate_config['blocking'] and fail_fast):
logger.info(f"\n❌ QUALITY GATE FAILURE: {gate_name} failed (blocking)")
                overall_status = QualityGateStatus.FAILED
                break
            
            # Update overall status
            if gate_result.status == QualityGateStatus.FAILED and gate_config['blocking']:
                overall_status = QualityGateStatus.FAILED
            elif (gate_result.status == QualityGateStatus.WARNING and 
                  overall_status == QualityGateStatus.PASSED):
                overall_status = QualityGateStatus.WARNING
        
        # Generate comprehensive report
        report = QualityReport(
            project_root=str(self.project_root),
            report_timestamp=datetime.now(timezone.utc),
            overall_status=overall_status,
            gate_results=gate_results,
            summary_metrics=self._calculate_summary_metrics(gate_results),
            recommendations=self._generate_recommendations(gate_results),
            trend_analysis=self._analyze_trends()
        )
        
        # Save and display report
        self._save_report(report)
        self._display_summary(report)
        
        return report
    
    def _run_quality_gate(self, gate_name: str, gate_config: Dict[str, Any]) -> QualityGateResult:
        """Execute a specific quality gate.
        
        Args:
            gate_name: Name of the quality gate
            gate_config: Configuration for the gate
            
        Returns:
            QualityGateResult with execution details
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Map gate names to execution methods
            gate_methods = {
                'security_scan': self._run_security_scan,
                'complexity_check': self._run_complexity_check,
                'type_check': self._run_type_check,
                'test_coverage': self._run_test_coverage,
                'code_style': self._run_code_style_check,
                'documentation_check': self._run_documentation_check
            }
            
            if gate_name not in gate_methods:
                raise ValueError(f"Unknown quality gate: {gate_name}")
            
            # Execute the gate
            gate_method = gate_methods[gate_name]
            status, issues, metrics = gate_method()
            
        except Exception as e:
logger.error(f"Error executing {gate_name}: {e}")
            status = QualityGateStatus.FAILED
            issues = [QualityIssue(
                file_path="system",
                line_number=None,
                rule_id="execution_error",
                message=f"Quality gate execution failed: {e}",
                severity=QualitySeverity.CRITICAL,
                category="system",
                tool=gate_name
            )]
            metrics = {}
        
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        
        return QualityGateResult(
            gate_name=gate_name,
            status=status,
            duration_seconds=duration,
            issues=issues,
            metrics=metrics,
            started_at=start_time,
            completed_at=end_time
        )
    
    def _run_security_scan(self) -> Tuple[QualityGateStatus, List[QualityIssue], Dict[str, Any]]:
        """Run comprehensive security scanning."""
        try:
            # Use the security scanner from the framework
            cmd = [
                sys.executable, "-m", "dotmac_isp.core.security.security_scanner",
                "--project-root", str(self.project_root),
                "--format", "json"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                # Parse security scan results
                try:
                    scan_data = json.loads(result.stdout)
                    issues = self._parse_security_issues(scan_data)
                    
                    critical_issues = [i for i in issues if i.severity == QualitySeverity.CRITICAL]
                    
                    if critical_issues:
                        status = QualityGateStatus.FAILED
                    elif any(i.severity == QualitySeverity.HIGH for i in issues):
                        status = QualityGateStatus.WARNING
                    else:
                        status = QualityGateStatus.PASSED
                    
                    metrics = {
                        'total_files_scanned': scan_data.get('total_files_scanned', 0),
                        'critical_findings': len(critical_issues),
                        'total_findings': len(issues)
                    }
                    
                    return status, issues, metrics
                    
                except json.JSONDecodeError:
                    # Fallback to text parsing
                    pass
            
            # Fallback implementation using basic patterns
            return self._basic_security_scan()
            
        except subprocess.TimeoutExpired:
            return QualityGateStatus.FAILED, [QualityIssue(
                file_path="system",
                line_number=None,
                rule_id="timeout",
                message="Security scan timed out",
                severity=QualitySeverity.CRITICAL,
                category="system",
                tool="security_scanner"
            )], {}
        except Exception as e:
            return QualityGateStatus.FAILED, [QualityIssue(
                file_path="system",
                line_number=None,
                rule_id="error",
                message=f"Security scan failed: {e}",
                severity=QualitySeverity.CRITICAL,
                category="system",
                tool="security_scanner"
            )], {}
    
    def _basic_security_scan(self) -> Tuple[QualityGateStatus, List[QualityIssue], Dict[str, Any]]:
        """Basic security scan using pattern matching."""
        issues = []
        files_scanned = 0
        
        # Dangerous patterns to look for
        dangerous_patterns = {
            r'password\s*=\s*["\'](?:testing123|secret123|admin|password)["\']': 'hardcoded_password',
            r'secret\s*=\s*["\'](?:testing123|secret123|admin)["\']': 'hardcoded_secret',
            r'api_key\s*=\s*["\'][^"\']{10,}["\']': 'hardcoded_api_key',
        }
        
        import re
        
        for py_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
            
            try:
                content = py_file.read_text(encoding='utf-8')
                files_scanned += 1
                
                for line_num, line in enumerate(content.splitlines(), 1):
                    for pattern, rule_id in dangerous_patterns.items():
                        if re.search(pattern, line, re.IGNORECASE):
                            issues.append(QualityIssue(
                                file_path=str(py_file.relative_to(self.project_root),
                                line_number=line_num,
                                rule_id=rule_id,
                                message=f"Potential hardcoded secret detected: {rule_id}",
                                severity=QualitySeverity.CRITICAL,
                                category="security",
                                tool="basic_security_scan",
                                fix_suggestion="Use environment variables or secure secret management"
                            )
            except Exception as e:
logger.warning(f"Warning: Could not scan file {py_file}: {e}")
        
        critical_issues = [i for i in issues if i.severity == QualitySeverity.CRITICAL]
        
        if critical_issues:
            status = QualityGateStatus.FAILED
        elif issues:
            status = QualityGateStatus.WARNING
        else:
            status = QualityGateStatus.PASSED
        
        metrics = {
            'total_files_scanned': files_scanned,
            'critical_findings': len(critical_issues),
            'total_findings': len(issues)
        }
        
        return status, issues, metrics
    
    def _run_complexity_check(self) -> Tuple[QualityGateStatus, List[QualityIssue], Dict[str, Any]]:
        """Run McCabe cyclomatic complexity analysis."""
        try:
            cmd = ["radon", "cc", str(self.project_root / "src"), "--min", "B", "--show-complexity", "--json"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            issues = []
            total_functions = 0
            complex_functions = 0
            
            if result.returncode == 0:
                try:
                    complexity_data = json.loads(result.stdout)
                    
                    for file_path, file_data in complexity_data.items():
                        for item in file_data:
                            if item['type'] == 'function':
                                total_functions += 1
                                complexity = item['complexity']
                                
                                if complexity > self.config['complexity_threshold']:
                                    complex_functions += 1
                                    severity = QualitySeverity.CRITICAL if complexity > 15 else QualitySeverity.HIGH
                                    
                                    issues.append(QualityIssue(
                                        file_path=file_path.replace(str(self.project_root) + "/", ""),
                                        line_number=item['lineno'],
                                        rule_id="high_complexity",
                                        message=f"Function '{item['name']}' has complexity {complexity} "
                                               f"(threshold: {self.config['complexity_threshold']})",
                                        severity=severity,
                                        category="complexity",
                                        tool="radon",
                                        fix_suggestion="Consider refactoring using Strategy Pattern or decomposition"
                                    )
                
                except json.JSONDecodeError:
                    # Parse text output as fallback
                    complex_functions = result.stdout.count("C") + result.stdout.count("D") + result.stdout.count("E") + result.stdout.count("F")
            
            critical_issues = [i for i in issues if i.severity == QualitySeverity.CRITICAL]
            
            if critical_issues:
                status = QualityGateStatus.FAILED
            elif issues:
                status = QualityGateStatus.WARNING
            else:
                status = QualityGateStatus.PASSED
            
            metrics = {
                'total_functions': total_functions,
                'complex_functions': complex_functions,
                'average_complexity': total_functions / max(1, complex_functions),
                'complexity_threshold': self.config['complexity_threshold']
            }
            
            return status, issues, metrics
            
        except subprocess.TimeoutExpired:
            return QualityGateStatus.FAILED, [QualityIssue(
                file_path="system",
                line_number=None,
                rule_id="timeout",
                message="Complexity check timed out",
                severity=QualitySeverity.CRITICAL,
                category="system",
                tool="radon"
            )], {}
        except Exception as e:
            return QualityGateStatus.FAILED, [], {'error': str(e)}
    
    def _run_type_check(self) -> Tuple[QualityGateStatus, List[QualityIssue], Dict[str, Any]]:
        """Run MyPy type checking."""
        try:
            cmd = ["mypy", str(self.project_root / "src"), "--json-report", "/dev/stdout"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            
            issues = []
            
            # Parse MyPy output
            for line in result.stdout.splitlines():
                if ": error:" in line or ": warning:" in line:
                    parts = line.split(":")
                    if len(parts) >= 4:
                        file_path = parts[0]
                        line_number = int(parts[1]) if parts[1].isdigit() else None
                        message = ":".join(parts[3:]).strip()
                        
                        severity = QualitySeverity.HIGH if "error" in line else QualitySeverity.MEDIUM
                        
                        issues.append(QualityIssue(
                            file_path=file_path.replace(str(self.project_root) + "/", ""),
                            line_number=line_number,
                            rule_id="type_error",
                            message=message,
                            severity=severity,
                            category="typing",
                            tool="mypy",
                            fix_suggestion="Add proper type annotations"
                        )
            
            error_count = len([i for i in issues if i.severity == QualitySeverity.HIGH])
            
            if error_count > 0:
                status = QualityGateStatus.FAILED
            elif issues:
                status = QualityGateStatus.WARNING
            else:
                status = QualityGateStatus.PASSED
            
            metrics = {
                'total_issues': len(issues),
                'error_count': error_count,
                'warning_count': len(issues) - error_count
            }
            
            return status, issues, metrics
            
        except Exception as e:
            return QualityGateStatus.FAILED, [], {'error': str(e)}
    
    def _run_test_coverage(self) -> Tuple[QualityGateStatus, List[QualityIssue], Dict[str, Any]]:
        """Run test coverage analysis."""
        try:
            # Set PYTHONPATH to include src directory
            env = os.environ.copy()
            env['PYTHONPATH'] = str(self.project_root / "src")
            
            cmd = [
                "pytest", 
                str(self.project_root / "tests"),
                "--cov=" + str(self.project_root / "src"),
                "--cov-report=json",
                f"--cov-fail-under={self.config['coverage_threshold']}",
                "--tb=short"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600, env=env)
            
            issues = []
            coverage_data = {}
            
            # Try to read coverage report
            coverage_file = self.project_root / "coverage.json"
            if coverage_file.exists():
                try:
                    with open(coverage_file, 'r') as f:
                        coverage_data = json.load(f)
                except Exception as e:
logger.warning(f"Warning: Could not read coverage data: {e}")
            
            total_coverage = coverage_data.get('totals', {}).get('percent_covered', 0)
            
            # Check coverage threshold
            if total_coverage < self.config['coverage_threshold']:
                issues.append(QualityIssue(
                    file_path="project",
                    line_number=None,
                    rule_id="low_coverage",
                    message=f"Test coverage {total_coverage:.1f}% is below threshold "
                           f"{self.config['coverage_threshold']}%",
                    severity=QualitySeverity.CRITICAL,
                    category="testing",
                    tool="pytest",
                    fix_suggestion="Add more comprehensive test cases"
                )
            
            # Check individual file coverage
            files_data = coverage_data.get('files', {})
            for file_path, file_data in files_data.items():
                file_coverage = file_data.get('summary', {}).get('percent_covered', 0)
                
                if file_coverage < self.config['critical_coverage_threshold']:
                    issues.append(QualityIssue(
                        file_path=file_path.replace(str(self.project_root) + "/", ""),
                        line_number=None,
                        rule_id="file_low_coverage",
                        message=f"File coverage {file_coverage:.1f}% is below critical threshold "
                               f"{self.config['critical_coverage_threshold']}%",
                        severity=QualitySeverity.HIGH,
                        category="testing",
                        tool="pytest",
                        fix_suggestion="Add targeted tests for this file"
                    )
            
            critical_issues = [i for i in issues if i.severity == QualitySeverity.CRITICAL]
            
            if critical_issues:
                status = QualityGateStatus.FAILED
            elif issues:
                status = QualityGateStatus.WARNING
            else:
                status = QualityGateStatus.PASSED
            
            metrics = {
                'total_coverage': total_coverage,
                'coverage_threshold': self.config['coverage_threshold'],
                'files_under_threshold': len([i for i in issues if i.rule_id == 'file_low_coverage']),
                'total_files': len(files_data)
            }
            
            return status, issues, metrics
            
        except subprocess.TimeoutExpired:
            return QualityGateStatus.FAILED, [QualityIssue(
                file_path="system",
                line_number=None,
                rule_id="timeout",
                message="Test coverage analysis timed out",
                severity=QualitySeverity.CRITICAL,
                category="system",
                tool="pytest"
            )], {}
        except Exception as e:
            return QualityGateStatus.FAILED, [], {'error': str(e)}
    
    def _run_code_style_check(self) -> Tuple[QualityGateStatus, List[QualityIssue], Dict[str, Any]]:
        """Run code style checking with Black and isort."""
        issues = []
        
        try:
            # Check Black formatting
            cmd = ["black", "--check", str(self.project_root / "src")]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                for line in result.stderr.splitlines():
                    if "would reformat" in line:
                        file_path = line.split()[2] if len(line.split() > 2 else "unknown"
                        issues.append(QualityIssue(
                            file_path=file_path.replace(str(self.project_root) + "/", ""),
                            line_number=None,
                            rule_id="formatting",
                            message="File needs Black formatting",
                            severity=QualitySeverity.LOW,
                            category="style",
                            tool="black",
                            fix_suggestion="Run 'black .' to auto-format"
                        )
            
            # Check isort
            cmd = ["isort", "--check-only", str(self.project_root / "src")]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                for line in result.stdout.splitlines():
                    if "Skipped" not in line and self.project_root.name in line:
                        file_path = line.strip()
                        issues.append(QualityIssue(
                            file_path=file_path.replace(str(self.project_root) + "/", ""),
                            line_number=None,
                            rule_id="import_sorting",
                            message="Imports need sorting",
                            severity=QualitySeverity.LOW,
                            category="style",
                            tool="isort",
                            fix_suggestion="Run 'isort .' to auto-sort imports"
                        )
            
            # Style checks are usually non-blocking
            status = QualityGateStatus.WARNING if issues else QualityGateStatus.PASSED
            
            metrics = {
                'style_issues': len(issues),
                'formatting_issues': len([i for i in issues if i.rule_id == 'formatting']),
                'import_issues': len([i for i in issues if i.rule_id == 'import_sorting'])
            }
            
            return status, issues, metrics
            
        except Exception as e:
            return QualityGateStatus.WARNING, [], {'error': str(e)}
    
    def _run_documentation_check(self) -> Tuple[QualityGateStatus, List[QualityIssue], Dict[str, Any]]:
        """Check documentation completeness."""
        issues = []
        files_checked = 0
        undocumented_functions = 0
        
        try:
            for py_file in (self.project_root / "src").rglob("*.py"):
                if self._should_skip_file(py_file):
                    continue
                
                files_checked += 1
                content = py_file.read_text(encoding='utf-8')
                
                # Basic docstring checking
                import ast
                try:
                    tree = ast.parse(content)
                    
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef):
                            if (not ast.get_docstring(node) and 
                                not node.name.startswith('_') and 
                                node.name not in ['__init__']):
                                
                                undocumented_functions += 1
                                issues.append(QualityIssue(
                                    file_path=str(py_file.relative_to(self.project_root),
                                    line_number=node.lineno,
                                    rule_id="missing_docstring",
                                    message=f"{node.__class__.__name__} '{node.name}' lacks docstring",
                                    severity=QualitySeverity.LOW,
                                    category="documentation",
                                    tool="ast_parser",
                                    fix_suggestion="Add comprehensive docstring with Args, Returns, and Examples"
                                )
                
                except SyntaxError:
                    # Skip files with syntax errors
                    pass
        
        except Exception as e:
            return QualityGateStatus.WARNING, [], {'error': str(e)}
        
        # Documentation issues are typically warnings, not failures
        status = QualityGateStatus.WARNING if issues else QualityGateStatus.PASSED
        
        metrics = {
            'files_checked': files_checked,
            'undocumented_functions': undocumented_functions,
            'documentation_score': max(0, 100 - (undocumented_functions / max(1, files_checked) * 10)
        }
        
        return status, issues, metrics
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped based on exclusion patterns."""
        file_str = str(file_path)
        for excluded in self.config['excluded_paths']:
            if excluded in file_str:
                return True
        return False
    
    def _parse_security_issues(self, scan_data: Dict[str, Any]) -> List[QualityIssue]:
        """Parse security scan results into QualityIssue objects."""
        issues = []
        
        # This would be implemented based on the actual security scanner output format
        findings = scan_data.get('findings', [])
        
        for finding in findings:
            severity_map = {
                'critical': QualitySeverity.CRITICAL,
                'high': QualitySeverity.HIGH,
                'medium': QualitySeverity.MEDIUM,
                'low': QualitySeverity.LOW
            }
            
            issues.append(QualityIssue(
                file_path=finding.get('file_path', 'unknown'),
                line_number=finding.get('line_number'),
                rule_id=finding.get('rule_id', 'security_issue'),
                message=finding.get('message', 'Security issue detected'),
                severity=severity_map.get(finding.get('severity', 'medium'), QualitySeverity.MEDIUM),
                category="security",
                tool="security_scanner",
                fix_suggestion=finding.get('remediation')
            )
        
        return issues
    
    def _calculate_summary_metrics(self, gate_results: List[QualityGateResult]) -> Dict[str, Any]:
        """Calculate summary metrics from all gate results."""
        total_issues = sum(len(result.issues) for result in gate_results)
        critical_issues = sum(
            len([i for i in result.issues if i.severity == QualitySeverity.CRITICAL])
            for result in gate_results
        )
        
        passed_gates = len([r for r in gate_results if r.status == QualityGateStatus.PASSED])
        failed_gates = len([r for r in gate_results if r.status == QualityGateStatus.FAILED])
        
        total_duration = sum(result.duration_seconds for result in gate_results)
        
        return {
            'total_gates': len(gate_results),
            'passed_gates': passed_gates,
            'failed_gates': failed_gates,
            'total_issues': total_issues,
            'critical_issues': critical_issues,
            'total_duration_seconds': total_duration,
            'quality_score': max(0, 100 - (critical_issues * 10) - (total_issues * 2)
        }
    
    def _generate_recommendations(self, gate_results: List[QualityGateResult]) -> List[str]:
        """Generate actionable recommendations based on results."""
        recommendations = []
        
        for result in gate_results:
            if result.status == QualityGateStatus.FAILED:
                if result.gate_name == 'security_scan':
                    recommendations.append(
                        "🔒 Critical: Fix all security vulnerabilities before deployment. "
                        "Use environment variables for secrets and implement proper access controls."
                    )
                elif result.gate_name == 'complexity_check':
                    recommendations.append(
                        "🔄 Refactor high-complexity functions using Strategy Pattern or decomposition. "
                        "Target functions with complexity > 10 for immediate refactoring."
                    )
                elif result.gate_name == 'test_coverage':
                    recommendations.append(
                        "🧪 Increase test coverage by adding unit tests for uncovered code paths. "
                        "Focus on critical business logic and error handling scenarios."
                    )
        
        # Add general recommendations
        critical_count = sum(
            len([i for i in result.issues if i.severity == QualitySeverity.CRITICAL])
            for result in gate_results
        )
        
        if critical_count > 0:
            recommendations.append(
                f"⚠️ Address {critical_count} critical issues immediately. "
                "These issues block production deployment."
            )
        
        if not recommendations:
            recommendations.append("✅ All quality gates passed! Maintain these high standards.")
        
        return recommendations
    
    def _analyze_trends(self) -> Dict[str, Any]:
        """Analyze quality trends over time."""
        # This would implement trend analysis by comparing with historical reports
        return {
            'trend_analysis': 'Historical trend analysis requires multiple report runs',
            'improvement_areas': ['Implement trend tracking', 'Set up historical data storage']
        }
    
    def _save_report(self, report: QualityReport) -> None:
        """Save comprehensive report to files."""
        timestamp = report.report_timestamp.strftime("%Y%m%d_%H%M%S")
        
        # Save JSON report
        json_file = self.report_dir / f"quality_report_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(asdict(report), f, indent=2, default=str)
        
        # Save human-readable report
        text_file = self.report_dir / f"quality_report_{timestamp}.txt"
        with open(text_file, 'w') as f:
            f.write(self._format_text_report(report)
        
        # Save latest report (symlink)
        latest_json = self.report_dir / "quality_report_latest.json"
        latest_text = self.report_dir / "quality_report_latest.txt"
        
        if latest_json.exists():
            latest_json.unlink()
        if latest_text.exists():
            latest_text.unlink()
        
        latest_json.symlink_to(json_file.name)
        latest_text.symlink_to(text_file.name)
        
logger.info(f"\n📊 Quality report saved to {json_file}")
    
    def _format_text_report(self, report: QualityReport) -> str:
        """Format report as human-readable text."""
        lines = []
        lines.append("=" * 80)
        lines.append("DotMac ISP Framework - Quality Assurance Report")
        lines.append("=" * 80)
        lines.append(f"Generated: {report.report_timestamp}")
        lines.append(f"Project: {report.project_root}")
        lines.append(f"Overall Status: {report.overall_status.value.upper()}")
        lines.append("")
        
        # Summary metrics
        metrics = report.summary_metrics
        lines.append("SUMMARY METRICS:")
        lines.append("-" * 40)
        lines.append(f"Quality Score: {metrics.get('quality_score', 0):.1f}/100")
        lines.append(f"Gates Passed: {metrics.get('passed_gates', 0)}/{metrics.get('total_gates', 0)}")
        lines.append(f"Critical Issues: {metrics.get('critical_issues', 0)}")
        lines.append(f"Total Issues: {metrics.get('total_issues', 0)}")
        lines.append(f"Total Duration: {metrics.get('total_duration_seconds', 0):.1f}s")
        lines.append("")
        
        # Gate results
        lines.append("QUALITY GATE RESULTS:")
        lines.append("-" * 40)
        for result in report.gate_results:
            status_icon = {
                QualityGateStatus.PASSED: "✅",
                QualityGateStatus.FAILED: "❌",
                QualityGateStatus.WARNING: "⚠️",
                QualityGateStatus.SKIPPED: "⏭️"
            }[result.status]
            
            lines.append(f"{status_icon} {result.gate_name}: {result.status.value.upper()} "
                        f"({result.duration_seconds:.1f}s)")
            
            if result.issues:
                critical = len([i for i in result.issues if i.severity == QualitySeverity.CRITICAL])
                high = len([i for i in result.issues if i.severity == QualitySeverity.HIGH])
                
                if critical:
                    lines.append(f"   🔴 {critical} critical issues")
                if high:
                    lines.append(f"   🟡 {high} high priority issues")
        
        lines.append("")
        
        # Recommendations
        lines.append("RECOMMENDATIONS:")
        lines.append("-" * 40)
        for i, rec in enumerate(report.recommendations, 1):
            lines.append(f"{i}. {rec}")
        
        lines.append("")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def _display_summary(self, report: QualityReport) -> None:
        """Display summary of quality assessment."""
logger.info("\n" + "=" * 60)
logger.info("QUALITY ASSURANCE SUMMARY")
logger.info("=" * 60)
        
        # Overall status
        status_icons = {
            QualityGateStatus.PASSED: "✅",
            QualityGateStatus.FAILED: "❌",
            QualityGateStatus.WARNING: "⚠️"
        }
        
logger.info(f"Overall Status: {status_icons[report.overall_status]} {report.overall_status.value.upper()}")
        
        # Metrics
        metrics = report.summary_metrics
logger.info(f"Quality Score: {metrics.get('quality_score', 0):.1f}/100")
logger.info(f"Gates Passed: {metrics.get('passed_gates', 0)}/{metrics.get('total_gates', 0)}")
        
        if metrics.get('critical_issues', 0) > 0:
logger.info(f"🔴 Critical Issues: {metrics['critical_issues']} (MUST FIX)")
        
        if metrics.get('total_issues', 0) > 0:
logger.info(f"📋 Total Issues: {metrics['total_issues']}")
        
logger.info(f"⏱️  Total Duration: {metrics.get('total_duration_seconds', 0):.1f}s")
        
        # Top recommendations
logger.info("\nTOP RECOMMENDATIONS:")
        for i, rec in enumerate(report.recommendations[:3], 1):
logger.info(f"{i}. {rec}")
        
logger.info("=" * 60)


def main():
    """Main entry point for quality assurance automation."""
    parser = argparse.ArgumentParser(description="DotMac ISP Framework Quality Assurance Automation")
    parser.add_argument(
        "--project-root", 
        type=Path, 
        default=Path.cwd(),
        help="Root directory of the project (default: current directory)"
    )
    parser.add_argument(
        "--config", 
        type=Path,
        help="Configuration file path"
    )
    parser.add_argument(
        "--fail-fast", 
        action="store_true",
        help="Stop on first critical failure"
    )
    parser.add_argument(
        "--gates",
        nargs="+",
        help="Specific gates to run (default: all enabled gates)"
    )
    parser.add_argument(
        "--output-format",
        choices=["text", "json", "both"],
        default="both",
        help="Output format for results"
    )
    
    args = parser.parse_args()
    
    # Initialize QA automation
    qa_system = QualityAssuranceAutomation(
        project_root=args.project_root,
        config_file=args.config
    )
    
    # Run quality gates
    try:
        report = qa_system.run_all_quality_gates(fail_fast=args.fail_fast)
        
        # Exit with appropriate code
        if report.overall_status == QualityGateStatus.FAILED:
logger.info("\n❌ QUALITY ASSURANCE FAILED")
logger.info("Code does not meet quality standards and cannot be deployed.")
            sys.exit(1)
        elif report.overall_status == QualityGateStatus.WARNING:
logger.warning("\n⚠️  QUALITY ASSURANCE PASSED WITH WARNINGS")
logger.warning("Consider addressing warnings before deployment.")
            sys.exit(0)
        else:
logger.info("\n✅ QUALITY ASSURANCE PASSED")
logger.info("Code meets all quality standards.")
            sys.exit(0)
            
    except KeyboardInterrupt:
logger.info("\n⏹️  Quality assurance interrupted by user")
        sys.exit(130)
    except Exception as e:
logger.error(f"\n💥 Quality assurance system error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()