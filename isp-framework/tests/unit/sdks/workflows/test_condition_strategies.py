"""
Tests for workflow automation condition strategies.

REFACTORED: Tests for the strategy pattern implementation that replaced
the 14-complexity if-elif chain in ConditionEvaluator.evaluate_condition.
"""

import pytest
import re
from unittest.mock import Mock, patch

from dotmac_isp.sdks.workflows.condition_strategies import (
    ConditionStrategy,
    EqualsStrategy,
    NotEqualsStrategy,
    GreaterThanStrategy,
    LessThanStrategy,
    GreaterEqualStrategy,
    LessEqualStrategy,
    ContainsStrategy,
    NotContainsStrategy,
    InStrategy,
    NotInStrategy,
    ExistsStrategy,
    NotExistsStrategy,
    RegexStrategy,
    ConditionEvaluationEngine,
    create_condition_engine,
)
from dotmac_isp.sdks.workflows.automation import ConditionOperator


class TestConditionStrategies:
    """Test individual condition strategies."""

    def test_equals_strategy(self):
        """Test equals strategy."""
        strategy = EqualsStrategy()
        
        assert strategy.evaluate("test", "test") is True
        assert strategy.evaluate("test", "other") is False
        assert strategy.evaluate(42, 42) is True
        assert strategy.evaluate(42, 43) is False
        assert strategy.get_operator_name() == "equals"

    def test_not_equals_strategy(self):
        """Test not equals strategy."""
        strategy = NotEqualsStrategy()
        
        assert strategy.evaluate("test", "other") is True
        assert strategy.evaluate("test", "test") is False
        assert strategy.evaluate(42, 43) is True
        assert strategy.evaluate(42, 42) is False
        assert strategy.get_operator_name() == "not_equals"

    def test_greater_than_strategy(self):
        """Test greater than strategy."""
        strategy = GreaterThanStrategy()
        
        assert strategy.evaluate(10, 5) is True
        assert strategy.evaluate(5, 10) is False
        assert strategy.evaluate(5, 5) is False
        assert strategy.get_operator_name() == "greater_than"
        
        # Test type error handling
        with patch('dotmac_isp.sdks.workflows.condition_strategies.logger') as mock_logger:
            result = strategy.evaluate("text", 5)
            assert result is False
            mock_logger.warning.assert_called_once()

    def test_less_than_strategy(self):
        """Test less than strategy."""
        strategy = LessThanStrategy()
        
        assert strategy.evaluate(5, 10) is True
        assert strategy.evaluate(10, 5) is False
        assert strategy.evaluate(5, 5) is False
        assert strategy.get_operator_name() == "less_than"

    def test_greater_equal_strategy(self):
        """Test greater than or equal strategy."""
        strategy = GreaterEqualStrategy()
        
        assert strategy.evaluate(10, 5) is True
        assert strategy.evaluate(5, 5) is True
        assert strategy.evaluate(5, 10) is False
        assert strategy.get_operator_name() == "greater_equal"

    def test_less_equal_strategy(self):
        """Test less than or equal strategy."""
        strategy = LessEqualStrategy()
        
        assert strategy.evaluate(5, 10) is True
        assert strategy.evaluate(5, 5) is True
        assert strategy.evaluate(10, 5) is False
        assert strategy.get_operator_name() == "less_equal"

    def test_contains_strategy(self):
        """Test contains strategy."""
        strategy = ContainsStrategy()
        
        assert strategy.evaluate("hello world", "world") is True
        assert strategy.evaluate("hello world", "foo") is False
        assert strategy.evaluate([1, 2, 3], "2") is True  # String conversion
        assert strategy.get_operator_name() == "contains"

    def test_not_contains_strategy(self):
        """Test not contains strategy."""
        strategy = NotContainsStrategy()
        
        assert strategy.evaluate("hello world", "foo") is True
        assert strategy.evaluate("hello world", "world") is False
        assert strategy.get_operator_name() == "not_contains"

    def test_in_strategy(self):
        """Test 'in' strategy."""
        strategy = InStrategy()
        
        assert strategy.evaluate("apple", ["apple", "banana", "cherry"]) is True
        assert strategy.evaluate("grape", ["apple", "banana", "cherry"]) is False
        assert strategy.evaluate(2, [1, 2, 3]) is True
        assert strategy.get_operator_name() == "in"

    def test_not_in_strategy(self):
        """Test 'not in' strategy."""
        strategy = NotInStrategy()
        
        assert strategy.evaluate("grape", ["apple", "banana", "cherry"]) is True
        assert strategy.evaluate("apple", ["apple", "banana", "cherry"]) is False
        assert strategy.get_operator_name() == "not_in"

    def test_exists_strategy(self):
        """Test exists strategy."""
        strategy = ExistsStrategy()
        
        assert strategy.evaluate("value", None) is True  # expected_value ignored
        assert strategy.evaluate(0, None) is True
        assert strategy.evaluate("", None) is True
        assert strategy.evaluate(None, None) is False
        assert strategy.get_operator_name() == "exists"

    def test_not_exists_strategy(self):
        """Test not exists strategy."""
        strategy = NotExistsStrategy()
        
        assert strategy.evaluate(None, None) is True  # expected_value ignored
        assert strategy.evaluate("value", None) is False
        assert strategy.evaluate(0, None) is False
        assert strategy.get_operator_name() == "not_exists"

    def test_regex_strategy(self):
        """Test regex strategy."""
        strategy = RegexStrategy()
        
        assert strategy.evaluate("hello@example.com", r".*@.*\.com") is True
        assert strategy.evaluate("invalid-email", r".*@.*\.com") is False
        assert strategy.evaluate("test123", r"\d+") is True
        assert strategy.get_operator_name() == "regex"
        
        # Test regex error handling
        with patch('dotmac_isp.sdks.workflows.condition_strategies.logger') as mock_logger:
            result = strategy.evaluate("test", "[invalid regex")
            assert result is False
            mock_logger.warning.assert_called_once()


