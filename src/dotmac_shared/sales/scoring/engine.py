"""
Lead scoring engine using Strategy pattern.
"""

import logging
from typing import Any, Optional

try:
    from .strategies import (
        BANTScoringStrategy,
        BudgetScoringStrategy,
        CompanySizeScoringStrategy,
        CustomerTypeScoringStrategy,
        EngagementScoringStrategy,
        LeadScoringStrategy,
        LeadSourceScoringStrategy,
    )
except ImportError:
    from .strategies import (
        BANTScoringStrategy,
        BudgetScoringStrategy,
        CompanySizeScoringStrategy,
        CustomerTypeScoringStrategy,
        EngagementScoringStrategy,
        LeadScoringStrategy,
        LeadSourceScoringStrategy,
    )

logger = logging.getLogger(__name__)


class LeadScoringEngine:
    """
    Lead scoring engine using Strategy pattern.

    REFACTORED: Replaces 14-complexity _calculate_lead_score method with
    focused, configurable scoring strategies (Complexity: 3).
    """

    def __init__(self, custom_strategies: Optional[list[LeadScoringStrategy]] = None):
        """Initialize with default and custom scoring strategies."""
        self.strategies = [
            BudgetScoringStrategy(),
            CustomerTypeScoringStrategy(),
            LeadSourceScoringStrategy(),
            BANTScoringStrategy(),
            CompanySizeScoringStrategy(),
            EngagementScoringStrategy(),
        ]

        # Add custom strategies if provided
        if custom_strategies:
            self.strategies.extend(custom_strategies)

    def calculate_lead_score(self, lead_data: dict[str, Any]) -> int:
        """
        Calculate total lead score using all scoring strategies.

        COMPLEXITY REDUCTION: This method replaces the original 14-complexity
        method with a simple iteration over strategies (Complexity: 3).

        Args:
            lead_data: Dictionary containing lead information

        Returns:
            Total lead score (capped at 100)
        """
        # Step 1: Initialize scoring (Complexity: 1)
        total_score = 0
        strategy_scores = {}

        # Step 2: Apply all scoring strategies (Complexity: 1)
        for strategy in self.strategies:
            try:
                strategy_score = strategy.calculate_score(lead_data)
                total_score += strategy_score
                strategy_scores[strategy.get_strategy_name()] = strategy_score
            except Exception as e:
                logger.warning(f"Error in {strategy.get_strategy_name()}: {e}")
                strategy_scores[strategy.get_strategy_name()] = 0

        # Step 3: Return capped score (Complexity: 1)
        final_score = min(total_score, 100)

        # Log detailed scoring for analysis
        logger.debug(f"Lead scoring breakdown: {strategy_scores}, Total: {final_score}")

        return final_score

    def get_scoring_breakdown(self, lead_data: dict[str, Any]) -> dict[str, int]:
        """Get detailed scoring breakdown by strategy."""
        breakdown = {}

        for strategy in self.strategies:
            try:
                score = strategy.calculate_score(lead_data)
                breakdown[strategy.get_strategy_name()] = score
            except Exception as e:
                logger.warning(f"Error in {strategy.get_strategy_name()}: {e}")
                breakdown[strategy.get_strategy_name()] = 0

        return breakdown

    def add_scoring_strategy(self, strategy: LeadScoringStrategy) -> None:
        """Add a custom scoring strategy."""
        self.strategies.append(strategy)
        logger.info(f"Added custom scoring strategy: {strategy.get_strategy_name()}")

    def remove_scoring_strategy(self, strategy_name: str) -> bool:
        """Remove a scoring strategy by name."""
        original_count = len(self.strategies)
        self.strategies = [s for s in self.strategies if s.get_strategy_name() != strategy_name]
        removed = len(self.strategies) < original_count

        if removed:
            logger.info(f"Removed scoring strategy: {strategy_name}")

        return removed

    def get_active_strategies(self) -> list[str]:
        """Get list of active scoring strategy names."""
        return [strategy.get_strategy_name() for strategy in self.strategies]


class WeightedLeadScoringEngine(LeadScoringEngine):
    """
    Advanced lead scoring engine with weighted strategies.
    Allows different importance weights for different scoring criteria.
    """

    def __init__(self, strategy_weights: Optional[dict[str, float]] = None):
        """Initialize with weighted strategies."""
        super().__init__()

        # Default weights (can be customized)
        self.strategy_weights = strategy_weights or {
            "Budget Scoring": 1.2,  # Budget is very important
            "Customer Type Scoring": 1.0,  # Standard weight
            "Lead Source Scoring": 0.8,  # Slightly less important
            "BANT Criteria Scoring": 1.1,  # BANT is important
            "Company Size Scoring": 0.9,  # Moderately important
            "Engagement Scoring": 0.7,  # Nice to have
        }

    def calculate_lead_score(self, lead_data: dict[str, Any]) -> int:
        """Calculate weighted lead score."""
        total_score = 0

        for strategy in self.strategies:
            try:
                strategy_score = strategy.calculate_score(lead_data)
                strategy_name = strategy.get_strategy_name()
                weight = self.strategy_weights.get(strategy_name, 1.0)
                weighted_score = strategy_score * weight
                total_score += weighted_score
            except Exception as e:
                logger.warning(f"Error in {strategy.get_strategy_name()}: {e}")

        return min(int(total_score), 100)


def create_lead_scoring_engine(
    weighted: bool = False,
    custom_strategies: Optional[list[LeadScoringStrategy]] = None,
    strategy_weights: Optional[dict[str, float]] = None,
) -> LeadScoringEngine:
    """
    Factory function to create a configured lead scoring engine.

    This is the main entry point for replacing the 14-complexity method.

    Args:
        weighted: Whether to use weighted scoring engine
        custom_strategies: Additional custom scoring strategies
        strategy_weights: Custom weights for strategies (if weighted=True)

    Returns:
        Configured lead scoring engine
    """
    if weighted:
        return WeightedLeadScoringEngine(strategy_weights)
    else:
        return LeadScoringEngine(custom_strategies)
