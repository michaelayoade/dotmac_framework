#!/usr/bin/env python3
"""
Custom security validation script for the DotMac Management Platform.

This script performs additional security checks beyond standard tools,
including configuration validation, secret detection, and custom security rules.
"""

import os
import re
import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Set
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class SecurityFinding:
    """Represents a security finding."""
    severity: str  # critical, high, medium, low, info
    category: str
    title: str
    description: str
    file_path: str
    line_number: int = 0
    recommendation: str = ""
    cwe_id: str = ""


class SecurityChecker:
    """Custom security checker for DotMac platform."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.findings: List[SecurityFinding] = []
        self.logger = logging.getLogger(__name__)
        
        # Security patterns to detect
        self.secret_patterns = {
            'aws_access_key': r'AKIA[0-9A-Z]{16}',
            'aws_secret_key': r'[0-9a-zA-Z/+]{40}',
            'jwt_secret': r'jwt[_-]?secret[_-]?key.*?[\'"][0-9a-zA-Z/+]{32,}[\'"]',
            'password_hash': r'password.*?[\'"][0-9a-zA-Z/+$]{60,}[\'"]',
            'api_key': r'api[_-]?key.*?[\'"][0-9a-zA-Z]{32,}[\'"]',
            'private_key': r'-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----',
            'stripe_key': r'sk_live_[0-9a-zA-Z]{24}',
            'sendgrid_key': r'SG\.[0-9a-zA-Z_-]{22}\.[0-9a-zA-Z_-]{43}',
        }
        
        # Insecure patterns
        self.insecure_patterns = {
            'hardcoded_secret': r'(secret|password|key|token)\s*=\s*[\'"][^\'"\s]{8,}[\'"]',
            'sql_injection': r'(execute|query|cursor).*?%s|f[\'"].*?{.*?}.*?[\'"]',
            'command_injection': r'(os\.system|subprocess\.call|shell=True)',
            'weak_crypto': r'(md5|sha1|des|rc4)[\(\.]',
            'debug_enabled': r'debug\s*=\s*True',
            'insecure_random': r'random\.random\(\)|random\.choice\(',
        }
        
        # File extensions to scan
        self.scan_extensions = {'.py', '.yml', '.yaml', '.json', '.env', '.tf', '.dockerfile'}
        
        # Files to exclude
        self.exclude_patterns = {
            'test_', '__pycache__', '.git', 'node_modules', '.venv', 
            'dist', 'build', '.pytest_cache', '.mypy_cache'
        }
    
    def should_scan_file(self, file_path: Path) -> bool:
        """Determine if a file should be scanned."""
        # Check extension
        if file_path.suffix not in self.scan_extensions:
            return False
        
        # Check exclusions
        for exclude in self.exclude_patterns:
            if exclude in str(file_path):
                return False
        
        return True
    
    def scan_file_for_secrets(self, file_path: Path) -> None:
        """Scan a file for hardcoded secrets."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
                
                for pattern_name, pattern in self.secret_patterns.items():
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        # Find line number
                        line_num = content[:match.start()].count('\n') + 1
                        
                        self.findings.append(SecurityFinding(
                            severity="critical",
                            category="secrets",
                            title=f"Potential {pattern_name.replace('_', ' ').title()} Found",
                            description=f"Detected potential {pattern_name} in source code",
                            file_path=str(file_path.relative_to(self.project_root)),
                            line_number=line_num,
                            recommendation="Move secrets to environment variables or secure vault",
                            cwe_id="CWE-798"
                        ))
        except Exception as e:
            self.logger.warning(f"Error scanning {file_path}: {e}")
    
    def scan_file_for_insecure_patterns(self, file_path: Path) -> None:
        """Scan a file for insecure coding patterns."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                for pattern_name, pattern in self.insecure_patterns.items():
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        
                        severity = "high" if pattern_name in ['sql_injection', 'command_injection'] else "medium"
                        
                        self.findings.append(SecurityFinding(
                            severity=severity,
                            category="code_security",
                            title=f"Insecure Pattern: {pattern_name.replace('_', ' ').title()}",
                            description=f"Detected {pattern_name} pattern in code",
                            file_path=str(file_path.relative_to(self.project_root)),
                            line_number=line_num,
                            recommendation=self._get_pattern_recommendation(pattern_name),
                            cwe_id=self._get_pattern_cwe(pattern_name)
                        ))
        except Exception as e:
            self.logger.warning(f"Error scanning {file_path}: {e}")
    
    def _get_pattern_recommendation(self, pattern_name: str) -> str:
        """Get recommendation for a specific pattern."""
        recommendations = {
            'hardcoded_secret': "Use environment variables or secure configuration management",
            'sql_injection': "Use parameterized queries and ORM",
            'command_injection': "Validate input and avoid shell=True",
            'weak_crypto': "Use strong cryptographic algorithms (SHA-256, AES)",
            'debug_enabled': "Disable debug mode in production",
            'insecure_random': "Use secrets module for cryptographic randomness",
        }
        return recommendations.get(pattern_name, "Review and fix security issue")
    
    def _get_pattern_cwe(self, pattern_name: str) -> str:
        """Get CWE ID for a specific pattern."""
        cwe_mapping = {
            'hardcoded_secret': "CWE-798",
            'sql_injection': "CWE-89",
            'command_injection': "CWE-78",
            'weak_crypto': "CWE-327",
            'debug_enabled': "CWE-489",
            'insecure_random': "CWE-338",
        }
        return cwe_mapping.get(pattern_name, "")
    
    def check_configuration_security(self) -> None:
        """Check configuration files for security issues."""
        config_files = [
            'docker-compose.yml',
            '.env.example',
            'pyproject.toml',
        ]
        
        for config_file in config_files:
            config_path = self.project_root / config_file
            if config_path.exists():
                self._check_config_file(config_path)
    
    def _check_config_file(self, config_path: Path) -> None:
        """Check individual configuration file."""
        try:
            with open(config_path, 'r') as f:
                content = f.read()
                
                # Check for insecure configurations
                insecure_configs = [
                    ('debug.*true', "Debug mode enabled"),
                    ('ssl.*false', "SSL disabled"),
                    ('password.*=.*admin|password|123', "Weak default password"),
                    ('secret.*=.*secret|default|example', "Default secret key"),
                ]
                
                for pattern, description in insecure_configs:
                    if re.search(pattern, content, re.IGNORECASE):
                        line_num = 1  # Simplified line detection
                        
                        self.findings.append(SecurityFinding(
                            severity="medium",
                            category="configuration",
                            title="Insecure Configuration",
                            description=description,
                            file_path=str(config_path.relative_to(self.project_root)),
                            line_number=line_num,
                            recommendation="Review and secure configuration settings"
                        ))
        except Exception as e:
            self.logger.warning(f"Error checking config {config_path}: {e}")
    
    def check_dependency_versions(self) -> None:
        """Check for outdated or vulnerable dependencies."""
        pyproject_path = self.project_root / 'pyproject.toml'
        if not pyproject_path.exists():
            return
        
        try:
            with open(pyproject_path, 'r') as f:
                content = f.read()
                
                # Check for potentially vulnerable versions
                vulnerable_patterns = [
                    (r'django\s*=\s*[\'"]1\.', "Django 1.x is end-of-life"),
                    (r'flask\s*=\s*[\'"]0\.', "Flask 0.x has known vulnerabilities"),
                    (r'requests\s*=\s*[\'"]2\.2[0-5]', "Requests < 2.26 has vulnerabilities"),
                ]
                
                for pattern, description in vulnerable_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        self.findings.append(SecurityFinding(
                            severity="high",
                            category="dependencies",
                            title="Potentially Vulnerable Dependency",
                            description=description,
                            file_path="pyproject.toml",
                            recommendation="Update to latest secure version"
                        ))
        except Exception as e:
            self.logger.warning(f"Error checking dependencies: {e}")
    
    def check_docker_security(self) -> None:
        """Check Docker configurations for security issues."""
        dockerfile_paths = list(self.project_root.glob('**/Dockerfile*'))
        
        for dockerfile in dockerfile_paths:
            self._check_dockerfile(dockerfile)
    
    def _check_dockerfile(self, dockerfile_path: Path) -> None:
        """Check individual Dockerfile for security issues."""
        try:
            with open(dockerfile_path, 'r') as f:
                lines = f.readlines()
                
                for i, line in enumerate(lines, 1):
                    line = line.strip().lower()
                    
                    # Check for security issues
                    if line.startswith('user root') or 'user 0' in line:
                        self.findings.append(SecurityFinding(
                            severity="high",
                            category="docker",
                            title="Running as Root User",
                            description="Container runs as root user",
                            file_path=str(dockerfile_path.relative_to(self.project_root)),
                            line_number=i,
                            recommendation="Use non-root user for container execution",
                            cwe_id="CWE-250"
                        ))
                    
                    if '--allow-unauthenticated' in line or '--no-check-certificate' in line:
                        self.findings.append(SecurityFinding(
                            severity="medium",
                            category="docker",
                            title="Insecure Package Installation",
                            description="Package installation without authentication",
                            file_path=str(dockerfile_path.relative_to(self.project_root)),
                            line_number=i,
                            recommendation="Remove insecure flags from package installation"
                        ))
        except Exception as e:
            self.logger.warning(f"Error checking Dockerfile {dockerfile_path}: {e}")
    
    def run_full_scan(self) -> List[SecurityFinding]:
        """Run complete security scan."""
        self.logger.info("Starting security scan...")
        
        # Scan all files
        for file_path in self.project_root.rglob('*'):
            if file_path.is_file() and self.should_scan_file(file_path):
                self.scan_file_for_secrets(file_path)
                if file_path.suffix == '.py':
                    self.scan_file_for_insecure_patterns(file_path)
        
        # Check configurations
        self.check_configuration_security()
        self.check_dependency_versions()
        self.check_docker_security()
        
        self.logger.info(f"Security scan complete. Found {len(self.findings)} issues.")
        return self.findings
    
    def generate_report(self, output_format: str = 'json') -> str:
        """Generate security report in specified format."""
        if output_format == 'json':
            return json.dumps([asdict(finding) for finding in self.findings], indent=2)
        elif output_format == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['Severity', 'Category', 'Title', 'File', 'Line', 'Description', 'Recommendation'])
            
            for finding in self.findings:
                writer.writerow([
                    finding.severity, finding.category, finding.title,
                    finding.file_path, finding.line_number,
                    finding.description, finding.recommendation
                ])
            
            return output.getvalue()
        else:
            # Human-readable format
            report = f"Security Scan Report - {datetime.now().isoformat()}\n"
            report += "=" * 60 + "\n\n"
            
            # Group by severity
            by_severity = {}
            for finding in self.findings:
                if finding.severity not in by_severity:
                    by_severity[finding.severity] = []
                by_severity[finding.severity].append(finding)
            
            for severity in ['critical', 'high', 'medium', 'low', 'info']:
                if severity in by_severity:
                    report += f"{severity.upper()} SEVERITY ISSUES ({len(by_severity[severity])})\n"
                    report += "-" * 40 + "\n"
                    
                    for finding in by_severity[severity]:
                        report += f"  {finding.title}\n"
                        report += f"  File: {finding.file_path}:{finding.line_number}\n"
                        report += f"  {finding.description}\n"
                        if finding.recommendation:
                            report += f"  Recommendation: {finding.recommendation}\n"
                        report += "\n"
            
            return report


def main():
    """Main entry point."""
    logging.basicConfig(level=logging.INFO)
    
    project_root = Path(__file__).parent.parent
    checker = SecurityChecker(project_root)
    
    # Run scan
    findings = checker.run_full_scan()
    
    # Generate reports
    json_report = checker.generate_report('json')
    with open('security-findings.json', 'w') as f:
        f.write(json_report)
    
    text_report = checker.generate_report('text')
    with open('security-report.txt', 'w') as f:
        f.write(text_report)
    
    print(f"Security scan complete. Found {len(findings)} issues.")
    print("Reports generated:")
    print("  - security-findings.json")
    print("  - security-report.txt")
    
    # Exit with error code if critical or high severity issues found
    critical_high = [f for f in findings if f.severity in ['critical', 'high']]
    if critical_high:
        print(f"\nERROR: Found {len(critical_high)} critical/high severity issues!")
        sys.exit(1)
    else:
        print("\nNo critical or high severity issues found.")
        sys.exit(0)


if __name__ == '__main__':
    main()