"""
Lead scoring strategies using Strategy pattern.
Replaces the 14-complexity _calculate_lead_score method with focused scoring strategies.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

try:
    from ..core.models import CustomerType, LeadSource
except ImportError:
    from ..core.models import CustomerType, LeadSource

logger = logging.getLogger(__name__)


class LeadScoringStrategy(ABC):
    """Base strategy for lead scoring criteria."""

    @abstractmethod
    def calculate_score(self, lead_data: dict[str, Any]) -> int:
        """Calculate score for this criteria."""
        pass

    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get strategy name for logging."""
        pass


class BudgetScoringStrategy(LeadScoringStrategy):
    """Strategy for scoring based on budget capacity."""

    def calculate_score(self, lead_data: dict[str, Any]) -> int:
        """Calculate budget score based on budget ranges."""
        budget = lead_data.get("budget")
        if not budget:
            return 0

        # Define budget scoring tiers
        budget_tiers = [
            (10000, 25),  # $10k+ = 25 points
            (5000, 15),  # $5k+ = 15 points
            (1000, 10),  # $1k+ = 10 points
            (0, 5),  # Any budget = 5 points
        ]

        for min_budget, score in budget_tiers:
            if budget >= min_budget:
                return score

        return 0

    def get_strategy_name(self) -> str:
        """Get Strategy Name operation."""
        return "Budget Scoring"


class CustomerTypeScoringStrategy(LeadScoringStrategy):
    """Strategy for scoring based on customer type."""

    def __init__(self):
        """Initialize with customer type scoring matrix."""
        self.type_scores = {
            CustomerType.ENTERPRISE: 30,
            CustomerType.MEDIUM_BUSINESS: 20,
            CustomerType.SMALL_BUSINESS: 15,
            CustomerType.GOVERNMENT: 25,
            CustomerType.EDUCATION: 20,
            CustomerType.HEALTHCARE: 20,
            CustomerType.RESIDENTIAL: 10,
            CustomerType.NON_PROFIT: 15,
        }

    def calculate_score(self, lead_data: dict[str, Any]) -> int:
        """Calculate score based on customer type."""
        customer_type = lead_data.get("customer_type")
        if not customer_type:
            return 0

        return self.type_scores.get(customer_type, 0)

    def get_strategy_name(self) -> str:
        """Get Strategy Name operation."""
        return "Customer Type Scoring"


class LeadSourceScoringStrategy(LeadScoringStrategy):
    """Strategy for scoring based on lead source quality."""

    def __init__(self):
        """Initialize with lead source scoring matrix."""
        self.source_scores = {
            LeadSource.REFERRAL: 20,
            LeadSource.EXISTING_CUSTOMER: 25,
            LeadSource.PARTNER: 15,
            LeadSource.WEBSITE: 10,
            LeadSource.EVENT: 15,
            LeadSource.TRADE_SHOW: 15,
            LeadSource.EMAIL_CAMPAIGN: 10,
            LeadSource.SOCIAL_MEDIA: 8,
            LeadSource.ADVERTISEMENT: 8,
            LeadSource.COLD_CALL: 5,
            LeadSource.OTHER: 5,
        }

    def calculate_score(self, lead_data: dict[str, Any]) -> int:
        """Calculate score based on lead source."""
        source = lead_data.get("lead_source")
        if not source:
            return 0

        return self.source_scores.get(source, 0)

    def get_strategy_name(self) -> str:
        """Get Strategy Name operation."""
        return "Lead Source Scoring"


class BANTScoringStrategy(LeadScoringStrategy):
    """Strategy for scoring based on BANT (Budget, Authority, Need, Timeline) criteria."""

    def calculate_score(self, lead_data: dict[str, Any]) -> int:
        """Calculate score based on BANT criteria."""
        score = 0

        # Authority scoring
        if lead_data.get("authority"):
            score += 10

        # Need scoring
        if lead_data.get("need"):
            score += 15

        # Timeline scoring
        if lead_data.get("timeline"):
            timeline = lead_data["timeline"].lower()
            if "immediate" in timeline or "30 day" in timeline:
                score += 15
            elif "90 day" in timeline or "quarter" in timeline:
                score += 10
            else:
                score += 5

        return score

    def get_strategy_name(self) -> str:
        """Get Strategy Name operation."""
        return "BANT Criteria Scoring"


class CompanySizeScoringStrategy(LeadScoringStrategy):
    """Strategy for scoring based on company size indicators."""

    def calculate_score(self, lead_data: dict[str, Any]) -> int:
        """Calculate score based on company size metrics."""
        score = 0

        # Employee count scoring
        employee_count = lead_data.get("employee_count", 0)
        if employee_count >= 1000:
            score += 15
        elif employee_count >= 100:
            score += 10
        elif employee_count >= 50:
            score += 8
        elif employee_count >= 10:
            score += 5

        # Revenue scoring (if available)
        annual_revenue = lead_data.get("annual_revenue", 0)
        if annual_revenue >= 10000000:  # $10M+
            score += 10
        elif annual_revenue >= 1000000:  # $1M+
            score += 8
        elif annual_revenue >= 100000:  # $100K+
            score += 5

        return score

    def get_strategy_name(self) -> str:
        """Get Strategy Name operation."""
        return "Company Size Scoring"


class EngagementScoringStrategy(LeadScoringStrategy):
    """Strategy for scoring based on engagement indicators."""

    def calculate_score(self, lead_data: dict[str, Any]) -> int:
        """Calculate score based on engagement metrics."""
        score = 0

        # Website activity
        page_views = lead_data.get("page_views", 0)
        if page_views >= 10:
            score += 8
        elif page_views >= 5:
            score += 5
        elif page_views >= 1:
            score += 3

        # Downloaded resources
        downloads = lead_data.get("resource_downloads", 0)
        score += min(downloads * 2, 10)  # Cap at 10 points

        # Email engagement
        email_opens = lead_data.get("email_opens", 0)
        score += min(email_opens, 5)  # Cap at 5 points

        # Social media engagement
        if lead_data.get("social_media_follow"):
            score += 3

        return score

    def get_strategy_name(self) -> str:
        """Get Strategy Name operation."""
        return "Engagement Scoring"
