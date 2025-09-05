"""
Environment-Specific Security Validation

Provides comprehensive security validation that enforces different security
requirements based on deployment environment (production, staging, development).
"""

import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

import structlog

from ..application.config import DeploymentContext, DeploymentMode
from .secrets_policy import Environment, HardenedSecretsManager
from .unified_csrf_strategy import CSRFConfig, CSRFMode

logger = structlog.get_logger(__name__)


class SecuritySeverity(str, Enum):
    """Security issue severity levels."""

    CRITICAL = "critical"  # Production-breaking security issues
    HIGH = "high"  # Serious security vulnerabilities
    MEDIUM = "medium"  # Security best practice violations
    LOW = "low"  # Minor security improvements
    INFO = "info"  # Informational security notes


@dataclass
class SecurityViolation:
    """Represents a security validation violation."""

    severity: SecuritySeverity
    category: str
    message: str
    environment: Environment
    portal_name: Optional[str] = None
    remediation: Optional[str] = None
    compliance_standard: Optional[str] = None


@dataclass
class SecurityValidationResult:
    """Results of comprehensive security validation."""

    environment: Environment
    compliant: bool
    violations: list[SecurityViolation]
    passed_checks: list[str]
    security_score: float  # 0-100 score based on violations

    def get_violations_by_severity(
        self, severity: SecuritySeverity
    ) -> list[SecurityViolation]:
        """Get violations filtered by severity."""
        return [v for v in self.violations if v.severity == severity]

    def has_critical_violations(self) -> bool:
        """Check if there are any critical violations."""
        return any(v.severity == SecuritySeverity.CRITICAL for v in self.violations)

    def calculate_security_score(self) -> float:
        """Calculate security score (0-100) based on violations."""
        if not self.violations:
            return 100.0

        # Weight violations by severity
        severity_weights = {
            SecuritySeverity.CRITICAL: 25,
            SecuritySeverity.HIGH: 15,
            SecuritySeverity.MEDIUM: 10,
            SecuritySeverity.LOW: 5,
            SecuritySeverity.INFO: 1,
        }

        total_penalty = sum(
            severity_weights.get(v.severity, 0) for v in self.violations
        )

        # Cap at 100 point deduction
        penalty = min(total_penalty, 100)
        return max(0.0, 100.0 - penalty)


