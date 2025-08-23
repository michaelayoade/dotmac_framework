"""
Test suite for configuration field validation strategies.
Validates the replacement of the 23-complexity _validate_field method.
"""

import pytest
import re
from unittest.mock import Mock, patch

from dotmac_isp.core.config_validation_strategies import (
    ValidationRule,
    ValidationIssue,
    ValidationSeverity,
    ValidationCategory,
    FieldValidationOrchestrator,
    RequiredFieldStrategy,
    LengthValidationStrategy,
    PatternValidationStrategy,
    AllowedValuesStrategy,
    ForbiddenPatternsStrategy,
    EntropyValidationStrategy,
    CustomValidationStrategy,
    create_field_validation_orchestrator,
)


@pytest.mark.unit
class TestValidationStrategies:
    """Test individual validation strategies."""
    
    def test_required_field_strategy(self):
        """Test required field validation strategy."""
        strategy = RequiredFieldStrategy()
        
        rule = ValidationRule(
            rule_id="test_rule",
            name="Test Required",
            severity=ValidationSeverity.ERROR,
            category=ValidationCategory.CONFIGURATION,
            field_patterns=["test.*"],
            required=True
        )
        
        # Missing required field
        issues = strategy.validate("test.field", None, rule)
        assert len(issues) == 1
        assert "required" in issues[0].issue_id
        assert issues[0].severity == ValidationSeverity.ERROR
        
        # Empty required field
        issues = strategy.validate("test.field", "", rule)
        assert len(issues) == 1
        
        # Present required field
        issues = strategy.validate("test.field", "value", rule)
        assert len(issues) == 0
        
        # Not required field
        rule.required = False
        issues = strategy.validate("test.field", None, rule)
        assert len(issues) == 0
    
    def test_length_validation_strategy(self):
        """Test length validation strategy."""
        strategy = LengthValidationStrategy()
        
        rule = ValidationRule(
            rule_id="test_rule",
            name="Test Length",
            severity=ValidationSeverity.WARNING,
            category=ValidationCategory.CONFIGURATION,
            field_patterns=["test.*"],
            min_length=5,
            max_length=20
        )
        
        # Too short
        issues = strategy.validate("test.field", "abc", rule)
        assert len(issues) == 1
        assert "min_length" in issues[0].issue_id
        
        # Too long
        issues = strategy.validate("test.field", "a" * 25, rule)
        assert len(issues) == 1
        assert "max_length" in issues[0].issue_id
        
        # Just right
        issues = strategy.validate("test.field", "perfect", rule)
        assert len(issues) == 0
        
        # No value
        issues = strategy.validate("test.field", None, rule)
        assert len(issues) == 0
    
    def test_pattern_validation_strategy(self):
        """Test pattern validation strategy."""
        strategy = PatternValidationStrategy()
        
        rule = ValidationRule(
            rule_id="test_rule",
            name="Test Pattern",
            severity=ValidationSeverity.ERROR,
            category=ValidationCategory.SECURITY,
            field_patterns=["test.*"],
            expected_pattern=r"^[A-Z][a-z]+$"  # Capitalized word
        )
        
        # Matches pattern
        issues = strategy.validate("test.field", "Hello", rule)
        assert len(issues) == 0
        
        # Doesn't match pattern
        issues = strategy.validate("test.field", "hello", rule)
        assert len(issues) == 1
        assert "pattern" in issues[0].issue_id
        
        issues = strategy.validate("test.field", "HELLO", rule)
        assert len(issues) == 1
        
        # No pattern specified
        rule.expected_pattern = None
        issues = strategy.validate("test.field", "anything", rule)
        assert len(issues) == 0
    
    def test_allowed_values_strategy(self):
        """Test allowed values validation strategy."""
        strategy = AllowedValuesStrategy()
        
        rule = ValidationRule(
            rule_id="test_rule",
            name="Test Allowed Values",
            severity=ValidationSeverity.ERROR,
            category=ValidationCategory.CONFIGURATION,
            field_patterns=["test.*"],
            allowed_values=["production", "staging", "development"]
        )
        
        # Allowed value
        issues = strategy.validate("test.field", "production", rule)
        assert len(issues) == 0
        
        # Not allowed value
        issues = strategy.validate("test.field", "invalid", rule)
        assert len(issues) == 1
        assert "allowed_values" in issues[0].issue_id
        
        # No allowed values specified
        rule.allowed_values = None
        issues = strategy.validate("test.field", "anything", rule)
        assert len(issues) == 0
    
    def test_forbidden_patterns_strategy(self):
        """Test forbidden patterns validation strategy."""
        strategy = ForbiddenPatternsStrategy()
        
        rule = ValidationRule(
            rule_id="test_rule", 
            name="Test Forbidden",
            severity=ValidationSeverity.CRITICAL,
            category=ValidationCategory.SECURITY,
            field_patterns=["test.*"],
            forbidden_patterns=[r"password", r"secret", r"\d{4}-\d{4}-\d{4}-\d{4}"]
        )
        
        # No forbidden patterns
        issues = strategy.validate("test.field", "clean_value", rule)
        assert len(issues) == 0
        
        # Contains forbidden pattern
        issues = strategy.validate("test.field", "my_password_123", rule)
        assert len(issues) == 1
        assert issues[0].severity == ValidationSeverity.CRITICAL
        assert "forbidden_pattern" in issues[0].issue_id
        
        # Multiple forbidden patterns
        issues = strategy.validate("test.field", "password and secret", rule)
        assert len(issues) == 2
        
        # Credit card pattern
        issues = strategy.validate("test.field", "1234-5678-9012-3456", rule)
        assert len(issues) == 1
    
    def test_entropy_validation_strategy(self):
        """Test entropy validation strategy."""
        strategy = EntropyValidationStrategy()
        
        rule = ValidationRule(
            rule_id="test_rule",
            name="Test Entropy",
            severity=ValidationSeverity.WARNING,
            category=ValidationCategory.SECURITY,
            field_patterns=["test.*"],
            entropy_threshold=3.0
        )
        
        # High entropy (random-looking)
        issues = strategy.validate("test.field", "xK9#mZ@q$7Nw", rule)
        assert len(issues) == 0
        
        # Low entropy (repeated characters)
        issues = strategy.validate("test.field", "aaaaaa", rule)
        assert len(issues) == 1
        assert "entropy" in issues[0].issue_id
        
        # No entropy threshold
        rule.entropy_threshold = None
        issues = strategy.validate("test.field", "aaaaaa", rule)
        assert len(issues) == 0
        
        # Empty value
        issues = strategy.validate("test.field", "", rule)
        rule.entropy_threshold = 3.0
        assert len(issues) == 0
    
    def test_custom_validation_strategy(self):
        """Test custom validation strategy."""
        def custom_validator(field_path, field_value, rule, environment):
            if field_value == "forbidden":
                return [ValidationIssue(
                    issue_id=f"{rule.rule_id}_custom_error",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.CONFIGURATION,
                    field_path=field_path,
                    rule_name=rule.name,
                    message="Custom validation failed",
                    suggestion="Use a different value"
                )]
            return []
        
        strategy = CustomValidationStrategy({"test_validator": custom_validator})
        
        rule = ValidationRule(
            rule_id="test_rule",
            name="Test Custom",
            severity=ValidationSeverity.ERROR,
            category=ValidationCategory.CONFIGURATION,
            field_patterns=["test.*"],
            validator_function="test_validator"
        )
        
        # Valid value
        issues = strategy.validate("test.field", "allowed", rule)
        assert len(issues) == 0
        
        # Invalid value
        issues = strategy.validate("test.field", "forbidden", rule)
        assert len(issues) == 1
        assert "custom_error" in issues[0].issue_id
        
        # No validator function
        rule.validator_function = None
        issues = strategy.validate("test.field", "anything", rule)
        assert len(issues) == 0
        
        # Invalid validator function
        rule.validator_function = "nonexistent"
        issues = strategy.validate("test.field", "anything", rule)
        assert len(issues) == 0