class TestConditionEvaluationEngine:
    """Test condition evaluation engine."""

    def test_engine_initialization(self):
        """Test engine initializes with all strategies."""
        engine = ConditionEvaluationEngine()
        
        # Verify all operators are supported
        expected_operators = [
            ConditionOperator.EQUALS,
            ConditionOperator.NOT_EQUALS,
            ConditionOperator.GREATER_THAN,
            ConditionOperator.LESS_THAN,
            ConditionOperator.GREATER_EQUAL,
            ConditionOperator.LESS_EQUAL,
            ConditionOperator.CONTAINS,
            ConditionOperator.NOT_CONTAINS,
            ConditionOperator.IN,
            ConditionOperator.NOT_IN,
            ConditionOperator.EXISTS,
            ConditionOperator.NOT_EXISTS,
            ConditionOperator.REGEX,
        ]
        
        supported_operators = engine.get_supported_operators()
        for operator in expected_operators:
            assert operator in supported_operators

    def test_evaluate_condition_equals(self):
        """Test condition evaluation with equals operator."""
        engine = ConditionEvaluationEngine()
        
        result = engine.evaluate_condition(
            ConditionOperator.EQUALS, "test", "test"
        )
        assert result is True
        
        result = engine.evaluate_condition(
            ConditionOperator.EQUALS, "test", "other"
        )
        assert result is False

    def test_evaluate_condition_greater_than(self):
        """Test condition evaluation with greater than operator."""
        engine = ConditionEvaluationEngine()
        
        result = engine.evaluate_condition(
            ConditionOperator.GREATER_THAN, 10, 5
        )
        assert result is True
        
        result = engine.evaluate_condition(
            ConditionOperator.GREATER_THAN, 5, 10
        )
        assert result is False

    def test_evaluate_condition_contains(self):
        """Test condition evaluation with contains operator."""
        engine = ConditionEvaluationEngine()
        
        result = engine.evaluate_condition(
            ConditionOperator.CONTAINS, "hello world", "world"
        )
        assert result is True
        
        result = engine.evaluate_condition(
            ConditionOperator.CONTAINS, "hello world", "foo"
        )
        assert result is False

    def test_evaluate_condition_regex(self):
        """Test condition evaluation with regex operator."""
        engine = ConditionEvaluationEngine()
        
        result = engine.evaluate_condition(
            ConditionOperator.REGEX, "test@example.com", r".*@.*\.com"
        )
        assert result is True
        
        result = engine.evaluate_condition(
            ConditionOperator.REGEX, "invalid-email", r".*@.*\.com"
        )
        assert result is False

    def test_evaluate_condition_unknown_operator(self):
        """Test evaluation with unknown operator raises error."""
        engine = ConditionEvaluationEngine()
        
        with pytest.raises(ValueError, match="Unknown operator"):
            engine.evaluate_condition("unknown_operator", "value", "expected")

    def test_evaluate_condition_with_exception(self):
        """Test evaluation handles exceptions gracefully."""
        engine = ConditionEvaluationEngine()
        
        # Mock strategy that raises exception
        mock_strategy = Mock()
        mock_strategy.evaluate.side_effect = Exception("Test error")
        mock_strategy.get_operator_name.return_value = "test_strategy"
        engine.strategies[ConditionOperator.EQUALS] = mock_strategy
        
        with patch('dotmac_isp.sdks.workflows.condition_strategies.logger') as mock_logger:
            result = engine.evaluate_condition(
                ConditionOperator.EQUALS, "value", "expected"
            )
            assert result is False
            mock_logger.error.assert_called_once()

    def test_add_custom_strategy(self):
        """Test adding custom strategy."""
        engine = ConditionEvaluationEngine()
        
        # Create custom strategy
        custom_strategy = Mock(spec=ConditionStrategy)
        custom_strategy.get_operator_name.return_value = "custom"
        
        # Add custom strategy
        engine.add_custom_strategy("custom_op", custom_strategy)
        
        assert "custom_op" in engine.strategies
        assert engine.strategies["custom_op"] == custom_strategy

    def test_remove_strategy(self):
        """Test removing strategy."""
        engine = ConditionEvaluationEngine()
        
        # Remove existing strategy
        assert engine.remove_strategy(ConditionOperator.EQUALS) is True
        assert ConditionOperator.EQUALS not in engine.strategies
        
        # Try to remove non-existent strategy
        assert engine.remove_strategy("non_existent") is False


