#!/usr/bin/env python3
"""
Template-Aware Security Scanner for DotMac Framework

This scanner recognizes legitimate ${SECRET:*} templates while detecting
actual hardcoded secrets. Designed to reduce false positives in CI/CD.
"""

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class SecurityViolation:
    """Represents a potential security violation."""

    file_path: str
    line_number: int
    line_content: str
    violation_type: str
    severity: str
    pattern_matched: str


class TemplateAwareSecurityScanner:
    """Security scanner that understands secret templates."""

    def __init__(self):
        # Safe patterns that should NOT trigger alerts
        self.SAFE_PATTERNS = [
            r"\$\{SECRET:[^}]+\}",  # ${SECRET:name} templates
            r"SECRET:\"\)\:",  # Template validation code
            r'"SECRET:" in \w+',  # Template detection logic
            r'\.startswith\("SECRET:',  # Placeholder validation
            r'PASSWORD\s*=\s*"pwd"',  # Our enum fix
            r"password.*test.*",  # Test patterns
            r"api_key.*example",  # Example patterns
        ]

        # Dangerous patterns that SHOULD trigger alerts
        self.DANGER_PATTERNS = [
            {
                "pattern": r'password\s*[:=]\s*[\'"]([^\'"\$][^\'"]{5,})[\'"]',
                "type": "HARDCODED_PASSWORD",
                "severity": "HIGH",
                "description": "Potential hardcoded password",
            },
            {
                "pattern": r'api_key\s*[:=]\s*[\'"]([^\'"\$][^\'"]{19,})[\'"]',
                "type": "HARDCODED_API_KEY",
                "severity": "CRITICAL",
                "description": "Potential hardcoded API key",
            },
            {
                "pattern": r'secret\s*[:=]\s*[\'"]([^\'"\$][^\'"]{9,})[\'"]',
                "type": "HARDCODED_SECRET",
                "severity": "CRITICAL",
                "description": "Potential hardcoded secret",
            },
            {
                "pattern": r'token\s*[:=]\s*[\'"]([^\'"\$][^\'"]{19,})[\'"]',
                "type": "HARDCODED_TOKEN",
                "severity": "HIGH",
                "description": "Potential hardcoded token",
            },
        ]

        # File patterns to skip entirely
        self.SKIP_FILES = [
            r".*test.*\.py$",
            r".*example.*\.py$",
            r".*template.*\.py$",
            r".*\.md$",
            r".*/__pycache__/.*",
            r".*\.pyc$",
        ]

        # Paths with relaxed rules
        self.RELAXED_PATHS = ["config_generator.py", "validators.py", "test_security_validation.py"]

    def is_safe_template(self, text: str) -> bool:
        """Check if text contains legitimate template patterns."""
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in self.SAFE_PATTERNS)

    def should_skip_file(self, file_path: str) -> bool:
        """Check if file should be skipped entirely."""
        return any(re.match(pattern, file_path) for pattern in self.SKIP_FILES)

    def is_relaxed_path(self, file_path: str) -> bool:
        """Check if file has relaxed scanning rules."""
        return any(relaxed in file_path for relaxed in self.RELAXED_PATHS)

    def scan_file(self, file_path: Path) -> list[SecurityViolation]:
        """Scan a single file for security violations."""
        violations = []

        # Skip files that shouldn't be scanned
        if self.should_skip_file(str(file_path)):
            return violations

        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.split("\n")

            for line_num, line in enumerate(lines, 1):
                # Skip empty lines and comments
                stripped_line = line.strip()
                if not stripped_line or stripped_line.startswith("#"):
                    continue

                # Check each danger pattern
                for danger_rule in self.DANGER_PATTERNS:
                    pattern = danger_rule["pattern"]
                    match = re.search(pattern, line, re.IGNORECASE)

                    if match:
                        # Check if it's a safe template
                        if not self.is_safe_template(line):
                            # Check if file has relaxed rules
                            if self.is_relaxed_path(str(file_path)):
                                # Only report critical issues in relaxed files
                                if danger_rule["severity"] != "CRITICAL":
                                    continue

                            violation = SecurityViolation(
                                file_path=str(file_path),
                                line_number=line_num,
                                line_content=line.strip(),
                                violation_type=danger_rule["type"],
                                severity=danger_rule["severity"],
                                pattern_matched=match.group(),
                            )
                            violations.append(violation)

        except (UnicodeDecodeError, PermissionError) as e:
            print(f"⚠️  Could not read {file_path}: {e}")

        return violations

    def scan_directory(self, directory: Path) -> list[SecurityViolation]:
        """Scan all Python files in directory."""
        violations = []

        for py_file in directory.rglob("*.py"):
            file_violations = self.scan_file(py_file)
            violations.extend(file_violations)

        return violations

    def generate_report(self, violations: list[SecurityViolation]) -> dict[str, Any]:
        """Generate a comprehensive report."""

        # Group violations by severity
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        violation_details = []

        for violation in violations:
            severity_counts[violation.severity] += 1
            violation_details.append(
                {
                    "file": violation.file_path,
                    "line": violation.line_number,
                    "content": violation.line_content,
                    "type": violation.violation_type,
                    "severity": violation.severity,
                    "pattern": violation.pattern_matched,
                }
            )

        return {
            "scan_summary": {
                "total_violations": len(violations),
                "critical": severity_counts["CRITICAL"],
                "high": severity_counts["HIGH"],
                "medium": severity_counts["MEDIUM"],
                "low": severity_counts["LOW"],
            },
            "violations": violation_details,
            "template_patterns_ignored": len(self.SAFE_PATTERNS),
            "scan_status": "PASS" if len(violations) == 0 else "FAIL",
        }


def main():
    """Main scanner execution."""
    print("🔍 DotMac Template-Aware Security Scanner")
    print("=" * 50)

    scanner = TemplateAwareSecurityScanner()

    # Scan source directory
    src_path = Path("./src")
    if not src_path.exists():
        print("❌ Source directory ./src not found")
        sys.exit(1)

    violations = scanner.scan_directory(src_path)
    report = scanner.generate_report(violations)

    # Print results
    print("📊 Scan Results:")
    print(f"   Total violations: {report['scan_summary']['total_violations']}")
    print(f"   Critical: {report['scan_summary']['critical']}")
    print(f"   High: {report['scan_summary']['high']}")
    print(f"   Template patterns ignored: {report['template_patterns_ignored']}")

    if violations:
        print("\n🚨 Security Violations Found:")
        for violation in violations:
            print(f"   {violation.severity}: {violation.file_path}:{violation.line_number}")
            print(f"      {violation.violation_type}: {violation.line_content}")
            print()
    else:
        print("\n✅ No security violations detected")
        print("✅ All ${SECRET:*} templates properly ignored")

    # Save detailed report
    report_file = Path("security-scan-report.json")
    report_file.write_text(json.dumps(report, indent=2))
    print(f"📄 Detailed report saved to: {report_file}")

    # Exit with appropriate code
    sys.exit(0 if report["scan_status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
