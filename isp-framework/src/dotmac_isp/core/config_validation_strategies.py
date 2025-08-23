"""
Configuration field validation strategies using Strategy pattern.
Replaces the 23-complexity _validate_field method with focused validation strategies.
"""

import re
import math
from abc import ABC, abstractmethod
from typing import Any, List, Optional, Dict, Callable
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ValidationSeverity(str, Enum):
    """Validation severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"  
    CRITICAL = "critical"


class ValidationCategory(str, Enum):
    """Validation categories."""
    SECURITY = "security"
    COMPLIANCE = "compliance"
    PERFORMANCE = "performance"
    CONFIGURATION = "configuration"


@dataclass
class ValidationRule:
    """Validation rule for type hints."""
    rule_id: str
    name: str
    severity: ValidationSeverity
    category: ValidationCategory
    field_patterns: List[str]
    compliance_frameworks: List[str] = None
    
    # Validation criteria
    required: bool = False
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    expected_pattern: Optional[str] = None
    allowed_values: Optional[List[str]] = None
    forbidden_patterns: List[str] = None
    entropy_threshold: Optional[float] = None
    validator_function: Optional[str] = None


@dataclass
class ValidationIssue:
    """Validation issue for type hints."""
    issue_id: str
    severity: ValidationSeverity
    category: ValidationCategory
    field_path: str
    rule_name: str
    message: str
    suggestion: str
    compliance_frameworks: List[str] = None
    current_value: str = ""
    expected_value: str = ""
    validation_rule: str = ""


class FieldValidationStrategy(ABC):
    """Base strategy for field validation."""
    
    @abstractmethod
    def validate(self, field_path: str, field_value: Any, rule: ValidationRule, 
                environment: Optional[str] = None) -> List[ValidationIssue]:
        """Validate field against this strategy's criteria."""
        pass


class RequiredFieldStrategy(FieldValidationStrategy):
    """Validate required field presence."""
    
    def validate(self, field_path: str, field_value: Any, rule: ValidationRule, 
                environment: Optional[str] = None) -> List[ValidationIssue]:
        """Check if required field is present and not empty."""
        if not rule.required:
            return []
        
        value_str = str(field_value) if field_value is not None else ""
        
        if not value_str:
            return [ValidationIssue(
                issue_id=f"{rule.rule_id}_{field_path}_required",
                severity=rule.severity,
                category=rule.category,
                field_path=field_path,
                rule_name=rule.name,
                message=f"Required field '{field_path}' is missing or empty",
                suggestion="Provide a value for this required field",
                compliance_frameworks=rule.compliance_frameworks or [],
                current_value=value_str,
            )]
        
        return []


class LengthValidationStrategy(FieldValidationStrategy):
    """Validate field length constraints."""
    
    def validate(self, field_path: str, field_value: Any, rule: ValidationRule,
                environment: Optional[str] = None) -> List[ValidationIssue]:
        """Check field length against min/max constraints."""
        if field_value is None:
            return []
        
        value_str = str(field_value)
        issues = []
        
        # Min length check
        if rule.min_length and len(value_str) < rule.min_length:
            issues.append(ValidationIssue(
                issue_id=f"{rule.rule_id}_{field_path}_min_length",
                severity=rule.severity,
                category=rule.category,
                field_path=field_path,
                rule_name=rule.name,
                message=f"Field '{field_path}' is too short (minimum {rule.min_length} characters)",
                suggestion=f"Increase length to at least {rule.min_length} characters",
                compliance_frameworks=rule.compliance_frameworks or [],
                current_value=f"length: {len(value_str)}",
                expected_value=f"minimum length: {rule.min_length}",
            ))
        
        # Max length check
        if rule.max_length and len(value_str) > rule.max_length:
            issues.append(ValidationIssue(
                issue_id=f"{rule.rule_id}_{field_path}_max_length",
                severity=ValidationSeverity.WARNING,
                category=rule.category,
                field_path=field_path,
                rule_name=rule.name,
                message=f"Field '{field_path}' is too long (maximum {rule.max_length} characters)",
                suggestion=f"Reduce length to at most {rule.max_length} characters",
                compliance_frameworks=rule.compliance_frameworks or [],
                current_value=f"length: {len(value_str)}",
                expected_value=f"maximum length: {rule.max_length}",
            ))
        
        return issues


