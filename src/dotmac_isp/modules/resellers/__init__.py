"""
Reseller Management Module for ISP Framework

Provides comprehensive reseller functionality leveraging shared patterns:
- Website reseller application signup
- Admin application review and approval  
- Reseller portal and dashboard
- Customer assignment and management
- Commission tracking and reporting

Extends dotmac_shared reseller models with ISP-specific functionality.
"""

from .router import reseller_router
from .models import *
from .services import ResellerApplicationService, ResellerService, ResellerCustomerService

__all__ = [
    "reseller_router",
    "ResellerApplicationService",
    "ResellerService", 
    "ResellerCustomerService"
]