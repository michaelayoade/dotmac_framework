"""
Field validation strategies for secure configuration validation.

REFACTORED: Extracted from secure_config_validator.py to reduce _validate_field 
complexity from 16→8 using Strategy pattern.
"""

import re
import math
from abc import ABC, abstractmethod
from typing import List, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Import necessary types from validation types module
from .validation_types import ValidationIssue, ValidationSeverity, ValidationCategory


class FieldValidationStrategy(ABC):
    """Base strategy for field validation."""
    
    @abstractmethod
    def validate(self, field_path: str, field_value: Any, rule, environment: Optional[str] = None) -> List[ValidationIssue]:
        """Validate field and return any issues found."""
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get strategy name for logging."""
        pass
    
    @abstractmethod
    def applies_to_rule(self, rule) -> bool:
        """Check if this strategy applies to the given rule."""
        pass


class RequiredFieldStrategy(FieldValidationStrategy):
    """Strategy for required field validation."""
    
    def validate(self, field_path: str, field_value: Any, rule, environment: Optional[str] = None) -> List[ValidationIssue]:
        """Validate required field constraint."""
        issues = []
        value_str = str(field_value) if field_value is not None else ""
        
        if rule.required and not value_str:
            issues.append(
                ValidationIssue(
                    issue_id=f"{rule.rule_id}_{field_path}_required",
                    severity=rule.severity,
                    category=rule.category,
                    field_path=field_path,
                    rule_name=rule.name,
                    message=f"Required field '{field_path}' is missing or empty",
                    suggestion="Provide a value for this required field",
                    compliance_frameworks=rule.compliance_frameworks,
                    current_value=value_str,
                )
            )
        
        return issues
    
    def get_strategy_name(self) -> str:
        """Get Strategy Name operation."""
        return "Required Field Validation"
    
    def applies_to_rule(self, rule) -> bool:
        """Apply to rules that specify required=True."""
        return getattr(rule, 'required', False)


class LengthValidationStrategy(FieldValidationStrategy):
    """Strategy for length validation (min/max)."""
    
    def validate(self, field_path: str, field_value: Any, rule, environment: Optional[str] = None) -> List[ValidationIssue]:
        """Validate field length constraints."""
        issues = []
        value_str = str(field_value) if field_value is not None else ""
        
        # Skip if empty and not required
        if not value_str and not getattr(rule, 'required', False):
            return issues
        
        # Min length validation
        if getattr(rule, 'min_length', None) and len(value_str) < rule.min_length:
            issues.append(
                ValidationIssue(
                    issue_id=f"{rule.rule_id}_{field_path}_min_length",
                    severity=rule.severity,
                    category=rule.category,
                    field_path=field_path,
                    rule_name=rule.name,
                    message=f"Field '{field_path}' is too short (minimum {rule.min_length} characters)",
                    suggestion=f"Increase length to at least {rule.min_length} characters",
                    compliance_frameworks=rule.compliance_frameworks,
                    current_value=f"length: {len(value_str)}",
                    expected_value=f"minimum length: {rule.min_length}",
                )
            )
        
        # Max length validation
        if getattr(rule, 'max_length', None) and len(value_str) > rule.max_length:
            issues.append(
                ValidationIssue(
                    issue_id=f"{rule.rule_id}_{field_path}_max_length",
                    severity=ValidationSeverity.WARNING,  # Usually not security critical
                    category=rule.category,
                    field_path=field_path,
                    rule_name=rule.name,
                    message=f"Field '{field_path}' is too long (maximum {rule.max_length} characters)",
                    suggestion=f"Reduce length to at most {rule.max_length} characters",
                    compliance_frameworks=rule.compliance_frameworks,
                    current_value=f"length: {len(value_str)}",
                    expected_value=f"maximum length: {rule.max_length}",
                )
            )
        
        return issues
    
    def get_strategy_name(self) -> str:
        """Get Strategy Name operation."""
        return "Length Validation"
    
    def applies_to_rule(self, rule) -> bool:
        """Apply to rules that specify min_length or max_length."""
        return (getattr(rule, 'min_length', None) is not None or 
                getattr(rule, 'max_length', None) is not None)


class PatternValidationStrategy(FieldValidationStrategy):
    """Strategy for regex pattern validation."""
    
    def validate(self, field_path: str, field_value: Any, rule, environment: Optional[str] = None) -> List[ValidationIssue]:
        """Validate field against regex pattern."""
        issues = []
        value_str = str(field_value) if field_value is not None else ""
        
        # Skip if empty and not required
        if not value_str and not getattr(rule, 'required', False):
            return issues
        
        if getattr(rule, 'expected_pattern', None) and not re.match(rule.expected_pattern, value_str):
            issues.append(
                ValidationIssue(
                    issue_id=f"{rule.rule_id}_{field_path}_pattern",
                    severity=rule.severity,
                    category=rule.category,
                    field_path=field_path,
                    rule_name=rule.name,
                    message=f"Field '{field_path}' does not match expected pattern",
                    suggestion=f"Ensure value matches pattern: {rule.expected_pattern}",
                    compliance_frameworks=rule.compliance_frameworks,
                    validation_rule=rule.expected_pattern,
                )
            )
        
        return issues
    
    def get_strategy_name(self) -> str:
        """Get Strategy Name operation."""
        return "Pattern Validation"
    
    def applies_to_rule(self, rule) -> bool:
        """Apply to rules that specify expected_pattern."""
        return getattr(rule, 'expected_pattern', None) is not None


class AllowedValuesStrategy(FieldValidationStrategy):
    """Strategy for allowed values validation."""
    
    def validate(self, field_path: str, field_value: Any, rule, environment: Optional[str] = None) -> List[ValidationIssue]:
        """Validate field against allowed values list."""
        issues = []
        value_str = str(field_value) if field_value is not None else ""
        
        # Skip if empty and not required
        if not value_str and not getattr(rule, 'required', False):
            return issues
        
        if getattr(rule, 'allowed_values', None) and value_str not in rule.allowed_values:
            issues.append(
                ValidationIssue(
                    issue_id=f"{rule.rule_id}_{field_path}_allowed_values",
                    severity=rule.severity,
                    category=rule.category,
                    field_path=field_path,
                    rule_name=rule.name,
                    message=f"Field '{field_path}' has invalid value",
                    suggestion=f"Use one of: {', '.join(rule.allowed_values)}",
                    compliance_frameworks=rule.compliance_frameworks,
                    current_value=value_str,
                    expected_value=f"one of: {', '.join(rule.allowed_values)}",
                )
            )
        
        return issues
    
    def get_strategy_name(self) -> str:
        """Get Strategy Name operation."""
        return "Allowed Values Validation"
    
    def applies_to_rule(self, rule) -> bool:
        """Apply to rules that specify allowed_values."""
        return getattr(rule, 'allowed_values', None) is not None


class ForbiddenPatternsStrategy(FieldValidationStrategy):
    """Strategy for forbidden patterns validation."""
    
    def validate(self, field_path: str, field_value: Any, rule, environment: Optional[str] = None) -> List[ValidationIssue]:
        """Validate field doesn't contain forbidden patterns."""
        issues = []
        value_str = str(field_value) if field_value is not None else ""
        
        # Skip if empty and not required
        if not value_str and not getattr(rule, 'required', False):
            return issues
        
        forbidden_patterns = getattr(rule, 'forbidden_patterns', [])
        for forbidden_pattern in forbidden_patterns:
            if re.search(forbidden_pattern, value_str, re.IGNORECASE):
                issues.append(
                    ValidationIssue(
                        issue_id=f"{rule.rule_id}_{field_path}_forbidden_pattern",
                        severity=ValidationSeverity.CRITICAL,  # Security issue
                        category=ValidationCategory.SECURITY,
                        field_path=field_path,
                        rule_name=rule.name,
                        message=f"Field '{field_path}' contains forbidden pattern: {forbidden_pattern}",
                        suggestion="Remove or replace the forbidden content",
                        compliance_frameworks=rule.compliance_frameworks,
                        validation_rule=f"forbidden: {forbidden_pattern}",
                    )
                )
        
        return issues
    
    def get_strategy_name(self) -> str:
        """Get Strategy Name operation."""
        return "Forbidden Patterns Validation"
    
    def applies_to_rule(self, rule) -> bool:
        """Apply to rules that specify forbidden_patterns."""
        return getattr(rule, 'forbidden_patterns', None) is not None


