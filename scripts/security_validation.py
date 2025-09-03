#!/usr/bin/env python3
"""
Production Security Validation Script for DotMac Framework.

Validates that all critical security measures are properly configured
before production deployment.

Usage:
    python scripts/security_validation.py
    
Exit codes:
    0 - All security validations passed
    1 - Critical security issues found
    2 - Warnings found (non-critical)
"""

import os
import re
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class SecurityValidator:
    """Security validation for production deployment."""
    
    def __init__(self):
        self.critical_failures = []
        self.warnings = []
        self.successes = []
        
    def add_success(self, check: str, message: str = ""):
        """Add a successful security check."""
        self.successes.append((check, message))
        logger.info(f"✅ {check}: {message}")
        
    def add_warning(self, check: str, message: str):
        """Add a security warning."""
        self.warnings.append((check, message))
        logger.warning(f"⚠️  {check}: {message}")
        
    def add_critical(self, check: str, message: str):
        """Add a critical security failure."""
        self.critical_failures.append((check, message))
        logger.error(f"❌ {check}: {message}")

    def validate_environment_security(self) -> bool:
        """Validate security-related environment variables."""
        logger.info("Validating environment security configuration...")
        
        # Required security variables
        security_vars = [
            ("SECRET_KEY", 64),
            ("JWT_SECRET", 64), 
            ("ENCRYPTION_KEY", 32),
            ("OPENBAO_URL", None),
            ("OPENBAO_TOKEN", 20),
        ]
        
        all_good = True
        
        for var_name, min_length in security_vars:
            value = os.getenv(var_name)
            
            if not value:
                self.add_critical("Environment Security", f"{var_name} is not set")
                all_good = False
            elif min_length and len(value) < min_length:
                self.add_critical("Environment Security", f"{var_name} must be at least {min_length} characters")
                all_good = False
            else:
                self.add_success("Environment Security", f"{var_name} properly configured")
        
        # Check for development/test values
        dangerous_values = [
            "test", "example", "changeme", "password", "secret", "admin", "demo",
            "INSECURE", "CHANGE_ME", "development", "localhost"
        ]
        
        for var_name, _ in security_vars:
            value = os.getenv(var_name, "")
            for dangerous in dangerous_values:
                if dangerous.lower() in value.lower():
                    self.add_critical("Environment Security", f"{var_name} contains unsafe value: {dangerous}")
                    all_good = False
                    break
        
        return all_good

    def scan_for_hardcoded_secrets(self) -> bool:
        """Scan codebase for hardcoded secrets."""
        logger.info("Scanning for hardcoded secrets...")
        
        # Patterns to detect secrets
        secret_patterns = [
            (r'(?i)(password|secret|key|token)\s*[:=]\s*["\'][^"\']{8,}["\']', "Potential hardcoded credential"),
            (r'(?i)jwt_secret\s*[:=]\s*["\'][^"\']+["\']', "Hardcoded JWT secret"),
            (r'(?i)api_key\s*[:=]\s*["\'][^"\']+["\']', "Hardcoded API key"),
            (r'(?i)password\s*[:=]\s*["\'][^"\']+["\']', "Hardcoded password"),
        ]
        
        # Exclude patterns (legitimate uses)
        exclude_patterns = [
            r'test', r'example', r'CHANGE_ME', r'INSECURE.*EXAMPLE',
            r'\.git', r'__pycache__', r'\.pyc', r'NEVER.*PRODUCTION'
        ]
        
        issues_found = []
        
        # Scan Python files
        for py_file in Path(".").rglob("*.py"):
            if any(re.search(pattern, str(py_file), re.IGNORECASE) for pattern in exclude_patterns):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for pattern, description in secret_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
                    for match in matches:
                        # Skip if it's in a comment or test
                        line = match.group(0)
                        if any(exclude in line for exclude in ['#', 'test', 'Test', 'TEST', 'example', 'EXAMPLE']):
                            continue
                            
                        issues_found.append((str(py_file), description, line.strip()))
            except (UnicodeDecodeError, PermissionError):
                continue
        
        # Scan configuration files
        for config_file in Path(".").rglob("*.yml"):
            if any(re.search(pattern, str(config_file), re.IGNORECASE) for pattern in exclude_patterns):
                continue
                
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Look for hardcoded values in production configs
                if 'production' in content.lower():
                    for pattern, description in secret_patterns:
                        matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
                        for match in matches:
                            line = match.group(0)
                            if not any(exclude in line for exclude in ['${', 'CHANGE_ME']):
                                issues_found.append((str(config_file), "Production config with hardcoded value", line.strip()))
            except (UnicodeDecodeError, PermissionError):
                continue
        
        if issues_found:
            for file_path, description, line in issues_found:
                self.add_critical("Hardcoded Secrets", f"{description} in {file_path}: {line[:50]}...")
            return False
        else:
            self.add_success("Hardcoded Secrets", "No hardcoded secrets found in production code")
            return True

    def validate_unsafe_functions(self) -> bool:
        """Check for usage of unsafe functions."""
        logger.info("Checking for unsafe function usage...")
        
        unsafe_patterns = [
            (r'\beval\s*\(', "Use of eval() function"),
            (r'\bexec\s*\(', "Use of exec() function"), 
            (r'subprocess\.call\s*\([^)]*shell\s*=\s*True', "Subprocess with shell=True"),
            (r'os\.system\s*\(', "Use of os.system()"),
        ]
        
        issues_found = []
        
        for py_file in Path(".").rglob("*.py"):
            # Skip test files and examples
            if any(skip in str(py_file) for skip in ['test', 'example', '.git', '__pycache__']):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for pattern, description in unsafe_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
                    for match in matches:
                        # Get the line for context
                        lines = content[:match.start()].count('\n') + 1
                        issues_found.append((str(py_file), lines, description))
            except (UnicodeDecodeError, PermissionError):
                continue
        
        if issues_found:
            for file_path, line_num, description in issues_found:
                self.add_warning("Unsafe Functions", f"{description} in {file_path}:{line_num}")
            return True  # Warnings, not critical
        else:
            self.add_success("Unsafe Functions", "No unsafe function usage detected")
            return True

    def validate_production_configs(self) -> bool:
        """Validate production configuration security."""
        logger.info("Validating production configuration security...")
        
        all_good = True
        
        # Check that production environment is properly set
        environment = os.getenv("ENVIRONMENT")
        if environment != "production":
            self.add_warning("Production Config", f"ENVIRONMENT should be 'production', got '{environment}'")
        else:
            self.add_success("Production Config", "ENVIRONMENT properly set to 'production'")
        
        # Check strict baseline
        strict_baseline = os.getenv("STRICT_PROD_BASELINE", "").lower()
        if strict_baseline != "true":
            self.add_critical("Production Config", "STRICT_PROD_BASELINE must be 'true' for production")
            all_good = False
        else:
            self.add_success("Production Config", "STRICT_PROD_BASELINE properly enabled")
        
        # Check database URL is not SQLite
        db_url = os.getenv("DATABASE_URL", "")
        if db_url.startswith("sqlite"):
            self.add_critical("Production Config", "SQLite database not allowed in production")
            all_good = False
        elif db_url:
            self.add_success("Production Config", "Non-SQLite database configured")
        
        # Check RLS is enabled
        rls_enabled = os.getenv("APPLY_RLS_AFTER_MIGRATION", "").lower()
        if rls_enabled != "true":
            self.add_critical("Production Config", "APPLY_RLS_AFTER_MIGRATION must be 'true' for production")
            all_good = False
        else:
            self.add_success("Production Config", "Row-Level Security properly enabled")
        
        return all_good

    def validate_tls_configuration(self) -> bool:
        """Validate TLS/SSL configuration."""
        logger.info("Validating TLS configuration...")
        
        # Check CORS origins don't include insecure protocols
        cors_origins = os.getenv("CORS_ORIGINS", "")
        if "http://" in cors_origins and "localhost" not in cors_origins:
            self.add_critical("TLS Configuration", "CORS_ORIGINS contains insecure HTTP URLs")
            return False
        
        # Check for HTTPS enforcement
        if cors_origins and "https://" not in cors_origins:
            self.add_warning("TLS Configuration", "CORS_ORIGINS should use HTTPS for production")
        
        self.add_success("TLS Configuration", "TLS settings validated")
        return True

    def generate_security_report(self) -> Dict[str, Any]:
        """Generate comprehensive security validation report."""
        return {
            "overall_status": "SECURE" if not self.critical_failures else "INSECURE",
            "critical_failures": len(self.critical_failures),
            "warnings": len(self.warnings), 
            "successes": len(self.successes),
            "details": {
                "critical": [{"check": check, "message": msg} for check, msg in self.critical_failures],
                "warnings": [{"check": check, "message": msg} for check, msg in self.warnings],
                "successes": [{"check": check, "message": msg} for check, msg in self.successes],
            },
            "recommendations": self._generate_recommendations()
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate security recommendations based on findings."""
        recommendations = []
        
        if self.critical_failures:
            recommendations.append("❗ Fix all critical security issues before production deployment")
        
        if any("hardcoded" in msg.lower() for _, msg in self.critical_failures):
            recommendations.append("🔐 Implement proper secrets management with OpenBao/Vault")
        
        if any("eval" in msg.lower() or "exec" in msg.lower() for _, msg in self.warnings):
            recommendations.append("⚠️ Replace unsafe function usage with secure alternatives")
        
        if not self.critical_failures and not self.warnings:
            recommendations.append("✅ Security validation passed - ready for production")
        
        return recommendations

    def run_all_validations(self) -> bool:
        """Run all security validations."""
        logger.info("Starting comprehensive security validation...")
        
        validations = [
            ("Environment Security", self.validate_environment_security),
            ("Hardcoded Secrets", self.scan_for_hardcoded_secrets), 
            ("Unsafe Functions", self.validate_unsafe_functions),
            ("Production Config", self.validate_production_configs),
            ("TLS Configuration", self.validate_tls_configuration),
        ]
        
        all_passed = True
        
        for validation_name, validation_func in validations:
            try:
                result = validation_func()
                if not result:
                    all_passed = False
            except Exception as e:
                self.add_critical("Validation Error", f"{validation_name} failed: {e}")
                all_passed = False
        
        return all_passed and len(self.critical_failures) == 0


def main():
    """Main entry point for security validation."""
    validator = SecurityValidator()
    
    try:
        success = validator.run_all_validations()
        
        # Generate and display report
        report = validator.generate_security_report()
        
        print("\n" + "="*60)
        print("SECURITY VALIDATION REPORT") 
        print("="*60)
        print(f"Overall Status: {report['overall_status']}")
        print(f"Successes: {report['successes']}")
        print(f"Warnings: {report['warnings']}")
        print(f"Critical Failures: {report['critical_failures']}")
        
        if report['details']['critical']:
            print("\n🚨 CRITICAL SECURITY ISSUES (must fix):")
            for item in report['details']['critical']:
                print(f"  ❌ {item['check']}: {item['message']}")
        
        if report['details']['warnings']:
            print("\n⚠️  SECURITY WARNINGS (recommended to fix):")
            for item in report['details']['warnings']:
                print(f"  ⚠️  {item['check']}: {item['message']}")
        
        if report['recommendations']:
            print("\n📋 RECOMMENDATIONS:")
            for rec in report['recommendations']:
                print(f"  {rec}")
        
        print("\n" + "="*60)
        
        # Write report to file
        report_file = Path(__file__).parent.parent / "security-validation-report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Full report saved to: {report_file}")
        
        if success:
            print("✅ Security validation PASSED")
            return 0
        else:
            print("❌ Security validation FAILED")
            return 1
            
    except Exception as e:
        logger.error(f"Security validation failed with exception: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)