class EnvironmentSecurityValidator:
    """
    Comprehensive security validator with environment-specific requirements.

    Validates security configurations, secret management, CSRF protection,
    and other security controls based on deployment environment.
    """

    def __init__(
        self,
        environment: Environment,
        portal_name: Optional[str] = None,
        deployment_context: Optional[DeploymentContext] = None,
    ):
        self.environment = environment
        self.portal_name = portal_name or "unknown"
        self.deployment_context = deployment_context

        # Environment-specific security requirements
        self.requirements = self._get_environment_requirements()

    def _get_environment_requirements(self) -> dict[str, Any]:
        """Get security requirements based on environment."""

        if self.environment == Environment.PRODUCTION:
            return {
                "secrets_management": {
                    "vault_required": True,
                    "env_fallback_allowed": False,
                    "rotation_enforced": True,
                },
                "csrf_protection": {
                    "required": True,
                    "strict_mode": True,
                    "referer_check": True,
                },
                "rate_limiting": {"required": True, "strict_limits": True},
                "security_headers": {
                    "required": True,
                    "hsts_required": True,
                    "csp_required": True,
                },
                "tls": {"required": True, "min_version": "1.2"},
                "logging": {"security_events": True, "audit_required": True},
            }

        elif self.environment == Environment.STAGING:
            return {
                "secrets_management": {
                    "vault_required": True,
                    "env_fallback_allowed": True,  # With warnings
                    "rotation_enforced": False,
                },
                "csrf_protection": {
                    "required": True,
                    "strict_mode": True,
                    "referer_check": True,
                },
                "rate_limiting": {"required": True, "strict_limits": False},
                "security_headers": {
                    "required": True,
                    "hsts_required": False,
                    "csp_required": True,
                },
                "tls": {"required": True, "min_version": "1.2"},
                "logging": {"security_events": True, "audit_required": False},
            }

        else:  # Development
            return {
                "secrets_management": {
                    "vault_required": False,
                    "env_fallback_allowed": True,
                    "rotation_enforced": False,
                },
                "csrf_protection": {
                    "required": False,  # Optional in development
                    "strict_mode": False,
                    "referer_check": False,
                },
                "rate_limiting": {"required": False, "strict_limits": False},
                "security_headers": {
                    "required": False,
                    "hsts_required": False,
                    "csp_required": False,
                },
                "tls": {"required": False, "min_version": "1.0"},
                "logging": {"security_events": False, "audit_required": False},
            }

    async def validate_comprehensive_security(
        self,
        secrets_manager: Optional[HardenedSecretsManager] = None,
        csrf_config: Optional[CSRFConfig] = None,
        additional_checks: Optional[dict[str, Any]] = None,
    ) -> SecurityValidationResult:
        """
        Run comprehensive security validation.

        Args:
            secrets_manager: Optional secrets manager to validate
            csrf_config: Optional CSRF configuration to validate
            additional_checks: Additional portal-specific checks

        Returns:
            Complete security validation result
        """
        violations = []
        passed_checks = []

        try:
            # 1. Validate secrets management
            secrets_result = await self._validate_secrets_management(secrets_manager)
            violations.extend(secrets_result["violations"])
            passed_checks.extend(secrets_result["passed"])

            # 2. Validate CSRF protection
            csrf_result = self._validate_csrf_protection(csrf_config)
            violations.extend(csrf_result["violations"])
            passed_checks.extend(csrf_result["passed"])

            # 3. Validate environment configuration
            env_result = self._validate_environment_configuration()
            violations.extend(env_result["violations"])
            passed_checks.extend(env_result["passed"])

            # 4. Validate security headers
            headers_result = self._validate_security_headers()
            violations.extend(headers_result["violations"])
            passed_checks.extend(headers_result["passed"])

            # 5. Validate rate limiting
            rate_result = self._validate_rate_limiting()
            violations.extend(rate_result["violations"])
            passed_checks.extend(rate_result["passed"])

            # 6. Additional portal-specific checks
            if additional_checks:
                additional_result = self._validate_additional_checks(additional_checks)
                violations.extend(additional_result["violations"])
                passed_checks.extend(additional_result["passed"])

            # Create validation result
            result = SecurityValidationResult(
                environment=self.environment,
                compliant=not any(
                    v.severity == SecuritySeverity.CRITICAL for v in violations
                ),
                violations=violations,
                passed_checks=passed_checks,
                security_score=0.0,  # Will be calculated below
            )

            result.security_score = result.calculate_security_score()

            logger.info(
                "Security validation completed",
                environment=self.environment.value,
                portal=self.portal_name,
                compliant=result.compliant,
                security_score=result.security_score,
                violations_count=len(violations),
                critical_violations=len(
                    result.get_violations_by_severity(SecuritySeverity.CRITICAL)
                ),
            )

            return result

        except Exception as e:
            logger.error(f"Security validation failed: {e}")

            # Create failure result
            return SecurityValidationResult(
                environment=self.environment,
                compliant=False,
                violations=[
                    SecurityViolation(
                        severity=SecuritySeverity.CRITICAL,
                        category="validation_failure",
                        message=f"Security validation process failed: {e}",
                        environment=self.environment,
                        portal_name=self.portal_name,
                        remediation="Fix validation process and retry",
                    )
                ],
                passed_checks=[],
                security_score=0.0,
            )

    async def _validate_secrets_management(
        self, secrets_manager: Optional[HardenedSecretsManager]
    ) -> dict[str, list]:
        """Validate secrets management configuration."""
        violations = []
        passed = []
        requirements = self.requirements["secrets_management"]

        if not secrets_manager:
            if requirements["vault_required"]:
                violations.append(
                    SecurityViolation(
                        severity=SecuritySeverity.CRITICAL,
                        category="secrets_management",
                        message="Secrets manager not configured but required",
                        environment=self.environment,
                        portal_name=self.portal_name,
                        remediation="Configure HardenedSecretsManager with OpenBao/Vault",
                        compliance_standard="DOTMAC-SEC-001",
                    )
                )
            else:
                passed.append("secrets_manager_not_required")
        else:
            try:
                # Check environment compliance
                compliance = await secrets_manager.validate_environment_compliance()

                if not compliance["compliant"]:
                    for violation_msg in compliance["violations"]:
                        severity = (
                            SecuritySeverity.CRITICAL
                            if requirements["vault_required"]
                            else SecuritySeverity.HIGH
                        )
                        violations.append(
                            SecurityViolation(
                                severity=severity,
                                category="secrets_compliance",
                                message=violation_msg,
                                environment=self.environment,
                                portal_name=self.portal_name,
                                remediation="Fix OpenBao/Vault configuration",
                                compliance_standard="DOTMAC-SEC-002",
                            )
                        )
                else:
                    passed.append("secrets_compliance_valid")

                # Check store status
                store_status = compliance.get("store_status", {})

                # Validate primary store (OpenBao/Vault)
                primary_store = store_status.get("primary")
                if requirements["vault_required"]:
                    if not primary_store or not primary_store.get("healthy"):
                        violations.append(
                            SecurityViolation(
                                severity=SecuritySeverity.CRITICAL,
                                category="vault_health",
                                message="OpenBao/Vault primary store not healthy",
                                environment=self.environment,
                                portal_name=self.portal_name,
                                remediation="Check OpenBao/Vault connectivity and health",
                                compliance_standard="DOTMAC-SEC-003",
                            )
                        )
                    else:
                        passed.append("vault_primary_healthy")

                # Check fallback store usage
                fallback_store = store_status.get("fallback")
                if fallback_store and self.environment == Environment.PRODUCTION:
                    violations.append(
                        SecurityViolation(
                            severity=SecuritySeverity.CRITICAL,
                            category="env_fallback",
                            message="Environment variable fallback active in production",
                            environment=self.environment,
                            portal_name=self.portal_name,
                            remediation="Configure OpenBao/Vault for production secrets",
                            compliance_standard="DOTMAC-SEC-004",
                        )
                    )

            except Exception as e:
                violations.append(
                    SecurityViolation(
                        severity=SecuritySeverity.HIGH,
                        category="secrets_validation_error",
                        message=f"Failed to validate secrets manager: {e}",
                        environment=self.environment,
                        portal_name=self.portal_name,
                        remediation="Check secrets manager configuration",
                    )
                )

        return {"violations": violations, "passed": passed}

    def _validate_csrf_protection(
        self, csrf_config: Optional[CSRFConfig]
    ) -> dict[str, list]:
        """Validate CSRF protection configuration."""
        violations = []
        passed = []
        requirements = self.requirements["csrf_protection"]

        if requirements["required"]:
            if not csrf_config:
                violations.append(
                    SecurityViolation(
                        severity=SecuritySeverity.HIGH,
                        category="csrf_missing",
                        message="CSRF protection not configured but required",
                        environment=self.environment,
                        portal_name=self.portal_name,
                        remediation="Configure CSRF protection middleware",
                        compliance_standard="DOTMAC-SEC-005",
                    )
                )
            elif csrf_config.mode == CSRFMode.DISABLED:
                violations.append(
                    SecurityViolation(
                        severity=SecuritySeverity.HIGH,
                        category="csrf_disabled",
                        message="CSRF protection disabled in environment that requires it",
                        environment=self.environment,
                        portal_name=self.portal_name,
                        remediation="Enable CSRF protection",
                        compliance_standard="DOTMAC-SEC-006",
                    )
                )
            else:
                passed.append("csrf_protection_enabled")

                # Check strict mode requirement
                if (
                    requirements["strict_mode"]
                    and not csrf_config.require_referer_check
                ):
                    violations.append(
                        SecurityViolation(
                            severity=SecuritySeverity.MEDIUM,
                            category="csrf_not_strict",
                            message="CSRF protection not in strict mode",
                            environment=self.environment,
                            portal_name=self.portal_name,
                            remediation="Enable strict CSRF mode with referer checking",
                        )
                    )
                else:
                    passed.append("csrf_strict_mode_ok")
        else:
            passed.append("csrf_not_required")

        return {"violations": violations, "passed": passed}

    def _validate_environment_configuration(self) -> dict[str, list]:
        """Validate environment-specific configuration."""
        violations = []
        passed = []

        # Check environment variable consistency
        env_var = os.getenv("ENVIRONMENT", "").lower()
        if env_var and env_var != self.environment.value:
            violations.append(
                SecurityViolation(
                    severity=SecuritySeverity.MEDIUM,
                    category="env_mismatch",
                    message=f"Environment variable ({env_var}) doesn't match detected environment ({self.environment.value})",
                    environment=self.environment,
                    portal_name=self.portal_name,
                    remediation="Ensure ENVIRONMENT variable matches deployment",
                )
            )
        else:
            passed.append("environment_consistent")

        # Check deployment context consistency
        if self.deployment_context:
            if (
                self.environment == Environment.PRODUCTION
                and self.deployment_context.mode == DeploymentMode.DEVELOPMENT
            ):
                violations.append(
                    SecurityViolation(
                        severity=SecuritySeverity.HIGH,
                        category="deployment_mismatch",
                        message="Production environment with development deployment mode",
                        environment=self.environment,
                        portal_name=self.portal_name,
                        remediation="Ensure deployment mode matches environment",
                    )
                )
            else:
                passed.append("deployment_context_consistent")

        # Check production-specific requirements
        if self.environment == Environment.PRODUCTION:
            # Check debug mode
            debug_mode = os.getenv("DEBUG", "false").lower() in ["true", "1", "yes"]
            if debug_mode:
                violations.append(
                    SecurityViolation(
                        severity=SecuritySeverity.HIGH,
                        category="debug_in_production",
                        message="Debug mode enabled in production",
                        environment=self.environment,
                        portal_name=self.portal_name,
                        remediation="Disable debug mode in production",
                        compliance_standard="DOTMAC-SEC-007",
                    )
                )
            else:
                passed.append("debug_mode_disabled")

        return {"violations": violations, "passed": passed}

    def _validate_security_headers(self) -> dict[str, list]:
        """Validate security headers configuration."""
        violations = []
        passed = []
        requirements = self.requirements["security_headers"]

        if requirements["required"]:
            # In a real implementation, we would check the actual headers
            # being set by the security middleware
            passed.append("security_headers_assumed_configured")

            if (
                requirements.get("hsts_required")
                and self.environment == Environment.PRODUCTION
            ):
                # Check if HTTPS is enforced
                https_only = os.getenv("HTTPS_ONLY", "false").lower() in [
                    "true",
                    "1",
                    "yes",
                ]
                if not https_only:
                    violations.append(
                        SecurityViolation(
                            severity=SecuritySeverity.HIGH,
                            category="https_not_enforced",
                            message="HTTPS not enforced in production",
                            environment=self.environment,
                            portal_name=self.portal_name,
                            remediation="Enable HTTPS enforcement",
                            compliance_standard="DOTMAC-SEC-008",
                        )
                    )
                else:
                    passed.append("https_enforced")
        else:
            passed.append("security_headers_not_required")

        return {"violations": violations, "passed": passed}

    def _validate_rate_limiting(self) -> dict[str, list]:
        """Validate rate limiting configuration."""
        violations = []
        passed = []
        requirements = self.requirements["rate_limiting"]

        if requirements["required"]:
            # In a real implementation, we would check the actual rate limiting
            # configuration from the middleware
            passed.append("rate_limiting_assumed_configured")

            if (
                requirements.get("strict_limits")
                and self.environment == Environment.PRODUCTION
            ):
                # Could check specific rate limit values if available
                passed.append("strict_rate_limits_assumed")
        else:
            passed.append("rate_limiting_not_required")

        return {"violations": violations, "passed": passed}

    def _validate_additional_checks(
        self, additional_checks: dict[str, Any]
    ) -> dict[str, list]:
        """Validate additional portal-specific checks."""
        violations = []
        passed = []

        for check_name, check_config in additional_checks.items():
            try:
                if check_config.get("required", False):
                    if not check_config.get("configured", False):
                        violations.append(
                            SecurityViolation(
                                severity=SecuritySeverity.MEDIUM,
                                category=f"additional_{check_name}",
                                message=f"Additional security check '{check_name}' required but not configured",
                                environment=self.environment,
                                portal_name=self.portal_name,
                                remediation=check_config.get(
                                    "remediation", f"Configure {check_name}"
                                ),
                            )
                        )
                    else:
                        passed.append(f"additional_{check_name}_configured")
                else:
                    passed.append(f"additional_{check_name}_not_required")

            except Exception as e:
                violations.append(
                    SecurityViolation(
                        severity=SecuritySeverity.LOW,
                        category="additional_check_error",
                        message=f"Failed to validate additional check '{check_name}': {e}",
                        environment=self.environment,
                        portal_name=self.portal_name,
                    )
                )

        return {"violations": violations, "passed": passed}


