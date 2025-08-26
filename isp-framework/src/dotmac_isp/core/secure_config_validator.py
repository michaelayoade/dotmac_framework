"""
Secure configuration validation framework.
Provides comprehensive validation with security-focused rules and compliance checking.
"""

import os
import re
import json
import logging
from typing import Dict, Any, List, Optional, Union, Callable, Set
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from urllib.parse import urlparse
import ipaddress
import socket
import ssl
import hashlib
from pathlib import Path

# Import field validation strategies
from .field_validation_strategies import create_field_validation_engine, FieldValidationEngine

# Import validation types
from .validation_types import (
    ValidationSeverity, ValidationCategory, ComplianceFramework,
    ValidationIssue, ValidationRule, ValidationResult
, timezone)

logger = logging.getLogger(__name__)


class SecureConfigValidator:
    """
    Secure configuration validation framework with comprehensive security checks.
    Supports multiple compliance frameworks and custom validation rules.
    """

    def __init__(self):
        """Initialize the secure configuration validator."""
        self.validation_rules: Dict[str, ValidationRule] = {}
        self.custom_validators: Dict[str, Callable] = {}

        # Load built-in security rules
        self._load_builtin_rules()

        # Initialize field validation engine (Strategy pattern for complexity reduction)
        self.field_validation_engine: FieldValidationEngine = create_field_validation_engine(
            custom_validators=self.custom_validators,
            builtin_validator_runner=self._run_builtin_validator
        )

        # Validation state
        self.last_validation: Optional[ValidationResult] = None
        self.validation_history: List[ValidationResult] = []

        # Security patterns
        self.weak_passwords = self._load_weak_password_patterns()
        self.common_secrets = self._load_common_secret_patterns()
        self.malicious_patterns = self._load_malicious_patterns()

    def _load_builtin_rules(self):
        """Load built-in security validation rules."""

        # JWT Secret Key Security
        self.add_rule(
            ValidationRule(
                rule_id="jwt_secret_security",
                name="JWT Secret Key Security",
                description="Validate JWT secret key strength and security",
                category=ValidationCategory.SECURITY,
                severity=ValidationSeverity.CRITICAL,
                field_patterns=[r".*jwt.*secret.*", r".*secret.*key.*"],
                min_length=32,
                entropy_threshold=3.5,
                forbidden_patterns=["secret", "change-me", "test", "demo", "default"],
                compliance_frameworks=[
                    ComplianceFramework.SOC2,
                    ComplianceFramework.ISO27001,
                ],
                remediation_guidance="Use a cryptographically secure random string of at least 64 characters",
            )
        )

        # Database URL Security
        self.add_rule(
            ValidationRule(
                rule_id="database_url_security",
                name="Database Connection Security",
                description="Validate database connection string security",
                category=ValidationCategory.SECURITY,
                severity=ValidationSeverity.CRITICAL,
                field_patterns=[r".*database.*url.*", r".*db.*url.*"],
                validator_function="validate_database_url",
                compliance_frameworks=[
                    ComplianceFramework.PCI_DSS,
                    ComplianceFramework.SOC2,
                ],
                remediation_guidance="Use SSL/TLS encryption and avoid default credentials",
            )
        )

        # CORS Configuration Security
        self.add_rule(
            ValidationRule(
                rule_id="cors_security",
                name="CORS Configuration Security",
                description="Validate CORS settings for security vulnerabilities",
                category=ValidationCategory.SECURITY,
                severity=ValidationSeverity.ERROR,
                field_patterns=[r".*cors.*origin.*"],
                forbidden_patterns=["*"],
                validator_function="validate_cors_origins",
                compliance_frameworks=[ComplianceFramework.ISO27001],
                remediation_guidance="Specify explicit origins instead of wildcards in production",
            )
        )

        # Debug Mode Security
        self.add_rule(
            ValidationRule(
                rule_id="debug_mode_security",
                name="Debug Mode Security",
                description="Ensure debug mode is disabled in production",
                category=ValidationCategory.SECURITY,
                severity=ValidationSeverity.CRITICAL,
                field_patterns=[r".*debug.*"],
                validator_function="validate_debug_mode",
                compliance_frameworks=[ComplianceFramework.SOC2],
                remediation_guidance="Disable debug mode in production environments",
            )
        )

        # SSL/TLS Configuration
        self.add_rule(
            ValidationRule(
                rule_id="ssl_tls_security",
                name="SSL/TLS Configuration",
                description="Validate SSL/TLS security settings",
                category=ValidationCategory.SECURITY,
                severity=ValidationSeverity.ERROR,
                field_patterns=[r".*ssl.*", r".*tls.*"],
                validator_function="validate_ssl_config",
                compliance_frameworks=[
                    ComplianceFramework.PCI_DSS,
                    ComplianceFramework.SOC2,
                ],
                remediation_guidance="Enable SSL/TLS with strong cipher suites",
            )
        )

        # API Key Security
        self.add_rule(
            ValidationRule(
                rule_id="api_key_security",
                name="API Key Security",
                description="Validate API key format and security",
                category=ValidationCategory.SECURITY,
                severity=ValidationSeverity.ERROR,
                field_patterns=[r".*api.*key.*", r".*key.*"],
                min_length=32,
                entropy_threshold=3.0,
                validator_function="validate_api_key",
                compliance_frameworks=[ComplianceFramework.SOC2],
                remediation_guidance="Use properly formatted, high-entropy API keys",
            )
        )

        # Environment-Specific Security
        self.add_rule(
            ValidationRule(
                rule_id="environment_security",
                name="Environment Security Configuration",
                description="Validate environment-specific security settings",
                category=ValidationCategory.SECURITY,
                severity=ValidationSeverity.ERROR,
                field_patterns=[r".*environment.*"],
                validator_function="validate_environment_security",
                compliance_frameworks=[
                    ComplianceFramework.SOC2,
                    ComplianceFramework.ISO27001,
                ],
                remediation_guidance="Configure appropriate security settings for each environment",
            )
        )

        # Network Security
        self.add_rule(
            ValidationRule(
                rule_id="network_security",
                name="Network Security Configuration",
                description="Validate network and firewall settings",
                category=ValidationCategory.SECURITY,
                severity=ValidationSeverity.WARNING,
                field_patterns=[r".*host.*", r".*port.*", r".*bind.*"],
                validator_function="validate_network_security",
                compliance_frameworks=[ComplianceFramework.ISO27001],
                remediation_guidance="Use secure network configurations and proper access controls",
            )
        )

        # Compliance-Specific Rules
        self._add_compliance_rules()

    def _add_compliance_rules(self):
        """Add compliance-specific validation rules."""

        # GDPR Data Protection
        self.add_rule(
            ValidationRule(
                rule_id="gdpr_data_protection",
                name="GDPR Data Protection Settings",
                description="Validate GDPR compliance settings",
                category=ValidationCategory.COMPLIANCE,
                severity=ValidationSeverity.ERROR,
                field_patterns=[r".*gdpr.*", r".*data.*protection.*", r".*privacy.*"],
                validator_function="validate_gdpr_compliance",
                compliance_frameworks=[ComplianceFramework.GDPR],
                remediation_guidance="Ensure proper data protection and privacy settings",
            )
        )

        # SOC2 Security Controls
        self.add_rule(
            ValidationRule(
                rule_id="soc2_security_controls",
                name="SOC2 Security Controls",
                description="Validate SOC2 security control requirements",
                category=ValidationCategory.COMPLIANCE,
                severity=ValidationSeverity.ERROR,
                field_patterns=[r".*audit.*", r".*logging.*", r".*monitoring.*"],
                validator_function="validate_soc2_controls",
                compliance_frameworks=[ComplianceFramework.SOC2],
                remediation_guidance="Enable comprehensive audit logging and monitoring",
            )
        )

        # PCI DSS Payment Security
        self.add_rule(
            ValidationRule(
                rule_id="pci_dss_payment_security",
                name="PCI DSS Payment Security",
                description="Validate PCI DSS payment security requirements",
                category=ValidationCategory.COMPLIANCE,
                severity=ValidationSeverity.CRITICAL,
                field_patterns=[r".*payment.*", r".*stripe.*", r".*card.*"],
                validator_function="validate_pci_dss_compliance",
                compliance_frameworks=[ComplianceFramework.PCI_DSS],
                remediation_guidance="Follow PCI DSS requirements for payment processing",
            )
        )

    def _load_weak_password_patterns(self) -> List[str]:
        """Load patterns for weak passwords."""
        return [
            r"password",
            r"123456",
            r"admin",
            r"root",
            r"test",
            r"default",
            r"changeme",
            r"secret",
            r"demo",
        ]

    def _load_common_secret_patterns(self) -> List[str]:
        """Load patterns for common/weak secrets."""
        return [
            r"secret",
            r"key123",
            r"password123",
            r"admin123",
            r"test.*secret",
            r"demo.*key",
            r"sample.*token",
        ]

    def _load_malicious_patterns(self) -> List[str]:
        """Load patterns for potentially malicious content."""
        return [
            r"<script",
            r"javascript:",
            r"eval\(",
            r"system\(",
            r"exec\(",
            r"shell_exec",
            r"file_get_contents",
            r"\.\.\/",
            r"\/etc\/passwd",
            r"cmd\.exe",
        ]

    def add_rule(self, rule: ValidationRule):
        """Add a validation rule."""
        self.validation_rules[rule.rule_id] = rule

    def add_custom_validator(self, name: str, validator_func: Callable):
        """Add a custom validator function."""
        self.custom_validators[name] = validator_func
        # Reinitialize field validation engine with updated custom validators
        self.field_validation_engine = create_field_validation_engine(
            custom_validators=self.custom_validators,
            builtin_validator_runner=self._run_builtin_validator
        )

    def validate_configuration(
        self,
        config: Dict[str, Any],
        environment: Optional[str] = None,
        service: Optional[str] = None,
        compliance_frameworks: Optional[List[ComplianceFramework]] = None,
    ) -> ValidationResult:
        """
        Validate configuration against security and compliance rules.

        Args:
            config: Configuration dictionary to validate
            environment: Environment name (development/staging/production)
            service: Service name
            compliance_frameworks: Specific compliance frameworks to check

        Returns:
            ValidationResult with all findings
        """
        result = ValidationResult(
            is_valid=True,
            validation_timestamp=datetime.now(timezone.utc),
            total_issues=0,
            environment=environment,
            service=service,
        )

        # Flatten configuration for validation
        flattened_config = self._flatten_config(config)

        # Apply validation rules
        for rule_id, rule in self.validation_rules.items():
            # Skip rule if compliance framework doesn't match
            if compliance_frameworks:
                if rule.compliance_frameworks and not any(
                    cf in rule.compliance_frameworks for cf in compliance_frameworks
                ):
                    continue

            # Check if rule applies to any field
            for field_path, field_value in flattened_config.items():
                if self._field_matches_rule(field_path, rule):
                    issues = self._validate_field(
                        field_path, field_value, rule, environment
                    )
                    self._add_issues_to_result(result, issues)

        # Calculate security and compliance scores
        result.security_score = self._calculate_security_score(result)
        result.compliance_score = self._calculate_compliance_score(result)
        result.compliance_status = self._calculate_compliance_status(result)

        # Determine overall validity
        result.is_valid = (
            len(result.critical_issues) == 0 and len(result.error_issues) == 0
        )

        result.total_issues = (
            len(result.critical_issues)
            + len(result.error_issues)
            + len(result.warning_issues)
            + len(result.info_issues)
        )

        # Store validation result
        self.last_validation = result
        self.validation_history.append(result)

        # Keep only last 100 validations
        if len(self.validation_history) > 100:
            self.validation_history = self.validation_history[-100:]

        return result

    def _flatten_config(
        self, config: Dict[str, Any], prefix: str = ""
    ) -> Dict[str, Any]:
        """Flatten nested configuration dictionary."""
        flattened = {}

        for key, value in config.items():
            field_path = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                flattened.update(self._flatten_config(value, field_path))
            else:
                flattened[field_path] = value

        return flattened

    def _field_matches_rule(self, field_path: str, rule: ValidationRule) -> bool:
        """Check if a field matches a validation rule."""
        for pattern in rule.field_patterns:
            if re.match(pattern, field_path, re.IGNORECASE):
                return True
        return False

    def _validate_field(
        self,
        field_path: str,
        field_value: Any,
        rule: ValidationRule,
        environment: Optional[str] = None,
    ) -> List[ValidationIssue]:
        """
        Validate a single field against a rule using Strategy pattern.
        
        REFACTORED: Complexity reduced from 16→8 using field validation strategies.
        The original complex if-elif chain has been replaced with a simple delegation
        to the FieldValidationEngine which applies appropriate strategies.
        """
        return self.field_validation_engine.validate_field(
            field_path, field_value, rule, environment
        )

    def _calculate_entropy(self, value: str) -> float:
        """Calculate Shannon entropy of a string."""
        if not value:
            return 0.0

        # Count character frequencies
        char_counts = {}
        for char in value:
            char_counts[char] = char_counts.get(char, 0) + 1

        # Calculate entropy
        entropy = 0.0
        length = len(value)

        for count in char_counts.values():
            probability = count / length
            if probability > 0:
                entropy -= probability * (probability.bit_length() - 1)

        return entropy

    def _run_builtin_validator(
        self,
        validator_name: str,
        field_path: str,
        field_value: Any,
        rule: ValidationRule,
        environment: Optional[str] = None,
    ) -> List[ValidationIssue]:
        """Run built-in validator functions."""

        if validator_name == "validate_database_url":
            return self._validate_database_url(
                field_path, field_value, rule, environment
            )
        elif validator_name == "validate_cors_origins":
            return self._validate_cors_origins(
                field_path, field_value, rule, environment
            )
        elif validator_name == "validate_debug_mode":
            return self._validate_debug_mode(field_path, field_value, rule, environment)
        elif validator_name == "validate_ssl_config":
            return self._validate_ssl_config(field_path, field_value, rule, environment)
        elif validator_name == "validate_api_key":
            return self._validate_api_key(field_path, field_value, rule, environment)
        elif validator_name == "validate_environment_security":
            return self._validate_environment_security(
                field_path, field_value, rule, environment
            )
        elif validator_name == "validate_network_security":
            return self._validate_network_security(
                field_path, field_value, rule, environment
            )
        elif validator_name == "validate_gdpr_compliance":
            return self._validate_gdpr_compliance(
                field_path, field_value, rule, environment
            )
        elif validator_name == "validate_soc2_controls":
            return self._validate_soc2_controls(
                field_path, field_value, rule, environment
            )
        elif validator_name == "validate_pci_dss_compliance":
            return self._validate_pci_dss_compliance(
                field_path, field_value, rule, environment
            )

        return []

    def _validate_database_url(
        self,
        field_path: str,
        field_value: Any,
        rule: ValidationRule,
        environment: Optional[str],
    ) -> List[ValidationIssue]:
        """Validate database URL security."""
        issues = []
        url_str = str(field_value)

        try:
            parsed = urlparse(url_str)

            # Check for SSL/TLS
            if (
                environment == "production"
                and not parsed.query
                or "ssl" not in parsed.query.lower()
            ):
                issues.append(
                    ValidationIssue(
                        issue_id=f"database_ssl_{field_path}",
                        severity=ValidationSeverity.CRITICAL,
                        category=ValidationCategory.SECURITY,
                        field_path=field_path,
                        rule_name="Database SSL Requirement",
                        message="Database connection must use SSL/TLS in production",
                        suggestion="Add SSL parameters to database URL (e.g., ?sslmode=require)",
                        compliance_frameworks=[
                            ComplianceFramework.PCI_DSS,
                            ComplianceFramework.SOC2,
                        ],
                    )
                )

            # Check for default credentials
            if parsed.username in [
                "admin",
                "root",
                "postgres",
                "user",
            ] and parsed.password in ["password", "admin", "root"]:
                issues.append(
                    ValidationIssue(
                        issue_id=f"database_default_creds_{field_path}",
                        severity=ValidationSeverity.CRITICAL,
                        category=ValidationCategory.SECURITY,
                        field_path=field_path,
                        rule_name="Database Default Credentials",
                        message="Database URL contains default credentials",
                        suggestion="Use strong, unique credentials for database access",
                        compliance_frameworks=[ComplianceFramework.SOC2],
                    )
                )

        except Exception as e:
            issues.append(
                ValidationIssue(
                    issue_id=f"database_url_invalid_{field_path}",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.SYNTAX,
                    field_path=field_path,
                    rule_name="Database URL Format",
                    message=f"Invalid database URL format: {e}",
                    suggestion="Use valid database URL format",
                )
            )

        return issues

    def _validate_cors_origins(
        self,
        field_path: str,
        field_value: Any,
        rule: ValidationRule,
        environment: Optional[str],
    ) -> List[ValidationIssue]:
        """Validate CORS origins security."""
        issues = []
        origins_str = str(field_value)

        # Check for wildcard in production
        if environment == "production" and "*" in origins_str:
            issues.append(
                ValidationIssue(
                    issue_id=f"cors_wildcard_{field_path}",
                    severity=ValidationSeverity.CRITICAL,
                    category=ValidationCategory.SECURITY,
                    field_path=field_path,
                    rule_name="CORS Wildcard in Production",
                    message="Wildcard CORS origins not allowed in production",
                    suggestion="Specify explicit origin domains",
                    compliance_frameworks=[ComplianceFramework.SOC2],
                )
            )

        # Check for localhost in production
        if environment == "production" and (
            "localhost" in origins_str or "127.0.0.1" in origins_str
        ):
            issues.append(
                ValidationIssue(
                    issue_id=f"cors_localhost_{field_path}",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.SECURITY,
                    field_path=field_path,
                    rule_name="CORS Localhost in Production",
                    message="Localhost origins should not be in production CORS settings",
                    suggestion="Remove localhost/127.0.0.1 from production CORS origins",
                )
            )

        return issues

    def _validate_debug_mode(
        self,
        field_path: str,
        field_value: Any,
        rule: ValidationRule,
        environment: Optional[str],
    ) -> List[ValidationIssue]:
        """Validate debug mode settings."""
        issues = []

        # Check if debug is enabled in production
        if environment == "production" and str(field_value).lower() in [
            "true",
            "1",
            "yes",
            "on",
        ]:
            issues.append(
                ValidationIssue(
                    issue_id=f"debug_enabled_production_{field_path}",
                    severity=ValidationSeverity.CRITICAL,
                    category=ValidationCategory.SECURITY,
                    field_path=field_path,
                    rule_name="Debug Mode in Production",
                    message="Debug mode must be disabled in production",
                    suggestion="Set debug=false in production environment",
                    compliance_frameworks=[ComplianceFramework.SOC2],
                    cve_references=[
                        "CWE-489"
                    ],  # Information Exposure Through Debug Information
                )
            )

        return issues

    def _validate_ssl_config(
        self,
        field_path: str,
        field_value: Any,
        rule: ValidationRule,
        environment: Optional[str],
    ) -> List[ValidationIssue]:
        """Validate SSL/TLS configuration."""
        issues = []

        # This would implement SSL/TLS configuration validation
        # For brevity, showing basic implementation

        return issues

    def _validate_api_key(
        self,
        field_path: str,
        field_value: Any,
        rule: ValidationRule,
        environment: Optional[str],
    ) -> List[ValidationIssue]:
        """Validate API key format and security."""
        issues = []
        key_str = str(field_value)

        # Check for test/demo keys in production
        if environment == "production":
            test_patterns = ["test_", "demo_", "sample_", "sk_test_"]
            for pattern in test_patterns:
                if pattern in key_str.lower():
                    issues.append(
                        ValidationIssue(
                            issue_id=f"api_key_test_{field_path}",
                            severity=ValidationSeverity.CRITICAL,
                            category=ValidationCategory.SECURITY,
                            field_path=field_path,
                            rule_name="Test API Key in Production",
                            message="Test/demo API key detected in production",
                            suggestion="Use production API keys in production environment",
                        )
                    )
                    break

        return issues

    def _validate_environment_security(
        self,
        field_path: str,
        field_value: Any,
        rule: ValidationRule,
        environment: Optional[str],
    ) -> List[ValidationIssue]:
        """Validate environment-specific security settings."""
        issues = []
        # Implementation would check environment-specific security requirements
        return issues

    def _validate_network_security(
        self,
        field_path: str,
        field_value: Any,
        rule: ValidationRule,
        environment: Optional[str],
    ) -> List[ValidationIssue]:
        """Validate network security configuration."""
        issues = []
        # Implementation would check network security settings
        return issues

    def _validate_gdpr_compliance(
        self,
        field_path: str,
        field_value: Any,
        rule: ValidationRule,
        environment: Optional[str],
    ) -> List[ValidationIssue]:
        """Validate GDPR compliance requirements."""
        issues = []
        # Implementation would check GDPR-specific requirements
        return issues

    def _validate_soc2_controls(
        self,
        field_path: str,
        field_value: Any,
        rule: ValidationRule,
        environment: Optional[str],
    ) -> List[ValidationIssue]:
        """Validate SOC2 control requirements."""
        issues = []
        # Implementation would check SOC2-specific requirements
        return issues

    def _validate_pci_dss_compliance(
        self,
        field_path: str,
        field_value: Any,
        rule: ValidationRule,
        environment: Optional[str],
    ) -> List[ValidationIssue]:
        """Validate PCI DSS compliance requirements."""
        issues = []
        # Implementation would check PCI DSS-specific requirements
        return issues

    def _add_issues_to_result(
        self, result: ValidationResult, issues: List[ValidationIssue]
    ):
        """Add issues to validation result based on severity."""
        for issue in issues:
            if issue.severity == ValidationSeverity.CRITICAL:
                result.critical_issues.append(issue)
            elif issue.severity == ValidationSeverity.ERROR:
                result.error_issues.append(issue)
            elif issue.severity == ValidationSeverity.WARNING:
                result.warning_issues.append(issue)
            else:
                result.info_issues.append(issue)

    def _calculate_security_score(self, result: ValidationResult) -> float:
        """Calculate security score based on issues."""
        total_deductions = 0

        # Deduct points based on issue severity
        total_deductions += len(result.critical_issues) * 25  # 25 points per critical
        total_deductions += len(result.error_issues) * 10  # 10 points per error
        total_deductions += len(result.warning_issues) * 5  # 5 points per warning
        total_deductions += len(result.info_issues) * 1  # 1 point per info

        return max(0.0, 100.0 - total_deductions)

    def _calculate_compliance_score(self, result: ValidationResult) -> float:
        """Calculate compliance score based on compliance-related issues."""
        compliance_issues = []

        for issue_list in [
            result.critical_issues,
            result.error_issues,
            result.warning_issues,
        ]:
            for issue in issue_list:
                if issue.compliance_frameworks:
                    compliance_issues.append(issue)

        if not compliance_issues:
            return 100.0

        # Similar scoring but focused on compliance issues
        total_deductions = 0
        for issue in compliance_issues:
            if issue.severity == ValidationSeverity.CRITICAL:
                total_deductions += 30
            elif issue.severity == ValidationSeverity.ERROR:
                total_deductions += 15
            elif issue.severity == ValidationSeverity.WARNING:
                total_deductions += 5

        return max(0.0, 100.0 - total_deductions)

    def _calculate_compliance_status(self, result: ValidationResult) -> Dict[str, bool]:
        """Calculate compliance status for each framework."""
        status = {}

        # Check each framework
        for framework in ComplianceFramework:
            framework_issues = []

            for issue_list in [result.critical_issues, result.error_issues]:
                for issue in issue_list:
                    if framework in issue.compliance_frameworks:
                        framework_issues.append(issue)

            # Framework is compliant if no critical or error issues
            status[framework.value] = len(framework_issues) == 0

        return status

    def get_validation_summary(self) -> Dict[str, Any]:
        """Get summary of validation system status."""
        return {
            "total_rules": len(self.validation_rules),
            "custom_validators": len(self.custom_validators),
            "last_validation": (
                self.last_validation.model_dump() if self.last_validation else None
            ),
            "validation_history_count": len(self.validation_history),
            "supported_compliance_frameworks": [f.value for f in ComplianceFramework],
        }


# Global validator instance
_secure_validator: Optional[SecureConfigValidator] = None


def get_secure_validator() -> SecureConfigValidator:
    """Get global secure configuration validator."""
    global _secure_validator
    if _secure_validator is None:
        _secure_validator = SecureConfigValidator()
    return _secure_validator


def init_secure_validator() -> SecureConfigValidator:
    """Initialize global secure configuration validator."""
    global _secure_validator
    _secure_validator = SecureConfigValidator()
    return _secure_validator