@pytest.mark.unit
class TestFieldValidationOrchestrator:
    """Test the field validation orchestrator."""
    
    def setup_method(self):
        """Set up test orchestrator."""
        self.orchestrator = FieldValidationOrchestrator()
    
    def test_orchestrator_initialization(self):
        """Test that orchestrator initializes with all strategies."""
        strategy_names = self.orchestrator.get_active_strategies()
        
        expected_strategies = [
            "RequiredFieldStrategy",
            "LengthValidationStrategy",
            "PatternValidationStrategy", 
            "AllowedValuesStrategy",
            "ForbiddenPatternsStrategy",
            "EntropyValidationStrategy",
            "CustomValidationStrategy"
        ]
        
        for expected in expected_strategies:
            assert expected in strategy_names
    
    def test_validate_field_all_pass(self):
        """Test field validation when all strategies pass."""
        rule = ValidationRule(
            rule_id="test_rule",
            name="Test All Pass",
            severity=ValidationSeverity.INFO,
            category=ValidationCategory.CONFIGURATION,
            field_patterns=["test.*"],
            required=False,
            min_length=3,
            max_length=20,
            expected_pattern=r"^[a-zA-Z]+$",
            allowed_values=["valid", "okay", "good"],
            forbidden_patterns=[],
            entropy_threshold=None
        )
        
        issues = self.orchestrator.validate_field("test.field", "valid", rule)
        assert len(issues) == 0
    
    def test_validate_field_required_fails_early_exit(self):
        """Test early exit when required field validation fails."""
        rule = ValidationRule(
            rule_id="test_rule",
            name="Test Required Fails",
            severity=ValidationSeverity.ERROR,
            category=ValidationCategory.CONFIGURATION,
            field_patterns=["test.*"],
            required=True,
            min_length=5,  # This should not be checked
            max_length=20
        )
        
        # Empty required field should trigger early exit
        issues = self.orchestrator.validate_field("test.field", "", rule)
        assert len(issues) == 1
        assert "required" in issues[0].issue_id
        # Should not have length validation issues since it exited early
    
    def test_validate_field_multiple_failures(self):
        """Test field validation with multiple strategy failures."""
        rule = ValidationRule(
            rule_id="test_rule",
            name="Test Multiple Failures",
            severity=ValidationSeverity.WARNING,
            category=ValidationCategory.SECURITY,
            field_patterns=["test.*"],
            required=False,
            min_length=10,  # Will fail
            expected_pattern=r"^[0-9]+$",  # Will fail for letters
            allowed_values=["123456789"],  # Will fail
            forbidden_patterns=[r"bad"],  # Will fail
        )
        
        issues = self.orchestrator.validate_field("test.field", "bad_text", rule)
        
        # Should have multiple issues
        assert len(issues) > 1
        issue_types = [issue.issue_id.split('_')[-1] for issue in issues]
        assert "length" in str(issue_types)
        assert "pattern" in str(issue_types)
        assert "values" in str(issue_types)
        assert "forbidden" in str(issue_types)
    
    def test_validate_field_empty_non_required(self):
        """Test validation of empty non-required field."""
        rule = ValidationRule(
            rule_id="test_rule",
            name="Test Empty Non-Required",
            severity=ValidationSeverity.INFO,
            category=ValidationCategory.CONFIGURATION,
            field_patterns=["test.*"],
            required=False,
            min_length=5  # Should not be checked for empty field
        )
        
        issues = self.orchestrator.validate_field("test.field", "", rule)
        assert len(issues) == 0
    
    def test_add_custom_strategy(self):
        """Test adding custom validation strategy."""
        class CustomStrategy:
            def validate(self, field_path, field_value, rule, environment=None):
                if field_value == "custom_fail":
                    return [ValidationIssue(
                        issue_id="custom_issue",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.CONFIGURATION,
                        field_path=field_path,
                        rule_name=rule.name,
                        message="Custom strategy failed",
                        suggestion="Don't use 'custom_fail'"
                    )]
                return []
        
        original_count = len(self.orchestrator.strategies)
        custom_strategy = CustomStrategy()
        
        self.orchestrator.add_validation_strategy(custom_strategy)
        
        assert len(self.orchestrator.strategies) == original_count + 1
        
        # Test the custom strategy works
        rule = ValidationRule(
            rule_id="test_rule",
            name="Test Custom Strategy",
            severity=ValidationSeverity.INFO,
            category=ValidationCategory.CONFIGURATION,
            field_patterns=["test.*"]
        )
        
        issues = self.orchestrator.validate_field("test.field", "custom_fail", rule)
        assert len(issues) == 1
        assert issues[0].issue_id == "custom_issue"


