"""
DotMac Sales - Customer Relationship Management Toolkit

This package provides comprehensive CRM and sales management capabilities:
- Lead management and scoring
- Opportunity pipeline tracking
- Sales activity management
- Quote and proposal generation
- Sales forecasting and analytics
- Territory management
- Multi-tenant sales operations
"""
from typing import Optional

try:
    from .core.models import (
        ActivityStatus,
        ActivityType,
        CustomerType,
        Lead,
        LeadSource,
        LeadStatus,
        Opportunity,
        OpportunityStage,
        OpportunityStatus,
        Quote,
        QuoteLineItem,
        QuoteStatus,
        SalesActivity,
        SalesForecast,
        Territory,
    )
except ImportError as e:
    import warnings

    warnings.warn(f"Sales core models not available: {e}")
    # Set models to None for availability checking
    Lead = Opportunity = SalesActivity = Quote = None
    LeadSource = LeadStatus = OpportunityStage = None

try:
    from .core.schemas import (
        LeadBase,
        LeadCreate,
        LeadResponse,
        LeadUpdate,
        OpportunityBase,
        OpportunityCreate,
        OpportunityResponse,
        OpportunityUpdate,
        PipelineSummary,
        SalesActivityBase,
        SalesActivityCreate,
        SalesActivityResponse,
        SalesActivityUpdate,
        SalesDashboard,
        SalesMetrics,
    )
except ImportError as e:
    import warnings

    warnings.warn(f"Sales schemas not available: {e}")
    LeadBase = LeadCreate = OpportunityBase = SalesDashboard = None

