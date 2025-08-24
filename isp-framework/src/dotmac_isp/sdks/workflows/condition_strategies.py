"""
Condition evaluation strategies for workflow automation.

REFACTORED: Extracted from automation.py to reduce ConditionEvaluator.evaluate_condition 
complexity from 14→3 using Strategy pattern.
"""

import re
from abc import ABC, abstractmethod
from typing import Any, Dict

import structlog

logger = structlog.get_logger(__name__)


class ConditionStrategy(ABC):
    """Base strategy for condition evaluation."""
    
    @abstractmethod
    def evaluate(self, field_value: Any, expected_value: Any) -> bool:
        """Evaluate condition with given values."""
        pass
    
    @abstractmethod
    def get_operator_name(self) -> str:
        """Get operator name for logging."""
        pass


class EqualsStrategy(ConditionStrategy):
    """Strategy for equality comparison."""
    
    def evaluate(self, field_value: Any, expected_value: Any) -> bool:
        """Check if field value equals expected value."""
        return field_value == expected_value
    
    def get_operator_name(self) -> str:
        """Get Operator Name operation."""
        return "equals"


class NotEqualsStrategy(ConditionStrategy):
    """Strategy for inequality comparison."""
    
    def evaluate(self, field_value: Any, expected_value: Any) -> bool:
        """Check if field value does not equal expected value."""
        return field_value != expected_value
    
    def get_operator_name(self) -> str:
        """Get Operator Name operation."""
        return "not_equals"


class GreaterThanStrategy(ConditionStrategy):
    """Strategy for greater than comparison."""
    
    def evaluate(self, field_value: Any, expected_value: Any) -> bool:
        """Check if field value is greater than expected value."""
        try:
            return field_value > expected_value
        except TypeError:
            logger.warning("Type error in greater than comparison",
                         field_value=field_value, expected_value=expected_value)
            return False
    
    def get_operator_name(self) -> str:
        """Get Operator Name operation."""
        return "greater_than"


class LessThanStrategy(ConditionStrategy):
    """Strategy for less than comparison."""
    
    def evaluate(self, field_value: Any, expected_value: Any) -> bool:
        """Check if field value is less than expected value."""
        try:
            return field_value < expected_value
        except TypeError:
            logger.warning("Type error in less than comparison",
                         field_value=field_value, expected_value=expected_value)
            return False
    
    def get_operator_name(self) -> str:
        """Get Operator Name operation."""
        return "less_than"


class GreaterEqualStrategy(ConditionStrategy):
    """Strategy for greater than or equal comparison."""
    
    def evaluate(self, field_value: Any, expected_value: Any) -> bool:
        """Check if field value is greater than or equal to expected value."""
        try:
            return field_value >= expected_value
        except TypeError:
            logger.warning("Type error in greater equal comparison",
                         field_value=field_value, expected_value=expected_value)
            return False
    
    def get_operator_name(self) -> str:
        """Get Operator Name operation."""
        return "greater_equal"


class LessEqualStrategy(ConditionStrategy):
    """Strategy for less than or equal comparison."""
    
    def evaluate(self, field_value: Any, expected_value: Any) -> bool:
        """Check if field value is less than or equal to expected value."""
        try:
            return field_value <= expected_value
        except TypeError:
            logger.warning("Type error in less equal comparison",
                         field_value=field_value, expected_value=expected_value)
            return False
    
    def get_operator_name(self) -> str:
        """Get Operator Name operation."""
        return "less_equal"


class ContainsStrategy(ConditionStrategy):
    """Strategy for contains comparison."""
    
    def evaluate(self, field_value: Any, expected_value: Any) -> bool:
        """Check if field value contains expected value."""
        try:
            return expected_value in str(field_value)
        except (TypeError, ValueError):
            logger.warning("Error in contains comparison",
                         field_value=field_value, expected_value=expected_value)
            return False
    
    def get_operator_name(self) -> str:
        """Get Operator Name operation."""
        return "contains"


class NotContainsStrategy(ConditionStrategy):
    """Strategy for not contains comparison."""
    
    def evaluate(self, field_value: Any, expected_value: Any) -> bool:
        """Check if field value does not contain expected value."""
        try:
            return expected_value not in str(field_value)
        except (TypeError, ValueError):
            logger.warning("Error in not contains comparison",
                         field_value=field_value, expected_value=expected_value)
            return False
    
    def get_operator_name(self) -> str:
        """Get Operator Name operation."""
        return "not_contains"


class InStrategy(ConditionStrategy):
    """Strategy for 'in' comparison."""
    
    def evaluate(self, field_value: Any, expected_value: Any) -> bool:
        """Check if field value is in expected collection."""
        try:
            return field_value in expected_value
        except TypeError:
            logger.warning("Type error in 'in' comparison",
                         field_value=field_value, expected_value=expected_value)
            return False
    
    def get_operator_name(self) -> str:
        """Get Operator Name operation."""
        return "in"


