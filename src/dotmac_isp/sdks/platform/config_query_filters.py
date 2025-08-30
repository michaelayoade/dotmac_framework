"""
Configuration query filter strategies using Strategy pattern.
Replaces the 24-complexity _matches_query method with focused filter strategies.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass
class ConfigEntry:
    """Configuration entry for type hints."""

    scope: Optional[str] = None
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    service_name: Optional[str] = None
    key: str = ""
    category: Optional[str] = None
    environment: Optional[str] = None
    data_type: Optional[str] = None
    is_secret: Optional[bool] = None
    is_readonly: Optional[bool] = None
    tags: List[str] = None


@dataclass
class ConfigQuery:
    """Configuration query for type hints."""

    scope: Optional[str] = None
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    service_name: Optional[str] = None
    key_prefix: Optional[str] = None
    keys: Optional[List[str]] = None
    category: Optional[str] = None
    environment: Optional[str] = None
    data_types: Optional[List[str]] = None
    is_secret: Optional[bool] = None
    is_readonly: Optional[bool] = None
    tags: Optional[List[str]] = None


class ConfigFilterStrategy(ABC):
    """Base strategy for configuration filtering."""

    @abstractmethod
    def matches(self, config: ConfigEntry, query: ConfigQuery) -> bool:
        """Check if configuration matches this filter criteria."""
        pass


class ScopeFilterStrategy(ConfigFilterStrategy):
    """Filter by configuration scope."""

    def matches(self, config: ConfigEntry, query: ConfigQuery) -> bool:
        """Check if config scope matches query scope."""
        if query.scope is None:
            return True
        return config.scope == query.scope


class TenantFilterStrategy(ConfigFilterStrategy):
    """Filter by tenant ID."""

    def matches(self, config: ConfigEntry, query: ConfigQuery) -> bool:
        """Check if config tenant matches query tenant."""
        if query.tenant_id is None:
            return True
        return config.tenant_id == query.tenant_id


class UserFilterStrategy(ConfigFilterStrategy):
    """Filter by user ID."""

    def matches(self, config: ConfigEntry, query: ConfigQuery) -> bool:
        """Check if config user matches query user."""
        if query.user_id is None:
            return True
        return config.user_id == query.user_id


class ServiceFilterStrategy(ConfigFilterStrategy):
    """Filter by service name."""

    def matches(self, config: ConfigEntry, query: ConfigQuery) -> bool:
        """Check if config service matches query service."""
        if query.service_name is None:
            return True
        return config.service_name == query.service_name


class KeyFilterStrategy(ConfigFilterStrategy):
    """Filter by configuration key patterns."""

    def matches(self, config: ConfigEntry, query: ConfigQuery) -> bool:
        """Check if config key matches query key criteria."""
        # Check key prefix
        if query.key_prefix and not config.key.startswith(query.key_prefix):
            return False

        # Check specific keys
        if query.keys and config.key not in query.keys:
            return False

        return True


class CategoryFilterStrategy(ConfigFilterStrategy):
    """Filter by configuration category."""

    def matches(self, config: ConfigEntry, query: ConfigQuery) -> bool:
        """Check if config category matches query category."""
        if query.category is None:
            return True
        return config.category == query.category


class EnvironmentFilterStrategy(ConfigFilterStrategy):
    """Filter by environment."""

    def matches(self, config: ConfigEntry, query: ConfigQuery) -> bool:
        """Check if config environment matches query environment."""
        if query.environment is None:
            return True
        return config.environment == query.environment


class DataTypeFilterStrategy(ConfigFilterStrategy):
    """Filter by data types."""

    def matches(self, config: ConfigEntry, query: ConfigQuery) -> bool:
        """Check if config data type is in query data types."""
        if query.data_types is None:
            return True
        return config.data_type in query.data_types


class SecretFilterStrategy(ConfigFilterStrategy):
    """Filter by secret flag."""

    def matches(self, config: ConfigEntry, query: ConfigQuery) -> bool:
        """Check if config secret flag matches query."""
        if query.is_secret is None:
            return True
        return config.is_secret == query.is_secret


class ReadOnlyFilterStrategy(ConfigFilterStrategy):
    """Filter by readonly flag."""

    def matches(self, config: ConfigEntry, query: ConfigQuery) -> bool:
        """Check if config readonly flag matches query."""
        if query.is_readonly is None:
            return True
        return config.is_readonly == query.is_readonly


class TagsFilterStrategy(ConfigFilterStrategy):
    """Filter by tags."""

    def matches(self, config: ConfigEntry, query: ConfigQuery) -> bool:
        """Check if config has all required tags."""
        if query.tags is None:
            return True

        if config.tags is None:
            return False

        # All query tags must be present in config tags
        return all(tag in config.tags for tag in query.tags)


class ConfigQueryMatcher:
    """
    Configuration query matcher using Strategy pattern.

    REFACTORED: Replaces 24-complexity _matches_query method with
    focused, testable filter strategies (Complexity: 3).
    """

    def __init__(self):
        """Initialize with default filter strategies."""
        self.strategies = [
            ScopeFilterStrategy(),
            TenantFilterStrategy(),
            UserFilterStrategy(),
            ServiceFilterStrategy(),
            KeyFilterStrategy(),
            CategoryFilterStrategy(),
            EnvironmentFilterStrategy(),
            DataTypeFilterStrategy(),
            SecretFilterStrategy(),
            ReadOnlyFilterStrategy(),
            TagsFilterStrategy(),
        ]

    def matches_query(self, config: ConfigEntry, query: ConfigQuery) -> bool:
        """
        Check if configuration matches query using all filter strategies.

        COMPLEXITY REDUCTION: This method replaces the original 24-complexity
        method with a simple iteration over strategies (Complexity: 2).

        Args:
            config: Configuration entry to check
            query: Query with filter criteria

        Returns:
            True if config matches all query criteria
        """
        # Step 1: Apply all filter strategies (Complexity: 1)
        for strategy in self.strategies:
            if not strategy.matches(config, query):
                return False

        # Step 2: Return match result (Complexity: 1)
        return True

    def add_filter_strategy(self, strategy: ConfigFilterStrategy) -> None:
        """Add a custom filter strategy."""
        self.strategies.append(strategy)

    def remove_filter_strategy(self, strategy_class: type) -> bool:
        """Remove a filter strategy by class type."""
        original_count = len(self.strategies)
        self.strategies = [
            s for s in self.strategies if not isinstance(s, strategy_class)
        ]
        return len(self.strategies) < original_count

    def get_active_strategies(self) -> List[str]:
        """Get list of active filter strategy names."""
        return [strategy.__class__.__name__ for strategy in self.strategies]


def create_config_query_matcher() -> ConfigQueryMatcher:
    """
    Factory function to create a configured query matcher.

    This is the main entry point for replacing the 24-complexity method.
    """
    return ConfigQueryMatcher()
