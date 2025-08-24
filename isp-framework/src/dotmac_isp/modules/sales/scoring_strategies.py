"""
Lead scoring strategies using Strategy pattern.
Replaces the 14-complexity _calculate_lead_score method with focused scoring strategies.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class CustomerType(str, Enum):
    """Customer type enumeration."""
    ENTERPRISE = "enterprise"
    MEDIUM_BUSINESS = "medium_business" 
    SMALL_BUSINESS = "small_business"
    GOVERNMENT = "government"
    EDUCATION = "education"
    HEALTHCARE = "healthcare"
    RESIDENTIAL = "residential"
    NON_PROFIT = "non_profit"


class LeadSource(str, Enum):
    """Lead source enumeration."""
    REFERRAL = "referral"
    EXISTING_CUSTOMER = "existing_customer"
    PARTNER = "partner"
    WEBSITE = "website"
    EVENT = "event"
    TRADE_SHOW = "trade_show"
    EMAIL_CAMPAIGN = "email_campaign"
    SOCIAL_MEDIA = "social_media"
    ADVERTISEMENT = "advertisement"
    COLD_CALL = "cold_call"
    OTHER = "other"


class LeadScoringStrategy(ABC):
    """Base strategy for lead scoring criteria."""
    
    @abstractmethod
    def calculate_score(self, lead_data: Dict[str, Any]) -> int:
        """Calculate score for this criteria."""
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get strategy name for logging."""
        pass


class BudgetScoringStrategy(LeadScoringStrategy):
    """Strategy for scoring based on budget capacity."""
    
    def calculate_score(self, lead_data: Dict[str, Any]) -> int:
        """Calculate budget score based on budget ranges."""
        budget = lead_data.get("budget")
        if not budget:
            return 0
        
        # Define budget scoring tiers
        budget_tiers = [
            (10000, 25),  # $10k+ = 25 points
            (5000, 15),   # $5k+ = 15 points  
            (1000, 10),   # $1k+ = 10 points
            (0, 5),       # Any budget = 5 points
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
    
    def calculate_score(self, lead_data: Dict[str, Any]) -> int:
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
    
    def calculate_score(self, lead_data: Dict[str, Any]) -> int:
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
    
    def calculate_score(self, lead_data: Dict[str, Any]) -> int:
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
    
    def calculate_score(self, lead_data: Dict[str, Any]) -> int:
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
        elif annual_revenue >= 100000:   # $100K+
            score += 5
        
        return score
    
    def get_strategy_name(self) -> str:
        """Get Strategy Name operation."""
        return "Company Size Scoring"


class EngagementScoringStrategy(LeadScoringStrategy):
    """Strategy for scoring based on engagement indicators."""
    
    def calculate_score(self, lead_data: Dict[str, Any]) -> int:
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


class LeadScoringEngine:
    """
    Lead scoring engine using Strategy pattern.
    
    REFACTORED: Replaces 14-complexity _calculate_lead_score method with 
    focused, configurable scoring strategies (Complexity: 3).
    """
    
    def __init__(self, custom_strategies: List[LeadScoringStrategy] = None):
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
    
    def calculate_lead_score(self, lead_data: Dict[str, Any]) -> int:
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
    
    def get_scoring_breakdown(self, lead_data: Dict[str, Any]) -> Dict[str, int]:
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
    
    def get_active_strategies(self) -> List[str]:
        """Get list of active scoring strategy names."""
        return [strategy.get_strategy_name() for strategy in self.strategies]


class WeightedLeadScoringEngine(LeadScoringEngine):
    """
    Advanced lead scoring engine with weighted strategies.
    Allows different importance weights for different scoring criteria.
    """
    
    def __init__(self, strategy_weights: Dict[str, float] = None):
        """Initialize with weighted strategies."""
        super().__init__()
        
        # Default weights (can be customized)
        self.strategy_weights = strategy_weights or {
            "Budget Scoring": 1.2,           # Budget is very important
            "Customer Type Scoring": 1.0,    # Standard weight
            "Lead Source Scoring": 0.8,      # Slightly less important
            "BANT Criteria Scoring": 1.1,    # BANT is important
            "Company Size Scoring": 0.9,     # Moderately important
            "Engagement Scoring": 0.7,       # Nice to have
        }
    
    def calculate_lead_score(self, lead_data: Dict[str, Any]) -> int:
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


def create_lead_scoring_engine(weighted: bool = False, 
                              custom_strategies: List[LeadScoringStrategy] = None,
                              strategy_weights: Dict[str, float] = None) -> LeadScoringEngine:
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