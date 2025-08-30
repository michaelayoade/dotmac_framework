"""
Service Assurance Package - Network and Service Monitoring.

This package provides comprehensive service assurance capabilities including:
- Network probing and synthetic monitoring (ICMP, DNS, HTTP, TCP)
- SNMP trap and syslog alarm processing
- NetFlow/sFlow/IPFIX traffic analytics
- SLA compliance monitoring and violation tracking
- Real-time performance metrics and alerting
"""

# Core imports with graceful handling of missing dependencies
try:
    from .sdk.service_assurance_sdk import ServiceAssuranceSDK

    SDK_AVAILABLE = True
except ImportError as e:
    import warnings

    warnings.warn(f"Service Assurance SDK not available: {e}")
    ServiceAssuranceSDK = None
    SDK_AVAILABLE = False

try:
    from .services.alarm_service import AlarmService
    from .services.flow_service import FlowService
    from .services.probe_service import ProbeService

    SERVICES_AVAILABLE = True
except ImportError as e:
    import warnings

    warnings.warn(f"Service Assurance services not available: {e}")
    AlarmService = FlowService = ProbeService = None
    SERVICES_AVAILABLE = False

try:
    from .utils.event_parsers import EventNormalizer, SNMPTrapParser, SyslogParser
    from .utils.metrics_calculators import (
        AlertingThresholds,
        PerformanceMetrics,
        SLACalculator,
        TrafficAnalyzer,
    )

    UTILS_AVAILABLE = True
except ImportError as e:
    import warnings

    warnings.warn(f"Service Assurance utilities not available: {e}")
    SNMPTrapParser = SyslogParser = EventNormalizer = None
    PerformanceMetrics = SLACalculator = TrafficAnalyzer = AlertingThresholds = None
    UTILS_AVAILABLE = False

# Always available - core enums and types
from .core.enums import (
    AlarmSeverity,
    AlarmStatus,
    AlarmType,
    CollectorStatus,
    EventType,
    FlowType,
    ProbeStatus,
    ProbeType,
    SLAComplianceStatus,
)

# Version info
__version__ = "1.0.0"
__author__ = "DotMac Team"
__email__ = "dev@dotmac.com"

# Main exports
__all__ = [
    # Core SDK
    "ServiceAssuranceSDK",
    "create_service_assurance_sdk",
    # Services
    "AlarmService",
    "FlowService",
    "ProbeService",
    # Utilities
    "SNMPTrapParser",
    "SyslogParser",
    "EventNormalizer",
    "PerformanceMetrics",
    "SLACalculator",
    "TrafficAnalyzer",
    "AlertingThresholds",
    # Enums
    "ProbeType",
    "ProbeStatus",
    "AlarmSeverity",
    "AlarmStatus",
    "AlarmType",
    "EventType",
    "FlowType",
    "CollectorStatus",
    "SLAComplianceStatus",
    # Version info
    "__version__",
]

# Configuration defaults
DEFAULT_CONFIG = {
    "probes": {
        "default_interval": 30,
        "default_timeout": 10,
        "max_results_per_probe": 1000,
        "simulation_mode": True,
    },
    "alarms": {
        "storm_threshold": 10,
        "storm_window_minutes": 5,
        "default_severity": "warning",
        "max_memory_alarms": 5000,
    },
    "flows": {
        "max_memory_flows": 10000,
        "default_sampling_rate": 1,
        "aggregation_window_minutes": 15,
    },
    "sla": {
        "default_availability_threshold": 99.9,
        "default_latency_threshold_ms": 100,
        "default_measurement_window_hours": 24,
    },
    "analytics": {
        "anomaly_detection_threshold": 2.0,
        "baseline_window_hours": 24,
        "confidence_level": 0.95,
    },
}


def create_service_assurance_sdk(
    tenant_id: str, database_session=None, config: dict = None
) -> "ServiceAssuranceSDK":
    """
    Create Service Assurance SDK instance.

    Args:
        tenant_id: Unique tenant identifier for multi-tenant isolation
        database_session: Optional database session for persistent storage
        config: Optional configuration overrides

    Returns:
        ServiceAssuranceSDK instance configured for the tenant

    Raises:
        ImportError: If ServiceAssuranceSDK is not available

    Example:
        ```python
        # In-memory mode for testing
        sdk = create_service_assurance_sdk("test-tenant")

        # With database persistence
        sdk = create_service_assurance_sdk(
            tenant_id="production-tenant",
            database_session=db_session,
            config={"probes": {"simulation_mode": False}}
        )

        # Create ICMP probe
        probe = await sdk.create_icmp_probe(
            probe_name="Gateway Monitor",
            target="192.168.1.1",
            interval=30
        )

        # Execute probe
        result = await sdk.execute_probe(probe["probe_id"])
        ```
    """
    if not SDK_AVAILABLE:
        raise ImportError(
            "ServiceAssuranceSDK not available. Please ensure all dependencies are installed."
        )

    # Merge default config with user config
    merged_config = DEFAULT_CONFIG.copy()
    if config:
        for section, settings in config.items():
            if section in merged_config:
                merged_config[section].update(settings)
            else:
                merged_config[section] = settings

    return ServiceAssuranceSDK(
        tenant_id=tenant_id, database_session=database_session, config=merged_config
    )


