"""
DotMac Framework Shared Components

Cross-module utilities and common code for the DotMac Framework ecosystem.
"""
import importlib
from typing import Optional

# Re-export database initialization service for convenience
from .database_init import (
    ConnectionValidator,
    DatabaseCreator,
    DatabaseInstance,
    HealthStatus,
    SchemaManager,
    SeedManager,
)

# Re-export consolidated DRY patterns for convenience
try:
    from .repositories import (
        AsyncBaseRepository,
        AsyncTenantRepository,
        RepositoryFactory,
        SyncBaseRepository,
        SyncTenantRepository,
        create_async_repository,
        create_repository,
        create_sync_repository,
    )

    _repositories_available = True
except ImportError:
    _repositories_available = False
    AsyncBaseRepository = AsyncTenantRepository = SyncBaseRepository = None
    SyncTenantRepository = RepositoryFactory = None
    create_repository = create_async_repository = create_sync_repository = None

try:
    from .services import BaseService, ServiceFactory, create_service

    _services_available = True
except ImportError:
    _services_available = False
    BaseService = ServiceFactory = create_service = None

try:
    from .schemas import (
        AuditMixin,
        BaseCreateSchema,
        BaseResponseSchema,
        BaseSchema,
        BaseTenantCreateSchema,
        BaseTenantResponseSchema,
        BaseTenantUpdateSchema,
        BaseUpdateSchema,
        CommonValidators,
        EntityStatus,
        OperationStatus,
        PaginatedResponseSchema,
        SoftDeleteMixin,
        TenantMixin,
        TimestampMixin,
    )

    _schemas_available = True
except ImportError:
    _schemas_available = False
    BaseSchema = BaseCreateSchema = BaseUpdateSchema = BaseResponseSchema = None
    BaseTenantCreateSchema = BaseTenantUpdateSchema = BaseTenantResponseSchema = None
    PaginatedResponseSchema = TimestampMixin = AuditMixin = TenantMixin = None
    SoftDeleteMixin = CommonValidators = EntityStatus = OperationStatus = None

try:
    from .api import (
        PaginatedDependencies,
        RouterFactory,
        StandardDependencies,
        get_admin_deps,
        get_paginated_deps,
        get_standard_deps,
        rate_limit,
        standard_exception_handler,
    )

    _api_available = True
except ImportError:
    _api_available = False
    RouterFactory = standard_exception_handler = rate_limit = None
    StandardDependencies = PaginatedDependencies = None
    get_standard_deps = get_paginated_deps = get_admin_deps = None

try:
    from .validation import BusinessValidators

    _validation_available = True
except ImportError:
    _validation_available = False
    BusinessValidators = None

__version__ = "1.0.0"

# Export commonly used shared services - with safe imports
_available_modules = []

# Core modules that should always be available
core_modules = [
    "database_init",  # Our new module
    "security",
]

# Optional modules that may have additional dependencies
optional_modules = [
    "auth",
    "billing",
    "cache",
    "communication",
    "container",
    "container_monitoring",
    "deployment",
    "events",
    "files",
    "inventory_management",  # Universal inventory management system
    "observability",  # Our new observability package
    "plugins",
    "project_management",  # Universal project management system
    "provisioning",
    "secrets",
    "services",
    "services_framework",  # Universal service lifecycle management framework
    "ticketing",  # Universal ticketing system
    "websockets",
]

# Import core modules safely

for module_name in core_modules:
    try:
        # Use importlib instead of exec() for safe dynamic imports
        module = importlib.import_module(f".{module_name}", package=__name__)
        globals()[module_name] = module
        _available_modules.append(module_name)
    except ImportError:
        import warnings

        warnings.warn(f"Core module {module_name} failed to import")

# Import optional modules with graceful fallback
for module_name in optional_modules:
    try:
        # Use importlib instead of exec() for safe dynamic imports
        module = importlib.import_module(f".{module_name}", package=__name__)
        globals()[module_name] = module
        _available_modules.append(module_name)
    except ImportError:
        # Optional modules can fail silently
        pass


# Re-export observability services for convenience (with graceful handling)
try:
    from .observability import (
        ObservabilityConfig,
        ObservabilityManager,
        get_default_config,
        get_observability,
        init_observability,
    )

    _observability_available = True
except ImportError:
    _observability_available = False
    init_observability = get_observability = ObservabilityManager = None
    ObservabilityConfig = get_default_config = None

# Re-export ticketing services for convenience
try:
    from .ticketing import (
        TicketingPlatformAdapter,
        TicketManager,
        TicketService,
        get_ticket_manager,
        initialize_ticketing,
    )

    _ticketing_available = True
except ImportError:
    _ticketing_available = False
    initialize_ticketing = get_ticket_manager = TicketManager = None
    TicketService = TicketingPlatformAdapter = None

# Re-export project management services for convenience
try:
    from .project_management import (
        ProjectManager,
        ProjectPlatformAdapter,
        ProjectService,
        ProjectWorkflowManager,
        get_project_manager,
        initialize_project_management,
    )

    _project_management_available = True
except ImportError:
    _project_management_available = False
    initialize_project_management = get_project_manager = ProjectManager = None
    ProjectService = ProjectWorkflowManager = ProjectPlatformAdapter = None

# Re-export inventory management services for convenience
try:
    from .inventory_management import (
        InventoryManager,
        InventoryPlatformAdapter,
        InventoryService,
        ISPInventoryAdapter,
        ItemStatus,
        ItemType,
        ManagementInventoryAdapter,
        MovementType,
        PurchaseOrderStatus,
        WarehouseType,
    )

    _inventory_management_available = True
