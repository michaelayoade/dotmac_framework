"""
Validation types and enums shared across validation modules.
"""

from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationCategory(str, Enum):
    """Categories of validation checks."""

    SECURITY = "security"
    COMPLIANCE = "compliance"
    PERFORMANCE = "performance"
    CONNECTIVITY = "connectivity"
    SYNTAX = "syntax"
    BUSINESS_LOGIC = "business_logic"


class ComplianceFramework(str, Enum):
    """Supported compliance frameworks."""

    GDPR = "gdpr"
    SOC2 = "soc2"
    ISO27001 = "iso27001"
    PCI_DSS = "pci_dss"
    HIPAA = "hipaa"
    NIST = "nist"


class ValidationIssue(BaseModel):
    """Represents a validation issue found during configuration validation."""

    issue_id: str = Field(..., description="Unique identifier for this issue")
    severity: ValidationSeverity = Field(..., description="Severity level of the issue")
    category: ValidationCategory = Field(..., description="Category of the validation")
    field_path: str = Field(..., description="Path to the field that caused the issue")
    rule_name: str = Field(..., description="Name of the validation rule")
    message: str = Field(..., description="Human-readable issue description")
    suggestion: str = Field(..., description="Suggested remediation")
    compliance_frameworks: List[ComplianceFramework] = Field(
        default_factory=list, description="Affected compliance frameworks"
    )
    current_value: Optional[str] = Field(None, description="Current field value")
    expected_value: Optional[str] = Field(None, description="Expected field value")
    validation_rule: Optional[str] = Field(
        None, description="The validation rule applied"
    )


class ValidationRule(BaseModel):
    """Defines a validation rule for configuration fields."""

    rule_id: str = Field(..., description="Unique identifier for this rule")
    name: str = Field(..., description="Human-readable name for the rule")
    description: str = Field(..., description="Description of what this rule validates")
    severity: ValidationSeverity = Field(
        ..., description="Default severity for violations"
    )
    category: ValidationCategory = Field(..., description="Category of validation")
    field_patterns: List[str] = Field(
        ..., description="Regex patterns for field matching"
    )
    required: bool = Field(default=False, description="Is this field required")
    min_length: Optional[int] = Field(None, description="Minimum field length")
    max_length: Optional[int] = Field(None, description="Maximum field length")
    expected_pattern: Optional[str] = Field(None, description="Expected regex pattern")
    allowed_values: List[str] = Field(
        default_factory=list, description="List of allowed values"
    )
    forbidden_patterns: List[str] = Field(
        default_factory=list, description="List of forbidden regex patterns"
    )
    entropy_threshold: Optional[float] = Field(
        None, description="Minimum entropy for security fields"
    )
    validator_function: Optional[str] = Field(
        None, description="Custom validator function name"
    )
    compliance_frameworks: List[ComplianceFramework] = Field(
        default_factory=list, description="Applicable compliance frameworks"
    )
    applies_to_environments: List[str] = Field(
        default_factory=list, description="Environments this rule applies to"
    )
    applies_to_services: List[str] = Field(
        default_factory=list, description="Services this rule applies to"
    )


class ValidationResult(BaseModel):
    """Result of a configuration validation run."""

    is_valid: bool = Field(..., description="Overall validation result")
    issues: List[ValidationIssue] = Field(..., description="List of validation issues")
    total_checks: int = Field(
        ..., description="Total number of validation checks performed"
    )
    passed_checks: int = Field(..., description="Number of checks that passed")
    failed_checks: int = Field(..., description="Number of checks that failed")
    critical_issues: int = Field(..., description="Number of critical issues")
    error_issues: int = Field(..., description="Number of error issues")
    warning_issues: int = Field(..., description="Number of warning issues")
    info_issues: int = Field(..., description="Number of info issues")
    compliance_status: dict = Field(
        default_factory=dict, description="Compliance status by framework"
    )
    validation_timestamp: str = Field(..., description="When validation was performed")
    environment: Optional[str] = Field(None, description="Environment validated")
    service: Optional[str] = Field(None, description="Service validated")