class PatternValidationStrategy(FieldValidationStrategy):
    """Validate field against expected pattern."""
    
    def validate(self, field_path: str, field_value: Any, rule: ValidationRule,
                environment: Optional[str] = None) -> List[ValidationIssue]:
        """Check field matches expected regex pattern."""
        if not rule.expected_pattern or field_value is None:
            return []
        
        value_str = str(field_value)
        
        if not re.match(rule.expected_pattern, value_str):
            return [ValidationIssue(
                issue_id=f"{rule.rule_id}_{field_path}_pattern",
                severity=rule.severity,
                category=rule.category,
                field_path=field_path,
                rule_name=rule.name,
                message=f"Field '{field_path}' does not match expected pattern",
                suggestion=f"Ensure value matches pattern: {rule.expected_pattern}",
                compliance_frameworks=rule.compliance_frameworks or [],
                validation_rule=rule.expected_pattern,
            )]
        
        return []


class AllowedValuesStrategy(FieldValidationStrategy):
    """Validate field against allowed values list."""
    
    def validate(self, field_path: str, field_value: Any, rule: ValidationRule,
                environment: Optional[str] = None) -> List[ValidationIssue]:
        """Check field value is in allowed values list."""
        if not rule.allowed_values or field_value is None:
            return []
        
        value_str = str(field_value)
        
        if value_str not in rule.allowed_values:
            return [ValidationIssue(
                issue_id=f"{rule.rule_id}_{field_path}_allowed_values",
                severity=rule.severity,
                category=rule.category,
                field_path=field_path,
                rule_name=rule.name,
                message=f"Field '{field_path}' has invalid value",
                suggestion=f"Use one of: {', '.join(rule.allowed_values)}",
                compliance_frameworks=rule.compliance_frameworks or [],
                current_value=value_str,
                expected_value=f"one of: {', '.join(rule.allowed_values)}",
            )]
        
        return []


class ForbiddenPatternsStrategy(FieldValidationStrategy):
    """Validate field against forbidden patterns."""
    
    def validate(self, field_path: str, field_value: Any, rule: ValidationRule,
                environment: Optional[str] = None) -> List[ValidationIssue]:
        """Check field doesn't contain forbidden patterns."""
        if not rule.forbidden_patterns or field_value is None:
            return []
        
        value_str = str(field_value)
        issues = []
        
        for forbidden_pattern in rule.forbidden_patterns:
            if re.search(forbidden_pattern, value_str, re.IGNORECASE):
                issues.append(ValidationIssue(
                    issue_id=f"{rule.rule_id}_{field_path}_forbidden_pattern",
                    severity=ValidationSeverity.CRITICAL,
                    category=ValidationCategory.SECURITY,
                    field_path=field_path,
                    rule_name=rule.name,
                    message=f"Field '{field_path}' contains forbidden pattern: {forbidden_pattern}",
                    suggestion="Remove or replace the forbidden content",
                    compliance_frameworks=rule.compliance_frameworks or [],
                    validation_rule=f"forbidden: {forbidden_pattern}",
                ))
        
        return issues


class EntropyValidationStrategy(FieldValidationStrategy):
    """Validate field entropy (for secrets/passwords)."""
    
    def validate(self, field_path: str, field_value: Any, rule: ValidationRule,
                environment: Optional[str] = None) -> List[ValidationIssue]:
        """Check field has sufficient entropy."""
        if not rule.entropy_threshold or field_value is None:
            return []
        
        value_str = str(field_value)
        entropy = self._calculate_entropy(value_str)
        
        if entropy < rule.entropy_threshold:
            return [ValidationIssue(
                issue_id=f"{rule.rule_id}_{field_path}_entropy",
                severity=rule.severity,
                category=ValidationCategory.SECURITY,
                field_path=field_path,
                rule_name=rule.name,
                message=f"Field '{field_path}' has insufficient entropy ({entropy:.2f})",
                suggestion=f"Use a more random value with entropy >= {rule.entropy_threshold}",
                compliance_frameworks=rule.compliance_frameworks or [],
                current_value=f"entropy: {entropy:.2f}",
                expected_value=f"minimum entropy: {rule.entropy_threshold}",
            )]
        
        return []
    
    def _calculate_entropy(self, value: str) -> float:
        """Calculate Shannon entropy of string."""
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
            entropy -= probability * math.log2(probability)
        
        return entropy


