"""
DotMac Framework Shared Components

Cross-module utilities and common code for the DotMac Framework ecosystem.
"""

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

# Import core modules
for module_name in core_modules:
    try:
        exec(f"from . import {module_name}")
        _available_modules.append(module_name)
    except ImportError as e:
        import warnings

        warnings.warn(f"Core module {module_name} not available: {e}")

# Import optional modules with graceful fallback
for module_name in optional_modules:
    try:
        exec(f"from . import {module_name}")
        _available_modules.append(module_name)
    except ImportError:
        # Optional modules can fail silently
        pass

# Re-export database initialization service for convenience
from .database_init import (
    ConnectionValidator,
    DatabaseCreator,
    DatabaseInstance,
    HealthStatus,
    SchemaManager,
    SeedManager,
)

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
    # NotificationService = NotificationServiceConfig = AnalyticsService = AnalyticsServiceConfig = None  # Notification services consolidated
    AnalyticsService = AnalyticsServiceConfig = None
    create_auth_service = create_payment_service = create_analytics_service = None
    # create_notification_service = None  # Notification services consolidated

# Build __all__ dynamically based on what's actually available
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
        # "NotificationServiceConfig",  # Consolidated to dotmac_shared.notifications.core
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
    + observability_exports
    + inventory_exports
    + services_framework_exports
)
