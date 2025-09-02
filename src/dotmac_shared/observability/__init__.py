"""
DotMac Framework Comprehensive Observability Package

Production-ready monitoring and observability with SigNoz, Prometheus & Grafana:
- Distributed tracing with log correlation
- Tenant-aware metrics and context propagation  
- Database query monitoring and N+1 detection
- Enhanced APM with Prometheus metrics
- Business metrics monitoring with anomaly detection
- Comprehensive alerting and notification system
- SLA monitoring and performance baseline tracking
- Cache and task processing performance monitoring
- Real-time dashboards for operations teams

Usage:
    from dotmac_shared.observability import setup_comprehensive_observability
    
    # In your FastAPI main.py
    app = FastAPI()
    setup_comprehensive_observability(app, database_engine)
"""

from typing import Optional
import warnings

# Import new observability components
try:
    from .otel import (
        setup_otel,
        get_tracer,
        get_meter,
        OTelConfig,
        # Pre-configured metrics
        tenant_operation_counter,
        tenant_operation_duration,
        db_operation_duration,
        commission_calculation_counter,
        partner_customer_counter,
        # Metric recording functions
        record_tenant_operation,
        record_db_operation,
    )
except ImportError as e:
    warnings.warn(f"OpenTelemetry components not available: {e}")
    setup_otel = get_tracer = get_meter = OTelConfig = None
    tenant_operation_counter = tenant_operation_duration = db_operation_duration = None
    commission_calculation_counter = partner_customer_counter = None
    record_tenant_operation = record_db_operation = None

try:
    from .logging import (
        setup_logging,
        get_logger,
        DotMacLogger,
        OTelTraceContextFilter,
        StructuredFormatter,
        # Pre-configured loggers
        audit_logger,
        security_logger,
        performance_logger,
        business_logger,
    )
except ImportError as e:
    warnings.warn(f"Logging components not available: {e}")
    setup_logging = get_logger = DotMacLogger = None
    OTelTraceContextFilter = StructuredFormatter = None
    audit_logger = security_logger = performance_logger = business_logger = None

try:
    from .middleware import (
        TenantContextMiddleware,
        MetricsMiddleware,
    )
except ImportError as e:
    warnings.warn(f"Middleware components not available: {e}")
    TenantContextMiddleware = MetricsMiddleware = None

try:
    from .database import (
        setup_database_observability,
        traced_db_operation,
        traced_transaction,
        QueryMonitor,
        query_monitor,
    )
except ImportError as e:
    warnings.warn(f"Database observability not available: {e}")
    setup_database_observability = traced_db_operation = traced_transaction = None
    QueryMonitor = query_monitor = None

# Enhanced monitoring components
try:
    from .apm_middleware import (
        EnhancedAPMMiddleware,
        record_cache_operation,
        record_task_queue_size,
        record_task_processing,
        record_database_connections,
        record_rate_limit_hit,
    )
except ImportError as e:
    warnings.warn(f"Enhanced APM middleware not available: {e}")
    EnhancedAPMMiddleware = None
    record_cache_operation = record_task_queue_size = record_task_processing = None
    record_database_connections = record_rate_limit_hit = None

try:
    from .enhanced_business_metrics import (
        enhanced_business_metrics,
        record_revenue_event,
        record_customer_lifecycle_event,
        record_commission_event,
    )
except ImportError as e:
    warnings.warn(f"Enhanced business metrics not available: {e}")
    enhanced_business_metrics = None
    record_revenue_event = record_customer_lifecycle_event = record_commission_event = None

try:
    from .alerting_system import (
        alert_manager,
        trigger_alert,
        add_alert_rule,
        add_notification_target,
        AlertRule,
        NotificationTarget,
        AlertSeverity,
        NotificationChannel,
    )
except ImportError as e:
    warnings.warn(f"Alerting system not available: {e}")
    alert_manager = trigger_alert = add_alert_rule = add_notification_target = None
    AlertRule = NotificationTarget = AlertSeverity = NotificationChannel = None

try:
    from .sla_monitoring import (
        sla_monitor,
        get_sla_status,
        get_performance_baseline_status,
        add_custom_sla_target,
        add_custom_baseline,
        SLATarget,
        PerformanceBaseline,
    )
except ImportError as e:
    warnings.warn(f"SLA monitoring not available: {e}")
    sla_monitor = get_sla_status = get_performance_baseline_status = None
    add_custom_sla_target = add_custom_baseline = SLATarget = PerformanceBaseline = None

