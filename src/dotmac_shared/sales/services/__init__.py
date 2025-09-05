"""
Sales service components.
"""
try:
    from .lead_service import LeadService
except ImportError as e:
    import warnings

    warnings.warn(f"Lead service not available: {e}")
    LeadService = None

try:
    from .opportunity_service import OpportunityService
except ImportError as e:
    import warnings

    warnings.warn(f"Opportunity service not available: {e}")
    OpportunityService = None

try:
    from .activity_service import SalesActivityService
except ImportError as e:
    import warnings

    warnings.warn(f"Sales activity service not available: {e}")
    SalesActivityService = None

try:
    from .analytics_service import SalesAnalyticsService
except ImportError as e:
    import warnings

    warnings.warn(f"Sales analytics service not available: {e}")
    SalesAnalyticsService = None

__all__ = [
    "LeadService",
    "OpportunityService",
    "SalesActivityService",
    "SalesAnalyticsService",
]
