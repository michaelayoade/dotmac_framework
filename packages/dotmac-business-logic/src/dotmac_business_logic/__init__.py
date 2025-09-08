"""
DotMac Business Logic Package

Comprehensive business logic components for enterprise applications.
Aggregates related functionality for better maintainability and DRY principles.

Key Modules:
- tasks: Background processing, workflows, and job scheduling
- billing: Invoicing, payments, subscriptions, and revenue management
- files: Document generation, templates, and file processing

Benefits:
- DRY Principles: Shared utilities, no duplication
- Logical Grouping: Related functionality together
- Production Ready: Comprehensive and tested components
- Clear Dependencies: Well-defined module boundaries
- Easier Maintenance: Fewer packages to manage and version

Usage:
    # Task processing
    from dotmac_business_logic.tasks import TaskEngine, WorkflowManager

    # Billing operations
    from dotmac_business_logic.billing import BillingService, Invoice

    # File operations
    from dotmac_business_logic.files import TemplateEngine, DocumentGenerator
"""

__version__ = "1.0.0"
__author__ = "DotMac Framework Team"
__email__ = "support@dotmac.dev"

# Tasks Module - Background processing and workflows
try:
    # TODO: Fix star import - from .tasks import *

    _tasks_available = True
except ImportError:
    _tasks_available = False
    TaskEngine = None
    WorkflowManager = None
    JobScheduler = None
    TaskQueue = None
    BackgroundWorker = None

# Billing Module - Financial operations
try:
    from .billing import (
        BillingService,
        Customer,
        Invoice,
        InvoiceService,
        Payment,
        PaymentService,
        Subscription,
        SubscriptionService,
    )

    _billing_available = True
except ImportError:
    _billing_available = False
    BillingService = None
    InvoiceService = None
    PaymentService = None
    SubscriptionService = None
    Customer = None
    Invoice = None
    Payment = None
    Subscription = None

# Files Module - Document and template management
try:
    from .files import (
        CacheIntegration,
        DocumentGenerator,
        FileProcessor,
        TemplateEngine,
    )

    _files_available = True
except ImportError:
    _files_available = False
    TemplateEngine = None
    DocumentGenerator = None
    FileProcessor = None
    CacheIntegration = None

__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__email__",
    # Tasks exports
    "TaskEngine",
    "WorkflowManager",
    "JobScheduler",
    "TaskQueue",
    "BackgroundWorker",
    # Billing exports
    "BillingService",
    "InvoiceService",
    "PaymentService",
    "SubscriptionService",
    "Customer",
    "Invoice",
    "Payment",
    "Subscription",
    # Files exports
    "TemplateEngine",
    "DocumentGenerator",
    "FileProcessor",
    "CacheIntegration",
]
