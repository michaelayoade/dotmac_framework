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

from .admin_interface import ResellerAdminActions, ResellerAdminCLI
from .automation_coordinator import AutomationJobStatus, AutomationJobType, ResellerAutomationCoordinator
from .commission_automation import (
    CommissionAutomationEngine,
    CommissionReconciliationEngine,
    CommissionWorkflowExecution,
    CommissionWorkflowStatus,
    PaymentBatch,
    PaymentStatus,
)
from .commission_system import CommissionCalculator, CommissionReportGenerator, CommissionService
from .complete_router import reseller_router
from .customer_lifecycle import (
    CustomerHealthScore,
    CustomerInteraction,
    CustomerInteractionType,
    CustomerLifecycleManager,
    CustomerLifecycleRecord,
    CustomerLifecycleStage,
)
from .customer_management_advanced import AdvancedCustomerManager
from .db_models import (
    ApplicationStatus,
    Base,
    CommissionStructure,
    Reseller,
    ResellerApplication,
    ResellerCommission,
    ResellerCustomer,
    ResellerOpportunity,
    ResellerStatus,
    ResellerType,
)
from .onboarding_workflow import (
    OnboardingTask,
    OnboardingTaskCategory,
    OnboardingTaskPriority,
    OnboardingTaskStatus,
    OnboardingTaskTemplate,
    OnboardingWorkflowEngine,
    ResellerOnboardingChecklist,
)
from .partner_success_monitoring import (
    AlertSeverity,
    InterventionType,
    PartnerAlert,
    PartnerHealthStatus,
    PartnerInterventionRecord,
    PartnerSuccessEngine,
    PartnerSuccessMetric,
)
from .portal_interface import ResellerPortalRenderer, ResellerPortalService
from .services_complete import (
    EmailService,
    ResellerApplicationService,
    ResellerCustomerService,
    ResellerOnboardingService,
    ResellerService,
)

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
    "ResellerAdminCLI",
]
