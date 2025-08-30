"""
Core sales components.
"""

# Handle optional dependencies gracefully
try:
    from .models import (
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

    warnings.warn(f"Sales models not available: {e}")
    Lead = Opportunity = SalesActivity = Quote = None
    LeadSource = LeadStatus = OpportunityStage = None

try:
    from .schemas import (
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
    LeadBase = OpportunityBase = SalesDashboard = None

__all__ = [
    # Models
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
]
