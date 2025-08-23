"""
Feature flag operator strategies package.
Replaces complex if-elif chains with Strategy pattern.
"""

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

from .strategy_registry import OperatorStrategyRegistry

__all__ = [
    'OperatorStrategy',
    'EqualsStrategy',
    'NotEqualsStrategy', 
    'GreaterThanStrategy',
    'LessThanStrategy',
    'GreaterThanOrEqualStrategy',
    'LessThanOrEqualStrategy',
    'ContainsStrategy',
    'NotContainsStrategy',
    'StartsWithStrategy',
    'EndsWithStrategy',
    'InStrategy',
    'NotInStrategy',
    'RegexStrategy',
    'VersionCompareStrategy',
    'DateCompareStrategy',
    'OperatorStrategyRegistry',
]