def create_alarm_processor(
    tenant_id: str, database_session=None, config: dict = None
) -> "AlarmService":
    """
    Create standalone alarm processing service.

    Args:
        tenant_id: Unique tenant identifier
        database_session: Optional database session
        config: Optional configuration overrides

    Returns:
        AlarmService instance for processing SNMP/syslog events

    Example:
        ```python
        alarm_service = create_alarm_processor("tenant-1")

        # Create SNMP trap rule
        rule = await alarm_service.create_alarm_rule(
            rule_name="Link Down Alert",
            event_type="snmp_trap",
            match_criteria={"trap_oid": "1.3.6.1.6.3.1.1.5.3"},
            severity="major"
        )

        # Process SNMP trap
        result = await alarm_service.process_snmp_trap(
            source_device="switch-01",
            source_ip="192.168.1.10",
            trap_oid="1.3.6.1.6.3.1.1.5.3",
            varbinds={"interface": "GigabitEthernet0/1"}
        )
        ```
    """
    if not SERVICES_AVAILABLE:
        raise ImportError(
            "AlarmService not available. Please ensure all dependencies are installed."
        )

    return AlarmService(
        tenant_id=tenant_id,
        database_session=database_session,
        config=config or DEFAULT_CONFIG.get("alarms", {}),
    )


def create_flow_analyzer(
    tenant_id: str, database_session=None, config: dict = None
) -> "FlowService":
    """
    Create standalone flow analytics service.

    Args:
        tenant_id: Unique tenant identifier
        database_session: Optional database session
        config: Optional configuration overrides

    Returns:
        FlowService instance for NetFlow/sFlow analytics

    Example:
        ```python
        flow_service = create_flow_analyzer("tenant-1")

        # Create NetFlow collector
        collector = await flow_service.create_flow_collector(
            collector_name="Core Router Collector",
            flow_type="netflow",
            listen_port=2055
        )

        # Ingest flow data
        await flow_service.ingest_flow_record(
            collector_id=collector["collector_id"],
            exporter_ip="192.168.1.1",
            src_addr="10.0.1.100",
            dst_addr="10.0.2.200",
            src_port=80,
            dst_port=443,
            protocol=6,
            packets=100,
            bytes=64000
        )

        # Get traffic summary
        summary = await flow_service.get_traffic_summary(hours=1)
        ```
    """
    if not SERVICES_AVAILABLE:
        raise ImportError(
            "FlowService not available. Please ensure all dependencies are installed."
        )

    return FlowService(
        tenant_id=tenant_id,
        database_session=database_session,
        config=config or DEFAULT_CONFIG.get("flows", {}),
    )


def get_version():
    """Get package version."""
    return __version__


def get_default_config():
    """Get default configuration."""
    return DEFAULT_CONFIG.copy()


def check_dependencies():
    """Check package dependencies and return status."""
    return {
        "sdk_available": SDK_AVAILABLE,
        "services_available": SERVICES_AVAILABLE,
        "utils_available": UTILS_AVAILABLE,
        "core_enums_available": True,  # Always available
    }


# Package health check
def health_check():
    """Perform basic package health check."""
    deps = check_dependencies()

    health = {
        "package": "service_assurance",
        "version": __version__,
        "status": "healthy" if all(deps.values()) else "degraded",
        "dependencies": deps,
        "available_components": [],
    }

    if SDK_AVAILABLE:
        health["available_components"].append("ServiceAssuranceSDK")
    if SERVICES_AVAILABLE:
        health["available_components"].extend(
            ["AlarmService", "FlowService", "ProbeService"]
        )
    if UTILS_AVAILABLE:
        health["available_components"].extend(["EventParsers", "MetricsCalculators"])

    health["available_components"].append("CoreEnums")

    return health


# Backwards compatibility - create simple factory for basic usage
def create_simple_service_assurance(
    tenant_id: str = "default",
) -> "ServiceAssuranceSDK":
    """
    Create simple Service Assurance SDK for testing and development.

    This is a convenience function for quick setup with in-memory storage.

    Args:
        tenant_id: Tenant identifier (defaults to "default")

    Returns:
        ServiceAssuranceSDK configured with simulation mode enabled

    Example:
        ```python
        # Quick setup for testing
        sa = create_simple_service_assurance()

        # Create and execute a probe
        probe = await sa.create_icmp_probe("Test Probe", "8.8.8.8")
        result = await sa.execute_probe(probe["probe_id"])
        ```
    """
    return create_service_assurance_sdk(
        tenant_id=tenant_id,
        database_session=None,  # In-memory mode
        config={
            "probes": {"simulation_mode": True},
            "alarms": {"storm_threshold": 5},
            "flows": {"max_memory_flows": 1000},
        },
    )