except ImportError:
    _inventory_management_available = False
    InventoryManager = InventoryService = InventoryPlatformAdapter = None
    ISPInventoryAdapter = ManagementInventoryAdapter = None
    ItemType = ItemStatus = MovementType = WarehouseType = PurchaseOrderStatus = None

# Re-export services framework for convenience
try:
    from .services_framework import (  # NotificationService,  # Consolidated to dotmac_shared.notifications.core; NotificationServiceConfig,  # Consolidated to dotmac_shared.notifications.core; create_notification_service,  # Consolidated to dotmac_shared.notifications.core
        AnalyticsService,
        AnalyticsServiceConfig,
        AuthService,
        AuthServiceConfig,
        BaseService,
        ConfigurableService,
        DeploymentAwareServiceFactory,
        HealthAlert,
        HealthMonitor,
        HealthMonitorConfig,
        PaymentService,
        PaymentServiceConfig,
        ServiceConfig,
        ServiceCreationResult,
        ServiceDiscovery,
        ServiceFactory,
        ServiceHealth,
        ServiceRegistry,
        ServiceStatus,
        StatefulService,
        create_analytics_service,
        create_auth_service,
        create_payment_service,
    )

    _services_framework_available = True
except ImportError:
    _services_framework_available = False
    BaseService = ConfigurableService = StatefulService = None
    ServiceStatus = ServiceHealth = ServiceRegistry = ServiceConfig = None
    ServiceFactory = DeploymentAwareServiceFactory = ServiceCreationResult = None
    ServiceDiscovery = HealthMonitor = HealthAlert = HealthMonitorConfig = None
    AuthService = AuthServiceConfig = PaymentService = PaymentServiceConfig = None
    # Notification services consolidated to dotmac_shared.notifications.core
    AnalyticsService = AnalyticsServiceConfig = None
    create_auth_service = create_payment_service = create_analytics_service = None

# Build __all__ dynamically based on what's actually available

# Build DRY pattern exports
repositories_exports = []
if _repositories_available:
    repositories_exports = [
        "AsyncBaseRepository",
        "AsyncTenantRepository",
        "SyncBaseRepository",
        "SyncTenantRepository",
        "RepositoryFactory",
        "create_repository",
        "create_async_repository",
        "create_sync_repository",
    ]

services_exports = []
if _services_available:
    services_exports = [
        "BaseService",
        "ServiceFactory",
        "create_service",
    ]

schemas_exports = []
if _schemas_available:
    schemas_exports = [
        "BaseSchema",
        "BaseCreateSchema",
        "BaseUpdateSchema",
        "BaseResponseSchema",
        "BaseTenantCreateSchema",
        "BaseTenantUpdateSchema",
        "BaseTenantResponseSchema",
        "PaginatedResponseSchema",
        "TimestampMixin",
        "AuditMixin",
        "TenantMixin",
        "SoftDeleteMixin",
        "CommonValidators",
        "EntityStatus",
        "OperationStatus",
    ]

api_exports = []
if _api_available:
    api_exports = [
        "RouterFactory",
        "standard_exception_handler",
        "rate_limit",
        "StandardDependencies",
        "PaginatedDependencies",
        "get_standard_deps",
        "get_paginated_deps",
        "get_admin_deps",
    ]

validation_exports = []
if _validation_available:
    validation_exports = [
        "BusinessValidators",
    ]

observability_exports = []
if _observability_available:
    observability_exports = [
        "init_observability",
        "get_observability",
        "ObservabilityManager",
        "ObservabilityConfig",
        "get_default_config",
    ]

# Build inventory management exports
inventory_exports = []
if _inventory_management_available:
    inventory_exports = [
        "InventoryManager",
        "InventoryService",
        "InventoryPlatformAdapter",
        "ISPInventoryAdapter",
        "ManagementInventoryAdapter",
        "ItemType",
        "ItemStatus",
        "MovementType",
        "WarehouseType",
        "PurchaseOrderStatus",
    ]

# Build services framework exports
services_framework_exports = []
if _services_framework_available:
    services_framework_exports = [
        "BaseService",
        "ConfigurableService",
        "StatefulService",
        "ServiceStatus",
        "ServiceHealth",
        "ServiceRegistry",
        "ServiceConfig",
        "ServiceFactory",
        "DeploymentAwareServiceFactory",
        "ServiceCreationResult",
        "ServiceDiscovery",
        "HealthMonitor",
        "HealthAlert",
        "HealthMonitorConfig",
        "AuthService",
        "AuthServiceConfig",
        "PaymentService",
        "PaymentServiceConfig",
        # "NotificationService",  # Consolidated to dotmac_shared.notifications.core
        "AnalyticsService",
        "AnalyticsServiceConfig",
        "create_auth_service",
        "create_payment_service",
        # "create_notification_service",  # Consolidated to dotmac_shared.notifications.core
        "create_analytics_service",
    ]

__all__ = (
    _available_modules
    + [
        # Database initialization exports (always available)
        "DatabaseCreator",
        "DatabaseInstance",
        "SchemaManager",
        "SeedManager",
        "ConnectionValidator",
        "HealthStatus",
    ]
    + repositories_exports
    + services_exports
    + schemas_exports
    + api_exports
    + validation_exports
    + observability_exports
    + inventory_exports
    + services_framework_exports
)