# Factory functions for portal-specific validators


def create_admin_portal_validator(
    environment: Environment, deployment_context: Optional[DeploymentContext] = None
) -> EnvironmentSecurityValidator:
    """Create security validator for Admin Portal."""
    return EnvironmentSecurityValidator(
        environment=environment,
        portal_name="admin",
        deployment_context=deployment_context,
    )


def create_customer_portal_validator(
    environment: Environment, deployment_context: Optional[DeploymentContext] = None
) -> EnvironmentSecurityValidator:
    """Create security validator for Customer Portal."""
    return EnvironmentSecurityValidator(
        environment=environment,
        portal_name="customer",
        deployment_context=deployment_context,
    )


def create_management_portal_validator(
    environment: Environment, deployment_context: Optional[DeploymentContext] = None
) -> EnvironmentSecurityValidator:
    """Create security validator for Management Portal."""
    return EnvironmentSecurityValidator(
        environment=environment,
        portal_name="management",
        deployment_context=deployment_context,
    )


def create_reseller_portal_validator(
    environment: Environment, deployment_context: Optional[DeploymentContext] = None
) -> EnvironmentSecurityValidator:
    """Create security validator for Reseller Portal."""
    return EnvironmentSecurityValidator(
        environment=environment,
        portal_name="reseller",
        deployment_context=deployment_context,
    )