try:
    from .cache_task_monitoring import (
        cache_monitor,
        task_monitor,
        monitored_cache_operation,
        monitored_task_processing,
        record_cache_hit,
        record_cache_miss,
        get_cache_stats,
        get_task_stats,
    )
except ImportError as e:
    warnings.warn(f"Cache and task monitoring not available: {e}")
    cache_monitor = task_monitor = None
    monitored_cache_operation = monitored_task_processing = None
    record_cache_hit = record_cache_miss = get_cache_stats = get_task_stats = None

try:
    from .grafana_dashboards import (
        dashboard_generator,
        create_dashboard_files,
    )
except ImportError as e:
    warnings.warn(f"Grafana dashboards not available: {e}")
    dashboard_generator = create_dashboard_files = None


def setup_observability(app, database_engine=None, config=None):
    """
    Basic observability setup for DotMac applications.
    
    This is the basic entry point that configures:
    - OpenTelemetry tracing and metrics
    - Structured logging with trace correlation
    - Tenant context middleware
    - Database monitoring
    - HTTP metrics collection
    
    Args:
        app: FastAPI application instance
        database_engine: SQLAlchemy async engine (optional)
        config: OTelConfig instance (optional)
    
    Returns:
        Tuple of (TracerProvider, MeterProvider)
    """
    if not setup_otel:
        warnings.warn("OpenTelemetry setup not available, skipping observability setup")
        return None, None
    
    # Setup logging first
    if setup_logging:
        setup_logging(
            log_level="INFO",
            enable_trace_correlation=True,
            use_json_format=True
        )
    
    if get_logger:
        logger = get_logger("dotmac.observability")
        logger.info("Initializing DotMac observability stack")
    
    # Setup OpenTelemetry
    tracer_provider, meter_provider = setup_otel(app, database_engine, config)
    
    # Add observability middleware
    if TenantContextMiddleware:
        app.add_middleware(TenantContextMiddleware)
    if MetricsMiddleware:
        app.add_middleware(MetricsMiddleware)
    
    # Setup database monitoring if engine provided
    if database_engine and setup_database_observability:
        setup_database_observability(database_engine)
    
    if get_logger:
        logger = get_logger("dotmac.observability")
        logger.info("DotMac observability setup complete")
    
    return tracer_provider, meter_provider


