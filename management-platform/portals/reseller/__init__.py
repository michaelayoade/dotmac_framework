"""
Reseller Portal for DotMac Management Platform.

This portal provides SaaS channel partner interface including:
- ISP prospect pipeline and sales management
- SaaS commission tracking with recurring revenue focus
- Customer health scoring and expansion opportunities
- Partner training and certification tracking
- Territory management and competitive analysis
"""

from .api import reseller_router
from .schemas import (
    ResellerDashboardOverview,
    SalesOpportunity,
    CommissionSummary,
    CustomerHealthScore,
    TerritoryPerformance,
    SalesQuote,
)

__all__ = [
    "reseller_router", 
    "ResellerDashboardOverview",
    "SalesOpportunity",
    "CommissionSummary",
    "CustomerHealthScore",
    "TerritoryPerformance", 
    "SalesQuote",
]