"""
DotMac Framework Testing Infrastructure
Provides testing utilities, fixtures, and integration test capabilities
"""

from .event_simulator import EventSimulator
from .integration_base import IntegrationTestBase

# Chaos Engineering Components
try:
    from .chaos_engineering import (
        ChaosExperiment,
        ChaosMetrics,
        DatabaseFailureInjector,
        FailureInjector,
        NetworkFailureInjector,
        ServiceFailureInjector,
    )
    from .chaos_monitoring import AlertManager, ChaosMonitor, MetricsCollector
    from .chaos_pipeline import ChaosPipelineScheduler, PipelineConfig
    from .chaos_scenarios import DotMacChaosScenarios
    from .chaos_test_runner import ChaosTestRunner
    from .resilience_validator import ResilienceLevel, ResilienceValidator

    CHAOS_AVAILABLE = True
except ImportError as e:
    import warnings

    warnings.warn(f"Chaos engineering components not available: {e}")
    CHAOS_AVAILABLE = False
    ChaosExperiment = ChaosTestRunner = None

# Test Data Factories
try:
    from .entity_factories import (
        BillingFactory,
        CustomerFactory,
        DeviceFactory,
        ServiceFactory,
        TenantFactory,
        TicketFactory,
    )
    from .factories import BaseFactory, FactoryRegistry, RelationshipManager
    from .generators import DataGenerator, FakeDataProvider, ISPDataProvider

    FACTORIES_AVAILABLE = True
except ImportError as e:
    import warnings

    warnings.warn(f"Test data factories not available: {e}")
    FACTORIES_AVAILABLE = False
    BaseFactory = FactoryRegistry = None

__all__ = [
    "IntegrationTestBase",
    "EventSimulator",
    "CHAOS_AVAILABLE",
    "FACTORIES_AVAILABLE",
]

# Add chaos components to exports if available
if CHAOS_AVAILABLE:
    __all__.extend(
        [
            "ChaosExperiment",
            "FailureInjector",
            "ChaosMetrics",
            "DotMacChaosScenarios",
            "ResilienceValidator",
            "ResilienceLevel",
            "ChaosMonitor",
            "ChaosPipelineScheduler",
            "PipelineConfig",
            "ChaosTestRunner",
        ]
    )

# Add factory components to exports if available
if FACTORIES_AVAILABLE:
    __all__.extend(
        [
            "BaseFactory",
            "FactoryRegistry",
            "RelationshipManager",
            "DataGenerator",
            "FakeDataProvider",
            "ISPDataProvider",
            "TenantFactory",
            "CustomerFactory",
            "ServiceFactory",
            "BillingFactory",
            "DeviceFactory",
            "TicketFactory",
        ]
    )
