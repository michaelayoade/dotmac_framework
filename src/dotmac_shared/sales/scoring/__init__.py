"""
Sales scoring components.
"""
try:
    from .engine import (
        LeadScoringEngine,
        WeightedLeadScoringEngine,
        create_lead_scoring_engine,
    )
except ImportError as e:
    import warnings

    warnings.warn(f"Lead scoring engine not available: {e}")
    LeadScoringEngine = WeightedLeadScoringEngine = create_lead_scoring_engine = None

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
except ImportError as e:
    import warnings

    warnings.warn(f"Lead scoring strategies not available: {e}")
    LeadScoringStrategy = BudgetScoringStrategy = CustomerTypeScoringStrategy = None
    LeadSourceScoringStrategy = BANTScoringStrategy = CompanySizeScoringStrategy = None
    EngagementScoringStrategy = None

__all__ = [
    "LeadScoringEngine",
    "WeightedLeadScoringEngine",
    "create_lead_scoring_engine",
    "LeadScoringStrategy",
    "BudgetScoringStrategy",
    "CustomerTypeScoringStrategy",
    "LeadSourceScoringStrategy",
    "BANTScoringStrategy",
    "CompanySizeScoringStrategy",
    "EngagementScoringStrategy",
]