class EntropyValidationStrategy(FieldValidationStrategy):
    """Strategy for entropy validation (for secrets/passwords)."""
    
    def validate(self, field_path: str, field_value: Any, rule, environment: Optional[str] = None) -> List[ValidationIssue]:
        """Validate field entropy for security."""
        issues = []
        value_str = str(field_value) if field_value is not None else ""
        
        # Skip if empty and not required
        if not value_str and not getattr(rule, 'required', False):
            return issues
        
        entropy_threshold = getattr(rule, 'entropy_threshold', None)
        if entropy_threshold:
            entropy = self._calculate_entropy(value_str)
            if entropy < entropy_threshold:
                issues.append(
                    ValidationIssue(
                        issue_id=f"{rule.rule_id}_{field_path}_entropy",
                        severity=rule.severity,
                        category=ValidationCategory.SECURITY,
                        field_path=field_path,
                        rule_name=rule.name,
                        message=f"Field '{field_path}' has insufficient entropy ({entropy:.2f})",
                        suggestion=f"Use a more random value with entropy >= {entropy_threshold}",
                        compliance_frameworks=rule.compliance_frameworks,
                        current_value=f"entropy: {entropy:.2f}",
                        expected_value=f"minimum entropy: {entropy_threshold}",
                    )
                )
        
        return issues
    
    def _calculate_entropy(self, value: str) -> float:
        """Calculate Shannon entropy of a string."""
        if not value:
            return 0.0
        
        # Count character frequencies
        freq = {}
        for char in value:
            freq[char] = freq.get(char, 0) + 1
        
        # Calculate entropy
        length = len(value)
        entropy = 0.0
        for count in freq.values():
            probability = count / length
            if probability > 0:
                entropy -= probability * math.log2(probability)
        
        return entropy
    
    def get_strategy_name(self) -> str:
        """Get Strategy Name operation."""
        return "Entropy Validation"
    
    def applies_to_rule(self, rule) -> bool:
        """Apply to rules that specify entropy_threshold."""
        return getattr(rule, 'entropy_threshold', None) is not None