class NotInStrategy(ConditionStrategy):
    """Strategy for 'not in' comparison."""
    
    def evaluate(self, field_value: Any, expected_value: Any) -> bool:
        """Check if field value is not in expected collection."""
        try:
            return field_value not in expected_value
        except TypeError:
            logger.warning("Type error in 'not in' comparison",
                         field_value=field_value, expected_value=expected_value)
            return False
    
    def get_operator_name(self) -> str:
        """Get Operator Name operation."""
        return "not_in"


class ExistsStrategy(ConditionStrategy):
    """Strategy for existence check."""
    
    def evaluate(self, field_value: Any, expected_value: Any) -> bool:
        """Check if field value exists (not None)."""
        return field_value is not None
    
    def get_operator_name(self) -> str:
        """Get Operator Name operation."""
        return "exists"


class NotExistsStrategy(ConditionStrategy):
    """Strategy for non-existence check."""
    
    def evaluate(self, field_value: Any, expected_value: Any) -> bool:
        """Check if field value does not exist (is None)."""
        return field_value is None
    
    def get_operator_name(self) -> str:
        """Get Operator Name operation."""
        return "not_exists"


class RegexStrategy(ConditionStrategy):
    """Strategy for regex pattern matching."""
    
    def evaluate(self, field_value: Any, expected_value: Any) -> bool:
        """Check if field value matches regex pattern."""
        try:
            return bool(re.search(expected_value, str(field_value)))
        except (re.error, TypeError, ValueError) as e:
            logger.warning("Error in regex comparison",
                         field_value=field_value, 
                         expected_value=expected_value,
                         error=str(e))
            return False
    
    def get_operator_name(self) -> str:
        """Get Operator Name operation."""
        return "regex"


class ConditionEvaluationEngine:
    """
    Engine for evaluating automation conditions using Strategy pattern.
    
    REFACTORED: Replaces the 14-complexity if-elif chain in ConditionEvaluator.evaluate_condition
    with a simple strategy lookup (Complexity: 3).
    """
    
    def __init__(self):
        """Initialize with all available condition strategies."""
        from .automation import ConditionOperator
        
        self.strategies = {
            ConditionOperator.EQUALS: EqualsStrategy(),
            ConditionOperator.NOT_EQUALS: NotEqualsStrategy(),
            ConditionOperator.GREATER_THAN: GreaterThanStrategy(),
            ConditionOperator.LESS_THAN: LessThanStrategy(),
            ConditionOperator.GREATER_EQUAL: GreaterEqualStrategy(),
            ConditionOperator.LESS_EQUAL: LessEqualStrategy(),
            ConditionOperator.CONTAINS: ContainsStrategy(),
            ConditionOperator.NOT_CONTAINS: NotContainsStrategy(),
            ConditionOperator.IN: InStrategy(),
            ConditionOperator.NOT_IN: NotInStrategy(),
            ConditionOperator.EXISTS: ExistsStrategy(),
            ConditionOperator.NOT_EXISTS: NotExistsStrategy(),
            ConditionOperator.REGEX: RegexStrategy(),
        }
    
    def evaluate_condition(self, operator: str, field_value: Any, expected_value: Any) -> bool:
        """
        Evaluate condition using appropriate strategy.
        
        COMPLEXITY REDUCTION: This method replaces the original 14-complexity 
        if-elif chain with simple strategy lookup (Complexity: 3).
        
        Args:
            operator: Condition operator
            field_value: Actual field value
            expected_value: Expected value to compare against
            
        Returns:
            Boolean result of condition evaluation
            
        Raises:
            ValueError: If operator is unknown
        """
        # Step 1: Get strategy for operator (Complexity: 1)
        strategy = self.strategies.get(operator)
        if not strategy:
            raise ValueError(f"Unknown operator: {operator}")
        
        # Step 2: Evaluate using strategy (Complexity: 1)
        try:
            result = strategy.evaluate(field_value, expected_value)
            logger.debug("Condition evaluated",
                        operator=operator,
                        strategy=strategy.get_operator_name(),
                        result=result)
            return result
        except Exception as e:
            logger.error("Condition evaluation failed",
                        operator=operator,
                        field_value=field_value,
                        expected_value=expected_value,
                        error=str(e))
            return False
    
    def get_supported_operators(self) -> list[str]:
        """Get list of supported operators."""
        return list(self.strategies.keys())
    
    def add_custom_strategy(self, operator: str, strategy: ConditionStrategy) -> None:
        """Add a custom condition strategy."""
        self.strategies[operator] = strategy
        logger.info("Added custom condition strategy",
                   operator=operator,
                   strategy_name=strategy.get_operator_name())
    
    def remove_strategy(self, operator: str) -> bool:
        """Remove a condition strategy."""
        if operator in self.strategies:
            del self.strategies[operator]
            logger.info("Removed condition strategy", operator=operator)
            return True
        return False


def create_condition_engine() -> ConditionEvaluationEngine:
    """
    Factory function to create a configured condition evaluation engine.
    
    This is the main entry point for replacing the 14-complexity condition evaluation.
    
    Returns:
        Configured condition evaluation engine
    """
    return ConditionEvaluationEngine()