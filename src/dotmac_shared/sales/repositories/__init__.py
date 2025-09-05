"""
Sales repository components.
"""
try:
    from .lead_repository import LeadRepository
except ImportError as e:
    import warnings

    warnings.warn(f"Lead repository not available: {e}")
    LeadRepository = None

try:
    from .opportunity_repository import OpportunityRepository
except ImportError as e:
    import warnings

    warnings.warn(f"Opportunity repository not available: {e}")
    OpportunityRepository = None

try:
    from .activity_repository import SalesActivityRepository
except ImportError as e:
    import warnings

    warnings.warn(f"Sales activity repository not available: {e}")
    SalesActivityRepository = None

__all__ = ["LeadRepository", "OpportunityRepository", "SalesActivityRepository"]
