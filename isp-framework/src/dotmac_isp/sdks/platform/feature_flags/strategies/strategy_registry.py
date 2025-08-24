"""
Strategy registry for feature flag operator evaluation.
Centralized registry that maps operators to their strategies.
"""

from typing import Dict, Any, Optional
from enum import Enum
import logging

from .operator_strategy import (
    OperatorStrategy,
    EqualsStrategy,
    NotEqualsStrategy,
    GreaterThanStrategy,
    LessThanStrategy,
    GreaterThanOrEqualStrategy,
    LessThanOrEqualStrategy,
    ContainsStrategy,
    NotContainsStrategy,
    StartsWithStrategy,
    EndsWithStrategy,
    InStrategy,
    NotInStrategy,
    RegexStrategy,
    VersionCompareStrategy,
    DateCompareStrategy,
)

logger = logging.getLogger(__name__)


class TargetingOperator(Enum):
    """Enumeration of supported targeting operators."""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    IN = "in"
    NOT_IN = "not_in"
    REGEX = "regex"
    VERSION_COMPARE = "version_compare"
    DATE_COMPARE = "date_compare"


class OperatorStrategyRegistry:
    """
    Registry for operator strategies.
    Replaces the 21-complexity if-elif chain with Strategy pattern.
    """
    
    def __init__(self):
        """  Init   operation."""
        self._strategies: Dict[TargetingOperator, OperatorStrategy] = {}
        self._initialize_default_strategies()
    
    def _initialize_default_strategies(self):
        """Initialize the registry with default strategies."""
        self._strategies = {
            TargetingOperator.EQUALS: EqualsStrategy(),
            TargetingOperator.NOT_EQUALS: NotEqualsStrategy(),
            TargetingOperator.GREATER_THAN: GreaterThanStrategy(),
            TargetingOperator.LESS_THAN: LessThanStrategy(),
            TargetingOperator.GREATER_THAN_OR_EQUAL: GreaterThanOrEqualStrategy(),
            TargetingOperator.LESS_THAN_OR_EQUAL: LessThanOrEqualStrategy(),
            TargetingOperator.CONTAINS: ContainsStrategy(),
            TargetingOperator.NOT_CONTAINS: NotContainsStrategy(),
            TargetingOperator.STARTS_WITH: StartsWithStrategy(),
            TargetingOperator.ENDS_WITH: EndsWithStrategy(),
            TargetingOperator.IN: InStrategy(),
            TargetingOperator.NOT_IN: NotInStrategy(),
            TargetingOperator.REGEX: RegexStrategy(),
            TargetingOperator.VERSION_COMPARE: VersionCompareStrategy(),
            TargetingOperator.DATE_COMPARE: DateCompareStrategy(),
        }
    
    def register_strategy(self, operator: TargetingOperator, strategy: OperatorStrategy) -> None:
        """
        Register a custom strategy for an operator.
        
        Args:
            operator: The targeting operator
            strategy: The strategy implementation
        """
        self._strategies[operator] = strategy
        logger.info(f"Registered strategy for operator: {operator.value}")
    
    def get_strategy(self, operator: TargetingOperator) -> Optional[OperatorStrategy]:
        """
        Get the strategy for a given operator.
        
        Args:
            operator: The targeting operator
            
        Returns:
            The strategy implementation or None if not found
        """
        return self._strategies.get(operator)
    
    def evaluate(self, operator: TargetingOperator, attribute_value: Any, rule_value: Any) -> bool:
        """
        Evaluate an operator against values using the appropriate strategy.
        
        This replaces the original 21-complexity if-elif chain.
        
        Args:
            operator: The targeting operator
            attribute_value: The actual value from user context
            rule_value: The expected value from the targeting rule
            
        Returns:
            bool: True if the rule matches, False otherwise
        """
        strategy = self.get_strategy(operator)
        if strategy is None:
            logger.warning(f"No strategy found for operator: {operator.value}")
            return False
        
        try:
            result = strategy.evaluate(attribute_value, rule_value)
            logger.debug(f"Evaluated {operator.value}: {attribute_value} vs {rule_value} = {result}")
            return result
        except Exception as e:
            logger.error(f"Error evaluating {operator.value}: {e}")
            return False
    
    def get_supported_operators(self) -> list[TargetingOperator]:
        """Get a list of all supported operators."""
        return list(self._strategies.keys())
    
    def is_operator_supported(self, operator: TargetingOperator) -> bool:
        """Check if an operator is supported."""
        return operator in self._strategies


# Global registry instance - singleton pattern
_registry_instance: Optional[OperatorStrategyRegistry] = None


def get_operator_registry() -> OperatorStrategyRegistry:
    """Get the global operator registry instance (singleton)."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = OperatorStrategyRegistry()
    return _registry_instance


def evaluate_targeting_rule(operator: TargetingOperator, attribute_value: Any, rule_value: Any) -> bool:
    """
    Convenience function to evaluate a targeting rule.
    
    This is the new simplified interface that replaces the complex method.
    
    Args:
        operator: The targeting operator
        attribute_value: The actual value from user context  
        rule_value: The expected value from the targeting rule
        
    Returns:
        bool: True if the rule matches, False otherwise
    """
    registry = get_operator_registry()
    return registry.evaluate(operator, attribute_value, rule_value)