def create_technician_portal_validator(
    environment: Environment, deployment_context: Optional[DeploymentContext] = None
) -> EnvironmentSecurityValidator:
    """Create security validator for Technician Portal."""
    return EnvironmentSecurityValidator(
        environment=environment,
        portal_name="technician",
        deployment_context=deployment_context,
    )


# Utility functions


async def validate_portal_security(
    portal_type: str,
    environment: Environment,
    secrets_manager: Optional[HardenedSecretsManager] = None,
    csrf_config: Optional[CSRFConfig] = None,
    deployment_context: Optional[DeploymentContext] = None,
    additional_checks: Optional[dict[str, Any]] = None,
) -> SecurityValidationResult:
    """
    Convenience function to validate security for any portal type.

    Args:
        portal_type: Type of portal (admin, customer, management, reseller, technician)
        environment: Deployment environment
        secrets_manager: Optional secrets manager to validate
        csrf_config: Optional CSRF configuration to validate
        deployment_context: Optional deployment context
        additional_checks: Optional additional checks

    Returns:
        Security validation result
    """
    validator_creators = {
        "admin": create_admin_portal_validator,
        "customer": create_customer_portal_validator,
        "management": create_management_portal_validator,
        "reseller": create_reseller_portal_validator,
        "technician": create_technician_portal_validator,
    }

    validator_creator = validator_creators.get(portal_type)
    if not validator_creator:
        raise ValueError(f"Unknown portal type: {portal_type}")

    validator = validator_creator(environment, deployment_context)

    return await validator.validate_comprehensive_security(
        secrets_manager=secrets_manager,
        csrf_config=csrf_config,
        additional_checks=additional_checks,
    )


async def validate_all_portals_security(
    environment: Environment, deployment_context: Optional[DeploymentContext] = None
) -> dict[str, SecurityValidationResult]:
    """
    Validate security for all portal types.

    Args:
        environment: Deployment environment
        deployment_context: Optional deployment context

    Returns:
        Dictionary mapping portal types to validation results
    """
    portal_types = ["admin", "customer", "management", "reseller", "technician"]
    results = {}

    for portal_type in portal_types:
        try:
            result = await validate_portal_security(
                portal_type=portal_type,
                environment=environment,
                deployment_context=deployment_context,
            )
            results[portal_type] = result
        except Exception as e:
            logger.error(f"Failed to validate security for {portal_type} portal: {e}")
            results[portal_type] = SecurityValidationResult(
                environment=environment,
                compliant=False,
                violations=[
                    SecurityViolation(
                        severity=SecuritySeverity.CRITICAL,
                        category="validation_error",
                        message=f"Validation failed for {portal_type}: {e}",
                        environment=environment,
                        portal_name=portal_type,
                    )
                ],
                passed_checks=[],
                security_score=0.0,
            )

    return results