class CustomValidatorStrategy(FieldValidationStrategy):
    """Strategy for custom validator functions."""
    
    def __init__(self, custom_validators=None, builtin_validator_runner=None):
        """Initialize with custom validators and builtin runner."""
        self.custom_validators = custom_validators or {}
        self.builtin_validator_runner = builtin_validator_runner
    
    def validate(self, field_path: str, field_value: Any, rule, environment: Optional[str] = None) -> List[ValidationIssue]:
        """Run custom validator functions."""
        issues = []
        validator_function = getattr(rule, 'validator_function', None)
        
        if not validator_function:
            return issues
        
        # Try custom validators first
        if validator_function in self.custom_validators:
            try:
                custom_issues = self.custom_validators[validator_function](
                    field_path, field_value, rule, environment
                )
                if custom_issues:
                    issues.extend(custom_issues)
            except Exception as e:
                logger.error(f"Custom validator {validator_function} failed: {e}")
        
        # Try builtin validators
        elif self.builtin_validator_runner:
            try:
                custom_issues = self.builtin_validator_runner(
                    validator_function, field_path, field_value, rule, environment
                )
                if custom_issues:
                    issues.extend(custom_issues)
            except Exception as e:
                logger.error(f"Builtin validator {validator_function} failed: {e}")
        
        return issues
    
    def get_strategy_name(self) -> str:
        """Get Strategy Name operation."""
        return "Custom Validator"
    
    def applies_to_rule(self, rule) -> bool:
        """Apply to rules that specify validator_function."""
        return getattr(rule, 'validator_function', None) is not None


