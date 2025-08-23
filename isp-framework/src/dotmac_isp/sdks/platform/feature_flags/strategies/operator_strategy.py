"""
Base strategy pattern for feature flag operator evaluation.
This replaces the 21-complexity if-elif chain in _evaluate_targeting_rule.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
import re
import logging

logger = logging.getLogger(__name__)


class OperatorStrategy(ABC):
    """Base class for all operator evaluation strategies."""
    
    @abstractmethod
    def evaluate(self, attribute_value: Any, rule_value: Any) -> bool:
        """
        Evaluate the operator against the given values.
        
        Args:
            attribute_value: The actual value from user context
            rule_value: The expected value from the targeting rule
            
        Returns:
            bool: True if the rule matches, False otherwise
        """
        pass
    
    def _safe_string_conversion(self, value: Any) -> str:
        """Safely convert any value to string for string operations."""
        if value is None:
            return ""
        return str(value)
    
    def _safe_numeric_conversion(self, value: Any) -> float:
        """Safely convert any value to numeric for numeric operations."""
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0


class EqualsStrategy(OperatorStrategy):
    """Strategy for equality comparison."""
    
    def evaluate(self, attribute_value: Any, rule_value: Any) -> bool:
        return attribute_value == rule_value


class NotEqualsStrategy(OperatorStrategy):
    """Strategy for inequality comparison."""
    
    def evaluate(self, attribute_value: Any, rule_value: Any) -> bool:
        return attribute_value != rule_value


class GreaterThanStrategy(OperatorStrategy):
    """Strategy for greater than comparison."""
    
    def evaluate(self, attribute_value: Any, rule_value: Any) -> bool:
        try:
            return self._safe_numeric_conversion(attribute_value) > self._safe_numeric_conversion(rule_value)
        except Exception as e:
            logger.warning(f"Error in greater than comparison: {e}")
            return False


class LessThanStrategy(OperatorStrategy):
    """Strategy for less than comparison."""
    
    def evaluate(self, attribute_value: Any, rule_value: Any) -> bool:
        try:
            return self._safe_numeric_conversion(attribute_value) < self._safe_numeric_conversion(rule_value)
        except Exception as e:
            logger.warning(f"Error in less than comparison: {e}")
            return False


class GreaterThanOrEqualStrategy(OperatorStrategy):
    """Strategy for greater than or equal comparison."""
    
    def evaluate(self, attribute_value: Any, rule_value: Any) -> bool:
        try:
            return self._safe_numeric_conversion(attribute_value) >= self._safe_numeric_conversion(rule_value)
        except Exception as e:
            logger.warning(f"Error in greater than or equal comparison: {e}")
            return False


class LessThanOrEqualStrategy(OperatorStrategy):
    """Strategy for less than or equal comparison."""
    
    def evaluate(self, attribute_value: Any, rule_value: Any) -> bool:
        try:
            return self._safe_numeric_conversion(attribute_value) <= self._safe_numeric_conversion(rule_value)
        except Exception as e:
            logger.warning(f"Error in less than or equal comparison: {e}")
            return False


class ContainsStrategy(OperatorStrategy):
    """Strategy for substring containment check."""
    
    def evaluate(self, attribute_value: Any, rule_value: Any) -> bool:
        try:
            attr_str = self._safe_string_conversion(attribute_value).lower()
            rule_str = self._safe_string_conversion(rule_value).lower()
            return rule_str in attr_str
        except Exception as e:
            logger.warning(f"Error in contains comparison: {e}")
            return False


class NotContainsStrategy(OperatorStrategy):
    """Strategy for substring not containment check."""
    
    def evaluate(self, attribute_value: Any, rule_value: Any) -> bool:
        try:
            attr_str = self._safe_string_conversion(attribute_value).lower()
            rule_str = self._safe_string_conversion(rule_value).lower()
            return rule_str not in attr_str
        except Exception as e:
            logger.warning(f"Error in not contains comparison: {e}")
            return False


class StartsWithStrategy(OperatorStrategy):
    """Strategy for string prefix check."""
    
    def evaluate(self, attribute_value: Any, rule_value: Any) -> bool:
        try:
            attr_str = self._safe_string_conversion(attribute_value).lower()
            rule_str = self._safe_string_conversion(rule_value).lower()
            return attr_str.startswith(rule_str)
        except Exception as e:
            logger.warning(f"Error in starts with comparison: {e}")
            return False


class EndsWithStrategy(OperatorStrategy):
    """Strategy for string suffix check."""
    
    def evaluate(self, attribute_value: Any, rule_value: Any) -> bool:
        try:
            attr_str = self._safe_string_conversion(attribute_value).lower()
            rule_str = self._safe_string_conversion(rule_value).lower()
            return attr_str.endswith(rule_str)
        except Exception as e:
            logger.warning(f"Error in ends with comparison: {e}")
            return False


class InStrategy(OperatorStrategy):
    """Strategy for membership in a collection."""
    
    def evaluate(self, attribute_value: Any, rule_value: Any) -> bool:
        try:
            # rule_value should be a list/collection
            if isinstance(rule_value, (list, tuple, set)):
                return attribute_value in rule_value
            # If rule_value is a string, split it by comma
            elif isinstance(rule_value, str):
                values = [v.strip() for v in rule_value.split(',')]
                return str(attribute_value) in values
            return False
        except Exception as e:
            logger.warning(f"Error in in comparison: {e}")
            return False


class NotInStrategy(OperatorStrategy):
    """Strategy for non-membership in a collection."""
    
    def evaluate(self, attribute_value: Any, rule_value: Any) -> bool:
        try:
            # rule_value should be a list/collection
            if isinstance(rule_value, (list, tuple, set)):
                return attribute_value not in rule_value
            # If rule_value is a string, split it by comma
            elif isinstance(rule_value, str):
                values = [v.strip() for v in rule_value.split(',')]
                return str(attribute_value) not in values
            return True
        except Exception as e:
            logger.warning(f"Error in not in comparison: {e}")
            return False


class RegexStrategy(OperatorStrategy):
    """Strategy for regular expression matching."""
    
    def evaluate(self, attribute_value: Any, rule_value: Any) -> bool:
        try:
            attr_str = self._safe_string_conversion(attribute_value)
            pattern = self._safe_string_conversion(rule_value)
            return bool(re.search(pattern, attr_str, re.IGNORECASE))
        except Exception as e:
            logger.warning(f"Error in regex comparison: {e}")
            return False


class VersionCompareStrategy(OperatorStrategy):
    """Strategy for semantic version comparison."""
    
    def evaluate(self, attribute_value: Any, rule_value: Any) -> bool:
        try:
            attr_version = self._parse_version(str(attribute_value))
            rule_version = self._parse_version(str(rule_value))
            return attr_version >= rule_version
        except Exception as e:
            logger.warning(f"Error in version comparison: {e}")
            return False
    
    def _parse_version(self, version_str: str) -> tuple:
        """Parse version string into comparable tuple."""
        parts = version_str.replace('v', '').split('.')
        return tuple(int(part) for part in parts if part.isdigit())


class DateCompareStrategy(OperatorStrategy):
    """Strategy for date comparison."""
    
    def evaluate(self, attribute_value: Any, rule_value: Any) -> bool:
        try:
            attr_date = self._parse_date(attribute_value)
            rule_date = self._parse_date(rule_value)
            return attr_date >= rule_date if attr_date and rule_date else False
        except Exception as e:
            logger.warning(f"Error in date comparison: {e}")
            return False
    
    def _parse_date(self, date_value: Any) -> Optional[datetime]:
        """Parse various date formats into datetime."""
        if isinstance(date_value, datetime):
            return date_value
        
        try:
            # Try ISO format first
            return datetime.fromisoformat(str(date_value).replace('Z', '+00:00'))
        except ValueError:
            try:
                # Try common formats
                from datetime import datetime as dt
                for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y']:
                    try:
                        return dt.strptime(str(date_value), fmt)
                    except ValueError:
                        continue
            except Exception:
                pass
        
        return None