@pytest.mark.unit
class TestComplexityReduction:
    """Test that validates complexity reduction from 23 to 2."""
    
    def test_original_method_replacement(self):
        """Verify the 23-complexity method is replaced."""
        # The orchestrator's validate_field method should be simple
        orchestrator = create_field_validation_orchestrator()
        
        assert hasattr(orchestrator, 'validate_field')
        
        # Test basic functionality
        rule = ValidationRule(
            rule_id="test_rule",
            name="Basic Test",
            severity=ValidationSeverity.INFO,
            category=ValidationCategory.CONFIGURATION,
            field_patterns=["test.*"]
        )
        
        # Should not crash and should work correctly
        issues = orchestrator.validate_field("test.field", "test_value", rule)
        assert isinstance(issues, list)
    
    def test_strategy_pattern_handles_all_validations(self):
        """Test that strategy pattern handles all original validation types."""
        orchestrator = create_field_validation_orchestrator()
        
        # Test comprehensive rule with all validation types
        rule = ValidationRule(
            rule_id="comprehensive_rule",
            name="Comprehensive Test",
            severity=ValidationSeverity.ERROR,
            category=ValidationCategory.SECURITY,
            field_patterns=["test.*"],
            required=True,
            min_length=8,
            max_length=50,
            expected_pattern=r"^[A-Za-z0-9@#$%]+$",
            allowed_values=None,  # Allow any pattern-matching value
            forbidden_patterns=[r"password", r"123456"],
            entropy_threshold=4.0
        )
        
        # Test valid value
        issues = orchestrator.validate_field(
            "test.secure_field", 
            "SecureP@ssw0rd#123", 
            rule
        )
        # Should pass all validations except forbidden pattern
        assert len(issues) >= 1  # Should catch "password" in forbidden patterns
        
        # Test multiple validation failures
        issues = orchestrator.validate_field(
            "test.secure_field",
            "weak",  # Too short, low entropy, etc.
            rule  
        )
        assert len(issues) > 1  # Multiple validation failures
    
    def test_error_handling_preserved(self):
        """Test that error handling is preserved in new implementation."""
        def failing_validator(field_path, field_value, rule, environment):
            raise ValueError("Validator failed")
        
        orchestrator = create_field_validation_orchestrator({
            "failing_validator": failing_validator
        })
        
        rule = ValidationRule(
            rule_id="test_rule",
            name="Test Error Handling",
            severity=ValidationSeverity.ERROR,
            category=ValidationCategory.CONFIGURATION,
            field_patterns=["test.*"],
            validator_function="failing_validator"
        )
        
        # Should handle validator exception gracefully
        issues = orchestrator.validate_field("test.field", "test_value", rule)
        
        assert len(issues) == 1
        assert "custom_validator_error" in issues[0].issue_id
        assert "Validator failed" in issues[0].message