class CustomValidationStrategy(FieldValidationStrategy):
    """Execute custom validation functions."""
    
    def __init__(self, custom_validators: Dict[str, Callable] = None):
        """Initialize with custom validators."""
        self.custom_validators = custom_validators or {}
    
    def validate(self, field_path: str, field_value: Any, rule: ValidationRule,
                environment: Optional[str] = None) -> List[ValidationIssue]:
        """Run custom validation function if specified."""
        if not rule.validator_function or rule.validator_function not in self.custom_validators:
            return []
        
        try:
            custom_issues = self.custom_validators[rule.validator_function](
                field_path, field_value, rule, environment
            )
            return custom_issues if custom_issues else []
        except Exception as e:
            logger.error(f"Custom validator {rule.validator_function} failed: {e}")
            return [ValidationIssue(
                issue_id=f"{rule.rule_id}_{field_path}_custom_validator_error",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.CONFIGURATION,
                field_path=field_path,
                rule_name=rule.name,
                message=f"Custom validator '{rule.validator_function}' failed: {str(e)}",
                suggestion="Check custom validation function implementation",
                compliance_frameworks=rule.compliance_frameworks or [],
            )]


class FieldValidationOrchestrator:
    """
    Field validation orchestrator using Strategy pattern.
    
    REFACTORED: Replaces 23-complexity _validate_field method with 
    focused, testable validation strategies (Complexity: 3).
    """
    
    def __init__(self, custom_validators: Dict[str, Callable] = None):
        """Initialize with validation strategies."""
        self.strategies = [
            RequiredFieldStrategy(),
            LengthValidationStrategy(),
            PatternValidationStrategy(),
            AllowedValuesStrategy(),
            ForbiddenPatternsStrategy(),
            EntropyValidationStrategy(),
            CustomValidationStrategy(custom_validators),
        ]
    
    def validate_field(self, field_path: str, field_value: Any, rule: ValidationRule,
                      environment: Optional[str] = None) -> List[ValidationIssue]:
        """
        Validate field using all applicable strategies.
        
        COMPLEXITY REDUCTION: This method replaces the original 23-complexity 
        method with a simple iteration over strategies (Complexity: 3).
        
        Args:
            field_path: Path to the field being validated
            field_value: Value to validate
            rule: Validation rule to apply
            environment: Optional environment context
            
        Returns:
            List of validation issues found
        """
        # Step 1: Early return for empty non-required fields (Complexity: 1)
        value_str = str(field_value) if field_value is not None else ""
        if not value_str and not rule.required:
            return []
        
        # Step 2: Apply all validation strategies (Complexity: 1)
        all_issues = []
        for strategy in self.strategies:
            issues = strategy.validate(field_path, field_value, rule, environment)
            all_issues.extend(issues)
            
            # Early exit if required field is missing (no point in further validation)
            if issues and any(issue.issue_id.endswith('_required') for issue in issues):
                return issues
        
        # Step 3: Return collected issues (Complexity: 1)
        return all_issues
    
    def add_validation_strategy(self, strategy: FieldValidationStrategy) -> None:
        """Add a custom validation strategy."""
        self.strategies.append(strategy)
    
    def remove_validation_strategy(self, strategy_class: type) -> bool:
        """Remove a validation strategy by class type."""
        original_count = len(self.strategies)
        self.strategies = [s for s in self.strategies if not isinstance(s, strategy_class)]
        return len(self.strategies) < original_count
    
    def get_active_strategies(self) -> List[str]:
        """Get list of active validation strategy names."""
        return [strategy.__class__.__name__ for strategy in self.strategies]


def create_field_validation_orchestrator(custom_validators: Dict[str, Callable] = None) -> FieldValidationOrchestrator:
    """
    Factory function to create a configured field validation orchestrator.
    
    This is the main entry point for replacing the 23-complexity method.
    """
    return FieldValidationOrchestrator(custom_validators)