class TestConditionEngineFactory:
    """Test condition engine factory function."""

    def test_create_condition_engine(self):
        """Test factory creates properly configured engine."""
        engine = create_condition_engine()
        
        assert isinstance(engine, ConditionEvaluationEngine)
        assert len(engine.get_supported_operators()) == 13  # All standard operators
        
        # Test basic functionality
        result = engine.evaluate_condition(
            ConditionOperator.EQUALS, "test", "test"
        )
        assert result is True


class TestComplexityReduction:
    """Test that demonstrates the complexity reduction achieved."""

    def test_original_vs_refactored_complexity(self):
        """
        Test demonstrating complexity reduction from 14→3.
        
        Original method had 14 if-elif branches (complexity 14).
        New method has simple strategy lookup (complexity 3).
        """
        engine = create_condition_engine()
        
        # Test all operator types that were in original if-elif chain
        test_cases = [
            (ConditionOperator.EQUALS, "test", "test", True),
            (ConditionOperator.NOT_EQUALS, "test", "other", True),
            (ConditionOperator.GREATER_THAN, 10, 5, True),
            (ConditionOperator.LESS_THAN, 5, 10, True),
            (ConditionOperator.GREATER_EQUAL, 5, 5, True),
            (ConditionOperator.LESS_EQUAL, 5, 5, True),
            (ConditionOperator.CONTAINS, "hello world", "world", True),
            (ConditionOperator.NOT_CONTAINS, "hello world", "foo", True),
            (ConditionOperator.IN, "apple", ["apple", "banana"], True),
            (ConditionOperator.NOT_IN, "grape", ["apple", "banana"], True),
            (ConditionOperator.EXISTS, "value", None, True),
            (ConditionOperator.NOT_EXISTS, None, None, True),
            (ConditionOperator.REGEX, "test@example.com", r".*@.*\.com", True),
        ]
        
        for operator, field_value, expected_value, expected_result in test_cases:
            result = engine.evaluate_condition(operator, field_value, expected_value)
            assert result == expected_result, f"Failed for operator {operator}"
        
        # Verify all 13 operators work without complex if-elif logic
        assert len(engine.get_supported_operators()) == 13


class TestIntegrationWithAutomation:
    """Test integration with automation module."""

    def test_condition_evaluator_uses_strategy(self):
        """Test that ConditionEvaluator uses new strategy pattern."""
        from dotmac_isp.sdks.workflows.automation import (
            ConditionEvaluator,
            AutomationCondition,
        )
        
        evaluator = ConditionEvaluator()
        condition = AutomationCondition(
            field="test_field",
            operator=ConditionOperator.EQUALS,
            value="expected_value"
        )
        
        data = {"test_field": "expected_value"}
        
        # This should use the new strategy pattern internally
        result = evaluator.evaluate_condition(condition, data)
        assert result is True
        
        # Test with condition not met
        data = {"test_field": "different_value"}
        result = evaluator.evaluate_condition(condition, data)
        assert result is False

    def test_nested_field_access(self):
        """Test nested field access still works with strategy pattern."""
        from dotmac_isp.sdks.workflows.automation import (
            ConditionEvaluator,
            AutomationCondition,
        )
        
        evaluator = ConditionEvaluator()
        condition = AutomationCondition(
            field="user.profile.name",
            operator=ConditionOperator.EQUALS,
            value="John Doe"
        )
        
        data = {
            "user": {
                "profile": {
                    "name": "John Doe"
                }
            }
        }
        
        result = evaluator.evaluate_condition(condition, data)
        assert result is True