def setup_comprehensive_observability(
    app,
    database_engine=None,
    config=None,
    enable_enhanced_apm=True,
    enable_business_metrics=True,
    enable_alerting=True,
    enable_sla_monitoring=True,
    enable_cache_monitoring=True,
    create_dashboards=True
):
    """
    Comprehensive observability setup for DotMac applications with full monitoring stack.
    
    This is the complete entry point that configures:
    - OpenTelemetry tracing and metrics with SigNoz
    - Enhanced APM with Prometheus metrics
    - Structured logging with trace correlation
    - Tenant context and performance middleware
    - Database monitoring with N+1 detection
    - Business metrics monitoring with anomaly detection
    - Comprehensive alerting and notification system
    - SLA monitoring and performance baseline tracking
    - Cache and task processing performance monitoring
    - Grafana dashboard generation
    
    Args:
        app: FastAPI application instance
        database_engine: SQLAlchemy async engine (optional)
        config: OTelConfig instance (optional)
        enable_enhanced_apm: Enable enhanced APM middleware with Prometheus metrics
        enable_business_metrics: Enable business metrics collection and anomaly detection
        enable_alerting: Enable alerting and notification system
        enable_sla_monitoring: Enable SLA monitoring and baseline tracking
        enable_cache_monitoring: Enable cache and task monitoring
        create_dashboards: Generate Grafana dashboard JSON files
    
    Returns:
        Dict containing initialized monitoring components
    
    Example:
        >>> from fastapi import FastAPI
        >>> from dotmac_shared.observability import setup_comprehensive_observability
        >>> from your_db import engine
        >>> 
        >>> app = FastAPI()
        >>> monitoring_components = setup_comprehensive_observability(
        ...     app, 
        ...     engine,
        ...     enable_enhanced_apm=True,
        ...     enable_business_metrics=True,
        ...     enable_alerting=True
        ... )
        >>> 
        >>> # Your app now has comprehensive observability!
    """
    components = {}
    
    if not setup_otel:
        warnings.warn("OpenTelemetry setup not available, skipping comprehensive observability setup")
        return components
    
    if get_logger:
        logger = get_logger("dotmac.comprehensive_observability")
        logger.info("Initializing comprehensive DotMac observability stack")
    
    # 1. Setup basic observability
    tracer_provider, meter_provider = setup_observability(app, database_engine, config)
    components["tracer_provider"] = tracer_provider
    components["meter_provider"] = meter_provider
    
    # 2. Enhanced APM middleware
    if enable_enhanced_apm and EnhancedAPMMiddleware:
        apm_middleware = EnhancedAPMMiddleware(
            app,
            enable_system_metrics=True,
            enable_business_metrics=enable_business_metrics,
            enable_anomaly_detection=True
        )
        app.add_middleware(EnhancedAPMMiddleware)
        components["apm_middleware"] = apm_middleware
        
        if get_logger:
            logger.info("Enhanced APM middleware configured")
    
    # 3. Business metrics monitoring
    if enable_business_metrics and enhanced_business_metrics:
        components["business_metrics"] = enhanced_business_metrics
        
        if get_logger:
            logger.info("Business metrics monitoring configured")
    
    # 4. Alerting system
    if enable_alerting and alert_manager:
        components["alert_manager"] = alert_manager
        
        if get_logger:
            logger.info("Alerting system configured with default rules and targets")
    
    # 5. SLA monitoring
    if enable_sla_monitoring and sla_monitor:
        components["sla_monitor"] = sla_monitor
        
        if get_logger:
            logger.info("SLA monitoring and performance baselines configured")
    
    # 6. Cache and task monitoring
    if enable_cache_monitoring:
        if cache_monitor:
            components["cache_monitor"] = cache_monitor
        if task_monitor:
            components["task_monitor"] = task_monitor
        
        if get_logger:
            logger.info("Cache and task processing monitoring configured")
    
    # 7. Generate Grafana dashboards
    if create_dashboards and dashboard_generator:
        try:
            create_dashboard_files("./grafana_dashboards")
            components["dashboards_created"] = True
            
            if get_logger:
                logger.info("Grafana dashboard JSON files created in ./grafana_dashboards/")
        except Exception as e:
            if get_logger:
                logger.warning(f"Failed to create dashboard files: {e}")
            components["dashboards_created"] = False
    
    if get_logger:
        logger.info(
            "Comprehensive DotMac observability setup complete",
            components_initialized=len(components),
            enhanced_apm=enable_enhanced_apm,
            business_metrics=enable_business_metrics,
            alerting=enable_alerting,
            sla_monitoring=enable_sla_monitoring,
            cache_monitoring=enable_cache_monitoring
        )
    
    return components


__all__ = [
    # Main setup functions
    "setup_observability",
    "setup_comprehensive_observability",
    
    # OpenTelemetry components
    "setup_otel",
    "get_tracer", 
    "get_meter",
    "OTelConfig",
    
    # Logging components
    "setup_logging",
    "get_logger",
    "DotMacLogger",
    "OTelTraceContextFilter",
    "StructuredFormatter",
    "audit_logger",
    "security_logger", 
    "performance_logger",
    "business_logger",
    
    # Middleware
    "TenantContextMiddleware",
    "MetricsMiddleware",
    "EnhancedAPMMiddleware",
    
    # Database observability
    "setup_database_observability",
    "traced_db_operation",
    "traced_transaction",
    "QueryMonitor",
    "query_monitor",
    
    # Enhanced business metrics
    "enhanced_business_metrics",
    "record_revenue_event",
    "record_customer_lifecycle_event",
    "record_commission_event",
    
    # Alerting system
    "alert_manager",
    "trigger_alert",
    "add_alert_rule",
    "add_notification_target",
    "AlertRule",
    "NotificationTarget", 
    "AlertSeverity",
    "NotificationChannel",
    
    # SLA monitoring
    "sla_monitor",
    "get_sla_status",
    "get_performance_baseline_status",
    "add_custom_sla_target",
    "add_custom_baseline",
    "SLATarget",
    "PerformanceBaseline",
    
    # Cache and task monitoring
    "cache_monitor",
    "task_monitor",
    "monitored_cache_operation",
    "monitored_task_processing",
    "record_cache_hit",
    "record_cache_miss",
    "get_cache_stats",
    "get_task_stats",
    
    # Grafana dashboards
    "dashboard_generator",
    "create_dashboard_files",
    
    # APM helper functions
    "record_cache_operation",
    "record_task_queue_size", 
    "record_task_processing",
    "record_database_connections",
    "record_rate_limit_hit",
    
    # Pre-configured metrics
    "tenant_operation_counter",
    "tenant_operation_duration",
    "db_operation_duration",
    "commission_calculation_counter",
    "partner_customer_counter",
    
    # Metric recording functions
    "record_tenant_operation",
    "record_db_operation",
]