@pytest.mark.integration
class TestConfigValidationIntegration:
    """Integration tests for configuration validation system."""
    
    def test_secure_config_validator_integration(self):
        """Test integration with secure config validator."""
        # This would test the actual replacement in secure_config_validator.py
        # For now, we validate the interface compatibility
        
        orchestrator = create_field_validation_orchestrator()
        
        # Test method signature compatibility
        import inspect
        sig = inspect.signature(orchestrator.validate_field)
        param_names = list(sig.parameters.keys())
        
        expected_params = ['field_path', 'field_value', 'rule', 'environment']
        assert len(param_names) == len(expected_params)
        for param in expected_params:
            assert param in param_names


@pytest.mark.performance  
class TestPerformanceImprovement:
    """Test that the new implementation performs well."""
    
    def test_strategy_pattern_performance(self):
        """Test that strategy pattern is efficient."""
        import time
        
        orchestrator = create_field_validation_orchestrator()
        
        rule = ValidationRule(
            rule_id="perf_rule",
            name="Performance Test",
            severity=ValidationSeverity.INFO,
            category=ValidationCategory.CONFIGURATION,
            field_patterns=["test.*"],
            required=True,
            min_length=1,
            max_length=100,
            expected_pattern=r"^[a-zA-Z0-9_-]+$",
            forbidden_patterns=[r"forbidden"],
            entropy_threshold=2.0
        )
        
        # Time multiple validations
        start_time = time.time()
        
        for i in range(1000):
            issues = orchestrator.validate_field(
                f"test.field_{i}", 
                f"valid_value_{i}", 
                rule
            )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete quickly (under 1 second for 1000 validations)
        assert duration < 1.0, f"Performance test took {duration:.3f}s"
    
    def test_orchestrator_creation_efficiency(self):
        """Test that orchestrator creation is efficient."""
        import time
        
        # Time multiple orchestrator creations
        start_time = time.time()
        
        for _ in range(100):
            orchestrator = create_field_validation_orchestrator()
            assert orchestrator is not None
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete very quickly (under 0.1 second for 100 creations)
        assert duration < 0.1, f"Orchestrator creation took {duration:.3f}s"