# Scoring engine imports
try:
    from .scoring.engine import (
        LeadScoringEngine,
        WeightedLeadScoringEngine,
        create_lead_scoring_engine,
    )
    from .scoring.strategies import (
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

    warnings.warn(f"Sales scoring engine not available: {e}")
    LeadScoringEngine = create_lead_scoring_engine = None

# Service layer imports
try:
    from .services.activity_service import SalesActivityService
    from .services.analytics_service import SalesAnalyticsService
    from .services.lead_service import LeadService
    from .services.opportunity_service import OpportunityService
except ImportError as e:
    import warnings

    warnings.warn(f"Sales services not available: {e}")
    LeadService = OpportunityService = SalesActivityService = None

# Repository layer imports
try:
    from .repositories.activity_repository import SalesActivityRepository
    from .repositories.lead_repository import LeadRepository
    from .repositories.opportunity_repository import OpportunityRepository
except ImportError as e:
    import warnings

    warnings.warn(f"Sales repositories not available: {e}")
    LeadRepository = OpportunityRepository = SalesActivityRepository = None

# Platform adapters
try:
    from .adapters.isp_adapter import ISPSalesAdapter
except ImportError:
    ISPSalesAdapter = None

try:
    from .adapters.management_adapter import ManagementPlatformSalesAdapter
except ImportError:
    ManagementPlatformSalesAdapter = None

# Version and metadata
__version__ = "1.0.0"
__author__ = "DotMac Team"
__email__ = "dev@dotmac.com"

# Main exports
__all__ = [
    # Core models
    "Lead",
    "Opportunity",
    "SalesActivity",
    "Quote",
    "QuoteLineItem",
    "SalesForecast",
    "Territory",
    # Enums
    "LeadSource",
    "LeadStatus",
    "OpportunityStage",
    "OpportunityStatus",
    "ActivityType",
    "ActivityStatus",
    "QuoteStatus",
    "CustomerType",
    # Schemas
    "LeadBase",
    "LeadCreate",
    "LeadUpdate",
    "LeadResponse",
    "OpportunityBase",
    "OpportunityCreate",
    "OpportunityUpdate",
    "OpportunityResponse",
    "SalesActivityBase",
    "SalesActivityCreate",
    "SalesActivityUpdate",
    "SalesActivityResponse",
    "SalesDashboard",
    "SalesMetrics",
    "PipelineSummary",
    # Scoring engine
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
    # Services
    "LeadService",
    "OpportunityService",
    "SalesActivityService",
    "SalesAnalyticsService",
    # Repositories
    "LeadRepository",
    "OpportunityRepository",
    "SalesActivityRepository",
    # Platform adapters
    "ISPSalesAdapter",
    "ManagementPlatformSalesAdapter",
    # Version
    "__version__",
]

# Configuration defaults
DEFAULT_CONFIG = {
    "lead_scoring": {
        "engine_type": "standard",  # standard, weighted
        "max_score": 100,
        "auto_qualification_threshold": 70,
        "strategies": {
            "budget": {"enabled": True, "weight": 1.2},
            "customer_type": {"enabled": True, "weight": 1.0},
            "lead_source": {"enabled": True, "weight": 0.8},
            "bant": {"enabled": True, "weight": 1.1},
            "company_size": {"enabled": True, "weight": 0.9},
            "engagement": {"enabled": True, "weight": 0.7},
        },
    },
    "opportunity": {
        "default_probability": 10,
        "auto_stage_progression": True,
        "require_approval_threshold": 50000,
        "forecast_categories": ["pipeline", "best_case", "commit", "closed"],
    },
    "activity": {
        "default_duration_minutes": 60,
        "reminder_enabled": True,
        "auto_follow_up": True,
        "overdue_notification_hours": 2,
    },
    "quote": {
        "default_validity_days": 30,
        "require_approval": True,
        "auto_expiry_notification": True,
        "revision_limit": 5,
    },
    "pipeline": {
        "stages": [
            "prospecting",
            "qualification",
            "needs_analysis",
            "proposal",
            "negotiation",
            "closed_won",
            "closed_lost",
        ],
        "probability_by_stage": {
            "prospecting": 10,
            "qualification": 25,
            "needs_analysis": 40,
            "proposal": 60,
            "negotiation": 80,
            "closed_won": 100,
            "closed_lost": 0,
        },
    },
    "forecasting": {
        "forecast_periods": ["Q1", "Q2", "Q3", "Q4"],
        "accuracy_tracking": True,
        "variance_threshold": 10,  # percentage
        "confidence_levels": ["pipeline", "best_case", "commit"],
    },
}


def get_version():
    """Get package version."""
    return __version__


def get_default_config():
    """Get default sales configuration."""
    return DEFAULT_CONFIG.copy()


# Quick setup functions for common use cases
def create_lead_manager(database_session=None, config: Optional[dict] = None) -> "LeadService":
    """Create a configured lead management service."""
    if not LeadService:
        raise ImportError("Sales services not available")

    config = config or get_default_config()
    return LeadService(database_session, config.get("lead_scoring", {}))


def create_opportunity_manager(database_session=None, config: Optional[dict] = None) -> "OpportunityService":
    """Create a configured opportunity management service."""
    if not OpportunityService:
        raise ImportError("Sales services not available")

    config = config or get_default_config()
    return OpportunityService(database_session, config.get("opportunity", {}))


def create_sales_analytics(database_session=None, config: Optional[dict] = None) -> "SalesAnalyticsService":
    """Create a sales analytics service."""
    if not SalesAnalyticsService:
        raise ImportError("Sales analytics service not available")

    config = config or get_default_config()
    return SalesAnalyticsService(database_session, config)


def create_simple_lead_scorer() -> "LeadScoringEngine":
    """Create a simple lead scoring engine for testing."""
    if not LeadScoringEngine:
        raise ImportError("Lead scoring engine not available")

    return create_lead_scoring_engine(weighted=False)


def create_weighted_lead_scorer(
    weights: Optional[dict] = None,
) -> "WeightedLeadScoringEngine":
    """Create a weighted lead scoring engine."""
    if not WeightedLeadScoringEngine:
        raise ImportError("Weighted lead scoring engine not available")

    return create_lead_scoring_engine(weighted=True, strategy_weights=weights)
