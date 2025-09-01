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

from .complete_router import reseller_router
from .db_models import *
from .services_complete import *
from .commission_system import *
from .commission_automation import *
from .onboarding_workflow import *
from .customer_lifecycle import *
from .customer_management_advanced import *
from .partner_success_monitoring import *
from .automation_coordinator import *
from .portal_interface import *
from .admin_interface import *

__all__ = [
    "reseller_router",
    "ResellerApplicationService",
    "ResellerService", 
    "ResellerCustomerService",
    "ResellerOnboardingService",
    "EmailService",
    "CommissionCalculator",
    "CommissionService",
    "CommissionReportGenerator",
    "CommissionAutomationEngine",
    "CommissionReconciliationEngine",
    "OnboardingWorkflowEngine",
    "CustomerLifecycleManager",
    "AdvancedCustomerManager",
    "PartnerSuccessEngine",
    "ResellerAutomationCoordinator",
    "ResellerPortalService",
    "ResellerAdminCLI"
]