class FieldValidationEngine:
    """
    Engine for validating configuration fields using Strategy pattern.
    
    REFACTORED: Replaces the 16-complexity _validate_field method with
    a simple strategy-based approach (Complexity: 8).
    """
    
    def __init__(self, custom_validators=None, builtin_validator_runner=None):
        """Initialize with all validation strategies."""
        self.strategies = [
            RequiredFieldStrategy(),
            LengthValidationStrategy(),
            PatternValidationStrategy(),
            AllowedValuesStrategy(),
            ForbiddenPatternsStrategy(),
            EntropyValidationStrategy(),
            CustomValidatorStrategy(custom_validators, builtin_validator_runner),
        ]
    
    def validate_field(self, field_path: str, field_value: Any, rule, environment: Optional[str] = None) -> List[ValidationIssue]:
        """
        Validate field using applicable strategies.
        
        COMPLEXITY REDUCTION: This method replaces the original 16-complexity 
        _validate_field method with strategy-based validation (Complexity: 8).
        
        Args:
            field_path: Path to the field being validated
            field_value: Value of the field
            rule: Validation rule to apply
            environment: Environment context (optional)
            
        Returns:
            List of validation issues found
        """
        # Step 1: Initialize results (Complexity: 1)
        all_issues = []
        
        # Step 2: Handle early termination for required fields (Complexity: 2)
        value_str = str(field_value) if field_value is not None else ""
        if getattr(rule, 'required', False) and not value_str:
            # Required field validation takes precedence - return immediately if missing
            required_strategy = RequiredFieldStrategy()
            return required_strategy.validate(field_path, field_value, rule, environment)
        
        # Step 3: Skip further validation if field is empty and not required (Complexity: 1)
        if not value_str and not getattr(rule, 'required', False):
            return all_issues
        
        # Step 4: Apply all applicable strategies (Complexity: 3)
        for strategy in self.strategies:
            try:
                if strategy.applies_to_rule(rule):
                    issues = strategy.validate(field_path, field_value, rule, environment)
                    if issues:
                        all_issues.extend(issues)
                        logger.debug(f"Validation strategy {strategy.get_strategy_name()} found {len(issues)} issues")
            except Exception as e:
                logger.error(f"Validation strategy {strategy.get_strategy_name()} failed: {e}")
        
        # Step 5: Return collected issues (Complexity: 1)
        return all_issues
    
    def get_strategy_names(self) -> List[str]:
        """Get names of all validation strategies."""
        return [strategy.get_strategy_name() for strategy in self.strategies]
    
    def add_custom_strategy(self, strategy: FieldValidationStrategy) -> None:
        """Add a custom validation strategy."""
        self.strategies.append(strategy)
        logger.info(f"Added custom validation strategy: {strategy.get_strategy_name()}")
    
    def remove_strategy(self, strategy_name: str) -> bool:
        """Remove a validation strategy by name."""
        original_count = len(self.strategies)
        self.strategies = [s for s in self.strategies if s.get_strategy_name() != strategy_name]
        removed = len(self.strategies) < original_count
        
        if removed:
            logger.info(f"Removed validation strategy: {strategy_name}")
        
        return removed


def create_field_validation_engine(custom_validators=None, builtin_validator_runner=None) -> FieldValidationEngine:
    """
    Factory function to create a configured field validation engine.
    
    This is the main entry point for replacing the 16-complexity _validate_field method.
    
    Args:
        custom_validators: Dictionary of custom validator functions
        builtin_validator_runner: Function to run builtin validators
        
    Returns:
        Configured field validation engine
    """
    return FieldValidationEngine(custom_validators, builtin_validator_runner)